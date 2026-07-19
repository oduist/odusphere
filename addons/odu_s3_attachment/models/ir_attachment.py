# -*- coding: utf-8 -*-
import logging

import psycopg2
import pytz

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError
from odoo.http import Stream, request
from odoo.tools import split_every, str2bool
from odoo.tools.image import image_guess_size_from_field_name

from .odu_s3_backend import S3_PREFIX

_logger = logging.getLogger(__name__)


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    # store_fname marker for S3-backed files: 's3://<code>/<sha[:2]>/<sha>'.
    # Reads route on this prefix, so non-prefixed (local) files keep working.
    _S3_PREFIX = S3_PREFIX
    # Web-asset mimetypes kept in Odoo when "keep assets local" is on.
    _S3_ASSET_MIMETYPES = ("text/css", "application/javascript", "text/javascript")

    # ------------------------------------------------------------------
    # global routing configuration (ir.config_parameter, edited in the wizard)
    # ------------------------------------------------------------------
    def _s3_should_offload(self, mimetype, size):
        """Decide whether content of this mimetype/size is eligible for S3.

        This is the "what stays in Odoo" filter only; it does NOT check whether
        a backend is configured. Everything is eligible except, per the global
        settings: web assets (CSS/JS), images below a size threshold, and any
        extra MIME-type prefixes the admin chose to keep local.
        """
        if not mimetype:
            return True
        ICP = self.env["ir.config_parameter"].sudo()
        # 1) web assets (CSS/JS) -> served by Odoo
        if str2bool(ICP.get_param("odu_s3_attachment.keep_assets_local", "True"), True):
            if mimetype in self._S3_ASSET_MIMETYPES:
                return False
        # 2) small images -> kept local (0 disables the rule)
        img_kb = int(ICP.get_param("odu_s3_attachment.keep_images_below_kb", 50) or 0)
        if img_kb and mimetype.startswith("image/") and size <= img_kb * 1024:
            return False
        # 3) advanced: extra comma-separated mimetype prefixes
        extra = ICP.get_param("odu_s3_attachment.keep_local_mimetypes", "") or ""
        for prefix in (p.strip() for p in extra.split(",")):
            if prefix and mimetype.startswith(prefix):
                return False
        return True

    def _s3_direct_download_enabled(self):
        return str2bool(self.env["ir.config_parameter"].sudo().get_param(
            "odu_s3_attachment.direct_download", "True"), False)

    def _s3_signed_ttl(self):
        return int(self.env["ir.config_parameter"].sudo().get_param(
            "odu_s3_attachment.signed_url_ttl", 30) or 30)

    # ------------------------------------------------------------------
    # marker helpers
    # ------------------------------------------------------------------
    def _s3_is_s3(self, fname):
        return bool(fname) and fname.startswith(self._S3_PREFIX)

    def _odu_s3_pending(self):
        """Transaction-scoped {checksum: (backend_id, mimetype)} coordination map.

        In Odoo 19 the S3 routing decision has to be made in
        ``_get_datas_related_values`` (the only hook that sees the mimetype and
        size) while the actual byte upload happens later in a separate
        ``_file_write(raw, checksum)`` call that only receives the checksum.
        The two are bridged by this map, stored on the current cursor so it
        lives exactly as long as the transaction (single-threaded per request).
        """
        cr = self.env.cr
        pending = getattr(cr, "_odu_s3_pending_map", None)
        if pending is None:
            pending = {}
            cr._odu_s3_pending_map = pending
        return pending

    # ------------------------------------------------------------------
    # routing decision (has mimetype + size)
    # ------------------------------------------------------------------
    def _get_datas_related_values(self, data, mimetype):
        values = super()._get_datas_related_values(data, mimetype)
        # Only reroute content that core decided to put in the filestore
        # (store_fname set). 'db' storage and empty data are left untouched.
        store_fname = values.get("store_fname")
        if data and store_fname and not str(store_fname).startswith(self._S3_PREFIX):
            if self._s3_should_offload(mimetype, len(data)):
                checksum = values["checksum"]
                pending = self._odu_s3_pending()
                if checksum in pending:
                    # identical content already routed in this transaction: reuse
                    # the same backend so the single deduplicated _file_write and
                    # every attachment's marker agree on one storage location.
                    backend = self.env["odu.s3.backend"].sudo().browse(pending[checksum][0])
                else:
                    backend = self.env["odu.s3.backend"]._s3_pick_backend(mimetype, len(data))
                if backend:
                    values["store_fname"] = backend._s3_marker(checksum)
                    values["db_datas"] = False
                    pending.setdefault(checksum, (backend.id, mimetype))
        return values

    # ------------------------------------------------------------------
    # storage backend overrides
    # ------------------------------------------------------------------
    @api.model
    def _file_write(self, bin_value, checksum):
        pending = self._odu_s3_pending().pop(checksum, None)
        if pending:
            backend_id, mimetype = pending
            backend = self.env["odu.s3.backend"].sudo().browse(backend_id)
            if backend.exists():
                return backend._s3_upload(checksum, bin_value, mimetype)
        return super()._file_write(bin_value, checksum)

    @api.model
    def _file_read(self, fname, size=None):
        if self._s3_is_s3(fname):
            backend, key = self.env["odu.s3.backend"]._s3_backend_for_marker(fname)
            if backend:
                return backend._s3_read(key, size)
            _logger.warning("odu_s3 read: no backend resolves marker %s", fname)
            return b""
        return super()._file_read(fname, size)

    @api.model
    def _file_delete(self, fname):
        if self._s3_is_s3(fname):
            self._s3_mark_for_gc(fname)
        else:
            return super()._file_delete(fname)

    def _s3_mark_for_gc(self, fname):
        """Queue an S3 object for deferred, reference-counted deletion.

        Written in a separate cursor so the deletion intent survives a rollback
        of the current transaction (object stores are not transactional with
        PostgreSQL). Mirrors the core filestore checklist, likewise written
        outside the transaction.
        """
        with self.env.registry.cursor() as new_cr:
            new_cr.execute(
                "INSERT INTO odu_s3_gc (store_fname) VALUES (%s) "
                "ON CONFLICT (store_fname) DO NOTHING",
                (fname,),
            )
            new_cr.commit()

    # ------------------------------------------------------------------
    # HTTP serving: presigned-URL redirect or stream bytes from S3
    # ------------------------------------------------------------------
    def _to_http_stream(self):
        """Serve S3-backed attachments; delegate local ones to core.

        Core's implementation assumes ``store_fname`` is a local filesystem
        path (``os.stat`` on it), which would fail for our ``s3://`` markers, so
        S3-backed attachments must build their own stream. Access control has
        already been enforced by ``ir.binary._find_record`` before this runs.
        """
        self.ensure_one()
        if self._s3_is_s3(self.store_fname):
            return self._s3_http_stream()
        return super()._to_http_stream()

    def _s3_http_stream(self):
        self.ensure_one()
        backend, key = self.env["odu.s3.backend"]._s3_backend_for_marker(self.store_fname)
        # Direct download: 302 to a short-lived presigned URL, unless an image
        # transform (resize/crop) is requested — those need the actual bytes.
        if backend and self._s3_direct_download_enabled() and not self._s3_transform_requested():
            download = bool(request and request.params.get("download"))
            url = backend._s3_presigned_url(
                key, download=download, filename=self.name, ttl=self._s3_signed_ttl())
            if url:
                return Stream(
                    type="url", url=url, max_age=0,
                    mimetype=self.mimetype, download_name=self.name,
                    etag=self.checksum, public=self.public)
        # Fallback: stream the bytes read back from S3 through Odoo.
        data = self.raw or b""
        return Stream(
            type="data", data=data, mimetype=self.mimetype,
            download_name=self.name, etag=self.checksum, public=self.public,
            size=len(data), last_modified=self.write_date)

    def _s3_transform_requested(self):
        """True when the current request asks /web/image to resize/crop."""
        if not request:
            return False
        params = request.params
        for key in ("width", "height", "quality"):
            try:
                if int(params.get(key) or 0):
                    return True
            except (TypeError, ValueError):
                pass
        # When width and height are omitted, ir.binary derives them later from
        # an Image field name such as ``avatar_128``. A URL stream would make
        # ir.binary return early and skip that resize, so keep these requests on
        # the data-stream path as well.
        field_name = params.get("field")
        if field_name and image_guess_size_from_field_name(field_name) != (0, 0):
            return True
        return str2bool(params.get("crop") or "false", False)

    # ------------------------------------------------------------------
    # migration of existing (local) attachments to S3
    # ------------------------------------------------------------------
    def _s3_offload(self):
        """Relocate each eligible local attachment in ``self`` to S3."""
        moved = 0
        for attach in self:
            if attach._s3_offload_one():
                moved += 1
        return moved

    def _s3_offload_one(self):
        """Relocate ONE local attachment to S3 at the storage layer.

        Reads the local bytes, uploads them to the routed backend, swaps
        ``store_fname`` with a direct SQL UPDATE and garbage-collects the old
        local file. Deliberately bypasses the ir.attachment ORM ``write`` chain,
        so the relocation does NOT trigger sibling modules' write hooks — it is a
        pure storage move that keeps checksum/file_size/dedup intact. Returns
        True if the file was moved.
        """
        self.ensure_one()
        # Stabilize the attachment before reading or uploading. The table lock
        # is compatible with normal attachment writes but excludes both native
        # and S3 GC's SHARE lock until this transaction commits; the row lock
        # serializes this relocation with a concurrent replacement or unlink.
        self.env.cr.execute("LOCK ir_attachment IN ROW EXCLUSIVE MODE")
        self.env.cr.execute(
            "SELECT store_fname FROM ir_attachment WHERE id = %s FOR UPDATE",
            (self.id,),
        )
        row = self.env.cr.fetchone()
        if not row:
            return False
        old = row[0]
        self.invalidate_recordset([
            "store_fname", "raw", "datas", "db_datas", "file_size",
            "checksum", "mimetype", "type",
        ])
        if not old or old.startswith(self._S3_PREFIX) or self.type != "binary":
            return False
        if not self._s3_should_offload(self.mimetype, self.file_size):
            return False
        backend = self.env["odu.s3.backend"]._s3_pick_backend(self.mimetype, self.file_size)
        if not backend:
            return False
        data = self.raw or b""
        # Guard against an unhealthy source filestore (e.g. a dead network mount
        # returning ENOTCONN): core ``_file_read`` swallows the error and returns
        # b'', which would otherwise store empty content and orphan the original.
        if self.file_size and len(data) != self.file_size:
            _logger.warning(
                "odu_s3 migrate: skipping attachment %s, read %d/%d bytes "
                "(source filestore unreadable?)", self.id, len(data), self.file_size)
            return False
        checksum = self.checksum or self._compute_checksum(data)
        new_fname = backend._s3_upload(checksum, data, self.mimetype)
        # swap the storage location without going through the ORM write hooks
        self.env.cr.execute(
            "UPDATE ir_attachment SET store_fname = %s "
            "WHERE id = %s AND store_fname = %s",
            (new_fname, self.id, old))
        if self.env.cr.rowcount != 1:
            _logger.warning(
                "odu_s3 migrate: attachment %s changed during relocation; "
                "leaving the uploaded object queued for GC", self.id)
            return False
        self.invalidate_recordset(["store_fname", "raw", "datas"])
        self._file_delete(old)  # GC the now-orphaned local file (ref-counted)
        return True

    @api.model
    def _s3_migrate_domain(self):
        # Local binary attachments not yet on S3. The explicit res_field terms
        # suppress the automatic res_field=False filter added by
        # ir.attachment._search (same trick as core force_storage), so
        # binary-field attachments are included too.
        return [
            ("type", "=", "binary"),
            ("store_fname", "!=", False),
            ("store_fname", "not like", "s3://%"),
            "|", ("res_field", "=", False), ("res_field", "!=", False),
        ]

    @api.model
    def _s3_local_pending_count(self):
        return self.search_count(self._s3_migrate_domain())

    @api.model
    def _s3_migrated_count(self):
        return self.search_count([
            ("store_fname", "=like", "s3://%"),
            "|", ("res_field", "=", False), ("res_field", "!=", False),
        ])

    @api.model
    def _s3_migrate_is_running(self):
        # read the live (committed) value, bypassing the ORM cache
        self.env.cr.execute(
            "SELECT value FROM ir_config_parameter "
            "WHERE key = 'odu_s3_attachment.migrate_active'")
        row = self.env.cr.fetchone()
        return bool(row) and row[0] in ("1", "True", "true")

    @api.model
    def _s3_migrate_in_window(self):
        """True if the current time is within the configured migration window.

        Hours are interpreted in ``odu_s3_attachment.migrate_window_tz`` (falling
        back to the current user's timezone, then UTC). start == end disables the
        window (migration may run any time). Overnight windows (e.g. 22 -> 6) are
        supported.
        """
        ICP = self.env["ir.config_parameter"].sudo()
        start = int(ICP.get_param("odu_s3_attachment.migrate_window_start", 0) or 0)
        end = int(ICP.get_param("odu_s3_attachment.migrate_window_end", 0) or 0)
        if start == end:
            return True
        tzname = ICP.get_param("odu_s3_attachment.migrate_window_tz") or self.env.user.tz or "UTC"
        try:
            tz = pytz.timezone(tzname)
        except Exception:
            tz = pytz.UTC
        hour = pytz.utc.localize(fields.Datetime.now()).astimezone(tz).hour
        if start < end:
            return start <= hour < end
        return hour >= start or hour < end

    @api.model
    def _s3_migrate_set_flag(self, value):
        """Flip only the on/off parameter (never touches the cron row)."""
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("odu_s3_attachment.migrate_active", "1" if value else "0")
        # keep _s3_migrate_is_running() (raw SQL) consistent
        self.env["ir.config_parameter"].flush_model(["value"])

    @api.model
    def _s3_migrate_set_running(self, running):
        if not self.env.is_admin():
            raise AccessError(_("Only administrators can manage S3 migration."))
        if running and not self.env["odu.s3.backend"]._s3_has_backend():
            raise UserError(_("No active S3 backend is configured."))
        self._s3_migrate_set_flag(running)
        cron = self.env.ref(
            "odu_s3_attachment.ir_cron_odu_s3_migrate", raise_if_not_found=False)
        if not cron:
            return
        # Writing the cron row would deadlock if a job is live, so guard it.
        # Start is only reachable when not running, so activation is safe; Stop
        # relies on the flag (checked between batches), the cron write being a
        # best-effort tidy-up.
        if running:
            try:
                cron.sudo().write({"active": True, "nextcall": fields.Datetime.now()})
                cron.sudo()._trigger()
            except Exception:
                pass
        else:
            try:
                cron.sudo().write({"active": False})
            except Exception:
                pass

    @api.model
    def _cron_odu_s3_migrate(self):
        """Background worker: relocate eligible local attachments to S3.

        Gated by the ``odu_s3_attachment.migrate_active`` flag (Start/Stop) and
        the configured time window. Works in id-ordered, per-batch-committed
        chunks; re-checks the flag and window between batches and clears the flag
        once a full sweep finds nothing left to move. Never writes the cron
        record itself (that would deadlock on its own row lock).
        """
        if not self._s3_migrate_is_running():
            return
        if not self.env["odu.s3.backend"]._s3_has_backend():
            self._s3_migrate_set_flag(False)
            return
        if not self._s3_migrate_in_window():
            return  # outside the allowed window -> nothing to do this tick
        batch_size = int(self.env["ir.config_parameter"].sudo().get_param(
            "odu_s3_attachment.migrate_batch_size", 100) or 100)
        domain = self._s3_migrate_domain()
        last_id = 0
        moved = 0
        had_errors = False
        while True:
            if not self._s3_migrate_is_running():
                _logger.info("odu_s3 migration stopped (%d moved this run)", moved)
                return
            if not self._s3_migrate_in_window():
                _logger.info("odu_s3 migration paused: outside window "
                             "(%d moved this run)", moved)
                return
            batch = self.search(
                domain + [("id", ">", last_id)], order="id", limit=batch_size)
            if not batch:
                break
            last_id = batch[-1].id
            for attach in batch:
                try:
                    # Isolate every attachment so one PostgreSQL error cannot
                    # roll back successful relocations earlier in the batch.
                    with self.env.cr.savepoint():
                        moved_one = attach._s3_offload_one()
                    if moved_one:
                        moved += 1
                except psycopg2.OperationalError:
                    had_errors = True
                    _logger.warning("odu_s3 migrate: deferring attachment %s "
                                    "(concurrent update)", attach.id)
                except Exception:
                    had_errors = True
                    _logger.warning("odu_s3 migrate: error on attachment %s",
                                    attach.id, exc_info=True)
            self.env.cr.commit()
        if had_errors:
            _logger.warning(
                "odu_s3 migration deferred failed attachments; %d moved this "
                "run and migration remains active for retry", moved)
            return
        self._s3_migrate_set_flag(False)
        _logger.info("odu_s3 migration finished (%d moved this run)", moved)

    # ------------------------------------------------------------------
    # garbage collection of orphaned S3 objects (dedup-aware, multi-backend)
    # ------------------------------------------------------------------
    @api.autovacuum
    def _gc_odu_s3_store(self):
        if not self.env["odu.s3.backend"]._s3_has_backend(include_archived=True):
            return
        cr = self.env.cr
        # Continue in a new transaction; the LOCK below must be the first
        # statement so the snapshot sees the most recent ir_attachment changes.
        cr.commit()
        cr.execute("SET LOCAL lock_timeout TO '10s'")
        try:
            cr.execute("LOCK ir_attachment IN SHARE MODE")
        except psycopg2.errors.LockNotAvailable:
            cr.rollback()
            return False
        self._gc_odu_s3_collect()
        cr.commit()

    def _gc_odu_s3_collect(self):
        """The actual orphan sweep, without transaction management.

        Split out from ``_gc_odu_s3_store`` so it can be exercised inside a test
        transaction (the commit/LOCK wrapper would break the test savepoints).
        """
        cr = self.env.cr
        # make sure pending ORM writes are reflected in the raw SQL below
        self.env["ir.attachment"].flush_model(["store_fname"])
        self.env["odu.s3.gc"].flush_model(["store_fname"])
        cr.execute("SELECT id, store_fname FROM odu_s3_gc")
        rows = cr.fetchall()
        if not rows:
            return 0

        by_fname = {}
        for gc_id, fname in rows:
            by_fname.setdefault(fname, []).append(gc_id)

        referenced = set()
        for chunk in split_every(cr.IN_MAX, list(by_fname)):
            cr.execute(
                "SELECT store_fname FROM ir_attachment WHERE store_fname IN %s",
                [tuple(chunk)])
            referenced.update(row[0] for row in cr.fetchall())

        Backend = self.env["odu.s3.backend"].sudo()
        removed = 0
        processed_ids = []
        for fname, ids in by_fname.items():
            if fname not in referenced:
                backend, key = Backend._s3_backend_for_marker(fname)
                if not backend:
                    _logger.warning("odu_s3 gc: no backend resolves %s, keeping "
                                    "queue entry", fname)
                    continue  # keep the entry, retry once the backend is back
                try:
                    backend._s3_delete(key)
                    removed += 1
                except Exception:
                    _logger.info("odu_s3 gc could not delete %s", fname, exc_info=True)
                    continue  # keep the queue entry, retry next run
            processed_ids.extend(ids)

        if processed_ids:
            cr.execute(
                "DELETE FROM odu_s3_gc WHERE id IN %s", [tuple(processed_ids)])
        _logger.info("odu_s3 gc: %d checked, %d removed", len(rows), removed)
        return removed

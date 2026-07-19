# -*- coding: utf-8 -*-
import logging
import re

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

from . import s3_client

_logger = logging.getLogger(__name__)

# store_fname marker prefix identifying an S3-backed object.
S3_PREFIX = "s3://"
# A backend code must be a safe, stable slug: it is embedded verbatim in the
# store_fname marker of every object stored on the backend and must never
# change once objects exist.
_CODE_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


class OduS3Backend(models.Model):
    """An S3-compatible object store attachments can be offloaded to.

    Several backends may be active at once. When a new attachment is offloaded
    the backends are consulted in ``sequence`` order and the first one whose
    MIME-type filter matches claims the upload; its ``code`` is baked into the
    object's ``store_fname`` marker (``s3://<code>/<sha[:2]>/<sha>``), so reads
    always route back to the exact store the object lives on — even after the
    default/active target has been changed to a different S3.
    """

    _name = "odu.s3.backend"
    _description = "S3 Storage Backend"
    _order = "sequence, id"

    name = fields.Char(required=True, help="Human-readable label for this store.")
    code = fields.Char(
        required=True,
        help="Stable slug embedded in every stored object's location marker "
             "(s3://<code>/...). Lowercase letters, digits, '-' and '_' only. "
             "Do NOT change it after objects have been stored here — existing "
             "attachments would become unreadable.")
    active = fields.Boolean(
        default=True,
        help="Archived backends no longer receive new uploads, but their "
             "objects stay readable (the marker still resolves to them).")
    sequence = fields.Integer(
        default=10,
        help="Routing priority. Lower comes first; the first active backend "
             "whose MIME filter matches a new attachment claims it.")

    # --- connection ---
    endpoint_url = fields.Char(
        string="Endpoint URL",
        help="S3 API endpoint. Leave empty for AWS S3; set it for MinIO, "
             "Wasabi, Cloudflare R2, DigitalOcean Spaces, Ceph, ... "
             "(e.g. http://minio:9000).")
    public_endpoint_url = fields.Char(
        string="Public Endpoint URL",
        help="Host used to sign presigned URLs when the public address differs "
             "from the one Odoo uses internally (e.g. an internal MinIO behind "
             "a public proxy). Leave empty to sign against the Endpoint URL.")
    bucket = fields.Char(required=True, help="Target bucket name (kept private).")
    region = fields.Char(help="Region name, e.g. eu-central-1. Optional for MinIO.")
    access_key = fields.Char(string="Access Key", required=True)
    secret_key = fields.Char(string="Secret Key", required=True)

    # --- routing ---
    mimetype_prefixes = fields.Char(
        string="MIME Filter",
        help="Optional comma-separated MIME-type prefixes this backend claims, "
             "e.g. 'application/pdf, image/'. Leave empty to make it a catch-all "
             "(claims anything reaching it). Order backends with the 'Priority' "
             "field; put the catch-all last.")

    # --- diagnostics ---
    status = fields.Char(
        string="Configuration", compute="_compute_status",
        help="Configuration completeness. Use 'Test Connection' for a live "
             "reachability check (which makes a network call).")

    _code_uniq = models.Constraint(
        "UNIQUE (code)", "The backend code must be unique.")

    # ------------------------------------------------------------------
    # constraints
    # ------------------------------------------------------------------
    @api.constrains("code")
    def _check_code(self):
        for backend in self:
            if not backend.code or not _CODE_RE.match(backend.code):
                raise ValidationError(_(
                    "Backend code %r is invalid: use lowercase letters, digits, "
                    "'-' and '_' only, starting with a letter or digit.",
                    backend.code))

    def write(self, vals):
        # Both values form the durable location resolved by every marker.
        # Credentials and endpoints remain editable for normal rotation and
        # network-address changes, but a different code or bucket is a different
        # physical store and must be represented by a new backend.
        location_fields = {"code", "bucket"} & vals.keys()
        if location_fields:
            for backend in self:
                changed = [
                    field_name for field_name in location_fields
                    if backend[field_name] != vals[field_name]
                ]
                if changed and backend._s3_has_objects():
                    raise UserError(_(
                        "Cannot change the storage location of backend %r: "
                        "files are stored on it or awaiting cleanup. Create a "
                        "new backend instead.",
                        backend.name))
        return super().write(vals)

    def unlink(self):
        for backend in self:
            if backend._s3_has_objects():
                raise UserError(_(
                    "Cannot delete backend %r while files are stored on it or "
                    "awaiting cleanup. Archive the backend instead so existing "
                    "files remain readable and cleanup can finish.",
                    backend.name))
        return super().unlink()

    def _s3_has_objects(self):
        """True if a live or queued object marker points at this backend."""
        self.ensure_one()
        marker_domain = [("store_fname", "=like", "s3://%s/%%" % self.code)]
        if self.env["ir.attachment"].sudo().search_count(marker_domain + [
            "|", ("res_field", "=", False), ("res_field", "!=", False),
        ], limit=1):
            return True
        return bool(self.env["odu.s3.gc"].sudo().search_count(marker_domain, limit=1))

    # ------------------------------------------------------------------
    # diagnostics
    # ------------------------------------------------------------------
    @api.depends("bucket", "access_key", "secret_key")
    def _compute_status(self):
        # Cheap, no network: form-load must not block on an unreachable store.
        for backend in self:
            if not s3_client.HAS_BOTO3:
                backend.status = _("boto3 is not installed on the Odoo server.")
            elif not (backend.access_key and backend.secret_key and backend.bucket):
                backend.status = _("Incomplete configuration.")
            else:
                backend.status = _("Configured — press 'Test Connection' to verify.")

    def _s3_probe(self):
        """Live reachability check (network). Returns a human-readable status."""
        self.ensure_one()
        if not s3_client.HAS_BOTO3:
            return _("boto3 is not installed on the Odoo server.")
        if not (self.access_key and self.secret_key and self.bucket):
            return _("Incomplete configuration.")
        try:
            self._s3_client().head_bucket(Bucket=self.sudo().bucket)
            return _("Connected — bucket \"%s\" reachable.", self.bucket)
        except Exception as exc:  # noqa: BLE001 - surface any connection error
            return _("Error reaching bucket \"%s\": %s", self.bucket, exc)

    def action_test_connection(self):
        self.ensure_one()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "info",
                "title": _("S3 backend: %s", self.name),
                "message": self._s3_probe(),
                "sticky": False,
            },
        }

    # ------------------------------------------------------------------
    # routing (which backend claims a new upload)
    # ------------------------------------------------------------------
    @api.model
    def _s3_pick_backend(self, mimetype, size):
        """Return the active backend that should store new content of this kind.

        Backends are evaluated in ``sequence`` order; the first whose MIME
        filter matches wins. Returns an empty recordset when none matches (the
        content then stays in the local filestore).
        """
        for backend in self.sudo().search([]):
            if backend._s3_matches(mimetype, size):
                return backend
        return self.browse()

    def _s3_matches(self, mimetype, size):
        """True if this backend's MIME filter accepts ``mimetype``."""
        self.ensure_one()
        prefixes = [p.strip() for p in (self.mimetype_prefixes or "").split(",") if p.strip()]
        if not prefixes:
            return True  # catch-all
        return any((mimetype or "").startswith(prefix) for prefix in prefixes)

    @api.model
    def _s3_has_backend(self, include_archived=False):
        """Return whether a usable backend record exists.

        Upload routing and migration use the default active-only behavior. GC
        includes archived records because they remain authoritative for objects
        already stored on them.
        """
        backends = self.sudo()
        if include_archived:
            backends = backends.with_context(active_test=False)
        return bool(backends.search_count([], limit=1))

    # ------------------------------------------------------------------
    # marker <-> (backend, key)
    # ------------------------------------------------------------------
    def _s3_key(self, checksum):
        """Content-addressed object key, same scatter as the native filestore."""
        return checksum[:2] + "/" + checksum

    def _s3_marker(self, checksum):
        """Full ``store_fname`` marker for content stored on this backend."""
        self.ensure_one()
        return S3_PREFIX + self.code + "/" + self._s3_key(checksum)

    @api.model
    def _s3_backend_for_marker(self, fname):
        """Resolve an ``s3://<code>/<key>`` marker to ``(backend, key)``.

        Uses ``active_test=False`` so objects on an archived backend stay
        readable. Returns ``(empty recordset, '')`` when the code is unknown.
        """
        rest = fname[len(S3_PREFIX):]
        code, sep, key = rest.partition("/")
        if not sep:
            return self.browse(), ""
        backend = self.sudo().with_context(active_test=False).search(
            [("code", "=", code)], limit=1)
        return backend, key

    # ------------------------------------------------------------------
    # boto3 operations
    # ------------------------------------------------------------------
    def _s3_settings(self, public=False):
        self.ensure_one()
        backend = self.sudo()
        return {
            "endpoint_url": backend.endpoint_url or None,
            "public_endpoint_url": backend.public_endpoint_url or None,
            "access_key": backend.access_key,
            "secret_key": backend.secret_key,
            "region": backend.region or None,
        }

    def _s3_client(self, public=False):
        return s3_client.get_client(self._s3_settings(public=public), public=public)

    def _s3_upload(self, checksum, data, mimetype=None):
        """Upload ``data`` (dedup-aware) and return its ``store_fname`` marker."""
        self.ensure_one()
        key = self._s3_key(checksum)
        marker = self._s3_marker(checksum)
        # Object storage is not transactional. Register the prospective object
        # before touching S3 so a later PostgreSQL rollback leaves a durable GC
        # intent, exactly like Odoo's native filestore checklist.
        self.env["ir.attachment"]._s3_mark_for_gc(marker)
        s3_client.upload_dedup(self._s3_client(), self.sudo().bucket, key, data, mimetype)
        return marker

    def _s3_read(self, key, size=None):
        """Read an object's bytes; return b'' on any error (mirrors core)."""
        self.ensure_one()
        try:
            resp = self._s3_client().get_object(Bucket=self.sudo().bucket, Key=key)
            return resp["Body"].read(size)
        except Exception:
            _logger.info("odu_s3 read failed for %s/%s", self.code, key, exc_info=True)
            return b""

    def _s3_delete(self, key):
        """Delete a single object (used by the dedup-aware GC)."""
        self.ensure_one()
        self._s3_client().delete_object(Bucket=self.sudo().bucket, Key=key)

    def _s3_presigned_url(self, key, download=False, filename=None, ttl=30):
        """Generate a short-lived presigned GET URL, or False on failure."""
        self.ensure_one()
        params = {"Bucket": self.sudo().bucket, "Key": key}
        if download:
            name = (filename or "download").replace("\"", "")
            params["ResponseContentDisposition"] = "attachment; filename=\"%s\"" % name
        try:
            client = self._s3_client(public=True)
            return client.generate_presigned_url(
                "get_object", Params=params, ExpiresIn=ttl)
        except Exception:
            _logger.info("odu_s3 presigned URL failed for %s/%s", self.code, key,
                         exc_info=True)
            return False

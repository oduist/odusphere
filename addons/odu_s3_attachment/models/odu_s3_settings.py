# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.tools import str2bool


class OduS3Settings(models.TransientModel):
    """Global S3 storage settings + migration console.

    A lightweight settings surface (deliberately not ``res.config.settings``, to
    avoid depending on ``base_setup`` — outside the OduSphere allowed framework
    set). Every value is persisted as an ``ir.config_parameter``: loaded in
    ``default_get`` and written back in ``action_apply``.
    """

    _name = "odu.s3.settings"
    _description = "S3 Storage Settings"

    # --- routing: what stays in Odoo ---
    keep_assets_local = fields.Boolean(
        string="Keep web assets (CSS/JS) in Odoo", default=True,
        help="Serve CSS/JavaScript bundles from Odoo instead of S3. "
             "Recommended — they are tiny and latency-sensitive.")
    keep_images_below_kb = fields.Integer(
        string="Keep images smaller than (KB) in Odoo", default=50,
        help="Images below this size stay in Odoo (avatars, thumbnails). "
             "Set to 0 to send all images to S3.")
    keep_local_mimetypes = fields.Char(
        string="Also keep these MIME types in Odoo",
        help="Advanced: comma-separated MIME-type prefixes to keep local, "
             "e.g. 'application/xml, text/'. Leave empty if unsure.")

    # --- direct download ---
    direct_download = fields.Boolean(
        string="Direct download via presigned URL", default=True,
        help="Serve S3-backed files by redirecting (302) to a short-lived "
             "presigned URL after access rights are checked, so the bytes are "
             "fetched straight from the object store instead of through Odoo.")
    signed_url_ttl = fields.Integer(
        string="Presigned URL TTL (seconds)", default=30,
        help="Validity of generated presigned download URLs.")

    # --- migration ---
    migrate_batch_size = fields.Integer(
        string="Migration batch size", default=100,
        help="Number of attachments scanned per batch during migration.")
    migrate_window_start = fields.Integer(
        string="Run from (hour)", default=0,
        help="Migration only runs at or after this hour. Leave start = end to "
             "allow migration at any time.")
    migrate_window_end = fields.Integer(
        string="Run until (hour)", default=0,
        help="Migration stops when this hour is reached (and resumes next day). "
             "Supports overnight windows, e.g. 22 -> 6.")
    migrate_window_tz = fields.Char(
        string="Window timezone",
        help="Timezone for the migration window hours (e.g. Europe/Warsaw). "
             "Empty = the current user timezone, then UTC.")

    # --- read-only diagnostics / progress ---
    backend_count = fields.Integer(string="Configured backends", readonly=True)
    migrated_count = fields.Integer(string="Attachments on S3", readonly=True)
    local_count = fields.Integer(string="Local attachments pending", readonly=True)
    migration_running = fields.Boolean(string="Migration running", readonly=True)

    # ------------------------------------------------------------------
    # load / persist
    # ------------------------------------------------------------------
    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        ICP = self.env["ir.config_parameter"].sudo()
        Att = self.env["ir.attachment"]
        res.update(
            keep_assets_local=str2bool(
                ICP.get_param("odu_s3_attachment.keep_assets_local", "True"), True),
            keep_images_below_kb=int(
                ICP.get_param("odu_s3_attachment.keep_images_below_kb", 50) or 0),
            keep_local_mimetypes=ICP.get_param("odu_s3_attachment.keep_local_mimetypes", "") or "",
            direct_download=str2bool(
                ICP.get_param("odu_s3_attachment.direct_download", "True"), True),
            signed_url_ttl=int(ICP.get_param("odu_s3_attachment.signed_url_ttl", 30) or 30),
            migrate_batch_size=int(
                ICP.get_param("odu_s3_attachment.migrate_batch_size", 100) or 100),
            migrate_window_start=int(
                ICP.get_param("odu_s3_attachment.migrate_window_start", 0) or 0),
            migrate_window_end=int(
                ICP.get_param("odu_s3_attachment.migrate_window_end", 0) or 0),
            migrate_window_tz=ICP.get_param("odu_s3_attachment.migrate_window_tz", "") or "",
            backend_count=self.env["odu.s3.backend"].sudo().search_count([]),
            migrated_count=Att._s3_migrated_count(),
            local_count=Att._s3_local_pending_count(),
            migration_running=Att._s3_migrate_is_running(),
        )
        return res

    def action_apply(self):
        self.ensure_one()
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("odu_s3_attachment.keep_assets_local", str(self.keep_assets_local))
        ICP.set_param("odu_s3_attachment.keep_images_below_kb", str(self.keep_images_below_kb or 0))
        ICP.set_param("odu_s3_attachment.keep_local_mimetypes", self.keep_local_mimetypes or "")
        ICP.set_param("odu_s3_attachment.direct_download", str(self.direct_download))
        ICP.set_param("odu_s3_attachment.signed_url_ttl", str(self.signed_url_ttl or 30))
        ICP.set_param("odu_s3_attachment.migrate_batch_size", str(self.migrate_batch_size or 100))
        ICP.set_param("odu_s3_attachment.migrate_window_start", str(self.migrate_window_start or 0))
        ICP.set_param("odu_s3_attachment.migrate_window_end", str(self.migrate_window_end or 0))
        ICP.set_param("odu_s3_attachment.migrate_window_tz", self.migrate_window_tz or "")
        return self._reload()

    # ------------------------------------------------------------------
    # migration console
    # ------------------------------------------------------------------
    def action_migrate_start(self):
        self.ensure_one()
        self.action_apply()  # persist batch size / window before starting
        self.env["ir.attachment"]._s3_migrate_set_running(True)
        return self._reload()

    def action_migrate_stop(self):
        self.ensure_one()
        self.env["ir.attachment"]._s3_migrate_set_running(False)
        return self._reload()

    def action_refresh(self):
        self.ensure_one()
        return self._reload()

    def _reload(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": "odu.s3.settings",
            "view_mode": "form",
            "target": "current",
            "name": _("S3 Storage Settings"),
        }

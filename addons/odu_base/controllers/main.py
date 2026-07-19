# -*- coding: utf-8 -*-
import re
from datetime import timedelta

from odoo import fields, http
from odoo.http import request

#: Permissive email shape check — real validation is whether delivery works.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

#: Upper bounds so a public, unauthenticated endpoint cannot store huge blobs.
_MAX_NAME = 200
_MAX_EMAIL = 254
_MAX_MESSAGE = 5000
_MAX_IP = 64

#: Hard cap on the raw request body. Enforced before the JSON is parsed so a
#: public caller cannot force the server to buffer a huge payload in memory.
#: (The gateway caps this too; this is the guaranteed application-layer backstop.)
_MAX_BODY_BYTES = 64 * 1024

#: Admin-tunable per-IP rate limit. A max of 0 (or below) disables the limit.
_RATE_MAX_PARAM = "odu_base.contact_rate_limit_max"
_RATE_WINDOW_PARAM = "odu_base.contact_rate_limit_window_minutes"
_RATE_MAX_DEFAULT = 10
_RATE_WINDOW_DEFAULT = 10


class OduContactController(http.Controller):
    """Public contact endpoint backing the starter website's contact form."""

    @http.route(
        "/api/contact",
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def submit_contact(self):
        """Persist a contact request sent by the public website.

        Expects a JSON body ``{"name", "email", "message"}`` plus an optional
        ``company`` honeypot field. Returns ``{"ok": true}`` on success, or
        ``{"ok": false, "error": ...}`` with a non-200 status on bad input.

        Abuse controls for this anonymous endpoint, in order: an oversized body
        is rejected (413) before parsing; a filled honeypot is silently dropped;
        and once validated, submissions from the same IP are throttled (429).
        Records are created with ``sudo()`` because the public user holds no
        access on the model (only administrators do).
        """
        # Reject oversized bodies before reading/parsing them.
        content_length = request.httprequest.content_length
        if content_length is not None and content_length > _MAX_BODY_BYTES:
            return request.make_json_response(
                {"ok": False, "error": "Request too large."}, status=413
            )

        try:
            payload = request.get_json_data()
        except Exception:
            return request.make_json_response(
                {"ok": False, "error": "Invalid request."}, status=400
            )

        if not isinstance(payload, dict):
            return request.make_json_response(
                {"ok": False, "error": "Invalid request."}, status=400
            )

        # Honeypot: a real visitor never fills this. Pretend success, store nothing.
        if (payload.get("company") or "").strip():
            return request.make_json_response({"ok": True})

        name = (payload.get("name") or "").strip()
        email = (payload.get("email") or "").strip()
        message = (payload.get("message") or "").strip()

        if not name or not email or not message:
            return request.make_json_response(
                {"ok": False, "error": "Name, email and message are required."},
                status=400,
            )
        if not _EMAIL_RE.match(email):
            return request.make_json_response(
                {"ok": False, "error": "Please provide a valid email address."},
                status=400,
            )

        client_ip = request.httprequest.remote_addr or ""
        if self._contact_rate_limited(client_ip):
            return request.make_json_response(
                {"ok": False, "error": "Too many requests. Please try again later."},
                status=429,
            )

        request.env["odu.contact.message"].sudo().create(
            {
                "name": name[:_MAX_NAME],
                "email": email[:_MAX_EMAIL],
                "message": message[:_MAX_MESSAGE],
                "client_ip": client_ip[:_MAX_IP],
            }
        )
        return request.make_json_response({"ok": True})

    def _contact_rate_limited(self, client_ip):
        """Return ``True`` when ``client_ip`` exceeded its recent-submission quota.

        The quota and window are tunable via the ``odu_base.contact_rate_limit_max``
        and ``…_window_minutes`` system parameters; a max of 0 disables the limit.
        Accurate per-client limiting requires Odoo ``proxy_mode`` so ``remote_addr``
        is the real visitor's IP and not the gateway's — see the Admin Guide.
        """
        if not client_ip:
            return False
        params = request.env["ir.config_parameter"].sudo()
        max_recent = self._int_param(params, _RATE_MAX_PARAM, _RATE_MAX_DEFAULT)
        window = self._int_param(params, _RATE_WINDOW_PARAM, _RATE_WINDOW_DEFAULT)
        if max_recent <= 0 or window <= 0:
            return False
        since = fields.Datetime.now() - timedelta(minutes=window)
        recent = (
            request.env["odu.contact.message"]
            .sudo()
            .search_count(
                [("client_ip", "=", client_ip), ("create_date", ">=", since)]
            )
        )
        return recent >= max_recent

    @staticmethod
    def _int_param(params, key, default):
        """Read an integer system parameter, falling back to ``default``."""
        try:
            return int(params.get_param(key, default))
        except (TypeError, ValueError):
            return default

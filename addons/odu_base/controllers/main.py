# -*- coding: utf-8 -*-
import re

from odoo import http
from odoo.http import request

#: Permissive email shape check — real validation is whether delivery works.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

#: Upper bounds so a public, unauthenticated endpoint cannot store huge blobs.
_MAX_NAME = 200
_MAX_EMAIL = 254
_MAX_MESSAGE = 5000


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
        ``{"ok": false, "error": ...}`` with a 400 status on bad input. Records
        are created with ``sudo()`` because the public user holds no access on
        the model (only administrators do).
        """
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

        request.env["odu.contact.message"].sudo().create(
            {
                "name": name[:_MAX_NAME],
                "email": email[:_MAX_EMAIL],
                "message": message[:_MAX_MESSAGE],
            }
        )
        return request.make_json_response({"ok": True})

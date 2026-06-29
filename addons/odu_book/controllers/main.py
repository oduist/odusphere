# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class OduBookController(http.Controller):
    """Thin JSON wrapper over the ``odu.book`` model for the client action."""

    @http.route("/odu_book/book", type="jsonrpc", auth="user")
    def book(self):
        return request.env["odu.book"].get_book()

    @http.route("/odu_book/admin", type="jsonrpc", auth="user")
    def admin_book(self):
        # get_admin_book enforces the system-admin group itself.
        return request.env["odu.book"].get_admin_book()

    @http.route("/odu_book/changes", type="jsonrpc", auth="user")
    def changes(self):
        return request.env["odu.book"].get_changes()

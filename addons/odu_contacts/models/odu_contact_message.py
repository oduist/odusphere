# -*- coding: utf-8 -*-
from odoo import api, fields, models


class OduContactMessage(models.Model):
    """Enrich the core contact request with a triage workflow and collaboration.

    ``odu_base`` defines the bare model (name / email / message / handled) and the
    public ``POST /api/contact`` endpoint that fills it. This module layers on the
    operational side: a three-state status, an assigned owner, chatter and
    scheduled activities (``mail.thread`` + ``mail.activity.mixin``).
    """

    _name = "odu.contact.message"
    _inherit = ["odu.contact.message", "mail.thread", "mail.activity.mixin"]

    state = fields.Selection(
        [
            ("new", "New"),
            ("in_progress", "In Progress"),
            ("done", "Done"),
        ],
        string="Status",
        default="new",
        required=True,
        index=True,
        tracking=True,
    )
    user_id = fields.Many2one(
        "res.users",
        string="Assigned To",
        index=True,
        tracking=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._odu_sync_handled()
        return records

    def write(self, vals):
        res = super().write(vals)
        if "state" in vals:
            self._odu_sync_handled()
        return res

    def _odu_sync_handled(self):
        """Keep the core ``handled`` flag in step with the richer ``state``.

        ``handled`` is the boolean triage flag defined by ``odu_base``. The
        Contacts workspace supersedes it with the three-state ``state`` workflow
        but keeps it truthful — ``handled`` mirrors "the request is ``done``" — so
        anything still reading the core field stays consistent. The sync is
        one-directional (``state`` drives ``handled``) and only writes on a real
        change, so it never recurses.
        """
        for record in self:
            handled = record.state == "done"
            if record.handled != handled:
                record.handled = handled

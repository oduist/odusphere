# -*- coding: utf-8 -*-
from odoo import fields, models


class OduContactMessage(models.Model):
    """A message submitted through the public website contact form.

    Persisted by the public ``POST /api/contact`` controller (auth=public, via
    ``sudo()``) and reviewed by administrators in the Contact Requests inbox.
    """

    _name = "odu.contact.message"
    _description = "Contact Request"
    _order = "create_date desc"
    _rec_name = "name"

    name = fields.Char(required=True)
    email = fields.Char(required=True)
    message = fields.Text(required=True)
    handled = fields.Boolean(
        default=False,
        help="Set once an administrator has processed this request.",
    )

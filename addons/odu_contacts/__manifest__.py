{
    "name": "Contacts",
    "summary": "Contacts workspace: partner directory + website contact requests with a triage workflow",
    "description": """
Contacts
========

A top-level **Contacts** workspace for everyday internal users, with two sections:

* **Contacts** — the partner directory (``res.partner``), reusing the framework's
  own views (no bespoke partner screens — Zero Bloat).
* **Requests** — the website contact submissions (``odu.contact.message``),
  enriched into a small triage workflow: a ``new`` / ``in_progress`` / ``done``
  status, an assigned owner, scheduled activities and a full chatter
  (``mail.thread`` + ``mail.activity.mixin``).

This module supersedes the administrator-only Contact Requests inbox that ships in
``odu_base`` (its Settings menu is hidden on install).
""",
    "version": "19.0.1.0.0",
    "category": "Contacts",
    "author": "OduSphere",
    "license": "LGPL-3",
    "depends": ["odu_base", "mail"],
    "data": [
        "security/ir.model.access.csv",
        "data/odu_contacts_data.xml",
        "views/odu_contact_message_views.xml",
        "views/res_partner_views.xml",
        "views/odu_contacts_menus.xml",
    ],
    "application": True,
    "installable": True,
}

# -*- coding: utf-8 -*-
{
    "name": "S3 Attachment Storage",
    "summary": "Offload user ir.attachment binaries to one or more S3-compatible "
               "object stores and serve them via presigned URLs",
    "description": """
S3 Attachment Storage
=====================

Keeps Odoo's own web assets (CSS/JS, small images) served locally, and
transparently offloads everything a user attaches (PDFs, images, documents,
...) to an S3-compatible object store. Content can be spread across **several
different S3 backends** at once, chosen by routing rules; each stored object
remembers which backend it lives on, so reads always route back to the right
store. Files are handed to the browser through short-lived presigned URLs, so
the bytes flow straight from the object store instead of through Odoo.

This module is part of the OduSphere platform and depends on ``odu_base``.
""",
    "version": "19.0.1.0.0",
    "category": "Technical",
    "author": "OduSphere",
    "license": "LGPL-3",
    "depends": ["odu_base", "web"],
    "external_dependencies": {
        "python": ["boto3"],
    },
    "data": [
        "security/ir.model.access.csv",
        "data/ir_cron.xml",
        "views/odu_s3_backend_views.xml",
        "views/odu_s3_settings_views.xml",
        "views/odu_s3_menus.xml",
    ],
    "application": False,
    "installable": True,
}

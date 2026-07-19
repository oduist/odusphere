# -*- coding: utf-8 -*-
from odoo import fields, models


class OduS3Gc(models.Model):
    """Deferred-deletion queue for S3-backed attachment objects.

    Equivalent of the core filestore "checklist" spool, but stored in the
    database (there is no on-disk file to spool for a remote object). Rows are
    inserted in a *separate* cursor by ``ir.attachment._file_delete`` so the
    deletion intent survives a rollback of the current transaction, and are
    consumed by the ``ir.attachment._gc_odu_s3_store`` autovacuum, which only
    removes an object when no ``ir.attachment`` still references the same
    ``store_fname`` (deduplication guard).
    """

    _name = "odu.s3.gc"
    _description = "S3 Attachment GC Queue"

    store_fname = fields.Char(
        string="Stored Filename", required=True,
        help="The s3://<code>/<key> marker of an object queued for deletion.")

    _store_fname_uniq = models.Constraint(
        "UNIQUE (store_fname)",
        "A garbage-collection entry already exists for this stored filename.")

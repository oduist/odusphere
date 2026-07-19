# -*- coding: utf-8 -*-
import base64
import datetime as _dt
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.odu_s3_attachment.models import ir_attachment as ir_attachment_module

# a valid 1x1 transparent PNG (core image post-processing must be able to open it)
TINY_PNG = base64.b64decode(
    b'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==')

# Live S3 backend for the integration suite, taken from the environment.
_ENV = {
    "endpoint_url": os.environ.get("ODU_S3_TEST_ENDPOINT"),
    "bucket": os.environ.get("ODU_S3_TEST_BUCKET"),
    "access_key": os.environ.get("ODU_S3_TEST_ACCESS_KEY"),
    "secret_key": os.environ.get("ODU_S3_TEST_SECRET_KEY"),
    "region": os.environ.get("ODU_S3_TEST_REGION"),
}
_HAS_LIVE_S3 = bool(_ENV["bucket"] and _ENV["access_key"] and _ENV["secret_key"])


@tagged("post_install", "-at_install")
class TestS3Routing(TransactionCase):
    """Pure routing/marker tests; no live S3 backend required."""

    def setUp(self):
        super().setUp()
        self.Attachment = self.env["ir.attachment"]
        self.Backend = self.env["odu.s3.backend"]

    def test_keep_local_rules_predicate(self):
        A = self.Attachment
        # web assets -> always local
        self.assertFalse(A._s3_should_offload("text/css", 10 ** 6))
        self.assertFalse(A._s3_should_offload("application/javascript", 5))
        self.assertFalse(A._s3_should_offload("text/javascript", 5))
        # images: local only under the threshold (default 50 KB)
        self.assertFalse(A._s3_should_offload("image/png", 1000))
        self.assertTrue(A._s3_should_offload("image/png", 200000))
        # documents / unknown -> eligible for S3
        self.assertTrue(A._s3_should_offload("application/pdf", 4000))
        self.assertTrue(A._s3_should_offload("application/octet-stream", 1))

    def test_extra_keep_local_mimetypes(self):
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("odu_s3_attachment.keep_local_mimetypes", "application/pdf")
        self.assertFalse(self.Attachment._s3_should_offload("application/pdf", 4000))

    def test_backend_code_validation(self):
        from odoo.exceptions import ValidationError
        self.Backend.create({
            "name": "OK", "code": "primary-1", "bucket": "b",
            "access_key": "k", "secret_key": "s"})
        with self.assertRaises(ValidationError):
            self.Backend.create({
                "name": "Bad", "code": "Bad Code!", "bucket": "b",
                "access_key": "k", "secret_key": "s"})

    def test_backend_location_and_deletion_are_protected(self):
        backend = self.Backend.create({
            "name": "Protected", "code": "protected", "bucket": "old-bucket",
            "access_key": "k", "secret_key": "s"})
        attachment = self.Attachment.create({"name": "owned.pdf"})
        marker = backend._s3_marker("ab" + "1" * 38)
        self.env.cr.execute(
            "UPDATE ir_attachment SET store_fname = %s WHERE id = %s",
            (marker, attachment.id),
        )
        attachment.invalidate_recordset(["store_fname"])

        with self.assertRaises(UserError):
            backend.write({"bucket": "new-bucket"})
        with self.assertRaises(UserError):
            backend.unlink()

        # Connection and credential rotation remain supported.
        backend.write({"endpoint_url": "https://s3.example.test", "access_key": "new"})

    def test_archived_backend_is_visible_to_gc_gate(self):
        backend = self.Backend.create({
            "name": "Archived", "code": "archived", "bucket": "b",
            "access_key": "k", "secret_key": "s", "active": False})
        self.assertFalse(self.Backend._s3_has_backend())
        self.assertTrue(self.Backend._s3_has_backend(include_archived=True))
        self.assertFalse(backend.active)

    def test_backend_with_pending_gc_object_cannot_be_deleted(self):
        backend = self.Backend.create({
            "name": "Pending GC", "code": "pending-gc", "bucket": "b",
            "access_key": "k", "secret_key": "s"})
        self.env["odu.s3.gc"].create({
            "store_fname": backend._s3_marker("ab" + "3" * 38),
        })
        with self.assertRaises(UserError):
            backend.unlink()

    def test_upload_registers_rollback_gc_intent(self):
        backend = self.Backend.create({
            "name": "Rollback", "code": "rollback", "bucket": "b",
            "access_key": "k", "secret_key": "s"})
        checksum = "ab" + "2" * 38
        marker = backend._s3_marker(checksum)
        uploaded_marker = None
        queued = False
        try:
            with patch.object(type(backend), "_s3_client", return_value=object()), \
                    patch("odoo.addons.odu_s3_attachment.models.s3_client.upload_dedup"):
                uploaded_marker = backend._s3_upload(checksum, b"payload")
        finally:
            # TransactionCase uses a stable snapshot, so verify and clean the
            # separately committed row from another cursor.
            with self.env.registry.cursor() as cleanup_cr:
                cleanup_cr.execute(
                    "SELECT 1 FROM odu_s3_gc WHERE store_fname = %s", (marker,))
                queued = bool(cleanup_cr.fetchone())
                cleanup_cr.execute(
                    "DELETE FROM odu_s3_gc WHERE store_fname = %s", (marker,))
                cleanup_cr.commit()
        self.assertEqual(uploaded_marker, marker)
        self.assertTrue(queued)

    def test_marker_roundtrip_and_backend_resolution(self):
        backend = self.Backend.create({
            "name": "Docs", "code": "docs", "bucket": "b",
            "access_key": "k", "secret_key": "s"})
        checksum = "ab" + "0" * 38
        marker = backend._s3_marker(checksum)
        self.assertEqual(marker, "s3://docs/ab/" + checksum)
        self.assertTrue(self.Attachment._s3_is_s3(marker))
        resolved, key = self.Backend._s3_backend_for_marker(marker)
        self.assertEqual(resolved, backend)
        self.assertEqual(key, "ab/" + checksum)
        # unknown code resolves to empty
        empty, _key = self.Backend._s3_backend_for_marker("s3://nope/ab/" + checksum)
        self.assertFalse(empty)

    def test_pick_backend_routing_by_mime_and_priority(self):
        # A PDF-only backend (priority 1) and a catch-all (priority 20).
        pdf = self.Backend.create({
            "name": "PDFs", "code": "pdfs", "bucket": "b1", "access_key": "k",
            "secret_key": "s", "sequence": 1, "mimetype_prefixes": "application/pdf"})
        catchall = self.Backend.create({
            "name": "Everything", "code": "all", "bucket": "b2", "access_key": "k",
            "secret_key": "s", "sequence": 20})
        self.assertEqual(self.Backend._s3_pick_backend("application/pdf", 10), pdf)
        self.assertEqual(self.Backend._s3_pick_backend("image/jpeg", 10), catchall)
        # archived backends are ignored for new uploads
        catchall.active = False
        pdf.active = False
        self.assertFalse(self.Backend._s3_pick_backend("image/jpeg", 10))

    def test_pick_backend_none_when_no_catchall(self):
        # only a filtered backend exists -> non-matching content stays local
        self.Backend.create({
            "name": "Images", "code": "img", "bucket": "b", "access_key": "k",
            "secret_key": "s", "mimetype_prefixes": "image/"})
        self.assertFalse(self.Backend._s3_pick_backend("application/pdf", 10))

    def test_migrate_window(self):
        ICP = self.env["ir.config_parameter"].sudo()
        A = self.Attachment
        # start == end -> window disabled, runs any time
        ICP.set_param("odu_s3_attachment.migrate_window_start", "0")
        ICP.set_param("odu_s3_attachment.migrate_window_end", "0")
        self.assertTrue(A._s3_migrate_in_window())
        # daytime window 2..6 (UTC)
        ICP.set_param("odu_s3_attachment.migrate_window_start", "2")
        ICP.set_param("odu_s3_attachment.migrate_window_end", "6")
        ICP.set_param("odu_s3_attachment.migrate_window_tz", "UTC")
        with patch.object(fields.Datetime, "now", return_value=_dt.datetime(2026, 1, 1, 3)):
            self.assertTrue(A._s3_migrate_in_window())
        with patch.object(fields.Datetime, "now", return_value=_dt.datetime(2026, 1, 1, 12)):
            self.assertFalse(A._s3_migrate_in_window())
        # overnight window 22..6
        ICP.set_param("odu_s3_attachment.migrate_window_start", "22")
        ICP.set_param("odu_s3_attachment.migrate_window_end", "6")
        with patch.object(fields.Datetime, "now", return_value=_dt.datetime(2026, 1, 1, 23)):
            self.assertTrue(A._s3_migrate_in_window())
        with patch.object(fields.Datetime, "now", return_value=_dt.datetime(2026, 1, 1, 4)):
            self.assertTrue(A._s3_migrate_in_window())
        with patch.object(fields.Datetime, "now", return_value=_dt.datetime(2026, 1, 1, 12)):
            self.assertFalse(A._s3_migrate_in_window())

    def test_field_derived_image_size_requires_data_stream(self):
        with patch.object(
                ir_attachment_module, "request",
                SimpleNamespace(params={"field": "avatar_128"})):
            self.assertTrue(self.Attachment._s3_transform_requested())
        with patch.object(
                ir_attachment_module, "request",
                SimpleNamespace(params={"field": "raw"})):
            self.assertFalse(self.Attachment._s3_transform_requested())


@tagged("post_install", "-at_install")
@unittest.skipUnless(_HAS_LIVE_S3, "ODU_S3_TEST_* environment not configured")
class TestS3Integration(TransactionCase):
    """End-to-end tests against a live (S3-compatible) backend."""

    def setUp(self):
        super().setUp()
        self.Attachment = self.env["ir.attachment"]
        self.backend = self.env["odu.s3.backend"].create({
            "name": "Test", "code": "test",
            "endpoint_url": _ENV["endpoint_url"] or False,
            "bucket": _ENV["bucket"], "region": _ENV["region"] or False,
            "access_key": _ENV["access_key"], "secret_key": _ENV["secret_key"],
        })
        client = self.backend._s3_client()
        try:  # make the suite self-contained against a fresh bucket-less backend
            client.create_bucket(Bucket=_ENV["bucket"])
        except Exception:
            pass

    def _object_exists(self, store_fname):
        backend, key = self.env["odu.s3.backend"]._s3_backend_for_marker(store_fname)
        try:
            backend._s3_client().head_object(Bucket=backend.bucket, Key=key)
            return True
        except Exception:
            return False

    def test_document_roundtrip(self):
        content = b"%PDF-1.4 " + os.urandom(64)
        att = self.Attachment.create({
            "name": "doc.pdf", "mimetype": "application/pdf", "raw": content})
        self.assertTrue(att.store_fname.startswith("s3://test/"),
                        "document should be stored on the test backend")
        self.assertTrue(self._object_exists(att.store_fname))
        att.invalidate_recordset(["raw", "datas"])
        self.assertEqual(att.raw, content)

    def test_web_asset_stays_local(self):
        att = self.Attachment.create({
            "name": "style.css", "mimetype": "text/css", "raw": b"body{color:red}"})
        self.assertFalse(att.store_fname.startswith("s3://"))

    def test_small_image_stays_local(self):
        # image_no_postprocess skips core's PIL autoresize (which chokes on the
        # degenerate 1x1 test PNG); routing by mimetype/size is unaffected.
        att = self.Attachment.with_context(image_no_postprocess=True).create({
            "name": "tiny.png", "mimetype": "image/png", "raw": TINY_PNG})
        self.assertFalse(att.store_fname.startswith("s3://"))

    def test_dedup_same_content_one_object(self):
        content = b"dedup-" + os.urandom(32)
        a1 = self.Attachment.create({
            "name": "a.pdf", "mimetype": "application/pdf", "raw": content})
        a2 = self.Attachment.create({
            "name": "b.pdf", "mimetype": "application/pdf", "raw": content})
        self.assertEqual(a1.store_fname, a2.store_fname)

    def test_gc_keeps_referenced_object(self):
        content = b"gc-ref-" + os.urandom(32)
        att = self.Attachment.create({
            "name": "a.pdf", "mimetype": "application/pdf", "raw": content})
        store_fname = att.store_fname
        self.env["odu.s3.gc"].create({"store_fname": store_fname})
        self.Attachment._gc_odu_s3_collect()
        self.assertTrue(self._object_exists(store_fname))
        self.assertFalse(
            self.env["odu.s3.gc"].search([("store_fname", "=", store_fname)]))

    def test_gc_removes_orphan_object(self):
        key = "ab/" + "a" * 40
        store_fname = "s3://test/" + key
        self.backend._s3_client().put_object(
            Bucket=_ENV["bucket"], Key=key, Body=b"orphan-data")
        self.assertTrue(self._object_exists(store_fname))
        self.env["odu.s3.gc"].create({"store_fname": store_fname})
        self.Attachment._gc_odu_s3_collect()
        self.assertFalse(self._object_exists(store_fname))

    def test_migrate_storage_level(self):
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("odu_s3_attachment.keep_local_mimetypes", "application/pdf")
        content = b"%PDF-1.4 " + os.urandom(48)
        att = self.Attachment.create({
            "name": "reloc.pdf", "mimetype": "application/pdf", "raw": content})
        self.assertFalse(att.store_fname.startswith("s3://"))
        ICP.set_param("odu_s3_attachment.keep_local_mimetypes", "")
        moved = att._s3_offload()
        att.invalidate_recordset(["store_fname", "raw", "datas"])
        self.assertEqual(moved, 1)
        self.assertTrue(att.store_fname.startswith("s3://test/"))
        self.assertTrue(self._object_exists(att.store_fname))
        self.assertEqual(att.raw, content)

    def test_presigned_url(self):
        content = b"%PDF-1.4 " + os.urandom(32)
        att = self.Attachment.create({
            "name": "doc.pdf", "mimetype": "application/pdf", "raw": content})
        backend, key = self.env["odu.s3.backend"]._s3_backend_for_marker(att.store_fname)
        url = backend._s3_presigned_url(key, ttl=30)
        self.assertTrue(url and url.startswith("http"))

# -*- coding: utf-8 -*-
import json

from odoo.tests.common import HttpCase, TransactionCase


class TestContactMessageModel(TransactionCase):
    """The contact message model stores a public submission."""

    def test_create_contact_message(self):
        record = self.env["odu.contact.message"].create(
            {
                "name": "Ada Lovelace",
                "email": "ada@example.com",
                "message": "Hello from the website.",
            }
        )
        self.assertEqual(record.name, "Ada Lovelace")
        self.assertFalse(record.handled, "New requests start unhandled.")


class TestContactEndpoint(HttpCase):
    """Behaviour contract for the public POST /api/contact endpoint."""

    def _post(self, payload):
        return self.url_open(
            "/api/contact",
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )

    def test_valid_submission_creates_record(self):
        Message = self.env["odu.contact.message"]
        before = Message.search_count([])
        response = self._post(
            {
                "name": "Grace Hopper",
                "email": "grace@example.com",
                "message": "Nice starter site.",
            }
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json().get("ok"))
        self.assertEqual(Message.search_count([]), before + 1)

    def test_missing_fields_rejected(self):
        Message = self.env["odu.contact.message"]
        before = Message.search_count([])
        response = self._post({"name": "", "email": "", "message": ""})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json().get("ok"))
        self.assertEqual(Message.search_count([]), before)

    def test_invalid_email_rejected(self):
        response = self._post(
            {"name": "X", "email": "not-an-email", "message": "hi"}
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json().get("ok"))

    def test_honeypot_drops_silently(self):
        Message = self.env["odu.contact.message"]
        before = Message.search_count([])
        response = self._post(
            {
                "name": "Bot",
                "email": "bot@example.com",
                "message": "spam",
                "company": "EvilCorp",
            }
        )
        # The bot is told everything is fine, but nothing is stored.
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json().get("ok"))
        self.assertEqual(Message.search_count([]), before)

    def test_oversized_body_rejected(self):
        Message = self.env["odu.contact.message"]
        before = Message.search_count([])
        response = self._post(
            {"name": "A", "email": "a@example.com", "message": "x" * (70 * 1024)}
        )
        self.assertEqual(response.status_code, 413)
        self.assertEqual(Message.search_count([]), before)

    def test_client_ip_is_recorded(self):
        response = self._post(
            {"name": "IP", "email": "ip@example.com", "message": "hi"}
        )
        self.assertEqual(response.status_code, 200)
        record = self.env["odu.contact.message"].search(
            [("email", "=", "ip@example.com")], order="create_date desc", limit=1
        )
        self.assertTrue(record, "the submission should have been stored")
        self.assertTrue(record.client_ip, "the source IP should be recorded")

    def test_zz_rate_limit_throttles(self):
        # Named to sort last: its committed rows must not starve other tests'
        # per-IP quota (every HTTP submission here comes from the same client).
        payload = {"name": "Flood", "email": "flood@example.com", "message": "spam"}
        statuses = [self._post(payload).status_code for _ in range(15)]
        self.assertIn(429, statuses, "submissions should be throttled past the quota")
        self.assertLessEqual(
            statuses.count(200), 10, "no more than the default quota is accepted"
        )

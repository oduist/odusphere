# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase

from ..models.ir_module_module import ALLOWED_FRAMEWORK_MODULES, ALLOWED_PARAM


class TestInstallPolicy(TransactionCase):
    """Behaviour contract for the odu_ installation policy."""

    def setUp(self):
        super().setUp()
        self.Module = self.env["ir.module.module"]

    def test_predicate_odu_prefix_allowed(self):
        allowed = self.Module._odu_allowed_module_names()
        self.assertTrue(self.Module._odu_is_allowed("odu_warehouse", allowed))
        self.assertTrue(self.Module._odu_is_allowed("odu_crm", allowed))

    def test_predicate_framework_allowed(self):
        allowed = self.Module._odu_allowed_module_names()
        self.assertTrue(self.Module._odu_is_allowed("base", allowed))
        self.assertTrue(self.Module._odu_is_allowed("web", allowed))

    def test_predicate_business_app_forbidden(self):
        allowed = self.Module._odu_allowed_module_names()
        for name in ("sale", "purchase", "stock", "account", "crm", "hr", "product"):
            self.assertFalse(self.Module._odu_is_allowed(name, allowed), name)

    def test_config_parameter_extends_allowlist(self):
        self.env["ir.config_parameter"].sudo().set_param(
            ALLOWED_PARAM, "contacts, mail"
        )
        allowed = self.Module._odu_allowed_module_names()
        self.assertIn("contacts", allowed)
        self.assertIn("mail", allowed)
        # The hardcoded framework defaults are always present.
        self.assertTrue(ALLOWED_FRAMEWORK_MODULES <= allowed)

    def test_button_install_blocks_non_odu_module(self):
        forbidden = self.Module.search(
            [
                ("state", "=", "uninstalled"),
                ("name", "not like", "odu_%"),
                ("name", "not in", list(ALLOWED_FRAMEWORK_MODULES)),
            ],
            limit=1,
        )
        self.assertTrue(
            forbidden, "Expected at least one uninstalled non-odu module to test against"
        )
        with self.assertRaises(UserError):
            forbidden.button_install()

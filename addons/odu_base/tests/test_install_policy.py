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
        self.assertTrue(self.Module._odu_is_allowed("mail", allowed))

    def test_allowed_framework_module_pulls_in_its_dependencies(self):
        """Allowing a framework root implicitly allows its dependency closure."""
        allowed = self.Module._odu_allowed_module_names()
        self.assertIn("mail", allowed, "mail is a framework default")
        mail = self.Module.search([("name", "=", "mail")], limit=1)
        self.assertTrue(mail, "the 'mail' module must be on the addons path")
        for dep_name in mail.dependencies_id.mapped("name"):
            self.assertIn(
                dep_name,
                allowed,
                f"{dep_name} is a dependency of the allowed 'mail' and must be allowed too",
            )

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
        # Exclude the full allowed set (framework roots + their dependency
        # closure), so we never accidentally pick a now-allowed transitive
        # dependency such as ``bus`` or ``base_setup``.
        allowed = self.Module._odu_allowed_module_names()
        candidates = self.Module.search(
            [("state", "=", "uninstalled"), ("name", "not like", "odu_%")]
        )
        forbidden = candidates.filtered(lambda module: module.name not in allowed)[:1]
        self.assertTrue(
            forbidden,
            "Expected at least one uninstalled, non-allowed module to test against",
        )
        with self.assertRaises(UserError):
            forbidden.button_install()

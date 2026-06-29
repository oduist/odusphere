# -*- coding: utf-8 -*-
from odoo import _, models
from odoo.exceptions import UserError

#: Mandatory prefix for every OduSphere module (see ODUSPHERE.md, section 3).
ODU_PREFIX = "odu_"

#: Framework modules the Incubator is allowed to build upon even though they do
#: not carry the ``odu_`` prefix. Kept intentionally minimal: the base
#: identity/ORM layer (``base`` -> res.users / res.company / res.partner / ir.*)
#: and the web UI client (``web``). Extra names can be appended at runtime
#: through the ``odu_base.allowed_non_odu_modules`` system parameter.
ALLOWED_FRAMEWORK_MODULES = frozenset({"base", "web"})

#: System parameter holding extra comma-separated module names to allow on top
#: of :data:`ALLOWED_FRAMEWORK_MODULES`.
ALLOWED_PARAM = "odu_base.allowed_non_odu_modules"


class IrModuleModule(models.Model):
    _inherit = "ir.module.module"

    def button_install(self):
        """Enforce the OduSphere installation policy before installing anything.

        Installing a module also installs its not-yet-installed dependencies,
        so the whole upstream closure is validated here, not only the records
        the user explicitly clicked on. This is the single choke point the UI
        "Activate"/"Install" button funnels through (``button_immediate_install``
        delegates to it), so every interactive install is policed.
        """
        self._odu_assert_installable()
        return super().button_install()

    def _odu_allowed_module_names(self):
        """Return the full set of non-``odu_`` module names allowed to install.

        :return: union of :data:`ALLOWED_FRAMEWORK_MODULES` and the names listed
            in the ``odu_base.allowed_non_odu_modules`` system parameter
            (comma-separated, whitespace-trimmed).
        """
        param = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param(ALLOWED_PARAM, default="")
        )
        extra = {name.strip() for name in param.split(",") if name.strip()}
        return ALLOWED_FRAMEWORK_MODULES | extra

    def _odu_is_allowed(self, module_name, allowed_names):
        """Decide whether a single module name may be installed.

        :param module_name: the module's technical name.
        :param allowed_names: the set returned by
            :meth:`_odu_allowed_module_names`.
        :return: ``True`` for an ``odu_`` module or an explicitly allowed
            framework module, ``False`` otherwise.
        """
        return module_name.startswith(ODU_PREFIX) or module_name in allowed_names

    def _odu_assert_installable(self):
        """Raise ``UserError`` if this install would bring in a forbidden module.

        The candidate set is ``self`` plus every dependency that is not yet
        installed (``upstream_dependencies()``), i.e. everything the install
        action would actually add to the database. Records already in the
        ``installed`` state are ignored.
        """
        allowed_names = self._odu_allowed_module_names()
        candidates = self | self.upstream_dependencies()
        forbidden = candidates.filtered(
            lambda module: module.state != "installed"
            and not self._odu_is_allowed(module.name, allowed_names)
        )
        if forbidden:
            raise UserError(_("Only OduSphere modules can be installed."))

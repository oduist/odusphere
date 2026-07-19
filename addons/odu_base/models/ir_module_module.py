# -*- coding: utf-8 -*-
from odoo import _, models
from odoo.exceptions import UserError

#: Mandatory prefix for every OduSphere module (see ODUSPHERE.md, section 3).
ODU_PREFIX = "odu_"

#: Framework modules the Incubator is allowed to build upon even though they do
#: not carry the ``odu_`` prefix. Kept intentionally minimal: the base
#: identity/ORM layer (``base`` -> res.users / res.company / res.partner / ir.*),
#: the web UI client (``web``) and the messaging/activity framework (``mail`` ->
#: chatter, activities, mail templates). These are *framework* tiers, not business
#: applications. Allowing a module here also implicitly allows the modules it is
#: built on (its dependency closure) — see :meth:`_odu_allowed_module_names` — so
#: ``mail`` transparently permits ``bus`` / ``base_setup`` without listing each.
#: Extra names can be appended at runtime through the
#: ``odu_base.allowed_non_odu_modules`` system parameter.
ALLOWED_FRAMEWORK_MODULES = frozenset({"base", "web", "mail"})

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

        The set is built from the explicitly-allowed **framework roots**
        (:data:`ALLOWED_FRAMEWORK_MODULES` plus the names listed in the
        ``odu_base.allowed_non_odu_modules`` system parameter, comma-separated
        and whitespace-trimmed) and then widened with the **dependency closure**
        of those roots. Allowing a framework module therefore implicitly allows
        the modules it is built on (e.g. allowing ``mail`` also allows ``bus``
        and ``base_setup``), so the parameter/list never has to enumerate
        transitive framework dependencies by hand.

        Only the roots are expanded — the closure of an ``odu_`` module is *not*
        auto-allowed, so an ``odu_`` module cannot smuggle a business app in as a
        dependency; every such dependency is still checked on its own merits.

        :return: the allowed root names unioned with their full dependency closure.
        """
        param = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param(ALLOWED_PARAM, default="")
        )
        extra = {name.strip() for name in param.split(",") if name.strip()}
        roots = ALLOWED_FRAMEWORK_MODULES | extra
        return roots | self._odu_dependency_closure(roots)

    def _odu_dependency_closure(self, names):
        """Return the technical names of every dependency of ``names``, transitively.

        Walks the declared ``dependencies_id`` graph breadth-first over whatever
        module records exist on the addons path, independent of install state, so
        the result is stable whether or not the framework modules are installed
        yet.

        :param names: an iterable of module technical names (the roots).
        :return: the set of all upstream dependency names reachable from the
            roots (the roots themselves are **not** included).
        """
        Module = self.env["ir.module.module"].sudo()
        seen = set()
        frontier = set(names)
        while frontier:
            modules = Module.search([("name", "in", list(frontier))])
            frontier = set()
            for dep_name in modules.mapped("dependencies_id.name"):
                if dep_name not in seen:
                    seen.add(dep_name)
                    frontier.add(dep_name)
        return seen

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

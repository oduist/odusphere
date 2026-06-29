# odu_base — Module SPEC

## Identity & Manifest
- Technical name: `odu_base`
- Display name: `Base`
- Summary: OduSphere governance core: enforces the `odu_` module installation policy.
- Version: `19.0.1.0.0` (Odoo 19)
- Category: `Technical` · Author: `OduSphere` · License: `LGPL-3`
- Flags: `application = False`, `installable = True`, `auto_install` not set.
- `depends`: `["base"]` — must extend `ir.module.module`, which lives in `base`; no business apps.
- External Python libs: none.
- `data`: none.
- Assets: none.

## Models & Fields
- `ir.module.module` — `models.Model`, `_inherit = "ir.module.module"`. No new fields, no new
  stored state. The module only adds policy methods over the existing model.
- Module-level constants (`models/ir_module_module.py`):
  - `ODU_PREFIX = "odu_"` — the mandatory OduSphere module name prefix.
  - `ALLOWED_FRAMEWORK_MODULES = frozenset({"base", "web"})` — non-`odu_` modules the
    Incubator is allowed to build upon (base identity/ORM + web UI client).
  - `ALLOWED_PARAM = "odu_base.allowed_non_odu_modules"` — system-parameter key holding
    extra allowed module names.

## Constraints & Invariants
- No SQL constraints, no `@api.constrains`. The invariant is enforced imperatively at
  install time (see Business Rules), not as a stored-data constraint.

## Business Rules & State
- **Installation policy (the single rule):** a module may be installed **only if** its
  technical name starts with `odu_` **or** its name is in the allowed set. The allowed set
  is `ALLOWED_FRAMEWORK_MODULES` ∪ (names parsed from the `odu_base.allowed_non_odu_modules`
  system parameter, comma-separated, whitespace-trimmed). Everything else (standard Odoo
  business apps such as `sale`, `purchase`, `stock`, `account`, `crm`, `hr`, `product`, …)
  is refused.
- **Validation scope = the full install closure.** The candidate set checked is the
  records being installed **plus every not-yet-installed upstream dependency**
  (`upstream_dependencies()`). A forbidden module pulled in only as a dependency is enough
  to refuse the whole install. Records already in state `installed` are ignored.
- **Enforcement point.** The policy runs inside `button_install`, which the interactive
  "Activate"/"Install" Apps button reaches through `button_immediate_install`. Refusal
  happens **before** `super()`, so no partial install side effect occurs.
- **Out of scope (documented limitation).** Installation forced through the command line
  (`odoo -i <module>`) or low-level loader does **not** pass through `button_install` and is
  therefore not policed — this is an administrative/devops path used to install `odu_base`
  itself and is intentionally outside the in-system governance boundary. Module **upgrades**
  (`button_upgrade`) of already-installed modules are not affected.

## Methods & Actions
- `ir.module.module.button_install(self)` — override.
  - Purpose: enforce the policy, then delegate to the standard install.
  - Side effects: raises `UserError` and aborts when the policy is violated; otherwise
    identical to standard `button_install` (marks modules `to install`).
  - Trigger: Apps "Activate"/"Install" button → `button_immediate_install` →
    `button_install`; any server-side caller of `button_install`.
- `ir.module.module._odu_assert_installable(self)` — internal guard.
  - Computes `candidates = self | self.upstream_dependencies()`, filters to records whose
    `state != "installed"` and that are **not** allowed, and raises `UserError` listing the
    refused module names when that filtered set is non-empty. Returns `None` otherwise.
  - Error message names the prefix, the current allowed framework set, and the refused
    modules; built with `_()` for translation.
- `ir.module.module._odu_allowed_module_names(self) -> set[str]`.
  - Reads the `odu_base.allowed_non_odu_modules` system parameter via `sudo()`, splits on
    commas, trims, and returns the union with `ALLOWED_FRAMEWORK_MODULES`.
- `ir.module.module._odu_is_allowed(self, module_name, allowed_names) -> bool`.
  - Pure predicate: `module_name.startswith(ODU_PREFIX) or module_name in allowed_names`.

## Security
- No `ir.model.access.csv`, no new groups, no record rules — the module defines no new model.
- The system parameter is read with `sudo()`; writing it requires the standard
  `ir.config_parameter` access (Settings/admin), so only administrators can widen the
  allowlist.

## Views & UI
- None. No views, menus, actions, or assets. The module is pure backend governance; the
  only user-visible surface is the `UserError` dialog shown when an install is refused.

## API Endpoints
- None.

## Automation
- None — no crons, no server/automated actions.

## Seed / Demo Data
- None.

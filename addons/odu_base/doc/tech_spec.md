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
- `data`: `security/ir.model.access.csv`, `views/ir_module_views.xml`, `views/odu_contact_views.xml`.
- Assets: none.

## Models & Fields
- `ir.module.module` — `models.Model`, `_inherit = "ir.module.module"`. No new fields, no new
  stored state. The module only adds policy methods over the existing model.
- Module-level constants (`models/ir_module_module.py`):
  - `ODU_PREFIX = "odu_"` — the mandatory OduSphere module name prefix.
  - `ALLOWED_FRAMEWORK_MODULES = frozenset({"base", "web", "mail"})` — non-`odu_`
    framework modules the Incubator is allowed to build upon (base identity/ORM, the
    web UI client, and the `mail` messaging/activity framework — chatter, activities,
    mail templates). These are framework tiers, not business apps.
  - `ALLOWED_PARAM = "odu_base.allowed_non_odu_modules"` — system-parameter key holding
    extra allowed module names.
- `odu.contact.message` — `models.Model`, `_description = "Contact Request"`,
  `_order = "create_date desc"`, `_rec_name = "name"`. Stores a public website
  contact-form submission. Fields:
  - `name` (Char, `required=True`) — sender name.
  - `email` (Char, `required=True`) — sender email.
  - `message` (Text, `required=True`) — the message body.
  - `handled` (Boolean, `default=False`, `help` set) — administrator triage flag, set
    once the request has been processed.
  - The inherited `create_date` is the received timestamp (shown in the inbox and the
    `_order` key); no other stored state.

## Constraints & Invariants
- No SQL constraints, no `@api.constrains`. The invariant is enforced imperatively at
  install time (see Business Rules), not as a stored-data constraint.

## Business Rules & State
- **Installation policy (the single rule):** a module may be installed **only if** its
  technical name starts with `odu_` **or** its name is in the allowed set. The allowed set
  is the **framework roots** (`ALLOWED_FRAMEWORK_MODULES` ∪ names parsed from the
  `odu_base.allowed_non_odu_modules` system parameter, comma-separated, whitespace-trimmed)
  **plus the full dependency closure of those roots**. Expanding by the closure means
  allowing a framework module implicitly allows the modules it is built on (allowing
  `mail` also allows `bus`, `base_setup`, …), so the list never enumerates transitive
  framework dependencies by hand. **Only the roots are expanded** — an `odu_` module's own
  dependencies are *not* auto-allowed, so an `odu_` module cannot smuggle in a business app
  as a dependency. Everything else (standard Odoo business apps such as `sale`, `purchase`,
  `stock`, `account`, `crm`, `hr`, `product`, …) is refused.
- **Validation scope = the full install closure.** The candidate set checked is the
  records being installed **plus every not-yet-installed upstream dependency**
  (`upstream_dependencies()`). A forbidden module pulled in only as a dependency is enough
  to refuse the whole install. Records already in state `installed` are ignored.
- **Enforcement point.** The policy runs inside `button_install`, which the interactive
  "Activate"/"Install" Apps button reaches through `button_immediate_install`. Refusal
  happens **before** `super()`, so no partial install side effect occurs.
- **Refusal message.** A single short, translatable line: `Only OduSphere modules can be
  installed.` (no module listing, no rationale). Odoo renders it under its own
  "Invalid Operation" dialog title.
- **Apps listing scope.** The core Apps action (`base.open_module_tree`) carries a pinned
  domain `[('name', '=like', 'odu_%')]`, so the Apps screen only ever lists `odu_`
  modules regardless of search-bar state. The domain is enforced at the action level and
  cannot be cleared by the user.
- **Apps menu trimming.** The `Third-Party Apps` menu entry (`base.menu_third_party`) is
  deactivated (`active = False`) — OduSphere does not consume store/third-party apps.
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
    `state != "installed"` and that are **not** allowed, and raises
    `UserError(_("Only OduSphere modules can be installed."))` when that filtered set is
    non-empty. Returns `None` otherwise.
- `ir.module.module._odu_allowed_module_names(self) -> set[str]`.
  - Builds the framework roots: `ALLOWED_FRAMEWORK_MODULES` ∪ the names parsed from the
    `odu_base.allowed_non_odu_modules` system parameter (read via `sudo()`, split on
    commas, trimmed). Returns the roots unioned with their dependency closure
    (`_odu_dependency_closure(roots)`).
- `ir.module.module._odu_dependency_closure(self, names) -> set[str]`.
  - Breadth-first walk of the declared `dependencies_id` graph over the module records on
    the addons path, independent of install state. Returns every dependency name reachable
    from `names` (the roots themselves excluded). This is what makes allowing `mail` also
    allow `bus` / `base_setup`.
- `ir.module.module._odu_is_allowed(self, module_name, allowed_names) -> bool`.
  - Pure predicate: `module_name.startswith(ODU_PREFIX) or module_name in allowed_names`.

## Security
- `security/ir.model.access.csv` — one rule: `odu.contact.message` is granted full CRUD
  (read/write/create/unlink) to `base.group_system` **only**. No other group has any
  access — the public contact endpoint writes via `sudo()`, and the inbox is
  administrator-only.
- No new groups, no record rules.
- The system parameter is read with `sudo()`; writing it requires the standard
  `ir.config_parameter` access (Settings/admin), so only administrators can widen the
  allowlist.

## Views & UI
- No new views, no new menus, no new actions, no assets. The module only reshapes the
  existing Apps UI via two data records in `views/ir_module_views.xml`:
  - `base.open_module_tree` (act_window) — `domain` overridden to
    `[('name', '=like', 'odu_%')]`, restricting the Apps listing to OduSphere modules.
  - `base.menu_third_party` (ir.ui.menu) — `active` set to `False`, hiding the
    "Third-Party Apps" menu entry.
- The contact inbox (`views/odu_contact_views.xml`) adds, for `odu.contact.message`:
  - list view `view_odu_contact_message_list` — columns Received (`create_date`), `name`,
    `email`, `handled` (`boolean_toggle`); `decoration-muted` on handled rows.
  - form view `view_odu_contact_message_form` — `name`, `email` (`email` widget), Received,
    `handled`, and the `message` body.
  - search view `view_odu_contact_message_search` — search on name/email/message + an
    `Unhandled` filter (`[('handled', '=', False)]`).
  - action `action_odu_contact_message` ("Contact Requests", `view_mode=list,form`, context
    `{'search_default_unhandled': 1}`).
  - menu `menu_odu_contact_messages` ("Contact Requests") under `base.menu_administration`
    (Settings), `groups="base.group_system"` — administrator-only.
- The other user-visible surface is the `UserError` dialog shown when an install is refused.

## API Endpoints
- `POST /api/contact` — `type=http`, `auth=public`, `methods=["POST"]`, `csrf=False`.
  - Purpose: backs the starter website's contact form (ODUSPHERE.md §5 convention — public
    REST endpoints of `odu_*` modules live under `/api/*`). Triggered by the website
    `fetch`.
  - Request: JSON body `{"name", "email", "message"}` plus an optional `company` honeypot.
  - Behavior: parse JSON (400 `"Invalid request."` on failure / non-object); if `company`
    is non-empty (honeypot) return `{"ok": true}` and store **nothing**; trim fields;
    require non-empty `name`/`email`/`message` (400 `"Name, email and message are
    required."`); validate email shape (400 `"Please provide a valid email address."`);
    cap lengths (name 200, email 254, message 5000); then create one `odu.contact.message`
    via `sudo()` (the public user holds no access).
  - Response: `{"ok": true}` (HTTP 200) on success; `{"ok": false, "error": <reason>}`
    (HTTP 400) on bad input.

## Automation
- None — no crons, no server/automated actions.

## Seed / Demo Data
- None.

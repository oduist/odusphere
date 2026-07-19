# odu_base — Module SPEC

## Identity & Manifest
- Technical name: `odu_base`
- Display name: `Base`
- Summary: OduSphere governance core: enforces the `odu_` module installation policy.
- Version: `19.0.1.1.0` (Odoo 19)
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
  - `client_ip` (Char, `readonly=True`, `index=True`, `help` set) — source IP captured
    at submission time (from `request.httprequest.remote_addr`), used for the per-IP
    rate limit. Indexed because the rate-limit check filters on it.
  - `handled` (Boolean, `default=False`, `help` set) — administrator triage flag, set
    once the request has been processed.
  - The inherited `create_date` is the received timestamp (shown in the inbox, the
    `_order` key, and the rate-limit window filter); no other stored state.

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
- **Enforcement point.** The policy runs inside `button_install`, **and** inside
  `button_immediate_install` (the method the interactive "Activate"/"Install" Apps button
  invokes and which normally delegates to `button_install`). Asserting in both makes the
  guard independent of that delegation — the check is a pure read, so the double call is
  idempotent. Refusal happens **before** `super()`, so no partial install side effect
  occurs.
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
  (`odoo -i <module>`) or a low-level loader / direct `write({'state': 'to install'})` does
  **not** pass through `button_install` / `button_immediate_install` and is therefore not
  policed — these are administrative/devops paths (used to install `odu_base` itself) and
  are intentionally outside the in-system governance boundary. The policy is a UI/RPC-button
  guard, **not** a hard security boundary against a server administrator. Module **upgrades**
  (`button_upgrade`) of already-installed modules are not affected.

## Public Contact Endpoint — Abuse Controls
- The public `POST /api/contact` endpoint (see API Endpoints) is anonymous, so it applies,
  in order, three abuse controls before storing anything:
  1. **Body-size cap.** If `Content-Length` exceeds `_MAX_BODY_BYTES` (64 KB) the request is
     rejected with **HTTP 413** *before* the JSON is parsed, so a caller cannot force the
     server to buffer a huge body. (The gateway caps `/api/*` bodies too; this is the
     guaranteed application-layer backstop.)
  2. **Honeypot.** A non-empty `company` field ⇒ `{"ok": true}` (HTTP 200) and **nothing
     stored**.
  3. **Per-IP rate limit.** After field/email validation, if the same `client_ip` already has
     `≥ max` stored messages whose `create_date` is within the last `window` minutes, the
     request is rejected with **HTTP 429** and nothing is stored. `max` and `window` come
     from system parameters (`odu_base.contact_rate_limit_max`, default 10;
     `odu_base.contact_rate_limit_window_minutes`, default 10); a `max ≤ 0` or `window ≤ 0`
     **disables** the limit. Accurate per-client keying requires Odoo `proxy_mode` (so
     `remote_addr` is the visitor, not the gateway); otherwise the limit is effectively
     global. Length caps (`name` 200, `email`/`client_ip` 254/64, `message` 5000) still apply.

## Methods & Actions
- `ir.module.module.button_install(self)` — override.
  - Purpose: enforce the policy, then delegate to the standard install.
  - Side effects: raises `UserError` and aborts when the policy is violated; otherwise
    identical to standard `button_install` (marks modules `to install`).
  - Trigger: any server-side caller of `button_install`.
- `ir.module.module.button_immediate_install(self)` — override.
  - Purpose: same guard on the immediate-install path, independent of whether it delegates
    to `button_install`. Calls `_odu_assert_installable()` then `super()`.
  - Trigger: Apps "Activate"/"Install" button.
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
- `OduContactController._contact_rate_limited(self, client_ip) -> bool` (controller helper).
  - Returns `True` when `client_ip` has `≥ max` messages within the last `window` minutes.
    Reads `max`/`window` from the two rate-limit system parameters (defaults 10/10) via
    `sudo()`; returns `False` for an empty IP or when the limit is disabled (`≤ 0`).
- `OduContactController._int_param(params, key, default) -> int` (static helper).
  - Reads an integer system parameter, falling back to `default` on missing/invalid values.

## Security
- `security/ir.model.access.csv` — one rule: `odu.contact.message` is granted full CRUD
  (read/write/create/unlink) to `base.group_system` **only**. No other group has any
  access — the public contact endpoint writes via `sudo()`, and the inbox is
  administrator-only.
- No new groups, no record rules. `client_ip` is stored on the admin-only model, so the
  captured source IP is never exposed to non-administrators.
- The system parameters (allowlist and rate-limit) are read with `sudo()`; writing them
  requires the standard `ir.config_parameter` access (Settings/admin), so only
  administrators can widen the allowlist or retune/disable the rate limit.

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
    `client_ip`, `handled`, and the `message` body.
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
  - Behavior (in order): reject if `Content-Length` > 64 KB (413 `"Request too large."`,
    before parsing); parse JSON (400 `"Invalid request."` on failure / non-object); if
    `company` is non-empty (honeypot) return `{"ok": true}` and store **nothing**; trim
    fields; require non-empty `name`/`email`/`message` (400 `"Name, email and message are
    required."`); validate email shape (400 `"Please provide a valid email address."`);
    apply the per-IP rate limit (429 `"Too many requests. …"` — see *Public Contact
    Endpoint — Abuse Controls*); cap lengths (name 200, email 254, message 5000, client_ip
    64); then create one `odu.contact.message` via `sudo()` (the public user holds no
    access), recording `client_ip = remote_addr`.
  - Response: `{"ok": true}` (HTTP 200) on success; `{"ok": false, "error": <reason>}` on
    bad input (400), oversized body (413), or throttling (429).
  - Module-level constants (`controllers/main.py`): `_MAX_NAME`/`_MAX_EMAIL`/`_MAX_MESSAGE`/
    `_MAX_IP` (length caps), `_MAX_BODY_BYTES` (64 KB), `_RATE_MAX_PARAM`/`_RATE_WINDOW_PARAM`
    (system-parameter keys) with `_RATE_MAX_DEFAULT`/`_RATE_WINDOW_DEFAULT` (both 10).

## Automation
- None — no crons, no server/automated actions.

## Seed / Demo Data
- None.

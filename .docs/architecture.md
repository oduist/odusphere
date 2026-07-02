# OduSphere — Global System Map (core)

> Machine-readable index of the OduSphere backend. **Signatures and relations only — no code, no logic bodies.** Read this file first at the start of every session. Full per-module detail lives in each module's `doc/tech_spec.md`.
>
> **Upstream-owned — do NOT edit in a sphere.** This file documents only the core
> template modules and is maintained by the `oduist/odusphere` upstream; editing it
> downstream causes merge conflicts on every update. **Document this sphere's own
> `odu_*` modules in [`sphere/docs/architecture.local.md`](../sphere/docs/architecture.local.md)**
> and read both files at session start.

## Modules
| Module | Purpose | Depends | SPEC |
|---|---|---|---|
| `odu_base` | Governance core: enforces the `odu_`-only module installation policy. | `base` | `addons/odu_base/doc/tech_spec.md` |
| `odu_book` | Built-in user documentation assembled from every installed `odu_*` module's `doc/user_guide.md`. | `odu_base`, `web` | `addons/odu_book/doc/tech_spec.md` |

## Models
- `ir.module.module` (`odu_base`) — `_inherit`; no new fields. Adds the install-policy guard.
  - `button_install(self)` — override; runs `_odu_assert_installable()` then `super()`.
  - `_odu_assert_installable(self) -> None` — raises `UserError("Only OduSphere modules can be installed.")` if `self | upstream_dependencies()` contains a non-installed, non-allowed module.
  - `_odu_allowed_module_names(self) -> set[str]` — `ALLOWED_FRAMEWORK_MODULES` ∪ `odu_base.allowed_non_odu_modules` param.
  - `_odu_is_allowed(self, module_name, allowed_names) -> bool` — `odu_`-prefixed or in allowed set.
  - Constants: `ODU_PREFIX="odu_"`, `ALLOWED_FRAMEWORK_MODULES={"base","web"}`, `ALLOWED_PARAM="odu_base.allowed_non_odu_modules"`.
- `odu.contact.message` (`odu_base`) — `Model`; public contact-form submissions. Fields: `name` (Char, req), `email` (Char, req), `message` (Text, req), `handled` (Boolean, default `False`). `_order="create_date desc"`, `_rec_name="name"`.
- `odu.book` (`odu_book`) — `AbstractModel`, no table. Userbook + Adminbook + change-timeline collector. Human guides served per reader language (`doc/i18n/<lang>/`, source fallback); language policy in root `LANG.md`, selections in `sphere/LANG.local.md`.
  - `get_book(self) -> {"pages": [{id, module, title, html}, ...]}` — `@api.model`; aggregates installed `odu_*` `doc/user_guide.md` (Userbook).
  - `get_admin_book(self) -> {"pages": [...]}` — `@api.model`; aggregates `doc/admin_guide.md` (Adminbook). Raises `AccessError` unless caller `has_group("base.group_system")`.
  - `_doc_lang(self) -> str` — short doc-language code from `context['lang']`/`user.lang` (`en_US`→`en`, default `en`).
  - `_collect_pages(self, filename, lang) -> [{id, module, title, html}, ...]` — shared collector behind `get_book`/`get_admin_book`.
  - `_read_module_doc(self, module_name, filename, lang) -> html | None` — renders a module's guide: prefers `doc/i18n/<lang>/<filename>`, falls back to `doc/<filename>`; strips leading i18n provenance marker.
  - `get_changes(self) -> {"days": [{date, entries: [{module, title, html}, ...]}, ...]}` — `@api.model`; aggregates installed `odu_*` modules' `doc/changes/YYYY-MM-DD.md`, grouped by day (descending).
  - `_read_module_changes(self, module_name) -> [(date_str, html), ...]` — reads one module's `doc/changes/*.md` (file names matching `YYYY-MM-DD.md`).

## Helpers (non-ORM)
- `odu_book/models/markdown.py` → `md_to_html(text) -> html` — dependency-free Markdown→HTML renderer; escapes all input; `diff` fenced blocks colour `+`/`-` lines (`.o_diff_add`/`.o_diff_del`).

## HTTP Endpoints
- `POST /api/contact` (`odu_base`) — `http`, `auth=public`, `csrf=False` → parses + honeypot-filters + validates JSON `{name,email,message}`, creates `odu.contact.message` via `sudo()`. Returns `{"ok": bool, "error"?}` (200 ok / 400 bad input).
- `POST /odu_book/book` — `jsonrpc`, `auth=user` → `odu.book.get_book()`.
- `POST /odu_book/admin` — `jsonrpc`, `auth=user` → `odu.book.get_admin_book()` (admin-only; raises `AccessError` for non-`base.group_system`).
- `POST /odu_book/changes` — `jsonrpc`, `auth=user` → `odu.book.get_changes()`.

## Client Actions & Menus
- `action_odu_contact_message` (`odu_base`; `ir.actions.act_window`, `odu.contact.message`, `list,form`, default filter Unhandled) ↔ menu `menu_odu_contact_messages` "Contact Requests" under `base.menu_administration` (Settings), `groups="base.group_system"` — admin-only contact inbox.
- `action_odu_book` (`ir.actions.client`, tag `odu_book.book`) ↔ OWL `BookApp` (template `odu_book.BookApp`, static `endpoint`).
- `action_odu_book_admin` (`ir.actions.client`, tag `odu_book.admin`) ↔ OWL `AdminBookApp` (subclass of `BookApp`, `endpoint=/odu_book/admin`).
- `action_odu_book_changes` (`ir.actions.client`, tag `odu_book.changes`) ↔ OWL `ChangesApp` (template `odu_book.ChangesApp`).
- Menu `menu_odu_book_root` — "Book", root-level container, sequence 5 (no action).
  - `menu_odu_book_doc` — "User Guide", sequence 5 → `action_odu_book`.
  - `menu_odu_book_admin` — "Admin Guide", sequence 7 → `action_odu_book_admin`, `groups="base.group_system"`.
  - `menu_odu_book_changes` — "Changes", sequence 10 → `action_odu_book_changes`.

## Cross-Module Relations
- Every `odu_*` module declares `odu_base` in its manifest `depends` (mandatory governance base; ODUSPHERE.md §3). `odu_book` → `depends(odu_base, web)`.
- `odu_book` consumes other `odu_*` modules' `doc/user_guide.md`, `doc/admin_guide.md`, `doc/changes/*.md` and translated mirrors `doc/i18n/<lang>/*.md` at the filesystem level, not via ORM relations.
- Documentation language policy: root `LANG.md` (rules) + `sphere/LANG.local.md` (sphere selections: source `en`, no targets yet); translations managed by the `odu-doc-i18n` skill, not consumed by `odu_book` at runtime.

## UI Overrides
- `odu_base` reshapes the existing Apps UI (data records, no new views): pins `base.open_module_tree` domain to `[('name','=like','odu_%')]` (Apps lists only `odu_` modules) and deactivates the `base.menu_third_party` ("Third-Party Apps") menu.

## Security Surface
- `odu_base`: install policy enforced in `button_install` (UI path only — CLI `-i` is out of scope by design); allowlist widened only via the `odu_base.allowed_non_odu_modules` system parameter (admin-only). Adds model `odu.contact.message` with a single ACL: full CRUD to `base.group_system` only — the public `/api/contact` endpoint writes via `sudo()`, and the inbox menu is admin-only.
- `odu_book`: no model ACL/groups (AbstractModel); Userbook & Changes endpoints/menus open to all internal users; reads `ir.module.module` via `sudo()`. **Adminbook** (`get_admin_book` / `/odu_book/admin` / `menu_odu_book_admin`) is restricted to `base.group_system` — enforced server-side (`AccessError`) and in the menu (`groups`).

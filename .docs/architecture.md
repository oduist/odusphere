# OduSphere — Global System Map

> Machine-readable index of the entire OduSphere backend. **Signatures and relations only — no code, no logic bodies.** Read this file first at the start of every session. Full per-module detail lives in each module's `doc/tech_spec.md`.

## Modules
| Module | Purpose | Depends | SPEC |
|---|---|---|---|
| `odu_base` | Governance core: enforces the `odu_`-only module installation policy. | `base` | `addons/odu_base/doc/tech_spec.md` |
| `odu_book` | Built-in user documentation assembled from every installed `odu_*` module's `doc/user_guide.md`. | `web` | `addons/odu_book/doc/tech_spec.md` |

## Models
- `ir.module.module` (`odu_base`) — `_inherit`; no new fields. Adds the install-policy guard.
  - `button_install(self)` — override; runs `_odu_assert_installable()` then `super()`.
  - `_odu_assert_installable(self) -> None` — raises `UserError("Only OduSphere modules can be installed.")` if `self | upstream_dependencies()` contains a non-installed, non-allowed module.
  - `_odu_allowed_module_names(self) -> set[str]` — `ALLOWED_FRAMEWORK_MODULES` ∪ `odu_base.allowed_non_odu_modules` param.
  - `_odu_is_allowed(self, module_name, allowed_names) -> bool` — `odu_`-prefixed or in allowed set.
  - Constants: `ODU_PREFIX="odu_"`, `ALLOWED_FRAMEWORK_MODULES={"base","web"}`, `ALLOWED_PARAM="odu_base.allowed_non_odu_modules"`.
- `odu.book` (`odu_book`) — `AbstractModel`, no table. User-documentation collector.
  - `get_book(self) -> {"pages": [{id, module, title, html}, ...]}` — `@api.model`; aggregates installed `odu_*` guides.
  - `_read_module_guide(self, module_name) -> html | None` — renders a single module's `doc/user_guide.md`.

## Helpers (non-ORM)
- `odu_book/models/markdown.py` → `md_to_html(text) -> html` — dependency-free Markdown→HTML renderer; escapes all input.

## HTTP Endpoints
- `POST /odu_book/book` — `jsonrpc`, `auth=user` → `odu.book.get_book()`.

## Client Actions & Menus
- `action_odu_book` (`ir.actions.client`, tag `odu_book.book`) ↔ OWL `BookApp` (template `odu_book.BookApp`).
- Menu `menu_odu_book_root` — "Book", root-level, sequence 5.

## Cross-Module Relations
- None yet. `odu_book` consumes other `odu_*` modules' `doc/user_guide.md` at the filesystem level, not via ORM relations.

## UI Overrides
- `odu_base` reshapes the existing Apps UI (data records, no new views): pins `base.open_module_tree` domain to `[('name','=like','odu_%')]` (Apps lists only `odu_` modules) and deactivates the `base.menu_third_party` ("Third-Party Apps") menu.

## Security Surface
- `odu_base`: no new model/ACL/groups; install policy enforced in `button_install` (UI path only — CLI `-i` is out of scope by design). Allowlist widened only via the `odu_base.allowed_non_odu_modules` system parameter (admin-only).
- `odu_book`: no model ACL/groups (AbstractModel); endpoint and menu open to all internal users; reads `ir.module.module` via `sudo()`.

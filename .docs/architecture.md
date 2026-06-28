# OduSphere — Global System Map

> Machine-readable index of the entire OduSphere backend. **Signatures and relations only — no code, no logic bodies.** Read this file first at the start of every session. Full per-module detail lives in each module's `doc/tech_spec.md`.

## Modules
| Module | Purpose | Depends | SPEC |
|---|---|---|---|
| `odu_book` | Built-in user documentation assembled from every installed `odu_*` module's `doc/user_guide.md`. | `web` | `addons/odu_book/doc/tech_spec.md` |

## Models
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

## Security Surface
- `odu_book`: no model ACL/groups (AbstractModel); endpoint and menu open to all internal users; reads `ir.module.module` via `sudo()`.

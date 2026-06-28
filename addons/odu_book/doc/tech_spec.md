# odu_book — Module SPEC

## Identity & Manifest
- Technical name: `odu_book`
- Display name: `Book`
- Summary: Interactive user documentation assembled from the `odu_*` modules.
- Version: `19.0.1.1.0` (Odoo 19)
- Category: `Tools` · Author: `OduSphere` · License: `LGPL-3`
- Flags: `application = True`, `installable = True`
- `depends`: `["web"]` — framework only; no business apps (complies with the Incubator constraint).
- External Python libs: none. The single import, `markupsafe`, ships with Odoo.
- `data`: `views/odu_book_views.xml`.
- Assets (`web.assets_backend`): `static/src/book/book.scss`, `static/src/book/book.js`, `static/src/book/book.xml`.

## Models & Fields
- `odu.book` — `models.AbstractModel`, `_description = "User Book"`.
  - No table, no fields, no persisted state. A service that reads other modules' guides from disk on demand.
- Module-level constants (`models/odu_book.py`):
  - `DOC_DIRNAME = "doc"` — folder inside each module holding the docs.
  - `GUIDE_FILENAME = "user_guide.md"` — the user-guide file name.
  - `MODULE_PREFIX = "odu_"` — only modules with this prefix are collected.

## Constraints & Invariants
- None — no SQL constraints and no `@api.constrains`; the model stores no data.

## Business Rules & State
- The Book aggregates **one page per installed `odu_*` module** that ships a readable `doc/user_guide.md`.
- Source selection: `ir.module.module` where `state = "installed"` AND `name =like "odu_%"`, ordered by `name` ascending, read with `sudo()`.
- Page skipping: a module whose guide is missing, unreadable, or non-UTF-8 is **silently skipped** (logged as a warning), never raised as an error.
- Page title rule: `module.shortdesc or module.name`.
- Only `user_guide.md` is exposed. The agent-facing `doc/tech_spec.md` is **deliberately never** read or shown to users.
- HTML is rendered from Markdown at request time — no caching, no stored HTML.

## Methods & Actions
- `odu.book.get_book(self)` — `@api.model`.
  - Purpose: assemble the whole book. Input: none.
  - Returns: `{"pages": [{"id": <module name>, "module": <module name>, "title": <shortdesc|name>, "html": <rendered HTML>}, ...]}`.
  - Side effects: none (read-only; reads files from disk).
  - Trigger: the `/odu_book/book` controller (and any server-side caller).
- `odu.book._read_module_guide(self, module_name)` — private.
  - Resolves the module path and returns the rendered HTML of its `doc/user_guide.md`, or `None` when the module path / file is absent or the file cannot be read/decoded.
- `markdown.md_to_html(text)` — pure function (`models/markdown.py`), no Odoo dependency.
  - Purpose: dependency-free Markdown → HTML renderer, written from scratch so the Book needs no extra packages.
  - Supported syntax (behavior contract): ATX headings `#`..`######` (each gets an `id` slug via `_slug`), paragraphs, unordered/ordered lists incl. nesting and lazy continuation, fenced code blocks (``` ``` ``` or `~~~`, optional language → `class="language-<lang>"`), recursive blockquotes, GFM pipe tables (header + separator row), horizontal rules, and inline: bold `**`, italic `*`, inline code `` ` ``, links `[t](url)` → `<a target="_blank" rel="noreferrer noopener">`, images `![alt](src)`.
  - Security/escaping: **all** text is HTML-escaped (`markupsafe.escape`); inline code is stashed before escaping so its content is never reformatted; `_` is intentionally left untouched so identifiers like `res_partner`/`odu_book` are not rendered as emphasis. Empty input → `""`.
  - Private helpers (no external contract, omitted by design): `_consume_fence/_consume_quote/_consume_table/_consume_list`, `_render_list`, `_split_row`, `_inline`, `_slug`.

## Security
- No `ir.model.access.csv`, no security groups, no record rules — `odu.book` is an AbstractModel with no table and needs no model ACL.
- Controller `/odu_book/book` is `auth="user"` → any authenticated internal user.
- The client action and root menu carry **no group restriction** → visible to all internal users.
- `get_book` reads `ir.module.module` via `sudo()`; the user is not granted direct registry access.

## Views & UI
- `ir.actions.client` `action_odu_book`: name `Book`, `tag = "odu_book.book"`.
- `menuitem` `menu_odu_book_root`: name `Book`, root-level (no parent), `sequence = 5`, action `action_odu_book`, no groups.
- OWL client action `BookApp` (template `odu_book.BookApp`, registered in the `actions` registry under tag `odu_book.book`):
  - Two-pane viewer: left = search box + table of contents (one entry per page); right = rendered guide.
  - State: `pages`, `activeId`, `search`, `loaded`.
  - Behavior: on start fetches `/odu_book/book` and auto-selects the first page; the TOC filters by case-insensitive substring match on `title`; the active page is highlighted; guide HTML is injected via `markup()` + `t-out`.
  - UI states: loading ("Loading…"), empty ("No documentation found."), no-selection placeholder ("Select a section…").
- Styling: `static/src/book/book.scss` (`.o_odu_book*`) — fixed 280px sidebar, active-link highlight, and typography for headings/code/tables/blockquotes/images inside `.o_odu_book_doc`.

## API Endpoints
- `POST /odu_book/book` — `type="jsonrpc"`, `auth="user"`.
  - Request: no parameters.
  - Response: the `get_book()` payload `{"pages": [{id, module, title, html}, ...]}`.
  - Controller: `OduBookController.book` → `request.env["odu.book"].get_book()`.

## Automation
- None — no crons, no server/automated actions.

## Seed / Demo Data
- None.

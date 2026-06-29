# odu_book — Module SPEC

## Identity & Manifest
- Technical name: `odu_book`
- Display name: `Book`
- Summary: Interactive user documentation assembled from the `odu_*` modules.
- Version: `19.0.1.2.0` (Odoo 19)
- Category: `Tools` · Author: `OduSphere` · License: `LGPL-3`
- Flags: `application = True`, `installable = True`
- `depends`: `["odu_base", "web"]` — the mandatory OduSphere governance core (`odu_base`) plus the web framework; no business apps (complies with the Incubator constraint).
- External Python libs: none. The single import, `markupsafe`, ships with Odoo.
- `data`: `views/odu_book_views.xml`.
- Assets (`web.assets_backend`): `static/src/book/book.scss`, `static/src/book/book.js`, `static/src/book/book.xml`, `static/src/changes/changes.js`, `static/src/changes/changes.xml`.

## Models & Fields
- `odu.book` — `models.AbstractModel`, `_description = "User Book"`.
  - No table, no fields, no persisted state. A service that reads other modules' guides from disk on demand.
- Module-level constants (`models/odu_book.py`):
  - `DOC_DIRNAME = "doc"` — folder inside each module holding the docs.
  - `GUIDE_FILENAME = "user_guide.md"` — the user-guide file name.
  - `CHANGES_DIRNAME = "changes"` — folder inside `doc/` holding the per-day change timeline.
  - `CHANGE_FILE_RE` — matches a change file name `YYYY-MM-DD.md` and captures the date.
  - `MODULE_PREFIX = "odu_"` — only modules with this prefix are collected.

## Constraints & Invariants
- None — no SQL constraints and no `@api.constrains`; the model stores no data.

## Business Rules & State
- The Book aggregates **one page per installed `odu_*` module** that ships a readable `doc/user_guide.md`.
- Source selection (Book **and** Changes): `ir.module.module` where `state = "installed"` AND `name =like "odu_%"`, ordered by `name` ascending, read with `sudo()`.
- Page skipping: a module whose guide is missing, unreadable, or non-UTF-8 is **silently skipped** (logged as a warning), never raised as an error.
- Page title rule: `module.shortdesc or module.name`.
- Only `user_guide.md` is exposed. The agent-facing `doc/tech_spec.md` is **deliberately never** read or shown to users.
- HTML is rendered from Markdown at request time — no caching, no stored HTML.
- **Changes archive** (the documentation-change timeline):
  - Each module may keep an append-only timeline under `doc/changes/`, **one Markdown file per calendar day**, named `YYYY-MM-DD.md`. Files whose name does not match `YYYY-MM-DD.md` are ignored; a module with no `doc/changes/` folder contributes nothing.
  - Aggregation axis is the **day**: every module's change file for a given date becomes one *entry* under that date. A day groups entries from all contributing modules.
  - Days are ordered **most-recent first** (descending date). Entries within a day are ordered by module name ascending. Entry title rule: `module.shortdesc or module.name`.
  - Same skip-on-error rule as guides: unreadable / non-UTF-8 change files are skipped with a warning.
  - This is an **intentional duplication**: `user_guide.md`/`tech_spec.md` are the current snapshot; `doc/changes/*.md` are the timeline of how that snapshot changed.

## Methods & Actions
- `odu.book.get_book(self)` — `@api.model`.
  - Purpose: assemble the whole book. Input: none.
  - Returns: `{"pages": [{"id": <module name>, "module": <module name>, "title": <shortdesc|name>, "html": <rendered HTML>}, ...]}`.
  - Side effects: none (read-only; reads files from disk).
  - Trigger: the `/odu_book/book` controller (and any server-side caller).
- `odu.book._read_module_guide(self, module_name)` — private.
  - Resolves the module path and returns the rendered HTML of its `doc/user_guide.md`, or `None` when the module path / file is absent or the file cannot be read/decoded.
- `odu.book.get_changes(self)` — `@api.model`.
  - Purpose: assemble the day-by-day documentation-change archive. Input: none.
  - Returns: `{"days": [{"date": "YYYY-MM-DD", "entries": [{"module", "title", "html"}, ...]}, ...]}` — days descending, entries by module name.
  - Side effects: none (read-only; reads files from disk).
  - Trigger: the `/odu_book/changes` controller (and any server-side caller).
- `odu.book._read_module_changes(self, module_name)` — private.
  - Returns the list of `(date_str, html)` pairs for the module's `doc/changes/*.md` files whose name matches `YYYY-MM-DD.md` (sorted by file name). Returns `[]` when the module path / `doc/changes/` folder is absent. Individual unreadable / non-UTF-8 files are skipped with a warning.
- `markdown.md_to_html(text)` — pure function (`models/markdown.py`), no Odoo dependency.
  - Purpose: dependency-free Markdown → HTML renderer, written from scratch so the Book needs no extra packages.
  - Supported syntax (behavior contract): ATX headings `#`..`######` (each gets an `id` slug via `_slug`), paragraphs, unordered/ordered lists incl. nesting and lazy continuation, fenced code blocks (``` ``` ``` or `~~~`, optional language → `class="language-<lang>"`), recursive blockquotes, GFM pipe tables (header + separator row), horizontal rules, and inline: bold `**`, italic `*`, inline code `` ` ``, links `[t](url)` → `<a target="_blank" rel="noreferrer noopener">`, images `![alt](src)`.
  - **Diff blocks**: a fenced block with language `diff` is rendered line by line — a line starting with `+` is wrapped in `<span class="o_diff_add">`, a line starting with `-` in `<span class="o_diff_del">`; all other lines stay plain. Content is still fully escaped. Used by the Changes archive to colour added/removed documentation.
  - Security/escaping: **all** text is HTML-escaped (`markupsafe.escape`); inline code is stashed before escaping so its content is never reformatted; `_` is intentionally left untouched so identifiers like `res_partner`/`odu_book` are not rendered as emphasis. Empty input → `""`.
  - Private helpers (no external contract, omitted by design): `_consume_fence/_consume_quote/_consume_table/_consume_list`, `_render_diff`, `_render_list`, `_split_row`, `_inline`, `_slug`.

## Security
- No `ir.model.access.csv`, no security groups, no record rules — `odu.book` is an AbstractModel with no table and needs no model ACL.
- Controllers `/odu_book/book` and `/odu_book/changes` are `auth="user"` → any authenticated internal user.
- The client actions and all menus carry **no group restriction** → visible to all internal users.
- `get_book` / `get_changes` read `ir.module.module` via `sudo()`; the user is not granted direct registry access.

## Views & UI
- `ir.actions.client` `action_odu_book`: name `Book`, `tag = "odu_book.book"`.
- `ir.actions.client` `action_odu_book_changes`: name `Changes`, `tag = "odu_book.changes"`.
- Menu structure (root app + two children, no group restrictions):
  - `menu_odu_book_root`: name `Book`, root-level (no parent), `sequence = 5`, **no action** — acts as the app container.
  - `menu_odu_book_doc`: name `Documentation`, parent `menu_odu_book_root`, `sequence = 5`, action `action_odu_book`.
  - `menu_odu_book_changes`: name `Changes`, parent `menu_odu_book_root`, `sequence = 10`, action `action_odu_book_changes`.
- OWL client action `BookApp` (template `odu_book.BookApp`, registered in the `actions` registry under tag `odu_book.book`):
  - Two-pane viewer: left = search box + table of contents (one entry per page); right = rendered guide.
  - State: `pages`, `activeId`, `search`, `loaded`.
  - Behavior: on start fetches `/odu_book/book` and auto-selects the first page; the TOC filters by case-insensitive substring match on `title`; the active page is highlighted; guide HTML is injected via `markup()` + `t-out`.
  - UI states: loading ("Loading…"), empty ("No documentation found."), no-selection placeholder ("Select a section…").
- OWL client action `ChangesApp` (template `odu_book.ChangesApp`, registered in the `actions` registry under tag `odu_book.changes`):
  - Two-pane archive: left = day timeline grouped under "Month Year" headers (blog-archive style); right = every module's change entry for the selected day.
  - State: `days`, `activeDate`, `loaded`.
  - Behavior: on start fetches `/odu_book/changes` and auto-selects the most recent day. `archive` getter groups the (already descending) days by `YYYY-MM` month; each day link shows a short label `Weekday, D` and an entry-count badge; `activeDay` renders each entry's HTML via `markup()` + `t-out` inside `.o_odu_book_doc`. Date labels are formatted client-side from the `YYYY-MM-DD` string (English month/weekday names).
  - UI states: loading ("Loading…"), empty ("No changes recorded yet."), no-selection placeholder ("Select a day…").
- Styling: `static/src/book/book.scss` (`.o_odu_book*`, `.o_odu_changes*`, `.o_diff_add`/`.o_diff_del`) — fixed 280px sidebar, active-link highlight, month headers + count badges for the archive, green/red diff colouring, and typography for headings/code/tables/blockquotes/images inside `.o_odu_book_doc`. `static/src/changes/changes.{js,xml}` carry the Changes client action.

## API Endpoints
- `POST /odu_book/book` — `type="jsonrpc"`, `auth="user"`.
  - Request: no parameters.
  - Response: the `get_book()` payload `{"pages": [{id, module, title, html}, ...]}`.
  - Controller: `OduBookController.book` → `request.env["odu.book"].get_book()`.
- `POST /odu_book/changes` — `type="jsonrpc"`, `auth="user"`.
  - Request: no parameters.
  - Response: the `get_changes()` payload `{"days": [{date, entries: [{module, title, html}, ...]}, ...]}`.
  - Controller: `OduBookController.changes` → `request.env["odu.book"].get_changes()`.

## Automation
- None — no crons, no server/automated actions.

## Seed / Demo Data
- None.

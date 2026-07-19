# OduSphere — Sphere System Map (local)

> **Sphere-owned companion to `.docs/architecture.md`.** The upstream template
> never ships or edits this file, so it can never conflict on `git merge`.
> **This is where you document THIS sphere's own `odu_*` modules** — the same
> "signatures and relations only, no code, no logic bodies" rule as the core map.
>
> Read **both** `.docs/architecture.md` (upstream core) **and** this file at the
> start of every session to load the complete picture.
>
> Do **not** add sphere modules to `.docs/architecture.md` — that file is
> upstream-owned and would conflict on the next update.

## Modules
| Module | Purpose | Depends | SPEC |
|---|---|---|---|
| `odu_contacts` | Top-level **Contacts** workspace: `res.partner` directory + `odu.contact.message` requests with a triage workflow, chatter and activities. | `odu_base`, `mail` | `addons/odu_contacts/doc/tech_spec.md` |

## Models
- `odu.contact.message` (`odu_contacts`) — extends the `odu_base` model via
  `_inherit = ["odu.contact.message", "mail.thread", "mail.activity.mixin"]` (adds chatter +
  activities). New fields: `state` (Selection `new`/`in_progress`/`done`, default `new`, req,
  index, tracking), `user_id` (Many2one → `res.users`, "Assigned To", index, tracking).
  - `create(self, vals_list)` — `@api.model_create_multi` override; `super()` then `_odu_sync_handled()`.
  - `write(self, vals)` — override; `super()` then `_odu_sync_handled()` when `state` in `vals`.
  - `_odu_sync_handled(self)` — sets core `handled = (state == "done")`; one-directional, writes on change only.

## Client Actions & Menus
- `action_odu_contact_requests` (`ir.actions.act_window`, `odu.contact.message`, `kanban,list,form`, search default `open`) — the Requests inbox.
- `action_odu_contacts_partners` (`ir.actions.act_window`, `res.partner`, `kanban,list,form`, reuses framework views) — the Contacts directory.
- Menu `menu_odu_contacts_root` — "Contacts", top-level app (no `groups`), sequence 10.
  - `menu_odu_contacts_partners` — "Contacts", sequence 10 → `action_odu_contacts_partners`.
  - `menu_odu_contacts_requests` — "Requests", sequence 20 → `action_odu_contact_requests`.
- Views for `odu.contact.message`: `view_odu_contact_message_{list,kanban,form,search}` (form has statusbar `state` + `<chatter/>`).

## Security Surface
- `odu_contacts`: `base.group_user` (all internal users) full CRUD on `odu.contact.message`
  (additive to `odu_base`'s admin-only rule) and on `res.partner` (incl. `unlink`). Menus carry
  no `groups`.

## UI Overrides
- `odu_contacts` deactivates the core `odu_base.menu_odu_contact_messages` (Settings → Contact
  Requests) on install (`noupdate="1"` data record, `active=False`) — the Contacts → Requests
  workspace supersedes it.

## Cross-Module Relations
- `odu_contacts` → `depends(odu_base, mail)`. Extends `odu_base`'s `odu.contact.message`
  (adds `state`, `user_id`, `mail.thread`/`mail.activity.mixin`) and keeps the core `handled`
  flag in sync. `user_id` → `res.users`; Contacts directory reuses `res.partner` (framework views).
- Capture is unchanged: `odu_base`'s public `POST /api/contact` fills `odu.contact.message`
  (new records default to `state = new`).

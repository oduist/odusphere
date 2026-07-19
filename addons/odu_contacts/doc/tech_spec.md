# odu_contacts — Module SPEC

## Identity & Manifest
- Technical name: `odu_contacts`
- Display name: `Contacts`
- Summary: Contacts workspace: partner directory + website contact requests with a triage workflow.
- Version: `19.0.1.0.0` (Odoo 19)
- Category: `Contacts` · Author: `OduSphere` · License: `LGPL-3`
- Flags: `application = True`, `installable = True`, `auto_install` not set.
- `depends`: `["odu_base", "mail"]`.
  - `odu_base` — mandatory governance base (ODUSPHERE.md §3).
  - `mail` — messaging/activity framework for chatter + activities. Allowed to
    install because `odu_base`'s policy lists `mail` in `ALLOWED_FRAMEWORK_MODULES`
    and auto-allows its dependency closure (`bus`, `base_setup`, …).
- External Python libs: none.
- `data` (load order): `security/ir.model.access.csv`, `data/odu_contacts_data.xml`,
  `views/odu_contact_message_views.xml`, `views/res_partner_views.xml`,
  `views/odu_contacts_menus.xml`.
- Assets: none.

## Models & Fields
- `odu.contact.message` — `models.Model`, extended here via
  `_inherit = ["odu.contact.message", "mail.thread", "mail.activity.mixin"]`
  (the base model + fields `name`/`email`/`message`/`handled`, `_order`, `_rec_name`
  are owned by `odu_base`; this module only adds the workflow/collaboration layer).
  Added fields:
  - `state` (Selection, `string="Status"`, values `new` / `in_progress` / `done`,
    `default="new"`, `required=True`, `index=True`, `tracking=True`) — triage state.
  - `user_id` (Many2one → `res.users`, `string="Assigned To"`, `index=True`,
    `tracking=True`) — the internal owner responsible for the request.
  - Mixin-provided stored state used by the UI: `message_ids`,
    `message_follower_ids`, `activity_ids`, `activity_state` (from `mail.thread` /
    `mail.activity.mixin`). No custom attributes on these.

## Constraints & Invariants
- No SQL constraints, no `@api.constrains`.
- Invariant (maintained imperatively, not a DB constraint): the core boolean
  `handled` equals `state == "done"`. Kept in sync by `_odu_sync_handled` on
  `create`/`write` (see Business Rules).

## Business Rules & State
- **Triage states:** `new` → `in_progress` → `done`. Transitions are free (any
  state to any state) — driven by the form statusbar or by dragging kanban cards;
  there is no gating logic.
- **`handled` bridge (one-directional):** whenever `state` is set (on create, or on
  any write that includes `state`), `handled` is updated to `state == "done"`. The
  reverse is not enforced — `handled` remains a plain writable field so the core's
  own behavior and tests are unaffected; the sync only writes when the value
  actually changes, so it never recurses.
- **Inbox supersession:** on install, the module deactivates the administrator-only
  `odu_base.menu_odu_contact_messages` (Settings → Contact Requests) so the new
  top-level **Contacts → Requests** is the single entry point for the same model.
  The data record is `noupdate="1"`, so an admin may re-enable the old menu.
- **Public capture unchanged:** submissions still arrive via `odu_base`'s public
  `POST /api/contact` (created with `sudo()`, no `state` in the payload → defaults
  to `new`, `handled` → `False`).

## Methods & Actions
- `odu.contact.message.create(self, vals_list)` — `@api.model_create_multi` override.
  - Calls `super().create`, then `records._odu_sync_handled()`.
  - Trigger: any record creation (ORM, and the public endpoint via `sudo()`).
- `odu.contact.message.write(self, vals)` — override.
  - Calls `super().write`; if `"state" in vals`, calls `self._odu_sync_handled()`.
  - Trigger: any write; the sync fires only when `state` changes.
- `odu.contact.message._odu_sync_handled(self)` — internal helper.
  - Sets `handled = (state == "done")` per record, writing only on change. No return.

## Security
- `security/ir.model.access.csv` — two rows, both for `base.group_user` (every
  internal user), full CRUD (read/write/create/unlink):
  - `access_odu_contact_message_user` on `odu_base.model_odu_contact_message` —
    additive to `odu_base`'s admin-only rule; lets regular users triage requests.
  - `access_res_partner_odu_contacts_user` on `base.model_res_partner` — grants
    regular users full access to the partner directory (including `unlink`, on top
    of the framework's own partner ACLs).
- No new groups, no record rules.
- Menus carry no `groups`, so visibility follows the ACLs above (all internal users).

## Views & UI
- **`odu.contact.message`** (`views/odu_contact_message_views.xml`):
  - list `view_odu_contact_message_list` — columns Received (`create_date`), `name`,
    `email`, `user_id` (`many2one_avatar_user`, optional), `activity_ids`
    (`list_activity`, optional), `state` (`badge`, info/warning/success by state);
    `decoration-muted` on done rows.
  - kanban `view_odu_contact_message_kanban` — `default_group_by="state"`; card shows
    name, assigned-user avatar, email, and a `kanban_activity` widget.
  - form `view_odu_contact_message_form` — `<header>` statusbar for `state`
    (`clickable`); sheet with name/email(`email` widget)/`user_id`
    (`many2one_avatar_user`)/Received/message; a `<chatter/>` (followers, activities,
    log).
  - search `view_odu_contact_message_search` — search on name/email/message/user_id;
    filters Open (`state != done`), New, In Progress, Done, My Requests
    (`user_id = uid`), Unassigned (`user_id = False`); group-by Status and Assigned To.
  - action `action_odu_contact_requests` ("Requests", `view_mode=kanban,list,form`,
    `search_view_id` pinned, context `{'search_default_open': 1}`).
- **`res.partner`** (`views/res_partner_views.xml`):
  - action `action_odu_contacts_partners` ("Contacts", `view_mode=kanban,list,form`).
    No view records — the framework's default `res.partner` views are reused.
- **Menus** (`views/odu_contacts_menus.xml`):
  - `menu_odu_contacts_root` — "Contacts", top-level app (no parent, no `groups`),
    sequence 10.
  - `menu_odu_contacts_partners` — "Contacts", → `action_odu_contacts_partners`, seq 10.
  - `menu_odu_contacts_requests` — "Requests", → `action_odu_contact_requests`, seq 20.

## API Endpoints
- None. (Capture stays in `odu_base`'s `POST /api/contact`.)

## Automation
- None — no crons, no server/automated actions. Activities are user-scheduled via
  the `mail.activity.mixin` UI.

## Seed / Demo Data
- One configuration record (`data/odu_contacts_data.xml`, `noupdate="1"`):
  deactivates `odu_base.menu_odu_contact_messages` (`active = False`).

# Contacts — Administration

This page is for administrators. It covers who can use the **Contacts** app, how it
relates to the core contact endpoint, and the one dependency it brings in.

## Access

The Contacts app is open to **every internal user** (`base.group_user`), with
**full access** (read/write/create/delete) to both sections:

- **Requests** (`odu.contact.message`) — added by this module on top of the
  administrator-only rule that ships in `odu_base`.
- **Contacts** (`res.partner`) — this module grants internal users full access,
  **including delete**, on top of the framework's own partner permissions.

The menus carry no group restriction, so visibility follows those access rights. If
you want to narrow this — for example, keep the partner directory but forbid regular
users from deleting partners — tighten the rows in
`addons/odu_contacts/security/ir.model.access.csv` (set `perm_unlink` to `0`) or
restrict the menus with a `groups` attribute.

## The `mail` dependency

Chatter and activities on requests are provided by Odoo's `mail` framework, so this
module depends on `mail`. That is allowed by the OduSphere governance core:
`odu_base` lists `mail` among the permitted framework modules and automatically
permits the modules `mail` itself is built on (`bus`, `base_setup`). Nothing extra
has to be configured to install this module — see the **Base** Admin Guide,
"Allowing an extra framework module", for how the allow-list works.

Installing `odu_contacts` therefore also installs `mail` (and its framework
dependencies). This is a deliberate, framework-tier addition — not a business app.

## The old Contact Requests inbox

`odu_base` ships a minimal, administrator-only **Settings → Contact Requests**
inbox. Because the Contacts app now offers a richer inbox for everyone, this module
**hides that Settings menu on install** so there is a single entry point to the same
messages. It is only hidden, not deleted: to bring it back, re-activate the menu
`odu_base.menu_odu_contact_messages` (enable developer mode → **Settings →
Technical → User Interface → Menu Items**, set it active again).

## How requests are captured

Requests are still stored by the public `POST /api/contact` endpoint in `odu_base`
(open to anyone, no login). New submissions arrive with status **New** and no
assigned owner. The endpoint, its spam guards and its behavior are documented in the
**Base** Admin Guide — this module only adds the workflow and the workspace UI on
top of it.

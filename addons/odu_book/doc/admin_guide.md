# Book — Administration

This page is for administrators. It explains who can see which part of the
**Book** and how access is controlled. It is itself visible only to **Settings**
administrators.

## Upstream updates — protected core modules

`odu_base` and `odu_book` are part of the shared **OduSphere template**
(maintained upstream), not this sphere's own work. This sphere periodically pulls
new template versions through the OduSphere CLI (its
`update_sphere_from_upstream` tool).

**Do not edit anything inside `addons/odu_base/` or `addons/odu_book/`.** They
belong to the read-only **core lane**: inside a sphere the core is mounted
read-only for the coding agent, and the CLI refuses to deploy a sphere whose
core differs from the upstream template. On every update these two modules are
taken from upstream **as-is**: any stray local change to them is overwritten —
by design — so that upstream fixes always land cleanly. (Your own work is safe
in the **sphere lane** — everything under `sphere/` is kept: this sphere's
`odu_*` modules in `sphere/addons/`, `sphere/website/`, `sphere/README.md`,
`sphere/LANG.local.md` and the sphere system map
`sphere/docs/architecture.local.md`.)

To change or extend core behavior, **create your own `odu_*` module** in
`sphere/addons/` that depends on `odu_base` — never modify the core in place.
See `.docs/ownership.md` for the full ownership and isolation model.

## The three sections and who sees them

The Book app has three menus:

| Section | Reads | Who can open it |
|---|---|---|
| **User Guide** | each module's `doc/user_guide.md` | every internal user |
| **Admin Guide** | each module's `doc/admin_guide.md` | Settings administrators only |
| **Changes** | each module's `doc/changes/*.md` | every internal user |

## Access control

- The **Admin Guide** menu is restricted to the *Settings* group
  (`base.group_system`). Users without that group never see the menu.
- Access is also enforced on the server: the admin endpoint refuses to return
  any administrator guide to a non-administrator, so the restriction cannot be
  bypassed from the browser.

## What belongs here

Whenever a module has settings or privileged tasks — things that must be done
with administrator access — they are documented in that module's **Admin Guide**
page, not in the user guide. If the Admin Guide is empty, no installed module
currently exposes administrator settings.

## Documentation languages

The Book shows each reader the documentation in **their own language** — the one
set on their Odoo user profile. For a given module and page it looks for a
translation first and falls back to the original text when no translation exists,
so a partially translated system still reads cleanly.

- The set of languages is defined in the project's `sphere/LANG.local.md` file
  (the rules for those fields live in the upstream-owned `LANG.md`). Today the
  documentation ships in English only (`source: en`, no targets yet).
- Translations are **pre-generated files**, not live machine translation — there
  is no per-request translation cost or external service.
- To add a language, the maintainer runs the `odu-doc-i18n` skill, which mirrors
  the User Guide and Admin Guide of every module into the new language. The
  **Changes** archive is kept in the source language only.


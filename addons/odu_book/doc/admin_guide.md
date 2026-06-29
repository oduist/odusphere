# Book — Administration

This page is for administrators. It explains who can see which part of the
**Book** and how access is controlled. It is itself visible only to **Settings**
administrators.

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

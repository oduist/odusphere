@ODUSPHERE.md
@LANG.md
@sphere/LANG.local.md
@sphere/AGENTS.md

## Language

Always write **code** in English — comments, identifiers, UI strings (menus, views, labels, messages), and commit messages. Never hardcode non-English text in code. For UI-string localization, rely on Odoo's built-in translation mechanisms (`_()` / `env._()` helpers and `.po` / `.pot` files).

**Human documentation** (the `user_guide.md` / `admin_guide.md` guides) follows the language policy in `LANG.md` (with this sphere's selections in `sphere/LANG.local.md`): authored in the `source` language and mirrored into every `target` language. Agent-facing docs (`tech_spec.md`, the system map `.docs/architecture.md` + `sphere/docs/architecture.local.md`) and the change timeline stay in the `source` language only.

> The system map is split: `.docs/architecture.md` is the **upstream-owned core** (never edit it in a sphere) and `sphere/docs/architecture.local.md` is **sphere-owned** (document this sphere's modules there). Read **both** at the start of every session. See `ODUSPHERE.md` §6 and `.docs/ownership.md` for the core/sphere ownership model.

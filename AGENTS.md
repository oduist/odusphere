@ODUSPHERE.md
@LANG.md

## Language

Always write **code** in English — comments, identifiers, UI strings (menus, views, labels, messages), and commit messages. Never hardcode non-English text in code. For UI-string localization, rely on Odoo's built-in translation mechanisms (`_()` / `env._()` helpers and `.po` / `.pot` files).

**Human documentation** (the `user_guide.md` / `admin_guide.md` guides) follows the language policy in `LANG.md`: authored in the `source` language and mirrored into every `target` language. Agent-facing docs (`tech_spec.md`, `.docs/architecture.md`) and the change timeline stay in the `source` language only.

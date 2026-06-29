# Language Policy

Single source of truth for languages in this OduSphere. Read by the agent and by
the `odu-doc-i18n` skill.

> Two independent planes of i18n — do not mix them:
> - **UI strings** of modules (menus, labels, messages) are localised the Odoo
>   way, via `.po` / `.pot` files.
> - **Document content** (the human guides) is governed by *this* file and stored
>   as language mirrors under each module's `doc/i18n/<lang>/`.

## Agent communication

- primary: en

The language the agent uses when talking to the user. Actual enforcement lives in
the harness / `CLAUDE.md`; this section records the canonical choice.

## Documentation

- source: en
- targets:
- translate: user_guide.md, admin_guide.md
- source-only: tech_spec.md, .docs/architecture.md, changes/

Rules:

- **`source`** is the canonical authoring language for every document. The agent
  always writes the source first.
- **`targets`** are mirror languages kept in sync with the source. **Empty for
  now** — the system is multilingual-ready but ships only `en`.
- **`translate`** lists the human documents mirrored into every target language.
  Only the Userbook and the Adminbook are translated.
- **`source-only`** documents are never translated: agent contracts
  (`tech_spec.md`, `.docs/architecture.md`) and the change timeline (`changes/`).
- **Where mirrors live:** a target-language copy of `doc/<file>` lives at
  `doc/i18n/<lang>/<file>`. The Userbook/Adminbook serve each reader the file
  matching their Odoo language, falling back to the source file when a
  translation is absent.
- **Adding a language:** run the `odu-doc-i18n` skill (`add <lang>`). It mirrors
  every module's `translate` files into `doc/i18n/<lang>/`, stamps each with a
  provenance marker, and registers the new code under `targets` above. After a
  language exists, the agent authors documentation in **all** target languages
  by default (Definition of Done — see `ODUSPHERE.md` §6).

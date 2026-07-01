# Language Policy

The **rules** for how languages work in an OduSphere. This file is the
upstream-owned *policy*; the actual per-sphere **selections** (which languages
are active, the source language, the target list) live in the sphere-owned
[`LANG.local.md`](LANG.local.md).

> This split mirrors `.docs/architecture.md` (upstream core) vs
> `.docs/architecture.local.md` (sphere-owned): upstream can improve the policy
> below without ever conflicting with a sphere's chosen languages. Read **both**
> together — `LANG.md` explains the fields, `LANG.local.md` sets their values.

Read by the agent and by the `odu-doc-i18n` skill.

> Two independent planes of i18n — do not mix them:
> - **UI strings** of modules (menus, labels, messages) are localised the Odoo
>   way, via `.po` / `.pot` files.
> - **Document content** (the human guides) is governed by this policy and stored
>   as language mirrors under each module's `doc/i18n/<lang>/`.

## Agent communication

`LANG.local.md` → `Agent communication` → `primary` records the canonical
language the agent uses when talking to the user. Actual enforcement lives in the
harness / `CLAUDE.md`; the setting only records the canonical choice.

## Documentation

`LANG.local.md` → `Documentation` defines four fields — their meaning:

- **`source`** is the canonical authoring language for every document. The agent
  always writes the source first.
- **`targets`** are mirror languages kept in sync with the source. May be empty —
  the system is multilingual-ready even when it ships a single language.
- **`translate`** lists the human documents mirrored into every target language.
  Only the Userbook and the Adminbook are translated.
- **`source-only`** documents are never translated: agent contracts
  (`tech_spec.md`, the system map `.docs/architecture.md` +
  `.docs/architecture.local.md`) and the change timeline (`changes/`).

Rules that hold regardless of the selected values:

- **Where mirrors live:** a target-language copy of `doc/<file>` lives at
  `doc/i18n/<lang>/<file>`. The Userbook/Adminbook serve each reader the file
  matching their Odoo language, falling back to the source file when a
  translation is absent.
- **Adding a language:** run the `odu-doc-i18n` skill (`add <lang>`). It mirrors
  every module's `translate` files into `doc/i18n/<lang>/`, stamps each with a
  provenance marker, and registers the new code under `targets` in
  `LANG.local.md`. After a language exists, the agent authors documentation in
  **all** target languages by default (Definition of Done — see `ODUSPHERE.md`
  §6).

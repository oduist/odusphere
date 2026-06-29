# Base

The **Base** module is the governance core of your OduSphere. It does not add any
screen or menu — instead, it quietly protects your system by deciding **which modules
are allowed to be installed**.

## What it does

OduSphere is built on the principle of absolute minimalism: your system contains only
the software that was grown specifically for your business. To keep it that way, this
module allows installing **only**:

- modules whose technical name starts with **`odu_`** (the modules built for you), and
- a small set of allowed framework modules (`base`, `web`).

Any attempt to install a standard, off-the-shelf application — Sales, Purchase,
Inventory, Accounting, CRM, HR, Product, and so on — is refused with a clear message.
This guarantees your OduSphere never accumulates the bloat and unused features of a
traditional ERP.

## What you will see

When you (or anyone) open **Apps** and try to activate a module that is not part of
OduSphere, the installation stops and a dialog appears:

> **OduSphere installation policy**
> Only modules carrying the 'odu_' prefix may be installed (plus the allowed framework
> modules: base, web).
>
> Refused: <the module names that were blocked>

Installing an OduSphere module (anything named `odu_…`) works normally.

## Allowing an extra framework module (administrators)

In rare cases a legitimate technical framework module is needed as a building block.
An administrator can extend the allowed list without changing any code:

1. Enable developer mode.
2. Go to **Settings → Technical → System Parameters**.
3. Create (or edit) the parameter **`odu_base.allowed_non_odu_modules`**.
4. Set its value to a comma-separated list of the extra module names to allow, for
   example: `web, base, your_extra_module`.

The built-in framework modules (`base`, `web`) are always allowed, even if they are not
listed in the parameter.

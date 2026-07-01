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

The **Apps** screen lists **only OduSphere modules** — anything that is not part of your
OduSphere is hidden, so the catalog stays clean. The **Third-Party Apps** entry is removed
from the Apps menu as well.

If an installation of a non-OduSphere module is attempted anyway, it stops with a short
message:

> **Invalid Operation**
> Only OduSphere modules can be installed.

Installing an OduSphere module (anything named `odu_…`) works normally.

## Administrator settings

Configurable settings — such as allowing an extra framework module to install — are
administrator tasks and are documented in this module's **Admin Guide**.

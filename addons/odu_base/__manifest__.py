{
    "name": "Base",
    "summary": "OduSphere governance core: enforces the odu_ module installation policy",
    "description": """
Base
====

The OduSphere governance core. This module carries the platform-wide
constraints that keep an OduSphere pure. Right now it enforces a single,
non-negotiable rule:

**Only modules created according to the OduSphere specification may be
installed.** Concretely, a module can be installed only when its technical
name starts with the ``odu_`` prefix, plus a minimal, explicitly allowed set
of framework modules the Incubator is allowed to build upon (``base``,
``web``).

This blocks the standard Odoo business applications (``sale``, ``purchase``,
``stock``, ``account``, ``crm``, ``hr``, ``product`` ...) from ever entering
the system, preserving the Zero-Bloat architecture.
""",
    "version": "19.0.1.0.0",
    "category": "Technical",
    "author": "OduSphere",
    "license": "LGPL-3",
    "depends": ["base"],
    "data": [],
    "application": False,
    "installable": True,
}

# OduSphere 🪐

> **The Living ERP Architecture.** A paradigm shift in business automation away from traditional, bloated enterprise software legacy, powered entirely by autonomous AI orchestration.

---

## Repository layout — two lanes

An OduSphere repository is split into a **core** lane (upstream-owned, read-only
inside a sphere) and a **sphere** lane (everything this sphere builds). The full
model — mounts, merge lanes, the deploy gate — is documented in
[`.docs/ownership.md`](.docs/ownership.md); the machine-readable boundary is
[`.odusphere/ownership`](.odusphere/ownership).

```
.
├── ODUSPHERE.md, AGENTS.md, LANG.md   # Core: the contract (read-only in a sphere)
├── addons/                            # Core: odu_base + odu_book (read-only in a sphere)
├── .docs/                             # Core: system map + ownership model
├── .odusphere/                        # Core: ownership manifest (read by the CLI)
└── sphere/                            # SPHERE LANE — everything this sphere owns
    ├── addons/                        # This sphere's odu_* modules
    ├── website/                       # Astro site root; build → sphere/website/dist
    ├── AGENTS.md                      # Sphere-specific agent instructions
    ├── LANG.local.md                  # Sphere language selections
    ├── docs/architecture.local.md     # Sphere system map
    ├── sphere.caddy                   # Sphere-owned extra gateway routes
    └── README.md                      # Sphere-specific notes
```

OduSphere is headless: **Odoo** handles only the backend and data, the public
site is built with **Astro** (`sphere/website/`), and **Caddy** sits in front as
the single entry point. The standard Odoo `website` module is not used.

## Running a sphere

This sphere is **provisioned and operated entirely by the
[OduSphere CLI](https://github.com/oduist/odusphere-cli)** — there is no local
`docker compose` stack. The CLI runs the Postgres database, the Odoo backend, and
the Caddy gateway as containers (one isolated environment per git branch) and
exposes them to AI coding agents over MCP. Code reaches the running containers
**through git** (the CLI clones this repo and applies changes), and the agent's
own workspace is mounted with the core lane read-only.

To bring a sphere up, point the OduSphere CLI at this repository and let it create
the environment, install modules, and run tests. See the CLI documentation at
<https://docs.odusphere.dev/>.

Once an environment is up:

- `/` — public site (static files Caddy serves from `sphere/website/dist`, built
  with `astro build` — see [sphere/website/README.md](sphere/website/README.md)).
- `/odoo` — Odoo backend (login / database manager).

The demo module `odu_book` is installed through the CLI (e.g. its
`install_odoo_modules` tool), not a local shell command.

---

## Updating a sphere from the template

A **sphere** is a downstream copy of this template that follows one upstream
version branch (e.g. `19.0`) and pulls new template versions through the CLI's
`update_sphere_from_upstream` tool — a clean 3-way merge in which the ownership
lanes keep the sphere's files and land upstream's core changes. Deploying to
production is a separate, deliberate CLI step guarded by the core-integrity
gate. The full model, and the migration steps for spheres on the old layout,
live in [`.docs/ownership.md`](.docs/ownership.md).

Document this sphere's own modules in `sphere/docs/architecture.local.md` (not
the upstream-owned `.docs/architecture.md`), and add gateway routes in
`sphere/sphere.caddy`. See `ODUSPHERE.md` §6.

---

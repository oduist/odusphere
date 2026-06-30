# OduSphere 🪐

> **The Living ERP Architecture.** A paradigm shift in business automation away from traditional, bloated enterprise software legacy, powered entirely by autonomous AI orchestration.

---

## Repository layout

OduSphere follows a headless architecture: **Odoo** handles only the backend and
data, the public site is built with **Astro**, and **Caddy** sits in front as the
single entry point.

```
.
├── addons/             # OduSphere Odoo modules (odu_* prefix); e.g. odu_book
├── website/            # Astro site root; build → website/dist (served by Caddy)
├── Caddyfile           # Gateway: static website/dist + proxy to Odoo
└── sphere.caddy        # Sphere-owned extra gateway routes (imported by the Caddyfile)
```

The standard Odoo `website` module is not used — the entire public frontend lives in
`website/`.

## Running a sphere

This sphere is **provisioned and operated entirely by the
[OduSphere CLI](https://github.com/oduist/odusphere-cli)** — there is no local
`docker compose` stack. The CLI runs the Postgres database, the Odoo backend, and
the Caddy gateway as containers (one isolated environment per git branch) and
exposes them to AI coding agents over MCP. Code reaches the running containers
**through git** (the CLI clones this repo and applies changes), not a bind-mount.

To bring a sphere up, point the OduSphere CLI at this repository and let it create
the environment, install modules, and run tests. See the CLI documentation at
<https://docs.odusphere.dev/>.

Once an environment is up:

- `/` — public site (static files Caddy serves from `website/dist`, built with
  `astro build` — see [website/README.md](website/README.md)).
- `/odoo` — Odoo backend (login / database manager).

The demo module `odu_book` is installed through the CLI (e.g. its
`install_odoo_modules` tool), not a local shell command.

---

## Updating a sphere from the template

A **sphere** is a downstream copy of this template that pulls new template
versions from the `upstream` remote with minimal conflicts. The model — shared
history, ownership lanes, and a `merge=ours` driver — is documented in
[`scripts/README.md`](scripts/README.md). In short:

```bash
# Day-to-day: pull the latest template (clean 3-way merge, sphere files kept).
./scripts/update-from-upstream.sh

# One-time, only if the sphere has no shared history with upstream:
./scripts/link-upstream-history.sh

# Start a brand-new sphere as a clone (shares history from the start):
./scripts/bootstrap-sphere.sh <target-dir> <your-sphere-git-url>
```

Document this sphere's own modules in `.docs/architecture.local.md` (not the
upstream-owned `.docs/architecture.md`), and add gateway routes in `sphere.caddy`
(not the `Caddyfile`). See `ODUSPHERE.md` §6.

---

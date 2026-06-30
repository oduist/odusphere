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
├── config/odoo.conf    # Odoo configuration for the local stack
├── Caddyfile           # Gateway: static website/dist + proxy to Odoo
└── docker-compose.yml  # Local stack: Postgres + Odoo + Caddy
```

The standard Odoo `website` module is not used — the entire public frontend lives in
`website/`.

## Quick start

```bash
docker compose up -d        # start Postgres + Odoo + Caddy
docker compose ps           # check service status
```

Once running:

- `http://localhost/` — public site (static files from `website/dist`; currently a
  temporary placeholder until `astro build` has run — see
  [website/README.md](website/README.md)).
- `http://localhost/odoo` — Odoo backend (login / database manager).

Install the demo module `odu_book`:

```bash
docker compose exec odoo odoo -i odu_book -d odusphere --stop-after-init
```

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

# Sphere ↔ template update model

A **sphere** is a downstream copy of the `oduist/odusphere` **template**. Spheres
pull new template versions from the `upstream` remote and must do so *seamlessly*:
the sphere's own work should rarely, if ever, conflict with upstream.

That works only when three things hold. The scripts here set them up.

## 1. Shared history (the foundation)

Git can only do a clean **3-way** merge when the sphere and upstream share a
common ancestor. Without one, `git merge` degrades to a **2-way** merge and
conflicts on *every* file upstream changed since the copy — even files the sphere
never touched.

- **New spheres:** create them as a clone, not `git init` + copy:
  ```
  ./scripts/bootstrap-sphere.sh <target-dir> <your-sphere-git-url>
  ```
  This clones the template, wires `upstream` + `origin`, and pushes. History is
  shared from the start; no `--allow-unrelated-histories` is ever needed.

- **Existing spheres with unrelated history:** link them once:
  ```
  ./scripts/link-upstream-history.sh            # auto-detect the copy point
  ./scripts/link-upstream-history.sh --from v0.1  # or pin explicitly
  ```
  This records a shared ancestor without changing the sphere's tree. After it,
  all future updates are clean 3-way merges.

## 2. Ownership lanes (so the same file isn't edited by both sides)

The rule: for every file two parties would edit, either give each side its **own
file**, or declare a deterministic **winner**. Splitting is preferred — it keeps
both sides' content.

| Concern | Upstream-owned (you receive updates) | Sphere-owned (you keep yours) |
|---|---|---|
| System map | `.docs/architecture.md` (core only) | `.docs/architecture.local.md` (this sphere's modules) |
| Gateway | `Caddyfile` | `sphere.caddy` (imported by the Caddyfile) |
| Local stack | `docker-compose.yml` | `docker-compose.override.yml` (git-ignored; compose merges it natively) |
| Frontend | — | `website/**` |
| Config / docs | `ODUSPHERE.md`, `AGENTS.md`, core `addons/odu_base`, `addons/odu_book`, `scripts/` | `README.md`, `LANG.md`, `config/odoo.conf` |
| Your modules | — | `addons/odu_<your_module>/**` (upstream never ships these) |

**Never** add a sphere's modules to `.docs/architecture.md` or edit the
`Caddyfile`/`docker-compose.yml` directly — use the sphere-owned companion. That
is what keeps updates conflict-free (the contract in `ODUSPHERE.md` §6 enforces
this for the system map).

## 3. The merge drivers (auto-resolve conflicts deterministically)

`.gitattributes` assigns a winner per path so conflicts resolve without a human:

- **`merge=ours`** — sphere-owned files (`website/`, `README.md`, the sphere map,
  …): keep the sphere's version.
- **`merge=theirs`** — upstream-owned **core modules** (`addons/odu_base`,
  `addons/odu_book`): always take upstream. A sphere must **not** edit these; if it
  does, the local change is overwritten on update (by design), so core fixes always
  land. This prohibition is documented in the odu_book **Admin Guide**.

Both drivers live in `.git/config` (they can't be committed), so the
update/bootstrap/link scripts register them idempotently:
```
git config merge.ours.driver true
git config merge.theirs.driver 'cp -f "%B" "%A"'
```
**Limitation:** `merge=ours` only fires on a real 3-way *content* conflict. It
does **not** handle files upstream *adds* that the sphere lacks (a clean add) or
modify/delete conflicts. `update-from-upstream.sh` prunes upstream-added files
under `website/` itself, and reports any residual conflicts for a human.

## Day-to-day

```
./scripts/update-from-upstream.sh
```
With shared history + ownership lanes + the driver in place, this fetches,
merges, auto-keeps sphere-owned files, and commits — usually with **zero**
manual conflict resolution.

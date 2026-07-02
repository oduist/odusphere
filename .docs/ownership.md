# Core / Sphere ownership & isolation

A **sphere** is a downstream copy of the `oduist/odusphere` **template**. This
file defines the hard boundary between the two lanes of every sphere repository
and how that boundary is enforced. The machine-readable form of the boundary is
the manifest [`.odusphere/ownership`](../.odusphere/ownership); this file is the
human explanation.

## The two lanes

| Lane | Who owns it | Agent access | Contents |
|---|---|---|---|
| **Core** | upstream template | **read-only** | The contract (`ODUSPHERE.md`, `AGENTS.md`, `LANG.md`, `CLAUDE.md`, root `README.md`), core modules (`addons/odu_base`, `addons/odu_book`), the core system map (`.docs/`), the manifest (`.odusphere/`), upstream skills (`.claude/skills/odu-doc-i18n/`), `.gitattributes`, `.gitignore` |
| **Sphere** | this sphere | **read-write** | Everything under `sphere/`: client modules (`sphere/addons/`), the Astro site (`sphere/website/`), sphere agent instructions (`sphere/AGENTS.md`), language selections (`sphere/LANG.local.md`), the sphere system map (`sphere/docs/architecture.local.md`), extra gateway routes (`sphere/sphere.caddy`), sphere notes (`sphere/README.md`) — plus sphere-added skills in `.claude/skills/` |

The rule of thumb: **the agent builds the client's world inside `sphere/`; the
world's physics live outside it and cannot be changed from within.** Core evolves
only upstream and reaches the sphere through template updates.

## The manifest — `.odusphere/ownership`

One `<mode> <path>` per line (`rw` / `ro`, directories only, deeper paths
override). Everything not covered by an `rw` line is core. The OduSphere CLI
consumes it for both enforcement layers below; the merge lanes in
`.gitattributes` mirror the same boundary for git.

## Enforcement — three layers

1. **Agent-container mounts (filesystem wall).** The CLI mounts each checkout
   into the agent container read-only, then overlays the manifest's `rw`
   directories (plus `.git/`) as writable nested mounts. Writes to core paths
   fail with a filesystem error no matter which tool attempts them. Only
   directory mounts are used — single-file bind mounts break when git replaces
   a file (rename swaps the inode).
2. **Runtime containers.** The Odoo container receives the repo checkout
   read-only as well; code reaches it only via `git push` + the CLI's pull
   tools, so a shell inside the runtime container cannot alter core either.
3. **Deploy-time core-integrity gate (the hard wall).** Production only moves
   via the CLI. Before deploying, the CLI verifies that every core path in the
   deployed commit is byte-identical (by git blob/tree OID) to some commit of
   the upstream template branch the sphere follows. A diverged core — however
   it was produced — is refused with an explicit error.

## Versions

A sphere follows exactly one upstream **version branch** (e.g. `19.0`). The
catalog of public versions is configured in the CLI, and a sphere may follow a
custom (non-public) upstream branch instead — isolation is identical either
way: core is read-only and the gate verifies against the followed branch.
Switching version = merging the new upstream branch into the sphere (a forward
merge, then a deliberate deploy).

## Merge lanes (`.gitattributes`)

Updates stay conflict-free because each path has a deterministic owner:

- **`sphere/** merge=ours`** — on a content conflict, keep the sphere's version.
  With the mount wall in place upstream never edits `sphere/` and the sphere
  never edits core, so real conflicts should not occur; the lane is a safety
  net (e.g. for spheres updated before the wall existed).
- **`addons/odu_base/**`, `addons/odu_book/** merge=theirs`** — core modules
  always take upstream, so core fixes land even over stray local edits.
- **No rule (default 3-way merge)** — the rest of core: upstream improvements
  flow in.

Two git preconditions, both handled by the CLI (`update_sphere_from_upstream`):

- **Shared history.** Clean 3-way merges need a common ancestor — spheres are
  created as clones of the template, never `git init` + copy.
- **Merge drivers.** The `ours`/`theirs` drivers live in `.git/config` and are
  registered idempotently before every merge
  (`git config merge.ours.driver true`,
  `git config merge.theirs.driver 'cp -f "%B" "%A"'`). Note `merge=ours` fires
  only on a real content conflict; files upstream *adds* under `sphere/` are
  pruned by the update flow.

## Migrating a sphere from the pre-`sphere/` layout

Older spheres kept sphere-owned files at scattered paths. Before (or when) the
CLI merges a post-restructure template, apply the same moves locally so git
matches them up as renames:

```bash
git mv website sphere/website
git mv LANG.local.md sphere/LANG.local.md
mkdir -p sphere/docs && git mv .docs/architecture.local.md sphere/docs/architecture.local.md
[ -f sphere.caddy ] && git mv sphere.caddy sphere/sphere.caddy
git commit -m "Migrate to the sphere/ layout"
```

Sphere-specific content in the root `README.md` (now core) should move to
`sphere/README.md`. Client `odu_*` modules living directly under `addons/` move
to `sphere/addons/` (requires a module upgrade after the CLI updates the
addons path).

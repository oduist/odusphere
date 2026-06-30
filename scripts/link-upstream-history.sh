#!/usr/bin/env bash
#
# link-upstream-history.sh
#
# ONE-TIME fix for spheres that were bootstrapped by `git init` + copying the
# template (so they share NO history with upstream). Without a common ancestor,
# every `git merge upstream/main` degrades to a 2-way merge and conflicts on every
# file upstream ever touched. This records a shared ancestor ONCE so all future
# updates are clean 3-way merges.
#
# It runs:  git merge -s ours --allow-unrelated-histories <PIN>
# `-s ours` keeps this sphere's tree byte-for-byte (nothing changes now) but
# records <PIN> (an upstream commit) as a second parent — establishing the base.
#
# Choosing <PIN> matters:
#   * Ideal: the upstream commit this sphere was originally copied from. Its
#     core/contract files still match the sphere, so the next real update brings
#     in exactly the upstream changes made since the copy.
#   * Default (no --from): auto-detected as the NEWEST upstream commit whose core
#     files (addons/odu_base, addons/odu_book, ODUSPHERE.md) are identical to this
#     sphere's. If none match (you edited core), you must pass --from.
#   * Anti-pattern: pinning to the upstream TIP silently declares "sphere is
#     current", skipping real upstream deltas. The script warns if it picks the tip.
#
#   Usage:
#     ./scripts/link-upstream-history.sh                 # auto-detect the pin
#     ./scripts/link-upstream-history.sh --from v0.1     # pin to a tag/commit
#     ./scripts/link-upstream-history.sh --from a6dc6ea  # pin to a specific SHA
#
set -euo pipefail

UPSTREAM_REMOTE="upstream"
UPSTREAM_BRANCH="main"
# Upstream-owned paths used to auto-detect the copy point (must exist upstream).
CORE_PATHS=("addons/odu_base" "addons/odu_book" "ODUSPHERE.md")

FROM=""
while [ $# -gt 0 ]; do
  case "$1" in
    --from) FROM="${2:-}"; shift 2 ;;
    --from=*) FROM="${1#--from=}"; shift ;;
    -h|--help) sed -n '2,30p' "$0"; exit 0 ;;
    *) echo "✗ Unknown argument: $1" >&2; exit 1 ;;
  esac
done

cd "$(git rev-parse --show-toplevel)"

# Refuse a dirty tree — we are about to create a merge commit.
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "✗ Working tree has uncommitted changes. Commit or stash them first." >&2
  exit 1
fi

# Upstream remote must exist.
if ! git remote get-url "$UPSTREAM_REMOTE" >/dev/null 2>&1; then
  echo "✗ Remote '$UPSTREAM_REMOTE' not found. Add it with:" >&2
  echo "    git remote add $UPSTREAM_REMOTE git@github.com:oduist/odusphere.git" >&2
  exit 1
fi

# Register the merge drivers referenced by .gitattributes (idempotent; they live
# in .git/config and cannot be committed) so the first post-link update is clean.
git config merge.ours.driver true
git config merge.ours.name "Keep our version on conflict"
git config merge.theirs.driver 'cp -f "%B" "%A"'
git config merge.theirs.name "Always take upstream's version"

echo "→ Fetching $UPSTREAM_REMOTE/$UPSTREAM_BRANCH ..."
git fetch "$UPSTREAM_REMOTE" "$UPSTREAM_BRANCH"

# Already linked? Then there is nothing to do.
if git merge-base "$UPSTREAM_REMOTE/$UPSTREAM_BRANCH" HEAD >/dev/null 2>&1; then
  echo "✓ A shared history already exists — nothing to link."
  echo "  Just run ./scripts/update-from-upstream.sh to update."
  exit 0
fi

UPSTREAM_TIP="$(git rev-parse "$UPSTREAM_REMOTE/$UPSTREAM_BRANCH")"

# Resolve the pin: explicit --from, else auto-detect.
PIN=""
if [ -n "$FROM" ]; then
  if ! PIN="$(git rev-parse --verify --quiet "${FROM}^{commit}")"; then
    echo "✗ --from '$FROM' is not a valid commit/ref." >&2
    exit 1
  fi
  if ! git merge-base --is-ancestor "$PIN" "$UPSTREAM_REMOTE/$UPSTREAM_BRANCH"; then
    echo "✗ --from '$FROM' ($PIN) is not part of $UPSTREAM_REMOTE/$UPSTREAM_BRANCH history." >&2
    echo "  Pick a commit/tag that exists upstream." >&2
    exit 1
  fi
else
  echo "→ Auto-detecting the copy point (newest upstream commit whose core matches this sphere) ..."
  while IFS= read -r c; do
    if git diff --quiet "$c" HEAD -- "${CORE_PATHS[@]}"; then
      PIN="$c"
      break
    fi
  done < <(git rev-list "$UPSTREAM_REMOTE/$UPSTREAM_BRANCH")

  if [ -z "$PIN" ]; then
    echo "✗ Could not auto-detect the copy point: no upstream commit has the same" >&2
    echo "  core files (${CORE_PATHS[*]}) as this sphere." >&2
    echo "  Re-run with the upstream ref you copied from, e.g.:" >&2
    echo "    ./scripts/link-upstream-history.sh --from <ref>" >&2
    exit 1
  fi
fi

SHORT="$(git rev-parse --short "$PIN")"
echo "→ Using pin: $SHORT  ($(git log -1 --format='%s' "$PIN"))"

if [ "$PIN" = "$UPSTREAM_TIP" ]; then
  echo "⚠ The pin is the current upstream TIP. This declares the sphere already" >&2
  echo "  up to date and will SKIP any upstream changes made before now. Only" >&2
  echo "  proceed if this sphere already contains them. Ctrl-C to abort; continuing in 5s..." >&2
  sleep 5
fi

echo "→ Recording shared ancestor via: git merge -s ours --allow-unrelated-histories $SHORT"
git merge -s ours --allow-unrelated-histories --no-edit \
  -m "chore: link upstream history (base $SHORT) for clean future merges" \
  "$PIN"

# Verify it worked.
if git merge-base "$UPSTREAM_REMOTE/$UPSTREAM_BRANCH" HEAD >/dev/null 2>&1; then
  echo "✓ Linked. Future merges are now clean 3-way merges."
  echo "  Next: ./scripts/update-from-upstream.sh"
else
  echo "✗ Linking failed — no merge-base after the merge. Please inspect manually." >&2
  exit 1
fi

#!/usr/bin/env bash
#
# update-from-upstream.sh
#
# Pull the latest template from the `upstream` remote into this sphere, keeping a
# clean separation between what upstream owns and what the sphere owns.
#
# How conflicts are minimized (see scripts/README.md for the full model):
#   * A committed .gitattributes marks sphere-owned files `merge=ours`, so git
#     auto-keeps OUR version on a content conflict (website/, README.md, the
#     sphere maps, etc.). This script registers the `ours` merge driver first
#     (it lives in .git/config and cannot be committed).
#   * Files upstream ADDS under a fully sphere-owned directory are a clean add,
#     NOT a conflict — the driver can't catch them — so we prune them here.
#   * A real shared merge-base makes the merge a proper 3-way; without one git
#     degrades to a 2-way merge and conflicts on every file upstream touched.
#     If there is no base we warn and point at scripts/link-upstream-history.sh.
#
#   Usage:
#     ./scripts/update-from-upstream.sh
#     ./scripts/update-from-upstream.sh --branch 19.0          # track a version branch
#     UPSTREAM_BRANCH=19.0 ./scripts/update-from-upstream.sh    # same, via env
#     ./scripts/update-from-upstream.sh --remote template       # different remote name
#
set -euo pipefail

# Upstream remote/branch are configurable via env vars or flags (flags win).
UPSTREAM_REMOTE="${UPSTREAM_REMOTE:-upstream}"
UPSTREAM_BRANCH="${UPSTREAM_BRANCH:-main}"
# Directories the sphere fully owns: their files are forced back to OURS and any
# files upstream added under them are dropped. Add more here if needed.
OWNED_DIRS=("website")

while [ $# -gt 0 ]; do
  case "$1" in
    --remote) UPSTREAM_REMOTE="${2:?--remote needs a value}"; shift 2 ;;
    --remote=*) UPSTREAM_REMOTE="${1#--remote=}"; shift ;;
    --branch) UPSTREAM_BRANCH="${2:?--branch needs a value}"; shift 2 ;;
    --branch=*) UPSTREAM_BRANCH="${1#--branch=}"; shift ;;
    -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
    *) echo "✗ Unknown argument: $1" >&2; exit 1 ;;
  esac
done

# Always operate from the repository root.
cd "$(git rev-parse --show-toplevel)"

# 1. Refuse to run with a dirty working tree (untracked / ignored files are OK).
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "✗ Working tree has uncommitted changes. Commit or stash them first." >&2
  exit 1
fi

# 2. Make sure the upstream remote exists.
if ! git remote get-url "$UPSTREAM_REMOTE" >/dev/null 2>&1; then
  echo "✗ Remote '$UPSTREAM_REMOTE' not found. Add it with:" >&2
  echo "    git remote add $UPSTREAM_REMOTE git@github.com:oduist/odusphere.git" >&2
  exit 1
fi

# 3. Register the merge drivers referenced by .gitattributes. They cannot be
#    committed (they live in .git/config), so set them idempotently on every run.
#    Plain `git config` writes the shared config — correct across worktrees; do
#    NOT use --worktree or the drivers won't apply elsewhere / in CI.
#    ours   -> keep the sphere's version (sphere-owned files).
#    theirs -> take upstream's version (upstream-owned core modules).
git config merge.ours.driver true
git config merge.ours.name "Keep our version on conflict"
git config merge.theirs.driver 'cp -f "%B" "%A"'
git config merge.theirs.name "Always take upstream's version"

echo "→ Fetching $UPSTREAM_REMOTE/$UPSTREAM_BRANCH ..."
git fetch "$UPSTREAM_REMOTE" "$UPSTREAM_BRANCH"

# Remember our current commit — the source of truth for the OWNED_DIRS.
OURS="$(git rev-parse HEAD)"

# Nothing to do if upstream is already part of our history.
if git merge-base --is-ancestor "$UPSTREAM_REMOTE/$UPSTREAM_BRANCH" HEAD; then
  echo "✓ Already up to date with $UPSTREAM_REMOTE/$UPSTREAM_BRANCH."
  exit 0
fi

# 4. Decide the merge strategy from whether a shared history exists.
MERGE_FLAGS=""
if git merge-base "$UPSTREAM_REMOTE/$UPSTREAM_BRANCH" HEAD >/dev/null 2>&1; then
  echo "→ Shared history found — performing a clean 3-way merge."
else
  echo "⚠ No shared history with $UPSTREAM_REMOTE/$UPSTREAM_BRANCH (unrelated histories)." >&2
  echo "  Every file upstream changed will likely conflict in this degraded mode." >&2
  echo "  Run ONCE to fix this permanently, then re-run me:" >&2
  echo "    ./scripts/link-upstream-history.sh --from <upstream-ref-you-copied-from>" >&2
  echo "→ Proceeding in degraded 2-way mode (--allow-unrelated-histories) ..." >&2
  MERGE_FLAGS="--allow-unrelated-histories"
fi

echo "→ Merging $UPSTREAM_REMOTE/$UPSTREAM_BRANCH (sphere-owned files auto-kept via .gitattributes) ..."
# A non-zero exit here just means there are conflicts — handle them below.
# shellcheck disable=SC2086  # MERGE_FLAGS is intentionally word-split (may be empty).
git merge --no-commit --no-ff $MERGE_FLAGS \
  "$UPSTREAM_REMOTE/$UPSTREAM_BRANCH" || true

# 5. Force every OWNED_DIR back to OUR version. `merge=ours` already resolves
#    content conflicts there; this also covers the residual the driver cannot:
#    files upstream ADDED under the dir that we never had (clean adds).
echo "→ Restoring sphere-owned directories: ${OWNED_DIRS[*]} ..."
for dir in "${OWNED_DIRS[@]}"; do
  # a) overwrite tracked files (and resolve any conflicts) with our version
  git checkout "$OURS" -- "$dir" 2>/dev/null || true
  # b) drop files upstream ADDED under $dir that we never had (e.g. scaffold
  #    .gitkeep / dist files). Untracked files (node_modules, .env) are never
  #    listed by `git ls-files`, so they stay safe.
  while IFS= read -r f; do
    [ -z "$f" ] && continue
    if ! git cat-file -e "$OURS:$f" 2>/dev/null; then
      git rm -f --quiet --ignore-unmatch -- "$f"
    fi
  done < <(git ls-files -- "$dir")
done

# 6. If conflicts remain, stop and let a human resolve them before committing.
#    --diff-filter=U includes modify/delete (tree) conflicts the content driver
#    cannot touch.
conflicts="$(git diff --name-only --diff-filter=U)"
if [ -n "$conflicts" ]; then
  echo "✗ Conflicts remain. Resolve them, then run 'git commit':" >&2
  echo "$conflicts" | sed 's/^/    /' >&2
  echo "  (Files here are either not covered by a merge=ours rule, or are" >&2
  echo "   modify/delete conflicts. If you see core/contract files you never" >&2
  echo "   edited, you are likely in degraded mode — see link-upstream-history.sh.)" >&2
  exit 1
fi

# 7. Commit the merge.
git commit --no-edit
echo "✓ Updated from $UPSTREAM_REMOTE/$UPSTREAM_BRANCH — sphere-owned files kept ours."

#!/usr/bin/env bash
#
# update-from-upstream.sh
#
# Pull the latest template from the `upstream` remote into this repository,
# always keeping OUR own `website/` directory and discarding whatever the
# template ships under `website/`.
#
# Everything outside `website/` is taken from upstream as a normal merge.
#
#   Usage:  ./scripts/update-from-upstream.sh
#
set -euo pipefail

UPSTREAM_REMOTE="upstream"
UPSTREAM_BRANCH="main"
PROTECTED_DIR="website"   # this directory always stays ours

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

echo "→ Fetching $UPSTREAM_REMOTE/$UPSTREAM_BRANCH ..."
git fetch "$UPSTREAM_REMOTE" "$UPSTREAM_BRANCH"

# Remember our current commit — this is the source of truth for $PROTECTED_DIR/.
OURS="$(git rev-parse HEAD)"

# Nothing to do if upstream is already part of our history.
if git merge-base --is-ancestor "$UPSTREAM_REMOTE/$UPSTREAM_BRANCH" HEAD; then
  echo "✓ Already up to date with $UPSTREAM_REMOTE/$UPSTREAM_BRANCH."
  exit 0
fi

echo "→ Merging $UPSTREAM_REMOTE/$UPSTREAM_BRANCH (conflicts inside $PROTECTED_DIR/ are expected) ..."
# A non-zero exit here just means there are conflicts — handle them below.
git merge --no-commit --no-ff --allow-unrelated-histories \
  "$UPSTREAM_REMOTE/$UPSTREAM_BRANCH" || true

# 3. Force $PROTECTED_DIR/ back to OUR version, no matter what upstream did.
echo "→ Restoring our own $PROTECTED_DIR/ ..."
#   a) overwrite tracked files (and resolve any conflicts) with our version
git checkout "$OURS" -- "$PROTECTED_DIR"
#   b) drop files upstream ADDED under $PROTECTED_DIR/ that we never had
#      (e.g. scaffold .gitkeep / dist files). node_modules etc. are untracked,
#      so `git ls-files` never lists them — they are safe.
while IFS= read -r f; do
  [ -z "$f" ] && continue
  if ! git cat-file -e "$OURS:$f" 2>/dev/null; then
    git rm -f --quiet --ignore-unmatch -- "$f"
  fi
done < <(git ls-files -- "$PROTECTED_DIR")

# 4. If conflicts remain (they can only be OUTSIDE $PROTECTED_DIR/), stop and
#    let a human resolve them before committing.
conflicts="$(git diff --name-only --diff-filter=U)"
if [ -n "$conflicts" ]; then
  echo "✗ Conflicts remain outside $PROTECTED_DIR/. Resolve them, then run 'git commit':" >&2
  echo "$conflicts" | sed 's/^/    /' >&2
  exit 1
fi

# 5. Commit the merge.
git commit --no-edit
echo "✓ Updated from $UPSTREAM_REMOTE/$UPSTREAM_BRANCH — $PROTECTED_DIR/ kept ours."

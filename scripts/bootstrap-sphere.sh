#!/usr/bin/env bash
#
# bootstrap-sphere.sh
#
# Create a NEW sphere as a CLONE of the template so it shares git history with
# upstream from day one. This is the recommended way to start a sphere: every
# future `git merge upstream/main` is then a clean 3-way merge — no
# `--allow-unrelated-histories`, no link-upstream-history.sh needed.
#
# (The old way — `git init` + copying files — produces unrelated histories and
# painful merges. Prefer this script for new spheres.)
#
#   Usage:
#     ./scripts/bootstrap-sphere.sh <target-dir> <sphere-origin-url>
#
#   Example:
#     ./scripts/bootstrap-sphere.sh acme-sphere git@github.com:acme/odusphere.git
#
set -euo pipefail

TEMPLATE_URL="git@github.com:oduist/odusphere.git"
TEMPLATE_BRANCH="main"

TARGET="${1:-}"
ORIGIN_URL="${2:-}"

if [ -z "$TARGET" ] || [ -z "$ORIGIN_URL" ]; then
  sed -n '2,20p' "$0"
  exit 1
fi
if [ -e "$TARGET" ]; then
  echo "✗ '$TARGET' already exists. Choose a fresh directory name." >&2
  exit 1
fi

echo "→ Cloning template into '$TARGET' ..."
git clone --branch "$TEMPLATE_BRANCH" "$TEMPLATE_URL" "$TARGET"

cd "$TARGET"

echo "→ Wiring remotes (template -> 'upstream', your repo -> 'origin') ..."
git remote rename origin upstream
git remote add origin "$ORIGIN_URL"

echo "→ Registering the merge drivers (used by .gitattributes on updates) ..."
git config merge.ours.driver true
git config merge.ours.name "Keep our version on conflict"
git config merge.theirs.driver 'cp -f "%B" "%A"'
git config merge.theirs.name "Always take upstream's version"

echo "→ Pushing initial history to your origin ..."
git push -u origin "$TEMPLATE_BRANCH"

cat <<EOF

✓ Sphere '$TARGET' is ready and shares history with the template.

  Remotes:
    origin   -> $ORIGIN_URL        (your sphere)
    upstream -> $TEMPLATE_URL       (the template)

  To pull future template updates (clean 3-way merges):
    cd $TARGET && ./scripts/update-from-upstream.sh

  Next: build this sphere's own odu_* modules and document them in
  .docs/architecture.local.md (NOT .docs/architecture.md, which is upstream-owned).
EOF

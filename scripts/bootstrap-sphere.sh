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
#     ./scripts/bootstrap-sphere.sh --branch 19.0 <target-dir> <sphere-origin-url>
#
#   The template URL and branch are configurable via env vars or flags (flags win):
#     TEMPLATE_URL, TEMPLATE_BRANCH  /  --template-url <url>, --branch <name>
#
#   Example:
#     ./scripts/bootstrap-sphere.sh acme-sphere git@github.com:acme/odusphere.git
#
set -euo pipefail

TEMPLATE_URL="${TEMPLATE_URL:-git@github.com:oduist/odusphere.git}"
TEMPLATE_BRANCH="${TEMPLATE_BRANCH:-main}"

POSITIONAL=()
while [ $# -gt 0 ]; do
  case "$1" in
    --branch) TEMPLATE_BRANCH="${2:?--branch needs a value}"; shift 2 ;;
    --branch=*) TEMPLATE_BRANCH="${1#--branch=}"; shift ;;
    --template-url) TEMPLATE_URL="${2:?--template-url needs a value}"; shift 2 ;;
    --template-url=*) TEMPLATE_URL="${1#--template-url=}"; shift ;;
    -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
    -*) echo "✗ Unknown argument: $1" >&2; exit 1 ;;
    *) POSITIONAL+=("$1"); shift ;;
  esac
done
TARGET="${POSITIONAL[0]:-}"
ORIGIN_URL="${POSITIONAL[1]:-}"

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

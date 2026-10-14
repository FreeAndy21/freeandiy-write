#!/usr/bin/env bash
# Modified-by: FreeANDIY (Free Andy Agency), 2026. New file, not part of upstream.
#
# Pull the latest upstream into this FreeANDIY app.
#
#   freeandiy/scripts/sync-upstream.sh [--no-test] [--push]
#
# 1. fetch `upstream` (the [apps.<app>].upstream repository) and fast-forward the `upstream-main` branch to it
# 2. regenerate `main` = new upstream + freeandiy/ (freeandiy/scripts/regenerate.sh)
# 3. check branding, build, and run the tests of the crates the branding touches
# 4. with --push: push `upstream-main` and `main` to origin (plain pushes, never forced)
#
# When a patch or rule no longer fits the new upstream, step 2 stops and names it; fix it in
# freeandiy/ (see freeandiy/docs/upstream-sync.md), commit, and run this script again.
set -euo pipefail

TEST=1 PUSH=0
for a in "$@"; do
  case "$a" in
    --no-test) TEST=0 ;;
    --push) PUSH=1 ;;
    *) echo "unknown option $a" >&2; exit 2 ;;
  esac
done

. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
cd "$ROOT"
[ "$(git rev-parse --abbrev-ref HEAD)" = main ] || { echo "error: run on main" >&2; exit 1; }
git remote get-url upstream >/dev/null 2>&1 || git remote add upstream "https://github.com/$(fa_get this.upstream).git"

echo "==> fetch upstream"
git fetch --quiet upstream
OLD="$(git rev-parse upstream-main)"
NEW="$(git rev-parse upstream/main)"
if ! git merge-base --is-ancestor "$OLD" "$NEW"; then
  echo "error: upstream/main is not a fast-forward of upstream-main (upstream rewrote history?); ask before resetting it" >&2
  exit 1
fi
git branch --force upstream-main "$NEW"
echo "    upstream-main: $(git rev-parse --short "$OLD") -> $(git rev-parse --short "$NEW") ($(git rev-list --count "$OLD..$NEW") new commits)"

echo "==> regenerate main"
freeandiy/scripts/regenerate.sh upstream-main

echo "==> check branding"
freeandiy/scripts/check-branding.sh

if [ "$TEST" = 1 ]; then
  echo "==> build and test"
  # shellcheck disable=SC2046 # the settings are cargo argument lists
  cargo build --release --locked $(fa_get build.bins) $(fa_get build.features "")
  # shellcheck disable=SC2046
  env $(fa_get build.test_env "") cargo test --locked $(fa_get build.tests) --lib --tests
fi

if [ "$PUSH" = 1 ]; then
  echo "==> push"
  git push origin upstream-main main
fi
echo "done: main = upstream $(git rev-parse --short "$NEW") + freeandiy/"

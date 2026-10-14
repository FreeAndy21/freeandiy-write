#!/usr/bin/env bash
# Modified-by: FreeANDIY (Free Andy Agency), 2026. New file, not part of upstream.
#
# Fail if upstream branding leaks into what FreeANDIY ships.
#
#   freeandiy/scripts/check-branding.sh [BINARY_OR_DIR ...]
#
# 1. Source: no ArtCraft / storyteller / getartcraft / Discord / "Crafting Apps" outside the
#    allowed places (licences, NOTICE, ATTRIBUTION, upstream's developer docs, the attribution
#    text), and no upstream product name (this.upstream_name) in what users read (UI code
#    strings, translations, packaging, the web page).
# 2. Artifacts (optional arguments): the same terms in the strings of built binaries, packages
#    or the web build. Only the attribution sentence may name ArtCraft and the upstream app.
# Per-app exceptions: [check] in freeandiy/app.toml.
set -euo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
cd "$ROOT"
fail=0

UP="$(fa_get this.upstream_name)"
TEMPLATE_OUT="$(fa_get check.template crates/ui-egui/src/freeandiy.rs)"
WEB_INDEX="$(fa_get build.web_index "")"
EXTRA_ALLOW="$(fa_get check.allow "")"
read -r -a RS_EXCLUDE <<<"$(fa_get check.rs_exclude ":!xtask/**")"

BANNED='ArtCraft|artcraft|storyteller|getartcraft|discord\.gg|Crafting Apps'
# Allowed mentions: the About attribution (English and translated), upstream's copyright line, upstream's
# credit for its own work, and app-specific fixtures (check.allow).
ALLOWED_STRINGS="based on the open-source project|affiliated with the ArtCraft team|ArtCraft Team and contributors|ArtCraft Team a prispievatelia|ArtCraft Team and the $UP (contributors|authors)|the $UP authors|$UP.s own|^$UP\$"
[ -n "$EXTRA_ALLOW" ] && ALLOWED_STRINGS="$ALLOWED_STRINGS|$EXTRA_ALLOW"
# Where upstream's names may appear: licences and notices (must stay), upstream's developer
# docs (not shipped), credits, code comments about upstream work, and our own freeandiy/ sources.
# xtask/ is upstream's developer tooling (never shipped).
ALLOW=(':!NOTICE' ':!LICENSE-*' ':!**/LICENSE*' ':!ATTRIBUTION.md' ':!ATTRIBUTION.toml' ':!docs/**' ':!book/**' ':!*.md'
  ':!contributors/**' ':!freeandiy/**' ":!$TEMPLATE_OUT" ':!xtask/**')

echo "== source: upstream brand terms"
if hits="$(git grep -n -I -E "$BANNED" -- . "${ALLOW[@]}" | grep -v -E '^[^:]+:[0-9]+:\s*(//|#|<!--|\*)' | grep -v -E "$ALLOWED_STRINGS" || true)" && [ -n "$hits" ]; then
  echo "$hits" | head -50
  echo "FAIL: upstream brand terms above (remove them or add a rule in freeandiy/rules.toml)"
  fail=1
else
  echo "ok"
fi

echo "== source: product name in user-facing files"
# Translations (not comments), packaging, the web page, Rust string literals (not comments).
web=()
[ -n "$WEB_INDEX" ] && web=("$WEB_INDEX")
hits="$(
  {
    git grep -n -I "$UP" -- '**/i18n/*.tsv' | grep -v -E '^[^:]+:[0-9]+:#' || true
    git grep -n -I "$UP" -- packaging "${web[@]}" ':!*.md' | grep -v -E "the $UP authors" || true
    git grep -n -I -E "\"[^\"]*$UP[^\"]*\"" -- '*.rs' "${RS_EXCLUDE[@]}" ':!freeandiy/**' ":!$TEMPLATE_OUT" \
      | grep -v -E '^[^:]+:[0-9]+:\s*//' | grep -v -E "the $UP authors" || true
  } | { grep -v -E "$ALLOWED_STRINGS" || true; } | sort -u
)"
if [ -n "$hits" ]; then
  echo "$hits" | head -50
  echo "FAIL: '$UP' where users can read it"
  fail=1
else
  echo "ok"
fi

for target in "$@"; do
  echo "== artifact: $target"
  files=()
  if [ -d "$target" ]; then
    while IFS= read -r -d '' f; do files+=("$f"); done < <(find "$target" -type f \( -perm -u+x -o -name '*.wasm' -o -name '*.js' -o -name '*.html' -o -name '*.plist' -o -name '*.desktop' -o -name '*.xml' -o -name '*.json' -o -name '*.exe' -o -name '*.dll' \) -print0)
  else
    files=("$target")
  fi
  bad=0
  for f in "${files[@]}"; do
    hits="$(strings -n 6 "$f" 2>/dev/null | grep -E "$BANNED|$UP" | grep -v -E "$ALLOWED_STRINGS" | sort -u | head -20 || true)"
    if [ -n "$hits" ]; then
      echo "  $f:"
      echo "$hits" | sed 's/^/    /' | cut -c1-200
      bad=1
    fi
  done
  if [ "$bad" = 1 ]; then
    echo "FAIL: upstream branding in $target"
    fail=1
  else
    echo "ok (${#files[@]} file(s))"
  fi
done

exit "$fail"

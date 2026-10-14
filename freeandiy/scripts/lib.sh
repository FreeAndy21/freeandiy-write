# Modified-by: FreeANDIY (Free Andy Agency), 2026. New file, not part of upstream.
# Shared by the freeandiy/scripts: builds the rebrand tool and reads settings.
#   . "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
ROOT="$(git rev-parse --show-toplevel)"
REBRAND="$ROOT/freeandiy/tools/rebrand/target/release/freeandiy-rebrand"
cargo build --quiet --release --manifest-path "$ROOT/freeandiy/tools/rebrand/Cargo.toml"

# fa_get KEY [DEFAULT]: a value from freeandiy/branding.toml + app.toml (see `rebrand vars`).
fa_get() {
  local v
  if v="$("$REBRAND" get "$1" "$ROOT" 2>/dev/null)"; then
    printf '%s\n' "$v"
  elif [ $# -ge 2 ]; then
    printf '%s\n' "$2"
  else
    echo "error: freeandiy setting $1 missing (app.toml / branding.toml)" >&2
    return 1
  fi
}

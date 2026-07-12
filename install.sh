#!/usr/bin/env bash
# EDS — selective manual install. Thin wrapper over scripts/build-packs.js
# for anyone installing outside the Claude Code marketplace flow (a
# non-plugin-aware harness, or a deliberately slimmed-down local copy).
#
# Usage:
#   ./install.sh --list
#   ./install.sh --profile core --out ~/eds-install
#   ./install.sh --profile full --with production:model-governance,domains:credit-risk --out ~/eds-install
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if ! command -v node >/dev/null 2>&1; then
  echo "install.sh requires node on PATH" >&2
  exit 1
fi

node "$SCRIPT_DIR/scripts/build-packs.js" "$@"

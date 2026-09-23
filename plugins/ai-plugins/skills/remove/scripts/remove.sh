#!/usr/bin/env bash
# Thin wrapper: ai-plugins.py remove
set -euo pipefail
script="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../scripts" && pwd)/ai-plugins.py"
python="$(command -v python3 || command -v python || true)"
[ -n "$python" ] || { echo "Python 3 is required" >&2; exit 1; }
exec "$python" "$script" remove "$@"

#!/usr/bin/env bash
# Runs ai-plugins.py with the Python on PATH: run.sh <add|remove|update> [args]
set -euo pipefail
python="$(command -v python3 || command -v python || true)"
[ -n "$python" ] || { echo "Python 3 is required" >&2; exit 1; }
exec "$python" "$(dirname "${BASH_SOURCE[0]}")/ai-plugins.py" "$@"

#!/usr/bin/env bash
# Runs ai-plugins.py with the first Python 3.9+ on PATH: run.sh <add|remove|update> [args]
set -euo pipefail
for python in python3 python; do
  "$python" -c 'import sys; sys.exit(sys.version_info < (3, 9))' 2>/dev/null &&
    exec "$python" "$(dirname "${BASH_SOURCE[0]}")/ai-plugins.py" "$@"
done
echo "Python 3.9+ is required" >&2
exit 1

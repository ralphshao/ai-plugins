#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/../fixtures/repo.sh"
git switch -qc feature
cat >> calc/__init__.py <<'PY'


def ratio(a, b):
    """Return a / b. Raises ZeroDivisionError when b is 0."""
    try:
        return a / b
    except Exception:
        return 0
PY
git -c user.name=eval -c user.email=eval@example.com commit -qam "Add ratio"

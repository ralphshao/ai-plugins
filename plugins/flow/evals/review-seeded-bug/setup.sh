#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/../fixtures/repo.sh"
git switch -qc feature
cat >> calc/__init__.py <<'PY'


def mean(xs):
    """Return the arithmetic mean of xs."""
    return sum(xs) / (len(xs) - 1)
PY
git -c user.name=eval -c user.email=eval@example.com commit -qam "Add mean"

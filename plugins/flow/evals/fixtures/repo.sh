#!/usr/bin/env bash
# Seed a tiny Python repo with a passing test suite. Sourced by each case's
# scaffold script, which runs in the empty eval workspace.
set -euo pipefail
mkdir -p calc tests
cat > calc/__init__.py <<'PY'
def add(a, b):
    """Retrun the sum of a and b."""
    return a + b


def divide(a, b):
    return a / b
PY
cat > tests/test_calc.py <<'PY'
from calc import add, divide


def test_add():
    assert add(2, 3) == 5


def test_divide():
    assert divide(6, 3) == 2
PY
printf '# calc\n\nRun tests: `python3 -m pytest -q`\n' > README.md
git init -q -b main
git -c user.name=eval -c user.email=eval@example.com add -A
git -c user.name=eval -c user.email=eval@example.com commit -qm "initial"

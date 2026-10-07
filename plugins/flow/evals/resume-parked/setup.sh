#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/../fixtures/repo.sh"
git checkout -qb flow/divide-by-zero
mkdir -p .flow/divide-by-zero
cat > .flow/divide-by-zero/plan.md <<'MD'
# Divide by zero

## Goal
divide(a, 0) fails with a clear error instead of ZeroDivisionError.

## Acceptance criteria
- divide(1, 0) raises with the message "cannot divide by zero"

## Seams under test
- calc.divide - catches: the error type and message / misses: callers

## Steps
- [ ] Raise the agreed exception from divide

## Test command
`python3 -m pytest -q`

## Out of scope
- other operations

## Decisions

## Open questions
- [ ] Q1 Raise ValueError or a custom CalcError? - recommended: ValueError - blocks: 1

## Status
Approved - building
MD
git -c user.name=eval -c user.email=eval@example.com add -A
git -c user.name=eval -c user.email=eval@example.com commit -qm "flow: plan divide-by-zero"

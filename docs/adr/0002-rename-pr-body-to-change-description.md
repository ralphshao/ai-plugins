# 2. Rename flow's `pr-body` skill to `change-description`

Status: accepted (#8, 2026-10-08)

## Context

After [ADR 1](0001-flow-vcs-and-review-host-layers.md), the review-body
template serves GitHub pull requests, Swarm reviews, and Perforce changelist
descriptions. The name `pr-body` described only the first.

## Decision

Rename the skill to `change-description`: the field every host has (PR
description, review description, changelist description).

## Alternatives

- **Keep `pr-body`.** Rejected: misleading in Perforce workspaces.
- **`review-body`.** Rejected: reads as "review a body", not "write the
  description".
- **`describe-change`, `change-summary`.** Rejected: a verb name sits oddly
  among the noun-named skills, and the template covers more than a summary
  (evidence, merge danger, decisions).

## Consequences

`/flow:pr-body` no longer exists; anyone invoking it by name must use
`/flow:change-description`. Flow's version moved from 0.1.0 to 0.2.0 in the
same change.

# 2. Rename flow's `pr-body` skill to `change-body`

Status: accepted (#8, #9, 2026-10-08)

## Context

After [ADR 1](0001-flow-vcs-and-review-host-layers.md), the review-body
template serves GitHub pull requests, Swarm reviews, and Perforce changelist
descriptions. The name `pr-body` described only the first.

## Decision

Rename the skill to `change-body`: the body of a change, whatever the host
calls it (PR body, review description, changelist description). #8 first
shipped it as `change-description` in flow 0.2.0; #9 shortened it to
`change-body` in 0.2.1.

## Alternatives

- **Keep `pr-body`.** Rejected: misleading in Perforce workspaces.
- **`change-description`.** Shipped in 0.2.0, then replaced: longer, and
  "body" is the term people already use for PR and commit text.
- **`review-body`.** Rejected: reads as "review a body", not "write the
  body".
- **`describe-change`, `change-summary`.** Rejected: a verb name sits oddly
  among the noun-named skills, and the template covers more than a summary
  (evidence, merge danger, decisions).

## Consequences

`/flow:pr-body` (0.1.0) and `/flow:change-description` (0.2.0) no longer
exist; invoke `/flow:change-body`. Flow moved to 0.2.1 for the second rename.

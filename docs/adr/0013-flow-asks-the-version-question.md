# 13. flow asks the version question

Status: accepted (2026-10-15)

Refines [ADR 9](0009-gate-approval-and-version-bumps-are-explicit.md).

## Context

ADR 9 stops the agent from bumping a version nobody asked for. It doesn't
make anyone ask. PR #24 changed flow's behavior and merged with flow still
at 0.2.5: no one raised the version, so `claude plugin update` may not
deliver the change.

## Decision

When a task touches a versioned package (`plugin.json`, `package.json`,
and the like), flow asks about the version twice.

- **GATE 1, intent.** The plan gets a `## Version` line, and the gate asks
  "<pkg> is at X. Bump to what at ship, or none?" The answer goes into the
  plan as intent.
- **Ship, the go.** Before the review is readied, ship re-confirms the
  intent ("Still bump <pkg> to Y?", or "Still no bump?" for none). It
  changes the number only on a yes with the number. If the diff touches a
  versioned package and the plan has no Version line, ship asks fresh.
- **Trivial tasks** have no gates, so the final report asks the question.

ADR 9's rule stands: a bump listed in the plan is not a go.

## Alternatives

- **Ask only at ship.** Rejected. The user wants to state intent while
  scope is being decided, and a fresh question at the end is easy to wave
  through.
- **Take the GATE 1 answer as the go.** Rejected by ADR 9: the build can
  change what the release should be.
- **Skip the ship question for "none".** Rejected. A silent no-bump is the
  PR #24 failure.

## Consequences

- One more question at GATE 1 and at ship, only for tasks that touch a
  versioned package.

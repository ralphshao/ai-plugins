# 2. Between gates, flow escalates on concrete triggers and parks the question

Status: accepted (#7, 2026-10-07; recorded in #11)

## Context

[ADR 1](0001-flow-sized-phases-and-two-human-gates.md) has the agent work
unattended between GATE 1 and GATE 2. Decisions the plan didn't foresee
still come up during build and ship. An agent's own sense of confidence is
a poor signal for which of them need the user, and stopping on every
question would undo the point of working unattended.

## Decision

The agent escalates (asks the user) when any of these hold, and decides
otherwise:

- The plan doesn't cover the decision, or the code contradicts the plan.
- It changes scope or acceptance criteria.
- It is a one-way door: public API, schema or migration, data deletion,
  security or auth, a new dependency.
- Two or more plausible options differ in user-visible behavior.
- A test or review result shows a requirement is ambiguous.
- `review-validator` returns UNSURE on a high-severity finding.

[ADR 9](0009-gate-approval-and-version-bumps-are-explicit.md) later added
version changes to this list.

A decision the agent makes alone gets a line under `## Decisions` in
`plan.md` with a one-line reason. `ship` copies the list into the change
body, so the user reviews every unattended decision at GATE 2.

Escalation is park-and-continue:

1. Add the question under `## Open questions` in `plan.md`, with a
   recommended answer worded so "yes" accepts it and the steps it blocks.
   Save it with the work, then ask in chat.
2. Send a push notification where the host has one.
3. Keep working on steps the question doesn't block.
4. Stop only when every remaining step is blocked.
5. On an answer, tick the question, record it under `## Decisions`, and
   unblock its steps. An answer written into `plan.md` directly counts, so
   a task resumed elsewhere picks it up.

## Alternatives

- **Escalate when the agent feels unsure.** Rejected: self-rated
  confidence is unreliable in both directions.
- **Stop and wait on every question.** Rejected: one question would idle
  the whole task.

## Consequences

- The stop-time test gate must let a parked task stop
  ([ADR 5](0005-flow-stop-gate-runs-the-plans-tests.md)).
- The trigger list is the contract: a decision that should have been
  escalated but matches no trigger is a gap in the list, fixed by a new
  ADR.

# 4. Gate approval and version bumps are explicit

Status: accepted (#10, 2026-10-08)

## Context

While #10 was being planned, the agent treated the user's answers to the
plan's open questions as GATE 1 approval and started building. It also
took a "do it now" on one question as a go for a version bump. The user
had approved neither. The `plan` skill said "stop and wait for approval",
but didn't say what counts as approval.

## Decision

Only the user can give gate approval or a version bump, and only
explicitly.

- **Gates.** A gate passes only when the user says so for that gate
  ("approved", "build it", "go ahead"). Answering open questions doesn't
  count, even all of them. Neither does a "yes" to another question, or a
  "do it now" about one item. If it's unclear, the agent asks.
- **Versions.** The agent changes a version number only when the user asks
  for that change, gives the number, and says when. A bump listed in a plan
  waits for that go. `ai-plugins:update` copying an upstream plugin's new
  version into the catalog is the exception: running it is the go.

The `flow`, `plan`, and `ship` skills and AGENTS.md's Versions section say
this.

## Alternatives

- **Treat all questions answered as approval.** Rejected. That is the
  mistake this ADR fixes. Answers settle decisions; approval accepts the
  whole plan.
- **Ask only about the version number, not the timing.** Rejected. The
  user wants to choose when a bump lands, not only what it is.

## Consequences

- An extra round trip at each gate when the user's intent seems clear.
- Ship stops on a pending version bump, the same way it stops on an
  unticked open question.

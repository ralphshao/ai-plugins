# 10. The interview runs to completion for Normal tasks too

Status: accepted (#18, 2026-10-09). Supersedes the "adds a full interview"
part of ADR 1's Large size.

## Context

ADR 1 gave Large tasks "a full interview" and, by implication, Normal tasks
a short one. The `plan` skill capped Normal at one round. But the
`interview` skill it calls asks in rounds until no decision is left open,
then confirms. Nothing said what happened to decisions still open after
Normal's single round: they were decided silently, or left to surface
during the build.

## Decision

Normal and Large run the same interview: rounds until no decision is open.
Large still adds ADRs for one-way-door decisions and a `flow:tester` pass
at ship, plus two contrasting approach drafts before the interview.

## Alternatives

- **One round, then defaults shown at GATE 1.** Rejected by the user.
  Decisions that depend on round-1 answers would never be asked, only
  shown as defaults.
- **One round, then park the rest as open questions.** Rejected. Each
  parked question blocks its steps and `ship`, so this is the full
  interview with more waiting.

## Consequences

- A Normal task can take one or two more rounds before GATE 1.
- Normal no longer differs from Large before GATE 1, except for the
  drafts. The difference is ADRs, the drafts, and the tester pass.

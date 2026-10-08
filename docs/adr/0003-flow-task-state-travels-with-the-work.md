# 3. Flow's task state lives in `.flow/<slug>/` and travels with the work

Status: accepted (#7, 2026-10-07; recorded in #11)

## Context

A flow task outlives one session. It may pause at a gate or on an open
question, then resume on another machine or in a cloud session, where
nothing from the first session's memory or `~/.claude` exists.

## Decision

- Each task keeps its state in `.flow/<slug>/`: `brief.md` (the request
  and constraints) and `plan.md` (goal, steps, decisions, open questions,
  status).
- The state is committed on the task's feature branch, so it travels with
  the work to any checkout.
- `/flow` with no argument finds the state and resumes from the plan's
  Status, its first unticked step, and any open questions answered in the
  file since.
- `ship` removes `.flow/<slug>/` in its own commit before the change is
  marked ready, so the state never lands on the default branch.

## Alternatives

- **State in the session or in `~/.claude`.** Rejected: it doesn't reach
  another machine or a cloud session.
- **Keep the plan after merge** (e.g. under `docs/plans/`). Rejected: a
  plan isn't maintained after it is built, and readers keep trusting it.
  Lasting decisions go to `docs/adr/` instead. Flow's own design plan
  showed the problem and was deleted in #11.

## Consequences

- The feature branch's history shows the plan's progress; the default
  branch never sees it.
- [ADR 6](0006-flow-vcs-and-review-host-layers.md) moved saving and
  removing the state behind VCS operations (`checkpoint`, `drop-state`).
  Perforce keeps it in a never-submitted changelist instead of a branch.

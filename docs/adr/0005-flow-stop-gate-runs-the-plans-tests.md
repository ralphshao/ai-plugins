# 5. Flow's stop gate runs the plan's test command

Status: accepted (#7, 2026-10-07; recorded in #11)

## Context

Between gates the agent works unattended
([ADR 1](0001-flow-sized-phases-and-two-human-gates.md)). An agent can end
its turn believing the work is done while tests fail. Asking it to run the
tests is a request it can skip; a Stop hook isn't.

## Decision

`stop_gate.py`, a Stop hook, is active only when the repo has a
`.flow/<slug>/plan.md` whose Status starts with `Approved` and whose
`## Test command` section holds a command. It runs that command, and on
failure blocks the stop with the tail of the output.

It allows the stop when:

- the plan has an unticked item under `## Open questions`: the task is
  parked on the user ([ADR 2](0002-flow-decisions-between-gates.md)), and
  blocking would loop on tests the agent can't fix yet;
- `stop_hook_active` is set: the agent already got one block this turn.

The command comes from the repo's own plan, so the gate runs it with the
same trust as running the tests by hand.

## Alternatives

- **Instructions only** ("run the tests before you stop"). Rejected: not
  enforced.
- **Detect the test command from the repo.** Rejected: the plan already
  names one, reviewed at GATE 1, and detection would guess wrong in mixed
  repos.

## Consequences

- No plan, no approval, or no test command: the gate is off.
- A slow test suite runs at every stop. Later changes skip the run when
  nothing changed since the last pass (in git), and find the plan from a
  Perforce client root
  ([ADR 6](0006-flow-vcs-and-review-host-layers.md)).

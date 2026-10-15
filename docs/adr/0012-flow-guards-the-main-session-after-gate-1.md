# 12. Flow guards the main session after GATE 1

Status: accepted (#21, 2026-10-15)

## Context

The stop gate ([ADR 5](0005-flow-stop-gate-runs-the-plans-tests.md)) blocks
stopping while the plan's tests fail. The guard
([ADR 4](0004-flow-guards-dispatch-by-agent-type.md)) restricts only flow's
subagents, so the main agent could pass the gate by editing the plan's test
command or weakening existing tests. Asking it not to is an instruction it
can skip; a hook isn't.

## Decision

`guard.py` also checks the main session (no `agent_type`) while some
`.flow/<slug>/plan.md` has a Status starting with `Approved` and no plan has
an unticked open question. It blocks:

- an Edit or Write of an approved plan that changes its `## Test command`
  section or takes its Status off `Approved` (ticking steps and adding
  decisions stay allowed);
- an Edit or Write of an existing test file after which any of its old
  lines is gone, duplicates counted. A changed line counts as gone.

New files, additions to existing tests, and source edits pass. Test files
are recognized as the tester guard recognizes them, also in lowercase,
since macOS and Windows open `TESTS/` as `tests/`.

Parking an open question
([ADR 2](0002-flow-decisions-between-gates.md)) lifts the guard: the user
answers, the agent makes the change, then ticks the question. A guard error
fails open for the main session, as before.

## Consequences

- Bash (`sed -i`, `rm`, `git checkout`) and Codex's `apply_patch` can still
  change tests unchecked. Parsing every main-session command is fragile and
  would block ordinary work; the gap is accepted, like the tester's in ADR 4.
- While a question is open, every test edit is allowed, not only the one the
  user approved. Ticking promptly keeps that window short.
- "Existing" means on disk now, so a test the task wrote after GATE 1 is
  guarded too: fixing a new test that fails for the wrong reason takes an
  open question. Telling the task's own tests apart needs git state at the
  approval commit, which wasn't worth the cost.
- Added lines can still weaken a test (`pytest.skip()`, a skip marker).
- Each main-session Edit and Write runs `git rev-parse` to find the plans.

## Alternatives

- Guard Bash too: rejected, see above.
- An override flag in the plan: rejected; the open-question route already
  puts the user in the loop.

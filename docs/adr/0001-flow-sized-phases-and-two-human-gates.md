# 1. Flow sizes each task and runs it through phases with two human gates

Status: accepted (#7, 2026-10-07; recorded in #11)

## Context

We wanted one engineering workflow that runs a task from a prompt or an
issue to a change ready to land, mostly unattended, on Claude Code and
Codex, on any machine or cloud session. A human still has to own two
things an agent can't: what gets built, and whether it lands.

This was decided in the flow design plan (`docs/plans/flow.md`), which #11
deleted once its lasting decisions were recorded here and in ADRs 2-5.

## Decision

- **One entry point.** `/flow <prompt | issue>` sizes the task, says its
  call in one line, and walks it through the phases. With no argument it
  resumes a task in progress.
- **Size by behavior change, not line count.** Trivial: no change a caller
  could notice; done in place, no gates. Normal: a feature or bug fix.
  Large: crosses modules or adds a subsystem; adds a full interview, an ADR
  for each one-way-door decision, and a tester pass. When unsure between
  two sizes, pick the larger. The user can override.
- **Phases:** `start` (isolate, brief), `plan` (explore, interview, plan),
  build (TDD at the plan's seams), `ship` (verify, review, ready the
  change).
- **Two human gates.** GATE 1: the user approves the plan before any code
  is written. GATE 2: the user lands the change. Everything between runs
  unattended, except the escalations in ADR 2. The first gate catches a
  wrong goal while it is cheap to fix; the second keeps landing a human
  act. [ADR 9](0009-gate-approval-and-version-bumps-are-explicit.md) says
  what counts as approval.
- **Orchestrators and disciplines.** Phase skills (`flow`, `start`,
  `plan`, `ship`, `retro`) are user-invoked and orchestrate. Reusable
  discipline (`interview`, `tdd`, `deep-review`, `change-body`) is
  model-invocable. An orchestrator may use a discipline skill, never
  another orchestrator: `/flow` reads a phase's file and follows it.
- **Portable.** No absolute paths, nothing from the user's `~/.claude`,
  stdlib-only Python, Linux, macOS, and Windows. Claude Code and Codex use
  the same skill and hook files
  ([ADR 8](0008-flow-hooks-shared-by-claude-code-and-codex.md)).

## Alternatives

- **One fixed path for every task.** Rejected: gates and a plan file are
  ceremony on a typo, and too little on a new subsystem.
- **Size by lines changed.** Rejected: a one-line change to what a public
  function returns needs a plan; a large docs edit doesn't.
- **Phases calling each other as skills.** Rejected: orchestration would
  spread across skills, and a phase could start another phase's gate.
- **Out of scope for now:** multi-agent parallel implementation of large
  tasks, per-repo setup (glossary, domain docs, triage labels).

## Consequences

- The router's sizing call decides how much ceremony a task gets, so a
  wrong call either skips the gates or wastes a round trip. The user's
  override is the fix.
- GitHub-only in v1. [ADR 6](0006-flow-vcs-and-review-host-layers.md)
  later moved VCS and review-host steps behind skill layers.
- Some skills adapt mattpocock/skills (MIT) and credit it in the skill.

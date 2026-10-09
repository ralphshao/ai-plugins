---
name: plan
description: Second flow phase. Explores the code, interviews the user on open decisions, writes .flow/<slug>/plan.md, and stops at GATE 1 for approval.
disable-model-invocation: true
---

Input: `.flow/<slug>/brief.md` from `start`.

## 1. Explore

Spawn an exploration subagent (`Explore` in Claude Code, `explorer` in
Codex) to find the code the request touches: entry points, callers, existing
tests and their style, the test command, and repo standards files. Ask it
to end with the 5-10 files most worth reading, and read those yourself
before going on. Facts are your job: never ask the user something you can
look up.

Then re-size, as the `flow` skill's "Size the task" section says: now that
you know which modules the change touches and whether it has a one-way
door, the size from the brief may be wrong. A new size changes which of
the steps below run.

## 2. Draft approaches (Large only)

In one message, spawn two planning subagents (`Plan` in Claude Code,
`explorer` in Codex) with the brief and the key files. One drafts the
smallest change that meets the request, reusing what exists; the other
drafts the cleanest structure for it. Each returns its approach: the
files it touches, the shape of the change, and its trade-offs.

Compare the drafts. Each point where they differ is a decision for the
interview, with your recommendation, so the user can take parts of both.
Don't ask the user to pick a whole draft.

## 3. Interview

Use the `interview` skill on the decisions the exploration and the drafts
left open, in rounds until no decision is open. Skip it if nothing is
open. Skip the interview's closing confirmation: GATE 1 shows the decisions
and asks once, so a "yes" to a summary can't pass for approval.

## 4. Write the plan

Write `.flow/<slug>/plan.md`:

```
# <title>

## Goal
<one or two sentences, from the user's point of view>

## Acceptance criteria
- <observable behavior that proves it's done>

## Seams under test
- <public interface> - catches: <what> / misses: <what>

## Steps
- [ ] <small step, one checkpoint>

## Test command
`<one shell command that runs the relevant tests>`

## Out of scope
- <what this change won't do>

## Decisions
- <decision> - <one-line reason>

## Open questions

## Status
Awaiting GATE 1
```

Rules:

- Seams are public interfaces where tests observe behavior. Prefer existing
  seams and the highest one that works; fewer is better. Each gets one line
  on what a test there catches and misses.
- Steps are vertical slices, each small enough for one checkpoint.
- The test command must exist in the repo already. If there isn't one, add
  `No test command in repo - stop-time test gate off` under Decisions and
  leave the Test command section with no lines at all, not even a
  placeholder: the stop-time gate runs its first line as a command.
- Record interview answers under Decisions.
- Large: add one step per one-way-door decision to write its ADR. The
  `flow:tester` pass belongs to `ship` and needs no step.

Checkpoint: `flow: plan <slug>`.

## 5. GATE 1

Re-size first against the written plan, as after exploring: the interview
can grow the scope. Going up adds Large's ADR steps to the plan but not the
drafts, since the design is settled; going down drops them. `checkpoint`
if the size changed.

Show the plan (size, Goal, Acceptance criteria, Seams, Steps, Test command,
Out of scope, Decisions, and Open questions) and ask for approval. Stop and wait. Don't write code before approval.

Approval must be explicit: the user says the plan is approved, or to build
it. Answering open questions, saying "yes" to one of them, or "do it now"
about one item is not approval, even when every question is answered. If
it's unclear, ask whether the plan is approved; never assume it.

On approval:

1. Set Status to `Approved - building`, `checkpoint`.
2. `publish`, then `open-draft`: title from the plan, body linking
   `.flow/<slug>/plan.md` and the issue. If either fails, say so and
   continue locally.

On changes requested: revise the plan, `checkpoint`, and ask again.

---
name: plan
description: Second flow phase. Explores the code, interviews the user on open decisions, writes .flow/<slug>/plan.md, and stops at GATE 1 for approval.
disable-model-invocation: true
---

Input: `.flow/<slug>/brief.md` from `start`.

## 1. Explore

Spawn an exploration subagent (`Explore` in Claude Code, `explorer` in
Codex) to find the code the request touches: entry points, callers, existing
tests and their style, the test command, and repo standards files. Facts are
your job: never ask the user something you can look up.

## 2. Interview

Use the `interview` skill on the decisions the exploration left open.

- Normal: at most one round. Skip it if nothing is open.
- Large: rounds until no decision is open.

## 3. Write the plan

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
- The test command must exist in the repo already. If there isn't one, say
  so under Status and leave the section empty: the stop-time test gate then
  stays off.
- Record interview answers under Decisions.

Checkpoint: `flow: plan <slug>`.

## 4. GATE 1

Show the plan (Goal, Acceptance criteria, Seams, Steps) and ask for
approval. Stop and wait. Don't write code before approval.

On approval:

1. Set Status to `Approved - building`, `checkpoint`.
2. `publish`, then `open-draft`: title from the plan, body linking
   `.flow/<slug>/plan.md` and the issue. If either fails, say so and
   continue locally.

On changes requested: revise the plan, `checkpoint`, and ask again.

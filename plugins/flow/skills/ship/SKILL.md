---
name: ship
description: Last flow phase. Verifies the work, runs deep-review, fixes confirmed findings, strips .flow/, and readies the review for GATE 2.
disable-model-invocation: true
---

Input: an approved `.flow/<slug>/plan.md` with every step ticked.

## 1. Verify

- Every step in `## Steps` is ticked. If not, go back to building.
- `## Open questions` has no unticked item. If one does, stop: it is still
  waiting on the user.
- Version. Each `## Version` line is intent from GATE 1, not a go.
  Re-confirm each: "Still bump <pkg> to Y?", or for "none", "<pkg> stays at
  X. Still no bump?" If `diff-scope` touches a versioned package and the
  plan has no `## Version` line, ask fresh: "<pkg> is at X. Bump to what,
  or none?" A "yes" to "Still bump <pkg> to Y?", or a reply naming a
  number, is the go: change the number, then `checkpoint`. Ask and wait,
  don't park it as an open question: don't ready the review without the
  answer.
- Run the plan's test command. It must pass.
- Large tasks: spawn `flow:tester` on the `diff-scope` diff for coverage
  gaps; `checkpoint` the tests it adds.

## 2. Review

`checkpoint`, then use the `deep-review` skill on the task's `diff-scope`,
with `.flow/<slug>/plan.md` as the spec path, so reviewers check the diff
against the approved acceptance criteria. Fix every confirmed
finding, rerun the test command, `checkpoint`. Findings that fall under the
escalation rule (see the `flow` skill) are parked as open questions, not
fixed silently.

## 3. Clean up

Copy `## Decisions` out of the plan first; the review body needs it. Then
`drop-state`.

## 4. Review request

Write the review body with the `change-body` skill, including the Decisions
list. `publish`, then `ready-for-review`.

## 5. GATE 2

Report the review link (or the branch or changelist, with no host), test
results, and the review summary. The user lands it (`land`). Never land it
yourself, and never enable auto-merge unless asked.

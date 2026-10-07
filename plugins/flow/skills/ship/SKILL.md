---
name: ship
description: Last flow phase. Verifies the work, runs deep-review, fixes confirmed findings, strips .flow/, and readies the PR for GATE 2.
disable-model-invocation: true
---

Input: an approved `.flow/<slug>/plan.md` with every step ticked.

## 1. Verify

- Every step in `## Steps` is ticked. If not, go back to building.
- `## Open questions` has no unticked item. If one does, stop: it is still
  waiting on the user.
- Run the plan's test command. It must pass.
- Large tasks: spawn `flow:tester` on `git diff <base>...HEAD` for coverage
  gaps; commit the tests it adds.

## 2. Review

Use the `deep-review` skill against the PR base branch. Fix every confirmed
finding, rerun the test command, commit. Findings that fall under the
escalation rule (see the `flow` skill) are parked as open questions, not
fixed silently.

## 3. Clean up

Remove `.flow/<slug>/` in its own commit: `flow: remove plan files for
<slug>`. Copy `## Decisions` out of the plan first; the PR body needs it.

## 4. PR

Write the PR body with the `pr-body` skill, including the Decisions list.
Push, update the PR body, and mark it ready for review
(`gh pr ready`). If no PR exists yet, create it.

## 5. GATE 2

Report the PR link, test results, and the review summary. The user merges.
Never merge, and never enable auto-merge unless asked.

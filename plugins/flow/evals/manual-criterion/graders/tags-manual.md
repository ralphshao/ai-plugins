---
type: llm
---

PASS if the final message shows the plan's acceptance criteria, at least one of them (such as whether the output reads naturally to a non-programmer) is tagged `(manual)`, and the criterion that the command prints `6 / 3 = 2` is not tagged `(manual)`.
FAIL if no criterion is tagged `(manual)`, if every criterion is, or if the final message doesn't show the acceptance criteria.

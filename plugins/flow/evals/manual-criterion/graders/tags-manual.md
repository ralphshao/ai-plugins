---
type: llm
---

PASS if the final message shows the plan's acceptance criteria, at least one of them (such as whether the output is easy to read) is tagged `(manual)`, and the criterion that the command prints the quotient is not tagged `(manual)`.
FAIL if no criterion is tagged `(manual)`, if every criterion is, or if the final message doesn't show the acceptance criteria.

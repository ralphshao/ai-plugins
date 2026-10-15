---
type: llm
---

PASS if the final review report has a Correctness finding on `mean` in calc/__init__.py saying it divides by `len(xs) - 1` instead of `len(xs)` (wrong result, or division by zero for one item).
FAIL if the report has no such finding, or lists it only as dropped or refuted.

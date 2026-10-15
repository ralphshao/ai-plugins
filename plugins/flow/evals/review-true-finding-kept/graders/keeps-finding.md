---
type: llm
---

PASS if the final review report keeps a finding on `ratio` in calc/__init__.py saying the broad `except Exception` returns 0 instead of raising ZeroDivisionError as its docstring promises.
FAIL if the report has no such finding, or says validation dropped or refuted it.

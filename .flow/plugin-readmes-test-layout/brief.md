# Plugin READMEs and per-plugin test layout
Source: prompt
Size: Normal

## Request
do the above changes

(The "above changes", from the preceding conversation:)
- Add `plugins/ai-plugins/README.md` and `plugins/flow/README.md`: what the
  plugin does, its skills/commands, requirements, how to run its tests. Point
  the root README table rows at them.
- Keep `docs/adr/` at the repo root.
- Keep tests out of the plugin folders (the whole plugin folder ships to the
  user's plugin cache). Split root `tests/` into `tests/ai_plugins/` and
  `tests/flow/`, with shared `conftest.py` and catalog-level
  `test_marketplace.py` staying in `tests/`.
- Watch out for `REPO_ROOT` in conftest, pytest basename collisions, add a
  pytest config with `testpaths = tests`, and update the AGENTS.md "Tests"
  section.
- Consider whether `plugins/flow/evals/` should move to root `evals/`.

## Constraints
- Don't change plugin versions (AGENTS.md).
- ADRs are never edited after acceptance.

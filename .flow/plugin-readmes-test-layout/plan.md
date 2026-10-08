# Plugin READMEs and per-plugin test layout

## Goal
Each local plugin (`ai-plugins`, `flow`) gets its own README, and the test
suite is grouped by plugin under root `tests/` without shipping anything new
to users' plugin caches. Repo docs describe the new layout.

## Acceptance criteria
- `plugins/ai-plugins/README.md` and `plugins/flow/README.md` exist: purpose,
  skills (and flow's agents/hooks), requirements, how to run their tests.
- Root `README.md` plugin table links still point at the plugin folders
  (GitHub renders the README there); the "Repo structure" tree shows the
  new `tests/` layout.
- `tests/ai_plugins/` holds test_add, test_cli, test_helpers, test_remove,
  test_update, test_wrappers; `tests/flow/` holds test_codex_agents,
  test_guard, test_hooks, test_layout; `tests/conftest.py` and
  `tests/test_marketplace.py` stay at `tests/`.
- `python3 -m pytest` from the repo root collects 802 tests (798 passed,
  4 skipped), same as before the move.
- `python3 -m pytest tests/flow` and `python3 -m pytest tests/ai_plugins`
  each run on their own.
- `pytest.ini` sets `testpaths = tests`.
- AGENTS.md "Tests" section describes the layout and per-plugin runs.
- `claude plugin validate .` passes.
- `ai-plugins` is version 0.2.1 and `flow` is 0.2.4 in each plugin's
  `.claude-plugin/plugin.json` and `.codex-plugin/plugin.json`, in
  `.claude-plugin/marketplace.json`, and in the README table
  (`tests/test_marketplace.py` checks they agree).

## Seams under test
- The pytest suite itself (collection count + pass) - catches: broken
  imports from `conftest`, wrong `REPO_ROOT`, basename collisions, lost
  tests / misses: nothing about README content.

## Steps
- [x] Move ai-plugins tests to `tests/ai_plugins/`, flow tests to
      `tests/flow/` (drop `flow_` prefix), add `pytest.ini`; full suite green
      with same count
- [x] Add `plugins/ai-plugins/README.md`
- [x] Add `plugins/flow/README.md`
- [x] Update root README "Repo structure" and AGENTS.md "Tests" section
- [ ] Set versions: ai-plugins 1.4.0 -> 0.2.1, flow 0.2.3 -> 0.2.4

## Test command
`python3 -m pytest`

## Out of scope
- Moving `plugins/flow/evals/`.
- Editing ADRs (ADR 6 names `tests/test_flow_layout.py`; ADRs are never
  edited after acceptance).

## Decisions
- `plugins/flow/evals/` stays - `claude plugin eval` only reads an eval dir
  below the plugin (`--eval-dir`, default `evals/`).
- Drop the `test_flow_` prefix inside `tests/flow/` - the folder carries it;
  no basename collides with `tests/ai_plugins/`.
- Keep pytest's default import mode, no `__init__.py` - basenames stay
  unique and `from conftest import ...` keeps working because
  `tests/conftest.py` is loaded first.
- Plugin READMEs live at plugin root - GitHub renders them from the root
  README's existing links; loaders ignore them.
- Doc updates (plugin READMEs, root README, AGENTS.md) are in this change -
  user asked mid-plan.

- Versions: ai-plugins reset to 0.2.1 (one-time exception, user's number),
  flow 0.2.3 -> 0.2.4 - user gave both numbers.

## Open questions

## Status
Approved - building

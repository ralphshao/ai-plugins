# Follow-ups to #10: backfill ADRs from docs/plans/flow.md, delete the plan, fix pre-existing hook gaps

## Goal
Every flow design decision that still holds lives in an ADR, `docs/plans/flow.md`
is gone, and the stop and format hooks no longer fail silently or crash on
unreadable files.

## Acceptance criteria
- ADRs 0001-0005 record, from `docs/plans/flow.md`: flow's shape and two human
  gates; decisions between gates; task state in `.flow/`; the guard
  dispatcher in one `hooks.json`; the stop gate. Each is dated to #7
  (2026-10-07) and links the later ADRs that refine it.
- The existing ADRs move to 0006-0009 (old 1-4, same order). Their headings
  and every "ADR N" reference and link in the repo match the new numbers.
- `docs/plans/flow.md` is deleted and nothing links to it.
- AGENTS.md "Design records": plans don't live in `docs/` once implemented;
  lasting decisions go to `docs/adr/`.
- `stop_gate.py`: when `git rev-parse` times out or fails for a reason other
  than "not a git repository", it warns on stderr.
- `stop_gate.py`: an unreadable `plan.md` (OSError, invalid UTF-8) is skipped
  with a stderr warning, and other plans still gate.
- `format.py`: an unreadable `pyproject.toml` or `package.json` counts as no
  config. An error on one file of a multi-file patch is reported on stderr,
  and the remaining files are still formatted.
- `guard.py` docstring and ADR 0004 state the accepted tester gap: a test
  file the tester writes can edit source when run.

## Seams under test
- `stop_gate.py` run as a hook (stdin JSON, stdout/stderr, exit code), via
  `tests/test_flow_hooks.py`'s `hook()` - catches: warnings, skipped plans,
  crash-free exit / misses: real git timeouts (simulated with a fake `git`
  on PATH).
- `format.py` run as a hook, same helper - catches: crash on unreadable
  config, later files in a patch still formatted / misses: real ruff and
  prettier runs.

## Steps
- [x] Renumber ADRs 0001-0004 to 0006-0009 and fix their headings and
      references (AGENTS.md, ADR links).
- [x] Write ADRs 0001-0005 from `docs/plans/flow.md`.
- [x] Delete `docs/plans/flow.md`; update AGENTS.md "Design records".
- [x] `stop_gate.py`: skip an unreadable plan with a warning (test first).
- [x] `stop_gate.py`: warn when git fails other than "not a repository"
      (test first).
- [x] `format.py`: OSError in config checks counts as no config; catch
      errors per file (tests first).
- [x] `guard.py` docstring: note the accepted tester gap.

## Test command
`python3 -m pytest`

## Out of scope
- Fixing the tester gap itself.
- Retrying git in `repo_root`.
- A flow version bump.

## Decisions
- Five ADRs, one per decision, not one big ADR - supersession works per file;
  one big ADR repeats the drift problem `flow.md` has (user, Q1).
- Backfilled ADRs take 0001-0005 in date order; old 1-4 become 6-9, with
  links fixed. Only numbers and links change in accepted ADRs (user, Q2).
- `repo_root` warns, no retry (user, Q3).
- Unreadable plan: skip with warning (user, Q4).
- `format.py`: OSError counts as no config; catch any Exception per file
  and report it, because the hook is best-effort (user, Q5).
- Tester gap accepted; documented in `guard.py` and ADR 0004, not in the
  tester agent (user, Q6).
- No version change (user, Q7).
- Plan's Layout, Migration, Marketplace, and Build order sections get no
  ADR - they record history or code layout, not decisions that still hold.
- Review: stop-gate warnings stay on stderr, not a `systemMessage` - the
  issue and Q3/Q4 ask for stderr; visibility is a possible follow-up.

## Open questions

## Status
Approved - building

# memory-keeper: consolidate to one account-level task

## Goal
One account-level scheduled task maintains all memory, including every project's, and project rules live in `preferences.md` so project instructions never need edits.

## Acceptance criteria
- `maintain` has no project mode. Inside a project it says it must run outside one and stops, sending that via SendUserMessage so a leftover scheduled task is visible.
- `maintain` runs all former project checks that don't need project instructions, can write safe fixes to project files, and has no check that reads project instructions.
- Rule lines in any `preferences.md` are never reworded, merged or deleted as a safe fix, only proposed.
- Cross-project rule candidates are proposals to write account `/preferences.md`. Paste-ready output remains only for rules memory filters would drop.
- Default write cap is 20; "max N writes" still overrides it.
- The report has an unnumbered `**Flagged**` section for projects with no or empty `preferences.md` and folders that list empty or fail to list or read. A flag doesn't stop the run.
- `setup` has no project mode, stops inside a project, and uses only Sunday 8:45 AM and the name `Account memory maintenance`.
- Plugin README, plugin description and catalog/root README descriptions match the new behavior.

## Seams under test
- Skill text has no automated seam. `claude plugin validate .` and the catalog tests catch manifest or catalog drift / miss skill behavior.
- plugin-dev:plugin-validator and plugin-dev:skill-reviewer catch structure and instruction quality / miss live memory behavior, which needs a Cowork run after merge.

## Steps
- [x] maintain: remove mode selection, add the project guard, update description, tiers, write cap and rule-line protection
- [x] maintain: merge checks and safe fixes, remove instruction checks, add flags
- [x] maintain: retarget preference candidates, update proposals, report and approvals
- [x] setup: remove project mode, add the guard, set schedule and name
- [x] Update plugin README and the three plugin descriptions

## Test command
`uv run --with pytest pytest tests/test_marketplace.py`

## Out of scope
- One-time migration prompts and account cleanup
- Deleting old per-project scheduled tasks
- Detecting a separate-memory project whose folder never appears

## Version
memory-keeper 0.1.0 -> 0.1.1 (intent; applied at ship only on the user's go)

## Decisions
- memory-keeper version target 0.1.1 - user answer at GATE 1
- Version go for 0.1.1 given at ship

- Size Normal - rewrites two skills and docs, no code
- Skipped the Explore subagent - the plugin is three files, all read directly
- Unreachable signal: folder lists empty or fails to list or read; flag, don't stop - may be a new project with no memories yet
- Flags go in an unnumbered `**Flagged**` section - they have no exact change to approve
- Task name `Account memory maintenance`; setup's Change also accepts a rename so existing tasks can adopt it - user choice
- Cap 20, request override kept - issue says about 20
- Project guard keeps "project instructions present" - known gap: a project with empty instructions passes it
- Guard notice goes through SendUserMessage - makes leftover per-project tasks visible
- Plugin README documents preferences.md layout and the account preference line - every user needs them

## Open questions

## Status
Approved - building

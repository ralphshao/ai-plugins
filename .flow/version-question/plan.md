# Make flow raise the version question

## Goal
When a flow task touches a versioned package, flow asks the user what the version should become, instead of only refusing bumps nobody asked for. The user states intent at GATE 1 and gives the go at ship.

## Acceptance criteria
- `plan` skill: when the change touches a versioned package (plugin.json, package.json, pyproject.toml, ...), plan.md gets a `## Version` line, and GATE 1 asks "<pkg> is at X. Bump to what at ship, or none?". The answer goes under Decisions as intent, not a go.
- `ship` skill: in Verify, before drop-state and ready-for-review, ship re-confirms the recorded intent ("Still bump <pkg> to Y?"). A recorded "none" is re-confirmed too ("<pkg> stays at X. Still no bump?"). It bumps only on the user's yes with the number; a reply naming a number is that go. If `diff-scope` touches a versioned package and the plan has no Version line, ship asks fresh.
- `flow` skill, Trivial path: when the edit touches a versioned package, the final report asks the version question. Nothing gets bumped.
- AGENTS.md `## Versions`: one line describing the ask-at-GATE-1, confirm-at-ship flow.
- New `docs/adr/0013-flow-asks-the-version-question.md` refines ADR 9. ADR 9's rule that a plan-listed bump isn't a go stays.
- flow goes 0.2.5 -> 0.2.6 in `plugins/flow/.claude-plugin/plugin.json`, `plugins/flow/.codex-plugin/plugin.json`, and flow's entry in `.claude-plugin/marketplace.json`, applied at ship on the user's go. No other version changes.
- `uv run --with pytest pytest` passes.

## Seams under test
- Skill text only. No test seam exists for prose, so checks are the existing pytest suite (catalog and hooks still pass) and plugin-dev:skill-reviewer on each changed skill.

## Steps
- [ ] plan skill: Version section in template, version question at GATE 1, intent under Decisions
- [ ] ship skill: re-confirm or ask fresh in Verify, bump only on a yes with the number
- [ ] flow skill: Trivial report asks; top-level Version changes bullet mentions the ask
- [ ] AGENTS.md Versions line + ADR 0013
- [ ] Run tests, plugin-validator, skill-reviewer on plan/ship/flow

## Test command
`uv run --with pytest pytest`

## Out of scope
- Any hook or script that detects versioned files: the skills tell the agent to check; no code.

## Version
flow 0.2.5 -> 0.2.6 (intent; applied at ship only on the user's go)

## Decisions
- Bump flow to 0.2.6 in this task - user asked at GATE 1; intent only, ship asks for the go.
- Version line is a `## Version` section in plan.md, written only when a versioned package is touched - ship can find it by heading; absent means "no versioned package seen at plan time".
- Ship confirms in step 1 Verify - plan.md (and its Version line) is removed by drop-state in step 3, so the check must come before it.
- Ship re-confirms a recorded "none" too - a silent no-bump is the PR #24 failure; the build may have grown into a release (user, at GATE 1).
- ADR number 0013 - 0012 is taken twice; 0013 is free.

## Open questions

## Status
Approved - building

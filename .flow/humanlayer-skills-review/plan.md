# Adopt three ideas from humanlayer/skills into flow

## Goal
flow's exploration reports the code as it is, plans can name checks only a
person can do, and review bodies say why the change exists.

## Acceptance criteria
- `plan` step 1 has the main agent ask Explore neutral questions about the
  current code, not the desired change, and tells Explore to describe, not
  propose.
- `plan.md`'s template lets an acceptance criterion be tagged `(manual)`
  for checks that need a person (UI, hardware, judgment).
- `ship` lists the unconfirmed `(manual)` criteria in the GATE 2 report.
- `change-body` opens with a one-sentence `## Why`, and its Evidence lists
  manual checks still pending.
- No file under `plugins/flow/skills/` carries an upstream credit line;
  `plugins/flow/README.md` has a `## Credits` section naming each adapted
  skill's source, including HumanLayer's `visual-pr` and `show-me`.
- `tests/flow` passes and `claude plugin validate .` passes.

## Seams under test
- `claude plugin validate .` - catches: broken frontmatter or manifest /
  misses: wording and behavior.
- `tests/flow` (pytest) - catches: hooks that parse plan.md sections
  (`guard.py`, `stop_gate.py` read `## Test command` only) still work /
  misses: skill prose; no unit test covers it.

## Steps
- [ ] `plan/SKILL.md` step 1: the Explore prompt is current-state questions
      plus the describe-only rule, with the request kept out (Q1).
- [ ] `plan/SKILL.md` template and rules: `(manual)` tag on acceptance
      criteria; `ship/SKILL.md` Verify and GATE 2 report the pending ones;
      `change-body` Evidence gets a `Manual:` line (Q2).
- [ ] `change-body/SKILL.md`: `## Why` one-sentence section first, and a
      rule for it (Q3).
- [ ] Move credits out of `change-body`, `tdd`, `interview`, `retro`, and
      `deep-review/references/smell-baseline.md` into a `## Credits`
      section at the end of `plugins/flow/README.md`, adding `visual-pr`.
- [ ] Run plugin-dev's `plugin-validator` on `plugins/flow` and
      `skill-reviewer` on `plan`, `ship`, `change-body`; apply what fits
      this repo's conventions.

## Test command
`uv run --with pytest pytest tests/flow`

## Out of scope
- An implementer subagent for the build step (Q4: no).
- Per-phase documents or fresh sessions per phase (Q5: no).
- Bundling `show-me` or HumanLayer's other plugins into flow (Q6: no).
- New `claude plugin eval` cases for the changed prose.

## Version
flow 0.2.6 -> ? (intent; applied at ship only on the user's go)

## Decisions
- Reviewed humanlayer/skills at 653b6411c1f70c275a18e37673b042ff99f67ceb - the head on 2026-10-08.
- Q1 neutral exploration: adopt - user said yes.
- Q2 manual checks: adopt - user said yes.
- Q3 one-sentence Why in change-body: adopt - user said yes.
- Q4-Q6: skip - user took only 1-3.
- No new ADR for Q1-Q3 - prose changes inside existing phases, no one-way door.
- Credits move to flow's README, swept across all of flow - user asked.
- Credits section goes last in the README, as a table of flow skill and source - fits the README's table style.

## Open questions
- [ ] Q7 Write a short ADR 14 superseding ADR 1's "credit it in the skill" line? - recommended: yes - blocks: credits step
- [ ] Q8 Keep "From Fowler's *Refactoring*, ch. 3" in smell-baseline.md and move only the mattpocock part? - recommended: yes - blocks: credits step
- [ ] Q9 Give each upstream its copyright line and LICENSE link in the Credits section? - recommended: yes - blocks: credits step

## Status
Awaiting GATE 1

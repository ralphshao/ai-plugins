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
  skill's source, including HumanLayer's `visual-pr` and `show-me`, and
  linking `plugins/flow/THIRD_PARTY_NOTICES.md`, which holds each
  upstream's full MIT notice.
- `normal-feature` eval fails if any `Agent` call's input contains
  `ValueError` (the desired change leaking into Explore).
- A new `manual-criterion` eval passes only when the plan tags a
  judgment-only acceptance criterion `(manual)`.
- `tests/flow` passes and `claude plugin validate .` passes.

## Seams under test
- `claude plugin validate .` - catches: broken frontmatter or manifest /
  misses: wording and behavior.
- `tests/flow` (pytest) - catches: hooks that parse plan.md sections
  (`guard.py`, `stop_gate.py` read `## Test command` only) still work /
  misses: skill prose; no unit test covers it.
- `claude plugin eval` cases (`plugins/flow/evals/`) - catches: Explore
  prompt leaking the request (Q1), plan missing the `(manual)` tag (Q2) /
  misses: ship's GATE 2 list and change-body's `## Why` (ship-only, too
  costly to exercise); runs on the API, so in CI or by hand, not in the
  test command.

## Steps
- [x] `plan/SKILL.md` step 1: the Explore prompt is current-state questions
      plus the describe-only rule, with the request kept out (Q1).
- [x] `plan/SKILL.md` template and rules: `(manual)` tag on acceptance
      criteria; `ship/SKILL.md` Verify and GATE 2 report the pending ones;
      `change-body` Evidence gets a `Manual:` line (Q2).
- [ ] `change-body/SKILL.md`: `## Why` one-sentence section first, and a
      rule for it (Q3).
- [ ] Move credits out of `change-body`, `tdd`, `interview`, `retro`, and
      `deep-review/references/smell-baseline.md` into a `## Credits`
      section at the end of `plugins/flow/README.md`, adding `visual-pr`;
      write `plugins/flow/THIRD_PARTY_NOTICES.md` with the full MIT text of
      mattpocock/skills and humanlayer/skills and link it from the table.
- [ ] Write `docs/adr/0014-flow-credits-its-sources-in-its-readme.md`,
      superseding ADR 1's credit-in-the-skill line (Q7).
- [ ] Evals: add a `tool_used` grader on `Agent` with
      `input_match: 'ValueError'`, `max: 0` to `normal-feature` (first
      confirm `input_match` searches the Agent prompt); add a
      `manual-criterion` case (calc fixture, prompt asking for green
      terminal output from `divide`) with `file_exists` plan.md and an
      `llm` grader for a `(manual)` criterion; update the README's
      "Tests and evals" coverage line.
- [ ] Run plugin-dev's `plugin-validator` on `plugins/flow` and
      `skill-reviewer` on `plan`, `ship`, `change-body`; apply what fits
      this repo's conventions.

## Test command
`uv run --with pytest pytest tests/flow`

## Out of scope
- An implementer subagent for the build step (Q4: no; tracked in
  https://github.com/ralphshao/ai-plugins/issues/27).
- Per-phase documents or fresh sessions per phase (Q5: no).
- Bundling `show-me` or HumanLayer's other plugins into flow (Q6: no).
- Evals for ship's GATE 2 manual list and change-body's `## Why` - need a
  full ship run with deep-review and a remote.

## Version
flow 0.2.6 -> 0.2.7 (intent; applied at ship only on the user's go)

## Decisions
- Reviewed humanlayer/skills at 653b6411c1f70c275a18e37673b042ff99f67ceb - the head on 2026-10-08.
- Q1 neutral exploration: adopt - user said yes.
- Q2 manual checks: adopt - user said yes.
- Q3 one-sentence Why in change-body: adopt - user said yes.
- Q4-Q6: skip - user took only 1-3.
- No new ADR for Q1-Q3 - prose changes inside existing phases, no one-way door.
- Credits move to flow's README, swept across all of flow - user asked.
- Q7 ADR 14 supersedes ADR 1's credit line - user said yes.
- Q8 Fowler citation stays in smell-baseline.md; only the mattpocock part moves - user said yes.
- Q9 full MIT notices in plugins/flow/THIRD_PARTY_NOTICES.md, linked from a short README Credits table - user chose it.
- Evals: Explore grader on normal-feature plus a manual-criterion case - user chose both.
- Version intent: flow 0.2.6 -> 0.2.7 at ship - user said so at GATE 1.
- Credits section goes last in the README, as a table of flow skill and source - fits the README's table style.

## Open questions
- [x] Q7 Write a short ADR 14 superseding ADR 1's "credit it in the skill" line? - recommended: yes - blocks: credits step
- [x] Q8 Keep "From Fowler's *Refactoring*, ch. 3" in smell-baseline.md and move only the mattpocock part? - recommended: yes - blocks: credits step
- [x] Q9 Give each upstream its copyright line and LICENSE link in the Credits section? - recommended: yes - blocks: credits step

## Status
Approved - building

# flow: align with Anthropic/OpenAI agentic SDLC guidance and document the mapping

## Goal
flow enforces more of its own loop mechanically (plan-checked review, guarded tests after GATE 1, review-quality evals in CI) and its README shows how it maps to Anthropic's and OpenAI's guidance.

## Acceptance criteria
- `ship` passes `.flow/<slug>/plan.md` to `deep-review` as the spec path.
- With an Approved plan and no unticked open question, the main session's Edit/Write that changes `## Test command`, removes or changes lines in an existing test file, or overwrites one dropping lines, is blocked (exit 2) with a message naming the open-question route. Adding lines, new test files, ticking steps, and all subagent behavior are unchanged.
- With no Approved plan, or an unticked open question, the main session passes through as today. A guard error fails open for the main session.
- Two new eval cases (`review-seeded-bug`, `review-true-finding-kept`) exist and run under `claude plugin eval`.
- `.github/workflows/flow-evals.yml` runs the evals on PRs touching `plugins/flow/{skills,agents,hooks,evals}/**`, and skips with a notice when `ANTHROPIC_API_KEY` is unset.
- deep-review's error-handling/trust-boundary keyword lists and flow/SKILL.md's re-sizing section are shorter; no eval case regresses.
- `plugins/flow/README.md` has a section mapping flow to the labs' guidance, linking the four sources.
- New ADR for the main-session guard.

## Seams under test
- `guard.py` stdin JSON -> exit code/stderr (tests/flow/test_guard.py) - catches: block/allow decisions per tool, plan state, file kind / misses: Bash bypass (accepted gap).
- `claude plugin eval` cases - catches: review catches and false drops, sizing/gating regressions after trims / misses: model variance between runs.

## Steps
- [ ] ship passes plan.md as deep-review spec path
- [ ] guard.py: main-session guard after GATE 1, with tests (TDD)
- [ ] ADR 0012: flow guards the main session after GATE 1
- [ ] Eval cases review-seeded-bug and review-true-finding-kept
- [ ] CI workflow flow-evals.yml
- [ ] Trim deep-review scans and flow/SKILL.md re-sizing, evals before/after
- [ ] README section mapping flow to the labs' guidance

## Test command
`uv run --with pytest pytest tests/flow`

## Out of scope
- Maintain stage, cleanup agents, org governance.
- Guarding the main session's Bash.
- Version bumps.

## Decisions
- Skipped Large's two contrasting drafts - the issue already fixes the design.
- Q1 guard blocks Test-command edits, line-removing Edits, line-dropping Writes of existing test files - additions stay allowed.
- Q2 Bash gap accepted, documented in the ADR - parsing main-session Bash is fragile.
- Q3 guard off while an open question is unticked - reuses the park route as escape hatch.
- Q4 two review eval cases - smallest set scoring catches and false drops.
- Q5 path-filtered eval workflow, skips without ANTHROPIC_API_KEY - user adds the secret.
- Q6 small trims, kept only if evals don't regress.
- Q7 one ADR (guard); CI evals recorded here only.

## Open questions

## Status
Approved - building

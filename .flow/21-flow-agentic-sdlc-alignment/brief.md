# flow: align with Anthropic/OpenAI agentic SDLC guidance and document the mapping
Source: https://github.com/ralphshao/ai-plugins/issues/21
Size: Large
VCS: vcs-git; host: host-github
Isolation: worktree on branch claude/flow-21-588bbc (made for this task)

## Request
Issue #21 body (verbatim at the link above; copied here in substance — the
full comparison tables live in the issue):

Align flow more closely with the shape Anthropic and OpenAI both describe for
agentic engineering, and document how flow maps to it.

Deliberate differences to keep: human gates and deleting `.flow/` at ship (ADR 3).

## Changes, in order

- [ ] **Review the diff against the plan.** `ship` runs `deep-review` with no spec, so reviewers check against linked issues, not the approved acceptance criteria. Pass `.flow/<slug>/plan.md` as the spec path (it still exists then; `drop-state` runs after).
- [ ] **Guard the main agent after GATE 1.** `guard.py` only restricts subagents, so the main agent can edit the plan's test command or existing tests to get past `stop_gate.py`. Block those edits once Status is Approved; adding new tests stays allowed.
- [ ] **Review-quality evals.** The 5 eval cases cover sizing and gating only. Add fixture repos with seeded bugs and score `deep-review` on catches and on the validator's false drops.
- [ ] **Run evals in CI** when `skills/`, `agents/`, or `hooks/` change, and rerun them when a model pin in `agents/*.md` changes.
- [ ] **Trim recipe-style judgment steps** (deep-review's keyword scans for error handling and trust boundaries, the re-sizing rules in `flow/SKILL.md`), checked against the new evals. Keep the VCS procedures exact.
- [ ] **README: how flow maps to the labs' guidance.** Add a short section with a table mapping flow's pieces to Anthropic's playbook and OpenAI's harness engineering (shared shape, where flow matches, where it deliberately differs: human gates kept, `.flow/` deleted at ship per ADR 3), linking the sources above.

## Out of scope

A Maintain stage, cleanup agents, and org-level governance (managed settings, approved marketplaces).

## Constraints
No version bumps without the user's explicit go.

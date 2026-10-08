# Follow-ups to #10: backfill ADRs from docs/plans/flow.md, delete the plan, fix pre-existing hook gaps
Source: https://github.com/ralphshao/ai-plugins/issues/11
Size: Large

## Request
## Problem

`docs/plans/flow.md` is marked implemented and unmaintained, but some decisions that still apply exist only in that plan. Because nobody updates the plan, it drifts out of date while readers keep trusting it.

#10 adds ADR 3 (flow's hooks are shared by Claude Code and Codex) and ADR 4 (gate approval and version bumps are explicit). Once #10 merges, these statements in the plan are wrong, and ADR 3 supersedes them:

- "Codex hook input has no `agent_type`."
- "On Codex, reviewer read-only comes from `sandbox_mode`."
- "`/flow:setup-codex` writes the TOMLs."

These decisions still apply but have no ADR:

- Two human gates: approve the plan, approve landing. ADR 4 covers how approval is given, not why the gates exist.
- One `hooks/hooks.json` that picks a policy by `agent_type`, because Claude Code ignores `hooks:` frontmatter on plugin agents.
- The stop gate runs the plan's test command, and unticked open questions allow the stop.
- Any other section of the plan whose decision still holds (sizing, phases, state and handoff). Check each one.

## Proposal

1. Backfill ADRs for the decisions above, dated to when they were made, and link ADR 3 and ADR 4 where they apply.
2. Delete `docs/plans/flow.md`. Git history keeps the full text.
3. Update AGENTS.md's "Design records" section: plans don't live in `docs/` once implemented, and lasting decisions go to `docs/adr/`.

## Pre-existing hook gaps found in #10's review

Validated during #10's deep review and confirmed, but present before #10, so they were left out of it. Paths are under `plugins/flow/hooks/`.

- **`stop_gate.py` `repo_root`:** if `git rev-parse` fails or times out (5s), the root falls back to `cwd`. From a subdirectory no plan is found, and the gate allows the stop without a word. Retry, or warn on stderr when git fails in a way other than "not a repository".
- **`stop_gate.py` `active_plans`:** a `plan.md` that can't be read (OSError, or invalid UTF-8) crashes the hook with exit 1, which turns the gate off for every plan. Skip that plan with a warning instead.
- **`format.py` `has_ruff_config` and `has_prettier_config`:** an unreadable `pyproject.toml` or `package.json` (OSError) crashes the hook. Return False on OSError. Also, `main`'s per-file loop (new in #10) stops at the first error, so the remaining files in a multi-file `apply_patch` go unformatted. Catch the error per file.
- **Tester guard, by design:** the tester may write a test file that edits source files when run with `pytest`. Document this in `guard.py` or in the tester agent, or accept it.

## Acceptance criteria

- Every decision in `docs/plans/flow.md` that still applies is in an ADR.
- `docs/plans/flow.md` is gone, and nothing links to it.
- AGENTS.md describes the new rule for design records.
- Each hook gap above is either fixed with a test or explicitly accepted.

Depends on #10.

## Constraints
None stated beyond the issue.

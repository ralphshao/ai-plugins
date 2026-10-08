# deep-review: report lenses that didn't run, and pass reference sources to reviewers
Source: https://github.com/ralphshao/ai-plugins/issues/12
Size: Normal

## Request
Two gaps in `plugins/flow/skills/deep-review/SKILL.md` showed up while reviewing #10.

## 1. A lens that fails to start goes unreported

Step 3 launches one `flow:code-reviewer` per lens, but the skill doesn't say what to do if a launch fails. In #10's review, the standards lens was blocked by Claude Code's auto-mode permission check. The same prompt had launched normally in an earlier round, so the check doesn't block it consistently. Nothing in the skill makes the final report say that a lens didn't run, so it can read as a full review when it wasn't one.

**Proposed fix:** if a reviewer or validator can't start, retry once. If it still fails, the report names each lens or file that wasn't checked. "No issues found" only appears when every selected lens ran.

## 2. Reviewers don't get reference sources

Step 2's context block covers intent, spec, and standards files, but not external evidence. In #10, the correctness reviewer couldn't check one finding: it said it "couldn't check the Codex source offline". A local openai/codex clone existed, but nothing told the reviewer about it. The validators, whose prompts included the clone path, confirmed the same finding.

**Proposed fix:** add a `References:` line to the context block for the reviewers and the validators. It lists ADRs relevant to the diff, plus any local clones or docs of external systems the change depends on.

## Acceptance criteria

- `deep-review` says what to do when a subagent can't start, and the report lists any lens that didn't run.
- The context block has a `References:` line, and the reviewers and validators both receive it.

## Constraints
None stated.

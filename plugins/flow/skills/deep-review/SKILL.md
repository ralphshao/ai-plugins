---
name: deep-review
description: Multi-pass review of uncommitted work, a branch, or committed code (git SHA or range, PR, Perforce changelist, Swarm review). Runs parallel flow:code-reviewer subagents, one per lens (correctness/spec, standards/quality, history, and silent failures when the diff touches error handling), validates every finding with flow:review-validator, and reports only what survives. Use for "deep review", "thorough review", "review this branch/PR before I merge", or /deep-review.
argument-hint: "[target: sha:<rev> | <a>..<b> | pr:<n> | cl:<n> | review:<n> | #<n> | base-ref] [spec path] [correctness|standards|history|errors|all]"
allowed-tools: Read, Grep, Glob, Agent, Bash(git status:*), Bash(git diff:*), Bash(git log:*), Bash(git show:*), Bash(git rev-parse:*), Bash(git merge-base:*), Bash(git symbolic-ref:*), Bash(git cat-file:*), Bash(git fetch origin:*), Bash(git remote get-url:*), Bash(gh auth status:*), Bash(git worktree add --detach:*), Bash(git worktree remove:*), Bash(gh pr view:*), Bash(gh issue view:*), Bash(p4 -ztag info:*), Bash(p4 -ztag describe:*), Bash(p4 -ztag client -o:*), Bash(p4 -ztag stream -o:*), Bash(p4 info:*), Bash(p4 describe:*), Bash(p4 diff:*), Bash(p4 diff2:*), Bash(p4 opened:*), Bash(p4 changes:*), Bash(p4 property -l:*), Bash(p4 tickets:*), Bash(p4 login -s:*)
---

Orchestrate a review with the `flow:code-reviewer` and `flow:review-validator` subagents. You coordinate; the subagents read the code. Don't review the code yourself, and don't edit anything.

Some steps below point at sections of the `flow` skill. Read them from `${CLAUDE_SKILL_DIR}/../flow/SKILL.md` (the `flow` folder next to this skill's own); don't invoke `flow`, which would start or resume a task. On Codex, use the agent names from its "Agent names on Codex" section.

## 1. Pin the scope

Arguments: `$ARGUMENTS` (on Codex: whatever the user passed with the request)

Lens words (`correctness`, `standards`, `history`, `errors`, `all`) pick the lenses; the default is `all`. A path to an existing file is the spec. Pick the VCS and review-host skills as the `flow` skill's "VCS and review host" section says. Any other argument is a target:

- **Target** (`sha:<rev>`, `<a>..<b>`, `pr:<n>`, `cl:<n>`, `review:<n>`, `#<n>`, a bare number, bare hex, or a base ref): run the VCS skill's `resolve-target`. It may call the host's `fetch-review`.
- **Nothing**: run `diff-scope`. Uncommitted work wins over the branch or changelist.

Either way you get a diff command, the commits or changelists in range, the intent text, and how reviewers read files: a read root directory, or a print command for files that aren't local (Perforce). If the target doesn't resolve or the diff is empty, stop and say so. Don't start subagents on a bad scope.

## 2. Gather context

Collect these once, so each subagent doesn't repeat the work:

- **Intent**: the review title and body, and the commit or changelist descriptions.
- **Spec**: a spec path given in the arguments; otherwise issues referenced in the review body or descriptions (`#123`, `Closes #45`, a tracker key), fetched with `fetch-issue` or its no-host fallback. If there's none, note "no spec" and drop the Spec checks.
- **Standards files**: paths (not contents) of `CLAUDE.md`, `AGENTS.md`, and `CONTRIBUTING.md` at the read root and in each parent directory of a changed file (from the diff's file list).
- **References**: sources reviewers can check findings against. List paths (not contents) of ADRs in the repo's ADR folder (`docs/adr/`, or wherever the repo keeps them) that mention a changed file or module, plus any local clones or docs of external systems the change depends on that the arguments, intent, spec, or standards files name. Don't search the disk for clones. If there are none, note "none".
- **Error handling touched?** Scan the added lines in the diff output (`+` lines) for `try`, `catch`, `except`, `rescue`, `recover`, `finally`, `.catch(`, `|| default`-style fallbacks, `Result`/`Err(`, and `if err != nil`. Plain optional chaining (`?.`) and null-coalescing (`??`) don't count: they're everyday syntax in several languages. Note yes or no.

## 3. Review in parallel

In one message, launch one `flow:code-reviewer` subagent per selected lens (the correctness lens uses `flow:strong-reviewer`). Give each the same context block:

```
Scope: <the diff command>
Read files: <read root path, or the print command>
Commits: <commits or changelists in range>
Intent: <review title/body, or "descriptions only">
Spec: <spec text, or "none">
Standards files: <paths>
References: <paths, or "none">
```

Then the lens brief:

- **correctness** (launch `flow:strong-reviewer` instead, the same reviewer pinned to a stronger model; Codex: `flow-strong-reviewer`): "Report only Correctness and Spec findings. Look for bugs the diff introduces: wrong results, broken references, unhandled errors, security holes, races, leaks. Check the diff against the spec if there is one. Skip everything else."
- **standards**: "Report only Standards, Tests, Performance, Readability, Best practice, and Simplification findings. For Standards, quote the rule and name its file. Also check the diff against the smell baseline (read it from the path given); report a smell as a Readability or Simplification finding labelled 'possible <smell>', never as a hard violation, and drop it where a documented repo standard endorses the pattern. Skip correctness bugs; another reviewer covers them."

  Give the standards reviewer the path `${CLAUDE_SKILL_DIR}/references/smell-baseline.md` to Read for the baseline; don't paste it.
- **history**: "Report only Correctness findings that come from the code's history. For the lines each hunk changes or removes, read their history: in git, `git log -L <start>,<end>:<file>` or `git blame` on the pre-change revision, then `git show` on the commits that matter; in Perforce, `p4 annotate` and `p4 filelog`, then `p4 describe`. Report a change that undoes an earlier fix, reintroduces a bug a past commit removed, or contradicts the reason a past commit or changelist description gives for the code. Quote that description. Skip everything else."
- **errors** (only when `all` is selected and error handling was touched, or when `errors` is named explicitly): "Report only silent-failure findings, as Correctness: swallowed or overly broad catches, log-and-continue, defaults returned on error, fallbacks that hide failures, retries that give up silently. For each broad catch, name the errors it would hide. Skip everything else."

If a reviewer can't start (the launch is refused or errors) or returns without a report, retry it once. If it still fails, record that lens as not run and go on with the others. If no lens ran, stop and say the review didn't run, and why. A reviewer that returns a report with no findings did run.

## 4. Merge

Pool the findings. Two findings are duplicates when they name the same `file:line` and the same problem; keep the one with the stronger evidence. Keep each pre-existing issue once.

If no reviewer that ran reported any findings, skip to step 6.

## 5. Validate

Group the merged findings by file. In one message, launch one `flow:review-validator` subagent per file, in parallel. Give it the scope, the intent, the spec (if any), the `Read files:` and `References:` lines, and that file's findings verbatim, each with its title, category, cited lines, current code, and proposed fix.

Apply its verdicts:

- `CONFIRMED`: keep. If the fix is `CORRECTED`, use the corrected fix. If it `BREAKS` something, add that to the finding.
- `REFUTED`: drop.
- `UNSURE`: keep at Low severity, marked Likely, with the validator's reason, and keep the severity the reviewer reported next to it: `Low (reported: High; UNSURE: <reason>)`. The `flow` skill escalates an UNSURE high-severity finding, so that signal must survive.

Add anything listed under `Noticed:` to the report as Likely; it hasn't been validated.

If a validator can't start or returns no verdicts, retry it once. If it still fails, keep that file's findings, marked Likely and "not validated", and record the file as not validated. Treat a finding the validator returned no verdict for the same way.

## 6. Report

Use the finding format from the `## Output format` section of `${CLAUDE_SKILL_DIR}/../../agents/code-reviewer.md`. Start with one line naming the scope, the lenses run, the spec, the standards files, and the references used. If any lens didn't run or any file wasn't validated, follow it with a `Not checked:` line naming each one, so the report can't read as a full review. Then give the findings in two sections, so one axis can't bury the other:

- `## Correctness & spec`: Correctness, Spec, and silent-failure findings.
- `## Standards & quality`: everything else.

Within each section, group by file and put the most severe first. Then add `## Pre-existing`, if there are any. End with:

- counts per severity in each section
- the worst issue in each section
- how many findings validation dropped

If nothing survived and every selected lens and validator ran, say: "No issues found. Checked <lenses run>, spec (or: no spec), and standards." If something didn't run, say instead: "No issues found in what ran", followed by the `Not checked:` line.

If `resolve-target` made a temporary checkout, remove it as the VCS skill says, even when the review stopped early. Never post the findings to the review host; the report stays here.

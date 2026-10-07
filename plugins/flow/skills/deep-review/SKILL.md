---
name: deep-review
description: Multi-pass review of a branch, PR, or working-tree diff. Runs parallel flow:code-reviewer subagents, one per lens (correctness/spec, standards/quality, and silent failures when the diff touches error handling), validates every finding with flow:review-validator, and reports only what survives. Use for "deep review", "thorough review", "review this branch/PR before I merge", or /deep-review.
argument-hint: "[base-ref | PR number] [spec path] [correctness|standards|errors|all]"
allowed-tools: Read, Grep, Glob, Agent, Bash(git status:*), Bash(git diff:*), Bash(git log:*), Bash(git rev-parse:*), Bash(git merge-base:*), Bash(git symbolic-ref:*), Bash(gh pr view:*), Bash(gh issue view:*)
---

Orchestrate a review with the `flow:code-reviewer` and `flow:review-validator` subagents. You coordinate; the subagents read the code. Don't review the code yourself, and don't edit anything.

## 1. Pin the scope

Arguments: `$ARGUMENTS`

Lens words (`correctness`, `standards`, `errors`, `all`) pick the lenses; the default is `all`. The other arguments set the scope:

- **PR number**: run `gh pr view <n> --json title,body,baseRefName,headRefOid`. If `headRefOid` doesn't match `git rev-parse HEAD`, stop and tell the user to check out the PR branch first; the subagents read local files. Base is `origin/<baseRefName>`.
- **Base ref**: use it.
- **Nothing**: if the working tree has changes (`git status --porcelain`), the scope is `git diff HEAD`. Otherwise the base is the remote default branch: `git symbolic-ref --short refs/remotes/origin/HEAD`, else the first of `origin/main` and `origin/master` that resolves. Fall back to local `main` or `master` only when there's no remote. Local default branches go stale, and a stale one makes already-merged commits look new.

For a base, confirm it resolves (`git rev-parse <base>`). If `git rev-parse HEAD` equals the base's commit, stop: the branch has no commits of its own. Otherwise capture `git diff --stat <base>...HEAD` and `git log <base>..HEAD --oneline`. If the ref doesn't resolve or the diff is empty, stop and say so. Don't start subagents on a bad scope.

## 2. Gather context

Collect these once, so each subagent doesn't repeat the work:

- **Intent**: the PR title and body, and the commit subjects.
- **Spec**: a spec path given in the arguments; otherwise issues referenced in the PR body or commit messages (`#123`, `Closes #45`), fetched with `gh issue view <n> --json title,body`. If there's none, note "no spec" and drop the Spec checks.
- **Standards files**: paths (not contents) of `CLAUDE.md`, `AGENTS.md`, and `CONTRIBUTING.md` at the repo root and in each parent directory of a changed file (`git diff --name-only`).
- **Error handling touched?** Grep the added lines of the diff (`+` lines) for `try`, `catch`, `except`, `rescue`, `recover`, `finally`, `.catch(`, `?.`, `?? `, `|| default`-style fallbacks, `Result`/`Err(`, and `if err != nil`. Note yes or no.

## 3. Review in parallel

In one message, launch one `flow:code-reviewer` subagent per selected lens. Give each the same context block:

```
Scope: <the diff command, e.g. git diff main...HEAD>
Commits: <git log output>
Intent: <PR title/body, or "commit messages only">
Spec: <spec text, or "none">
Standards files: <paths>
```

Then the lens brief:

- **correctness** (pass `model: opus`): "Report only Correctness and Spec findings. Look for bugs the diff introduces: wrong results, broken references, unhandled errors, security holes, races, leaks. Check the diff against the spec if there is one. Skip everything else."
- **standards**: "Report only Standards, Tests, Performance, Readability, Best practice, and Simplification findings. For Standards, quote the rule and name its file. Also check the diff against the smell baseline below; report a smell as a Readability or Simplification finding labelled 'possible <smell>', never as a hard violation, and drop it where a documented repo standard endorses the pattern. Skip correctness bugs; another reviewer covers them."

  Paste this smell baseline (from Fowler's *Refactoring*, ch. 3; list adapted from mattpocock/skills, MIT) into the standards brief:

  - Mysterious Name: the name doesn't reveal what it does or holds.
  - Duplicated Code: the same logic shape in more than one hunk or file.
  - Feature Envy: a function that uses another object's data more than its own.
  - Data Clumps: the same few fields or params always travel together.
  - Primitive Obsession: a string or number standing in for a domain concept.
  - Repeated Switches: the same switch or if-cascade on the same type in several places.
  - Shotgun Surgery: one logical change forces scattered edits across many files.
  - Divergent Change: one module edited for several unrelated reasons.
  - Speculative Generality: abstraction, parameters, or hooks no requirement asks for.
  - Message Chains: long `a.b().c().d()` walks the caller shouldn't depend on.
  - Middle Man: a function or class that mostly delegates onward.
  - Refused Bequest: a subclass that ignores or overrides most of what it inherits.
- **errors** (only when `all` is selected and error handling was touched, or when `errors` is named explicitly): "Report only silent-failure findings, as Correctness: swallowed or overly broad catches, log-and-continue, defaults returned on error, fallbacks that hide failures, retries that give up silently. For each broad catch, name the errors it would hide. Skip everything else."

## 4. Merge

Pool the findings. Two findings are duplicates when they name the same `file:line` and the same problem; keep the one with the stronger evidence. Keep each pre-existing issue once.

If no reviewer reported any findings, skip to step 6.

## 5. Validate

Group the merged findings by file. In one message, launch one `flow:review-validator` subagent per file, in parallel. Give it the scope, the intent, the spec (if any), and that file's findings verbatim, each with its title, category, cited lines, current code, and proposed fix.

Apply its verdicts:

- `CONFIRMED`: keep. If the fix is `CORRECTED`, use the corrected fix. If it `BREAKS` something, add that to the finding.
- `REFUTED`: drop.
- `UNSURE`: keep at Low severity, marked Likely, with the validator's reason.

Add anything listed under `Noticed:` to the report as Likely; it hasn't been validated.

## 6. Report

Use the `flow:code-reviewer` output format. Start with one line naming the scope, the lenses run, the spec, and the standards files used. Then give the findings in two sections, so one axis can't bury the other:

- `## Correctness & spec`: Correctness, Spec, and silent-failure findings.
- `## Standards & quality`: everything else.

Within each section, group by file and put the most severe first. Then add `## Pre-existing`, if there are any. End with:

- counts per severity in each section
- the worst issue in each section
- how many findings validation dropped

If nothing survived, say: "No issues found. Checked <lenses run>, spec (or: no spec), and standards."

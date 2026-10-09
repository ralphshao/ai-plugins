---
name: vcs-git
description: How flow's VCS operations (find-state, isolate, checkpoint, diff-scope, publish, drop-state, land, resolve-target) run in a git repo, on a regular branch or in a worktree. Load when a flow phase or deep-review names one of these operations in a git work tree.
user-invocable: false
---

Flow's phases name an operation; this skill says how to run it in git. Git
has no pull requests or issues; those belong to a review host (`host-*`
skill), when there is one.

## Detect

Use this skill when `git rev-parse --is-inside-work-tree` prints `true`.

## Default branch

The default branch is the remote's: `git symbolic-ref --short
refs/remotes/origin/HEAD`, else the first of `origin/main` and
`origin/master` that resolves. Fall back to local `main` or `master` only
when there's no remote. Local default branches go stale, and a stale one
makes already-merged commits look new.

## find-state

Look for `.flow/*/plan.md` at `git rev-parse --show-toplevel`. Also check
the other places a task may live, and name them if a plan is there:

- other worktrees: each path in `git worktree list --porcelain`;
- branches without a worktree: `git branch --list 'flow/*'`, then
  `git show <branch>:.flow/<slug>/plan.md`.

To resume a task found elsewhere, work in its worktree, or switch to its
branch when the tree is clean.

## isolate

Give the task its own branch, `flow/<slug>`. Return the branch name (and
worktree path, if any) for the brief.

- **Already isolated:** stay put when on a feature branch made for this
  task, or in a linked worktree made for it (`git rev-parse --git-dir`
  differs from `git rev-parse --git-common-dir`).
- **Clean tree:** "clean" means `git status --porcelain` lists nothing
  outside `.flow/<slug>/` and the files the caller says belong to this task
  (a Trivial edit that grew into Normal). Branching in place keeps them.
  - On the default branch: `git switch -c flow/<slug>`.
  - Elsewhere (another branch, detached HEAD):
    `git switch -c flow/<slug> <default branch>`.
  - Never check out the default branch itself: in a worktree it may be
    checked out elsewhere. The uncommitted brief comes along either way.
- **Unrelated changes:** ask the user which they want:
  - a new worktree: `git worktree add -b flow/<slug> ../<repo>-<slug>
    <default branch>`; move the brief into it and work there from now on;
  - or they clean up the tree, and you then branch in place as above.

  Never stash, reset, or discard their changes.

## checkpoint

Stage the files this step changed by name, plus `.flow/<slug>/`, and
`git commit`. Follow the repo's commit convention (`AGENTS.md`,
`CONTRIBUTING.md`, recent `git log`). Never `git add -A` past files you
didn't touch.

## diff-scope

The changes to review or test, as a diff command, its base revision, a
commit list, and a read root.

- Uncommitted work: `git diff HEAD`; base `HEAD`.
- The task branch: base is `git merge-base <default branch> HEAD`; diff is
  `git diff <base>...HEAD`, commits `git log <base>..HEAD --oneline`.
- Read root: the repo root.

Stop and say so if the base doesn't resolve, HEAD equals the base, or the
diff is empty.

## publish

`git push -u origin <branch>`. With no remote, say so and continue locally.

## drop-state

`git rm -r .flow/<slug>` and commit `flow: remove plan files for <slug>`.

## land

The user merges the branch, through the review host or by hand. Never merge
it yourself and never push to the default branch. With no host, tell the
user: "merge `flow/<slug>` into `<default branch>`" (and, for a worktree,
`git worktree remove <path>` afterwards).

## resolve-target

Turn a deep-review target into a diff command, its base revision, commit
list, intent, and read root.

| Target | Diff | Base revision | Commits / intent |
|--------|------|---------------|------------------|
| `sha:<rev>`, or bare hex of 7-40 chars | `git diff <rev>^1 <rev>` (root commit: `git show <rev>`) | `<rev>^1` (root commit: none) | `git log -1 --format=%B <rev>` |
| `<a>..<b>` or `<a>...<b>` | `git diff <a>...<b>` | `git merge-base <a> <b>` | `git log <a>..<b> --oneline` |
| any other ref (a base) | `git diff <base>...HEAD` | `git merge-base <base> HEAD` | `git log <base>..HEAD --oneline` |
| `pr:<n>`, `#<n>`, or a bare number | host `fetch-review` gives base and head SHAs; `git diff <base>...<head>` | `git merge-base <base> <head>` | the review's title and body, plus commit subjects |

A three-dot diff compares against the merge-base, not the base ref's tip, so
the base revision is the merge-base.

Prefixes always win. Without one, a string with a letter a-f is a SHA; an
all-digit string of 7 or more characters is a SHA if it resolves as a
commit, otherwise a review number; shorter all-digit strings are review
numbers.

Confirm each rev resolves (`git rev-parse --verify <rev>^{commit}`). When a
review's head isn't local, the host's `fetch-review` says how to fetch it.
The host's `fetch-review` says which base and head to diff for each review
state.

**Read root.** When the target's head is `HEAD` and the tree is clean, the
read root is the repo root. Otherwise check the head out where reviewers
can read it, without touching the user's tree:

1. `git worktree add --detach <tmp>/flow-review-<short sha> <head>`, with
   `<tmp>` a fresh temp directory outside the repo.
2. Give reviewers that path as the read root.
3. After the report, `git worktree remove --force <path>`, even if the
   review failed.

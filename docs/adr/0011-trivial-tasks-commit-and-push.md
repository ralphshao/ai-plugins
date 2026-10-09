# 11. Trivial tasks commit and push

Status: accepted (#18, 2026-10-09). Supersedes the "done in place" part of
ADR 1's Trivial size.

## Context

ADR 1 made Trivial "done in place, no gates": edit, test, show the diff,
stop. Trivial never ran a VCS operation, so the change was left
uncommitted wherever the session was. The user usually starts sessions in
a worktree made for the task, where that left the right change on the
right branch but uncommitted. On the default branch, it left an
uncommitted edit on `main` with no warning.

## Decision

Trivial runs `isolate`, makes the change, runs the tests, `checkpoint`s
one commit, and `publish`es it, then reports the branch and stops. It
writes no `.flow/` files and has no gates. What happens to the pushed
branch (a review, a merge) is up to the user.

`isolate` already stays put in a worktree or feature branch made for the
task, so a session that starts in one pays nothing extra.

## Alternatives

- **Commit only.** Rejected: the push was still manual.
- **Also open a review ready to land.** Tried in #18 and reverted by the
  user, who handles reviews for Trivial changes by hand.

## Consequences

- Trivial on the default branch now branches first instead of editing
  `main`.
- A Trivial change is never left uncommitted, but flow doesn't track it
  after the push.

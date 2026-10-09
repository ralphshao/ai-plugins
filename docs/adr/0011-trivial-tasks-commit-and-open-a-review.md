# 11. Trivial tasks commit and open a review

Status: accepted (#18, 2026-10-09). Supersedes the "done in place" part of
ADR 1's Trivial size.

## Context

ADR 1 made Trivial "done in place, no gates": edit, test, show the diff,
stop. Trivial never ran a VCS operation, so the change was left
uncommitted wherever the session was. The user usually starts sessions in
a worktree made for the task, where that left a dead end: the right
change on the right branch, with no commit and no review. On the default
branch, it left an uncommitted edit on `main` with no warning.

## Decision

Trivial runs `isolate`, makes the change, runs the tests, `checkpoint`s
one commit, then `publish` and `ready-for-review` with a short
`change-body` description, and stops at GATE 2. It still writes no
`.flow/` files and has no GATE 1.

`isolate` already stays put in a worktree or feature branch made for the
task, so a session that starts in one pays nothing extra.

## Alternatives

- **Commit only.** Rejected by the user: the push and review were still
  manual.
- **Open a draft review.** Rejected by the user: a Trivial change has no
  build phase, so it is ready when opened.

## Consequences

- Every Trivial change ends with a review the user lands, the same GATE 2
  as Normal and Large.
- Trivial on the default branch now branches first instead of editing
  `main`.

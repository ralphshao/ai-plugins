# Make flow version-control agnostic

## Goal
flow runs the same plan/build/ship loop in a git repo or a Perforce
workspace, with or without a review host. Phase skills name operations; a
VCS skill (`vcs-git`, `vcs-perforce`) and an optional review-host skill
(`host-github`, `host-swarm`) say how to do each one.

## Acceptance criteria
- VCS skills `vcs-git` and `vcs-perforce` each define: isolate, checkpoint,
  diff-scope, publish, land.
- Host skills `host-github` and `host-swarm` define any of the optional
  host operations: fetch-issue, fetch-review, open-draft, ready-for-review.
  host-github defines all four; host-swarm defines all but fetch-issue.
- With no host: open-draft/ready-for-review report the branch or CL for
  review, GATE 2 tells the user to land it; fetch-issue falls back to a
  connected tracker tool, else asks for the text.
- Phase skills (flow, start, plan, ship) and deep-review contain no `git`,
  `gh`, or `p4` commands; they call operations and say how to pick skills.
- `gh` appears only in host-github; Swarm only in host-swarm.
- pr-body stays, worded as the review-body template for any host.
- vcs-git isolate: regular branch in place by default (`git switch -c
  flow/<slug> <base>`, never checking out the default branch); stays put on
  a feature branch or linked worktree; with unrelated changes on the default
  branch, asks: new worktree, or the user cleans up and flow branches in
  place. Resume finds plans in other worktrees and `flow/*` branches.
- vcs-perforce isolate: pending CL in the current workspace by default;
  stays on an existing task/dev stream (checkpoint = submit to it, review
  and land via copy-up CL); creates a stream only when asked; never creates
  classic branches.
- Reviewer/tester agents take the diff command from the caller, git or p4.
- guard.py lets reviewers run read-only p4 subcommands and blocks writes
  and connection-changing global flags.
- stop_gate.py finds the root in a p4 workspace with no git.
- format.py stops its upward walk at a P4CONFIG file.
- flow version 0.2.0 in both manifests and README.
- `python3 -m pytest -q` passes.

## Seams under test
- `guard.check_bash` via the hook - catches: p4 allow/deny list / misses: real p4 behavior
- `stop_gate.py` run as a hook with a fake `p4` on PATH, and in a linked git worktree - catches: root fallback order, worktree root / misses: real p4 info output variants
- `format.ancestors` - catches: walk stops at P4CONFIG / misses: nothing relevant
- layout test over skill files - catches: missing operation in a VCS skill, gh/Swarm/VCS commands leaking outside their skill / misses: prose quality

## Steps
- [ ] Add vcs-git skill
- [ ] Add vcs-perforce skill
- [ ] Add host-github skill (all gh steps move here)
- [ ] Add host-swarm skill
- [ ] Rewrite flow, start, plan, ship, deep-review, pr-body to use operations; layout test
- [ ] Generalize agents' scope wording (code-reviewer, review-validator, tester)
- [ ] guard.py: p4 read-only allowlist + tests
- [ ] stop_gate.py: p4 clientRoot fallback + tests (p4, linked worktree)
- [ ] format.py: stop at P4CONFIG + test
- [ ] Bump version to 0.2.0 (both manifests, README)

## Test command
`python3 -m pytest -q`

## Out of scope
- Perforce/Swarm eval cases (no server in CI).
- VCSs other than git and Perforce; hosts other than GitHub and Swarm.

## Decisions
- Skill names `vcs-*` and `host-*`, model-invocable, `user-invocable: false` - prefix avoids triggering on every git mention.
- Detect VCS: git work tree first, then `p4 info` client root containing cwd, else ask - git is cheap and common.
- Detect host: host-github when origin URL is github.com and `gh` works; host-swarm when `p4 property -l -n P4.Swarm.URL` is set; else none.
- Two layers: VCS (isolate, checkpoint, diff-scope, publish, land) and optional host (fetch-issue, fetch-review, open-draft, ready-for-review) - git has no PRs; GitHub and Swarm do.
- Perforce: pending CL (task stream only if repo uses streams); checkpoint/publish = shelve; user submits; .flow files shelved in CL and reverted before ready.
- Swarm in its own host skill - optional in p4 shops, REST API for fetch-review, own detection.
- fetch-issue optional; no host or no fetch-issue -> tracker tool, else ask - issues aren't a VCS concern.
- guard p4 read allowlist; stop_gate git -> p4 clientRoot -> cwd; format stops at P4CONFIG; tests for each.
- No Perforce eval; bump to 0.2.0.
- Git: regular branches and worktrees both supported; branch in place is the default, worktree offered only when the default branch has unrelated changes; never check out the default branch; resume across worktrees - user wants both modes.
- Perforce: CL workspace default, existing task/dev stream supported, streams created only on request, classic branches never created - stream/branch layout is a depot convention.

## Open questions
- [x] Q1-Q7 interview round 1 - accepted all
- [x] Q8 split VCS and review-host layers, Swarm in host-swarm - yes
- [x] Q9 git worktrees and regular branches - yes, both
- [x] Q10 Perforce CL workspaces and streams - yes

## Status
Awaiting GATE 1

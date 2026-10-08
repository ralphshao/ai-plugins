# Make flow version-control agnostic

## Goal
flow runs the same plan/build/ship loop in a git repo or a Perforce
workspace. Phase skills name VCS operations; a `vcs-git` or `vcs-perforce`
skill says how to do each one.

## Acceptance criteria
- `skills/vcs-git/SKILL.md` and `skills/vcs-perforce/SKILL.md` exist, each
  defining the required operations: isolate, checkpoint, diff-scope,
  publish-draft, ready-for-review, land. fetch-issue is optional: vcs-git
  defines it, vcs-perforce doesn't.
- Phase skills (flow, start, plan, ship) and deep-review contain no `git`
  or `gh` commands; they call the operations and say how to pick the skill.
- Reviewer/tester agents take the diff command from the caller, git or p4.
- guard.py lets reviewers run read-only p4 subcommands and blocks writes
  and connection-changing global flags.
- stop_gate.py finds the root in a p4 workspace with no git.
- format.py stops its upward walk at a P4CONFIG file.
- flow version 0.2.0 in both manifests and README.
- `python3 -m pytest -q` passes.

## Seams under test
- `guard.check_bash` via the hook - catches: p4 allow/deny list / misses: real p4 behavior
- `stop_gate.py` run as a hook with a fake `p4` on PATH - catches: root fallback order / misses: real p4 info output variants
- `format.ancestors` - catches: walk stops at P4CONFIG / misses: nothing relevant
- layout test over skill files - catches: missing required operation in a VCS skill, git/gh commands leaking back into phase skills / misses: prose quality

## Steps
- [ ] Add vcs-git skill (moves git + gh steps out of phases)
- [ ] Add vcs-perforce skill
- [ ] Rewrite flow, start, plan, ship, deep-review to use operations; layout test
- [ ] Generalize agents' scope wording (code-reviewer, review-validator, tester)
- [ ] guard.py: p4 read-only allowlist + tests
- [ ] stop_gate.py: p4 clientRoot fallback + test
- [ ] format.py: stop at P4CONFIG + test
- [ ] Bump version to 0.2.0 (both manifests, README)

## Test command
`python3 -m pytest -q`

## Out of scope
- Perforce eval cases (no p4 server in CI).
- VCSs other than git and Perforce.
- Non-GitHub trackers for git repos.

## Decisions
- Skill names `vcs-git`, `vcs-perforce`, model-invocable, `user-invocable: false` - prefix avoids triggering on every git mention.
- Detect: git work tree first, then `p4 info` client root containing cwd, else ask - git is cheap and common.
- Shared operation contract (isolate, checkpoint, diff-scope, publish-draft, ready-for-review, land) - phases stay VCS-free.
- fetch-issue optional; start uses it if defined, else a connected tracker tool, else asks - Perforce has no issue tracker, and issues aren't a VCS concern.
- Perforce: pending CL (task stream only if repo uses streams); checkpoint = shelve; Swarm review when present, else shelved CL; user submits; .flow files shelved in CL and reverted before ready.
- gh issue/PR steps live in vcs-git.
- guard p4 read allowlist; stop_gate git -> p4 clientRoot -> cwd; format stops at P4CONFIG; tests for each.
- No Perforce eval; bump to 0.2.0.

## Open questions
- [x] Q1-Q7 interview round 1 - accepted all recommendations

## Status
Awaiting GATE 1

# 6. Flow runs VCS and review-host steps through two skill layers

Status: accepted (#8, 2026-10-08)

## Context

Flow 0.1.0's phase skills (`start`, `plan`, `ship`, `deep-review`) ran
`git` and `gh` commands directly, so flow only worked in a git repo hosted on
GitHub. We wanted it to work in Perforce workspaces too, and to review
already-committed code (a SHA, a PR in any state, a submitted changelist, a
Swarm review).

Git itself has no pull requests or issues; GitHub adds them. Perforce has no
issue tracker, and Helix Swarm, which adds review, is optional in many
Perforce shops.

## Decision

Phase skills name operations and never run VCS commands. Two kinds of skill
implement them:

- **VCS skill**, required: `vcs-git` or `vcs-perforce`. Operations:
  `find-state`, `isolate`, `checkpoint`, `diff-scope`, `publish`,
  `drop-state`, `land`, `resolve-target`.
- **Review-host skill**, optional: `host-github` or `host-swarm`. Operations:
  `fetch-issue`, `fetch-review`, `open-draft`, `ready-for-review`. A host may
  leave operations out (Swarm has no `fetch-issue`).

Each skill has a Detect section; the `flow` skill's "VCS and review host"
section picks them and says what happens when there is no host or the host
lacks an operation. The skills are model-invocable but hidden from the slash
menu (`user-invocable: false`), and the `vcs-`/`host-` prefixes keep them from
triggering on every mention of git.

## Alternatives

- **One skill per VCS, with the host folded in** (GitHub inside `vcs-git`,
  Swarm inside `vcs-perforce`). Rejected: a git repo on GitLab or a Perforce
  shop without Swarm would inherit host steps that don't apply, and Swarm's
  REST API and detection have nothing to do with p4 itself.
- **`fetch-issue` as a required VCS operation.** Rejected: issues aren't a
  VCS concern, and Perforce has no tracker. With no host, flow falls back to a
  connected tracker tool or asks for the text.
- **Keep git and gh in the phases, branching on VCS inline.** Rejected: every
  phase would carry both VCSs, and adding a third would mean editing all of
  them.

## Consequences

- Adding a VCS or host is one new skill implementing the operations above.
  `tests/test_flow_layout.py` pins the operation names and fails if `git`,
  `gh`, or `p4` commands appear in any other skill.
- The operation names are now an interface: renaming one means editing every
  `vcs-*`/`host-*` skill and the phases that call it.
- Perforce keeps `.flow/` in a separate, never-submitted state changelist,
  since stream-mode steps are submitted and plan files must never reach the
  depot.
- The Perforce and Swarm steps are untested against a real server; CI has
  none.

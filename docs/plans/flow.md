# Plan: `flow` plugin

An engineering workflow plugin for Claude Code and Codex: skills for each
phase, subagents for review and testing, hooks for the rules that must hold.
It lives in this marketplace as a second local plugin next to `ai-plugins`,
so any machine or cloud session gets it by installing from the marketplace.

Status: design approved, not implemented.

## Goals

- One entry point (`/flow`) that sizes a task and walks it through the right
  phases, starting from a prompt (usual case) or a GitHub issue.
- Two human gates: approve the plan, approve the merge. Everything between
  runs unattended.
- Portable: no absolute paths, no dependence on `~/.claude` contents, stdlib
  Python only, works on Linux/macOS/Windows and in cloud sessions.
- Claude Code and Codex from the same skill and hook files.

## Non-goals (v1)

- No trackers other than GitHub Issues.
- Per-repo setup ceremony (glossary, domain docs, triage labels).
- Multi-agent parallel implementation for large tasks (revisit later; see
  `implement-spec` in mattpocock/skills for the pattern).

## Layout

```
plugins/flow/
  .claude-plugin/plugin.json
  .codex-plugin/plugin.json
  skills/
    flow/          user-invoked router
    start/         user-invoked: prompt or issue -> branch -> brief
    plan/          user-invoked: explore -> interview -> plan.md -> GATE 1
    ship/          user-invoked: verify -> review -> PR -> GATE 2
    retro/         user-invoked: environment improvements after a session
    setup-codex/   user-invoked: install Codex agent TOMLs on this machine
    interview/     model-invocable discipline
    tdd/           model-invocable discipline
    deep-review/   model-invocable (moved from ~/.claude/skills)
    pr-body/       model-invocable discipline
  agents/
    code-reviewer.md     moved from ~/.claude/agents
    review-validator.md  moved from ~/.claude/agents
    tester.md            moved from ~/.claude/agents
  hooks/
    hooks.json
    guard.py       dispatches to the reviewer/tester guards by agent_type
    test_gate.py   Stop hook
    format.py      PostToolUse format/lint
  scripts/
    codex_agents.py  generates ~/.codex/agents/*.toml from agents/*.md
```

## Invocation rule

- User-invoked skills (`disable-model-invocation: true`) orchestrate:
  `flow`, `start`, `plan`, `ship`, `retro`, `setup-codex`.
- Model-invocable skills hold reusable discipline: `interview`, `tdd`,
  `deep-review`, `pr-body`.
- An orchestrator may call a discipline skill, never another orchestrator.
  (`/flow` routes by telling the user or by following the phase skill's
  steps; it does not call `/plan` as a skill.)

Borrowed from mattpocock/skills (MIT); credit in each borrowing skill.

## Sizing

`/flow <prompt | #issue | issue URL>` classifies and states its call; the user
can override ("treat as large").

| Size    | Signal                         | Path                                                                 |
|---------|--------------------------------|----------------------------------------------------------------------|
| Trivial | typo, one-liner, obvious fix   | do it, quick review, no branch ceremony, no gates                    |
| Normal  | feature or bug, a few files    | start -> plan (at most one interview round) -> GATE 1 -> build -> ship -> GATE 2 |
| Large   | cross-module, new subsystem    | Normal, plus a full interview, an ADR for one-way-door decisions, tester pass |

## Phases

### start
- Input: prompt or GitHub issue (`gh issue view`).
- Creates a branch (worktree when the host supports it) and
  `.flow/<slug>/brief.md`: the request, the issue link, constraints.

### plan
1. Explore with a subagent (`Explore`, or Codex `explorer`); facts are the
   agent's job, never the user's.
2. Interview (`interview` skill): rounds of numbered questions covering the
   current frontier of decisions, each with a recommended answer, worded so
   "yes" accepts it. Normal: at most one round. Large: until the frontier is
   empty.
3. Write `.flow/<slug>/plan.md` from the template below and commit it.
4. GATE 1: user approves. On approval, push and open a draft PR whose body
   links the plan.

`plan.md` template:

```
# <title>
## Goal
## Acceptance criteria
## Seams under test
- <public interface> - catches: ... / misses: ...
## Steps
- [ ] ...
## Test command
<command the Stop gate runs>
## Out of scope
## Decisions
- <decision> - <one-line reason>
## Open questions
- [ ] Q1 <question> - recommended: <answer> - blocks: <steps>
## Status
```

### build
- Follows `tdd`: test only at the seams approved in the plan; one failing
  test, then the minimum code to pass, per slice; no tautological or
  implementation-coupled tests; refactoring waits for review.
- Ticks steps in `plan.md` as they land, small commits.

### ship
1. Verify: no unticked open questions in `plan.md`; run the plan's test
   command; Large tasks also get a `tester` pass.
2. Review: `deep-review` (correctness/spec, standards/quality, silent
   failures, plus a Fowler-smell lens where the repo's own standards win).
   Resolve the diff base and confirm the diff is non-empty before spawning
   reviewers.
3. Fix confirmed findings.
4. Remove `.flow/<slug>/` from the branch in its own commit.
5. Write the PR body with `pr-body`, mark the PR ready.
6. GATE 2: the user merges.

`pr-body` template: summary as the smallest visual that makes the change
clear; before/after evidence; merge danger (one-way or two-way door, blast
radius); decisions made between the gates, copied from `plan.md`; links to
the issue.

### retro (optional)
After a session, suggest environment fixes, most severe first. Mechanical
rules become a hook, lint rule, or CI check; judgment calls go to a standards
doc; CLAUDE.md/AGENTS.md hold only navigation pointers.

## Decisions between gates

The interview settles known decisions before GATE 1. Decisions that surface
during build or ship follow this rule. It uses concrete triggers, not the
agent's self-rated confidence.

Escalate (ask the user) when any of these hold:
- The plan doesn't cover the decision, or the code contradicts the plan.
- It changes scope or acceptance criteria.
- It is a one-way door: public API, schema or migration, data deletion,
  security or auth, a new dependency.
- Two or more plausible options differ in user-visible behavior.
- A test or review result shows a requirement is ambiguous.
- `review-validator` returns UNSURE on a high-severity finding.

Otherwise decide and log: add a line to `## Decisions` in `plan.md` with a
one-line reason. `/ship` copies the list into the PR body, so the user
reviews every unattended decision at GATE 2.

Escalation is park-and-continue:
1. Add the question to `## Open questions` in `plan.md` (interview format:
   recommended answer, worded so "yes" accepts it, plus the steps it blocks),
   commit, and ask it in chat.
2. Send a push notification where the host supports one (Claude Code); on
   Codex the chat question is the only signal.
3. Keep working on steps the question doesn't block.
4. Stop only when every remaining step is blocked. The Stop test gate
   allows this stop while unanswered open questions exist.
5. On an answer, tick the question, record it under `## Decisions`, and
   unblock its steps. `/flow` resuming on another machine picks up answers
   written into `plan.md` directly.

## State and handoff

- `.flow/<slug>/` (brief, plan) is committed on the feature branch so it
  travels to other machines and cloud sessions; `/ship` strips it before
  merge.
- `/flow` with no argument on a branch that has `.flow/` resumes from the
  plan's Status, unchecked steps, and open questions.

## Hooks

One `hooks/hooks.json`, shared by Claude Code and Codex (same event schema;
Codex sets `CLAUDE_PLUGIN_ROOT` for compatibility). Commands reference
`${CLAUDE_PLUGIN_ROOT}`.

| Hook | Event / matcher | Behavior |
|------|-----------------|----------|
| `guard.py` | PreToolUse `Bash\|Write\|Edit` | Reads `agent_type`. `flow:code-reviewer` and `flow:review-validator` get the read-only Bash guard; `flow:tester` gets the tester guard; anything else exits 0. |
| `format.py` | PostToolUse `Edit\|Write` | Runs the repo's formatter/linter on the edited file if one is detectable; no-op otherwise. |
| `test_gate.py` | Stop | Active only when the branch has `.flow/<slug>/plan.md` with a test command. Runs it; on failure blocks the stop with the failing output. Allows the stop while `## Open questions` has unticked items (parked work). Honors `stop_hook_active` to avoid loops. |

Why a dispatcher: Claude Code ignores `hooks:` frontmatter on plugin agents,
so the guards the agents carry today would silently stop running after the
move. Plugin-level hooks still fire inside subagents and carry `agent_type`.

Known limits:
- Codex hook input has no `agent_type`, so `guard.py` cannot tell subagents
  apart there. On Codex, reviewer read-only comes from `sandbox_mode` in the
  generated TOML instead (see below).
- Codex skips plugin hooks until the user trusts them, and Codex cloud
  orchestration doesn't run plugin hooks.

## Agents

- `agents/*.md` (Claude format) are the single source.
- `code-reviewer` keeps its `karpathy-guidelines` and `ponytail-review`
  skill preloads as optional: used when those plugins are installed.
- Codex: `/flow:setup-codex` runs `scripts/codex_agents.py`, which writes
  `~/.codex/agents/flow-<name>.toml` from each `.md` (`name`, `description`,
  `developer_instructions` from the body; `sandbox_mode = "read-only"` for the
  reviewers). Skills that spawn agents fall back to Codex's built-in
  `explorer`/`worker` with the same prompt when the TOML isn't installed.

## Marketplace changes

- Register `flow` in both marketplace files as a local source, the same
  shape as `ai-plugins` (`"./plugins/flow"` for Claude,
  `{"source": "local", "path": "./plugins/flow"}` for Codex), and in the
  README table. `ai-plugins.py update` already skips non-remote sources.
- Update AGENTS.md: `ai-plugins` is no longer the only local plugin.

## Migration of existing user config

1. Copy `~/.claude/agents/{code-reviewer,review-validator,tester}.md`,
   `reviewer-guard.py`, `tester-guard.py`, and `~/.claude/skills/deep-review`
   into the plugin; strip `hooks:` frontmatter from the agents; move
   `test_guards.py` into `tests/`.
2. Install the plugin, verify the guards fire via `guard.py`
   (a reviewer-agent write attempt is blocked).
3. Delete the originals from `~/.claude`.

## Build order

1. Skeleton, both manifests, marketplace + README + AGENTS.md entries.
2. Move agents, `deep-review`, guards; `guard.py` dispatcher; guard tests.
3. `flow`, `start`, `plan`, `ship` + `interview`, `tdd`, `pr-body`. Normal path
   works end to end.
4. `test_gate.py`, then `format.py`, with tests.
5. `setup-codex` + `codex_agents.py`, with a test.
6. `retro`.
7. `claude plugin eval` suite: `/flow` sizing and routing on a handful of
   prompts.
8. Migration step 3 (delete originals) once 1-7 are verified.

## Open items for later

- Large-task parallel implementation (Workflow script or implementer
  subagents in worktrees).
- Optional glossary/ADR domain docs per repo.

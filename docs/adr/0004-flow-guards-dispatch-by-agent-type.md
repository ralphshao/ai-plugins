# 4. Flow's subagent guards run from one plugin hooks.json, picked by `agent_type`

Status: accepted (#7, 2026-10-07; recorded in #11)

## Context

Flow's reviewer and tester agents came from `~/.claude/agents`, where each
carried its guard as `hooks:` frontmatter: reviewers get read-only Bash and
no writes; the tester writes test files only and runs test runners.

Claude Code ignores `hooks:` frontmatter on plugin agents. Moved into the
plugin as they were, the agents would have lost their guards without an
error. Plugin-level hooks do fire inside subagents, and their input carries
`agent_type`.

## Decision

- One `hooks/hooks.json` declares all of flow's hooks. Commands reference
  the plugin root, never absolute paths.
- `guard.py`, a PreToolUse hook on Bash and file writes, reads
  `agent_type` and applies the reviewer guard to flow's reviewer agents and
  the tester guard to `flow:tester`. Every other caller passes through.
- The same file declares the format-on-edit hook (`format.py`), which runs
  only a formatter the repo already opts into and never blocks, and the
  stop gate ([ADR 5](0005-flow-stop-gate-runs-the-plans-tests.md)).

[ADR 8](0008-flow-hooks-shared-by-claude-code-and-codex.md) extended this to
Codex. It supersedes the design plan's Codex notes: Codex hook input does
carry `agent_type` inside subagents, Codex ignores `sandbox_mode`, so
`guard.py` is the read-only control on both hosts, and the `setup-codex`
skill is gone.

## Alternatives

- **Keep `hooks:` frontmatter on the agents.** Not possible: Claude Code
  ignores it on plugin agents.
- **One hook entry per agent.** Rejected: hook matchers select tools, not
  agents, so each entry would still have to check `agent_type`.

## Consequences

- The guards depend on the host sending `agent_type`. A host that stops
  sending it turns the guards into pass-through without an error.
- The tester guard limits what the tester writes and runs, not what the
  tests it writes do. A test file can edit source files when `pytest` runs
  it. This is accepted: closing it would mean judging what test code does,
  and the tester's instructions already forbid editing source.

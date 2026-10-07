---
name: setup-codex
description: Install flow's review and test agents as Codex custom agents on this machine (writes ~/.codex/agents/flow-*.toml). Run once per machine, and again after updating flow.
disable-model-invocation: true
---

Codex can't load agents from a plugin, so this copies them into the user's
Codex agents folder.

1. Find this plugin's root: two folders up from this SKILL.md
   (`${CLAUDE_PLUGIN_ROOT}` in Claude Code).
2. Run `python3 <plugin root>/scripts/codex_agents.py`. It writes
   `flow-code-reviewer.toml`, `flow-review-validator.toml`, and
   `flow-tester.toml` into `$CODEX_HOME/agents/` (default `~/.codex/agents/`),
   overwriting earlier copies. Pass `--dest <dir>` for a project-scoped
   `.codex/agents/` instead.
3. Report the files written. Reviewers get `sandbox_mode = "read-only"`; the
   tester gets `workspace-write`.

Without this step, flow on Codex still works: skills fall back to the
built-in `explorer` (reviewers) and `worker` (tester) agents, given the same
instructions from the plugin's `agents/<name>.md`, but read-only isn't
enforced.

# 3. Flow's hooks serve Claude Code and Codex from one hooks.json

Status: accepted (#10, 2026-10-08)

## Context

Flow's hooks (`guard.py`, `format.py`, `stop_gate.py`) were written for
Claude Code. On Codex they loaded but didn't enforce the same rules. We
compared them with context-mode, which hooks both hosts, and read the
openai/codex source.

Codex behavior this decision relies on, as of openai/codex
`9b738582b13c2cdbeff54af0afd04c50c3e7ba09` (2026-10-08). Paths are under
`codex-rs/`. Check them again before changing the hooks.

- **Hook discovery.** Codex loads a plugin's `hooks/hooks.json` by default
  (`hooks/src/declarations.rs`). It sets `PLUGIN_ROOT` and
  `CLAUDE_PLUGIN_ROOT` as env vars but doesn't substitute them into the
  command text (`hooks/src/engine/discovery.rs`). Hooks are on by default.
  The `plugin_hooks` feature flag has been removed. Plugin hooks run only
  after the user accepts Codex's trust prompt.
- **Tool names.** File edits arrive as `tool_name: "apply_patch"`, and
  `Write` and `Edit` are matcher aliases for it
  (`core/src/tools/hook_names.rs`). The patch text is in
  `tool_input.command`, and there is no `file_path`
  (`core/src/tools/handlers/apply_patch.rs`). Subagent spawns arrive as
  `spawn_agent`, with `Agent` as a matcher alias. Their `tool_input` holds
  `agent_type` and `message`.
- **Subagents.** A hook running inside a spawned subagent gets
  `agent_type` set to the role name, such as `flow-tester`
  (`core/src/hook_runtime.rs`). `Stop` fires for the root turn only, and
  `SubagentStop` fires for children.
- **Agent roles.** A role file can set instructions, model, reasoning,
  personality, and service tier, and can turn features or skills off. It
  can't set `sandbox_mode`: a child gets its parent's sandbox and approval
  policy (`core/src/agent/role.rs`, `core/src/agent/child_config.rs`). The
  list of roles is read when the session loads its config. Each role file
  is read again at every spawn.
- **Windows.** Hooks run through `cmd.exe` (`COMSPEC`), which doesn't
  expand `${...}`. A hook entry can give a `commandWindows`, used instead
  of `command` on Windows (`config/src/hook_config.rs`). Claude Code's
  `claude plugin validate` accepts the extra key.

## Decision

- **One `hooks/hooks.json` for both hosts.** The scripts handle each host's
  payload themselves: `apply_patch` paths come from the patch headers, and
  both agent naming styles (`flow:tester`, `flow-tester`) are recognized.
- **`guard.py` is the read-only control on both hosts.** Codex ignores
  `sandbox_mode`, so the generated role files no longer set it. A crash in
  the guard blocks the call for flow's agents and allows it for every other
  caller.
- **A PreToolUse hook on `Agent` keeps the Codex agents current**
  (`hooks/codex_agents.py`). On a `flow-*` spawn it rewrites out-of-date
  role files and deletes generated ones that no agent matches. If the
  files are missing, it installs them and blocks that spawn, because Codex
  reads the list of roles only at session start. This replaces the
  `setup-codex` skill.
- **Every hook has a `commandWindows`**, and the POSIX `command` falls back
  from `python3` to `python`.

## Alternatives

- **A second `.codex-plugin/hooks.json` and adapter scripts per platform,
  as context-mode does.** Rejected. Codex's default path, its env var, and
  its matcher aliases make one file enough. A second copy would drift.
- **Rewriting `hooks.json` to absolute paths at runtime, as context-mode
  does.** Rejected. It edits the installed plugin cache to work around a
  problem `commandWindows` solves.
- **Keep `sandbox_mode` and `setup-codex`.** Rejected. The setting does
  nothing in Codex now. The skill had to be re-run by hand after every
  flow update.
- **Use the spawn hook to add instructions to subagent prompts, as
  context-mode does.** Rejected. Each flow agent carries its own
  instructions.
- **Python launcher scripts (`run.sh`/`run.cmd`), like `ai-plugins`
  uses.** Rejected for now. They would add a process to every guarded tool
  call. They would also skip the Microsoft Store `python3` stub, which the
  fallback doesn't.

## Consequences

- When Codex changes any behavior listed above, flow's hooks may break
  without an error. Re-check this list before changing them.
- On Codex, the built-in `explorer` and `worker` agents that flow falls
  back to before its agents are installed are not guarded.
- The first flow spawn in a new Codex install is blocked once, and the
  user has to restart Codex.
- `commandWindows` and the `python` fallback are untested on a real Windows
  host. The Windows CI job runs the hook scripts directly, not through
  `hooks.json`.

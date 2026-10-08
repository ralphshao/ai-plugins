# Make flow's hooks enforce the same rules on Codex as on Claude Code

## Goal
flow's guard and format hooks act on Codex edits and Codex subagents the same
way they do on Claude Code, and a guard crash never silently lets a flow
subagent through.

## Findings

What flow has today: one `hooks/hooks.json` (PreToolUse `guard.py`,
PostToolUse `format.py`, Stop `stop_gate.py`), `${CLAUDE_PLUGIN_ROOT}` in the
commands, and `python3` as the launcher.

Facts checked in the current openai/codex source (`codex-rs/`):

1. Codex loads `hooks/hooks.json` from a plugin root by default
   (`hooks/src/declarations.rs`). It sets both `PLUGIN_ROOT` and
   `CLAUDE_PLUGIN_ROOT` (`engine/discovery.rs:265`). flow's single file
   already loads on Codex. Codex enables hooks by default (`features` key
   `hooks`, Stable). `plugin_hooks` is now `Stage::Removed`, so the flag that
   context-mode's README asks for is no longer needed.
2. Codex edits files with `apply_patch`, and `Write` and `Edit` are matcher
   aliases for it (`core/src/tools/hook_names.rs`). So flow's `Write|Edit`
   matchers already fire on Codex edits. But stdin has
   `tool_name: "apply_patch"` and `tool_input: {"command": "<patch text>"}`,
   with no `file_path`. Result:
   - `guard.py` checks only `tool in ("Write", "Edit")`, so a Codex edit
     passes the guard unchecked.
   - `format.py` finds no `file_path`, so it never formats on Codex.
3. Codex now sends `agent_type` for spawned subagents. The value is the role
   name (`core/src/hook_runtime.rs:1057`). For flow's generated agents, the
   role names are `flow-code-reviewer`, `flow-review-validator`, and
   `flow-tester`. `guard.py` knows only the `flow:` names, so it lets these
   agents through. The plan doc says "Codex hook input has no `agent_type`".
   That is no longer true.
4. Stop: Codex sends `stop_hook_active` and honors
   `{"decision":"block","reason":...}` (`events/stop.rs`). `stop_gate.py`
   already works there.
5. If `guard.py` crashes (bad JSON, or an unexpected exception), it exits 1.
   Both hosts treat exit 1 as a non-blocking error, so the tool call runs. A
   bug in the guard turns the reviewer read-only rule off silently.
6. Codex ignores `sandbox_mode` in an agent role file. A role can only set
   instructions, model, reasoning, personality, service tier, and turn
   features or skills off (`core/src/agent/role.rs`, `AgentRoleOverrides`).
   The child agent takes the parent's sandbox and approval policy
   (`core/src/agent/child_config.rs`). So the `sandbox_mode = "read-only"`
   that `codex_agents.py` writes does nothing, and on Codex the guard hook
   is the only read-only control for reviewers. This makes findings 2 and 3
   more urgent.
7. Codex reads the list of agent roles once, when the session loads its
   config. It reads each role file's contents when it spawns that role
   (`role.rs`, `load_role_layer_toml`). So an updated role file takes effect
   on the next spawn. A newly added role file takes effect in the next
   session.
8. On Windows, Codex runs hook commands through `cmd.exe` (`COMSPEC`) and
   only sets `PLUGIN_ROOT` as an env var. It does not substitute it into
   the command text (`engine/discovery.rs`, `command_runner.rs`). cmd.exe
   does not expand `${CLAUDE_PLUGIN_ROOT}`, so flow's hooks can't start on
   Codex for Windows. Codex accepts a `commandWindows` key next to
   `command` for this case (`config/src/hook_config.rs`). Claude Code's
   `claude plugin validate` accepts the extra key.

From context-mode:

- Worth copying: normalize each platform's tool payload inside the script
  (its `hooks/codex/pretooluse.mjs` reads `apply_patch`). Also, decide on
  purpose what a crash does (its `run-hook.mjs` logs the error and exits 0).
  For a guard, the right choice is to fail closed for the agents it guards.
- Not worth copying: a second `.codex-plugin/hooks.json`, per-platform
  adapter scripts, one matcher group per tool, and rewriting `hooks.json` to
  absolute paths at runtime. Codex's default path, its env var, and its
  matcher aliases make one shared file enough. Rewriting files at runtime
  also edits the plugin cache.

How context-mode handles subagents, and what applies to flow:

- It detects a subagent call by `agent_id` or `agent_type` on stdin
  (`hooks/pretooluse.mjs:167`), then changes behavior for that call. flow's
  guard already chooses a policy by `agent_type`. The gap is the Codex role
  names (finding 3).
- It hooks the spawn call itself: PreToolUse on `Agent` (Codex alias for
  `spawn_agent`) appends routing rules to the subagent's prompt through
  `updatedInput` (`core/routing.mjs:892`). Not needed for flow: each flow
  agent carries its own instructions. On Codex, `updatedInput` also only
  works on codex-cli 0.141.0 or later.
- It tells a subagent only about tools the subagent can call. Subagents with
  a fixed tool set get no ctx_* advice, and Claude Code subagents get a
  ToolSearch step first for deferred tools. flow's Codex agent preamble
  already does the equivalent ("use the closest tool you do have").
- It records subagent launches and results for its post-compaction resume
  snapshot. Not needed: flow keeps its task state in `plan.md`.
- It registers no `SubagentStop` hook. Both hosts fire `Stop` only for
  the root turn and `SubagentStop` for a child turn (codex
  `core/src/hook_runtime.rs:400`). So `stop_gate.py` never runs the test
  command when a reviewer or tester returns. That is correct as it is.

## Acceptance criteria
- A Codex `flow-code-reviewer` or `flow-review-validator` subagent gets the
  same Bash rules as on Claude Code, and its `apply_patch` call is denied.
- A Codex `flow-tester` `apply_patch` call that adds, updates, deletes, or
  moves a file outside test paths is denied. A call that touches only test
  paths is allowed.
- A Claude reviewer or tester that sends `apply_patch` gets the same result
  (one code path for both hosts).
- `format.py` formats every file that an `apply_patch` adds, updates, or
  moves to, under the same rules as the Claude `file_path` case.
- With a flow `agent_type`, invalid JSON on stdin or an exception inside the
  check makes `guard.py` exit 2. Other callers keep exit 0 on a guard bug.
- The main session and non-flow agents still pass through untouched.

- When Codex spawns a `flow-*` role whose TOML differs from the current
  plugin's agents, the hook rewrites the file before the spawn and allows
  it. When the file is missing, the hook writes all three files to
  `$CODEX_HOME/agents/` and denies the spawn with a restart message.
- The `setup-codex` skill is gone. Nothing in the plugin tells the user to
  run it.
- Each hook in `hooks.json` has a `commandWindows` that starts it under
  `cmd.exe`, and a `command` that falls back to `python` when `python3`
  is not on PATH.

## Seams under test
- `guard.py` as a process (stdin JSON in, exit code and stderr out), as in
  `tests/test_flow_guard.py`. Catches: wrong allow or deny per agent, tool,
  and patch. Misses: whether the host actually sends that payload.
- `format.py` as a process, as in `tests/test_flow_hooks.py`. Catches: which
  files a patch causes to be formatted. Misses: real formatter behavior
  (tests use a stub formatter).
- `hooks/codex_agents.py` as a process with `CODEX_HOME` set to a temp
  folder. Catches: rewrite, install, deny, and pass-through for non-flow
  spawns. Misses: whether Codex reloads the role (finding 7 says it does).
- `hooks.json` structure in `tests/test_flow_layout.py`. Catches: a hook
  without `commandWindows`, or one that points outside the plugin. Misses:
  whether cmd.exe runs it.

## Steps
- [ ] guard: add the Codex role names (`flow-code-reviewer`,
      `flow-review-validator`, `flow-tester`) to the policy sets. Add tests.
- [ ] guard: treat `apply_patch` as a write. Parse the `*** Add File:`,
      `*** Update File:`, `*** Delete File:`, and `*** Move to:` headers from
      `tool_input.command`. Reviewers: deny. Tester: run `check_test_path` on
      each path. Deny a patch with no parseable header. Add tests.
- [ ] format: for `apply_patch`, format each Add, Update, or Move-to path
      that exists after the edit. Put the header parser in one place that
      both hooks import (`hooks/patch.py`, next to the scripts). Add tests.
- [ ] guard: fail closed. For a flow `agent_type`, catch a JSON or any other
      error, print it, and exit 2. If `agent_type` can't be read, exit 0 as
      today. Add tests.
- [ ] codex agents: stop writing `sandbox_mode` in `codex_agents.py`
      (finding 6). Change its `PREAMBLE`, which says "your sandbox enforces
      the same limits", to say flow's hooks enforce them. Update
      `tests/test_flow_codex_agents.py`.
- [ ] spawn hook (Q4): move `scripts/codex_agents.py` to
      `hooks/codex_agents.py` and make it the PreToolUse hook for `Agent`
      (Codex sends `spawn_agent`). Only `tool_input.agent_type` starting
      with `flow-` acts. Refresh the role file where it already exists
      (project `.codex/agents/`, else `$CODEX_HOME/agents/`). If it is
      missing, write all three to `$CODEX_HOME/agents/` and deny. Drop the
      CLI. Add tests.
- [ ] remove the `setup-codex` skill. Update `skills/flow/SKILL.md` ("once
      `setup-codex` has installed them") and `tests/test_flow_layout.py`.
- [ ] Windows (Q2, option C): add `commandWindows` to each hook,
      `python "%PLUGIN_ROOT%\hooks\<name>.py"`. Change each `command` to
      pick `python3` and fall back to `python`:
      `"$(command -v python3 || command -v python)" "${CLAUDE_PLUGIN_ROOT}/hooks/<name>.py"`.
      Add a layout test that every hook has both, and a test that runs one
      `command` through `sh` with only `python` on PATH.
- [ ] docs: update the `guard.py` and `format.py` docstrings, and the
      flow skill's Codex section: the agents install themselves on the first
      spawn, and the `explorer` and `worker` fallback agents are not
      guarded. Add one line telling the user to accept the hook trust prompt
      on Codex.
- [ ] stop gate (Q1): in a git repo, after a passing run, save a
      fingerprint of `HEAD`, `git status --porcelain`, `git diff`, and the
      contents of untracked files.
      Skip the run when the current fingerprint matches. Store it in the
      system temp folder, keyed by the repo root. Outside git, run every
      time as today. Add tests.

## Test command
`python3 -m pytest tests/test_flow_guard.py tests/test_flow_hooks.py tests/test_flow_layout.py tests/test_flow_codex_agents.py -q`

## Out of scope
- A separate Codex `hooks.json` or per-platform adapter scripts (see
  Findings).
- Changing the plugin version (AGENTS.md says to ask; see Q3).
- Editing `docs/plans/flow.md`: plans aren't maintained once implemented.

## Decisions
- One shared `hooks/hooks.json` for both hosts - Codex reads the same path,
  sets `CLAUDE_PLUGIN_ROOT`, and aliases `Write|Edit` to `apply_patch`.
- The guard fails closed only for flow agents - the guard exists for them.
  Failing closed for everyone would let one guard bug block the main session.
- Shared `hooks/patch.py` instead of copying the parser into two scripts -
  both hooks need the same header rules, and the scripts already sit in one
  folder that Python puts on `sys.path`.
- No `SubagentStop` hook - nothing in flow needs to run when a subagent
  returns.
- The spawn hook replaces `setup-codex` (user, Q4) - after the first
  install, the agent files stay current without a manual step.
- One `hooks/codex_agents.py` that renders and syncs - the CLI had one
  caller (`setup-codex`), and that caller is gone.
- Refresh a role file where it already is, and install new files only to
  `$CODEX_HOME/agents/` - this keeps a project-scoped install working
  without guessing where a new one should go.
- Stop-gate fingerprint goes in the system temp folder, not `.flow/` - a
  file under `.flow/` would change `git status` and so change the
  fingerprint. A lost temp file only costs one extra test run.
- Stop-gate fingerprint hashes untracked file contents - `git status`
  lists only their names, so an edit to a new, untracked test file would
  otherwise skip the run.
- Stop-gate fingerprint is git-only - a Perforce fingerprint needs more
  `p4` calls than it saves. Perforce keeps today's behavior.
- Read the patch from `tool_input.command` only - the current Codex source
  sends only that key. context-mode also reads `patch`, but no current
  Codex build sends it.

## Open questions
- [x] Q1 Skip the stop-gate test run when nothing changed since the last
      passing run? - answered yes - step added
- [x] Q2 How should hooks start on Windows? - answered C: `commandWindows`
      per hook, plus a `python3`-then-`python` fallback in `command`
- [x] Q3 Bump flow from 0.2.1 to 0.2.2 in both `plugin.json` files and
      in the flow entry of `.claude-plugin/marketplace.json`? - answered
      yes, but only when the user says so - blocks: the bump commit only
- [x] Q4 Add a PreToolUse hook on `Agent` (Codex `spawn_agent`). When Codex
      spawns a `flow-*` role, the hook rewrites that role's TOML file if it
      differs from what `codex_agents.py` renders from the current plugin.
      If the role file is missing, it writes all three files and denies the
      spawn with "flow agents installed; restart Codex, or use the
      explorer/worker fallback". OK to have a hook write to
      `$CODEX_HOME/agents/`? - answered yes, and remove `setup-codex`
- [ ] Q5 When the spawn hook syncs, also delete `flow-*.toml` files that
      carry flow's "Generated by" header but match no current agent (for
      example, after an agent is renamed)? - recommended: yes - blocks:
      spawn hook step
- [ ] Q6 Removing the `setup-codex` skill is a user-visible removal. Make
      the bump 0.3.0 instead of 0.2.2, still only when you say so? -
      recommended: yes - blocks: the bump commit only
- [ ] Q7 On approval, push `flow/flow-hooks-codex-parity` and open a draft
      PR (the flow plan phase does this)? - recommended: yes - blocks: none

## Status
Awaiting GATE 1

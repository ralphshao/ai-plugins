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

## Seams under test
- `guard.py` as a process (stdin JSON in, exit code and stderr out), as in
  `tests/test_flow_guard.py`. Catches: wrong allow or deny per agent, tool,
  and patch. Misses: whether the host actually sends that payload.
- `format.py` as a process, as in `tests/test_flow_hooks.py`. Catches: which
  files a patch causes to be formatted. Misses: real formatter behavior
  (tests use a stub formatter).

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
- [ ] docs: update the `guard.py` and `format.py` docstrings, and the
      `setup-codex` note that "read-only isn't enforced". After this change,
      the generated agents are also guarded by the hook. The `explorer` and
      `worker` fallback agents are still not guarded. Add one line telling
      the user to accept the hook trust prompt on Codex.

## Test command
`python3 -m pytest tests/test_flow_guard.py tests/test_flow_hooks.py tests/test_flow_layout.py -q`

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

## Open questions
- [ ] Q1 The stop gate runs the full test command at the end of every turn
      while the plan is Approved, including turns that only answer a
      question. Skip the run when `HEAD` and `git status --porcelain` are the
      same as at the last passing run (store a hash under `.flow/<slug>/`,
      gitignored)? - recommended: yes, as an extra step in this change -
      blocks: a new step 6
- [ ] Q2 Hook commands call bare `python3`. On Windows, that is often the
      Microsoft Store stub, so every hook fails as a non-blocking error.
      Leave this out of this change, and fix it in a follow-up that is
      checked on a real Windows host? - recommended: yes - blocks: none
- [ ] Q3 Bump flow from 0.2.1 to 0.2.2 in both manifests and both
      marketplace files? - recommended: yes, as the last commit before ship -
      blocks: ship

## Status
Awaiting GATE 1

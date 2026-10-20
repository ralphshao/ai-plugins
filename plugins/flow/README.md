# flow

An engineering workflow for Claude Code and Codex. The `flow` skill takes
one task from a prompt or issue to a review that's ready to land. You
approve it twice: the plan (GATE 1) and landing it (GATE 2). Between the
gates the agent works on its own, and parks questions it can't decide
alone instead of guessing.

flow works in git repos (GitHub for reviews) and in Perforce workspaces
(Helix Swarm for reviews).

## Stages

1. **start** - turns the prompt or issue into its own branch (or worktree,
   or changelist) and writes `.flow/<slug>/brief.md` with the request
   verbatim.
2. **plan** - an explorer subagent maps the code, `interview` settles open
   decisions with you, and flow writes `plan.md`: acceptance criteria, seams
   under test, steps, the test command, and decisions.
3. **GATE 1** - you approve the plan. Nothing is built before that.
4. **build** - `tdd` slices at the plan's seams, one commit per step.
   Questions the plan doesn't cover are parked under `## Open questions`
   instead of guessed. `stop_gate.py` blocks stopping while the test command
   fails, and `guard.py` blocks weakening the plan's test command or existing
   tests.
5. **ship** - reruns the tests, then `deep-review` checks the diff against
   `plan.md` with parallel lenses and a validator per file; confirmed
   findings get fixed. `.flow/` is deleted, and the review is marked ready.
6. **GATE 2** - you land it. flow never merges.

Trivial tasks skip all but build: one commit on its own branch, pushed;
opening a review is up to you. Large tasks add two
contrasting plan drafts, ADRs for one-way doors, and a `tester` pass in
ship.

## Usage

In Claude Code and Codex:

```
/flow:flow <prompt | #issue | issue URL>   start a task
/flow:flow                                 resume the task in .flow/
```

flow sizes the task first: **Trivial** for typos, docs, and formatting;
**Normal** for a feature or bug fix; **Large** when it crosses modules or
redesigns an API. Say "treat as large" to override.

Task state lives in `.flow/<slug>/` (`brief.md`, `plan.md`) and is committed
with the work, so a task can resume on another machine. `ship` removes it
before the review is marked ready.

## Skills

| Skill | Does |
| --- | --- |
| `flow` | Entry point. Sizes the task and runs the phases below. |
| `start`, `plan`, `ship` | The phases. `flow` runs them in order; you can also run one yourself. |
| `tdd` | Red-green slices at the seams the plan lists. |
| `interview` | Rounds of numbered questions with recommended answers until no decision is open. |
| `deep-review` | Parallel reviewers, one per lens, with every finding checked by a validator. Lenses: correctness, standards, history (changes that undo an earlier fix; skipped when the diff only adds lines), security (only when the diff touches a trust boundary), and errors (only when it touches error handling). Also usable on its own. |
| `change-body` | The shape of a PR, Swarm review, or changelist description. |
| `brb` | `/flow:brb [duration]`: keeps the prompt cache warm through a break (Claude Code only). Any message cancels it. |
| `retro` | Suggests environment fixes that would have prevented a session's mistakes. |
| `vcs-git`, `vcs-perforce`, `host-github`, `host-swarm` | How each VCS and review-host operation runs. Loaded by the other skills, not invoked by you. |

## Agents

`code-reviewer`, `strong-reviewer` (same instructions, with a
stronger model or higher effort; runs the correctness and security
lenses), `review-validator`, and `tester`. They are `flow:<name>` in
Claude Code and `flow-<name>` in Codex.

## Hooks

`hooks/hooks.json` wires these hooks, shared by Claude Code and Codex:

- `guard.py` keeps the reviewers read-only and limits `tester` to writing
  test files. Once a plan is approved, it also stops the main session from
  changing the plan's test command or removing lines from existing tests
  (Edit and Write only); parking an open question lifts that. It runs only when Python starts: without a usable interpreter
  the hook errors without blocking, and the agents run unguarded.
- `codex_agents.py` converts `agents/*.md` into Codex role files and keeps
  them current, because Codex plugins can't ship agents.
- `format.py` formats an edited file with a formatter the repo already uses
  (ruff, prettier, gofmt, rustfmt). It never blocks an edit.
- `stop_gate.py` blocks the agent from stopping while the approved plan's
  test command fails, except while `/brb` is armed.
- `brb.py` runs `/brb`'s keepalive (Claude Code only). A UserPromptExpansion
  hook arms it on `/brb`, and a UserPromptSubmit hook cancels it on any
  other prompt. A background
  Stop hook (`asyncRewake`) wakes the idle session for a cheap cached turn
  shortly before the cache expires, until the break plus grace ends. See
  [ADR 12](../../docs/adr/0012-flow-brb-keepalive-uses-asyncrewake.md).

On Codex, the hooks run only after you accept Codex's hook trust prompt for
this plugin.

## Requirements

- Python 3.9+ on PATH, for the hooks.
- `git` or `p4`. `gh` or the GitHub MCP tools for GitHub reviews.
- On Windows (Codex), the `py` launcher or `python` on PATH.

Optional: the reviewers preload `andrej-karpathy-skills:karpathy-guidelines`
and `ponytail:ponytail-review` when those plugins are installed, and run
without them otherwise.

## How flow maps to the labs' guidance

Anthropic's [AI-native SDLC playbook](https://claude.com/blog/the-ai-native-sdlc-playbook)
and OpenAI's [harness engineering](https://openai.com/index/harness-engineering/)
(with [Rethinking skills and prompts for GPT-6 Astra](https://learn.chatgpt.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra)
and [Building an AI-Native Engineering Team](https://learn.chatgpt.com/guides/build-ai-native-engineering-team))
describe the same loop. flow's pieces:

| Shared shape | flow |
| --- | --- |
| The repo is the agent's world | Reads the repo's own standards files; `retro` keeps them short |
| Written intent, then a committed plan | `brief.md`, then `plan.md` with acceptance criteria, seams, and decisions |
| The agent verifies its own work | `tdd` at the plan's seams; `stop_gate.py` blocks stopping while tests fail |
| Mechanical enforcement | `guard.py` for subagents, and for the main session's tests after GATE 1 |
| Agent review before humans | `deep-review` lenses and validator, checked against `plan.md` |
| Mistakes become checks | `retro`, on demand |
| Re-test on model or config change | `evals/` run in CI when skills, agents, or hooks change |

Where flow differs on purpose:

- **Human gates.** flow keeps two blocking gates (plan, landing), on
  Anthropic's side rather than OpenAI's mostly-ungated merges.
- **No kept plans.** `ship` deletes `.flow/` before review
  ([ADR 3](../../docs/adr/0003-flow-task-state-travels-with-the-work.md)):
  stale plans get trusted. Lasting decisions go to ADRs and the PR body.
- **Not covered:** a Maintain stage, cleanup agents, and org governance.
  They fit an org rollout, not a per-task plugin.

## Design

The decisions behind flow are in the repo's [`docs/adr/`](../../docs/adr/).

## Tests and evals

The tests live outside this folder, so they don't ship with the plugin. From
the repo root:

```bash
uv run --with pytest pytest tests/flow
```

Without uv: `python3 -m pytest tests/flow`.

`evals/` holds `claude plugin eval` cases. They stay inside the plugin
because `claude plugin eval` reads its eval folder from below the plugin.
They cover sizing and gating, and deep-review's catches and validator drops.
`.github/workflows/evals.yml` runs them on PRs that change flow's
skills, agents, hooks, or evals, when the `ANTHROPIC_API_KEY` secret is set.

## Credits

These skills adapt skills or ideas from other MIT-licensed projects. Their license
notices are in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

| flow skill | Adapted from |
| --- | --- |
| `change-body` | mattpocock/skills [`pr`](https://github.com/mattpocock/skills/tree/main/skills/engineering/pr), itself credited to humanlayer/skills [`show-me`](https://github.com/humanlayer/skills/tree/main/plugins/show-me/skills/show-me); its Why line from humanlayer/skills [`visual-pr`](https://github.com/humanlayer/skills/tree/main/plugins/visual-pr/skills/visual-pr) |
| `deep-review` | smell list from mattpocock/skills [`code-review`](https://github.com/mattpocock/skills/tree/main/skills/engineering/code-review) |
| `plan`, `ship` | neutral exploration and `(manual)` checks: ideas from humanlayer/skills [`rpi`](https://github.com/humanlayer/skills/tree/main/plugins/rpi) |
| `interview` | mattpocock/skills [`grilling`](https://github.com/mattpocock/skills/tree/main/skills/productivity/grilling) |
| `retro` | mattpocock/skills [`retro`](https://github.com/mattpocock/skills/tree/main/skills/engineering/retro) |
| `tdd` | mattpocock/skills [`tdd`](https://github.com/mattpocock/skills/tree/main/skills/engineering/tdd) |

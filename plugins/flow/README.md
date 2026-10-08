# flow

An engineering workflow for Claude Code and Codex. The `flow` skill takes
one task from a prompt or issue to a review that's ready to land. You
approve it twice: the plan (GATE 1) and landing it (GATE 2). Between the
gates the agent works on its own, and parks questions it can't decide
alone instead of guessing.

flow works in git repos (GitHub for reviews) and in Perforce workspaces
(Helix Swarm for reviews).

## Usage

In Claude Code and Codex:

```
/flow:flow <prompt | #issue | issue URL>   start a task
/flow:flow                                 resume the task in .flow/
```

flow sizes the task first:

- **Trivial** (typos, docs, formatting): makes the change, runs the tests,
  shows the diff. No gates.
- **Normal** (a feature or bug fix): start, plan, GATE 1, build test-first,
  ship, GATE 2.
- **Large** (crosses modules or redesigns an API): as Normal, plus a full
  interview, ADRs for one-way-door decisions, and a test-coverage pass.

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
| `deep-review` | Parallel reviewers, one per lens, with every finding checked by a validator. Also usable on its own. |
| `change-body` | The shape of a PR, Swarm review, or changelist description. |
| `retro` | Suggests environment fixes that would have prevented a session's mistakes. |
| `vcs-git`, `vcs-perforce`, `host-github`, `host-swarm` | How each VCS and review-host operation runs. Loaded by the other skills, not invoked by you. |

## Agents

`code-reviewer`, `correctness-reviewer` (same instructions, with a
stronger model or higher effort), `review-validator`, and `tester`. They
are `flow:<name>` in Claude Code and `flow-<name>` in Codex.

## Hooks

`hooks/hooks.json` wires four hooks, shared by Claude Code and Codex:

- `guard.py` keeps the reviewers read-only and limits `tester` to writing
  test files.
- `codex_agents.py` converts `agents/*.md` into Codex role files and keeps
  them current, because Codex plugins can't ship agents.
- `format.py` formats an edited file with a formatter the repo already uses
  (ruff, prettier, gofmt, rustfmt). It never blocks an edit.
- `stop_gate.py` blocks the agent from stopping while the approved plan's
  test command fails.

On Codex, the hooks run only after you accept Codex's hook trust prompt for
this plugin.

## Requirements

- Python 3.9+ on PATH, for the hooks.
- `git` or `p4`. `gh` or the GitHub MCP tools for GitHub reviews.

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

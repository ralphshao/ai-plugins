# AGENTS.md

Instructions for coding agents working in this repo.

## What this repo is

A Claude Code / Codex plugin marketplace. Every plugin except `ai-plugins`
and `flow` is a pinned remote git ref (`url` or `git-subdir` source, with a
`sha`) — not a vendored copy, not a submodule. There's nothing to edit
locally for those plugins; a fix belongs in the upstream repo. `ai-plugins`
and `flow` are the exceptions: their source lives directly in this repo at
`plugins/ai-plugins/` and `plugins/flow/` (local `source` paths).

## Docs

Each local plugin's user docs live in its own `plugins/<name>/README.md`.
The root `README.md` covers only the marketplace: install, the plugin
table, and the repo layout. Don't add plugin details to the root README;
link the plugin's folder instead.

## Two marketplace files, kept in sync

- `.claude-plugin/marketplace.json` — read by Claude Code.
- `.agents/plugins/marketplace.json` — read by Codex. Same plugins, same
  `source` object shape (`url`/`git-subdir` with `sha` and `ref`). A plugin
  with only one manifest (e.g. `andrej-karpathy-skills`, which has no
  `.codex-plugin/plugin.json`) uses that manifest's folder as the plugin
  root in both files; Claude Code and Codex both load either layout.

When adding, removing, or re-pinning a plugin, update both files. The
`ai-plugins` skills do this for you.

## Path quirks

`avoid-ai-writing` and `caveman` each bundle a Claude variant and a Codex
variant at *different* depths within their own repo, and which one is root
vs. nested differs per plugin:

- `avoid-ai-writing`: `.codex-plugin/plugin.json` is at the repo root —
  Codex's entry uses `"source": "url"` with no `path`. Its
  `.claude-plugin/plugin.json` is nested at `plugins/avoid-ai-writing/`
  inside that repo — Claude's entry uses `"source": "git-subdir"` with
  `"path": "plugins/avoid-ai-writing"`.
- `caveman`: the reverse. `.claude-plugin/plugin.json` is at the repo root —
  Claude's entry uses `"source": "url"` with no `path`. Its
  `.codex-plugin/plugin.json` is nested at `plugins/caveman/` inside that
  same repo — Codex's entry uses `"source": "git-subdir"` with
  `"path": "plugins/caveman"`.

Don't assume a bare `url` source is always right for both files — check
where that repo's `.claude-plugin/plugin.json` or `.codex-plugin/plugin.json`
actually lives before wiring up an entry. (Cloning the repo once to check is
fine; just don't commit the clone.)

## Validating changes

```bash
claude plugin validate .
```

only checks `.claude-plugin/marketplace.json`, and only validates local
relative-path sources' `plugin.json` — it does not fetch remote `url`/
`git-subdir` sources to check them. There's no CLI validator for the Codex
file either; check its JSON parses and that `source.sha` is a real commit
reachable from `source.url` (+ `path`, for `git-subdir`).

## Tests

From the repo root, with [uv](https://docs.astral.sh/uv/):

```bash
uv run --with pytest pytest                 # Python from .python-version (CI's main one)
uv run --python 3.9 --with pytest pytest    # the oldest Python the plugins support
```

Without uv: `python3 -m pip install pytest`, then `python3 -m pytest`.

`.python-version` only picks the Python for development. The plugins
themselves run on whatever `python3` the user has, using only the stdlib,
which is why CI also runs the suite on 3.9. Don't add a `pyproject.toml`
or dependencies.

Tests are grouped by plugin: `tests/ai_plugins/` and `tests/flow/`, with
the shared `conftest.py` and the catalog checks (`test_marketplace.py`)
directly in `tests/`. Run one plugin's suite by naming its folder, e.g.
`uv run --with pytest pytest tests/flow`. Keep tests out of `plugins/`: a plugin's
whole folder is copied into every user's plugin cache on install. Test
file names must stay unique across the subfolders (no `__init__.py`).

flow's `claude plugin eval` cases are the exception: they stay in
`plugins/flow/evals/`, because `claude plugin eval` reads its eval folder
from below the plugin.

All of `tests/` runs offline. For the ai-plugins tests, upstream plugin
repos are local git repos, and a private `GIT_CONFIG_GLOBAL` rewrites
`https://github.com/` to point at them.

CI (`.github/workflows/tests.yml`) runs them on Linux, macOS, and Windows.
Keep `.python-version` on the same version as CI's main matrix entry.
When you change a script or hook, add or update a test for the new behavior.

## Maintenance script

`plugins/ai-plugins/scripts/ai-plugins.py` (stdlib-only Python 3.9+) implements
the `add`, `remove`, and `update` subcommands. Each skill under
`plugins/ai-plugins/skills/<name>/` calls it through a shared wrapper,
`scripts/run.sh` or `scripts/run.ps1`, which only finds Python on PATH.
Put logic in the Python script, not in the wrappers.

The script parses the marketplace files as JSON and matches plugins by exact
`name`. Keep it that way, with no substring matching: a past version matched
paths with an unanchored regex and false-matched `andrej-**karpath**y-skills`.
The README plugin table is matched by the link text in each row's first
cell, parsed exactly.

Plugin order is `ai-plugins` first, then the other local plugins, then
the remote ones, each group alphabetical (case-insensitive). It's the same in both marketplace files and in the README table.
The script re-sorts on every write, so hand edits get normalized the next
time it runs.

## Adding, removing, and updating plugins

Use the `ai-plugins:add`, `ai-plugins:remove`, and `ai-plugins:update`
skills, or run `python3 plugins/ai-plugins/scripts/ai-plugins.py
<add|remove|update>` directly (see
[its README](plugins/ai-plugins/README.md)), rather than hand-editing the
marketplace files. `add` detects where each manifest lives, so it handles
the path quirks above. `remove` does not edit prose, such as the path quirks
above. It lists the lines that still mention the plugin, so update those by
hand. All three leave their edits uncommitted. Review them with `git diff`
before committing.

## flow's Codex agents

`plugins/flow/agents/*.md` (Claude Code format) is the only source for
flow's agents. Each agent sets its Codex model and effort separately, in
`codex-model:` and `codex-effort:` frontmatter that Claude Code ignores.
flow's spawn hook (`plugins/flow/hooks/codex_agents.py`) converts the agents
into Codex role files when Codex spawns one and copies them into the user's
Codex agents folder, because Codex plugins can't ship agents
([ADR 8](docs/adr/0008-flow-hooks-shared-by-claude-code-and-codex.md)). There
is no generated file to update.

## Versions

Change a plugin's version only when the user explicitly says to, with the
number they give. A "yes" to a related question, or a bump listed in a
plan, is not a go: ask, and wait. (`ai-plugins:update` copying an upstream
plugin's new version into the catalog is the exception: running it is the
go.) Change it per plugin entry, never with a search-and-replace across a
file: several plugins can share a version string.

## Design records

Design plans don't live in `docs/` once implemented: nobody maintains
them, and readers keep trusting them. A plan is working state (flow keeps
it in `.flow/<slug>/` and removes it before merge). Any decision in it that
still holds goes to `docs/adr/`.

`docs/adr/` holds architecture decision records: one numbered file per
hard-to-reverse decision, never edited after acceptance. A changed decision
gets a new ADR that supersedes the old one.

## Commit convention

This repo pushes real commits per change (not squashed), with a body
explaining *why*, and a `Co-Authored-By: Claude <model> <noreply@anthropic.com>`
trailer naming the Claude model that made the change.

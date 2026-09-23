# AGENTS.md

Instructions for coding agents working in this repo.

## What this repo is

A Claude Code / Codex / ChatGPT plugin marketplace. Every plugin except
`ai-plugins` itself is a pinned remote git ref (`url` or `git-subdir` source,
with a `sha`) — not a vendored copy, not a submodule. There's nothing to
edit locally for those plugins; a fix belongs in the upstream repo.
`ai-plugins` is the one exception: its source lives directly in this repo
at `plugins/ai-plugins/`.

## Two marketplace files, kept in sync

- `.claude-plugin/marketplace.json` — read by Claude Code.
- `.agents/plugins/marketplace.json` — read by Codex / ChatGPT. Same
  `source` object shape (`url`/`git-subdir` with `sha`), but only includes
  plugins whose repo ships a `.codex-plugin/plugin.json` or portable root
  `plugin.json`.

When adding, removing, or re-pinning a plugin, update both files unless the
plugin has no Codex manifest (currently only `andrej-karpathy-skills`). The
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

```bash
python3 -m pip install pytest   # once
python3 -m pytest               # from the repo root
```

`tests/` runs offline: upstream plugin repos are local git repos, and a
private `GIT_CONFIG_GLOBAL` rewrites `https://github.com/` to point at them.

CI (`.github/workflows/tests.yml`) runs them on Linux, macOS, and Windows.
When you change the script, add or update a test for the new behavior.

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

Plugin order is alphabetical (case-insensitive), with `ai-plugins` always
first. It's the same in both marketplace files and in the README table.
The script re-sorts on every write, so hand edits get normalized the next
time it runs.

## Adding, removing, and updating plugins

Use the `ai-plugins:add`, `ai-plugins:remove`, and `ai-plugins:update`
skills, or run `python3 plugins/ai-plugins/scripts/ai-plugins.py
<add|remove|update>` directly (see README.md), rather than hand-editing the
marketplace files. `add` detects where each manifest lives, so it handles
the path quirks above. `remove` does not edit prose, such as the Claude-only
note in README.md or the path quirks above. It lists the lines that still
mention the plugin, so update those by hand. All three leave their edits
uncommitted. Review them with `git diff` before committing.

## Commit convention

This repo pushes real commits per change (not squashed), with a body
explaining *why*, and a `Co-Authored-By: Claude <model> <noreply@anthropic.com>`
trailer naming the Claude model that made the change.

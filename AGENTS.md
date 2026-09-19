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
plugin has no Codex manifest (currently only `andrej-karpathy-skills`).

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

## Regex gotcha

`plugins/ai-plugins/skills/update/scripts/update-refs.sh` reads plugin
entries with `jq`, not a hand-rolled regex — if you touch its parsing, don't
reintroduce unanchored substring matching. A past version parsed
`.gitmodules` with `git config --get-regexp path` (unanchored), which
false-matched `andrej-**karpath**y-skills`. Anchor to `\.path$` if you ever
need config-file regex again.

## Updating pinned refs

Use the `ai-plugins:update` skill (or run
`plugins/ai-plugins/skills/update/scripts/update-refs.sh` directly — see
README.md) rather than hand-editing `source.sha`. It resolves each remote
plugin's latest commit via `git ls-remote`, prints a before/after SHA +
commit subject, and rewrites `source.sha` in both marketplace files for
anything that moved. Leaves the edits uncommitted; review with `git diff`
before committing.

## Commit convention

This repo pushes real commits per change (not squashed), with a body
explaining *why*, and a `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>`
trailer when Claude made the change.

# AGENTS.md

Instructions for coding agents working in this repo.

## What this repo is

A Claude Code / Codex / ChatGPT plugin marketplace. Plugins are git
submodules under `plugins/`, not vendored source — never edit files inside a
submodule directory and expect the change to persist. A submodule is a
separate git repo pinned to a commit; edits there are local-only unless you
have push access to that upstream repo and commit/push inside it directly.

## Two marketplace files, kept in sync

- `.claude-plugin/marketplace.json` — read by Claude Code.
- `.agents/plugins/marketplace.json` — read by Codex / ChatGPT. Different
  schema (`source: {"source": "local", "path": "..."}` instead of a bare
  string), and only includes plugins whose submodule ships a
  `.codex-plugin/plugin.json` or portable root `plugin.json`.

When adding, removing, or moving a plugin, update both files unless the
plugin has no Codex manifest (currently only `andrej-karpathy-skills`).

## Path quirks

Two submodules bundle a Claude variant and a Codex variant at *different*
depths, and which one is root vs. nested differs per plugin:

- `caveman`: `.claude-plugin/plugin.json` is at the submodule root
  (`plugins/caveman/.claude-plugin/`) — the Claude entry uses
  `./plugins/caveman`. Its `.codex-plugin/plugin.json` is nested at
  `plugins/caveman/plugins/caveman/.codex-plugin/` — the Codex entry uses
  `./plugins/caveman/plugins/caveman`.
- `avoid-ai-writing`: the reverse. `.codex-plugin/plugin.json` is at the
  submodule root (`plugins/avoid-ai-writing/.codex-plugin/`) — the Codex
  entry uses `./plugins/avoid-ai-writing`. Its `.claude-plugin/plugin.json`
  is nested at `plugins/avoid-ai-writing/plugins/avoid-ai-writing/.claude-plugin/`
  — the Claude entry uses that nested path.

Don't assume `./plugins/<name>` is always the right `source` path for both
files — check where that submodule's `.claude-plugin/plugin.json` or
`.codex-plugin/plugin.json` actually lives before wiring up an entry.

## Validating changes

```bash
claude plugin validate .
```

only checks `.claude-plugin/marketplace.json`. There's no CLI validator for
the Codex file — check its JSON parses and that every `source.path` resolves
to a real `.codex-plugin/plugin.json` (or portable root `plugin.json`).

## Regex gotcha

`plugins/ai-plugins/skills/update/scripts/update-submodules.sh` parses
`.gitmodules` with `git config --get-regexp`. Anchor any regex against these
keys (`\.path$`, not `path`) — an unanchored `path` substring-matches inside
`andrej-**karpath**y-skills`, so it isn't a hypothetical edge case here.

## Updating submodules

Use the `ai-plugins:update` skill (or run its script directly — see
README.md) rather than `git submodule update --remote --recursive` by hand,
so the before/after comparison gets printed. It leaves gitlink bumps
uncommitted; review with `git diff --submodule` before committing.

## Commit convention

This repo pushes real commits per change (not squashed), with a body
explaining *why*, and a `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>`
trailer when Claude made the change.

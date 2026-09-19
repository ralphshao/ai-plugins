# ai-plugins

A personal Claude Code / Codex / ChatGPT plugin marketplace. Each plugin is
vendored as a git submodule under [`plugins/`](plugins/), pinned to a
specific upstream commit.

## Install

### Claude Code

```bash
claude plugin marketplace add ralphshao/ai-plugins
claude plugin install <plugin-name>@ai-plugins
```

### Codex / ChatGPT

Codex and the ChatGPT desktop app read a separate catalog at
[`.agents/plugins/marketplace.json`](.agents/plugins/marketplace.json). Clone
this repo (or add it as a submodule of your own repo) and point Codex at
it — see [Package your plugin](https://developers.openai.com/plugins/build/plugins)
for how repo-scoped marketplaces are picked up.

`andrej-karpathy-skills` is Claude-only: its upstream repo ships only a
`.claude-plugin/plugin.json`, with no Codex-compatible manifest, so it's
omitted from the Codex catalog.

## Plugins

| Plugin | Description | Version |
| --- | --- | --- |
| [`ai-plugins`](plugins/ai-plugins) | Maintenance skill for this marketplace itself: `ai-plugins:update` bumps every submodule to its latest upstream HEAD | 1.0.0 |
| [`andrej-karpathy-skills`](plugins/andrej-karpathy-skills) | Behavioral guidelines to reduce common LLM coding mistakes | 1.0.0 |
| [`caveman`](plugins/caveman) | Ultra-compressed communication mode — cuts filler, keeps technical accuracy | 2.7.0 |
| [`context-mode`](plugins/context-mode) | MCP server for session continuity, sandboxed code execution, and an FTS5 knowledge base | 1.0.169 |
| [`ponytail`](plugins/ponytail) | Lazy senior dev mode — YAGNI, stdlib first, shortest working diff | 4.10.0 |
| [`avoid-ai-writing`](plugins/avoid-ai-writing) | Audit & rewrite content to remove AI writing patterns ("AI-isms") | 3.35.0 |
| [`i-have-adhd`](plugins/i-have-adhd) | Shapes Claude Code output for an ADHD reader | 0.3.0 |

## Repo structure

```
.claude-plugin/marketplace.json   # Claude Code marketplace catalog
.agents/plugins/marketplace.json  # Codex / ChatGPT marketplace catalog
plugins/<name>/                   # one git submodule per plugin
```

Two submodules bundle a Claude variant and a Codex variant at different
depths (see [AGENTS.md](AGENTS.md) for exactly which path each marketplace
file uses for `caveman` and `avoid-ai-writing`).

## Updating plugins

Install the `ai-plugins` plugin from this marketplace, then run its
`ai-plugins:update` skill (or run
`plugins/ai-plugins/skills/update/scripts/update-submodules.sh` directly from
the repo root). It bumps every submodule to the latest commit on its tracked
branch, prints a before/after SHA + commit subject per submodule, and leaves
the resulting gitlink changes uncommitted for you to review with
`git diff --submodule` before committing.

## Adding a plugin

1. `git submodule add <repo-url> plugins/<name>`
2. Add an entry to `.claude-plugin/marketplace.json` with `source: "./plugins/<name>"`
   (or the nested path, if the repo's actual plugin folder isn't at its root).
3. If the submodule ships a `.codex-plugin/plugin.json` (or a portable root
   `plugin.json`), add a matching entry to `.agents/plugins/marketplace.json`
   with `source: { "source": "local", "path": "./plugins/<name>" }`. If it
   doesn't, leave it out of the Codex catalog.
4. `claude plugin validate .` to check the Claude manifest.

Each plugin keeps its own upstream license; this repo adds no license of its
own for the marketplace glue.

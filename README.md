# ai-plugins

A personal Claude Code / Codex / ChatGPT plugin marketplace. Every plugin
except `ai-plugins` itself is fetched directly from its upstream git repo,
pinned to a specific commit SHA — there's no vendored copy in this repo.

## Install

### Claude Code

```bash
claude plugin marketplace add ralphshao/ai-plugins
claude plugin install <plugin-name>@ai-plugins
```

### Codex / ChatGPT

Codex and the ChatGPT desktop app read a separate catalog at
[`.agents/plugins/marketplace.json`](.agents/plugins/marketplace.json). Clone
this repo and point Codex at it — see
[Package your plugin](https://developers.openai.com/plugins/build/plugins)
for how repo-scoped marketplaces are picked up.

`andrej-karpathy-skills` is Claude-only: its upstream repo ships only a
`.claude-plugin/plugin.json`, with no Codex-compatible manifest, so it's
omitted from the Codex catalog.

## Plugins

| Plugin | Description | Version |
| --- | --- | --- |
| [`ai-plugins`](plugins/ai-plugins) | Maintenance skills for the ai-plugins marketplace itself | 1.0.0 |
| [andrej-karpathy-skills](https://github.com/multica-ai/andrej-karpathy-skills) | Behavioral guidelines to reduce common LLM coding mistakes | 1.0.0 |
| [caveman](https://github.com/JuliusBrussee/caveman) | Ultra-compressed communication mode — cuts filler, keeps technical accuracy | 2.7.0 |
| [context-mode](https://github.com/mksglu/context-mode) | MCP server for session continuity, sandboxed code execution, and an FTS5 knowledge base | 1.0.169 |
| [ponytail](https://github.com/dietrichgebert/ponytail) | Lazy senior dev mode — YAGNI, stdlib first, shortest working diff | 4.10.0 |
| [avoid-ai-writing](https://github.com/conorbronsdon/avoid-ai-writing) | Audit & rewrite content to remove AI writing patterns ("AI-isms") | 3.35.0 |
| [i-have-adhd](https://github.com/ayghri/i-have-adhd) | Shapes Claude Code output for an ADHD reader | 0.3.0 |

## Repo structure

```
.claude-plugin/marketplace.json   # Claude Code marketplace catalog
.agents/plugins/marketplace.json  # Codex / ChatGPT marketplace catalog
plugins/ai-plugins/               # the one plugin whose source actually lives in this repo
```

Every other plugin's `source` is a `url` or `git-subdir` object with a
pinned `sha`, not a relative path — see
[Create the marketplace file](https://developers.openai.com/plugins/build/plugins)
docs for the source schema. `caveman` and `avoid-ai-writing` each bundle a
Claude variant and a Codex variant at *different* subdirectory depths within
their own repo — see [AGENTS.md](AGENTS.md) for exactly which `path` each
marketplace file uses.

## Updating plugins

Install the `ai-plugins` plugin from this marketplace, then run its
`ai-plugins:update` skill (or run
`plugins/ai-plugins/skills/update/scripts/update-refs.sh` directly from the
repo root). It resolves each pinned plugin's latest commit via
`git ls-remote`, prints a before/after SHA + commit subject, and — for
anything that moved — rewrites `source.sha` in both marketplace files.
Leaves the edits uncommitted for you to review with `git diff` before
committing.

## Adding a plugin

1. Find the plugin's repo and note whether its `plugin.json` (or
   `.codex-plugin/plugin.json`) sits at the repo root or in a subdirectory.
2. Add an entry to `.claude-plugin/marketplace.json`:
   - Root: `"source": {"source": "url", "url": "<repo>.git", "sha": "<commit>"}`
   - Subdirectory: `"source": {"source": "git-subdir", "url": "<repo>.git", "path": "<subdir>", "sha": "<commit>"}`
3. If the repo also ships a Codex-compatible manifest (`.codex-plugin/plugin.json`
   or a portable root `plugin.json`), add a matching entry to
   `.agents/plugins/marketplace.json` (same `source` shape). If it doesn't,
   leave it out of the Codex catalog.
4. `claude plugin validate .` to check the Claude manifest.

Each plugin keeps its own upstream license; this repo adds no license of its
own for the marketplace glue.

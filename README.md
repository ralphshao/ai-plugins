# ai-plugins

A personal Claude Code / Codex plugin marketplace. Every plugin except
`ai-plugins` itself is fetched directly from its upstream git repo, pinned
to a specific commit SHA — there's no vendored copy in this repo.

## Install

### Claude Code

```bash
claude plugin marketplace add ralphshao/ai-plugins
claude plugin install <plugin-name>@ai-plugins
```

### Codex

```bash
codex plugin marketplace add ralphshao/ai-plugins
codex plugin install <plugin-name>@ai-plugins
```

## Plugins

| Plugin | Description | Version |
| --- | --- | --- |
| [`ai-plugins`](plugins/ai-plugins) | Maintenance skills for the ai-plugins marketplace itself | 1.3.0 |
| [andrej-karpathy-skills](https://github.com/multica-ai/andrej-karpathy-skills) | Behavioral guidelines to reduce common LLM coding mistakes | 1.0.0 |
| [avoid-ai-writing](https://github.com/conorbronsdon/avoid-ai-writing) | Audit & rewrite content to remove AI writing patterns ("AI-isms") | 3.36.0 |
| [caveman](https://github.com/JuliusBrussee/caveman) | Ultra-compressed communication mode — cuts filler, keeps technical accuracy | 2.7.0 |
| [context-mode](https://github.com/mksglu/context-mode) | MCP server for session continuity, sandboxed code execution, and an FTS5 knowledge base | 1.0.169 |
| [i-have-adhd](https://github.com/ayghri/i-have-adhd) | Shapes Claude Code output for an ADHD reader | 0.3.0 |
| [ponytail](https://github.com/dietrichgebert/ponytail) | Lazy senior dev mode — YAGNI, stdlib first, shortest working diff | 4.10.0 |

## Repo structure

```
.claude-plugin/marketplace.json   # Claude Code marketplace catalog
.agents/plugins/marketplace.json  # Codex marketplace catalog
plugins/ai-plugins/               # the one plugin whose source actually lives in this repo
tests/                            # pytest suite for the ai-plugins scripts
```

Every other plugin's `source` is a `url` or `git-subdir` object with a
pinned `sha`, not a relative path — see
[Create the marketplace file](https://developers.openai.com/plugins/build/plugins)
docs for the source schema. `caveman` and `avoid-ai-writing` each bundle a
Claude variant and a Codex variant at *different* subdirectory depths within
their own repo — see [AGENTS.md](AGENTS.md) for exactly which `path` each
marketplace file uses.

## Managing plugins

Install the `ai-plugins` plugin from this marketplace. It has three skills:

| Skill | Does |
| --- | --- |
| `ai-plugins:add <github-url-or-owner/repo>` | Pins the repo's latest release (highest `vX.Y.Z` tag), or its latest commit if it has no release tags. Detects where its `.claude-plugin/plugin.json` and `.codex-plugin/plugin.json` live, and adds entries to both marketplace files, with `ref` set to the release tag or branch next to `sha`. The repo needs at least one of the two; each catalog uses its own manifest's folder as the plugin root, falling back to the other. It also adds a row to the table above. Optional flags: `--path <subdir>` when the repo holds several plugins, `--description <text>` to override the upstream description. |
| `ai-plugins:remove <name>` | Removes the plugin from both marketplace files and the table above, then lists any other lines in README.md and AGENTS.md that still mention it. |
| `ai-plugins:update` | Uses `git ls-remote` to find each pinned plugin's latest release (or latest commit on its default branch if it has no release tags, or on its `ref` if that is some other branch), and prints the before/after SHA and commit subject. For anything that moved, it rewrites `source.sha` and `source.ref` in both marketplace files. If the plugin's version changed, it also updates `version` in `.claude-plugin/marketplace.json` and the plugin's row in the table above. |

Each skill calls a thin wrapper, `scripts/run.sh` or `scripts/run.ps1`,
which runs the shared
[`plugins/ai-plugins/scripts/ai-plugins.py`](plugins/ai-plugins/scripts/ai-plugins.py).
That script needs Python 3.9+ and `git`, and nothing else. You can also run it
directly from anywhere inside the repo:

```bash
python3 plugins/ai-plugins/scripts/ai-plugins.py add owner/repo
python3 plugins/ai-plugins/scripts/ai-plugins.py remove <name>
python3 plugins/ai-plugins/scripts/ai-plugins.py update
```

All three commands keep the plugin lists sorted alphabetically, with
`ai-plugins` first, in both marketplace files and the table above. They
leave their edits uncommitted, so review them with `git diff` before
committing. Run `claude plugin validate .` to check the Claude manifest.

Each plugin keeps its own upstream license; this repo adds no license of its
own for the marketplace glue.

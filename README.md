# ai-plugins

A personal Claude Code / Codex plugin marketplace. Every plugin except
`ai-plugins` and `flow` is fetched directly from its upstream git repo,
pinned to a specific commit SHA — there's no vendored copy in this repo.

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
| [`ai-plugins`](plugins/ai-plugins) | Maintenance skills for the ai-plugins marketplace itself | 0.2.1 |
| [andrej-karpathy-skills](https://github.com/multica-ai/andrej-karpathy-skills) | Behavioral guidelines to reduce common LLM coding mistakes | 1.0.0 |
| [avoid-ai-writing](https://github.com/conorbronsdon/avoid-ai-writing) | Audit & rewrite content to remove AI writing patterns ("AI-isms") | 3.36.0 |
| [caveman](https://github.com/JuliusBrussee/caveman) | Ultra-compressed communication mode — cuts filler, keeps technical accuracy | 2.7.0 |
| [context-mode](https://github.com/mksglu/context-mode) | MCP server for session continuity, sandboxed code execution, and an FTS5 knowledge base | 1.0.169 |
| [`flow`](plugins/flow) | Engineering workflow: plan, build, review, and ship a change with two human gates | 0.2.4 |
| [i-have-adhd](https://github.com/ayghri/i-have-adhd) | Shapes Claude Code output for an ADHD reader | 0.3.0 |
| [ponytail](https://github.com/dietrichgebert/ponytail) | Lazy senior dev mode — YAGNI, stdlib first, shortest working diff | 4.10.0 |

## Repo structure

```
.claude-plugin/marketplace.json   # Claude Code marketplace catalog
.agents/plugins/marketplace.json  # Codex marketplace catalog
plugins/ai-plugins/               # marketplace maintenance plugin (source lives here)
plugins/flow/                     # engineering workflow plugin (source lives here)
tests/                            # pytest suite: conftest.py, catalog checks
  ai_plugins/                     #   tests for plugins/ai-plugins
  flow/                           #   tests for plugins/flow
```

## Maintaining this marketplace

Install the [`ai-plugins`](plugins/ai-plugins) plugin. Its skills add,
remove, and re-pin plugins in both catalogs and the table above.

Each plugin keeps its own upstream license; this repo adds no license of its
own for the marketplace glue.

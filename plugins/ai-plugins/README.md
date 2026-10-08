# ai-plugins

Maintenance skills for the [ai-plugins marketplace](../../README.md) itself.
They keep the Claude Code catalog (`.claude-plugin/marketplace.json`), the
Codex catalog (`.agents/plugins/marketplace.json`), and the README plugin
table in sync.

## Skills

| Skill | Does |
| --- | --- |
| `ai-plugins:add <github-url-or-owner/repo>` | Pins the repo's latest release (highest `vX.Y.Z` tag), or its latest commit if it has no release tags. Detects where its `.claude-plugin/plugin.json` and `.codex-plugin/plugin.json` live, and adds entries to both marketplace files, with `ref` set to the release tag or branch next to `sha`. The repo needs at least one of the two; each catalog uses its own manifest's folder as the plugin root, falling back to the other. It also adds a row to the root README's plugin table. Optional flags: `--path <subdir>` when the repo holds several plugins, `--description <text>` to override the upstream description. |
| `ai-plugins:remove <name>` | Removes the plugin from both marketplace files and the root README's plugin table, then lists any other lines in README.md and AGENTS.md that still mention it. |
| `ai-plugins:update` | Uses `git ls-remote` to find each pinned plugin's latest release (or latest commit on its default branch if it has no release tags, or on its `ref` if that is some other branch), and prints the before/after SHA and commit subject. For anything that moved, it rewrites `source.sha` and `source.ref` in both marketplace files. If the plugin's version changed, it also updates `version` in `.claude-plugin/marketplace.json` and the plugin's row in the root README's table. |

All three keep the plugin lists sorted alphabetically, with `ai-plugins`
first, in both marketplace files and the README table. They leave their
edits uncommitted, so review them with `git diff` before committing. Run
`claude plugin validate .` to check the Claude manifest.

## Requirements

- Python 3.9+ on PATH (stdlib only).
- `git`, which `add` and `update` use to query upstream repos.

## How it works

Each skill calls a thin wrapper, `scripts/run.sh` or `scripts/run.ps1`,
which finds Python and runs [`scripts/ai-plugins.py`](scripts/ai-plugins.py).
All the logic lives in that script. You can also run it directly from
anywhere inside the repo:

```bash
python3 plugins/ai-plugins/scripts/ai-plugins.py add owner/repo
python3 plugins/ai-plugins/scripts/ai-plugins.py remove <name>
python3 plugins/ai-plugins/scripts/ai-plugins.py update
```

## Tests

The tests live outside this folder, so they don't ship with the plugin. From
the repo root:

```bash
python3 -m pytest tests/ai_plugins
```

They run offline against throwaway local git repos. `tests/test_marketplace.py`
checks the catalogs themselves.

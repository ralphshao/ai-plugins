# ai-plugins

Maintenance skills for the [ai-plugins marketplace](../../README.md) itself.
They keep the Claude Code catalog (`.claude-plugin/marketplace.json`), the
Codex catalog (`.agents/plugins/marketplace.json`), and the README plugin
table in sync.

## Skills

| Skill | Does |
| --- | --- |
| `ai-plugins:add <github-url-or-owner/repo>` | Pins a GitHub repo's latest release (or latest commit if it has none) and adds it to both catalogs and the README table. Detects where the repo's `.claude-plugin/plugin.json` and `.codex-plugin/plugin.json` live. |
| `ai-plugins:remove <plugin-name>` | Removes a plugin from both catalogs and the README table, then lists other lines that still mention it. |
| `ai-plugins:update` | Re-pins every remote plugin to its latest upstream release (or latest commit) and prints a before/after SHA comparison. |

The root README's [Managing plugins](../../README.md#managing-plugins)
section has the full flag reference. All three skills leave their edits
uncommitted for you to review with `git diff`.

## Requirements

- Python 3.9+ on PATH (stdlib only).
- `git`, for `add` and `update`, which query upstream repos.

## How it works

Each skill calls `scripts/run.sh` (or `scripts/run.ps1` on Windows), which
finds Python and runs `scripts/ai-plugins.py <add|remove|update>`. All the
logic lives in that Python script. You can also run it directly from the
repo root:

```bash
python3 plugins/ai-plugins/scripts/ai-plugins.py --help
```

## Tests

The tests live outside this folder, so they don't ship with the plugin. From
the repo root:

```bash
python3 -m pytest tests/ai_plugins
```

They run offline against throwaway local git repos. `tests/test_marketplace.py`
checks the catalogs themselves.

---
name: remove
description: Remove a named plugin from this marketplace, from the Claude and Codex catalogs and the README plugin table. Use for "remove plugin", "drop <name> from the marketplace", or /ai-plugins:remove.
argument-hint: <plugin-name>
---

From the repo root, run `${CLAUDE_PLUGIN_ROOT}/skills/remove/scripts/remove.sh $ARGUMENTS` (on Windows, `${CLAUDE_PLUGIN_ROOT}/skills/remove/scripts/remove.ps1 $ARGUMENTS`). Both are thin wrappers around `${CLAUDE_PLUGIN_ROOT}/scripts/ai-plugins.py remove`.

What the script does:
- Removes the plugin's entry from `.claude-plugin/marketplace.json`, `.agents/plugins/marketplace.json`, and `README.md`'s plugin table, wherever it appears.
- Refuses to remove `ai-plugins` itself, and fails if no plugin has that name.
- Lists any remaining mentions of the name in `README.md` or `AGENTS.md`, such as the Claude-only note or the path quirks.
- Leaves the edits uncommitted.

After running, if the script listed remaining mentions, update or delete those passages so the docs no longer describe the removed plugin.

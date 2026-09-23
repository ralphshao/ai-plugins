---
name: add
description: Add a new plugin to this marketplace from a GitHub URL or owner/repo slug, pinned to its latest commit, in the Claude and Codex catalogs and the README table. Use for "add plugin", "add <repo> to the marketplace", or /ai-plugins:add.
argument-hint: <github-url-or-owner/repo> [--path <subdir>] [--description <text>]
---

From the repo root, run `${CLAUDE_PLUGIN_ROOT}/scripts/run.sh add $ARGUMENTS` (on Windows, `${CLAUDE_PLUGIN_ROOT}/scripts/run.ps1 add $ARGUMENTS`). Both find a Python on PATH and run `${CLAUDE_PLUGIN_ROOT}/scripts/ai-plugins.py add`.

The argument can be `owner/repo`, `https://github.com/owner/repo(.git)`, or a `https://github.com/owner/repo/tree/<ref>/<subdir>` link. For a `/tree/` link, the script pins that ref and searches only under that subdirectory.

What the script does:
- Resolves the repo's latest commit, shallow-fetches it, and finds `.claude-plugin/plugin.json` and `.codex-plugin/plugin.json`, at the repo root or nested.
- Pins that SHA. When the manifest is at the repo root, it writes a `url` source; when it is nested, a `git-subdir` source with that `path`. The Claude and Codex paths are detected independently, because they can differ within one repo.
- Takes `name`, `description`, `version`, and `author` from `plugin.json`. `--description` replaces the README and Claude-catalog description.
- Adds the plugin to `.agents/plugins/marketplace.json` only when the repo ships `.codex-plugin/plugin.json`. Otherwise it reports the plugin as Claude-only.
- Adds a row to `README.md`'s plugin table, and keeps all three lists sorted alphabetically with `ai-plugins` first.
- Fails without editing anything when the name already exists, or when there are several candidate manifests. For several manifests, re-run with `--path <subdir>`.
- Leaves the edits uncommitted.

After running:
- If the description is long (more than about one sentence), suggest a shorter README description and offer to re-run with `--description`: first `remove <name>`, then `add` again.
- If the plugin is Claude-only, mention that the README's Codex section lists Claude-only plugins, and offer to add it there.

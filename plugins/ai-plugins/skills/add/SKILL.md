---
name: add
description: Add a new plugin to this marketplace from a GitHub URL or owner/repo slug, pinned to its latest release (or latest commit if it has none), in the Claude and Codex catalogs and the README table. Use for "add plugin", "add <repo> to the marketplace", or /ai-plugins:add.
argument-hint: <github-url-or-owner/repo> [--path <subdir>] [--description <text>]
---

From the repo root, run `${CLAUDE_PLUGIN_ROOT}/scripts/run.sh add $ARGUMENTS` (on Windows, `${CLAUDE_PLUGIN_ROOT}/scripts/run.ps1 add $ARGUMENTS`). Both find a Python on PATH and run `${CLAUDE_PLUGIN_ROOT}/scripts/ai-plugins.py add`.

The argument can be `owner/repo`, `https://github.com/owner/repo(.git)`, or a `https://github.com/owner/repo/tree/<ref>/<subdir>` link. For a `/tree/` link, the script pins that ref instead of the latest release, and searches only under that subdirectory.

What the script does:
- Resolves the commit to pin: the latest release (the highest `vX.Y.Z` tag, skipping pre-releases like `v2.0.0-beta`), or the default branch's latest commit when the repo has no release tags. It shallow-fetches that commit and finds `.claude-plugin/plugin.json` and `.codex-plugin/plugin.json`, at the repo root or nested.
- Pins that SHA and prints which release or branch it came from. Writes `sha` and, right after it, `ref`: the release tag, the default branch name, or the `/tree/` ref. When the manifest is at the repo root, it writes a `url` source; when it is nested, a `git-subdir` source with that `path`. The Claude and Codex paths are detected independently, because they can differ within one repo.
- Takes `name`, `description`, `version`, and `author` from `.claude-plugin/plugin.json`, or from `.codex-plugin/plugin.json` when there is no Claude manifest. `--description` replaces the README and Claude-catalog description.
- Adds the plugin to both catalogs. The repo needs `.claude-plugin/plugin.json` or `.codex-plugin/plugin.json`. Each catalog uses its own manifest's folder as the plugin root, and falls back to the other folder when its own manifest is missing, since Claude Code and Codex both load either layout.
- Adds a row to `README.md`'s plugin table, and keeps all three lists sorted alphabetically with `ai-plugins` first.
- Fails without editing anything when the name already exists, or when there are several candidate manifests. For several manifests, re-run with `--path <subdir>`.
- Leaves the edits uncommitted.

After running:
- If the description is long (more than about one sentence), suggest a shorter README description and offer to re-run with `--description`: first `remove <name>`, then `add` again.

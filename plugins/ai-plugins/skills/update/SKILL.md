---
name: update
description: Update every remote-ref plugin in this marketplace (pinned url/git-subdir sources) to its latest upstream HEAD and print a before/after SHA comparison. Use for "update plugins", "update pinned refs", "pull latest plugin versions", or /ai-plugins:update.
---

From the repo root, run `${CLAUDE_PLUGIN_ROOT}/scripts/run.sh update` (on Windows, `${CLAUDE_PLUGIN_ROOT}/scripts/run.ps1 update`). Both find a Python on PATH and run `${CLAUDE_PLUGIN_ROOT}/scripts/ai-plugins.py update`.

What the script does:
- Reads every plugin in `.claude-plugin/marketplace.json` whose `source` is a `url` or `git-subdir` object. It skips local entries such as `ai-plugins` itself.
- Uses `git ls-remote` to find each plugin's latest commit on its tracked ref. When no `ref` is set, that is the default branch.
- Prints one result per plugin: `up to date` with its SHA and commit subject, or `updated` with the before/after SHA and commit subject.
- When a plugin has a newer commit, rewrites its `source.sha` in `.claude-plugin/marketplace.json`, and in `.agents/plugins/marketplace.json` too if a matching entry exists. It also reads the plugin's `version` at the new commit. If the version changed, it updates the `version` field in `.claude-plugin/marketplace.json` and the plugin's row in `README.md`'s plugin table.
- Keeps plugins sorted alphabetically, with `ai-plugins` first, in both marketplace files and the README table.
- Leaves the edits uncommitted. The user reviews them with `git diff` and commits when ready.

After running, summarize which plugins changed, which commit each moved to, and any version bumps.

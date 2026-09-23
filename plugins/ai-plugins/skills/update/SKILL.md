---
name: update
description: Update every remote-ref plugin in this marketplace (pinned url/git-subdir sources) to its latest upstream release (or latest commit if it has none) and print a before/after SHA comparison. Use for "update plugins", "update pinned refs", "pull latest plugin versions", or /ai-plugins:update.
---

From the repo root, run `${CLAUDE_PLUGIN_ROOT}/scripts/run.sh update` (on Windows, `${CLAUDE_PLUGIN_ROOT}/scripts/run.ps1 update`). Both find a Python on PATH and run `${CLAUDE_PLUGIN_ROOT}/scripts/ai-plugins.py update`.

What the script does:
- Reads every plugin in `.claude-plugin/marketplace.json` whose `source` is a `url` or `git-subdir` object. It skips local entries such as `ai-plugins` itself.
- Uses `git ls-remote` to find each plugin's target commit. When the entry's `ref` is some other branch or tag, that is the ref's latest commit. When it has no `ref`, or its `ref` is a release tag or the default branch, it is the latest release (the highest `vX.Y.Z` tag, skipping pre-releases like `v2.0.0-beta`), or the default branch's latest commit when the repo has no release tags. A plugin pinned to a branch commit newer than its latest release moves back to the release.
- Prints one result per plugin: `up to date` with its SHA and commit subject, or `updated` with the before/after SHA and commit subject. Each line ends with where the commit came from: `(release vX.Y.Z)`, `(default branch)`, or `(ref <name>)`.
- When a plugin has a newer commit, rewrites its `source.sha` and `source.ref` in `.claude-plugin/marketplace.json`, and in `.agents/plugins/marketplace.json` too if a matching entry exists. An up-to-date plugin whose `ref` is missing or stale gets only its `ref` rewritten. It also reads the plugin's `version` at the new commit. If the version changed, it updates the `version` field in `.claude-plugin/marketplace.json` and the plugin's row in `README.md`'s plugin table.
- Keeps plugins sorted alphabetically, with `ai-plugins` first, in both marketplace files and the README table.
- Leaves the edits uncommitted. The user reviews them with `git diff` and commits when ready.

After running, summarize which plugins changed, which commit or release each moved to, and any version bumps.

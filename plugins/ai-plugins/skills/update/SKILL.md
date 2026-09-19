---
name: update
description: Update every remote-ref plugin in this marketplace (pinned url/github/git-subdir sources) to its latest upstream HEAD and print a before/after SHA comparison. Use for "update plugins", "update pinned refs", "pull latest plugin versions", or /ai-plugins:update.
---

Run `${CLAUDE_PLUGIN_ROOT}/skills/update/scripts/update-refs.sh` from the repo root.

The script:
- Reads every plugin in `.claude-plugin/marketplace.json` whose `source` is a `url`, `github`, or `git-subdir` object (skips plain relative-path/local entries like `ai-plugins` itself).
- Resolves each plugin's latest commit on its tracked ref (default branch if no `ref` is set) via `git ls-remote`.
- Prints, per plugin: `up to date` with its SHA + subject, or `updated` with before/after SHA + commit subject.
- When a plugin has a newer commit, rewrites its `source.sha` in `.claude-plugin/marketplace.json` and, if a matching entry exists, `.agents/plugins/marketplace.json` too. Leaves those edits uncommitted — review with `git diff`, commit yourself when ready.

After running, summarize which plugins changed and to what commit.

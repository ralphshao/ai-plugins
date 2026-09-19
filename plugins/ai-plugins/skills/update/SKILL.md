---
name: update
description: Update every plugin submodule in this marketplace to its latest upstream HEAD and print a before/after SHA comparison. Use for "update submodules", "update plugins", "pull latest plugin versions", or /ai-plugins:update.
---

Run `${CLAUDE_PLUGIN_ROOT}/skills/update/scripts/update-submodules.sh` from the repo root.

The script:
- Updates each submodule listed in `.gitmodules` to the latest commit on its tracked branch.
- Prints, per submodule: `up to date` with its SHA + subject, or `updated` with before/after SHA + commit subject.
- Leaves the resulting gitlink changes uncommitted in the working tree — review with `git diff --submodule`, commit yourself when ready.

After running, summarize which submodules changed and by how much (number of commits behind is not computed — only old vs new HEAD).

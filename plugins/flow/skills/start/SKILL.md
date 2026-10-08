---
name: start
description: First flow phase. Turns a prompt or issue into an isolated workspace (branch, worktree, or changelist) and a checkpointed .flow/<slug>/brief.md.
argument-hint: "[prompt | issue reference]"
disable-model-invocation: true
---

Arguments: `$ARGUMENTS`

1. **Pick the VCS and review-host skills** as the `flow` skill's "VCS and
   review host" section says.
2. **Read the request.**
   - Issue reference: `fetch-issue`. State the issue title before going on.
     If it fails, say so and ask for the text instead.
   - Prompt: use it as written.
3. **Pick a slug:** 2-5 lowercase words joined by hyphens, from the request
   (`retry-webhook-failures`). Prefix the issue number when there is one
   (`123-retry-webhook-failures`).
4. **Write `.flow/<slug>/brief.md`:**

   ```
   # <title>
   Source: <issue URL or key, or "prompt">
   Size: <size from the flow skill>
   VCS: <vcs skill>; host: <host skill, or "none">
   Isolation: <what isolate returned>

   ## Request
   <the issue body or prompt, verbatim>

   ## Constraints
   <anything the user stated: deadlines, files not to touch, compatibility>
   ```

5. **Isolate:** run `isolate` and fill in the brief's Isolation line. Never
   discard local changes.
6. **Checkpoint** the brief: `flow: start <slug>`.

If the VCS isn't available (no shell, or a command is denied), keep the
brief, say which steps you couldn't run, and continue to the plan phase.

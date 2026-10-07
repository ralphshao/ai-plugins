---
name: start
description: First flow phase. Turns a prompt or GitHub issue into a feature branch and a committed .flow/<slug>/brief.md.
argument-hint: "[prompt | #issue | issue URL]"
disable-model-invocation: true
---

Arguments: `$ARGUMENTS`

1. **Read the request.**
   - GitHub issue: `gh issue view <n> --json number,title,body,labels,url`.
     State the issue title before going on. If `gh` fails, say so and ask
     for the text instead.
   - Prompt: use it as written.
2. **Pick a slug:** 2-5 lowercase words joined by hyphens, from the request
   (`retry-webhook-failures`). Prefix the issue number when there is one
   (`123-retry-webhook-failures`).
3. **Branch.** If the current branch is the default branch, create
   `flow/<slug>` from it. If the session is already in a worktree or on a
   feature branch made for this task, stay there. Never discard local
   changes; if the tree is dirty and unrelated, stop and ask.
4. **Write `.flow/<slug>/brief.md`:**

   ```
   # <title>
   Source: <issue URL, or "prompt">
   Size: <trivial | normal | large>

   ## Request
   <the issue body or prompt, verbatim>

   ## Constraints
   <anything the user stated: deadlines, files not to touch, compatibility>
   ```

5. Commit it: `flow: start <slug>`.

---
name: host-github
description: How flow's review-host operations (fetch-issue, fetch-review, open-draft, ready-for-review) run on GitHub, with gh or the GitHub MCP tools. Load when a flow phase or deep-review names one of these operations and the repo's origin is on github.com.
user-invocable: false
---

GitHub hosts the pull requests and issues for a git repo. Branch, commit,
and push steps belong to `vcs-git`.

## Detect

Use this skill when `git remote get-url origin` points at github.com and
either `gh auth status` succeeds or GitHub MCP tools are available. The
commands below use `gh`; with only MCP tools, call their equivalents.

## fetch-issue

`gh issue view <n> --json number,title,body,labels,url` for `#<n>` or an
issue URL. State the issue title before going on. The review body links it
with `Closes #<n>`.

## fetch-review

`gh pr view <n> --json number,title,body,state,baseRefName,baseRefOid,headRefOid,mergeCommit,url`.
Base is `baseRefOid`, head is `headRefOid`. For a merged PR whose
`mergeCommit` has two parents, diff `<mergeCommit>^1 <mergeCommit>` instead:
that's what landed, including conflict resolutions. Squash and rebase merges
leave one parent and can't be told apart, so use base and head for them.

Check each commit is local with `git cat-file -e <sha>^{commit}`. Fetch a
missing head with `git fetch origin pull/<n>/head` and a missing base or
merge commit with `git fetch origin <baseRefName>`; both only write
`FETCH_HEAD` and remote refs.

## open-draft

After `publish`: `gh pr create --draft --title <title> --body <body>`. The
body links `.flow/<slug>/plan.md` and the issue (`Closes #<n>` when there is
one). If `gh` fails, say so and continue locally.

## ready-for-review

Update the body (`gh pr edit <n> --body-file <file>`), then `gh pr ready
<n>`. If no PR exists yet, create one without `--draft`. Report the PR URL.

Never merge (`gh pr merge`) and never enable auto-merge unless asked.

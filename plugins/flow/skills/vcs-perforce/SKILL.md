---
name: vcs-perforce
description: How flow's VCS operations (find-state, isolate, checkpoint, diff-scope, publish, drop-state, land, resolve-target) run in a Perforce (Helix Core) workspace, with pending changelists or a task/dev stream. Load when a flow phase or deep-review names one of these operations in a p4 workspace.
user-invocable: false
---

Flow's phases name an operation; this skill says how to run it with `p4`.
Code review belongs to a review host (`host-*` skill), when there is one.
Never submit to a shared stream or branch yourself, never run `p4 obliterate`,
and never revert files you didn't open.

## Detect

Use this skill when `p4 -ztag info` reports a `clientName` other than
`*unknown*` and a `clientRoot` that contains the current directory.

## Modes

Read `Stream` from `p4 -ztag client -o`. If it's set, read `Type` and
`Parent` from `p4 -ztag stream -o <stream>`.

- **Changelist mode** (the default): the work lives in one pending
  changelist in the current workspace. Used for classic workspaces and for
  streams not made for this task.
- **Stream mode**: the workspace is on a `task` or `development` stream made
  for this task (named after it, or the user says so). The stream is
  private to the work, so steps are submitted to it.

Create a new stream only when the user asks: ask for the name and parent,
then `p4 switch -c <name>` or `p4 stream` per the depot's convention. Never
create classic branches (branch specs, client views); work in whatever
branch the workspace maps.

## Working rules

Files are read-only until opened. Before changing a file,
`p4 edit -c <cl> <file>`; for a new file, `p4 add -c <cl> <file>`; to
delete, `p4 delete -c <cl> <file>`. Before each checkpoint, run
`p4 reconcile -c <cl> <paths you touched>` to catch anything missed. If a
file you need is already open in another changelist, ask before moving it.

## find-state

Look for `.flow/*/plan.md` under the client root. Flow keeps that folder in
its own pending **state changelist**, described `flow: state <slug>`, so
also check `p4 changes -s pending -c <client>`. From another workspace (a
new machine or cloud session), find it with
`p4 changes -s shelved -u <user>` and restore the plan files with
`p4 unshelve -s <cl> -c <new cl>`.

## isolate

Return what the brief should record: the work changelist (changelist mode)
or the stream (stream mode), plus the state changelist.

1. Create the state changelist: `p4 --field "Description=flow: state
   <slug>" change -o | p4 change -i`. Open `.flow/<slug>/` in it with
   `p4 add -c <state cl>`. It is never submitted.
2. Changelist mode: create the work changelist the same way, described
   `flow: <slug>`. Other files already open in the workspace stay where they
   are; flow only opens files into its own changelists.
3. Stream mode: stay on the stream. Each checkpoint gets its own changelist.

## checkpoint

Shelve the state changelist: `p4 shelve -f -c <state cl>`. Then:

- Changelist mode: `p4 shelve -f -c <cl>`. The shelf is the checkpoint.
- Stream mode: set the step's message as the changelist description and
  `p4 submit -c <cl>`.

## diff-scope

Changes to review or test, as a diff command, a change list, and a read
root.

- Changelist mode: checkpoint first, then `p4 describe -S -du <cl>`; its
  files are listed by `p4 describe -S -s <cl>`. The description is the
  intent.
- Stream mode: `p4 diff2 -du -S <stream>` (the stream against its parent),
  with changes from `p4 changes -l //<stream>/...`. Open, unsubmitted work
  adds `p4 diff -du` on the files of `p4 opened -c <cl>`.
- Read root: the client root; local files match the shelf or head.

## publish

Changelist mode: shelve (`p4 shelve -f -c <cl>`), which makes the work
visible to others. Stream mode: steps are already submitted to the stream;
nothing to do.

## drop-state

Delete the state changelist: `p4 shelve -d -c <state cl>`, then
`p4 revert -w -c <state cl> //...`, then `p4 change -d <state cl>`. The work
changelist never held `.flow/`, so it's untouched.

## land

The user lands the work; never do it yourself.

- Changelist mode: tell the user to submit it (`p4 submit -c <cl>`, or
  through the review host).
- Stream mode: landing is a copy-up to the parent. When asked to prepare
  it, switch the workspace to the parent (`p4 switch <parent>`; it refuses
  with files open, so checkpoint first), then `p4 copy -S <stream> -c <new
  cl>` and `p4 shelve -c <new cl>`. That shelved copy-up is what the review
  host reviews and what the user submits.

## resolve-target

Turn a deep-review target into a diff command, intent, and how to read the
files.

A bare number or `#<n>`: if a review host is present, ask its
`fetch-review` first; if no review has that ID, treat it as a changelist.

| Target | Diff | Read files with |
|--------|------|-----------------|
| `cl:<n>`, submitted | `p4 describe -du <n>` | `p4 print -q <depot file>@=<n>` |
| `cl:<n>`, pending with shelved files | `p4 describe -S -du <n>` | `p4 print -q <depot file>@=<n>` |
| `cl:<n>`, pending and open in this workspace | `p4 diff -du` on the files of `p4 opened -c <n>` | Read, under the client root |
| `review:<n>` | host `fetch-review` gives its changelists; apply the rows above to each and combine | as for each changelist |

Find the status with `p4 -ztag describe -s <n>` (`status`, and `shelved`
when there are shelved files). The changelist description is the intent.
For several changelists, read each file at the highest changelist that
touches it. Tell reviewers to read with `p4 print` instead of Read whenever
the files aren't local.

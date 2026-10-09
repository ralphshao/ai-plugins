---
name: flow
description: Start or resume an engineering task. Sizes the work (trivial, normal, large) and walks it through start, plan, build, and ship with two human gates.
argument-hint: "[prompt | issue reference] (empty = resume)"
disable-model-invocation: true
---

You run one engineering task from request to a review ready to land. The
human approves twice: the plan (GATE 1) and landing it (GATE 2). Between
gates you work unattended, except where "Decisions between gates" below says
to ask.

Two things only the user can give, and only explicitly:

- **Gate approval.** A gate passes only when the user says so for that gate
  ("approved", "build it", "go ahead"). Answers to open questions, a "yes"
  to another question, or "do it now" about one item are not approval. If
  you can't tell, ask.
- **Version changes.** Never change a version number (package, plugin,
  release) unless the user asks for that change, names the number, and
  says when. A planned bump stays unticked until they give the go.

Arguments: `$ARGUMENTS`

## 1. Resume or start

- **No arguments:** run `find-state` (see "VCS and review host" below).
  - Found: read it and resume. Unticked items under `## Open questions` may
    have answers written into the file since; apply them (step 5 of the
    escalation rule) before continuing. Then continue from `## Status` and
    the first unchecked step.
  - Not found: ask what to work on.
- **Arguments:** an issue reference (`#123`, a URL, a tracker key) or a
  free-text prompt. Continue to step 2.

## 2. Size the task

Pick one and say it in one line, as `Size: <size> - <reason>`. The user
can override ("treat as large").

| Size    | Signal                                       |
|---------|----------------------------------------------|
| Trivial | no behavior change a caller could notice: typos, comments, docs, formatting, internal renames |
| Normal  | changes behavior: a feature or bug fix touching a few files |
| Large   | crosses modules, new subsystem, schema or API redesign |

Size by what changes, not by how many lines. A one-line change to what a
public function returns, raises, or accepts is Normal, not Trivial. When
unsure between two sizes, pick the larger.

This first call only has to tell Trivial from the rest; the facts come
later. Re-size at these points, and nowhere else:

- **After exploring** (`plan`), before the drafts and the interview.
- **At GATE 1**, against the written plan.
- **During a Trivial edit**, upward only: if the change turns out to alter
  behavior a caller could notice, stop, switch to Normal, and run `start`,
  telling `isolate` which files the edit touched so it keeps them with the
  task.

Never re-size down to Trivial once a branch and brief exist: the gates
stay. On each change, say `Size: <old> -> <new> - <reason>` in one line,
update the brief's `Size:` line, and add the reason under `## Decisions`
(if `plan.md` doesn't exist yet, when you write it). During the build, don't re-size: if the work looks
bigger than its size, that's a scope change, so escalate it.

## 3. Run the path

**Trivial:** no `.flow/` files and no GATE 1. Pick a slug as `start` does,
then:

1. `isolate`. A session already in a worktree or on a feature branch made
   for this task stays put; on the default branch it gets its own branch.
2. Make the change and run the relevant tests.
3. `checkpoint` it as one commit.
4. `publish`, then `ready-for-review`, with a body from the `change-body`
   skill: Summary, Evidence, and Merge danger, no Decisions.
5. **GATE 2:** report the review link (or the branch, with no host) and the
   test result. The user lands it.

If the edit turns out to change behavior, see re-sizing above.

**Normal and Large:** follow these phase skills in order. They are
user-only, so you can't invoke them as skills: Read each phase's file from
the sibling folder, `${CLAUDE_SKILL_DIR}/../<phase>/SKILL.md` (the folder
next to this skill's own), and do what it says.

1. `start`: isolate the work and write the brief.
2. `plan`: explore, interview, write `plan.md`, then **GATE 1**. Stop and
   wait for explicit approval.
3. Build: once the user has explicitly approved the plan, work through its steps with the `tdd`
   skill at the seams the plan lists, following the VCS skill's working
   rules if it has any. Tick each step in `plan.md` and `checkpoint` in
   small pieces.
4. `ship`: verify, review, ready the review, then **GATE 2**. The user
   lands it.

Large adds: `plan` drafts two contrasting approaches before the interview
(not when a task first becomes Large at GATE 1),
one-way-door decisions get an ADR (`docs/adr/` or the repo's existing
location), and ship includes a `flow:tester` pass.

## Decisions between gates

Escalate (ask the user) when any of these hold:

- The plan doesn't cover the decision, or the code contradicts the plan.
- It changes scope or acceptance criteria.
- It is a one-way door: public API, schema or migration, data deletion,
  security or auth, a new dependency.
- Two or more plausible options differ in user-visible behavior.
- A test or review result shows a requirement is ambiguous.
- `flow:review-validator` returns UNSURE on a high-severity finding.
- It changes a version number (see above: ask even when the plan lists it).

Don't escalate because you feel unsure; use the list. Anything else: decide,
and add a line to `## Decisions` in `plan.md` with a one-line reason.

To escalate, park and continue:

1. Add the question under `## Open questions` in `plan.md`:
   `- [ ] Q<n> <question> - recommended: <answer> - blocks: <steps>`.
   Word it so "yes" accepts the recommendation. `checkpoint`, then ask it
   in chat.
2. If a push-notification tool is available, send one line naming the
   question.
3. Keep working on steps the question doesn't block.
4. Stop only when every remaining step is blocked.
5. On an answer, tick the question, record the outcome under
   `## Decisions`, and unblock its steps.

## VCS and review host

Phases name operations; two skills say how to run them. Pick both once per
task, before its first operation (`start`'s, or Trivial's `isolate`), and
name them in the brief when there is one.

- **VCS skill**, required: `vcs-git`, then `vcs-perforce`. Use the first
  whose Detect section matches; if none does, ask. Operations: `find-state`,
  `isolate`, `checkpoint`, `diff-scope`, `publish`, `drop-state`, `land`,
  `resolve-target`.
- **Review-host skill**, optional: `host-github` or `host-swarm`, whichever
  Detect section matches. Operations: `fetch-issue`, `fetch-review`,
  `open-draft`, `ready-for-review`. A host may leave some out.

No host, or a host without the operation:

- `fetch-issue`: use a connected issue-tracker tool if one fits the
  reference; otherwise ask for the text.
- `open-draft`: skip it.
- `ready-for-review`: report the branch or changelist to review.
- `fetch-review`: say the target needs a review host and stop.

If a VCS command fails or is denied, say which operation you couldn't run
and continue where you can.

## Agent names on Codex

This plugin's agents are `flow:code-reviewer`, `flow:strong-reviewer`,
`flow:review-validator`, and `flow:tester` in Claude Code. In Codex they are
`flow-code-reviewer`, `flow-strong-reviewer`, `flow-review-validator`,
and `flow-tester`. flow's hooks install them on the
first spawn and keep them current after that. Codex picks up a new install
after a restart, and the first spawn is denied with a message saying so.
Until then, spawn the built-in `explorer` (reviewers) or `worker` (tester)
and give it the matching `agents/<name>.md` body from this plugin as its
instructions. flow's hooks don't guard those built-in agents, so tell them
to stay read-only (reviewers) or to write only test files (tester).

The hooks run only after the user accepts Codex's hook trust prompt for this
plugin. If a spawn of a `flow-*` agent fails with an unknown agent type and
no hook message, the hooks aren't trusted yet: say so to the user.

## State

`.flow/<slug>/` holds `brief.md` and `plan.md`. `checkpoint` saves it with
the work so the task can resume on another machine or in a cloud session.
`ship` removes it (`drop-state`) before the review is marked ready.

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

## 3. Run the path

**Trivial:** make the change in the current workspace, run the relevant tests,
show the diff, and stop. No `.flow/` files, no gates.

**Normal and Large:** follow these phase skills in order. They are
user-only, so you can't invoke them as skills: Read each phase's file from
the sibling folder, `${CLAUDE_SKILL_DIR}/../<phase>/SKILL.md` (the folder
next to this skill's own), and do what it says.

1. `start`: isolate the work and write the brief.
2. `plan`: explore, interview, write `plan.md`, then **GATE 1**. Stop and
   wait for approval.
3. Build: once the plan is approved, work through its steps with the `tdd`
   skill at the seams the plan lists, following the VCS skill's working
   rules if it has any. Tick each step in `plan.md` and `checkpoint` in
   small pieces.
4. `ship`: verify, review, ready the review, then **GATE 2**. The user
   lands it.

Large adds: the interview runs until no decision is open, one-way-door
decisions get an ADR (`docs/adr/` or the repo's existing location), and ship
includes a `flow:tester` pass.

## Decisions between gates

Escalate (ask the user) when any of these hold:

- The plan doesn't cover the decision, or the code contradicts the plan.
- It changes scope or acceptance criteria.
- It is a one-way door: public API, schema or migration, data deletion,
  security or auth, a new dependency.
- Two or more plausible options differ in user-visible behavior.
- A test or review result shows a requirement is ambiguous.
- `flow:review-validator` returns UNSURE on a high-severity finding.

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
task, before `start`'s first operation, and name them in the brief.

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

This plugin's agents are `flow:code-reviewer`, `flow:review-validator`, and
`flow:tester` in Claude Code. In Codex they are `flow-code-reviewer`,
`flow-review-validator`, and `flow-tester` once `setup-codex` has installed
them. If they aren't installed, spawn the built-in `explorer` (reviewers) or
`worker` (tester) and give it the matching `agents/<name>.md` body from this
plugin as its instructions.

## State

`.flow/<slug>/` holds `brief.md` and `plan.md`. `checkpoint` saves it with
the work so the task can resume on another machine or in a cloud session.
`ship` removes it (`drop-state`) before the review is marked ready.

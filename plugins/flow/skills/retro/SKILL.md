---
name: retro
description: Retrospective on a coding session. Suggests fixes to the agent's environment (checks, standards, steering files, tooling) that would have prevented this session's mistakes, most severe first.
argument-hint: "[session or PR to review] (empty = this session)"
disable-model-invocation: true
---

Adapted from the `retro` skill in mattpocock/skills (MIT).

You suggest changes to the **environment** future sessions run in, not to
the code just written. Suggest only; change nothing until the user picks.

Arguments: `$ARGUMENTS`

## 1. Gather evidence

Default to the current session. Otherwise read what the user points at: a
review (the host's `fetch-review`, and its comments), a branch's commits
or changelists, or session logs. Note each place where the agent went wrong, slowed down, or needed
the user to step in.

## 2. Find candidates

| Category | Look for |
|----------|----------|
| Automated checks | A mistake a linter, type check, test, hook, or CI job could have caught. Read the repo's existing check commands and CI first: an existing check that isn't wired up is the finding. A repo with no pre-commit hook and no CI running its checks is a finding on its own. |
| Standards | A mistake review should have caught. If the rule is mechanical (a banned API, an import shape, a file location), it becomes an automated check, not prose. Only judgment calls go into a standards doc (`CODING_STANDARDS.md`, `CONTRIBUTING.md`). |
| Steering files | CLAUDE.md/AGENTS.md text that should be a check or a standards rule instead, or that changes nothing. These files load into every session: keep them to short facts and pointers to other docs. |
| Navigation | Time spent finding things. A pointer in CLAUDE.md/AGENTS.md or a short doc would fix it. |
| Information access | Something the agent needed but couldn't see: dev-server logs, read-only access to a service, an API doc. |
| Tool economy | Expensive or repeated tool calls a script, MCP tool, or better command would replace. |
| flow itself | A gate, escalation, or plan section that misfired. Note it for the flow plugin, not the repo. |

## 3. Report

List candidates most severe first. For each: what happened (with the
evidence), the change, and where it goes (file, hook, CI job). Then ask
which to apply.

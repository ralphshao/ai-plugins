# memory-keeper: consolidate to one account-level task; project rules move to memory
Source: https://github.com/ralphshao/ai-plugins/issues/30
Size: Normal
VCS: vcs-git; host: host-github
Isolation: branch claude/memory-keeper-single-task-a40d79 in linked worktree /Users/ralph/.claude/worktrees/ai-plugins/sandbox-github-docker-a475be (already isolated, stayed put)

## Request
## Context
- Goal: one scheduled task maintains all memory. Project instructions should never need edits.
- Confirmed: an account-level task can read and write all project memory.
- Tested (canary): an account-level task cannot read project instructions.
- New strategy: project behavior rules live in each project's `preferences.md`; rules shared across projects live in account `/preferences.md`. Project instructions hold only scope, a pointer telling Claude to read the project's `preferences.md`, and a few fixed rules memory can't reliably hold.

## maintain/SKILL.md
- [ ] **Tiers (line 18):** replace "Rules about how Claude should behave in one project belong in that project's instructions" with "…belong in that project's preferences.md; rules that apply across projects belong in account /preferences.md."
- [ ] **One mode only:** remove project mode and the mode-selection section. The skill always runs at account level and covers all projects. If invoked inside a project (project writes are confined to that project there), say it must run outside a project and stop. No migration logic in the skill; one-time migration lives in separate prompts.
- [ ] **Reach:** fold in the project-level checks (lines restating account preferences, broken links inside projects, project-vs-account copies) and allow safe-fix writes to project files.
- [ ] **Instruction checks:** the skill can't see project instructions. Remove "lines restating the project instructions", "behavior rules in memory that belong in the instructions", and "things the instructions reference that memory lacks". Treat each project's `preferences.md` as its rules source.
- [ ] **Profile-instruction candidates:** retarget to account `/preferences.md` (proposal-only memory write) instead of paste-ready instruction lines. Keep paste-ready output only for rules memory filters would drop (skip checks, trust claims, hold back concerns, persona).
- [ ] **Rule-line protection:** add "Never reword, merge or delete a rule line in any preferences.md as a safe fix; propose it."
- [ ] **Write cap:** raise from 8 to about 20 in account mode (11 projects).
- [ ] **New checks:** flag projects with no or empty `preferences.md`, and project folders that look unreachable (project memory set to separate).

## setup/SKILL.md
- [ ] Remove project mode. Inside a project, say setup must run outside a project and stop.
- [ ] Drop the 9:00 AM project schedule and the `(<project name>)` task naming.

## Out of scope for the plugin
One-time migration is done with prompts run by hand, not skill code: the per-project prompt that moves instruction rules into memory and outputs revised instructions, and a one-off account cleanup. Deleting old per-project scheduled tasks is a manual step too.

## Rollout (after merge)
1. Run the one-time per-project prompt in each project; paste the revised instructions.
2. Add to account preferences: read and follow account `/preferences.md` and, inside a project, that project's `preferences.md`; project wins on conflict.
3. Run the account cleanup once.
4. Delete the per-project scheduled tasks.

## Constraints
None stated beyond the issue. Out of scope per the issue: one-time migration prompts, deleting old per-project tasks.

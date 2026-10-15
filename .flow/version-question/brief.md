# Make flow raise the version question
Source: prompt
Size: Normal
VCS: vcs-git; host: host-github
Isolation: worktree /Users/ralph/.claude/worktrees/ai-plugins/code-reviewer-subagent-b30eb0, branch claude/great-allen-4a8d70

## Request
Normal size. Make flow raise the version question instead of only refusing unasked bumps. (1) plan skill: when the change touches a versioned package, add a Version line to plan.md and ask at GATE 1 "<pkg> is at X. Bump to what at ship, or none?"; record intent under Decisions (intent only, not a go). (2) ship skill: before ready-for-review, re-confirm "Still bump <pkg> to Y?" and apply only on the user's yes with the number; if diff-scope touches a versioned package and the plan has no Version line, ask fresh. (3) flow skill Trivial path: when a Trivial edit touches a versioned package, the final report asks the version question. (4) AGENTS.md Versions: one line on this. (5) New ADR 0013 refining ADR 9. Don't change any version number.

## Constraints
- Don't change any version number in this task.
- Done: skills, AGENTS.md, ADR updated; `uv run --with pytest pytest` passes; plugin-dev:skill-reviewer on each changed skill; PR opened.

# memory-keeper

Keeps claude.ai memory and profile/project instructions accurate,
deduplicated, and in the right tier. Claude only: it uses the claude.ai
memory tools (`memory_list`, `memory_delete`, ...), which Claude Code's CLI
and Codex don't have. Meant for Cowork, including cloud scheduled runs.

## Skills

| Skill | Does |
| --- | --- |
| `memory-keeper:memory-maintenance` | One run, no questions mid-run. Account mode outside a project, project mode inside one. Applies up to 8 safe fixes (say "max N writes" to change the cap), proposes everything else as numbered changes you approve by replying `approve 1, 3`. Say "dry run" to make no writes. |
| `memory-keeper:setup` | Creates, shows, changes, or removes the weekly cloud scheduled task that runs memory-maintenance: Sunday 8:45 AM for account mode, 9:00 AM for project mode, in your local time zone. |

## Memory layout it expects

Account memory: `/profile.md`, `/preferences.md`, `/topics`, `/areas`,
`/people`, and per-project folders under `/projects/`.

## Scheduling

Run `memory-keeper:setup` once outside any project for account mode, and
once inside each project you want maintained. Every task uses the same
prompt:

```
Run the memory-maintenance skill. If the skill isn't available, send a one-line SendUserMessage saying so and stop.
```

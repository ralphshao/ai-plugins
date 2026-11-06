# memory-keeper

Keeps claude.ai memory and profile instructions accurate,
deduplicated, and in the right tier. Claude only: it uses the claude.ai
memory tools (`memory_list`, `memory_delete`, ...), which Claude Code's CLI
and Codex don't have. Meant for Cowork, including cloud scheduled runs.

## Skills

| Skill | Does |
| --- | --- |
| `memory-keeper:maintain` | One run, no questions mid-run, outside any project; covers every project. Applies up to 20 safe fixes (say "max N writes" to change the cap), proposes everything else as numbered changes you approve by replying `approve 1, 3`. Say "dry run" to make no writes. |
| `memory-keeper:setup` | Creates, shows, changes, or removes the weekly cloud scheduled task that runs memory-keeper:maintain: Sunday 8:45 AM in your local time zone. Run it outside any project. |

## Memory layout it expects

Account memory: `/profile.md`, `/preferences.md`, `/topics`, `/areas`,
`/people`, and per-project folders under `/projects/`.

Behavior rules live in memory, because the scheduled task can't read project
instructions: one project's rules in that project's `preferences.md`, rules
shared across projects in account `/preferences.md`. Add this to your account
preferences so Claude follows them:

```
Read and follow account /preferences.md and, inside a project, that project's preferences.md. The project wins on conflict.
```

Each project's instructions then need only its scope, a pointer to its
`preferences.md`, and any fixed rules memory can't reliably hold. Reports flag
projects with no or empty `preferences.md`, and folders that list empty or
can't be read. A project with separate memory whose folder never appears can't
be detected.

## Scheduling

Run `memory-keeper:setup` once, outside any project. It creates one task,
`Account memory maintenance`, with this prompt:

```
Run the memory-keeper:maintain skill. If the skill isn't available, send a one-line SendUserMessage saying so and stop.
```

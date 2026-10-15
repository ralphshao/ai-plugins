# 12. flow's /brb keepalive wakes the session with an asyncRewake Stop hook

Status: accepted (#22, 2026-10-15).

## Context

An idle Claude Code session past its prompt-cache TTL rewrites its whole
context on the next turn: 1.25x base input on the 5-minute TTL, 2x on the
1-hour TTL. A cache read costs about 0.1x and resets the TTL, so a cheap
turn shortly before expiry keeps a session warm through a break. Doing this
blindly for every session wastes pings on sessions the user has abandoned,
so it has to be opt-in.

A hook can't submit a prompt or run a slash command. Typing into a terminal
(tmux `send-keys` and the like) can't reach the desktop app, which has no
terminal, and tmux isn't installed on every machine. A headless
`claude -p --resume` runs in another process with possibly a different
prefix, and Claude Code kills its async hooks at teardown.

## Decision

`/brb [duration]` is a user-only flow skill. Two hooks do the work, in
`hooks/brb.py`:

- **UserPromptExpansion** arms the keepalive when the typed command is
  `/brb` or `/flow:brb`, with an optional duration in `command_args`.
  Codex has no such event, so it never arms there.
- **UserPromptSubmit** cancels it on any other prompt. That event also
  fires for scheduled tasks, background subagents reporting back, and
  cross-session messages, so those cancel it too. The keepalive's own wakes
  arrive as system reminders, not prompts, so they don't cancel it.
- **Stop, with `asyncRewake: true`**, sleeps until the TTL minus a lead
  (55 minutes on 1h, 4 on 5m), then exits 2. Claude Code wakes the idle
  session, Claude answers `ok`, and that turn's Stop re-reads the TTL and
  schedules the next ping, until the duration plus grace (half the
  duration, at least one TTL) has passed. Claude Code enforces `timeout` on
  asyncRewake hooks, so the hook's is 3600 seconds.

The TTL comes from the newest `usage.cache_creation` in the transcript (1h
vs 5m write tokens), else Claude Code's documented settings precedence.
State is one JSON file per session in the system temp folder, not in
`.flow/`: it belongs to the session, not a task. Sessions with less than
20k tokens of context aren't pinged.

A spike in the CLI confirmed the mechanism: the Stop hook woke an idle
session after 60 seconds, and `/usage` showed no cache misses on the 1h TTL.

Claude Code only. Codex has no asyncRewake and would run the sleeping hook
synchronously. Besides lacking UserPromptExpansion, `brb.py` refuses to arm
for a transcript under `.codex/`.

## /later was dropped

The plan also had `/later`: for a session the user is leaving, wait out the
TTL in case they return, then compact just before the cache goes cold, so
the next visit pays for a summary instead of the full context. `/brb` would
hand off to it at its deadline.

The spike showed there's no way to compact from here. A woken turn asked to
call `Skill("compact")` got "compact is a built-in CLI command, not a
skill", and no hook or documented API triggers `/compact`. Claude Code
already does what `/later` meant to do: its idle compaction compacts a long
idle terminal session shortly before a 1h cache expires (`idleCompaction`,
on by default). So `/brb` just stops pinging at its deadline and leaves the
session to that.

## Alternatives

- **Terminal injection (tmux, cmux).** Rejected: no desktop app, needs
  tmux.
- **Headless `claude -p --resume` pings.** Rejected: separate process,
  possible cache-prefix mismatch, async hooks killed at teardown.
- **A detached scheduler process.** Not needed: the asyncRewake hook is the
  scheduler, and Claude Code owns its lifetime.
- **A separate plugin.** Rejected by the user: flow's hooks.json and test
  harness already fit.

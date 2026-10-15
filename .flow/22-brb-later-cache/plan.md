# flow: opt-in /brb cache warmer

## Goal
Before a break, the user runs `/brb 90m` and comes back to a warm prompt cache
instead of paying a full cache rewrite. Opt-in.

## Acceptance criteria
- `/brb <duration>` in Claude Code (CLI and desktop app) wakes the idle
  session about TTL minus a lead (55 min on 1h, 4 min on 5m) after the last
  turn, and keeps doing so until duration + grace (50% of the duration, at
  least one TTL).
- Bare `/brb` defaults its duration by TTL: one cycle (60m) on a 1h TTL,
  30m on a 5m TTL.
- Each woken ping turn reads the cache (`cache_read_input_tokens` close to
  the full context) and is answered briefly.
- Any real user prompt cancels the timer. The plugin's own wakes do not.
- TTL comes from the latest `usage.cache_creation` in the transcript (1h vs
  5m tokens), re-read after each ping. Fallback: the settings precedence
  chain from the issue.
- No wake when the context is below a minimum-token threshold.
- No wake is scheduled past duration + grace. After that, Claude Code's
  native idle compaction (terminal, 1h TTL) handles the idle session.
- Codex: the `/brb` hooks exit at once and never block.
- Hooks are stdlib-only and run on Python 3.9+, on Linux, macOS, and Windows.

## Seams under test
- `hooks/brb.py` run as a subprocess with stdin JSON (the existing
  test_hooks.py harness), with an env-injected clock and sleep - catches:
  arm/cancel/expiry state transitions, TTL parsing, schedule math, the
  Codex early exit, the cancel race during sleep / misses: whether the host
  really wakes the session and hits the cache (covered by the spike and a
  manual check at ship)
- `tests/flow/test_layout.py` - catches: user-only frontmatter and
  openai.yaml for `brb`, hook commands that resolve / misses:
  runtime behavior

## Steps
- [x] Spike (throwaway, not committed as code): an asyncRewake Stop hook
  that sleeps 60s and exits 2, in the desktop app and the CLI. Check that it
  wakes an idle session, that the woken turn shows a full cache read, how it
  interacts with a typed draft, and that Codex doesn't block on it. Also
  look for any working auto-compact path: a woken turn, `claude -p --resume`
  with `/compact`, or Codex `codex exec resume`. Record the results under
  Decisions. If the asyncRewake wake fails, stop and re-plan.
- [x] `brb.py` TTL and schedule: transcript parse (1h/5m, context size), the
  settings-precedence fallback, ping times, grace, and the bare-`/brb` default duration. Tests first.
- [x] `brb.py` arm/stop/prompt modes plus the `hooks.json` entries (an
  asyncRewake Stop and a UserPromptSubmit), with the Codex early exit and
  the min-token guard.
- [x] `skills/brb/` user-only skill (SKILL.md and agents/openai.yaml), and
  add it to USER_ONLY.
- [ ] ADR 0012: asyncRewake as the ping path, state in the temp dir and not
  in `.flow/`, Claude Code only, and why `/later` was dropped: its intent
  (wait out the TTL in case the user returns, then compact), the spike
  results (asyncRewake wakes an idle session with a cache hit;
  `Skill("compact")` is rejected), and native idle compaction covering it.
- [ ] flow README: Skills and Hooks sections (update the hook count).

## Test command
`uv run --with pytest pytest tests/flow`

## Out of scope
- tmux or other terminal injection.
- `/brb` on Codex.
- Detecting a draft in the input box: hooks can't see it.
- Surviving machine sleep or app quit: the ping is lost, which is harmless.
- A version bump (only on the user's explicit go).

## Decisions
- Lives inside flow, not a separate plugin - the user's choice; reuses
  hooks.json and the test harness.
- Ping path is an asyncRewake Stop hook - the user's choice; no terminal
  needed, works in the desktop app, same session and cache.
- Auto-compact is spiked first, and the fallback is built only if a path
  works; otherwise a nudge - the user's choice.
- A spike gates the build (step 1) - the user's choice.
- Bare `/brb` defaults to one cycle on 1h TTL, 30m on 5m TTL - the user's
  choice; a 5m cycle is too short for a real break.
- `/later` waits until just before the TTL ends instead of compacting at
  once - the user's intent: coming back within the TTL keeps the full
  context. It reuses `/brb`'s timer with zero pings.
- Docs (hooks, prompt-caching pages): asyncRewake exit 2 wakes Claude even
  when idle; its `timeout` IS enforced, so the hook timeout must exceed the
  longest sleep (~55 min on 1h TTL); in `-p` mode async hooks are killed at
  teardown. No hook or documented API triggers `/compact`.
- Q2: yes - spike plugin at `.flow/22-brb-later-cache/spike/`, run by the
  user in CLI and desktop app.
- Spike, CLI (2026-10-15): asyncRewake Stop hook woke the idle session
  after 60s; `/usage` showed no misses, 1h TTL warm, so the ping read the
  cache. `Skill("compact")` is rejected: "compact is a built-in CLI
  command, not a skill". No auto-compact path from a woken turn. Draft and
  desktop-app runs not done yet.
- Q1: drop `/later` entirely, on Claude Code and Codex - the user's choice;
  no skill or woken turn can run `/compact` (spike), and native idle
  compaction covers the leaving case. Supersedes the `/later` decisions
  above.
- State lives in `tempfile.gettempdir()/flow-brb-<session_id>.json` - it
  belongs to the session, not the task, and nothing is written to the repo.
- The plugin's wakes arrive as system reminders, not user prompts, so the
  UserPromptSubmit cancel needs no nonce - per the hooks docs; the spike
  confirms it.

## Open questions
- [x] Q1 Claude Code already compacts idle sessions shortly before a 1h cache
  expires (`idleCompaction`, on by default, terminal sessions, 1h TTL only).
  Drop `/later` and the compact fallback on Claude Code: `/brb` just stops
  pinging at duration + grace and native idle compaction takes over; `/later`
  stays for Codex only (if the spike finds a compact path there) - recommended:
  yes - blocks: spike's compact part, `skills/later/` step, ADR wording
- [x] Q2 The spike needs a live interactive session (desktop app and CLI) with
  a throwaway asyncRewake Stop hook; I can't install hooks into your settings
  from the sandbox. You run it from a test plugin I prepare - recommended: yes
  - blocks: steps 3-5

## Status
Approved - building

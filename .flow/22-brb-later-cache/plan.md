# flow: opt-in /brb cache warmer and /later compactor

## Goal
Before a break, the user runs `/brb 90m` and comes back to a warm prompt cache
instead of paying a full cache rewrite. `/later` compacts a session they're
leaving while its cache is still warm. Both are opt-in.

## Acceptance criteria
- `/brb <duration>` in Claude Code (CLI and desktop app) wakes the idle
  session about TTL minus a lead (55 min on 1h, 4 min on 5m) after the last
  turn, and keeps doing so until duration + grace (50% of the duration, at
  least one TTL).
- Each woken ping turn reads the cache (`cache_read_input_tokens` close to
  the full context) and is answered briefly.
- Any real user prompt cancels the timer. The plugin's own wakes do not.
- TTL comes from the latest `usage.cache_creation` in the transcript (1h vs
  5m tokens), re-read after each ping. Fallback: the settings precedence
  chain from the issue.
- No wake when the context is below a minimum-token threshold.
- On expiry, `/brb` falls back to compacting, if the step 1 spike finds a
  path that works. Otherwise its last wake posts a reminder to run
  `/compact`.
- `/later` compacts now, or tells the user to run `/compact` if the spike
  found no path.
- Codex: `/brb` hooks exit at once and never block. `/later` works as far as
  the spike allows.
- Hooks are stdlib-only and run on Python 3.9+, on Linux, macOS, and Windows.

## Seams under test
- `hooks/brb.py` run as a subprocess with stdin JSON (the existing
  test_hooks.py harness), with an env-injected clock and sleep - catches:
  arm/cancel/expiry state transitions, TTL parsing, schedule math, the
  Codex early exit, the cancel race during sleep / misses: whether the host
  really wakes the session and hits the cache (covered by the spike and a
  manual check at ship)
- `tests/flow/test_layout.py` - catches: user-only frontmatter and
  openai.yaml for `brb`/`later`, hook commands that resolve / misses:
  runtime behavior

## Steps
- [ ] Spike (throwaway, not committed as code): an asyncRewake Stop hook
  that sleeps 60s and exits 2, in the desktop app and the CLI. Check that it
  wakes an idle session, that the woken turn shows a full cache read, how it
  interacts with a typed draft, and that Codex doesn't block on it. Also
  look for any working auto-compact path: a woken turn, `claude -p --resume`
  with `/compact`, or Codex `codex exec resume`. Record the results under
  Decisions. If the asyncRewake wake fails, stop and re-plan.
- [ ] `brb.py` TTL and schedule: transcript parse (1h/5m, context size), the
  settings-precedence fallback, ping times, and grace. Tests first.
- [ ] `brb.py` arm/stop/prompt modes plus the `hooks.json` entries (an
  asyncRewake Stop and a UserPromptSubmit), with the Codex early exit and
  the min-token guard.
- [ ] `skills/brb/` user-only skill (SKILL.md and agents/openai.yaml), and
  add it to USER_ONLY.
- [ ] `skills/later/` user-only skill, plus the expiry fallback. Auto-compact
  if the spike found a path, otherwise a nudge.
- [ ] ADR 0012: asyncRewake as the ping path, state in the temp dir and not
  in `.flow/`, the Codex scope, and the compact fallback outcome.
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
- State lives in `tempfile.gettempdir()/flow-brb-<session_id>.json` - it
  belongs to the session, not the task, and nothing is written to the repo.
- The plugin's wakes arrive as system reminders, not user prompts, so the
  UserPromptSubmit cancel needs no nonce - per the hooks docs; the spike
  confirms it.

## Open questions

## Status
Awaiting GATE 1

# flow: opt-in /brb cache warmer and /later compactor
Source: https://github.com/ralphshao/ai-plugins/issues/22
Size: Large
VCS: vcs-git; host: host-github
Isolation: worktree /Users/ralph/.claude/worktrees/ai-plugins/sandbox-github-docker-a475be on branch claude/flow-22-8d0d52 (already made for this task)

## Request
Add opt-in `/brb` (keep the prompt cache warm for a break you'll come back from) and `/later` (compact now for a session you're leaving) to flow. `/brb` falls back to `/later` if you don't return.

### Context

An idle session past its cache TTL rewrites its whole context on the next turn, at 1.25x base input (5-min TTL) or 2x (1-hour TTL). A cache read costs ~0.1x and resets the TTL. Existing warmers ping blindly; making both actions opt-in avoids paying pings for sessions that are abandoned.

v1 scope: Claude Code gets both commands. Codex gets `/later` only (no retention control, no published in-memory TTL, so ping timing would be guesswork).

### Design

| Piece | Behavior |
|---|---|
| `/brb [duration]` e.g. `/brb 90m` | Ping at TTL minus a lead (~55 min on 1h, ~4 min on 5m) until duration + grace |
| Grace | ~50% of stated duration, or one extra TTL |
| Fallback | Not back by then: compact while the cache is still warm |
| `/later` | Compact now, while warm |
| Return | Any user prompt (UserPromptSubmit hook) cancels the timer; ignore the plugin's own pings |
| Timer | Stop hook arms an external scheduler after the turn ends |
| TTL detection | 1) last turn with writes: `usage.cache_creation.ephemeral_1h_input_tokens` vs `ephemeral_5m_input_tokens` from the transcript; 2) fallback: replicate settings precedence (`FORCE_PROMPT_CACHING_5M` → `CLAUDE_CODE_PROMPT_CACHE_TTL` → `promptCacheTtl` → `ENABLE_PROMPT_CACHING_1H` → plan default) |
| Re-detect | After each ping (Pro drops to 5m when usage credits kick in) |
| Guards | Skip if session active, draft in input box, or context below a min-token threshold |
| Codex `/later` | Compact via the same injection path; read size/idle from `~/.codex/sessions/.../rollout-*.jsonl` |

### Cost math

C = context size. Multipliers: 5m write 1.25x, 1h write 2x, read 0.1x ([Anthropic prompt caching docs](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)).

| 1.5h break on 1h TTL | Cost |
|---|---|
| Do nothing | 2.0xC rewrite |
| `/brb 90m` | ~0.1xC ping + 0.1xC read |
| `/later` | ~0.1xC + 2x summary size |

| Breakeven | Value |
|---|---|
| Pings worth sending if you return (1h TTL) | up to ~20 (0.1xC vs 2xC) |
| 1h TTL vs warmer on 5m, 10-15 min gaps | ~2.5 breaks/session |
| 1h TTL vs no warmer | ~1 break/session |

Output tokens ignored.

### Open questions

- [ ] Injection mechanism: tmux, cmux, or other. A hook can't submit a prompt, so pings and `/compact` need terminal injection. Spike decides.
- [ ] Confirm Claude Code's transcript JSONL stores the per-turn `cache_creation` 1h/5m breakdown.
- [ ] Any documented programmatic way to trigger `/compact` (vs. typing it)?
- [ ] Stop-hook `decision: "block"` as an alternative ping path (no terminal needed), and whether it can fit the timer model without blocking the input prompt.
- [ ] Codex hook support for the `/later` path and how it injects `/compact`.
- [ ] Desktop app / non-terminal sessions: likely unsupported in v1.

### Prior art

- [Aider `--cache-keepalive-pings`](https://aider.chat/docs/usage/caching.html): built-in keepalive in a widely used agent.

### References

- [How Claude Code uses prompt caching](https://code.claude.com/docs/en/prompt-caching): TTL buckets, settings precedence, compaction cost, cache-read reset.
- [OpenAI prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching): retention policies (context for Codex scope).

## Constraints
- Plugins run on user's python3 (3.9+), stdlib only; no new dependencies.
- Tests live in `tests/flow/`, offline; CI on Linux, macOS, Windows.
- No version bump unless the user names one.

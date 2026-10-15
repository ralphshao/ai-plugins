#!/usr/bin/env python3
"""Opt-in prompt-cache keepalive for /brb (Claude Code only).

Timing logic first: how long the session's cache lives (its TTL), how big
the context is, and when the next wake is due. The hook modes below use it.
"""
import json
import os
import re
import sys
import tempfile
import time
import uuid
from pathlib import Path

HOUR, FIVE_MIN = 3600, 300
LEAD = {HOUR: 5 * 60, FIVE_MIN: 60}  # wake this long before the cache expires
DEFAULT_DURATION = {HOUR: HOUR, FIVE_MIN: 30 * 60}  # bare /brb
MIN_CONTEXT = 20_000  # below this a cold rewrite is too cheap to bother


def parse_duration(text):
    """'90m', '1h30m', '2h', '45' (minutes) -> seconds; None if unparseable."""
    text = (text or "").strip().lower()
    if re.fullmatch(r"\d+", text):
        return int(text) * 60
    m = re.fullmatch(r"(?:(\d+)h)?\s*(?:(\d+)m)?", text)
    if not text or not m:
        return None
    return int(m.group(1) or 0) * HOUR + int(m.group(2) or 0) * 60


def last_usage(transcript_path):
    """The newest assistant usage that has a cache_creation breakdown."""
    try:
        lines = Path(transcript_path).read_text(encoding="utf-8").splitlines()
    except (OSError, TypeError):
        return None
    for line in reversed(lines):
        if '"cache_creation"' not in line:
            continue
        try:
            usage = json.loads(line)["message"]["usage"]
        except (ValueError, KeyError, TypeError):
            continue
        if isinstance(usage.get("cache_creation"), dict):
            return usage
    return None


def context_tokens(usage):
    if not usage:
        return 0
    return sum(usage.get(k) or 0 for k in
               ("input_tokens", "cache_creation_input_tokens",
                "cache_read_input_tokens"))


def _ttl_value(value):
    return {"1h": HOUR, "5m": FIVE_MIN}.get(str(value).strip().lower())


def settings_ttl(env, settings_files):
    """Claude Code's documented precedence for the main conversation's TTL."""
    if env.get("FORCE_PROMPT_CACHING_5M") == "1":
        return FIVE_MIN
    ttl = _ttl_value(env.get("CLAUDE_CODE_PROMPT_CACHE_TTL", ""))
    if ttl:
        return ttl
    for path in settings_files:  # highest precedence first
        try:
            value = json.loads(Path(path).read_text(encoding="utf-8")).get(
                "promptCacheTtl")
        except (OSError, ValueError, AttributeError):
            continue
        if _ttl_value(value or ""):
            return _ttl_value(value)
    if env.get("ENABLE_PROMPT_CACHING_1H") == "1":
        return HOUR
    # shortcut: the plan default (1h on a subscription within plan usage) isn't
    # visible to hooks; 5m wakes early rather than late. Upgrade if Claude Code
    # exposes the billing mode.
    return FIVE_MIN


def settings_files(cwd, home=None):
    home = Path(home or Path.home())
    root = Path(cwd or ".")
    return [root / ".claude" / "settings.local.json",
            root / ".claude" / "settings.json",
            home / ".claude" / "settings.json"]


def detect_ttl(usage, env, files):
    """The TTL the last cache write used, else the settings chain."""
    cc = (usage or {}).get("cache_creation") or {}
    if (cc.get("ephemeral_1h_input_tokens") or 0) > 0:
        return HOUR
    if (cc.get("ephemeral_5m_input_tokens") or 0) > 0:
        return FIVE_MIN
    return settings_ttl(env, files)


def deadline(armed_at, duration, ttl):
    """End of /brb: duration plus grace (half the duration, at least one TTL)."""
    if duration is None:
        duration = DEFAULT_DURATION[ttl]
    return armed_at + duration + max(duration // 2, ttl)


def next_wake(now, ttl, until):
    """When to ping next, or None once that would pass /brb's deadline.

    After the deadline the session is left idle, and Claude Code's own idle
    compaction takes over.
    """
    when = now + ttl - LEAD[ttl]
    return when if when < until else None


# --- hook modes ---------------------------------------------------------------
#
# expand (UserPromptExpansion): typing `/brb [duration]` or `/flow:brb ...`
#   arms the keepalive. Codex has no such event, so it never arms there.
# prompt (UserPromptSubmit): any prompt except the `/brb` command itself
#   cancels it. This event also fires for scheduled tasks, background
#   subagents reporting back, and cross-session messages, which cancel it too.
#   The keepalive's own wakes arrive as system reminders and don't fire it.
# stop (Stop, asyncRewake): if armed, sleep until the next ping is due, then
#   exit 2 so Claude Code wakes the idle session. That ping turn ends with
#   another Stop, which re-reads the TTL and schedules the next one.
#
# State is one JSON file per session in the system temp folder: it belongs to
# the session, not to a task, and losing it only stops the keepalive.

BRB = re.compile(r"/(?:flow:)?brb(?:\s.*)?", re.S)
POLL = 30  # seconds between cancel checks while sleeping
PING = ("flow /brb keepalive: the user is away and this turn only keeps the "
        "prompt cache warm. Reply with only \"ok\". Don't run tools.")


def now():
    return float(os.environ.get("FLOW_BRB_NOW") or time.time())


def state_path(session_id):
    root = os.environ.get("FLOW_BRB_STATE_DIR") or tempfile.gettempdir()
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", str(session_id))
    return Path(root) / f"flow-brb-{safe}.json"


def load(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def save(path, state):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state), encoding="utf-8")
    os.replace(tmp, path)


def drop(path):
    try:
        path.unlink()
    except OSError:
        pass


def on_expand(data):
    path = state_path(data.get("session_id"))
    if data.get("command_name") not in ("brb", "flow:brb"):
        drop(path)
        return
    # Codex has no asyncRewake, and a sleeping Stop hook would block it.
    transcript = str(data.get("transcript_path") or "").replace("\\", "/")
    args = str(data.get("command_args") or "").strip()
    duration = parse_duration(args) if args else None
    if "/.codex/" in transcript or (args and not duration):
        drop(path)  # the skill tells the user a bad duration armed nothing
        return
    save(path, {"armed_at": now(), "duration": duration})


def on_prompt(data):
    if not BRB.fullmatch(str(data.get("prompt") or "").strip()):
        drop(state_path(data.get("session_id")))


def on_stop(data):
    """Return the exit code: 2 wakes the session for a ping, 0 does nothing."""
    path = state_path(data.get("session_id"))
    state = load(path)
    if not state:
        return 0
    usage = last_usage(data.get("transcript_path"))
    if context_tokens(usage) < MIN_CONTEXT:
        drop(path)
        return 0
    ttl = detect_ttl(usage, os.environ, settings_files(data.get("cwd")))
    until = state.get("until") or deadline(state["armed_at"],
                                           state.get("duration"), ttl)
    t = now()
    when = next_wake(t, ttl, until)
    if when is None:
        drop(path)
        return 0
    token = uuid.uuid4().hex  # a newer Stop's sleeper supersedes this one
    save(path, {**state, "until": until, "token": token})
    if not os.environ.get("FLOW_BRB_NO_SLEEP"):
        while t < when:
            time.sleep(min(POLL, when - t))
            t = time.time()
            if (load(path) or {}).get("token") != token:
                return 0
    if (load(path) or {}).get("token") != token:
        return 0
    print(PING, file=sys.stderr)
    return 2


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return 0
    if mode == "expand":
        on_expand(data)
        return 0
    if mode == "prompt":
        on_prompt(data)
        return 0
    if mode == "stop":
        return on_stop(data)
    return 0


if __name__ == "__main__":
    sys.exit(main())

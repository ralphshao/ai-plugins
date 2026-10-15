#!/usr/bin/env python3
"""Opt-in prompt-cache keepalive for /brb (Claude Code only).

This module holds the timing logic: how long the session's cache lives (its
TTL), how big the context is, and when the next wake is due. The hook modes
that arm and cancel the timer build on it.
"""
import json
import re
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

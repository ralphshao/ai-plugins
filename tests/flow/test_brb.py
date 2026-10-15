"""Tests for flow's brb.py timing logic: TTL detection and wake schedule."""

import importlib.util
import json

import pytest

from conftest import REPO_ROOT

spec = importlib.util.spec_from_file_location(
    "brb", REPO_ROOT / "plugins" / "flow" / "hooks" / "brb.py")
brb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(brb)

H, M5 = brb.HOUR, brb.FIVE_MIN


def usage_line(h1=0, m5=0, read=0):
    return json.dumps({"type": "assistant", "message": {"usage": {
        "input_tokens": 2, "cache_creation_input_tokens": h1 + m5,
        "cache_read_input_tokens": read,
        "cache_creation": {"ephemeral_5m_input_tokens": m5,
                           "ephemeral_1h_input_tokens": h1}}}})


@pytest.mark.parametrize("text,seconds", [
    ("90m", 5400), ("2h", 7200), ("1h30m", 5400), ("45", 2700),
    (" 10M ", 600), ("", None), ("soon", None), ("1d", None)])
def test_parse_duration(text, seconds):
    assert brb.parse_duration(text) == seconds


def test_last_usage_takes_the_newest_breakdown(tmp_path):
    t = tmp_path / "t.jsonl"
    t.write_text("\n".join([usage_line(h1=500), usage_line(m5=40, read=9000),
                            '{"type": "user"}', "not json"]), encoding="utf-8")
    usage = brb.last_usage(t)
    assert usage["cache_creation"]["ephemeral_5m_input_tokens"] == 40
    assert brb.context_tokens(usage) == 2 + 40 + 9000


def test_last_usage_missing_file():
    assert brb.last_usage("/nonexistent/t.jsonl") is None
    assert brb.context_tokens(None) == 0


@pytest.mark.parametrize("h1,m5,ttl", [(10, 0, H), (0, 10, M5)])
def test_detect_ttl_from_transcript(h1, m5, ttl):
    usage = json.loads(usage_line(h1=h1, m5=m5))["message"]["usage"]
    assert brb.detect_ttl(usage, {"FORCE_PROMPT_CACHING_5M": "1"}, []) == ttl


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_settings_chain_precedence(tmp_path):
    files = brb.settings_files(tmp_path / "proj", home=tmp_path / "home")
    write(files[2], {"promptCacheTtl": "1h"})
    assert brb.settings_ttl({}, files) == H
    write(files[0], {"promptCacheTtl": "5m"})  # local beats user
    assert brb.settings_ttl({}, files) == M5
    assert brb.settings_ttl({"CLAUDE_CODE_PROMPT_CACHE_TTL": "1h"}, files) == H
    assert brb.settings_ttl({"FORCE_PROMPT_CACHING_5M": "1",
                             "CLAUDE_CODE_PROMPT_CACHE_TTL": "1h"}, files) == M5


def test_settings_chain_fallbacks(tmp_path):
    files = brb.settings_files(tmp_path, home=tmp_path)
    write(files[1], {"promptCacheTtl": "2h"})  # invalid value is ignored
    assert brb.settings_ttl({"ENABLE_PROMPT_CACHING_1H": "1"}, files) == H
    assert brb.settings_ttl({}, files) == M5
    assert brb.detect_ttl(None, {}, files) == M5


def test_deadline_grace_and_default():
    assert brb.deadline(0, 5400, H) == 5400 + H         # grace is one TTL
    assert brb.deadline(0, 4 * H, H) == 6 * H           # grace is half
    assert brb.deadline(0, None, H) == 2 * H            # bare /brb on 1h
    assert brb.deadline(0, None, M5) == 45 * 60         # bare /brb on 5m


def test_next_wake():
    assert brb.next_wake(0, H, 2 * H) == 55 * 60
    assert brb.next_wake(0, M5, H) == 240
    assert brb.next_wake(H, H, 2 * H) == H + 55 * 60
    assert brb.next_wake(H + 300, H, 2 * H) is None

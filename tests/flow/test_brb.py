"""Tests for flow's brb.py timing logic: TTL detection and wake schedule."""

import importlib.util
import json
import os
import subprocess
import sys

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


# --- hook modes, run as the hooks run ----------------------------------------

SCRIPT = REPO_ROOT / "plugins" / "flow" / "hooks" / "brb.py"


@pytest.fixture
def run(tmp_path):
    transcript = tmp_path / "t.jsonl"
    transcript.write_text(usage_line(h1=500, read=50_000), encoding="utf-8")

    def run(mode, at=1000.0, **payload):
        env = {**os.environ, "FLOW_BRB_STATE_DIR": str(tmp_path),
               "FLOW_BRB_NOW": str(at), "FLOW_BRB_NO_SLEEP": "1"}
        payload = {"session_id": "s1", "transcript_path": str(transcript),
                   "cwd": str(tmp_path), **payload}
        p = subprocess.run([sys.executable, str(SCRIPT), mode],
                           input=json.dumps(payload), capture_output=True,
                           text=True, env=env)
        return p.returncode, p.stderr
    run.state = tmp_path / "flow-brb-s1.json"
    run.transcript = transcript
    return run


def test_stop_without_brb_does_nothing(run):
    assert run("stop") == (0, "")


def arm(run, args="", name="flow:brb", **kw):
    """Type `/<name> <args>`: the expansion arms, the submit must not cancel."""
    run("expand", command_name=name, command_args=args, **kw)
    run("prompt", prompt=f"/{name} {args}".strip(), **kw)


@pytest.mark.parametrize("name,args", [
    ("flow:brb", ""), ("flow:brb", "90m"), ("brb", " 2h "), ("brb", "1h 30m")])
def test_brb_arms_and_stop_pings(run, name, args):
    arm(run, args, name)
    assert run.state.exists()
    code, err = run("stop")
    assert code == 2 and "keepalive" in err
    assert json.loads(run.state.read_text())["until"] > 1000


def test_other_prompt_cancels(run):
    arm(run)
    run("prompt", prompt="I'm back")
    assert not run.state.exists()
    assert run("stop") == (0, "")


def test_other_command_cancels(run):
    arm(run)
    run("expand", command_name="flow:plan", command_args="")
    run("prompt", prompt="/flow:plan")
    assert not run.state.exists()


@pytest.mark.parametrize("args", ["soon", "0", "0m", "1h extra"])
def test_bad_duration_does_not_arm(run, args):
    arm(run, args)
    assert not run.state.exists()


@pytest.mark.parametrize("path", ["/home/u/.codex/sessions/rollout-1.jsonl",
                                  r"C:\Users\u\.codex\sessions\r.jsonl"])
def test_codex_never_arms(run, path):
    arm(run, transcript_path=path)
    assert not run.state.exists()


def test_stops_after_deadline(run):
    arm(run, "60m", at=0)                         # 1h TTL: until = 2h
    assert run("stop", at=0)[0] == 2
    assert run("stop", at=3300)[0] == 2           # next ping at 6600 < 7200
    assert run("stop", at=6600)[0] == 0           # 9900 would be past it
    assert not run.state.exists()


def test_small_context_is_not_worth_pinging(run):
    run.transcript.write_text(usage_line(h1=500), encoding="utf-8")
    arm(run)
    assert run("stop")[0] == 0
    assert not run.state.exists()


def test_bad_stdin_is_ignored():
    p = subprocess.run([sys.executable, str(SCRIPT), "stop"], input="nope",
                       capture_output=True, text=True)
    assert p.returncode == 0


@pytest.mark.parametrize("prompt", ["/brbx", "please /brb", ""])
def test_typed_text_never_arms(run, prompt):
    run("prompt", prompt=prompt)
    assert not run.state.exists()


def test_rearm_replaces_state_and_corrupt_state_is_inert(run):
    arm(run, "30m", at=5)
    assert json.loads(run.state.read_text()) == {"armed_at": 5.0,
                                                 "duration": 1800}
    run.state.write_text("{not json")
    assert run("stop") == (0, "")


def test_state_path_sanitizes_session_id(tmp_path, monkeypatch):
    monkeypatch.setenv("FLOW_BRB_STATE_DIR", str(tmp_path))
    p = brb.state_path("../../etc/x y")
    assert p.parent == tmp_path and "/" not in p.name


# --- in-process: the sleeping Stop hook and its cancel race --------------------

class Sleeper:
    """Armed /brb at t=1000 on a 1h TTL (wake due at 4300) with a fake clock."""

    def __init__(self, tmp_path, monkeypatch):
        transcript = tmp_path / "t.jsonl"
        transcript.write_text(usage_line(h1=500, read=50_000), encoding="utf-8")
        monkeypatch.setenv("FLOW_BRB_STATE_DIR", str(tmp_path))
        monkeypatch.setenv("FLOW_BRB_NOW", "1000")
        monkeypatch.delenv("FLOW_BRB_NO_SLEEP", raising=False)
        self.state = brb.state_path("s1")
        self.state.write_text(json.dumps({"armed_at": 1000, "duration": None}))
        self.clock, self.naps, self.on_nap = 1000.0, [], None
        self.data = {"session_id": "s1", "transcript_path": str(transcript),
                     "cwd": str(tmp_path)}
        monkeypatch.setattr(brb.time, "time", lambda: self.clock)
        monkeypatch.setattr(brb.time, "sleep", self.sleep)
        monkeypatch.setattr(brb, "POLL", 1000)

    def sleep(self, n):
        self.naps.append(n)
        self.clock += n
        if self.on_nap:
            self.on_nap(len(self.naps))


@pytest.fixture
def sleeper(tmp_path, monkeypatch):
    return Sleeper(tmp_path, monkeypatch)


def test_sleeping_stop_pings_in_poll_chunks(sleeper):
    assert brb.on_stop(sleeper.data) == 2
    assert sleeper.naps == [1000, 1000, 1000, 300]  # 3300s total, last short


def test_cancel_while_sleeping_exits_quietly(sleeper, capsys):
    sleeper.on_nap = lambda n: sleeper.state.unlink()
    assert brb.on_stop(sleeper.data) == 0
    assert len(sleeper.naps) == 1
    assert capsys.readouterr().err == ""


def test_superseded_while_sleeping_exits_quietly(sleeper):
    def newer_stop(n):
        st = json.loads(sleeper.state.read_text())
        sleeper.state.write_text(json.dumps({**st, "token": "newer"}))
    sleeper.on_nap = newer_stop
    assert brb.on_stop(sleeper.data) == 0
    assert json.loads(sleeper.state.read_text())["token"] == "newer"


def test_missing_usage_keeps_state_for_the_next_stop(run):
    run.transcript.write_text('{"type": "user"}', encoding="utf-8")
    arm(run)
    assert run("stop")[0] == 0
    assert run.state.exists()


def test_save_leaves_no_temp_files(tmp_path):
    path = tmp_path / "flow-brb-s.json"
    brb.save(path, {"a": 1})
    brb.save(path, {"a": 2})
    assert [p.name for p in tmp_path.iterdir()] == [path.name]
    assert brb.load(path) == {"a": 2}


def test_skill_states_the_hook_constants():
    skill = (REPO_ROOT / "plugins" / "flow" / "skills" / "brb" / "SKILL.md"
             ).read_text(encoding="utf-8")
    assert f"{brb.DEFAULT_DURATION[H] // 60}m on a 1h cache" in skill
    assert f"{brb.DEFAULT_DURATION[M5] // 60}m on 5m" in skill
    assert f"~{brb.MIN_CONTEXT // 1000}k tokens" in skill
    assert brb.PING.split(":")[0] in skill  # "flow /brb keepalive"


def test_hooks_json_wires_brb():
    hooks = json.loads((REPO_ROOT / "plugins" / "flow" / "hooks" / "hooks.json"
                        ).read_text(encoding="utf-8"))["hooks"]

    def brb_entries(event, mode):
        return [h for group in hooks.get(event, []) for h in group["hooks"]
                if h["command"].endswith(f'brb.py" {mode}')]

    (stop,) = brb_entries("Stop", "stop")
    assert stop["asyncRewake"] is True
    # Claude Code enforces timeout on asyncRewake hooks: it must outlast a sleep.
    assert stop["timeout"] > H - brb.LEAD[H]
    assert len(brb_entries("UserPromptSubmit", "prompt")) == 1
    assert len(brb_entries("UserPromptExpansion", "expand")) == 1

"""Tests for plugins/flow/scripts/codex_agents.py."""

import subprocess
import sys

import pytest

from conftest import REPO_ROOT

SCRIPT = REPO_ROOT / "plugins" / "flow" / "scripts" / "codex_agents.py"
tomllib = pytest.importorskip("tomllib")  # Python 3.11+


def generate(dest, env=None):
    p = subprocess.run([sys.executable, str(SCRIPT), "--dest", str(dest)],
                       capture_output=True, text=True, env=env)
    assert p.returncode == 0, p.stderr
    return {f.stem: tomllib.loads(f.read_text(encoding="utf-8"))
            for f in dest.glob("*.toml")}


def test_writes_one_valid_agent_per_file(tmp_path):
    agents = generate(tmp_path / "agents")
    assert set(agents) == {"flow-code-reviewer", "flow-review-validator", "flow-tester"}
    for name, agent in agents.items():
        assert agent["name"] == name
        assert agent["description"]
        assert agent["developer_instructions"].startswith("You are running in Codex.")


def test_sandbox_follows_write_tools(tmp_path):
    agents = generate(tmp_path)
    assert agents["flow-code-reviewer"]["sandbox_mode"] == "read-only"
    assert agents["flow-review-validator"]["sandbox_mode"] == "read-only"
    assert agents["flow-tester"]["sandbox_mode"] == "workspace-write"


def test_body_survives_round_trip(tmp_path):
    agents = generate(tmp_path)
    body = (REPO_ROOT / "plugins/flow/agents/code-reviewer.md").read_text(encoding="utf-8")
    body = body.split("\n---\n", 1)[1].strip()
    assert agents["flow-code-reviewer"]["developer_instructions"].endswith(body)


def test_rerun_overwrites(tmp_path):
    generate(tmp_path)
    (tmp_path / "flow-tester.toml").write_text("stale")
    assert generate(tmp_path)["flow-tester"]["name"] == "flow-tester"

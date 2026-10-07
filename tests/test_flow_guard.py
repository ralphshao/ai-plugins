"""Tests for plugins/flow/hooks/guard.py, run as the hook runs it."""

import json
import subprocess
import sys

import pytest

from conftest import REPO_ROOT

GUARD = REPO_ROOT / "plugins" / "flow" / "hooks" / "guard.py"
REVIEWERS = ["flow:code-reviewer", "flow:review-validator"]
TESTER = "flow:tester"
R = "/repo"

READ_ONLY = [
    "git diff 97e1347...HEAD --stat",
    f"git -C {R} show -s d2472e6",
    f"git -C {R} diff 97e1347...HEAD -- plugins/x.py",
    "git --no-pager log --oneline",
    'grep -n "def test_\\|snapshot\\|add_row" tests/test_remove.py',
    'grep -rniE "up to date|could not resolve" plugins README.md tests',
    'grep -rn "latest_sha\\|ref=\\"HEAD\\"\\|\\^{}" tests',
    "grep -rn 'a;b' src",
    "git log --oneline | head -5",
]
ALWAYS_DENIED = [
    "git show -s d2472e6 && git diff --stat",
    "ls tests; grep x y",
    "cat a > b",
    "grep x y 2>/dev/null",
    "cat $(echo /etc/passwd)",
    "cat `echo x`",
    "git -c core.pager=sh log",
    f"git -C {R} push",
    "git -C",
    "git push",
    "rm -rf x",
    "find . -delete",
    'grep "unbalanced',
    "ls |",
    "cat a\nrm b",
]
RUNNERS = ["pytest -q", "python3 -m pytest tests", "go test ./...", "npm test",
           "npx vitest run"]
BAD_RUNNERS = ["python3 -m pip install x", "python3 script.py", "npm install",
               "npx prettier --write ."]


def run(payload):
    p = subprocess.run([sys.executable, str(GUARD)], input=json.dumps(payload),
                       capture_output=True, text=True)
    return p.returncode, p.stderr


def bash(agent, cmd):
    payload = {"tool_name": "Bash", "tool_input": {"command": cmd}}
    if agent:
        payload["agent_type"] = agent
    return run(payload)[0]


def write(agent, path, tool="Write"):
    payload = {"tool_name": tool, "tool_input": {"file_path": path}}
    if agent:
        payload["agent_type"] = agent
    return run(payload)[0]


@pytest.mark.parametrize("agent", REVIEWERS + [TESTER])
@pytest.mark.parametrize("cmd", READ_ONLY)
def test_read_only_commands_allowed(agent, cmd):
    assert bash(agent, cmd) == 0


@pytest.mark.parametrize("agent", REVIEWERS + [TESTER])
@pytest.mark.parametrize("cmd", ALWAYS_DENIED)
def test_unsafe_commands_denied(agent, cmd):
    assert bash(agent, cmd) == 2


@pytest.mark.parametrize("cmd", RUNNERS)
def test_tester_may_run_tests(cmd):
    assert bash(TESTER, cmd) == 0


@pytest.mark.parametrize("agent", REVIEWERS)
@pytest.mark.parametrize("cmd", RUNNERS)
def test_reviewers_may_not_run_tests(agent, cmd):
    assert bash(agent, cmd) == 2


@pytest.mark.parametrize("cmd", BAD_RUNNERS)
def test_tester_runner_args_are_limited(cmd):
    assert bash(TESTER, cmd) == 2


@pytest.mark.parametrize("agent", REVIEWERS)
@pytest.mark.parametrize("tool", ["Write", "Edit"])
def test_reviewers_never_write(agent, tool):
    assert write(agent, "tests/test_x.py", tool) == 2


@pytest.mark.parametrize("path", ["tests/test_x.py", "src/foo_test.go",
                                  "web/a.spec.ts", "pkg/__tests__/a.js",
                                  "conftest.py", "src/FooTest.java"])
def test_tester_writes_test_files(path):
    assert write(TESTER, path) == 0


@pytest.mark.parametrize("path", ["src/app.py", "README.md", "tests.py"])
def test_tester_cannot_write_source(path):
    assert write(TESTER, path, "Edit") == 2


@pytest.mark.parametrize("agent", [None, "Explore", "code-reviewer", "other:tester"])
def test_other_callers_pass_through(agent):
    assert bash(agent, "rm -rf x") == 0
    assert write(agent, "src/app.py") == 0


def test_denial_explains_itself():
    code, err = run({"agent_type": TESTER, "tool_name": "Write",
                     "tool_input": {"file_path": "src/app.py"}})
    assert code == 2
    assert "only test files" in err

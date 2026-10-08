"""Tests for plugins/flow/hooks/guard.py, run as the hook runs it."""

import json
import subprocess
import sys

import pytest

from conftest import REPO_ROOT

GUARD = REPO_ROOT / "plugins" / "flow" / "hooks" / "guard.py"
# Claude Code names, then the Codex role names codex_agents.py installs.
REVIEWERS = ["flow:code-reviewer", "flow:correctness-reviewer", "flow:review-validator",
             "flow-code-reviewer", "flow-correctness-reviewer", "flow-review-validator"]
TESTERS = ["flow:tester", "flow-tester"]
TESTER = TESTERS[0]
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
    "p4 describe -S -du 12345",
    "p4 -ztag describe -s 12345",
    "p4 -z tag opened -c 12345",
    "p4 diff2 -du -S //depot/task-x",
    "p4 print -q //depot/main/a.py@=12345",
    "p4 annotate -c //depot/main/a.py",
    "p4 changes -l //depot/task-x/...",
    "p4 change -o 12345",
    "p4 client -o",
    "p4 stream -o //depot/task-x",
    "p4 diff -du | head -40",
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
    "p4 submit -c 12345",
    "p4 edit a.py",
    "p4 shelve -c 12345",
    "p4 print -o out.py //depot/a.py",
    "p4 print -o/tmp/x //depot/a.py",
    "p4 client -o -d ws",
    "p4 change -d 12345",
    "p4 change",
    "p4 -c other-client opened",
    "p4 -p ssl:evil:1666 info",
    "p4 -x cmds.txt edit",
    "p4",
    "p4 -z foo opened",
    "p4 -z",
    "p4 -ztag",
    "p4 -ztag edit a.py",
    "p4 -ztag -c other opened",
    "p4 -Ztag opened",
    "p4 -ztag print -q -o out.py //depot/a.py",
    "p4 client -d ws",
    "p4 stream -i",
    "p4 change -f -o 12345",
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


@pytest.mark.parametrize("agent", REVIEWERS + TESTERS)
@pytest.mark.parametrize("cmd", READ_ONLY)
def test_read_only_commands_allowed(agent, cmd):
    assert bash(agent, cmd) == 0


@pytest.mark.parametrize("agent", REVIEWERS + TESTERS)
@pytest.mark.parametrize("cmd", ALWAYS_DENIED)
def test_unsafe_commands_denied(agent, cmd):
    assert bash(agent, cmd) == 2


@pytest.mark.parametrize("agent", TESTERS)
@pytest.mark.parametrize("cmd", RUNNERS)
def test_tester_may_run_tests(agent, cmd):
    assert bash(agent, cmd) == 0


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


@pytest.mark.parametrize("agent", TESTERS)
@pytest.mark.parametrize("path", ["tests/test_x.py", "src/foo_test.go",
                                  "web/a.spec.ts", "pkg/__tests__/a.js",
                                  "conftest.py", "src/FooTest.java"])
def test_tester_writes_test_files(agent, path):
    assert write(agent, path) == 0


@pytest.mark.parametrize("agent", TESTERS)
@pytest.mark.parametrize("path", ["src/app.py", "README.md", "tests.py"])
def test_tester_cannot_write_source(agent, path):
    assert write(agent, path, "Edit") == 2


@pytest.mark.parametrize("agent", [None, "Explore", "code-reviewer", "other:tester",
                                   "default", "explorer", "worker"])
def test_other_callers_pass_through(agent):
    assert bash(agent, "rm -rf x") == 0
    assert write(agent, "src/app.py") == 0


def test_denial_explains_itself():
    code, err = run({"agent_type": TESTER, "tool_name": "Write",
                     "tool_input": {"file_path": "src/app.py"}})
    assert code == 2
    assert "only test files" in err


def apply_patch(agent, *headers):
    body = "".join(f"*** {h}\n+x\n" for h in headers)
    return run({"agent_type": agent, "tool_name": "apply_patch",
                "tool_input": {"command": f"*** Begin Patch\n{body}*** End Patch\n"}})[0]


@pytest.mark.parametrize("agent", REVIEWERS)
def test_reviewers_never_patch(agent):
    assert apply_patch(agent, "Update File: tests/test_x.py") == 2


@pytest.mark.parametrize("agent", TESTERS)
@pytest.mark.parametrize("headers", [
    ["Add File: tests/test_new.py"],
    ["Update File: tests/test_x.py", "Delete File: tests/test_old.py"],
    ["Update File: tests/a.py", "Move to: tests/b.py"],
])
def test_tester_patches_test_files(agent, headers):
    assert apply_patch(agent, *headers) == 0


@pytest.mark.parametrize("agent", TESTERS)
@pytest.mark.parametrize("headers", [
    ["Add File: src/app.py"],
    ["Update File: tests/test_x.py", "Update File: src/app.py"],
    ["Delete File: src/app.py"],
    ["Update File: tests/test_x.py", "Move to: src/app.py"],
    [],
])
def test_tester_cannot_patch_source(agent, headers):
    assert apply_patch(agent, *headers) == 2


@pytest.mark.parametrize("agent", [None, "explorer"])
def test_other_callers_patch_freely(agent):
    assert apply_patch(agent, "Update File: src/app.py") == 0


def raw(stdin):
    p = subprocess.run([sys.executable, str(GUARD)], input=stdin,
                       capture_output=True, text=True)
    return p.returncode, p.stderr


@pytest.mark.parametrize("agent", REVIEWERS + TESTERS)
def test_guard_fails_closed_for_flow_agents(agent):
    # tool_input of the wrong type makes check() raise.
    code, err = run({"agent_type": agent, "tool_name": "Bash", "tool_input": "ls"})
    assert code == 2 and "guard failed" in err
    code, _ = raw('{"agent_type": "%s", "tool_name": ' % agent)
    assert code == 2


def test_guard_fails_open_for_others():
    assert run({"tool_name": "Bash", "tool_input": "ls"})[0] == 0
    assert raw("not json")[0] == 0


@pytest.mark.parametrize("agent", TESTERS)
@pytest.mark.parametrize("path", ["tests/../src/app.py", "/repo/tests/../src/app.py",
                                  "/home/me/tests/repo/src/app.py"])
def test_tester_cannot_escape_test_folders(agent, path):
    payload = {"agent_type": agent, "tool_name": "Write", "cwd": "/home/me/tests/repo",
               "tool_input": {"file_path": path}}
    assert run(payload)[0] == 2


@pytest.mark.parametrize("agent", TESTERS)
def test_tester_absolute_test_path_inside_cwd(agent):
    payload = {"agent_type": agent, "tool_name": "Write", "cwd": "/home/me/tests/repo",
               "tool_input": {"file_path": "/home/me/tests/repo/tests/test_a.py"}}
    assert run(payload)[0] == 0


@pytest.mark.parametrize("agent", TESTERS)
def test_tester_cannot_hide_an_indented_header(agent):
    patch = ("*** Begin Patch\n*** Add File: tests/test_a.py\n+x\n"
             " \t*** Update File: src/main.py\n@@\n-a\n+b\n*** End Patch\n")
    assert run({"agent_type": agent, "tool_name": "apply_patch",
                "tool_input": {"command": patch}})[0] == 2


@pytest.mark.parametrize("agent", TESTERS)
def test_patch_import_failure_fails_closed(agent, tmp_path):
    lonely = tmp_path / "guard.py"  # no patch.py beside it
    lonely.write_text(GUARD.read_text(encoding="utf-8"), encoding="utf-8")
    p = subprocess.run([sys.executable, str(lonely)], capture_output=True, text=True,
                       input=json.dumps({"agent_type": agent, "tool_name": "apply_patch",
                                         "tool_input": {"command": "*** Add File: tests/a.py"}}))
    assert p.returncode == 2

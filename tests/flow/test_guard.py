"""Tests for plugins/flow/hooks/guard.py, run as the hook runs it."""

import json
import subprocess
import sys

import pytest

from conftest import REPO_ROOT

GUARD = REPO_ROOT / "plugins" / "flow" / "hooks" / "guard.py"
# Claude Code names, then the Codex role names codex_agents.py installs.
REVIEWERS = ["flow:code-reviewer", "flow:strong-reviewer", "flow:review-validator",
             "flow-code-reviewer", "flow-strong-reviewer", "flow-review-validator"]
TESTERS = ["flow:tester", "flow-tester"]
# guard.py maps every name above to one of two policies, so the command and
# path cases run once per policy; test_each_name_gets_its_policy covers the
# mapping for every name.
REVIEWER = REVIEWERS[0]
TESTER = TESTERS[0]
POLICIES = [REVIEWER, TESTER]
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
    # Backticks and $( are plain text inside single quotes.
    "grep -n '`git \\|`gh ' plugins/flow/skills/plan/SKILL.md",
    "grep -rn '$(' src",
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
    'grep "`id`" src',
    'grep "$(id)" src',
    "grep 'a'\"$(id)\" src",
    "grep 'a\\' `id`",
]
RUNNERS = ["pytest -q", "python3 -m pytest tests", "go test ./...", "npm test",
           "npx vitest run", "uv run pytest -q",
           "uv run --offline --with pytest pytest tests -q",
           "uv run --python 3.9 --with pytest pytest",
           "uv run --frozen --with pytest-cov --with coverage pytest",
           "uv run python -m pytest", "uvx pytest -q"]
BAD_RUNNERS = ["python3 -m pip install x", "python3 script.py", "npm install",
               "npx prettier --write .", "uv run python script.py",
               "uv run --with evil pytest", "uv run --with=evil pytest",
               "uv run rm -rf x", "uv pip install x", "uv run", "uv run --python",
               "uv run --index-url http://x pytest", "uv run --script x.py",
               "uvx ruff check", "uvx --from evil pytest"]


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


@pytest.mark.parametrize("agent", POLICIES)
@pytest.mark.parametrize("cmd", READ_ONLY)
def test_read_only_commands_allowed(agent, cmd):
    assert bash(agent, cmd) == 0


@pytest.mark.parametrize("agent", POLICIES)
@pytest.mark.parametrize("cmd", ALWAYS_DENIED)
def test_unsafe_commands_denied(agent, cmd):
    assert bash(agent, cmd) == 2


@pytest.mark.parametrize("cmd", RUNNERS)
def test_tester_may_run_tests(cmd):
    assert bash(TESTER, cmd) == 0


@pytest.mark.parametrize("cmd", RUNNERS)
def test_reviewers_may_not_run_tests(cmd):
    assert bash(REVIEWER, cmd) == 2


@pytest.mark.parametrize("cmd", BAD_RUNNERS)
def test_tester_runner_args_are_limited(cmd):
    assert bash(TESTER, cmd) == 2


@pytest.mark.parametrize("tool", ["Write", "Edit"])
def test_reviewers_never_write(tool):
    assert write(REVIEWER, "tests/test_x.py", tool) == 2


@pytest.mark.parametrize("path", ["tests/test_x.py", "src/foo_test.go",
                                  "web/a.spec.ts", "pkg/__tests__/a.js",
                                  "conftest.py", "src/FooTest.java"])
def test_tester_writes_test_files(path):
    assert write(TESTER, path) == 0


@pytest.mark.parametrize("path", ["src/app.py", "README.md", "tests.py"])
def test_tester_cannot_write_source(path):
    assert write(TESTER, path, "Edit") == 2


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


def test_reviewers_never_patch():
    assert apply_patch(REVIEWER, "Update File: tests/test_x.py") == 2


@pytest.mark.parametrize("headers", [
    ["Add File: tests/test_new.py"],
    ["Update File: tests/test_x.py", "Delete File: tests/test_old.py"],
    ["Update File: tests/a.py", "Move to: tests/b.py"],
])
def test_tester_patches_test_files(headers):
    assert apply_patch(TESTER, *headers) == 0


@pytest.mark.parametrize("headers", [
    ["Add File: src/app.py"],
    ["Update File: tests/test_x.py", "Update File: src/app.py"],
    ["Delete File: src/app.py"],
    ["Update File: tests/test_x.py", "Move to: src/app.py"],
    [],
])
def test_tester_cannot_patch_source(headers):
    assert apply_patch(TESTER, *headers) == 2


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


@pytest.mark.parametrize("agent", REVIEWERS + TESTERS)
def test_each_name_gets_its_policy(agent):
    # Both policies block source writes, which unguarded callers may make;
    # only the tester may run tests.
    assert write(agent, "src/app.py") == 2
    assert bash(agent, "pytest -q") == (0 if agent in TESTERS else 2)


def test_guard_fails_open_for_others():
    assert run({"tool_name": "Bash", "tool_input": "ls"})[0] == 0
    assert raw("not json")[0] == 0


@pytest.mark.parametrize("path", ["tests/../src/app.py", "/repo/tests/../src/app.py",
                                  "/home/me/tests/repo/src/app.py"])
def test_tester_cannot_escape_test_folders(path):
    payload = {"agent_type": TESTER, "tool_name": "Write", "cwd": "/home/me/tests/repo",
               "tool_input": {"file_path": path}}
    assert run(payload)[0] == 2


def test_tester_absolute_test_path_inside_cwd():
    payload = {"agent_type": TESTER, "tool_name": "Write", "cwd": "/home/me/tests/repo",
               "tool_input": {"file_path": "/home/me/tests/repo/tests/test_a.py"}}
    assert run(payload)[0] == 0


def test_tester_cannot_hide_an_indented_header():
    patch = ("*** Begin Patch\n*** Add File: tests/test_a.py\n+x\n"
             " \t*** Update File: src/main.py\n@@\n-a\n+b\n*** End Patch\n")
    assert run({"agent_type": TESTER, "tool_name": "apply_patch",
                "tool_input": {"command": patch}})[0] == 2


def test_patch_import_failure_fails_closed(tmp_path):
    lonely = tmp_path / "guard.py"  # no patch.py beside it
    lonely.write_text(GUARD.read_text(encoding="utf-8"), encoding="utf-8")
    p = subprocess.run([sys.executable, str(lonely)], capture_output=True, text=True,
                       input=json.dumps({"agent_type": TESTER, "tool_name": "apply_patch",
                                         "tool_input": {"command": "*** Add File: tests/a.py"}}))
    assert p.returncode == 2


# Main-session guard after GATE 1: no agent_type, a plan whose Status starts
# with Approved, and no unticked open question.
PLAN = """# t

## Steps
- [ ] one

## Test command
`pytest`

## Open questions
{questions}
## Status
{status}
"""


def main_repo(tmp_path, status="Approved - building", questions=""):
    flow = tmp_path / ".flow" / "t"
    flow.mkdir(parents=True)
    (flow / "plan.md").write_text(PLAN.format(status=status, questions=questions))
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_a.py").write_text("def test_a():\n    assert 1\n")
    return tmp_path


def main_call(root, tool, path, **inp):
    code, err = run({"tool_name": tool, "cwd": str(root),
                     "tool_input": {"file_path": str(root / path), **inp}})
    return code, err


def test_main_cannot_change_test_command(tmp_path):
    root = main_repo(tmp_path)
    code, err = main_call(root, "Edit", ".flow/t/plan.md",
                          old_string="`pytest`", new_string="`true`")
    assert code == 2
    assert "open question" in err


def test_main_cannot_rewrite_plan_test_command(tmp_path):
    root = main_repo(tmp_path)
    text = (root / ".flow/t/plan.md").read_text().replace("`pytest`", "`true`")
    assert main_call(root, "Write", ".flow/t/plan.md", content=text)[0] == 2


def test_main_may_tick_steps(tmp_path):
    root = main_repo(tmp_path)
    assert main_call(root, "Edit", ".flow/t/plan.md",
                     old_string="- [ ] one", new_string="- [x] one")[0] == 0


def test_main_cannot_change_existing_test_lines(tmp_path):
    root = main_repo(tmp_path)
    assert main_call(root, "Edit", "tests/test_a.py",
                     old_string="assert 1", new_string="pass")[0] == 2


def test_main_may_add_to_existing_test(tmp_path):
    root = main_repo(tmp_path)
    assert main_call(root, "Edit", "tests/test_a.py", old_string="assert 1",
                     new_string="assert 1\n\n\ndef test_b():\n    assert 2")[0] == 0


def test_main_cannot_overwrite_test_dropping_lines(tmp_path):
    root = main_repo(tmp_path)
    assert main_call(root, "Write", "tests/test_a.py",
                     content="def test_a():\n    pass\n")[0] == 2


def test_main_may_overwrite_test_keeping_lines(tmp_path):
    root = main_repo(tmp_path)
    content = "import os\n\ndef test_a():\n    assert 1\n"
    assert main_call(root, "Write", "tests/test_a.py", content=content)[0] == 0


def test_main_may_write_new_tests_and_source(tmp_path):
    root = main_repo(tmp_path)
    assert main_call(root, "Write", "tests/test_new.py", content="x")[0] == 0
    (root / "app.py").write_text("a = 1\n")
    assert main_call(root, "Edit", "app.py", old_string="a = 1",
                     new_string="a = 2")[0] == 0


@pytest.mark.parametrize("status,questions", [
    ("Awaiting GATE 1", ""),
    ("Approved - building", "- [ ] Q1 change the test? - blocks: 2\n"),
])
def test_main_unguarded_before_approval_or_while_parked(tmp_path, status, questions):
    root = main_repo(tmp_path, status, questions)
    assert main_call(root, "Edit", "tests/test_a.py",
                     old_string="assert 1", new_string="pass")[0] == 0


@pytest.mark.parametrize("new", ["# assert 1", "assert 1 or True", "assert 10"])
def test_main_cannot_wrap_existing_test_lines(tmp_path, new):
    root = main_repo(tmp_path)
    assert main_call(root, "Edit", "tests/test_a.py",
                     old_string="assert 1", new_string=new)[0] == 2


def test_main_cannot_drop_a_duplicate_line(tmp_path):
    root = main_repo(tmp_path)
    (root / "tests/test_a.py").write_text("assert 1\nassert 1\n")
    assert main_call(root, "Write", "tests/test_a.py", content="assert 1\n")[0] == 2


def test_main_replace_all_is_checked(tmp_path):
    root = main_repo(tmp_path)
    (root / "tests/test_a.py").write_text("x = 1\nassert x\n")
    assert main_call(root, "Edit", "tests/test_a.py", old_string="x",
                     new_string="y", replace_all=True)[0] == 2


def test_main_cannot_unapprove_the_plan(tmp_path):
    root = main_repo(tmp_path)
    assert main_call(root, "Edit", ".flow/t/plan.md",
                     old_string="Approved - building", new_string="Building")[0] == 2


def test_main_case_variant_paths_still_guarded(tmp_path):
    root = main_repo(tmp_path)
    (root / "Fixtures").mkdir()
    (root / "Fixtures/b.py").write_text("assert 1\n")
    assert main_call(root, "Edit", "Fixtures/b.py",
                     old_string="assert 1", new_string="pass")[0] == 2


def test_main_denial_is_labelled_and_ignores_agent_names_in_text(tmp_path):
    root = main_repo(tmp_path)
    (root / "tests/test_a.py").write_text('A = "flow:tester"\n')
    code, err = main_call(root, "Edit", "tests/test_a.py",
                          old_string='"flow:tester"', new_string='"x"')
    assert code == 2
    assert "flow main-session guard" in err


def test_main_bash_is_not_checked(tmp_path):
    root = main_repo(tmp_path)
    code, _ = run({"tool_name": "Bash", "cwd": str(root),
                   "tool_input": {"command": "sed -i s/assert/pass/ tests/test_a.py"}})
    assert code == 0


def test_other_agents_are_not_main_guarded(tmp_path):
    root = main_repo(tmp_path)
    code, _ = run({"agent_type": "general-purpose", "tool_name": "Edit", "cwd": str(root),
                   "tool_input": {"file_path": str(root / "tests/test_a.py"),
                                  "old_string": "assert 1", "new_string": "pass"}})
    assert code == 0


def test_main_one_parked_plan_lifts_guard_for_all_plans(tmp_path):
    root = main_repo(tmp_path)
    other = root / ".flow" / "u"
    other.mkdir()
    (other / "plan.md").write_text(
        PLAN.format(status="Approved - building", questions="- [ ] Q1 ask - blocks: 1\n"))
    assert main_call(root, "Edit", "tests/test_a.py",
                     old_string="assert 1", new_string="pass")[0] == 0

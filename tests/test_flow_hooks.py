"""Tests for flow's stop_gate.py and format.py hooks, run as the hooks run."""

import importlib.util
import json
import os
import subprocess
import sys

import pytest

from conftest import REPO_ROOT, git

HOOKS = REPO_ROOT / "plugins" / "flow" / "hooks"
PY = f'"{sys.executable}"'
PASS = f'{PY} -c "print(1)"'
FAIL = f'{PY} -c "import sys; print(\'boom\'); sys.exit(3)"'


def hook(name, payload, env=None):
    p = subprocess.run([sys.executable, str(HOOKS / name)],
                       input=json.dumps(payload), capture_output=True, text=True,
                       env=env)
    assert p.returncode == 0, p.stderr
    return p.stdout.strip(), p.stderr


def plan(status="Approved - building", command=FAIL, questions=""):
    return (f"# t\n\n## Steps\n- [x] a\n\n## Test command\n`{command}`\n\n"
            f"## Open questions\n{questions}\n## Status\n{status}\n")


@pytest.fixture
def repo(tmp_path):
    git("init", "-q", cwd=tmp_path)
    return tmp_path


def gate(repo, text=None, **payload):
    if text is not None:
        (repo / ".flow" / "x").mkdir(parents=True, exist_ok=True)
        (repo / ".flow" / "x" / "plan.md").write_text(text, encoding="utf-8")
    out, _ = hook("stop_gate.py", {"cwd": str(repo), **payload})
    return json.loads(out) if out else None


def test_gate_blocks_on_failing_tests(repo):
    result = gate(repo, plan())
    assert result["decision"] == "block"
    assert "exit 3" in result["reason"] and "boom" in result["reason"]
    assert ".flow/x/plan.md" in result["reason"]


def test_gate_finds_plan_from_a_subdirectory(repo):
    (repo / "src").mkdir()
    gate(repo, plan())
    out, _ = hook("stop_gate.py", {"cwd": str(repo / "src")})
    assert json.loads(out)["decision"] == "block"


@pytest.mark.parametrize("text", [
    plan(command=PASS),
    plan(status="Awaiting GATE 1"),
    plan(command=""),
    plan(questions="- [ ] Q1 which db? - recommended: sqlite - blocks: 2\n"),
], ids=["passing", "not-approved", "no-command", "parked"])
def test_gate_allows_stop(repo, text):
    assert gate(repo, text) is None


def test_gate_runs_when_questions_are_answered(repo):
    assert gate(repo, plan(questions="- [x] Q1 answered\n"))["decision"] == "block"


def test_gate_allows_second_stop_in_a_turn(repo):
    assert gate(repo, plan(), stop_hook_active=True) is None


def test_gate_without_plan_is_a_no_op(repo):
    assert gate(repo) is None


def test_gate_reads_fenced_command(repo):
    text = plan().replace(f"`{FAIL}`", f"```bash\n{FAIL}\n```")
    assert gate(repo, text)["decision"] == "block"


def fake_p4(tmp_path, client_root, code=0):
    """A PATH with a `p4` that reports client_root as the client and exits
    with code."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    script = bin_dir / "p4.py"
    script.write_text(f"print('... clientName ws')\nprint('... clientRoot {client_root.as_posix()}')\nraise SystemExit({code})\n")
    if os.name == "nt":
        (bin_dir / "p4.cmd").write_text(f'@"{sys.executable}" "{script}" %*\n')
    else:
        exe = bin_dir / "p4"
        exe.write_text(f"#!{sys.executable}\nexec(open({str(script)!r}).read())\n")
        exe.chmod(0o755)
    return {**os.environ, "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}


def test_gate_finds_plan_at_p4_client_root(tmp_path):
    ws = tmp_path / "ws"
    (ws / "src").mkdir(parents=True)
    gate(ws, plan())
    out, _ = hook("stop_gate.py", {"cwd": str(ws / "src")}, env=fake_p4(tmp_path, ws))
    assert json.loads(out)["decision"] == "block"


def test_gate_ignores_p4_client_root_outside_cwd(tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    gate(ws, plan())
    other = tmp_path / "other"
    other.mkdir()
    out, _ = hook("stop_gate.py", {"cwd": str(ws)}, env=fake_p4(tmp_path, other))
    assert json.loads(out)["decision"] == "block"  # falls back to cwd


def test_gate_ignores_failing_p4(tmp_path):
    ws = tmp_path / "ws"
    (ws / "src").mkdir(parents=True)
    gate(ws, plan())
    env = fake_p4(tmp_path, ws, code=1)
    assert hook("stop_gate.py", {"cwd": str(ws / "src")}, env=env)[0] == ""


def test_gate_without_git_or_p4_uses_cwd(tmp_path):
    empty = tmp_path / "empty-bin"
    empty.mkdir()
    gate(tmp_path, plan())
    out, _ = hook("stop_gate.py", {"cwd": str(tmp_path)},
                  env={**os.environ, "PATH": str(empty)})
    assert json.loads(out)["decision"] == "block"


def test_gate_finds_plan_in_linked_worktree(repo):
    git("-c", "user.name=t", "-c", "user.email=t@example.com",
        "commit", "-q", "--allow-empty", "-m", "init", cwd=repo)
    wt = repo.parent / (repo.name + "-wt")
    git("worktree", "add", "-q", "-b", "flow/x", str(wt), cwd=repo)
    (wt / "src").mkdir()
    gate(wt, plan())
    out, _ = hook("stop_gate.py", {"cwd": str(wt / "src")})
    assert json.loads(out)["decision"] == "block"


# --- format.py ---------------------------------------------------------------

@pytest.fixture(scope="module")
def fmt():
    spec = importlib.util.spec_from_file_location("flow_format", HOOKS / "format.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_format_needs_repo_opt_in(fmt, repo, monkeypatch):
    monkeypatch.setattr(fmt.shutil, "which", lambda name: f"/bin/{name}")
    src = repo / "pkg" / "a.py"
    src.parent.mkdir()
    src.write_text("x=1\n")
    assert fmt.formatter(src) is None
    (repo / "pyproject.toml").write_text("[tool.ruff]\nline-length = 88\n")
    assert fmt.formatter(src)[:2] == ["ruff", "format"]


def test_format_uses_local_prettier_only(fmt, repo):
    src = repo / "web" / "a.ts"
    src.parent.mkdir()
    src.write_text("let x=1\n")
    (repo / "package.json").write_text('{"prettier": {}}')
    assert fmt.formatter(src) is None  # config but no local install
    bin_dir = repo / "node_modules" / ".bin"
    bin_dir.mkdir(parents=True)
    (bin_dir / "prettier").write_text("")
    assert fmt.formatter(src)[0] == str(bin_dir / "prettier")


def test_format_go_needs_gofmt(fmt, repo, monkeypatch):
    src = repo / "main.go"
    src.write_text("package main\n")
    monkeypatch.setattr(fmt.shutil, "which", lambda name: None)
    assert fmt.formatter(src) is None
    monkeypatch.setattr(fmt.shutil, "which", lambda name: f"/bin/{name}")
    assert fmt.formatter(src)[0] == "gofmt"


def test_format_stops_at_repo_root(fmt, tmp_path, monkeypatch):
    # A ruff config above the repo must not opt the repo in.
    monkeypatch.setattr(fmt.shutil, "which", lambda name: f"/bin/{name}")
    (tmp_path / "ruff.toml").write_text("")
    inner = tmp_path / "inner"
    inner.mkdir()
    git("init", "-q", cwd=inner)
    src = inner / "a.py"
    src.write_text("")
    assert fmt.formatter(src) is None


@pytest.mark.parametrize("marker", [".p4config", "p4env"])
def test_format_stops_at_p4_workspace_root(fmt, tmp_path, monkeypatch, marker):
    monkeypatch.setattr(fmt.shutil, "which", lambda name: f"/bin/{name}")
    monkeypatch.setenv("P4CONFIG", "p4env")
    (tmp_path / "ruff.toml").write_text("")
    ws = tmp_path / "ws"
    (ws / "src").mkdir(parents=True)
    (ws / marker).write_text("P4CLIENT=ws\n")
    src = ws / "src" / "a.py"
    src.write_text("")
    assert fmt.formatter(src) is None


@pytest.mark.parametrize("payload", [
    {"tool_name": "Write", "tool_input": {"file_path": "does/not/exist.py"}},
    {"tool_name": "apply_patch", "tool_input": {"command": "*** Begin Patch"}},
    {"tool_name": "Write", "tool_input": {"file_path": "README.md"}},
])
def test_format_hook_is_quiet_when_nothing_to_do(payload, tmp_path):
    payload["cwd"] = str(tmp_path)
    assert hook("format.py", payload) == ("", "")

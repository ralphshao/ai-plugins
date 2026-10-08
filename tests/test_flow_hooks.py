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


def counting_gate(repo, out):
    """Run the gate with a passing command that counts its runs, and a
    private temp folder for the gate's fingerprint, both in out (outside
    the repo, where they'd change what git sees)."""
    counter = out / "runs"
    cmd = f'{PY} -c "open(r\'{counter}\', \'a\').write(\'x\')"'
    tmp = out / "tmp"
    tmp.mkdir()
    env = {**os.environ, "TMPDIR": str(tmp), "TEMP": str(tmp), "TMP": str(tmp)}

    def stop(text=None):
        if text is not None:
            (repo / ".flow" / "x").mkdir(parents=True, exist_ok=True)
            (repo / ".flow" / "x" / "plan.md").write_text(text, encoding="utf-8")
        assert hook("stop_gate.py", {"cwd": str(repo)}, env=env)[0] == ""
        return len(counter.read_text()) if counter.exists() else 0
    return stop, plan(command=cmd)


def test_gate_skips_when_nothing_changed_since_a_pass(repo, tmp_path_factory):
    stop, text = counting_gate(repo, tmp_path_factory.mktemp("out"))
    (repo / "a.py").write_text("1\n")
    assert stop(text) == 1
    assert stop() == 1  # unchanged: skipped
    (repo / ".flow" / "x" / "plan.md").write_text(text + "\n", encoding="utf-8")
    assert stop() == 1  # plan edits don't count
    (repo / "a.py").write_text("2\n")  # untracked file contents count
    assert stop() == 2
    git("add", "a.py", cwd=repo)
    git("-c", "user.name=t", "-c", "user.email=t@example.com",
        "commit", "-q", "-m", "a", cwd=repo)
    assert stop() == 3  # new HEAD
    assert stop() == 3
    (repo / "a.py").write_text("3\n")  # tracked edit
    assert stop() == 4
    (repo / "a.py").write_bytes(b"caf\xe9\n")  # not UTF-8
    assert stop() == 5
    assert stop() == 5


def test_gate_reruns_after_a_failure(repo):
    assert gate(repo, plan())["decision"] == "block"
    assert gate(repo)["decision"] == "block"  # a failure is never remembered


def test_gate_always_runs_outside_git(tmp_path, tmp_path_factory):
    ws = tmp_path / "ws"
    ws.mkdir()
    stop, text = counting_gate(ws, tmp_path_factory.mktemp("out"))
    assert stop(text) == 1
    assert stop() == 2


def fake_bin(tmp_path, name, script):
    """A PATH with a `name` command that runs the Python script."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    path = bin_dir / f"{name}.py"
    path.write_text(script)
    if os.name == "nt":
        (bin_dir / f"{name}.cmd").write_text(f'@"{sys.executable}" "{path}" %*\n')
    else:
        exe = bin_dir / name
        exe.write_text(f"#!{sys.executable}\nexec(open({str(path)!r}).read())\n")
        exe.chmod(0o755)
    return {**os.environ, "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}


def fake_p4(tmp_path, client_root, code=0):
    """A PATH with a `p4` that reports client_root as the client and exits
    with code."""
    return fake_bin(tmp_path, "p4", f"print('... clientName ws')\nprint('... clientRoot {client_root.as_posix()}')\nraise SystemExit({code})\n")


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


@pytest.mark.parametrize("make_bad", [
    lambda p: p.write_bytes(b"caf\xe9\n"),  # not UTF-8
    lambda p: p.mkdir(),  # reading it raises OSError
], ids=["not-utf8", "unreadable"])
def test_gate_skips_a_plan_it_cannot_read(repo, make_bad):
    (repo / ".flow" / "a").mkdir(parents=True)
    make_bad(repo / ".flow" / "a" / "plan.md")
    gate(repo, plan())  # .flow/x/plan.md, a failing plan
    out, err = hook("stop_gate.py", {"cwd": str(repo)})
    assert json.loads(out)["decision"] == "block"
    assert ".flow/a/plan.md" in err.replace(os.sep, "/")


def fake_git(tmp_path, message):
    return fake_bin(tmp_path, "git", f"import sys\nsys.stderr.write({message!r})\nraise SystemExit(128)\n")


def test_gate_warns_when_git_fails(tmp_path):
    env = fake_git(tmp_path, "fatal: detected dubious ownership\n")
    _, err = hook("stop_gate.py", {"cwd": str(tmp_path)}, env=env)
    assert "dubious ownership" in err


def test_gate_is_quiet_outside_a_git_repo(tmp_path):
    env = fake_git(tmp_path, "fatal: not a git repository\n")
    assert hook("stop_gate.py", {"cwd": str(tmp_path)}, env=env) == ("", "")


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
    sys.path.insert(0, str(HOOKS))  # format.py imports its sibling patch.py
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
    assert fmt.formatter(src)[:2] == ["/bin/ruff", "format"]


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
    assert fmt.formatter(src)[0] == "/bin/gofmt"


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


def fake_gofmt(tmp_path):
    """A PATH whose `gofmt` appends a marker line to the file it formats."""
    return fake_bin(tmp_path, "gofmt", "import sys\nopen(sys.argv[-1], 'a').write('// formatted\\n')\n")


def test_format_formats_each_file_in_a_patch(repo, tmp_path):
    for name in ("added.go", "updated.go", "moved.go", "untouched.go"):
        (repo / name).write_text("package main\n")
    patch = ("*** Begin Patch\n*** Add File: added.go\n+package main\n"
             "*** Update File: updated.go\n@@\n"
             "*** Update File: old.go\n*** Move to: moved.go\n@@\n"
             "*** Delete File: gone.go\n*** End Patch\n")
    hook("format.py", {"cwd": str(repo), "tool_name": "apply_patch",
                       "tool_input": {"command": patch}}, env=fake_gofmt(tmp_path))
    formatted = {p.name for p in repo.glob("*.go") if "formatted" in p.read_text()}
    assert formatted == {"added.go", "updated.go", "moved.go"}


@pytest.mark.skipif(os.name == "nt", reason="symlinks need privileges on Windows")
def test_gate_runs_when_an_untracked_file_cannot_be_read(repo, tmp_path_factory):
    stop, text = counting_gate(repo, tmp_path_factory.mktemp("out"))
    (repo / "dangling").symlink_to(repo / "missing")
    assert stop(text) == 1
    assert stop() == 2  # can't prove nothing changed

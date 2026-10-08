#!/usr/bin/env python3
"""Stop hook: don't let a flow task stop while its tests fail.

Active only when the repo has a .flow/<slug>/plan.md whose Status starts with
"Approved" and whose "## Test command" section holds a command. It then runs
that command and, if it fails, blocks the stop with the tail of its output.

It allows the stop when:
- the plan has an unticked item under "## Open questions" (parked work
  waiting on the user), or
- stop_hook_active is set (the agent already got one block this turn), or
- in a git repo, nothing changed since the command last passed: same HEAD,
  same staged and unstaged diff, same untracked files and contents. Files
  under .flow/ don't count. The fingerprint lives in the system temp
  folder, so losing it costs one extra run.

The root is the git work tree, else the Perforce client root containing the
current directory, else the current directory.

The command comes from the repo's own plan file, so this runs the repo's
tests with the same trust as running them by hand.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

TIMEOUT = 600
TAIL = 40


def section(text, heading):
    m = re.search(rf"^## {re.escape(heading)}[ \t]*\n(.*?)(?=^## |\Z)",
                  text, re.M | re.S)
    return m.group(1) if m else ""


def test_command(text):
    for line in section(text, "Test command").splitlines():
        line = line.strip()
        if line and not line.startswith("```"):
            return line.strip("`").strip()
    return ""


def active_plans(root):
    """(plan path, test command) for each plan the gate applies to."""
    plans = []
    for path in sorted(root.glob(".flow/*/plan.md")):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            print(f"flow test gate: skipping {path}: {e}", file=sys.stderr)
            continue
        if not section(text, "Status").strip().startswith("Approved"):
            continue
        if re.search(r"^\s*- \[ \]", section(text, "Open questions"), re.M):
            return []  # parked: let it stop
        cmd = test_command(text)
        if cmd:
            plans.append((path, cmd))
    return plans


def run(cmd, cwd, text=True):
    """stdout of cmd (bytes unless text), or None if it's missing or fails."""
    exe = shutil.which(cmd[0])  # finds p4.bat/.cmd on Windows too
    if not exe:
        return None
    try:
        out = subprocess.run([exe, *cmd[1:]], cwd=cwd, capture_output=True,
                             text=text, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return out.stdout if out.returncode == 0 else None


def git_toplevel(cwd):
    """The git work tree containing cwd, or None. Warns when git fails for a
    reason other than cwd not being in a repo: the gate then looks for plans
    from cwd and, from a subdirectory, finds none."""
    exe = shutil.which("git")
    if not exe:
        return None
    try:
        # LC_ALL=C: git translates "not a git repository".
        out = subprocess.run([exe, "rev-parse", "--show-toplevel"], cwd=cwd,
                             capture_output=True, text=True, timeout=5,
                             env={**os.environ, "LC_ALL": "C"})
    except (OSError, subprocess.TimeoutExpired) as e:
        error = str(e)
    else:
        if out.returncode == 0 and out.stdout.strip():
            return Path(out.stdout.strip())
        if "not a git repository" in out.stderr:
            return None
        error = out.stderr.strip() or f"exit {out.returncode}"
    print(f"flow test gate: `git rev-parse` failed ({error}); looking for "
          f"plans from {cwd}.", file=sys.stderr)
    return None


def repo_root(cwd):
    """The git work tree, else the p4 client root containing cwd, else cwd."""
    cwd = Path(cwd).resolve()
    top = git_toplevel(cwd)
    if top:
        return top
    info = run(["p4", "-ztag", "info"], cwd) or ""
    m = re.search(r"^\.\.\. clientRoot (.+)$", info, re.M)
    if m:
        root = Path(m.group(1).strip()).resolve()
        if root == cwd or root in cwd.parents:
            return root
    return cwd


def fingerprint(root):
    """A hash of everything git sees outside .flow/, or None outside git."""
    outside_flow = ["--", ".", ":(exclude).flow"]
    # Bytes, not text: a diff of a non-UTF-8 file must not crash the gate.
    parts = [run(["git", "rev-parse", "-q", "--verify", "HEAD"], root, False) or b""]
    for cmd in (["git", "diff", "--binary"],
                ["git", "diff", "--binary", "--cached"],
                ["git", "ls-files", "-o", "--exclude-standard", "-z"]):
        out = run(cmd + outside_flow, root, False)
        if out is None:
            return None
        parts.append(out)
    h = hashlib.sha256(b"\0".join(parts))
    for name in filter(None, parts[-1].split(b"\0")):
        try:
            h.update((root / os.fsdecode(name)).read_bytes())
        except OSError:
            return None  # can't prove nothing changed: run the tests
    return h.hexdigest()


def pass_file(root, cmd):
    key = hashlib.sha256(f"{root}\0{cmd}".encode("utf-8")).hexdigest()[:16]
    return Path(tempfile.gettempdir()) / f"flow-stop-gate-{key}"


def main():
    data = json.load(sys.stdin)
    if data.get("stop_hook_active"):
        return
    root = repo_root(data.get("cwd") or ".")
    plans = active_plans(root)
    fp = fingerprint(root) if plans else None
    for path, cmd in plans:
        passed = pass_file(root, cmd)
        try:
            if fp and passed.read_text(encoding="utf-8") == fp:
                continue
        except OSError:
            pass
        try:
            run = subprocess.run(cmd, shell=True, cwd=root, capture_output=True,
                                 text=True, timeout=TIMEOUT)
        except subprocess.TimeoutExpired:
            print(f"flow test gate: `{cmd}` timed out after {TIMEOUT}s; "
                  "not blocking.", file=sys.stderr)
            continue
        if run.returncode != 0:
            tail = "\n".join((run.stdout + run.stderr).splitlines()[-TAIL:])
            rel = path.relative_to(root).as_posix()
            print(json.dumps({
                "decision": "block",
                "reason": (f"Tests fail for {rel} (`{cmd}`, exit "
                           f"{run.returncode}). Fix them before stopping, or "
                           "park the blocker as an open question.\n\n" + tail),
            }))
            return
        if fp:
            try:
                passed.write_text(fp, encoding="utf-8")
            except OSError:
                pass


if __name__ == "__main__":
    main()

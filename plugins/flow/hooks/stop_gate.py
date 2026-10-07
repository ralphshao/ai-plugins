#!/usr/bin/env python3
"""Stop hook: don't let a flow task stop while its tests fail.

Active only when the repo has a .flow/<slug>/plan.md whose Status starts with
"Approved" and whose "## Test command" section holds a command. It then runs
that command and, if it fails, blocks the stop with the tail of its output.

It allows the stop when:
- the plan has an unticked item under "## Open questions" (parked work
  waiting on the user), or
- stop_hook_active is set (the agent already got one block this turn).

The command comes from the repo's own plan file, so this runs the repo's
tests with the same trust as running them by hand.
"""
import json
import re
import subprocess
import sys
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
        text = path.read_text(encoding="utf-8")
        if not section(text, "Status").strip().startswith("Approved"):
            continue
        if re.search(r"^\s*- \[ \]", section(text, "Open questions"), re.M):
            return []  # parked: let it stop
        cmd = test_command(text)
        if cmd:
            plans.append((path, cmd))
    return plans


def repo_root(cwd):
    try:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=cwd,
                             capture_output=True, text=True)
    except OSError:
        return Path(cwd)
    return Path(out.stdout.strip()) if out.returncode == 0 else Path(cwd)


def main():
    data = json.load(sys.stdin)
    if data.get("stop_hook_active"):
        return
    root = repo_root(data.get("cwd") or ".")
    for path, cmd in active_plans(root):
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


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""PreToolUse guard for flow's subagents.

Claude Code ignores `hooks:` frontmatter on plugin agents, so the guards run
from the plugin's hooks.json instead and pick a policy by `agent_type`:

- flow:code-reviewer, flow:review-validator: read-only Bash (git, p4,
  file commands), no writes.
- flow:tester: read-only Bash plus test/coverage runners; writes to test
  files only.

Every other caller (the main session, other agents, Codex, which sends no
`agent_type`) passes through. Exit 2 blocks the call and shows stderr to the
agent.
"""
import json
import re
import shlex
import sys
from pathlib import PurePath
from typing import NoReturn

REVIEWERS = {"flow:code-reviewer", "flow:review-validator"}
TESTER = "flow:tester"

GIT_READ = {"diff", "log", "show", "status", "blame", "ls-files", "grep",
            "rev-parse", "merge-base"}
P4_READ = {"describe", "diff", "diff2", "print", "annotate", "filelog",
           "files", "fstat", "opened", "changes", "info", "where", "have"}
# Spec commands that only read with -o (no -o opens an editor or writes).
P4_SPEC = {"change", "changelist", "client", "stream"}
READ_CMDS = {"ls", "cat", "head", "tail", "wc", "grep", "rg", "find"}
# Test runners: first word -> allowed second words (None = any).
RUNNERS = {
    "pytest": None,
    "coverage": {"run", "report", "html", "json", "xml", "erase"},
    "python": {"-m"}, "python3": {"-m"},
    "go": {"test"},
    "cargo": {"test"},
    "npm": {"test"}, "pnpm": {"test"}, "yarn": {"test"},
    "npx": {"jest", "vitest"},
    "jest": None, "vitest": None,
}
PY_MODULES = {"pytest", "coverage", "unittest"}
# Flags that write files or run other programs.
BAD_FLAGS = {"-exec", "-execdir", "-ok", "-okdir", "-delete", "-fprint",
             "-fprint0", "-fprintf", "-fls", "--pre", "-O",
             "--open-files-in-pager", "--ext-diff"}
TEST_DIRS = {"test", "tests", "__tests__", "spec", "specs", "testdata",
             "fixtures"}
TEST_FILE = re.compile(
    r"^(test_.*|.*_test|.*\.(test|spec)|conftest|.*Tests?)\.\w+$")


class Denied(Exception):
    pass


def pipeline(cmd):
    """Split cmd into pipeline segments, honoring quotes.

    A | inside quotes (grep -E "a|b", grep "x\\|y") is part of the pattern,
    not a pipe. Any other shell operator outside quotes is denied.
    """
    # Quotes don't stop these from expanding, so check the raw string.
    if re.search(r"`|\$\(|\n", cmd):
        raise Denied("no newlines or command substitution")
    lex = shlex.shlex(cmd, posix=True, punctuation_chars=True)
    lex.whitespace_split = True
    try:
        tokens = list(lex)
    except ValueError:
        raise Denied("could not parse the command (unbalanced quotes?)")
    segments = [[]]
    for t in tokens:
        if t == "|":
            segments.append([])
        elif t and set(t) <= set("();<>|&"):
            raise Denied(f"'{t}' not allowed: run one command per call, "
                         "no &&, ;, or redirects")
        else:
            segments[-1].append(t)
    return segments


def check_bash(cmd, runners):
    for words in pipeline(cmd):
        if not words:
            raise Denied("empty pipeline segment")
        part = " ".join(words)
        if any(w in BAD_FLAGS or w.startswith("--output") for w in words):
            raise Denied(f"flag not allowed in: {part}")
        head, arg = words[0], words[1] if len(words) > 1 else None
        if head == "git":
            # Skip global options that only pick the repo or disable the
            # pager. -c stays blocked: it can set an alias that runs code.
            i = 1
            while i < len(words) and words[i] in ("-C", "--no-pager"):
                i += 2 if words[i] == "-C" else 1
            if i >= len(words) or words[i] not in GIT_READ:
                raise Denied(
                    f"git subcommand not allowed: {' '.join(words[:i + 1])}")
        elif head == "p4":
            check_p4(words)
        elif runners and head in RUNNERS:
            allowed = RUNNERS[head]
            if allowed is not None and arg not in allowed:
                raise Denied(f"only test/coverage runs allowed: {part}")
            if head.startswith("python") and (
                    len(words) < 3 or words[2] not in PY_MODULES):
                raise Denied("python -m only for pytest, coverage, unittest")
        elif head not in READ_CMDS:
            raise Denied(f"command not allowed: {head}")


def check_p4(words):
    """Read-only p4 subcommands. Global flags other than -ztag are denied:
    -c, -p, -u, -P, -x and friends pick another client, server, user, or a
    file of commands."""
    i = 1
    while i < len(words) and words[i].startswith("-"):
        if words[i] == "-ztag":
            i += 1
        elif words[i] == "-z" and words[i + 1:i + 2] == ["tag"]:
            i += 2
        else:
            raise Denied(f"p4 global flag not allowed: {words[i]}")
    sub, rest = (words[i], words[i + 1:]) if i < len(words) else (None, [])
    if sub in P4_SPEC and rest[:1] == ["-o"] and not any(
            w.startswith("-") for w in rest[1:]):
        return
    if sub not in P4_READ:
        raise Denied(f"p4 subcommand not allowed: {' '.join(words[:i + 1])}")
    if sub == "print" and any(w.startswith("-o") for w in rest):
        raise Denied("p4 print -o writes a file")


def check_test_path(path):
    p = PurePath(path)
    if TEST_DIRS.isdisjoint(p.parts[:-1]) and not TEST_FILE.match(p.name):
        raise Denied(f"only test files may be written: {path}")


def check(data):
    agent = data.get("agent_type")
    tool, inp = data.get("tool_name"), data.get("tool_input") or {}
    if agent in REVIEWERS:
        if tool == "Bash":
            check_bash(inp.get("command", ""), runners=False)
        elif tool in ("Write", "Edit"):
            raise Denied("reviewers never write files")
    elif agent == TESTER:
        if tool == "Bash":
            check_bash(inp.get("command", ""), runners=True)
        elif tool in ("Write", "Edit"):
            check_test_path(inp.get("file_path", ""))


def main() -> NoReturn:
    data = json.load(sys.stdin)
    try:
        check(data)
    except Denied as e:
        who = "tester" if data.get("agent_type") == TESTER else "reviewer"
        print(f"flow {who} guard blocked this: {e}", file=sys.stderr)
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()

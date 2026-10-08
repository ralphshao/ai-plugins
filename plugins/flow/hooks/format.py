#!/usr/bin/env python3
"""PostToolUse hook: format an edited file with the formatter the repo uses.

Runs only a formatter the repo already opts into, so it never reformats a
codebase that doesn't use one:

- .py: ruff, when ruff is on PATH and a ruff config exists.
- JS/TS/CSS/JSON/Markdown/YAML: the repo's own node_modules prettier, when
  a prettier config exists.
- .go: gofmt, when on PATH (Go code is always gofmt-formatted).
- .rs: rustfmt, when on PATH and the file sits in a Cargo project.

Never blocks: a formatter failure is reported on stderr and the edit stands.
Codex's apply_patch sends no file_path, so this does nothing there.
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

PRETTIER_EXTS = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".css",
                 ".scss", ".json", ".md", ".yaml", ".yml", ".html", ".vue"}
PRETTIER_CONFIGS = [".prettierrc", ".prettierrc.json", ".prettierrc.yaml",
                    ".prettierrc.yml", ".prettierrc.js", ".prettierrc.cjs",
                    ".prettierrc.mjs", ".prettierrc.toml",
                    "prettier.config.js", "prettier.config.cjs",
                    "prettier.config.mjs"]


def ancestors(path):
    """The file's directory and its parents, nearest first, up to the repo:
    a git work tree, or a Perforce workspace marked by its P4CONFIG file.
    Only the environment's P4CONFIG is seen, not one set with `p4 set`."""
    markers = {".git", ".p4config", os.environ.get("P4CONFIG") or ".p4config"}
    for d in path.parents:
        yield d
        if any((d / m).exists() for m in markers):
            return


def has_ruff_config(d):
    if (d / "ruff.toml").is_file() or (d / ".ruff.toml").is_file():
        return True
    pyproject = d / "pyproject.toml"
    return pyproject.is_file() and "[tool.ruff" in pyproject.read_text(
        encoding="utf-8", errors="replace")


def has_prettier_config(d):
    if any((d / name).is_file() for name in PRETTIER_CONFIGS):
        return True
    pkg = d / "package.json"
    if pkg.is_file():
        try:
            return "prettier" in json.loads(pkg.read_text(encoding="utf-8"))
        except ValueError:
            return False
    return False


def formatter(path):
    """The command to format path, or None."""
    ext = path.suffix.lower()
    dirs = list(ancestors(path))
    if ext == ".py" and shutil.which("ruff") and any(map(has_ruff_config, dirs)):
        return ["ruff", "format", "--quiet", str(path)]
    if ext in PRETTIER_EXTS and any(map(has_prettier_config, dirs)):
        for d in dirs:
            for name in ("prettier", "prettier.cmd"):
                exe = d / "node_modules" / ".bin" / name
                if exe.is_file():
                    return [str(exe), "--write", "--log-level", "warn", str(path)]
    if ext == ".go" and shutil.which("gofmt"):
        return ["gofmt", "-w", str(path)]
    if ext == ".rs" and shutil.which("rustfmt") and any(
            (d / "Cargo.toml").is_file() for d in dirs):
        return ["rustfmt", "--quiet", str(path)]
    return None


def main():
    data = json.load(sys.stdin)
    file_path = (data.get("tool_input") or {}).get("file_path")
    if not file_path:
        return
    path = Path(file_path)
    if not path.is_absolute():
        path = Path(data.get("cwd") or ".") / path
    if not path.is_file():
        return
    cmd = formatter(path.resolve())
    if not cmd:
        return
    try:
        run = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as e:
        print(f"flow format: {cmd[0]} failed: {e}", file=sys.stderr)
        return
    if run.returncode != 0:
        print(f"flow format: {' '.join(cmd)} exited {run.returncode}\n"
              f"{run.stderr.strip()}", file=sys.stderr)


if __name__ == "__main__":
    main()

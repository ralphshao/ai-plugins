#!/usr/bin/env python3
"""Maintain the ai-plugins marketplace: update, add, and remove pinned plugins.

Edits .claude-plugin/marketplace.json, .agents/plugins/marketplace.json, and
README.md's plugin table in the working tree of the repo containing the
current directory. Never commits. Standard library only; needs `git` on PATH.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

SELF = "ai-plugins"
CLAUDE_FILE = os.path.join(".claude-plugin", "marketplace.json")
CODEX_FILE = os.path.join(".agents", "plugins", "marketplace.json")
README_FILE = "README.md"
REMOTE_SOURCES = ("url", "github", "git-subdir")
DEFAULT_CATEGORY = "Productivity"

# README plugin table row: "| <name cell> | <description> | <version> |"
ROW_RE = re.compile(r"^\| (?P<name>[^|]+?) \| (?P<desc>.*) \| (?P<version>[^|]*?) \|$")
ROW_NAME_RE = re.compile(r"\[`?([^`\]]+)`?\]")


def die(msg):
    print(msg, file=sys.stderr)
    sys.exit(1)


def git(*args, cwd=None):
    result = subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"git {args[0]} failed")
    return result.stdout.strip()


def sort_key(plugin_name):
    # ai-plugins always first, everything else alphabetical.
    return (plugin_name != SELF, plugin_name.lower())


# --- JSON catalogs --------------------------------------------------------

def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_catalog(path, data):
    data["plugins"].sort(key=lambda p: sort_key(p["name"]))
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def find_plugin(data, name):
    return next((p for p in data["plugins"] if p["name"] == name), None)


# --- README table ---------------------------------------------------------

def read_readme_table():
    """Return (lines, start, end, rows) where rows maps name -> row line.

    start..end is the slice of body rows (after the header and separator).
    Returns None if README.md or its plugin table is missing.
    """
    if not os.path.isfile(README_FILE):
        return None
    with open(README_FILE, encoding="utf-8") as f:
        lines = f.read().split("\n")
    header = next(
        (i for i, line in enumerate(lines) if line.startswith("| Plugin |")), None
    )
    if header is None:
        return None
    start = header + 2
    end = start
    while end < len(lines) and lines[end].startswith("|"):
        end += 1
    rows = {}
    for line in lines[start:end]:
        m = ROW_NAME_RE.search(line.split("|")[1])
        if m:
            rows[m.group(1)] = line
    return lines, start, end, rows


def write_readme_table(table, rows):
    lines, start, end, _ = table
    body = [rows[name] for name in sorted(rows, key=sort_key)]
    lines[start:end] = body
    with open(README_FILE, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))


def readme_row(name, link, description, version):
    description = description.replace("|", "\\|")
    return f"| [{name}]({link}) | {description} | {version} |"


def set_row_version(row, version):
    m = ROW_RE.match(row)
    if not m:
        return row
    return f"| {m.group('name')} | {m.group('desc')} | {version} |"


# --- Git helpers ----------------------------------------------------------

def fetch_commit(url, ref):
    """Shallow-fetch one commit/ref into a temp dir checked out at FETCH_HEAD.

    Returns the temp dir path, or None on failure. Caller must remove it.
    """
    tmp = tempfile.mkdtemp(prefix="ai-plugins-")
    try:
        git("init", "-q", cwd=tmp)
        git("fetch", "-q", "--depth", "1", url, ref, cwd=tmp)
        git("checkout", "-q", "FETCH_HEAD", cwd=tmp)
        return tmp
    except RuntimeError:
        rmtree(tmp)
        return None


def rmtree(path):
    if not path:
        return

    def make_writable(func, p, _):
        # Windows marks .git objects read-only.
        os.chmod(p, 0o700)
        func(p)

    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=make_writable)
    else:
        shutil.rmtree(path, onerror=make_writable)


def latest_sha(url, ref):
    out = git("ls-remote", url, ref or "HEAD")
    return out.split("\t", 1)[0] if out else ""


def source_url(source):
    if source.get("source") == "github":
        return f"https://github.com/{source['repo']}.git"
    return source["url"]


def commit_subject(clone):
    if not clone:
        return ""
    try:
        return git("log", "-1", "--format=%s", cwd=clone)
    except RuntimeError:
        return ""


def read_manifest(root, subdir, kind):
    path = os.path.join(root, subdir, f".{kind}-plugin", "plugin.json")
    try:
        return load_json(path)
    except (OSError, ValueError):
        return None


# --- update ---------------------------------------------------------------

def cmd_update(_args):
    claude = load_json(CLAUDE_FILE)
    codex = load_json(CODEX_FILE) if os.path.isfile(CODEX_FILE) else None
    table = read_readme_table()
    rows = table[3] if table else {}

    remote = [
        p for p in claude["plugins"]
        if isinstance(p.get("source"), dict)
        and p["source"].get("source") in REMOTE_SOURCES
    ]
    if not remote:
        print(f"No remote-ref plugins found in {CLAUDE_FILE}")

    for plugin in remote:
        name = plugin["name"]
        source = plugin["source"]
        url = source_url(source)
        old_sha = source.get("sha", "")
        subdir = source.get("path", ".") if source["source"] == "git-subdir" else "."

        try:
            new_sha = latest_sha(url, source.get("ref"))
        except RuntimeError:
            new_sha = ""
        if not new_sha:
            print(f"== {name}: could not resolve latest ref from {url} ==\n")
            continue

        old_clone = fetch_commit(url, old_sha) if old_sha else None
        old_subject = commit_subject(old_clone)
        rmtree(old_clone)

        if old_sha == new_sha:
            print(f"== {name}: up to date ==")
            print(f"   {old_sha[:12]} {old_subject}\n")
            continue

        new_clone = fetch_commit(url, new_sha)
        new_subject = commit_subject(new_clone)
        manifest = read_manifest(new_clone, subdir, "claude") if new_clone else None
        rmtree(new_clone)
        new_version = (manifest or {}).get("version", "")
        old_version = plugin.get("version", "")

        print(f"== {name}: updated ==")
        print(f"   before: {old_sha[:12]} {old_subject}")
        print(f"   after:  {new_sha[:12]} {new_subject}")

        source["sha"] = new_sha
        codex_plugin = find_plugin(codex, name) if codex else None
        if codex_plugin and isinstance(codex_plugin.get("source"), dict):
            codex_plugin["source"]["sha"] = new_sha

        if new_version and new_version != old_version:
            print(f"   version: {old_version} -> {new_version}")
            plugin["version"] = new_version
            if name in rows:
                rows[name] = set_row_version(rows[name], new_version)
        print()

    save_catalog(CLAUDE_FILE, claude)
    if codex:
        save_catalog(CODEX_FILE, codex)
    if table:
        write_readme_table(table, rows)
    print_review_hint("Pinned refs (and versions, where changed) updated")


# --- add ------------------------------------------------------------------

def parse_repo(spec):
    """Turn a GitHub slug or URL into (clone_url, web_url, ref, path_hint)."""
    spec = spec.strip().rstrip("/")
    m = re.match(
        r"^(?:(?:https?://|git@)?(?:www\.)?github\.com[/:])?"
        r"(?P<owner>[\w.-]+)/(?P<repo>[\w.-]+?)(?:\.git)?"
        r"(?:/tree/(?P<ref>[^/]+)(?:/(?P<path>.+))?)?$",
        spec,
    )
    if m:
        owner, repo = m.group("owner"), m.group("repo")
        web = f"https://github.com/{owner}/{repo}"
        return f"{web}.git", web, m.group("ref"), m.group("path")
    if "://" in spec:
        web = spec[:-4] if spec.endswith(".git") else spec
        return f"{web}.git", web, None, None
    die(f"Not a GitHub URL or owner/repo slug: {spec}")


def find_manifests(root, kind):
    """Return repo-relative dirs containing .<kind>-plugin/plugin.json."""
    found = []
    for dirpath, dirnames, _ in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in (".git", "node_modules")]
        if os.path.isfile(os.path.join(dirpath, f".{kind}-plugin", "plugin.json")):
            rel = os.path.relpath(dirpath, root).replace(os.sep, "/")
            found.append("" if rel == "." else rel)
    return sorted(found)


def pick_manifest_dir(root, kind, path_hint):
    dirs = find_manifests(root, kind)
    if path_hint is not None:
        hint = re.sub(r"^(\./)+", "", path_hint).strip("/")
        dirs = [d for d in dirs if d == hint or d.startswith(hint + "/")]
    if len(dirs) > 1:
        listing = "\n".join(f"  {d or '.'}" for d in dirs)
        die(
            f"Found several .{kind}-plugin/plugin.json manifests:\n{listing}\n"
            "Re-run with --path <dir> to pick one."
        )
    return dirs[0] if dirs else None


def make_source(url, sha, subdir, codex_style=False):
    if not subdir:
        return {"source": "url", "url": url, "sha": sha}
    path = f"./{subdir}" if codex_style else subdir
    return {"source": "git-subdir", "url": url, "path": path, "sha": sha}


def cmd_add(args):
    clone_url, web_url, ref, path_hint = parse_repo(args.repo)
    if args.path is not None:
        path_hint = args.path

    pinned_ref = ref
    ref = ref or "HEAD"
    try:
        sha = latest_sha(clone_url, ref)
    except RuntimeError as e:
        die(f"Could not reach {clone_url}: {e}")
    if not sha:
        die(f"Could not resolve {ref} on {clone_url}")

    clone = fetch_commit(clone_url, sha)
    if not clone:
        die(f"Could not fetch {sha[:12]} from {clone_url}")
    try:
        claude_dir = pick_manifest_dir(clone, "claude", path_hint)
        codex_dir = pick_manifest_dir(clone, "codex", path_hint)
        claude_manifest = (
            read_manifest(clone, claude_dir, "claude") if claude_dir is not None else None
        )
        codex_manifest = (
            read_manifest(clone, codex_dir, "codex") if codex_dir is not None else None
        )
        subject = commit_subject(clone)
    finally:
        rmtree(clone)

    if not claude_manifest and not codex_manifest:
        die(
            f"No .claude-plugin/plugin.json or .codex-plugin/plugin.json found in "
            f"{web_url}{' under ' + path_hint if path_hint else ''}"
        )

    primary = claude_manifest or codex_manifest
    name = primary.get("name") or web_url.rsplit("/", 1)[-1]
    description = args.description or primary.get("description", "")
    version = primary.get("version", "")

    claude = load_json(CLAUDE_FILE)
    codex = load_json(CODEX_FILE) if os.path.isfile(CODEX_FILE) else None
    if find_plugin(claude, name) or (codex and find_plugin(codex, name)):
        die(f"A plugin named {name} is already in this marketplace")

    print(f"== {name}: adding ==")
    print(f"   repo:   {web_url}")
    print(f"   commit: {sha[:12]} {subject}")
    if version:
        print(f"   version: {version}")

    if claude_manifest:
        entry = {
            "name": name,
            "source": make_source(clone_url, sha, claude_dir),
            "description": description,
        }
        if pinned_ref:
            # update tracks this ref instead of the default branch.
            entry["source"]["ref"] = pinned_ref
        if version:
            entry["version"] = version
        if claude_manifest.get("author"):
            entry["author"] = claude_manifest["author"]
        claude["plugins"].append(entry)
        print(f"   claude: {'./' + claude_dir if claude_dir else 'repo root'}")
        save_catalog(CLAUDE_FILE, claude)
    else:
        print("   claude: no .claude-plugin/plugin.json, skipped")

    if codex is not None and codex_manifest:
        category = (codex_manifest.get("interface") or {}).get("category")
        codex["plugins"].append({
            "name": name,
            "source": make_source(clone_url, sha, codex_dir, codex_style=True),
            "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
            "category": category or DEFAULT_CATEGORY,
        })
        print(f"   codex:  {'./' + codex_dir if codex_dir else 'repo root'}")
        save_catalog(CODEX_FILE, codex)
    else:
        print("   codex:  no .codex-plugin/plugin.json, skipped (Claude-only)")

    table = read_readme_table()
    if table:
        rows = table[3]
        link = f"{web_url}/tree/HEAD/{claude_dir}" if claude_dir else web_url
        rows[name] = readme_row(name, link, description, version or "—")
        write_readme_table(table, rows)
    print()
    print_review_hint(f"Added {name}")


# --- remove ---------------------------------------------------------------

def cmd_remove(args):
    name = args.name
    if name == SELF:
        die(f"Refusing to remove {SELF} itself")

    removed = []
    claude = load_json(CLAUDE_FILE)
    if find_plugin(claude, name):
        claude["plugins"] = [p for p in claude["plugins"] if p["name"] != name]
        save_catalog(CLAUDE_FILE, claude)
        removed.append(CLAUDE_FILE)

    if os.path.isfile(CODEX_FILE):
        codex = load_json(CODEX_FILE)
        if find_plugin(codex, name):
            codex["plugins"] = [p for p in codex["plugins"] if p["name"] != name]
            save_catalog(CODEX_FILE, codex)
            removed.append(CODEX_FILE)

    table = read_readme_table()
    if table and name in table[3]:
        rows = table[3]
        del rows[name]
        write_readme_table(table, rows)
        removed.append(f"{README_FILE} plugin table")

    if not removed:
        die(f"No plugin named {name} in this marketplace")

    print(f"== {name}: removed ==")
    for where in removed:
        print(f"   {where}")

    # Prose elsewhere (e.g. "X is Claude-only") is left for a human to edit.
    for doc in (README_FILE, "AGENTS.md"):
        if not os.path.isfile(doc):
            continue
        with open(doc, encoding="utf-8") as f:
            hits = [
                i for i, line in enumerate(f, 1)
                if re.search(rf"(?<![\w-]){re.escape(name)}(?![\w-])", line)
            ]
        if hits:
            print(f"   note: {doc} still mentions {name} on line(s) "
                  f"{', '.join(map(str, hits))}")
    print()
    print_review_hint(f"Removed {name}")


# --- entry point ----------------------------------------------------------

def print_review_hint(what):
    files = f"{CLAUDE_FILE} {CODEX_FILE} {README_FILE}".replace(os.sep, "/")
    print(f"{what} in the working tree, not committed.")
    print(f"Review with: git diff -- {files}")
    print(f"Commit with: git add {files} && git commit")


def main():
    parser = argparse.ArgumentParser(
        prog="ai-plugins.py", description=__doc__.split("\n")[0]
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("update", help="re-pin every remote plugin to its latest commit")

    add = sub.add_parser("add", help="add a plugin from a GitHub URL or owner/repo slug")
    add.add_argument("repo", help="GitHub URL or owner/repo slug")
    add.add_argument("--path", help="subdirectory to search for the plugin manifest")
    add.add_argument("--description", help="override the plugin.json description")

    remove = sub.add_parser("remove", help="remove a plugin by name")
    remove.add_argument("name")

    args = parser.parse_args()

    try:
        os.chdir(git("rev-parse", "--show-toplevel"))
    except (RuntimeError, FileNotFoundError):
        die("Run this from inside the ai-plugins git repo (git must be on PATH)")
    if not os.path.isfile(CLAUDE_FILE):
        die(f"No {CLAUDE_FILE} found in {os.getcwd()}")

    {"update": cmd_update, "add": cmd_add, "remove": cmd_remove}[args.command](args)


if __name__ == "__main__":
    main()

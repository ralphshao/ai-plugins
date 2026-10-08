#!/usr/bin/env python3
"""Maintain the ai-plugins marketplace: update, add, and remove pinned plugins.

Edits .claude-plugin/marketplace.json, .agents/plugins/marketplace.json, and
README.md's plugin table in the working tree of the repo containing the
current directory. Never commits. Standard library only; needs `git` on PATH.
"""

import argparse
import json
import os
import posixpath
import re
import shutil
import signal
import subprocess
import sys
import tempfile
from typing import NoReturn

SELF = "ai-plugins"
CLAUDE_FILE = os.path.join(".claude-plugin", "marketplace.json")
CODEX_FILE = os.path.join(".agents", "plugins", "marketplace.json")
README_FILE = "README.md"
REMOTE_SOURCES = ("url", "git-subdir")
DEFAULT_CATEGORY = "Productivity"
GIT_TIMEOUT = 120  # seconds, per git call

# README plugin table row: "| <name cell> | <description> | <version> |"
ROW_RE = re.compile(r"^\| (?P<name>[^|]+?) \| (?P<desc>.*) \| (?P<version>[^|]*?) \|$")
ROW_NAME_RE = re.compile(r"\[`?([^`\]]+)`?\]")
RELEASE_TAG_RE = re.compile(r"^v?(\d+(?:\.\d+)+)$")


def die(msg) -> NoReturn:
    print(msg, file=sys.stderr)
    sys.exit(1)


def git(*args, cwd=None):
    # A private or mistyped repo URL must fail, not hang on a credential
    # prompt: git's own, or Git Credential Manager's GUI (Git for Windows).
    # start_new_session (POSIX) puts git and its helpers in one process group
    # that kill_tree can end together.
    proc = subprocess.Popen(
        ["git", *args], cwd=cwd, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "never"},
        start_new_session=True,
    )
    try:
        out, err = proc.communicate(timeout=GIT_TIMEOUT)
    except subprocess.TimeoutExpired:
        kill_tree(proc)
        proc.communicate()
        raise RuntimeError(f"git {args[0]} timed out after {GIT_TIMEOUT}s")
    if proc.returncode != 0:
        raise RuntimeError(err.strip() or f"git {args[0]} failed")
    return out.strip()


def kill_tree(proc):
    """Kill proc and its children.

    Killing only git leaves git-remote-https (and any credential helper)
    running. Those still hold git's output pipes, so on Windows the
    communicate() after the kill would wait on them forever.
    """
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                           capture_output=True)
        else:
            os.killpg(proc.pid, signal.SIGKILL)
    except OSError:
        pass  # Already gone; the kill below is a no-op then too.
    proc.kill()


def sort_key(plugin_name, local=False):
    # ai-plugins first, then the other local plugins, then remote ones; each
    # group alphabetical.
    return (plugin_name != SELF, not local, plugin_name.lower())


def is_local(entry):
    """True for a plugin whose source lives in this repo.

    Claude's catalog uses a relative-path string; Codex's uses
    {"source": "local", "path": ...}.
    """
    source = entry.get("source")
    return isinstance(source, str) or (
        isinstance(source, dict) and source.get("source") == "local")


def local_names(*catalogs):
    return {p["name"] for data in catalogs if data for p in data["plugins"]
            if is_local(p)}


# --- JSON catalogs --------------------------------------------------------

def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_file(path, text):
    """Write via a temp file and rename, so a crash never leaves it half-written."""
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        # Covers encode errors and Ctrl-C too; keep the original error.
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def save_catalog(path, data):
    data["plugins"].sort(key=lambda p: sort_key(p["name"], is_local(p)))
    write_file(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def find_plugin(data, name):
    return next((p for p in data["plugins"] if p["name"] == name), None)


# --- README table ---------------------------------------------------------

def read_readme_table():
    """Return (lines, start, end, rows) where rows maps name -> row line.

    start..end is the slice of body rows (after the header and separator).
    Returns None if README.md or its plugin table is missing. Exits on a row
    with no [name] link or a duplicate name: rewriting would drop it.
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
        if not m:
            die(f"Can't find the plugin name in this {README_FILE} table row:\n{line}")
        if m.group(1) in rows:
            die(f"{README_FILE} plugin table lists {m.group(1)} more than once")
        rows[m.group(1)] = line
    return lines, start, end, rows


def write_readme_table(table, rows, local):
    lines, start, end, _ = table
    body = [rows[name] for name in sorted(rows, key=lambda n: sort_key(n, n in local))]
    lines[start:end] = body
    write_file(README_FILE, "\n".join(lines))


def readme_row(name, link, description, version):
    description = description.replace("|", "\\|")
    return f"| [{name}]({link}) | {description} | {version} |"


def set_row_version(row, version):
    m = ROW_RE.match(row)
    if not m:
        # Returning the row unchanged would leave README behind the catalog.
        die(f"Can't parse this {README_FILE} table row to update its version:\n{row}")
    return f"| {m.group('name')} | {m.group('desc')} | {version} |"


# --- Git helpers ----------------------------------------------------------

def fetch_commit(url, ref):
    """Shallow-fetch one commit/ref into a temp dir checked out at FETCH_HEAD.

    Returns the temp dir path; caller must remove it. On failure, removes it
    and raises RuntimeError with git's error.
    """
    tmp = tempfile.mkdtemp(prefix="ai-plugins-")
    try:
        git("init", "-q", cwd=tmp)
        git("fetch", "-q", "--depth", "1", url, ref, cwd=tmp)
        git("checkout", "-q", "FETCH_HEAD", cwd=tmp)
        return tmp
    except RuntimeError:
        rmtree(tmp)
        raise


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
    """Return the commit sha that ref names on url, or "" if there is none.

    A bare ref is matched exactly as a tag or a branch, tag first like git
    does; a full one (refs/heads/x) is matched as given.
    ls-remote alone matches on suffix (main also hits feature/main) and gives
    an annotated tag's own sha, not its commit's.
    """
    if not ref or ref == "HEAD":
        out = git("ls-remote", url, "HEAD")
        return out.split("\t", 1)[0] if out else ""
    if ref.startswith("refs/"):
        wanted = [f"{ref}^{{}}", ref]
    else:
        wanted = [f"refs/tags/{ref}^{{}}", f"refs/tags/{ref}", f"refs/heads/{ref}"]
    found = {}
    for line in git("ls-remote", url, *wanted).splitlines():
        sha, name = line.split("\t", 1)
        found[name] = sha
    return next((found[n] for n in wanted if n in found), "")


def latest_release(url):
    """Return (tag, commit sha) of the highest release tag, or None.

    Release tags look like v1.2.3 or 1.2; pre-release tags (v1.2.3-beta) and
    other names are ignored.
    """
    # ponytail: tags stand in for GitHub releases (no API call, works offline);
    # a tagged commit with no published release still counts.
    shas = {}
    for line in git("ls-remote", "--tags", url).splitlines():
        sha, ref = line.split("\t", 1)
        tag = ref[len("refs/tags/"):]
        peeled = tag.endswith("^{}")  # annotated tag: this line has the commit
        tag = tag[:-3] if peeled else tag
        if RELEASE_TAG_RE.match(tag) and (peeled or tag not in shas):
            shas[tag] = sha
    if not shas:
        return None
    tag = max(shas, key=lambda t: tuple(
        int(n) for n in RELEASE_TAG_RE.match(t).group(1).split(".")))
    return tag, shas[tag]


def default_branch(url):
    for line in git("ls-remote", "--symref", url, "HEAD").splitlines():
        if line.startswith("ref: refs/heads/"):
            return line[len("ref: refs/heads/"):].split("\t", 1)[0]
    return None


def resolve_pin(url, ref, follow_releases=False):
    """Return (sha, ref, label) for what to pin.

    With no ref, the latest release tag wins, falling back to the default
    branch when the repo has no release tags. An explicit ref is followed
    as-is, unless follow_releases is set and it is a release tag or the
    default branch: then it is re-resolved as if there were no ref.
    """
    if ref and follow_releases and (
            RELEASE_TAG_RE.match(ref) or ref == default_branch(url)):
        ref = None
    if ref:
        return latest_sha(url, ref), ref, f"ref {ref}"
    release = latest_release(url)
    if release:
        return release[1], release[0], f"release {release[0]}"
    branch = default_branch(url)
    return latest_sha(url, branch), branch, "default branch"


def set_pin(source, sha, ref):
    """Set sha and ref in place, keeping ref right after sha."""
    items = [(k, v) for k, v in source.items() if k not in ("sha", "ref")]
    source.clear()
    source.update(items)
    source["sha"] = sha
    if ref:
        source["ref"] = ref


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
    rows = table[3] if table is not None else {}

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
        url = source["url"]
        old_sha = source.get("sha", "")
        subdir = source.get("path", ".") if source["source"] == "git-subdir" else "."

        unresolved = f"== {name}: could not resolve latest ref from {url} =="
        try:
            new_sha, new_ref, label = resolve_pin(
                url, source.get("ref"), follow_releases=True)
        except RuntimeError as e:
            # Timeout, auth failure, bad URL...: say which.
            print(f"{unresolved}\n   {e}\n")
            continue
        if not new_sha:
            print(f"{unresolved}\n")  # The ref isn't there; git had no error.
            continue

        codex_plugin = find_plugin(codex, name) if codex is not None else None
        codex_source = codex_plugin.get("source") if codex_plugin is not None else None
        pins = [(CLAUDE_FILE, source)]
        if isinstance(codex_source, dict):
            pins.append((CODEX_FILE, codex_source))

        if old_sha == new_sha:
            print(f"== {name}: up to date ==")
            print(f"   {old_sha[:12]} ({label})")
            # The Codex pin can drift from the Claude one after a hand edit,
            # so report each file's sha and ref separately.
            stale = False
            for path, s in pins:
                path = path.replace(os.sep, "/")
                if s.get("sha") != new_sha:
                    stale = True
                    print(f"   {path} sha: "
                          f"{(s.get('sha') or '(none)')[:12]} -> {new_sha[:12]}")
                if s.get("ref") != new_ref:
                    stale = True
                    print(f"   {path} ref: {s.get('ref') or '(none)'} -> {new_ref}")
            if stale:
                for _, s in pins:
                    set_pin(s, new_sha, new_ref)
            print()
            continue

        try:
            old_clone = fetch_commit(url, old_sha) if old_sha else None
        except RuntimeError:
            old_clone = None  # e.g. force-pushed away: no subject to show
        old_subject = commit_subject(old_clone)
        rmtree(old_clone)

        try:
            new_clone, fetch_error = fetch_commit(url, new_sha), ""
        except RuntimeError as e:
            new_clone, fetch_error = None, str(e)
        new_subject = commit_subject(new_clone)
        manifest = (
            read_manifest(new_clone, subdir, "claude")
            or read_manifest(new_clone, subdir, "codex")
        ) if new_clone else None
        rmtree(new_clone)
        new_version = (manifest or {}).get("version", "")
        old_version = plugin.get("version", "")

        print(f"== {name}: updated ==")
        print(f"   before: {old_sha[:12]} {old_subject}")
        print(f"   after:  {new_sha[:12]} {new_subject} ({label})")
        if manifest is None:
            # Still pin, but say why the version didn't move.
            why = (f"could not fetch {new_sha[:12]}: {fetch_error}" if fetch_error
                   else f"no plugin.json at {new_sha[:12]}")
            print(f"   note: version left at {old_version or '(none)'} ({why})")

        for _, s in pins:
            set_pin(s, new_sha, new_ref)

        if new_version and new_version != old_version:
            print(f"   version: {old_version} -> {new_version}")
            plugin["version"] = new_version
            if name in rows:
                rows[name] = set_row_version(rows[name], new_version)
        print()

    save_catalog(CLAUDE_FILE, claude)
    if codex is not None:
        save_catalog(CODEX_FILE, codex)
    if table is not None:
        write_readme_table(table, rows, local_names(claude, codex))
    print_review_hint("Pinned refs (and versions, where changed) updated")


# --- add ------------------------------------------------------------------

def parse_repo(spec):
    """Turn a GitHub slug or URL into (clone_url, web_url, ref, path_hint).

    A /tree/ link is split at its first slash, so a ref with a slash in it
    (feature/x) reads as ref "feature", path "x". Pass the slug and --path
    for those.
    """
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
        # "", ".", and "./" all mean the repo root.
        hint = posixpath.normpath(path_hint.replace("\\", "/") or ".").strip("/")
        hint = "" if hint == "." else hint
        dirs = [d for d in dirs if d == hint or d.startswith(hint + "/")]
    if len(dirs) > 1:
        listing = "\n".join(f"  {d or '.'}" for d in dirs)
        die(
            f"Found several .{kind}-plugin/plugin.json manifests:\n{listing}\n"
            "Re-run with --path <dir> to pick one."
        )
    return dirs[0] if dirs else None


def make_source(url, sha, ref, subdir, codex_style=False):
    if not subdir:
        source = {"source": "url", "url": url}
    else:
        path = f"./{subdir}" if codex_style else subdir
        source = {"source": "git-subdir", "url": url, "path": path}
    set_pin(source, sha, ref)
    return source


def cmd_add(args):
    clone_url, web_url, ref, path_hint = parse_repo(args.repo)
    if args.path is not None:
        path_hint = args.path

    try:
        sha, ref, label = resolve_pin(clone_url, ref)
    except RuntimeError as e:
        die(f"Could not reach {clone_url}: {e}")
    if not sha:
        die(f"Could not resolve {ref or 'HEAD'} on {clone_url}")

    try:
        clone = fetch_commit(clone_url, sha)
    except RuntimeError as e:
        die(f"Could not fetch {sha[:12]} from {clone_url}: {e}")
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

    if claude_manifest is None and codex_manifest is None:
        die(
            f"No .claude-plugin/plugin.json or .codex-plugin/plugin.json found in "
            f"{web_url}{' under ' + path_hint if path_hint else ''}"
        )

    # Each catalog uses its own manifest's folder as the plugin root, falling
    # back to the other one: Claude Code and Codex both load either layout.
    claude_note = codex_note = ""
    if claude_manifest is None:
        claude_dir, claude_manifest = codex_dir, codex_manifest
        claude_note = " (no .claude-plugin/plugin.json, using Codex plugin root)"
    if codex_manifest is None:
        codex_dir, codex_manifest = claude_dir, claude_manifest
        codex_note = " (no .codex-plugin/plugin.json, using Claude plugin root)"

    name = claude_manifest.get("name") or web_url.rsplit("/", 1)[-1]
    description = args.description or claude_manifest.get("description", "")
    version = claude_manifest.get("version", "")

    claude = load_json(CLAUDE_FILE)
    codex = load_json(CODEX_FILE) if os.path.isfile(CODEX_FILE) else None
    table = read_readme_table()
    if any(c is not None and find_plugin(c, name) is not None for c in (claude, codex)):
        die(f"A plugin named {name} is already in this marketplace")

    print(f"== {name}: adding ==")
    print(f"   repo:   {web_url}")
    print(f"   commit: {sha[:12]} {subject} ({label})")
    if version:
        print(f"   version: {version}")

    entry = {
        "name": name,
        "source": make_source(clone_url, sha, ref, claude_dir),
        "description": description,
    }
    if version:
        entry["version"] = version
    if claude_manifest.get("author"):
        entry["author"] = claude_manifest["author"]
    claude["plugins"].append(entry)
    print(f"   claude: {'./' + claude_dir if claude_dir else 'repo root'}{claude_note}")

    if codex is not None:
        category = (codex_manifest.get("interface") or {}).get("category")
        codex["plugins"].append({
            "name": name,
            "source": make_source(clone_url, sha, ref, codex_dir, codex_style=True),
            "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
            "category": category or DEFAULT_CATEGORY,
        })
        print(f"   codex:  {'./' + codex_dir if codex_dir else 'repo root'}{codex_note}")

    save_catalog(CLAUDE_FILE, claude)
    if codex is not None:
        save_catalog(CODEX_FILE, codex)
    if table is not None:
        rows = table[3]
        link = f"{web_url}/tree/HEAD/{claude_dir}" if claude_dir else web_url
        rows[name] = readme_row(name, link, description, version or "—")
        write_readme_table(table, rows, local_names(claude, codex))
    print()
    print_review_hint(f"Added {name}")


# --- remove ---------------------------------------------------------------

def cmd_remove(args):
    name = args.name
    if name == SELF:
        die(f"Refusing to remove {SELF} itself")

    catalogs = [(path, load_json(path)) for path in (CLAUDE_FILE, CODEX_FILE)
                if os.path.isfile(path)]
    table = read_readme_table()

    # Edit everything in memory first, so a malformed catalog fails before
    # any file is written.
    removed = []
    for path, data in catalogs:
        if find_plugin(data, name) is not None:
            data["plugins"] = [p for p in data["plugins"] if p["name"] != name]
            removed.append(path)
    rows = table[3] if table is not None else {}
    in_table = name in rows
    if in_table:
        del rows[name]

    for path, data in catalogs:
        if path in removed:
            save_catalog(path, data)
    if in_table:
        write_readme_table(table, rows, local_names(*(data for _, data in catalogs)))
        removed.append(f"{README_FILE} plugin table")

    if not removed:
        die(f"No plugin named {name} in this marketplace")

    print(f"== {name}: removed ==")
    for where in removed:
        print(f"   {where.replace(os.sep, '/')}")

    # Prose elsewhere (e.g. the path quirks in AGENTS.md) is left for a human to edit.
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

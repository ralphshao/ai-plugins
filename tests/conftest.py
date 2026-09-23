"""Shared fixtures for the ai-plugins maintenance script tests.

Every test runs offline. Upstream plugin repos are throwaway local git repos,
and a private global git config rewrites https://github.com/ to point at them,
so `owner/repo` slugs and github URLs resolve without touching the network.
"""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_ROOT = REPO_ROOT / "plugins" / "ai-plugins"
SCRIPT = PLUGIN_ROOT / "scripts" / "ai-plugins.py"
CLAUDE_FILE = Path(".claude-plugin", "marketplace.json")
CODEX_FILE = Path(".agents", "plugins", "marketplace.json")


@pytest.fixture(scope="session")
def ai_plugins():
    # The file name has a hyphen, so it can't be imported the normal way.
    spec = importlib.util.spec_from_file_location("ai_plugins", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write(path, text):
    """Write with LF endings on every OS, as the script itself does."""
    path.write_bytes(text.encode("utf-8"))


def git(*args, cwd):
    result = subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True
    )
    if result.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed:\n{result.stderr}")
    return result.stdout.strip()


# --- isolated git -----------------------------------------------------------

@pytest.fixture(autouse=True)
def git_sandbox(tmp_path_factory, monkeypatch):
    """Point git at a private config and a local stand-in for github.com."""
    base = tmp_path_factory.mktemp("git")
    remotes_root = base / "remotes"
    remotes_root.mkdir()
    gitconfig = base / "gitconfig"
    gitconfig.write_text(
        "[user]\n"
        "\tname = Test\n"
        "\temail = test@example.com\n"
        "[init]\n"
        "\tdefaultBranch = main\n"
        "[commit]\n"
        "\tgpgsign = false\n"
        "[protocol \"file\"]\n"
        "\tallow = always\n"
        f"[url \"{remotes_root.as_uri()}/\"]\n"
        "\tinsteadOf = https://github.com/\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(gitconfig))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_TERMINAL_PROMPT", "0")
    for var in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
        monkeypatch.delenv(var, raising=False)
    return remotes_root


class Remote:
    """A local git repo standing in for an upstream plugin repo."""

    def __init__(self, path, owner, repo):
        self.path = path
        self.owner = owner
        self.repo = repo
        path.mkdir(parents=True)
        git("init", "-q", cwd=path)
        # Let clients fetch any commit by SHA, like GitHub does.
        git("config", "uploadpack.allowAnySHA1InWant", "true", cwd=path)

    @property
    def slug(self):
        return f"{self.owner}/{self.repo}"

    @property
    def web_url(self):
        return f"https://github.com/{self.slug}"

    @property
    def clone_url(self):
        return f"{self.web_url}.git"

    def commit(self, files, message="update"):
        """Write files (path -> str, or dict for JSON) and commit. Returns SHA."""
        for rel, content in files.items():
            target = self.path / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(content, dict):
                content = json.dumps(content, indent=2)
            target.write_text(content, encoding="utf-8")
        git("add", "-A", cwd=self.path)
        git("commit", "-q", "--allow-empty", "-m", message, cwd=self.path)
        return self.head()

    def head(self):
        return git("rev-parse", "HEAD", cwd=self.path)

    def checkout(self, branch, create=False):
        git("checkout", "-q", *(["-b"] if create else []), branch, cwd=self.path)


def manifest(name, version="1.0.0", description=None, **extra):
    data = {"name": name, "version": version,
            "description": description or f"The {name} plugin"}
    data.update(extra)
    return data


@pytest.fixture
def make_remote(git_sandbox):
    def make(repo, owner="upstream"):
        return Remote(git_sandbox / owner / f"{repo}.git", owner, repo)
    return make


# --- marketplace repo -------------------------------------------------------

README_TEMPLATE = """\
# ai-plugins

`legacy-only` is Claude-only: it has no Codex manifest.

## Plugins

| Plugin | Description | Version |
| --- | --- | --- |
{rows}

## Repo structure

Trailing prose stays put.
"""

AGENTS_TEMPLATE = """\
# AGENTS.md

Notes about plugins live here.
"""


def table_rows(readme_text):
    """Body rows of the README plugin table, in file order."""
    lines = readme_text.split("\n")
    start = next(i for i, l in enumerate(lines) if l.startswith("| Plugin |")) + 2
    rows = []
    for line in lines[start:]:
        if not line.startswith("|"):
            break
        rows.append(line)
    return rows


class Market:
    """A throwaway git repo shaped like this marketplace."""

    def __init__(self, path):
        self.path = path
        self.claude_path = path / CLAUDE_FILE
        self.codex_path = path / CODEX_FILE
        self.readme_path = path / "README.md"

    def catalog(self, which="claude"):
        path = self.claude_path if which == "claude" else self.codex_path
        return json.loads(path.read_text(encoding="utf-8"))

    def readme(self):
        return self.readme_path.read_text(encoding="utf-8")

    def plugin(self, name, which="claude"):
        return next((p for p in self.catalog(which)["plugins"] if p["name"] == name),
                    None)

    def names(self, which="claude"):
        return [p["name"] for p in self.catalog(which)["plugins"]]

    def table_rows(self):
        return table_rows(self.readme())

    def snapshot(self):
        """Bytes of every file the script may touch, for no-change checks."""
        return {
            p: (self.path / p).read_bytes()
            for p in (CLAUDE_FILE, CODEX_FILE, Path("README.md"), Path("AGENTS.md"))
            if (self.path / p).exists()
        }

    def run(self, *args, cwd=None, check=None):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=cwd or self.path, capture_output=True, text=True,
        )
        if check is True:
            assert result.returncode == 0, result.stdout + result.stderr
        elif check is False:
            assert result.returncode != 0, result.stdout + result.stderr
        return result

    def save(self, data, which="claude"):
        path = self.claude_path if which == "claude" else self.codex_path
        write(path, json.dumps(data, indent=2) + "\n")

    def add_entry(self, entry, which="claude"):
        data = self.catalog(which)
        data["plugins"].append(entry)
        self.save(data, which)

    def add_row(self, row):
        text = self.readme()
        marker = "| --- | --- | --- |\n"
        rows_end = text.index("\n\n", text.index(marker))
        write(self.readme_path, text[:rows_end] + "\n" + row + text[rows_end:])


def codex_entry(name, source):
    return {
        "name": name,
        "source": source,
        "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
        "category": "Productivity",
    }


def pin(market, remote, sha, name=None, version="1.0.0", subdir=None, ref=None,
        codex=True, row=True, kind="url"):
    """Add a catalog entry pinned to sha, as `add` would have written it."""
    name = name or remote.repo
    if kind == "github":
        source = {"source": "github", "repo": remote.slug, "sha": sha}
    elif subdir:
        source = {"source": "git-subdir", "url": remote.clone_url, "path": subdir,
                  "sha": sha}
    else:
        source = {"source": "url", "url": remote.clone_url, "sha": sha}
    if ref:
        source["ref"] = ref
    market.add_entry({"name": name, "source": source, "description": name,
                      "version": version})
    if codex:
        codex_source = dict(source)
        if subdir:
            codex_source["path"] = f"./{subdir}"
        market.add_entry(codex_entry(name, codex_source), "codex")
    if row:
        market.add_row(f"| [{name}]({remote.web_url}) | Does {version} | {version} |")


@pytest.fixture
def market(tmp_path):
    """A marketplace repo holding only the local ai-plugins entry."""
    root = tmp_path / "market"
    (root / ".claude-plugin").mkdir(parents=True)
    (root / ".agents" / "plugins").mkdir(parents=True)
    claude = {
        "name": "ai-plugins",
        "owner": {"name": "Test"},
        "plugins": [{
            "name": "ai-plugins",
            "source": "./plugins/ai-plugins",
            "description": "Maintenance skills",
            "version": "1.0.0",
        }],
    }
    codex = {
        "name": "ai-plugins",
        "plugins": [codex_entry("ai-plugins",
                                {"source": "local", "path": "./plugins/ai-plugins"})],
    }
    write(root / CLAUDE_FILE, json.dumps(claude, indent=2) + "\n")
    write(root / CODEX_FILE, json.dumps(codex, indent=2) + "\n")
    write(root / "README.md", README_TEMPLATE.format(
        rows="| [`ai-plugins`](plugins/ai-plugins) | Maintenance skills | 1.0.0 |"))
    write(root / "AGENTS.md", AGENTS_TEMPLATE)
    git("init", "-q", cwd=root)
    git("add", "-A", cwd=root)
    git("commit", "-q", "-m", "init", cwd=root)
    return Market(root)

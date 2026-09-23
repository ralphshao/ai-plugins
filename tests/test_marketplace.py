"""Consistency checks on this repo's committed marketplace files.

These read the real catalogs and README (no network), so a hand edit that
breaks an invariant the maintenance script relies on fails here.
"""

import json
import re

import pytest

from conftest import CLAUDE_FILE, CODEX_FILE, PLUGIN_ROOT, REPO_ROOT, table_rows

REMOTE = ("url", "git-subdir")


def load(path):
    return json.loads((REPO_ROOT / path).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def claude():
    return load(CLAUDE_FILE)


@pytest.fixture(scope="module")
def codex():
    return load(CODEX_FILE)


@pytest.fixture(scope="module")
def table(ai_plugins):
    """README plugin table as {name: (version cell, row)}, in file order."""
    rows = {}
    for line in table_rows((REPO_ROOT / "README.md").read_text(encoding="utf-8")):
        m = ai_plugins.ROW_RE.match(line)
        assert m, f"malformed README row: {line}"
        name = ai_plugins.ROW_NAME_RE.search(m.group("name")).group(1)
        rows[name] = (m.group("version"), line)
    return rows


def is_remote(plugin):
    return isinstance(plugin["source"], dict) and plugin["source"].get("source") in REMOTE


@pytest.mark.parametrize("path", [CLAUDE_FILE, CODEX_FILE])
def test_catalog_is_in_canonical_script_format(ai_plugins, path, tmp_path):
    # Running the script must not reformat an untouched catalog. (Ignore CRLF
    # from a Windows checkout with core.autocrlf; git normalizes it on commit.)
    out = tmp_path / "out.json"
    ai_plugins.save_catalog(str(out), load(path))
    committed = (REPO_ROOT / path).read_bytes().replace(b"\r\n", b"\n")
    assert out.read_bytes() == committed


@pytest.mark.parametrize("path", [CLAUDE_FILE, CODEX_FILE])
def test_catalog_names_unique_and_sorted(ai_plugins, path):
    names = [p["name"] for p in load(path)["plugins"]]
    assert len(names) == len(set(names))
    assert names[0] == "ai-plugins"
    assert names == sorted(names, key=ai_plugins.sort_key)


def test_remote_sources_are_pinned(claude, codex):
    for plugin in claude["plugins"] + codex["plugins"]:
        if is_remote(plugin):
            assert re.fullmatch(r"[0-9a-f]{40}", plugin["source"].get("sha", "")), \
                f"{plugin['name']} is not pinned to a full commit SHA"


def test_codex_plugins_match_claude_pins(claude, codex):
    by_name = {p["name"]: p for p in claude["plugins"]}
    for plugin in codex["plugins"]:
        assert plugin["name"] in by_name, f"{plugin['name']} is Codex-only"
        if not is_remote(plugin):
            continue
        other = by_name[plugin["name"]]["source"]
        assert plugin["source"]["url"] == other["url"], plugin["name"]
        assert plugin["source"]["sha"] == other["sha"], plugin["name"]


def test_codex_entries_have_policy_and_category(codex):
    for plugin in codex["plugins"]:
        assert plugin["policy"] == {"installation": "AVAILABLE",
                                    "authentication": "ON_INSTALL"}, plugin["name"]
        assert plugin.get("category"), plugin["name"]


def test_readme_table_lists_every_plugin_in_order(ai_plugins, claude, codex, table):
    names = {p["name"] for p in claude["plugins"] + codex["plugins"]}
    assert list(table) == sorted(names, key=ai_plugins.sort_key)


def test_readme_versions_match_claude_catalog(claude, table):
    for plugin in claude["plugins"]:
        assert table[plugin["name"]][0] == plugin.get("version", "—"), plugin["name"]


def test_claude_only_plugins_are_called_out_in_readme(claude, codex):
    codex_names = {p["name"] for p in codex["plugins"]}
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    prose = "\n".join(l for l in readme.split("\n") if not l.startswith("|"))
    for plugin in claude["plugins"]:
        if plugin["name"] not in codex_names:
            assert f"`{plugin['name']}` is Claude-only" in prose


def test_self_plugin_versions_agree(claude):
    entry = next(p for p in claude["plugins"] if p["name"] == "ai-plugins")
    for kind in ("claude", "codex"):
        manifest = json.loads(
            (PLUGIN_ROOT / f".{kind}-plugin" / "plugin.json").read_text(encoding="utf-8"))
        assert manifest["name"] == "ai-plugins"
        assert manifest["version"] == entry["version"], f".{kind}-plugin/plugin.json"


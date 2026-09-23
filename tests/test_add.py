"""End-to-end tests for `ai-plugins.py add`, against local fake upstreams."""

import json

import pytest

from conftest import manifest, write

CLAUDE = ".claude-plugin/plugin.json"
CODEX = ".codex-plugin/plugin.json"
AUTHOR = {"name": "Jane Dev", "url": "https://example.com"}


@pytest.fixture
def both_at_root(make_remote):
    remote = make_remote("widget")
    remote.commit({
        CLAUDE: manifest("widget", "2.1.0", "Does widget things", author=AUTHOR),
        CODEX: manifest("widget", "2.1.0", interface={"category": "Coding"}),
    }, "Release 2.1.0")
    return remote


def test_add_root_manifests(market, both_at_root):
    remote = both_at_root
    result = market.run("add", remote.slug, check=True)
    sha = remote.head()

    assert market.claude_plugin("widget") == {
        "name": "widget",
        "source": {"source": "url", "url": remote.clone_url, "sha": sha},
        "description": "Does widget things",
        "version": "2.1.0",
        "author": AUTHOR,
    }
    assert market.codex_plugin("widget") == {
        "name": "widget",
        "source": {"source": "url", "url": remote.clone_url, "sha": sha},
        "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
        "category": "Coding",
    }
    assert market.table_rows()[-1] == \
        f"| [widget]({remote.web_url}) | Does widget things | 2.1.0 |"

    out = result.stdout
    assert "== widget: adding ==" in out
    assert f"repo:   {remote.web_url}" in out
    assert f"commit: {sha[:12]} Release 2.1.0" in out
    assert "claude: repo root" in out and "codex:  repo root" in out
    assert "not committed" in out


@pytest.mark.parametrize("spec", [
    "{slug}", "{web}", "{web}.git", "{web}/", "git@github.com:{slug}.git",
])
def test_add_accepts_url_forms(market, both_at_root, spec):
    remote = both_at_root
    market.run("add", spec.format(slug=remote.slug, web=remote.web_url), check=True)
    assert market.claude_plugin("widget")["source"]["url"] == remote.clone_url


def test_add_non_github_url(market, make_remote):
    remote = make_remote("elsewhere")
    remote.commit({CLAUDE: manifest("elsewhere")})
    # A file:// URL takes the non-GitHub branch of parse_repo.
    spec = remote.path.as_uri()[: -len(".git")]
    market.run("add", spec, check=True)
    assert market.claude_plugin("elsewhere")["source"]["url"] == remote.path.as_uri()


def test_add_claude_root_codex_nested(market, make_remote):
    # caveman's layout.
    remote = make_remote("caveman")
    remote.commit({
        CLAUDE: manifest("caveman"),
        f"plugins/caveman/{CODEX}": manifest("caveman"),
    })
    result = market.run("add", remote.slug, check=True)
    assert market.claude_plugin("caveman")["source"] == {
        "source": "url", "url": remote.clone_url, "sha": remote.head(),
    }
    assert market.codex_plugin("caveman")["source"] == {
        "source": "git-subdir", "url": remote.clone_url,
        "path": "./plugins/caveman", "sha": remote.head(),
    }
    assert market.codex_plugin("caveman")["category"] == "Productivity"
    assert "codex:  ./plugins/caveman" in result.stdout


def test_add_codex_root_claude_nested(market, make_remote):
    # avoid-ai-writing's layout.
    remote = make_remote("avoid")
    remote.commit({
        CODEX: manifest("avoid"),
        f"plugins/avoid/{CLAUDE}": manifest("avoid"),
    })
    result = market.run("add", remote.slug, check=True)
    assert market.claude_plugin("avoid")["source"] == {
        "source": "git-subdir", "url": remote.clone_url,
        "path": "plugins/avoid", "sha": remote.head(),
    }
    assert market.codex_plugin("avoid")["source"]["source"] == "url"
    assert market.table_rows()[-1].startswith(
        f"| [avoid]({remote.web_url}/tree/HEAD/plugins/avoid) |")
    assert "claude: ./plugins/avoid" in result.stdout


def test_add_claude_only(market, make_remote):
    remote = make_remote("solo")
    remote.commit({CLAUDE: manifest("solo")})
    result = market.run("add", remote.slug, check=True)
    assert market.claude_plugin("solo") is not None
    assert market.codex_plugin("solo") is None
    assert "Claude-only" in result.stdout


def test_add_codex_only(market, make_remote):
    remote = make_remote("cdx")
    remote.commit({CODEX: manifest("cdx", description="Codex thing")})
    result = market.run("add", remote.slug, check=True)
    assert market.claude_plugin("cdx") is None
    assert market.codex_plugin("cdx") is not None
    assert "claude: no .claude-plugin/plugin.json, skipped" in result.stdout
    assert market.table_rows()[-1] == f"| [cdx]({remote.web_url}) | Codex thing | 1.0.0 |"


def test_add_without_codex_catalog(market, both_at_root):
    market.codex_path.unlink()
    market.run("add", both_at_root.slug, check=True)
    assert market.claude_plugin("widget") is not None
    assert not market.codex_path.exists()


def test_add_several_manifests_fails_then_path_picks(market, make_remote):
    remote = make_remote("multi")
    remote.commit({
        f"plugins/one/{CLAUDE}": manifest("one"),
        f"plugins/two/{CLAUDE}": manifest("two"),
    })
    before = market.snapshot()
    result = market.run("add", remote.slug, check=False)
    assert "Found several .claude-plugin/plugin.json manifests" in result.stderr
    assert "plugins/one" in result.stderr and "plugins/two" in result.stderr
    assert market.snapshot() == before

    market.run("add", remote.slug, "--path", "plugins/two", check=True)
    assert market.claude_plugin("two")["source"]["path"] == "plugins/two"
    assert market.claude_plugin("one") is None


def test_add_tree_link_pins_ref_and_path(market, make_remote):
    remote = make_remote("branchy")
    main_sha = remote.commit({f"plugins/a/{CLAUDE}": manifest("a", "1.0.0"),
                              f"plugins/b/{CLAUDE}": manifest("b")})
    remote.checkout("next", create=True)
    next_sha = remote.commit({f"plugins/a/{CLAUDE}": manifest("a", "2.0.0-beta")})
    remote.checkout("main")

    market.run("add", f"{remote.web_url}/tree/next/plugins/a", check=True)
    entry = market.claude_plugin("a")
    assert entry["source"] == {
        "source": "git-subdir", "url": remote.clone_url, "path": "plugins/a",
        "sha": next_sha, "ref": "next",
    }
    assert entry["source"]["sha"] != main_sha
    assert entry["version"] == "2.0.0-beta"


def test_add_path_flag_overrides_tree_link_path(market, make_remote):
    remote = make_remote("multi")
    remote.commit({
        f"plugins/one/{CLAUDE}": manifest("one"),
        f"plugins/two/{CLAUDE}": manifest("two"),
    })
    market.run("add", f"{remote.web_url}/tree/main/plugins/one",
               "--path", "plugins/two", check=True)
    assert market.names() == ["ai-plugins", "two"]


def test_add_description_override(market, both_at_root):
    market.run("add", both_at_root.slug, "--description", "Short | sweet", check=True)
    assert market.claude_plugin("widget")["description"] == "Short | sweet"
    assert "| Short \\| sweet |" in market.table_rows()[-1]


def test_add_without_version_or_author(market, make_remote):
    remote = make_remote("bare")
    remote.commit({CLAUDE: {"name": "bare", "description": "Bare"}})
    result = market.run("add", remote.slug, check=True)
    entry = market.claude_plugin("bare")
    assert "version" not in entry and "author" not in entry
    assert market.table_rows()[-1].endswith("| Bare | — |")
    assert "version:" not in result.stdout


def test_add_falls_back_to_repo_name(market, make_remote):
    remote = make_remote("nameless")
    remote.commit({CLAUDE: {"description": "No name field"}})
    market.run("add", remote.slug, check=True)
    assert market.claude_plugin("nameless") is not None


def test_add_keeps_lists_sorted(market, make_remote):
    for repo in ("zulu", "Alpha", "mike"):
        remote = make_remote(repo)
        remote.commit({CLAUDE: manifest(repo), CODEX: manifest(repo)})
        market.run("add", remote.slug, check=True)
    expected = ["ai-plugins", "Alpha", "mike", "zulu"]
    assert market.names() == expected
    assert market.names("codex") == expected
    assert [r.split("](")[0].strip("| [`") for r in market.table_rows()] == expected


@pytest.mark.parametrize("where", ["claude", "codex"])
def test_add_duplicate_name_fails_without_edits(market, both_at_root, where):
    market.run("add", both_at_root.slug, check=True)
    if where == "codex":
        # Only the Codex catalog still has it.
        data = market.claude()
        data["plugins"] = [p for p in data["plugins"] if p["name"] != "widget"]
        write(market.claude_path, json.dumps(data, indent=2) + "\n")
    before = market.snapshot()
    result = market.run("add", both_at_root.slug, check=False)
    assert "A plugin named widget is already in this marketplace" in result.stderr
    assert market.snapshot() == before


def test_add_no_manifest_fails_without_edits(market, make_remote):
    remote = make_remote("empty")
    remote.commit({"README.md": "nothing here"})
    before = market.snapshot()
    result = market.run("add", remote.slug, check=False)
    assert "No .claude-plugin/plugin.json or .codex-plugin/plugin.json found" \
        in result.stderr
    assert market.snapshot() == before


def test_add_path_with_no_match_fails(market, both_at_root):
    result = market.run("add", both_at_root.slug, "--path", "nowhere", check=False)
    assert "under nowhere" in result.stderr


def test_add_unreachable_repo_fails_without_edits(market):
    before = market.snapshot()
    result = market.run("add", "ghost/missing", check=False)
    assert result.returncode == 1
    assert "https://github.com/ghost/missing.git" in result.stderr
    assert market.snapshot() == before


def test_add_unknown_ref_fails(market, both_at_root):
    result = market.run("add", f"{both_at_root.web_url}/tree/no-such-branch",
                        check=False)
    assert "Could not resolve no-such-branch" in result.stderr


def test_add_from_subdirectory_of_repo(market, both_at_root):
    sub = market.path / "plugins" / "deep"
    sub.mkdir(parents=True)
    market.run("add", both_at_root.slug, cwd=sub, check=True)
    assert market.claude_plugin("widget") is not None

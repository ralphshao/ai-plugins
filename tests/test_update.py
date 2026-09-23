"""End-to-end tests for `ai-plugins.py update`, against local fake upstreams."""

import pytest

from conftest import codex_entry, manifest

CLAUDE = ".claude-plugin/plugin.json"


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
    market.add_claude({"name": name, "source": source, "description": name,
                       "version": version})
    if codex:
        codex_source = dict(source)
        if subdir:
            codex_source["path"] = f"./{subdir}"
        market.add_codex(codex_entry(name, codex_source))
    if row:
        market.add_row(f"| [{name}]({remote.web_url}) | Does {version} | {version} |")


def test_update_nothing_remote(market):
    before = market.snapshot()
    result = market.run("update", check=True)
    assert "No remote-ref plugins found" in result.stdout
    assert market.snapshot() == before


def test_update_up_to_date_leaves_files_byte_identical(market, make_remote):
    remote = make_remote("steady")
    sha = remote.commit({CLAUDE: manifest("steady")}, "Initial release")
    pin(market, remote, sha)
    before = market.snapshot()

    result = market.run("update", check=True)
    assert "== steady: up to date ==" in result.stdout
    assert f"{sha[:12]} Initial release" in result.stdout
    assert market.snapshot() == before


def test_update_moves_sha_in_both_catalogs(market, make_remote):
    remote = make_remote("mover")
    old = remote.commit({CLAUDE: manifest("mover")}, "Old commit")
    new = remote.commit({"CHANGELOG": "x"}, "New commit")
    pin(market, remote, old)

    result = market.run("update", check=True)
    assert market.claude_plugin("mover")["source"]["sha"] == new
    assert market.codex_plugin("mover")["source"]["sha"] == new
    assert "== mover: updated ==" in result.stdout
    assert f"before: {old[:12]} Old commit" in result.stdout
    assert f"after:  {new[:12]} New commit" in result.stdout
    # Same version: no version line, README row untouched.
    assert "version:" not in result.stdout
    assert market.claude_plugin("mover")["version"] == "1.0.0"
    assert market.table_rows()[-1].endswith("| Does 1.0.0 | 1.0.0 |")


def test_update_bumps_version_and_readme_row(market, make_remote):
    remote = make_remote("bumpy")
    old = remote.commit({CLAUDE: manifest("bumpy", "1.0.0")})
    remote.commit({CLAUDE: manifest("bumpy", "1.1.0")}, "Release 1.1.0")
    pin(market, remote, old)

    result = market.run("update", check=True)
    assert "version: 1.0.0 -> 1.1.0" in result.stdout
    assert market.claude_plugin("bumpy")["version"] == "1.1.0"
    # Only the version cell changes, even though the description mentions 1.0.0.
    assert market.table_rows()[-1] == f"| [bumpy]({remote.web_url}) | Does 1.0.0 | 1.1.0 |"
    # The Codex catalog has no version field to bump.
    assert "version" not in market.codex_plugin("bumpy")


def test_update_git_subdir_reads_version_from_path(market, make_remote):
    remote = make_remote("mono")
    old = remote.commit({
        CLAUDE: manifest("root-thing", "9.9.9"),
        f"plugins/inner/{CLAUDE}": manifest("inner", "1.0.0"),
    })
    remote.commit({f"plugins/inner/{CLAUDE}": manifest("inner", "2.0.0")})
    pin(market, remote, old, name="inner", subdir="plugins/inner")

    market.run("update", check=True)
    entry = market.claude_plugin("inner")
    assert entry["version"] == "2.0.0"
    assert entry["source"]["path"] == "plugins/inner"
    assert market.codex_plugin("inner")["source"]["path"] == "./plugins/inner"


def test_update_follows_pinned_ref_not_default_branch(market, make_remote):
    remote = make_remote("tracked")
    base = remote.commit({CLAUDE: manifest("tracked")})
    remote.checkout("stable", create=True)
    stable = remote.commit({"s": "1"}, "Stable fix")
    remote.checkout("main")
    remote.commit({"m": "1"}, "Main work")
    pin(market, remote, base, ref="stable")

    market.run("update", check=True)
    source = market.claude_plugin("tracked")["source"]
    assert source["sha"] == stable
    assert source["ref"] == "stable"


def test_update_github_source(market, make_remote):
    remote = make_remote("gh")
    old = remote.commit({CLAUDE: manifest("gh")})
    new = remote.commit({"x": "1"})
    pin(market, remote, old, kind="github", codex=False)

    market.run("update", check=True)
    assert market.claude_plugin("gh")["source"] == {
        "source": "github", "repo": remote.slug, "sha": new,
    }


def test_update_skips_local_plugins(market, make_remote):
    remote = make_remote("remote-one")
    sha = remote.commit({CLAUDE: manifest("remote-one")})
    pin(market, remote, sha)
    result = market.run("update", check=True)
    assert "ai-plugins" not in result.stdout.split("in the working tree")[0]


def test_update_claude_only_plugin(market, make_remote):
    remote = make_remote("solo")
    old = remote.commit({CLAUDE: manifest("solo")})
    new = remote.commit({"x": "1"})
    pin(market, remote, old, codex=False)
    market.run("update", check=True)
    assert market.claude_plugin("solo")["source"]["sha"] == new
    assert market.codex_plugin("solo") is None


def test_update_without_readme_row_or_codex_catalog(market, make_remote):
    remote = make_remote("lean")
    old = remote.commit({CLAUDE: manifest("lean", "1.0.0")})
    remote.commit({CLAUDE: manifest("lean", "2.0.0")})
    pin(market, remote, old, row=False)
    market.codex_path.unlink()

    market.run("update", check=True)
    assert market.claude_plugin("lean")["version"] == "2.0.0"
    assert not any("[lean]" in r for r in market.table_rows())


def test_update_missing_manifest_keeps_version(market, make_remote):
    remote = make_remote("gone")
    old = remote.commit({CLAUDE: manifest("gone", "1.0.0")})
    (remote.path / ".claude-plugin" / "plugin.json").unlink()
    new = remote.commit({}, "Drop manifest")
    pin(market, remote, old)

    market.run("update", check=True)
    entry = market.claude_plugin("gone")
    assert entry["source"]["sha"] == new
    assert entry["version"] == "1.0.0"


def test_update_unreachable_plugin_does_not_block_others(market, make_remote):
    good = make_remote("good")
    old = good.commit({CLAUDE: manifest("good")})
    new = good.commit({"x": "1"})
    pin(market, good, old)
    ghost = make_remote("ghost")
    ghost_sha = ghost.commit({CLAUDE: manifest("ghost")})
    pin(market, ghost, ghost_sha)
    # Move the upstream away after pinning it (rename, since Windows can't
    # plain-delete read-only .git objects).
    ghost.path.rename(ghost.path.with_name("moved-away"))

    result = market.run("update", check=True)
    assert f"== ghost: could not resolve latest ref from {ghost.clone_url} ==" \
        in result.stdout
    assert market.claude_plugin("ghost")["source"]["sha"] == ghost_sha
    assert market.claude_plugin("good")["source"]["sha"] == new


def test_update_unknown_ref_is_reported(market, make_remote):
    remote = make_remote("reffy")
    sha = remote.commit({CLAUDE: manifest("reffy")})
    pin(market, remote, sha, ref="deleted-branch")
    result = market.run("update", check=True)
    assert "== reffy: could not resolve latest ref" in result.stdout
    assert market.claude_plugin("reffy")["source"]["sha"] == sha


def test_update_old_sha_no_longer_fetchable(market, make_remote):
    # Force-pushed upstream: the pinned commit is gone, so there is no old subject.
    remote = make_remote("rewritten")
    new = remote.commit({CLAUDE: manifest("rewritten")}, "Fresh history")
    pin(market, remote, "f" * 40)
    result = market.run("update", check=True)
    assert f"before: {'f' * 12} \n" in result.stdout
    assert f"after:  {new[:12]} Fresh history" in result.stdout
    assert market.claude_plugin("rewritten")["source"]["sha"] == new


def test_update_resorts_catalogs_and_table(market, make_remote):
    for name in ("zed", "Alpha"):
        remote = make_remote(name)
        pin(market, remote, remote.commit({CLAUDE: manifest(name)}))
    market.run("update", check=True)
    assert market.names() == ["ai-plugins", "Alpha", "zed"]
    assert market.names("codex") == ["ai-plugins", "Alpha", "zed"]
    assert [r.split("](")[0].strip("| [`") for r in market.table_rows()] == \
        ["ai-plugins", "Alpha", "zed"]


@pytest.mark.parametrize("kind", ["url", "git-subdir"])
def test_update_codex_entry_with_non_dict_source_is_left_alone(market, make_remote,
                                                               kind):
    remote = make_remote("odd")
    old = remote.commit({f"p/{CLAUDE}" if kind == "git-subdir" else CLAUDE:
                         manifest("odd")})
    new = remote.commit({"x": "1"})
    pin(market, remote, old, subdir="p" if kind == "git-subdir" else None,
        codex=False)
    market.add_codex(codex_entry("odd", "./vendored/odd"))

    market.run("update", check=True)
    assert market.claude_plugin("odd")["source"]["sha"] == new
    assert market.codex_plugin("odd")["source"] == "./vendored/odd"

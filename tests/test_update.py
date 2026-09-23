"""End-to-end tests for `ai-plugins.py update`, against local fake upstreams."""

from conftest import codex_entry, manifest, pin

CLAUDE = ".claude-plugin/plugin.json"


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
    assert market.plugin("mover")["source"]["sha"] == new
    assert market.plugin("mover", "codex")["source"]["sha"] == new
    assert "== mover: updated ==" in result.stdout
    assert f"before: {old[:12]} Old commit" in result.stdout
    assert f"after:  {new[:12]} New commit" in result.stdout
    # Same version: no version line, README row untouched.
    assert "version:" not in result.stdout
    assert market.plugin("mover")["version"] == "1.0.0"
    assert market.table_rows()[-1].endswith("| Does 1.0.0 | 1.0.0 |")


def test_update_bumps_version_and_readme_row(market, make_remote):
    remote = make_remote("bumpy")
    old = remote.commit({CLAUDE: manifest("bumpy", "1.0.0")})
    remote.commit({CLAUDE: manifest("bumpy", "1.1.0")}, "Release 1.1.0")
    pin(market, remote, old)

    result = market.run("update", check=True)
    assert "version: 1.0.0 -> 1.1.0" in result.stdout
    assert market.plugin("bumpy")["version"] == "1.1.0"
    # Only the version cell changes, even though the description mentions 1.0.0.
    assert market.table_rows()[-1] == f"| [bumpy]({remote.web_url}) | Does 1.0.0 | 1.1.0 |"
    # The Codex catalog has no version field to bump.
    assert "version" not in market.plugin("bumpy", "codex")


def test_update_git_subdir_reads_version_from_path(market, make_remote):
    remote = make_remote("mono")
    old = remote.commit({
        CLAUDE: manifest("root-thing", "9.9.9"),
        f"plugins/inner/{CLAUDE}": manifest("inner", "1.0.0"),
    })
    remote.commit({f"plugins/inner/{CLAUDE}": manifest("inner", "2.0.0")})
    pin(market, remote, old, name="inner", subdir="plugins/inner")

    market.run("update", check=True)
    entry = market.plugin("inner")
    assert entry["version"] == "2.0.0"
    assert entry["source"]["path"] == "plugins/inner"
    assert market.plugin("inner", "codex")["source"]["path"] == "./plugins/inner"


def test_update_follows_pinned_ref_not_default_branch(market, make_remote):
    remote = make_remote("tracked")
    base = remote.commit({CLAUDE: manifest("tracked")})
    remote.checkout("stable", create=True)
    stable = remote.commit({"s": "1"}, "Stable fix")
    remote.checkout("main")
    remote.commit({"m": "1"}, "Main work")
    pin(market, remote, base, ref="stable")

    market.run("update", check=True)
    source = market.plugin("tracked")["source"]
    assert source["sha"] == stable
    assert source["ref"] == "stable"


def test_update_github_source(market, make_remote):
    remote = make_remote("gh")
    old = remote.commit({CLAUDE: manifest("gh")})
    new = remote.commit({"x": "1"})
    pin(market, remote, old, kind="github", codex=False)

    market.run("update", check=True)
    assert market.plugin("gh")["source"] == {
        "source": "github", "repo": remote.slug, "sha": new,
    }


def test_update_without_readme_row_or_codex_catalog(market, make_remote):
    remote = make_remote("lean")
    old = remote.commit({CLAUDE: manifest("lean", "1.0.0")})
    remote.commit({CLAUDE: manifest("lean", "2.0.0")})
    pin(market, remote, old, row=False)
    market.codex_path.unlink()

    market.run("update", check=True)
    assert market.plugin("lean")["version"] == "2.0.0"
    assert not any("[lean]" in r for r in market.table_rows())


def test_update_missing_manifest_keeps_version(market, make_remote):
    remote = make_remote("gone")
    old = remote.commit({CLAUDE: manifest("gone", "1.0.0")})
    (remote.path / ".claude-plugin" / "plugin.json").unlink()
    new = remote.commit({}, "Drop manifest")
    pin(market, remote, old)

    market.run("update", check=True)
    entry = market.plugin("gone")
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
    assert market.plugin("ghost")["source"]["sha"] == ghost_sha
    assert market.plugin("good")["source"]["sha"] == new


def test_update_unknown_ref_is_reported(market, make_remote):
    remote = make_remote("reffy")
    sha = remote.commit({CLAUDE: manifest("reffy")})
    pin(market, remote, sha, ref="deleted-branch")
    result = market.run("update", check=True)
    assert "== reffy: could not resolve latest ref" in result.stdout
    assert market.plugin("reffy")["source"]["sha"] == sha


def test_update_old_sha_no_longer_fetchable(market, make_remote):
    # Force-pushed upstream: the pinned commit is gone, so there is no old subject.
    remote = make_remote("rewritten")
    new = remote.commit({CLAUDE: manifest("rewritten")}, "Fresh history")
    pin(market, remote, "f" * 40)
    result = market.run("update", check=True)
    assert f"before: {'f' * 12} \n" in result.stdout
    assert f"after:  {new[:12]} Fresh history" in result.stdout
    assert market.plugin("rewritten")["source"]["sha"] == new


def test_update_codex_entry_with_non_dict_source_is_left_alone(market, make_remote):
    remote = make_remote("odd")
    old = remote.commit({CLAUDE: manifest("odd")})
    new = remote.commit({"x": "1"})
    pin(market, remote, old, codex=False)
    market.add_entry(codex_entry("odd", "./vendored/odd"), "codex")

    market.run("update", check=True)
    assert market.plugin("odd")["source"]["sha"] == new
    assert market.plugin("odd", "codex")["source"] == "./vendored/odd"

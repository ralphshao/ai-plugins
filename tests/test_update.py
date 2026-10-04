"""End-to-end tests for `ai-plugins.py update`, against local fake upstreams."""

from conftest import codex_entry, manifest, pin

CLAUDE = ".claude-plugin/plugin.json"
CODEX = ".codex-plugin/plugin.json"


def test_update_nothing_remote(market):
    before = market.snapshot()
    result = market.run("update", check=True)
    assert "No remote-ref plugins found" in result.stdout
    assert market.snapshot() == before


def test_update_up_to_date_leaves_files_byte_identical(market, make_remote):
    remote = make_remote("steady")
    sha = remote.commit({CLAUDE: manifest("steady")}, "Initial release")
    pin(market, remote, sha, ref="main")
    before = market.snapshot()

    result = market.run("update", check=True)
    assert "== steady: up to date ==" in result.stdout
    # No clone just to print a subject when nothing changed.
    assert f"{sha[:12]} (" in result.stdout
    assert "Initial release" not in result.stdout
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


def test_update_codex_only_plugin_reads_codex_manifest(market, make_remote):
    remote = make_remote("cdx")
    old = remote.commit({CODEX: manifest("cdx", "1.0.0")})
    remote.commit({CODEX: manifest("cdx", "1.1.0")})
    pin(market, remote, old)

    market.run("update", check=True)
    assert market.plugin("cdx")["version"] == "1.1.0"


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
    remote.tag("v9.0.0")  # an explicit ref beats the latest release
    pin(market, remote, base, ref="stable")

    market.run("update", check=True)
    source = market.plugin("tracked")["source"]
    assert source["sha"] == stable
    assert source["ref"] == "stable"


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

    result = market.run("update", check=True)
    entry = market.plugin("gone")
    assert entry["source"]["sha"] == new
    assert entry["version"] == "1.0.0"
    assert f"note: version left at 1.0.0 (no plugin.json at {new[:12]})" in result.stdout


def test_update_failed_fetch_of_new_commit_says_why(market, make_remote, ai_plugins,
                                                    monkeypatch, capsys):
    remote = make_remote("flaky")
    old = remote.commit({CLAUDE: manifest("flaky", "1.0.0")})
    new = remote.commit({CLAUDE: manifest("flaky", "2.0.0")})
    pin(market, remote, old)

    # ls-remote sees the new commit, but fetching it fails (e.g. a timeout).
    def fail(url, ref):
        raise RuntimeError("git fetch timed out after 120s")

    monkeypatch.setattr(ai_plugins, "fetch_commit", fail)
    monkeypatch.chdir(market.path)
    ai_plugins.cmd_update(None)
    out = capsys.readouterr().out
    assert (f"note: version left at 1.0.0 (could not fetch {new[:12]}: "
            "git fetch timed out after 120s)") in out
    assert market.plugin("flaky")["source"]["sha"] == new


def test_update_with_empty_codex_catalog(market, make_remote):
    remote = make_remote("solo")
    old = remote.commit({CLAUDE: manifest("solo")})
    new = remote.commit({"x": "1"})
    pin(market, remote, old, codex=False)
    codex = market.catalog("codex")
    codex["plugins"] = []
    market.save(codex, "codex")

    market.run("update", check=True)
    assert market.plugin("solo")["source"]["sha"] == new
    assert market.catalog("codex")["plugins"] == []


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
    header = f"== ghost: could not resolve latest ref from {ghost.clone_url} =="
    assert header in result.stdout
    # git's own error follows, so the user can tell why.
    reason = result.stdout.split(header + "\n", 1)[1].split("\n", 1)[0]
    assert reason.startswith("   ") and reason.strip()
    assert market.plugin("ghost")["source"]["sha"] == ghost_sha
    assert market.plugin("good")["source"]["sha"] == new


def test_update_unknown_ref_is_reported(market, make_remote):
    remote = make_remote("reffy")
    sha = remote.commit({CLAUDE: manifest("reffy")})
    pin(market, remote, sha, ref="deleted-branch")
    result = market.run("update", check=True)
    # No git error to show for a ref that simply isn't there.
    assert f"== reffy: could not resolve latest ref from {remote.clone_url} ==\n\n" \
        in result.stdout
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


def test_update_pins_latest_release_not_branch_tip(market, make_remote):
    remote = make_remote("released")
    old = remote.commit({CLAUDE: manifest("released", "1.0.0")})
    remote.tag("v1.0.0")
    v19 = remote.commit({CLAUDE: manifest("released", "1.9.0")}, "Release 1.9.0")
    remote.tag("v1.9.0", annotated=True)
    v110 = remote.commit({CLAUDE: manifest("released", "1.10.0")}, "Release 1.10.0")
    # Annotated: ls-remote lists the tag object, then the peeled commit.
    remote.tag("v1.10.0", annotated=True)
    remote.commit({CLAUDE: manifest("released", "2.0.0-beta")}, "Beta")
    remote.tag("v2.0.0-beta")
    remote.tag("nightly")
    remote.commit({"x": "1"}, "Unreleased work")
    pin(market, remote, old)

    result = market.run("update", check=True)
    assert market.plugin("released")["source"]["sha"] == v110
    assert market.plugin("released", "codex")["source"]["sha"] == v110
    assert market.plugin("released")["version"] == "1.10.0"
    assert f"after:  {v110[:12]} Release 1.10.0 (release v1.10.0)" in result.stdout
    assert v19 != v110


def test_update_adds_missing_ref_when_up_to_date(market, make_remote):
    remote = make_remote("noref")
    sha = remote.commit({CLAUDE: manifest("noref")})
    remote.tag("v1.0.0")
    pin(market, remote, sha)

    result = market.run("update", check=True)
    assert "ref: (none) -> v1.0.0" in result.stdout
    for which in ("claude", "codex"):
        source = market.plugin("noref", which)["source"]
        assert source["sha"] == sha
        assert list(source)[-2:] == ["sha", "ref"]
        assert source["ref"] == "v1.0.0"


def test_update_moves_release_tag_ref_to_newest_release(market, make_remote):
    remote = make_remote("tagref")
    old = remote.commit({CLAUDE: manifest("tagref", "1.0.0")})
    remote.tag("v1.0.0")
    new = remote.commit({CLAUDE: manifest("tagref", "2.0.0")})
    remote.tag("v2.0.0")
    pin(market, remote, old, ref="v1.0.0")

    market.run("update", check=True)
    for which in ("claude", "codex"):
        source = market.plugin("tagref", which)["source"]
        assert (source["sha"], source["ref"]) == (new, "v2.0.0")


def test_update_default_branch_ref_switches_to_first_release(market, make_remote):
    remote = make_remote("late")
    old = remote.commit({CLAUDE: manifest("late")})
    new = remote.commit({"x": "1"}, "First release")
    remote.tag("v1.0.0")
    pin(market, remote, old, ref="main")

    market.run("update", check=True)
    source = market.plugin("late")["source"]
    assert (source["sha"], source["ref"]) == (new, "v1.0.0")


def test_update_without_release_tags_follows_default_branch(market, make_remote):
    remote = make_remote("untagged")
    old = remote.commit({CLAUDE: manifest("untagged")})
    remote.tag("not-a-release")
    new = remote.commit({"x": "1"}, "Tip")
    pin(market, remote, old)

    result = market.run("update", check=True)
    assert market.plugin("untagged")["source"]["sha"] == new
    assert market.plugin("untagged", "codex")["source"]["ref"] == "main"
    assert "(default branch)" in result.stdout


def test_update_pinned_ref_matches_branch_name_exactly(market, make_remote):
    remote = make_remote("suffix")
    base = remote.commit({CLAUDE: manifest("suffix")})
    remote.checkout("stable", create=True)
    stable = remote.commit({"s": "1"}, "Stable fix")
    # Sorts before refs/heads/stable and ends in "stable".
    remote.checkout("feature/stable", create=True)
    remote.commit({"f": "1"}, "Feature work")
    remote.checkout("main")
    pin(market, remote, base, ref="stable")

    market.run("update", check=True)
    assert market.plugin("suffix")["source"]["sha"] == stable


def test_update_annotated_tag_ref_pins_the_commit(market, make_remote):
    remote = make_remote("tagged")
    base = remote.commit({CLAUDE: manifest("tagged")})
    target = remote.commit({"t": "1"}, "Tagged")
    remote.tag("pinned-here", annotated=True)  # not a release tag, so followed as-is
    remote.commit({"m": "1"}, "Later")
    pin(market, remote, base, ref="pinned-here")

    market.run("update", check=True)
    assert market.plugin("tagged")["source"]["sha"] == target
    assert market.plugin("tagged", "codex")["source"]["sha"] == target


def test_update_tag_beats_branch_of_the_same_name(market, make_remote):
    remote = make_remote("dual")
    base = remote.commit({CLAUDE: manifest("dual")})
    remote.checkout("pinned", create=True)
    remote.commit({"b": "1"}, "Branch tip")
    remote.checkout("main")
    tagged = remote.commit({"t": "1"}, "Tagged")
    remote.tag("pinned")
    pin(market, remote, base, ref="pinned")

    market.run("update", check=True)
    assert market.plugin("dual")["source"]["sha"] == tagged


def test_update_fully_qualified_annotated_tag_pins_the_commit(market, make_remote):
    remote = make_remote("fqtag")
    base = remote.commit({CLAUDE: manifest("fqtag")})
    target = remote.commit({"t": "1"}, "Tagged")
    remote.tag("pinned-here", annotated=True)
    remote.commit({"m": "1"}, "Later")
    pin(market, remote, base, ref="refs/tags/pinned-here")

    market.run("update", check=True)
    assert market.plugin("fqtag")["source"]["sha"] == target


def test_update_head_ref_follows_remote_head(market, make_remote):
    remote = make_remote("headed")
    base = remote.commit({CLAUDE: manifest("headed")})
    tip = remote.commit({"x": "1"}, "Tip")
    pin(market, remote, base, ref="HEAD")

    market.run("update", check=True)
    source = market.plugin("headed")["source"]
    assert (source["sha"], source["ref"]) == (tip, "HEAD")


def test_update_unparseable_row_fails_before_any_edit(market, make_remote):
    # The name link parses, but the row's shape doesn't, so its version
    # cell can't be rewritten.
    remote = make_remote("cramped")
    old = remote.commit({CLAUDE: manifest("cramped", "1.0.0")})
    remote.commit({CLAUDE: manifest("cramped", "2.0.0")})
    pin(market, remote, old, row=False)
    market.add_row(f"|[cramped]({remote.web_url})|Does|1.0.0|")
    before = market.snapshot()

    result = market.run("update", check=False)
    assert "|[cramped]" in result.stderr
    assert market.snapshot() == before


def test_update_refuses_readme_row_it_cannot_parse(market, make_remote):
    remote = make_remote("rowy")
    sha = remote.commit({CLAUDE: manifest("rowy")})
    pin(market, remote, sha, ref="main")
    market.add_row("| hand-written | no link here | 1.0 |")
    before = market.snapshot()

    result = market.run("update", check=False)
    assert "| hand-written |" in result.stderr
    assert market.snapshot() == before


def test_update_refuses_duplicate_readme_rows(market, make_remote):
    remote = make_remote("twice")
    sha = remote.commit({CLAUDE: manifest("twice")})
    pin(market, remote, sha, ref="main")
    market.add_row(f"| [twice]({remote.web_url}) | Again | 1.0.0 |")
    before = market.snapshot()

    result = market.run("update", check=False)
    assert "lists twice more than once" in result.stderr
    assert market.snapshot() == before


def test_update_repairs_codex_sha_drift_when_claude_is_current(market, make_remote):
    remote = make_remote("drifty")
    old = remote.commit({CLAUDE: manifest("drifty")}, "Old")
    new = remote.commit({"x": "1"}, "New")
    pin(market, remote, new, ref="main")
    codex = market.catalog("codex")
    next(p for p in codex["plugins"] if p["name"] == "drifty")["source"]["sha"] = old
    market.save(codex, "codex")

    result = market.run("update", check=True)
    assert "== drifty: up to date ==" in result.stdout
    assert f"sha: {old[:12]} -> {new[:12]}" in result.stdout
    assert market.plugin("drifty", "codex")["source"]["sha"] == new
    assert market.plugin("drifty")["source"]["sha"] == new


def test_update_follows_fully_qualified_ref(market, make_remote):
    remote = make_remote("qualified")
    base = remote.commit({CLAUDE: manifest("qualified")})
    remote.checkout("stable", create=True)
    stable = remote.commit({"s": "1"}, "Stable fix")
    remote.checkout("main")
    pin(market, remote, base, ref="refs/heads/stable")

    market.run("update", check=True)
    source = market.plugin("qualified")["source"]
    assert source["sha"] == stable
    assert source["ref"] == "refs/heads/stable"


def test_update_names_the_file_whose_ref_is_stale(market, make_remote):
    remote = make_remote("refdrift")
    sha = remote.commit({CLAUDE: manifest("refdrift")})
    pin(market, remote, sha, ref="main")
    codex = market.catalog("codex")
    del next(p for p in codex["plugins"] if p["name"] == "refdrift")["source"]["ref"]
    market.save(codex, "codex")

    result = market.run("update", check=True)
    assert ".agents/plugins/marketplace.json ref: (none) -> main" in result.stdout
    assert ".claude-plugin/marketplace.json ref" not in result.stdout
    assert market.plugin("refdrift", "codex")["source"]["ref"] == "main"

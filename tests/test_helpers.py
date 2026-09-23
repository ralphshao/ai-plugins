"""Unit tests for ai-plugins.py's pure helpers (no git, no subprocess)."""

import json
import os

import pytest

from conftest import manifest


# --- sorting ----------------------------------------------------------------

def test_sort_key_puts_self_first_then_case_insensitive(ai_plugins):
    names = ["zeta", "Beta", "ai-plugins", "alpha", "ai-plugins-extra"]
    assert sorted(names, key=ai_plugins.sort_key) == [
        "ai-plugins", "ai-plugins-extra", "alpha", "Beta", "zeta",
    ]


def test_save_catalog_sorts_and_writes_utf8_with_trailing_newline(ai_plugins, tmp_path):
    path = tmp_path / "marketplace.json"
    data = {"plugins": [{"name": "b"}, {"name": "ai-plugins"},
                        {"name": "A", "author": {"name": "Mert Koseoğlu"}}]}
    ai_plugins.save_catalog(str(path), data)
    raw = path.read_bytes()
    assert raw.endswith(b"}\n")
    assert b"\r\n" not in raw
    text = raw.decode("utf-8")
    assert "Koseoğlu" in text  # not \u-escaped
    assert [p["name"] for p in json.loads(text)["plugins"]] == ["ai-plugins", "A", "b"]


# --- parse_repo -------------------------------------------------------------

GH = "https://github.com/owner/repo"


@pytest.mark.parametrize("spec", [
    "owner/repo",
    "owner/repo.git",
    " owner/repo/ ",
    "https://github.com/owner/repo",
    "https://github.com/owner/repo/",
    "https://github.com/owner/repo.git",
    "http://github.com/owner/repo",
    "https://www.github.com/owner/repo",
    "github.com/owner/repo",
    "git@github.com:owner/repo.git",
])
def test_parse_repo_github_forms(ai_plugins, spec):
    assert ai_plugins.parse_repo(spec) == (f"{GH}.git", GH, None, None)


def test_parse_repo_keeps_dots_and_dashes(ai_plugins):
    clone, web, _, _ = ai_plugins.parse_repo("my-org/my.repo-name")
    assert web == "https://github.com/my-org/my.repo-name"
    assert clone == f"{web}.git"


def test_parse_repo_tree_link_with_ref_only(ai_plugins):
    assert ai_plugins.parse_repo(f"{GH}/tree/v2") == (f"{GH}.git", GH, "v2", None)


def test_parse_repo_tree_link_with_nested_path(ai_plugins):
    assert ai_plugins.parse_repo(f"{GH}/tree/main/plugins/foo/") == (
        f"{GH}.git", GH, "main", "plugins/foo",
    )


def test_parse_repo_non_github_url(ai_plugins):
    assert ai_plugins.parse_repo("https://gitlab.com/group/sub/repo.git") == (
        "https://gitlab.com/group/sub/repo.git",
        "https://gitlab.com/group/sub/repo",
        None, None,
    )


@pytest.mark.parametrize("spec", ["just-a-name", "", "a/b/c"])
def test_parse_repo_rejects_garbage(ai_plugins, spec, capsys):
    with pytest.raises(SystemExit) as exc:
        ai_plugins.parse_repo(spec)
    assert exc.value.code == 1
    assert "Not a GitHub URL" in capsys.readouterr().err


# --- sources ----------------------------------------------------------------

def test_source_url(ai_plugins):
    assert ai_plugins.source_url({"source": "github", "repo": "o/r"}) == \
        "https://github.com/o/r.git"
    assert ai_plugins.source_url({"source": "url", "url": "https://x/y.git"}) == \
        "https://x/y.git"
    assert ai_plugins.source_url({"source": "git-subdir", "url": "https://x/y.git",
                                  "path": "p"}) == "https://x/y.git"


def test_make_source_root_is_url(ai_plugins):
    assert ai_plugins.make_source("U", "S", "") == {"source": "url", "url": "U", "sha": "S"}
    assert ai_plugins.make_source("U", "S", "", codex_style=True) == \
        {"source": "url", "url": "U", "sha": "S"}


def test_make_source_nested_is_git_subdir(ai_plugins):
    assert ai_plugins.make_source("U", "S", "plugins/x") == \
        {"source": "git-subdir", "url": "U", "path": "plugins/x", "sha": "S"}
    # Codex paths are written ./-relative.
    assert ai_plugins.make_source("U", "S", "plugins/x", codex_style=True)["path"] == \
        "./plugins/x"


# --- README rows ------------------------------------------------------------

def test_readme_row_escapes_pipes(ai_plugins):
    assert ai_plugins.readme_row("n", "L", "a | b", "1.0") == "| [n](L) | a \\| b | 1.0 |"


def test_set_row_version_replaces_last_cell_only(ai_plugins):
    row = "| [`x`](link) | Does 1.0 things \\| more | 1.0 |"
    assert ai_plugins.set_row_version(row, "2.0") == \
        "| [`x`](link) | Does 1.0 things \\| more | 2.0 |"


def test_set_row_version_leaves_malformed_row_alone(ai_plugins):
    assert ai_plugins.set_row_version("not a row", "2.0") == "not a row"


def test_row_name_matches_backticked_and_plain_link_text(ai_plugins):
    rx = ai_plugins.ROW_NAME_RE
    assert rx.search(" [`ai-plugins`](plugins/ai-plugins) ").group(1) == "ai-plugins"
    assert rx.search(" [caveman](https://x) ").group(1) == "caveman"


# --- README table read/write ------------------------------------------------

README = """\
# Title

intro

| Plugin | Description | Version |
| --- | --- | --- |
| [zed](z) | Z | 1 |
| [`ai-plugins`](p) | self | 1 |
| [Alpha](a) | A | 1 |

after"""


def test_read_readme_table_missing_file(ai_plugins, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert ai_plugins.read_readme_table() is None


def test_read_readme_table_without_table(ai_plugins, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "README.md").write_text("# No table here\n")
    assert ai_plugins.read_readme_table() is None


def test_read_readme_table_finds_rows_by_link_text(ai_plugins, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "README.md").write_text(README)
    lines, start, end, rows = ai_plugins.read_readme_table()
    assert lines[start] == "| [zed](z) | Z | 1 |"
    assert lines[end] == ""
    assert set(rows) == {"zed", "ai-plugins", "Alpha"}


def test_write_readme_table_sorts_and_preserves_surroundings(ai_plugins, tmp_path,
                                                             monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "README.md").write_text(README)
    table = ai_plugins.read_readme_table()
    ai_plugins.write_readme_table(table, table[3])
    assert (tmp_path / "README.md").read_text() == README.replace(
        "| [zed](z) | Z | 1 |\n| [`ai-plugins`](p) | self | 1 |\n| [Alpha](a) | A | 1 |",
        "| [`ai-plugins`](p) | self | 1 |\n| [Alpha](a) | A | 1 |\n| [zed](z) | Z | 1 |",
    )


def test_write_readme_table_can_drop_all_rows_but_one(ai_plugins, tmp_path,
                                                      monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "README.md").write_text(README)
    table = ai_plugins.read_readme_table()
    rows = {"ai-plugins": table[3]["ai-plugins"]}
    ai_plugins.write_readme_table(table, rows)
    text = (tmp_path / "README.md").read_text()
    assert "zed" not in text and "Alpha" not in text
    assert text.endswith("| [`ai-plugins`](p) | self | 1 |\n\nafter")


# --- manifest discovery -----------------------------------------------------

def write_manifest(root, subdir, kind, name="p"):
    d = root / subdir / f".{kind}-plugin"
    d.mkdir(parents=True, exist_ok=True)
    (d / "plugin.json").write_text(json.dumps(manifest(name)))


def test_find_manifests_root_and_nested(ai_plugins, tmp_path):
    write_manifest(tmp_path, ".", "claude")
    write_manifest(tmp_path, "plugins/b", "claude")
    write_manifest(tmp_path, "plugins/a", "codex")
    assert ai_plugins.find_manifests(str(tmp_path), "claude") == ["", "plugins/b"]
    assert ai_plugins.find_manifests(str(tmp_path), "codex") == ["plugins/a"]


def test_find_manifests_skips_git_and_node_modules(ai_plugins, tmp_path):
    write_manifest(tmp_path, "node_modules/dep", "claude")
    write_manifest(tmp_path, ".git/x", "claude")
    write_manifest(tmp_path, "real", "claude")
    assert ai_plugins.find_manifests(str(tmp_path), "claude") == ["real"]


def test_pick_manifest_dir_none_found(ai_plugins, tmp_path):
    assert ai_plugins.pick_manifest_dir(str(tmp_path), "claude", None) is None


def test_pick_manifest_dir_single(ai_plugins, tmp_path):
    write_manifest(tmp_path, "deep/er", "claude")
    assert ai_plugins.pick_manifest_dir(str(tmp_path), "claude", None) == "deep/er"


def test_pick_manifest_dir_several_dies_listing_them(ai_plugins, tmp_path, capsys):
    write_manifest(tmp_path, ".", "claude")
    write_manifest(tmp_path, "plugins/x", "claude")
    with pytest.raises(SystemExit):
        ai_plugins.pick_manifest_dir(str(tmp_path), "claude", None)
    err = capsys.readouterr().err
    assert "  .\n" in err and "  plugins/x\n" in err and "--path" in err


@pytest.mark.parametrize("hint", ["plugins/x", "./plugins/x", "plugins/x/", "plugins"])
def test_pick_manifest_dir_hint_narrows(ai_plugins, tmp_path, hint):
    write_manifest(tmp_path, ".", "claude")
    write_manifest(tmp_path, "plugins/x", "claude")
    write_manifest(tmp_path, "other", "claude")
    assert ai_plugins.pick_manifest_dir(str(tmp_path), "claude", hint) == "plugins/x"


def test_pick_manifest_dir_hint_is_prefix_on_path_segments(ai_plugins, tmp_path):
    # "plug" must not match "plugins/x".
    write_manifest(tmp_path, "plugins/x", "claude")
    assert ai_plugins.pick_manifest_dir(str(tmp_path), "claude", "plug") is None


def test_read_manifest_handles_missing_and_invalid(ai_plugins, tmp_path):
    assert ai_plugins.read_manifest(str(tmp_path), ".", "claude") is None
    d = tmp_path / ".claude-plugin"
    d.mkdir()
    (d / "plugin.json").write_text("{not json")
    assert ai_plugins.read_manifest(str(tmp_path), ".", "claude") is None
    (d / "plugin.json").write_text('{"name": "ok"}')
    assert ai_plugins.read_manifest(str(tmp_path), ".", "claude") == {"name": "ok"}


# --- git helpers against a local remote ----------------------------------------

def test_latest_sha_and_fetch_commit(ai_plugins, make_remote):
    remote = make_remote("thing")
    first = remote.commit({"a.txt": "1"}, "first")
    second = remote.commit({"a.txt": "2"}, "second")
    assert ai_plugins.latest_sha(remote.clone_url, None) == second

    clone = ai_plugins.fetch_commit(remote.clone_url, first)
    try:
        assert ai_plugins.commit_subject(clone) == "first"
    finally:
        ai_plugins.rmtree(clone)
    assert not os.path.exists(clone)


def test_fetch_commit_returns_none_and_cleans_up_on_failure(ai_plugins, make_remote,
                                                            monkeypatch, tmp_path):
    made = []
    real_mkdtemp = ai_plugins.tempfile.mkdtemp

    def tracking_mkdtemp(**kw):
        made.append(real_mkdtemp(**kw))
        return made[-1]

    monkeypatch.setattr(ai_plugins.tempfile, "mkdtemp", tracking_mkdtemp)
    remote = make_remote("thing")
    remote.commit({"a.txt": "1"})
    assert ai_plugins.fetch_commit(remote.clone_url, "0" * 40) is None
    assert made and not any(os.path.exists(p) for p in made)


def test_commit_subject_of_nothing(ai_plugins):
    assert ai_plugins.commit_subject(None) == ""
    ai_plugins.rmtree(None)  # no-op, must not raise

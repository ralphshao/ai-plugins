"""Unit tests for ai-plugins.py helper branches the end-to-end tests don't reach."""

import json

import pytest

from conftest import manifest


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


@pytest.mark.parametrize("spec", ["just-a-name", "", "a/b/c"])
def test_parse_repo_rejects_garbage(ai_plugins, spec, capsys):
    with pytest.raises(SystemExit) as exc:
        ai_plugins.parse_repo(spec)
    assert exc.value.code == 1
    assert "Not a GitHub URL" in capsys.readouterr().err


# --- manifest discovery -----------------------------------------------------

def write_manifest(root, subdir, kind, name="p"):
    d = root / subdir / f".{kind}-plugin"
    d.mkdir(parents=True, exist_ok=True)
    (d / "plugin.json").write_text(json.dumps(manifest(name)))


def test_find_manifests_skips_git_and_node_modules(ai_plugins, tmp_path):
    write_manifest(tmp_path, "node_modules/dep", "claude")
    write_manifest(tmp_path, ".git/x", "claude")
    write_manifest(tmp_path, "real", "claude")
    assert ai_plugins.find_manifests(str(tmp_path), "claude") == ["real"]


@pytest.mark.parametrize("hint", ["plugins/x", "plugins"])
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


# --- git helpers ------------------------------------------------------------

def test_fetch_commit_returns_none_and_cleans_up_on_failure(ai_plugins, make_remote,
                                                            monkeypatch, tmp_path):
    temp = tmp_path / "temp"
    temp.mkdir()
    monkeypatch.setattr(ai_plugins.tempfile, "tempdir", str(temp))
    remote = make_remote("thing")
    remote.commit({"a.txt": "1"})
    assert ai_plugins.fetch_commit(remote.clone_url, "0" * 40) is None
    assert not any(temp.iterdir())

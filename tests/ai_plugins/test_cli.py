"""Tests for ai-plugins.py's command-line entry point."""

import subprocess


def test_outside_a_git_repo(market, tmp_path):
    result = market.run("update", cwd=tmp_path, check=False)
    assert result.returncode == 1
    assert "Run this from inside the ai-plugins git repo" in result.stderr


def test_git_repo_without_marketplace(market, tmp_path):
    bare = tmp_path / "bare"
    bare.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=bare, check=True)
    result = market.run("update", cwd=bare, check=False)
    assert result.returncode == 1
    assert "No .claude-plugin" in result.stderr and "marketplace.json" in result.stderr


def test_runs_from_a_subdirectory(market):
    sub = market.path / "a" / "b"
    sub.mkdir(parents=True)
    market.run("update", cwd=sub, check=True)

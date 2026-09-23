"""Tests for ai-plugins.py's command-line entry point."""

import subprocess
import sys

import pytest

from conftest import SCRIPT


def run(*args, cwd):
    return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=cwd,
                          capture_output=True, text=True)


def test_no_subcommand_is_a_usage_error(market):
    result = run(cwd=market.path)
    assert result.returncode == 2
    assert "usage: ai-plugins.py" in result.stderr


@pytest.mark.parametrize("command", ["update", "add", "remove"])
def test_help_lists_each_subcommand(market, command):
    result = run("--help", cwd=market.path)
    assert result.returncode == 0
    assert command in result.stdout


def test_missing_required_argument(market):
    result = run("remove", cwd=market.path)
    assert result.returncode == 2
    assert "name" in result.stderr


def test_outside_a_git_repo(tmp_path):
    result = run("update", cwd=tmp_path)
    assert result.returncode == 1
    assert "Run this from inside the ai-plugins git repo" in result.stderr


def test_git_repo_without_marketplace(tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    result = run("update", cwd=tmp_path)
    assert result.returncode == 1
    assert "No .claude-plugin" in result.stderr and "marketplace.json" in result.stderr


def test_runs_from_a_subdirectory(market):
    sub = market.path / "a" / "b"
    sub.mkdir(parents=True)
    result = run("update", cwd=sub)
    assert result.returncode == 0, result.stderr

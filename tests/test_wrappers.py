"""Tests for the run.sh and run.ps1 wrappers around ai-plugins.py.

The wrappers must forward every argument and pass the script's exit code
through. The .sh tests need bash (skipped on Windows); the .ps1 tests need
PowerShell 7 (`pwsh`), and are skipped when it isn't installed.
"""

import os
import shutil
import subprocess
import sys

import pytest

from conftest import SCRIPT, manifest

RUN_SH = SCRIPT.with_name("run.sh")
RUN_PS1 = SCRIPT.with_name("run.ps1")
BASH = shutil.which("bash")
PWSH = shutil.which("pwsh")

needs_bash = pytest.mark.skipif(
    sys.platform == "win32" or not BASH, reason="bash wrappers are for macOS/Linux")
needs_pwsh = pytest.mark.skipif(not PWSH, reason="pwsh is not installed")


def run_sh(*args, cwd, env=None):
    return subprocess.run([BASH, str(RUN_SH), *args], cwd=cwd,
                          capture_output=True, text=True, env=env)


def run_ps1(*args, cwd):
    return subprocess.run(
        [PWSH, "-NoProfile", "-NonInteractive", "-File", str(RUN_PS1), *args],
        cwd=cwd, capture_output=True, text=True)


@pytest.mark.skipif(sys.platform == "win32", reason="no exec bit on Windows")
def test_sh_wrapper_is_executable():
    assert os.access(RUN_SH, os.X_OK)


# --- bash --------------------------------------------------------------------

@needs_bash
def test_sh_update_runs_from_another_directory(market):
    # The wrapper finds the script relative to itself, not the cwd.
    sub = market.path / "nested"
    sub.mkdir()
    result = run_sh("update", cwd=sub)
    assert result.returncode == 0, result.stderr
    assert "No remote-ref plugins found" in result.stdout


@needs_bash
def test_sh_add_forwards_all_arguments(market, make_remote):
    remote = make_remote("multi")
    remote.commit({
        "one/.claude-plugin/plugin.json": manifest("one"),
        "two/.claude-plugin/plugin.json": manifest("two"),
    })
    result = run_sh("add", remote.slug, "--path", "two",
                    "--description", "Two words", cwd=market.path)
    assert result.returncode == 0, result.stderr
    assert market.plugin("two")["description"] == "Two words"


@needs_bash
def test_sh_remove_passes_exit_code_through(market):
    result = run_sh("remove", "does-not-exist", cwd=market.path)
    assert result.returncode == 1
    assert "No plugin named does-not-exist" in result.stderr


@needs_bash
def test_sh_without_python(market, tmp_path):
    # A PATH holding only the tools the wrapper needs, but no python.
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    os.symlink(shutil.which("dirname"), bin_dir / "dirname")
    result = run_sh("update", cwd=market.path,
                    env={**os.environ, "PATH": str(bin_dir)})
    assert result.returncode == 1
    assert "Python 3 is required" in result.stderr


# --- PowerShell --------------------------------------------------------------

@needs_pwsh
def test_ps1_update_runs(market):
    result = run_ps1("update", cwd=market.path)
    assert result.returncode == 0, result.stderr
    assert "No remote-ref plugins found" in result.stdout


@needs_pwsh
def test_ps1_add_forwards_all_arguments(market, make_remote):
    remote = make_remote("multi")
    remote.commit({
        "one/.claude-plugin/plugin.json": manifest("one"),
        "two/.claude-plugin/plugin.json": manifest("two"),
    })
    result = run_ps1("add", remote.slug, "--path", "two",
                     "--description", "Two words", cwd=market.path)
    assert result.returncode == 0, result.stderr
    assert market.plugin("two")["description"] == "Two words"


@needs_pwsh
def test_ps1_remove_passes_exit_code_through(market):
    result = run_ps1("remove", "does-not-exist", cwd=market.path)
    assert result.returncode == 1
    assert "No plugin named does-not-exist" in result.stderr

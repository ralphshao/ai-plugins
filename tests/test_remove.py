"""End-to-end tests for `ai-plugins.py remove`."""

from conftest import codex_entry

SHA = "a" * 40


def seed(market, name, codex=True, row=True):
    source = {"source": "url", "url": f"https://github.com/o/{name}.git", "sha": SHA}
    market.add_claude({"name": name, "source": source, "description": name,
                       "version": "1.0.0"})
    if codex:
        market.add_codex(codex_entry(name, source))
    if row:
        market.add_row(f"| [{name}](https://github.com/o/{name}) | {name} | 1.0.0 |")


def removed_from(stdout):
    """The "   <where>" lines under the "removed" header."""
    block = stdout.split("removed ==\n", 1)[1].split("\n\n", 1)[0]
    return [line.strip() for line in block.splitlines() if not line.strip().startswith("note:")]


def test_remove_drops_plugin_everywhere(market):
    seed(market, "beta")
    seed(market, "gamma")
    result = market.run("remove", "beta", check=True)

    assert market.names() == ["ai-plugins", "gamma"]
    assert market.names("codex") == ["ai-plugins", "gamma"]
    assert not any("[beta]" in r for r in market.table_rows())
    assert len(market.table_rows()) == 2
    assert "== beta: removed ==" in result.stdout
    assert removed_from(result.stdout) == [
        ".claude-plugin/marketplace.json", ".agents/plugins/marketplace.json",
        "README.md plugin table",
    ]
    assert "not committed" in result.stdout
    # Prose outside the table is untouched.
    assert market.readme().endswith("## Repo structure\n\nTrailing prose stays put.\n")


def test_remove_claude_only_plugin(market):
    seed(market, "legacy-only", codex=False)
    result = market.run("remove", "legacy-only", check=True)
    assert market.claude_plugin("legacy-only") is None
    assert removed_from(result.stdout) == [
        ".claude-plugin/marketplace.json", "README.md plugin table",
    ]


def test_remove_row_only_plugin(market):
    # A stray README row with no catalog entry still gets cleaned up.
    market.add_row("| [stray](x) | stray | 1 |")
    result = market.run("remove", "stray", check=True)
    assert removed_from(result.stdout) == ["README.md plugin table"]
    assert not any("[stray]" in r for r in market.table_rows())


def test_remove_lists_remaining_mentions_with_line_numbers(market):
    seed(market, "legacy-only", codex=False)
    agents = market.path / "AGENTS.md"
    agents.write_text(agents.read_text() + "\nlegacy-only has quirks.\n")
    result = market.run("remove", "legacy-only", check=True)
    assert "note: README.md still mentions legacy-only on line(s) 3" in result.stdout
    assert "note: AGENTS.md still mentions legacy-only on line(s) 5" in result.stdout
    # The mention itself is left for a human.
    assert "`legacy-only` is Claude-only" in market.readme()


def test_remove_mentions_match_whole_names_only(market):
    seed(market, "karpathy")
    agents = market.path / "AGENTS.md"
    agents.write_text("andrej-karpathy-skills and karpathy-extra and karpathy_x\n")
    result = market.run("remove", "karpathy", check=True)
    assert "AGENTS.md still mentions" not in result.stdout


def test_remove_matches_exact_name_not_substring(market):
    seed(market, "cave")
    seed(market, "caveman")
    market.run("remove", "cave", check=True)
    assert market.names() == ["ai-plugins", "caveman"]
    assert market.names("codex") == ["ai-plugins", "caveman"]
    assert any("[caveman]" in r for r in market.table_rows())


def test_remove_unknown_plugin_fails_without_edits(market):
    seed(market, "beta")
    before = market.snapshot()
    result = market.run("remove", "nope", check=False)
    assert result.returncode == 1
    assert "No plugin named nope" in result.stderr
    assert market.snapshot() == before


def test_remove_refuses_self(market):
    before = market.snapshot()
    result = market.run("remove", "ai-plugins", check=False)
    assert "Refusing to remove ai-plugins" in result.stderr
    assert market.snapshot() == before


def test_remove_without_codex_catalog(market):
    seed(market, "beta")
    market.codex_path.unlink()
    market.run("remove", "beta", check=True)
    assert market.names() == ["ai-plugins"]
    assert not market.codex_path.exists()


def test_remove_resorts_hand_edited_catalog(market):
    seed(market, "zeta")
    seed(market, "Alpha")
    seed(market, "beta")
    market.run("remove", "beta", check=True)
    assert market.names() == ["ai-plugins", "Alpha", "zeta"]
    assert [r.split("]")[0] for r in market.table_rows()] == [
        "| [`ai-plugins`", "| [Alpha", "| [zeta",
    ]

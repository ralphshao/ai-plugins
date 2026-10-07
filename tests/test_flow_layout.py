"""Structural checks on the flow plugin's skills, agents, and hooks."""

import json
import re

import pytest

from conftest import REPO_ROOT

FLOW = REPO_ROOT / "plugins" / "flow"
# Orchestrators: only the user may start them, on Claude Code and Codex.
USER_ONLY = {"flow", "start", "plan", "ship", "setup-codex"}
SKILLS = sorted(p.parent.name for p in (FLOW / "skills").glob("*/SKILL.md"))


def frontmatter(path):
    m = re.match(r"---\n(.*?)\n---\n", path.read_text(encoding="utf-8"), re.S)
    assert m, f"{path} has no frontmatter"
    return dict(re.findall(r"^([\w-]+):\s*(.*)$", m.group(1), re.M))


@pytest.mark.parametrize("name", SKILLS)
def test_skill_frontmatter(name):
    fm = frontmatter(FLOW / "skills" / name / "SKILL.md")
    assert fm["name"] == name
    assert fm.get("description")
    user_only = fm.get("disable-model-invocation") == "true"
    assert user_only == (name in USER_ONLY), name
    policy = FLOW / "skills" / name / "agents" / "openai.yaml"
    if user_only:
        assert "allow_implicit_invocation: false" in policy.read_text(encoding="utf-8")


def test_every_user_only_skill_exists():
    assert USER_ONLY <= set(SKILLS)


@pytest.mark.parametrize("path", sorted((FLOW / "agents").glob("*.md")), ids=lambda p: p.name)
def test_agents_have_no_hooks_frontmatter(path):
    # Plugin agents ignore hooks:, so a guard declared there would never run.
    fm = frontmatter(path)
    assert fm["name"] == path.stem
    assert "hooks" not in fm


def test_hook_commands_resolve_inside_plugin():
    config = json.loads((FLOW / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    commands = [h["command"] for groups in config["hooks"].values()
                for g in groups for h in g["hooks"]]
    assert commands
    for cmd in commands:
        script = re.search(r'\$\{CLAUDE_PLUGIN_ROOT\}/([^"\s]+)', cmd)
        assert script, cmd
        assert (FLOW / script.group(1)).is_file(), cmd

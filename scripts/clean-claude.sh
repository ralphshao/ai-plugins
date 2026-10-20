#!/usr/bin/env bash
# Start Claude Code with only the named local plugins from this repo, and none
# of your own plugins, hooks, CLAUDE.md, or settings, to try a skill the way
# someone else would get it.
# Usage: scripts/clean-claude.sh <plugin>... [-- <claude args>]
set -euo pipefail
repo=$(cd "$(dirname "$0")/.." && pwd)
[ $# -gt 0 ] && [ "$1" != -- ] || { echo "usage: $0 <plugin>... [-- <claude args>]" >&2; exit 2; }
args=()
while [ $# -gt 0 ] && [ "$1" != -- ]; do
  [ -d "$repo/plugins/$1" ] || { echo "no such plugin: plugins/$1" >&2; exit 1; }
  args+=(--plugin-dir "$repo/plugins/$1")
  shift
done
[ "${1:-}" = -- ] && shift
# Kept between runs so you only log in once; nothing else of yours goes in it.
export CLAUDE_CONFIG_DIR=${CLEAN_CLAUDE_CONFIG_DIR:-$HOME/.claude-clean}
# An empty folder, so no project's CLAUDE.md or .claude/settings.json loads.
cd "$(mktemp -d)"
exec claude "${args[@]}" "$@"

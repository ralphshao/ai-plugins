#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

claude_file=".claude-plugin/marketplace.json"
codex_file=".agents/plugins/marketplace.json"
readme_file="README.md"

if [ ! -f "$claude_file" ]; then
  echo "No $claude_file found in $repo_root" >&2
  exit 1
fi

command -v jq >/dev/null || { echo "jq is required" >&2; exit 1; }

# Shallow-fetch one commit into a throwaway repo, checked out at FETCH_HEAD.
# Prints the temp dir path, or nothing on failure. Caller must rm -rf it.
fetch_commit() {
  local url="$1" sha="$2" tmp
  tmp="$(mktemp -d)"
  if git -C "$tmp" init -q >/dev/null 2>&1 \
     && git -C "$tmp" fetch -q --depth 1 "$url" "$sha" >/dev/null 2>&1 \
     && git -C "$tmp" checkout -q FETCH_HEAD >/dev/null 2>&1; then
    echo "$tmp"
  else
    rm -rf "$tmp"
  fi
}

resolve_url() {
  # $1: source object (jq -c)
  jq -r 'if .source == "github" then "https://github.com/" + .repo + ".git" else .url end' <<<"$1"
}

latest_sha() {
  local url="$1" ref="$2"
  if [ -n "$ref" ] && [ "$ref" != "null" ]; then
    git ls-remote "$url" "$ref" | cut -f1 | head -1
  else
    git ls-remote "$url" HEAD | cut -f1
  fi
}

# README.md's plugin table has one row per plugin, ending in "| <version> |".
# Rewrite that trailing cell for the row naming $1.
update_readme_version() {
  local name="$1" version="$2"
  [ -f "$readme_file" ] || return 0
  sed -i.bak -E "/\[\`?${name}\`?\]/ s/\| [^|]+ \|\$/| ${version} |/" "$readme_file"
  rm -f "${readme_file}.bak"
}

names="$(jq -r '.plugins[] | select(.source | type == "object") | select(.source.source == "url" or .source.source == "github" or .source.source == "git-subdir") | .name' "$claude_file")"

if [ -z "$names" ]; then
  echo "No remote-ref plugins found in $claude_file"
  exit 0
fi

while IFS= read -r name; do
  entry="$(jq -c --arg n "$name" '.plugins[] | select(.name == $n)' "$claude_file")"
  source_obj="$(jq -c '.source' <<<"$entry")"
  url="$(resolve_url "$source_obj")"
  ref="$(jq -r '.ref // empty' <<<"$source_obj")"
  old_sha="$(jq -r '.sha' <<<"$source_obj")"
  subdir="$(jq -r 'if .source == "git-subdir" then .path else "." end' <<<"$source_obj")"

  new_sha="$(latest_sha "$url" "$ref")"
  if [ -z "$new_sha" ]; then
    echo "== $name: could not resolve latest ref from $url =="
    echo
    continue
  fi

  old_clone="$(fetch_commit "$url" "$old_sha")"
  old_subject="$([ -n "$old_clone" ] && git -C "$old_clone" log -1 --format=%s || true)"

  if [ "$old_sha" = "$new_sha" ]; then
    echo "== $name: up to date =="
    echo "   ${old_sha:0:12} $old_subject"
    rm -rf "$old_clone"
  else
    new_clone="$(fetch_commit "$url" "$new_sha")"
    new_subject="$([ -n "$new_clone" ] && git -C "$new_clone" log -1 --format=%s || true)"
    new_version="$([ -n "$new_clone" ] && jq -r '.version // empty' "$new_clone/$subdir/.claude-plugin/plugin.json" 2>/dev/null || true)"
    old_version="$(jq -r '.version // empty' <<<"$entry")"

    echo "== $name: updated =="
    echo "   before: ${old_sha:0:12} $old_subject"
    echo "   after:  ${new_sha:0:12} $new_subject"
    if [ -n "$new_version" ] && [ "$new_version" != "$old_version" ]; then
      echo "   version: $old_version -> $new_version"
    fi
    rm -rf "$old_clone" "$new_clone"

    tmp="$(mktemp)"
    jq --arg n "$name" --arg sha "$new_sha" --arg v "$new_version" \
      '(.plugins[] | select(.name == $n) | .source.sha) = $sha
       | if $v != "" then (.plugins[] | select(.name == $n) | .version) = $v else . end' \
      "$claude_file" >"$tmp" && mv "$tmp" "$claude_file"

    if [ -f "$codex_file" ] && jq -e --arg n "$name" '.plugins[] | select(.name == $n)' "$codex_file" >/dev/null 2>&1; then
      tmp="$(mktemp)"
      jq --arg n "$name" --arg sha "$new_sha" \
        '(.plugins[] | select(.name == $n) | .source.sha) = $sha' \
        "$codex_file" >"$tmp" && mv "$tmp" "$codex_file"
    fi

    if [ -n "$new_version" ] && [ "$new_version" != "$old_version" ]; then
      update_readme_version "$name" "$new_version"
    fi
  fi
  echo
done <<<"$names"

echo "Pinned refs (and versions, where changed) updated in the working tree, not committed."
echo "Review with: git diff -- $claude_file $codex_file $readme_file"
echo "Commit with: git add $claude_file $codex_file $readme_file && git commit"

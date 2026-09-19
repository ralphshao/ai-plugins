#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

claude_file=".claude-plugin/marketplace.json"
codex_file=".agents/plugins/marketplace.json"

if [ ! -f "$claude_file" ]; then
  echo "No $claude_file found in $repo_root" >&2
  exit 1
fi

command -v jq >/dev/null || { echo "jq is required" >&2; exit 1; }

# Fetch one commit's subject line via a throwaway shallow fetch. Prints "" on failure.
commit_subject() {
  local url="$1" sha="$2" tmp
  tmp="$(mktemp -d)"
  if git -C "$tmp" init -q >/dev/null 2>&1 \
     && git -C "$tmp" fetch -q --depth 1 "$url" "$sha" >/dev/null 2>&1; then
    git -C "$tmp" log -1 --format=%s FETCH_HEAD 2>/dev/null
  fi
  rm -rf "$tmp"
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

  new_sha="$(latest_sha "$url" "$ref")"
  if [ -z "$new_sha" ]; then
    echo "== $name: could not resolve latest ref from $url =="
    echo
    continue
  fi

  old_subject="$(commit_subject "$url" "$old_sha")"

  if [ "$old_sha" = "$new_sha" ]; then
    echo "== $name: up to date =="
    echo "   ${old_sha:0:12} $old_subject"
  else
    new_subject="$(commit_subject "$url" "$new_sha")"
    echo "== $name: updated =="
    echo "   before: ${old_sha:0:12} $old_subject"
    echo "   after:  ${new_sha:0:12} $new_subject"

    tmp="$(mktemp)"
    jq --arg n "$name" --arg sha "$new_sha" \
      '(.plugins[] | select(.name == $n) | .source.sha) = $sha' \
      "$claude_file" >"$tmp" && mv "$tmp" "$claude_file"

    if [ -f "$codex_file" ] && jq -e --arg n "$name" '.plugins[] | select(.name == $n)' "$codex_file" >/dev/null 2>&1; then
      tmp="$(mktemp)"
      jq --arg n "$name" --arg sha "$new_sha" \
        '(.plugins[] | select(.name == $n) | .source.sha) = $sha' \
        "$codex_file" >"$tmp" && mv "$tmp" "$codex_file"
    fi
  fi
  echo
done <<<"$names"

echo "Pinned refs updated in the working tree, not committed."
echo "Review with: git diff -- $claude_file $codex_file"
echo "Commit with: git add $claude_file $codex_file && git commit"

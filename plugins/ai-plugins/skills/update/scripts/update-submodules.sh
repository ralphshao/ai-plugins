#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

if [ ! -f .gitmodules ]; then
  echo "No .gitmodules found in $repo_root" >&2
  exit 1
fi

git submodule sync --recursive >/dev/null

git config --file .gitmodules --get-regexp '\.path$' | awk '{print $2}' | while read -r path; do
  name="$(basename "$path")"
  old_sha="$(git -C "$path" rev-parse HEAD)"
  old_subject="$(git -C "$path" log -1 --format=%s "$old_sha")"

  git submodule update --remote "$path" >/dev/null

  new_sha="$(git -C "$path" rev-parse HEAD)"
  new_subject="$(git -C "$path" log -1 --format=%s "$new_sha")"

  if [ "$old_sha" = "$new_sha" ]; then
    echo "== $name: up to date =="
    echo "   ${old_sha:0:12} $old_subject"
  else
    echo "== $name: updated =="
    echo "   before: ${old_sha:0:12} $old_subject"
    echo "   after:  ${new_sha:0:12} $new_subject"
  fi
  echo
done

echo "Submodule pointers updated in the working tree, not committed."
echo "Review with: git diff --submodule"
echo "Commit with: git add <plugins/...> && git commit"

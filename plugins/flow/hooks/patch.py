"""Paths named in a Codex apply_patch payload.

Codex sends file edits as tool_name "apply_patch" with the patch text in
tool_input.command, and no file_path. Each file the patch touches has a
header line: "*** Add File: p", "*** Update File: p", "*** Delete File: p",
and "*** Move to: p" after an Update header that renames the file.
"""
import re

HEADER = re.compile(r"^\*\*\* (Add File|Update File|Delete File|Move to): (.+)$",
                    re.M)


def patch_paths(tool_input):
    """[(action, path)] for each header in the patch, in order."""
    text = (tool_input or {}).get("command") or ""
    return [(m.group(1), m.group(2).strip()) for m in HEADER.finditer(text)]

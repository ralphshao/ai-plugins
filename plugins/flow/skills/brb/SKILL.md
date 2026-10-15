---
name: brb
description: Keeps this session's prompt cache warm during a break, so the first turn back reads the cache instead of rewriting the whole context. Claude Code only.
argument-hint: "[duration, e.g. 90m, 2h; empty = one cache lifetime]"
disable-model-invocation: true
---

Arguments: `$ARGUMENTS`

flow's hooks do the work; you only confirm it. Reply in one or two lines,
then end your turn. Don't run tools.

- **Codex:** say `/brb` works only in Claude Code, and stop.
- **The duration doesn't parse** (not `<n>m`, `<n>h`, `<n>h<n>m`, or a
  number of minutes): say so, show those forms, and say nothing was armed.
- **Otherwise:** say the keepalive is armed for the duration given, or for
  one cache lifetime when none was given (60m on a 1h cache, 30m on 5m),
  plus grace. Add that any message cancels it, and that after it ends,
  Claude Code's own idle compaction handles the session.

While armed, flow wakes this session shortly before the cache expires with
a "flow /brb keepalive" reminder. Answer that reminder with only `ok`.

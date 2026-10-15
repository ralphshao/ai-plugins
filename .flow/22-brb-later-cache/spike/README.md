# brb spike (throwaway, removed with .flow/ before merge)

Run each test in a new session, then tell Claude the session ID (or let it
find the newest transcript).

1. CLI: `claude --plugin-dir <this folder>` in any scratch directory. Send
   one short prompt ("hi"), then leave the session alone for ~70s.
2. Desktop app: same, with this folder loaded as a plugin directory.
3. Draft test (CLI): repeat 1, but type a draft without sending during the 60s.

Check: did the session wake on its own? Did it answer the Skill("compact")
request, and did compaction run? Then run `/usage` and note the
`Prompt cache (main)` line.

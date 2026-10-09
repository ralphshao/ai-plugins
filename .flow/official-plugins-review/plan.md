# Adopt ideas from claude-plugins-official into flow

## Goal
flow borrows the few ideas from Anthropic's official plugins that it lacks,
and the user knows which official plugins to install alongside it.

## Findings (claude-plugins-official @ b860d6f, 315 plugins)

Install alongside flow:
- `security-guidance`: per-turn LLM security review of the diff (async Stop
  hook) plus an agentic review on `git commit`. flow has no security-specific
  pass; its correctness lens only lists "security holes". Async rewake, so it
  doesn't fight `stop_gate.py`. Costs one Opus call per turn with changes.
- `plugin-dev`: `plugin-validator` and `skill-reviewer` agents and hook/skill
  authoring skills. Useful in this repo, which is a plugin marketplace.
- Already installed and used by flow's reviewers: `pyright-lsp`,
  `typescript-lsp`. Keep.
- Optional, on demand: `claude-security` (`/claude-security scan changes`)
  for security-sensitive Large tasks. Heavy (multi-agent workflow).

Skip (flow or an installed plugin already covers it):
- `feature-dev`: same explore/clarify/design/build/review arc as flow.
- `code-review`, `pr-review-toolkit`: flow's code-reviewer covers its
  categories (comments, type design, silent failures, tests); the validator
  beats 0-100 confidence scoring.
- `code-simplifier`: ponytail and built-in `/simplify`.
- `commit-commands`: `vcs-git`. `ralph-loop`: `stop_gate.py`.
- `hookify`, `claude-md-management`: overlap `retro`.

Not flow, but found: `context-mode` is enabled twice in
`~/.claude/settings.json` (`context-mode@context-mode` and
`context-mode@ai-plugins`), so its hooks run twice. Disable one.

## Acceptance criteria
- `deep-review` runs a `history` lens under `all` (and when named): a
  reviewer reads `git log`/`git blame` for the changed hunks and reports
  changes that undo an earlier fix or contradict the reason in a past
  commit message. It is skipped (and named as skipped in the report) when
  no changed hunk touches lines with prior history, e.g. a diff of only new
  files.
- `plan` on a Large task has two Plan subagents draft contrasting
  approaches (smallest change vs. cleanest structure). The interview asks
  one question per point where the drafts differ, each with a recommended
  answer, so the user can mix parts of both; answers land under
  `## Decisions`.
- `plan`'s exploration subagent returns the key files to read, and the
  main agent reads them before the interview.
- `tests/flow` passes.

## Seams under test
- `tests/flow` (layout and hook tests) - catches: broken skill frontmatter,
  layout drift / misses: whether agents follow the new prose.
- `plugins/flow/evals/large-feature` - catches: Large plan flow end to end
  / misses: history lens (no eval covers deep-review). Run by hand; not in
  the test command.

## Steps
- [ ] deep-review: add the `history` lens (argument word, brief, Perforce
  equivalent via `p4 annotate`/`p4 filelog` if guard allows, else git only).
- [ ] deep-review: skip the history lens when no changed hunk has prior
  history; report it as skipped.
- [ ] plan: Large tasks draft two contrasting approaches; the interview asks
  per difference.
- [ ] plan: exploration returns key files; read them.
- [ ] README: mention the history lens.

## Test command
`uv run --with pytest pytest tests/flow`

## Out of scope
- Installing plugins (user settings; commands given in chat).
- Prior-PR-comment lens from `code-review` (needs a new host operation).
- A security lens in deep-review (security-guidance covers it).
- Version bump of flow (only on the user's explicit go).

## Decisions
- History lens uses git log/blame only, not past PR comments - no new host
  operation needed; guard already allows `git blame`.
- History lens on by default, skipped when the diff has no prior history -
  user's choice; ~25-35% more deep-review cost only when history exists.
- Contrasting approaches are mixed per difference, not picked whole - user
  likes parts of each.
- Contrasting approaches only for Large - Normal tasks rarely have two real
  designs; costs two subagents.
- README gets one line on the history lens under Skills - Q1, user said yes.

## Open questions
- [x] Q1 Mention the history lens in plugins/flow/README.md? - recommended: yes, one line under Skills - blocks: README step

## Status
Awaiting GATE 1

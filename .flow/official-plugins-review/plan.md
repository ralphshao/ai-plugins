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
- deep-review keeps an UNSURE finding's reported severity
  (`Low (reported: High; UNSURE: <reason>)`), so flow's "UNSURE on a
  high-severity finding" escalation can fire.
- plan puts a "no test command" note under Decisions, not Status, and
  leaves `## Test command` with no lines (stop_gate runs its first line).
- deep-review names the files to Read for flow's "VCS and review host" and
  "Agent names on Codex" sections and for the reviewer output format, and
  says not to invoke `flow`.
- flow's README lists `andrej-karpathy-skills` and `ponytail` as optional
  companions: reviewers preload their skills when installed; Claude Code
  skips a missing preload with a debug-log warning.
- AGENTS.md "Validating changes" says to run `plugin-dev:plugin-validator`
  and `plugin-dev:skill-reviewer` on plugin changes.
- `plan` runs the interview until no decision is open for both Normal and
  Large; flow/SKILL.md's "Large adds" no longer lists the interview.
- A new ADR supersedes ADR 0001's "Large adds a full interview".
- GATE 1 shows Goal, Acceptance criteria, Seams, Steps, Test command, Out
  of scope, and Decisions.
- deep-review's errors-lens trigger drops `?.` and `?? ` and says to scan
  the `+` lines of the diff output (not "Grep").
- The smell baseline lives in `deep-review/references/smell-baseline.md`;
  the standards brief passes its path instead of pasting it.
- deep-review `allowed-tools` adds `git remote get-url`, `gh auth status`,
  `git fetch origin:*` (replacing `git fetch origin pull/*`), `p4 tickets`,
  `p4 login -s`. Not `curl`.
- Each hook's `commandWindows` uses the `py -3` launcher when present and
  falls back to `python`, and passes the script's exit code through
  unchanged (guard.py's exit 2 must still block).
- flow re-sizes at three points besides the start: after exploration
  (before drafts and interview), at GATE 1 against the written plan, and
  upward-only mid-edit on a Trivial task that turns out to change behavior
  (switch to Normal, run `start`). Never down to Trivial once a branch and
  brief exist. Each change updates `Size:` in brief.md and adds a reason
  under Decisions. GATE 1 shows the size.
- deep-review runs a `security` lens (argument word `security`, and under
  `all`) only when the diff's `+` lines touch a trust boundary: auth, shell
  or exec, SQL, file paths, deserialization, HTML output, or secrets. It
  reports only security findings, as Correctness, validated like the rest.
  It runs on `flow:strong-reviewer`.
- `flow:correctness-reviewer` is renamed `flow:strong-reviewer`
  (`flow-strong-reviewer` on Codex) everywhere: agent file, guard.py's
  reviewer set, deep-review, flow, README, tests. guard.py keeps it
  read-only; Codex's stale `flow-correctness-reviewer.toml` is removed by
  codex_agents.py's existing cleanup.
- `tests/flow` passes.

## Seams under test
- `tests/flow/test_layout.py` commandWindows check - catches: hook entries
  drifting from the agreed Windows form / misses: real cmd.exe behavior
  (no Windows host runs hooks through cmd; ADR 0008 accepts that gap).
- `tests/flow` (layout and hook tests) - catches: broken skill frontmatter,
  layout drift / misses: whether agents follow the new prose.
- `plugins/flow/evals/large-feature` - catches: Large plan flow end to end
  / misses: history lens (no eval covers deep-review). Run by hand; not in
  the test command.

## Steps
- [x] deep-review: add the `history` lens (argument word, brief; Perforce
  via `p4 annotate`/`p4 filelog`).
- [x] deep-review: skip the history lens when no changed hunk has prior
  history; report it as skipped.
- [ ] plan: Large tasks draft two contrasting approaches; the interview asks
  per difference.
- [x] plan: exploration returns key files; read them.
- [x] deep-review: keep reported severity on UNSURE findings.
- [x] plan: no-test-command note goes under Decisions; Test command left empty.
- [x] deep-review: name sibling files to Read instead of "the flow skill".
- [ ] README: mention the history and security lenses; list optional companion plugins.
- [ ] plan + flow skills: Normal interview runs until no decision is open.
- [ ] docs/adr: new ADR superseding ADR 0001's interview split.
- [x] plan: GATE 1 shows the full plan sections.
- [x] deep-review: narrow the errors-lens trigger.
- [x] deep-review: move the smell baseline to references/.
- [x] deep-review: allowed-tools additions.
- [x] Rename correctness-reviewer -> strong-reviewer: update test_guard.py
  and test_codex_agents.py first (red), then agent, guard.py, skills, README.
- [x] deep-review: conditional `security` lens on `flow:strong-reviewer`.
- [ ] hooks.json: `py -3` with `python` fallback on Windows; update
  test_layout.py's commandWindows check first (red), then hooks.json.
  New ADR if it changes ADR 0008's stated Windows command.
- [ ] flow + plan skills: re-size after exploration and at GATE 1; Trivial
  switches to Normal on a behavior change; never down to Trivial.
- [ ] AGENTS.md: plugin-dev validator and skill-reviewer under Validating changes.
- [ ] Bump flow 0.2.4 -> 0.2.5 (patch) in plugins/flow/.claude-plugin/plugin.json,
  plugins/flow/.codex-plugin/plugin.json, .claude-plugin/marketplace.json,
  and the root README table; last build step.
- [ ] Before ship: run `plugin-dev:skill-reviewer` on edited skills and
  `plugin-dev:plugin-validator` on plugins/flow; fix what applies.

## Test command
`uv run --with pytest pytest tests/flow`

## Out of scope
- Prior-PR-comment lens from `code-review` (needs a new host operation).

## Decisions
- History lens uses git log/blame only, not past PR comments - no new host
  operation needed; guard already allows `git blame`.
- History lens on by default, skipped when the diff has no prior history -
  user's choice; ~25-35% more deep-review cost only when history exists.
- Contrasting approaches are mixed per difference, not picked whole - user
  likes parts of each.
- Contrasting approaches only for Large - Normal tasks rarely have two real
  designs; costs two subagents.
- `plugin-dev` enabled at project scope via committed `.claude/settings.json` - user asked; installed from the official marketplace at b860d6f.
- Companion skills stay soft preloads, not plugin.json `dependencies` -
  dependencies are hard (flow stops loading without them) and need
  cross-marketplace allowlisting; a missing preload is only skipped.
- Normal interview matches Large (rounds until nothing is open) - user
  chose it over capping at one round; avoids guessed defaults. Costs
  Normal 1-2 extra rounds before GATE 1.
- `curl -K -` stays out of allowed-tools - pre-approving curl allows
  network calls without a prompt; Swarm fetches keep prompting.
- Windows `py -3` fallback must not rerun the script after a non-zero
  exit (a plain `py ... || python ...` would rerun guard.py after it
  blocks). If cmd.exe has no single-line form that does this, escalate.
- Bump flow to 0.2.5 as the last build step - Q2, user said yes.
- Re-size only after exploration, at GATE 1, and Trivial-upward - build
  scope growth already escalates; ship and resume add no new facts.
- No ADR for re-sizing - ADR 0001 sets the start-time sizing and doesn't
  forbid later checks; reversible prose change.
- Task re-sized Normal -> Large at GATE 1 - scope grew to deep-review,
  plan, flow, hooks, a test, new ADRs and a version bump. Ship adds the
  `flow:tester` pass.
- Perforce history lens uses `p4 annotate`/`p4 filelog` - guard.py's
  P4_READ already allows both.
- Contrasting drafts use `Plan` subagents in Claude Code and `explorer` in
  Codex - Codex has no Plan type; matches how plan names Explore/explorer.
- Re-size line format `Size: <old> -> <new> - <reason>` - existing eval
  graders match `Size:\W{0,4}<size>` on the first size, so they keep
  passing; no new evals in this change.
- One PR for all steps - user's choice; sole reviewer, commits per step
  keep history readable.
- Task started under flow 0.1.0; brief backfilled with 0.2.4's VCS, host,
  and Isolation lines after the user updated - state matches 0.2.4 now.
- No `security-guidance` - user finds it too heavy (per-turn Opus review,
  commit reviews, SDK install at session start).
- Conditional security lens instead of security-guidance - Q3, user said
  yes; costs one reviewer only on diffs touching a trust boundary.
- Security lens runs on the stronger-model reviewer - user chose B; a
  missed vulnerability is the costliest miss, and the trigger bounds cost.
- Rename correctness-reviewer to strong-reviewer - user chose it; the agent
  now serves two lenses, so a topic name misleads. No model in the name:
  Codex runs it on GPT.
- Keep 0.2.5 despite the rename - user's call after the semver note.
- History lens skip test: diff has no `-` lines (only additions) - the
  orchestrator can read that from the diff without running blame; an
  added-only diff can't undo an earlier fix.
- README gets one line on the history lens under Skills - Q1, user said yes.

## Open questions
- [x] Q1 Mention the history lens in plugins/flow/README.md? - recommended: yes, one line under Skills - blocks: README step
- [x] Q2 Bump flow to 0.2.5 as the last build step? - recommended: yes - blocks: version step
- [x] Q3 Add a conditional `security` lens to deep-review, run only when the diff's `+` lines touch a trust boundary (auth, shell/exec, SQL, file paths, deserialization, HTML output, secrets), like the errors lens? - recommended: yes - blocks: none (would add one step)

## Status
Approved - building

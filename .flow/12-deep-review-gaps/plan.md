# deep-review: report lenses that didn't run, and pass reference sources to reviewers

## Goal
A deep-review report never reads as complete when a lens or validator didn't run, and reviewers and validators get the same reference sources (ADRs, local clones, docs) to check findings against.

## Acceptance criteria
- Step 3 and step 5 say: if a subagent can't start, retry once; if it still fails, record it as not run.
- The report's opening line lists lenses run and lenses not run; findings whose validator didn't run are kept, marked Likely and "not validated".
- "No issues found" appears only when every selected lens ran and every validator ran.
- Step 2 gathers **References**: ADRs in the repo's ADR folder that mention a changed file or module, plus local clones or docs of external systems named in the arguments, intent, spec, or standards files. "none" if empty.
- The context block has a `References:` line, and step 5 passes it to the validators.

## Seams under test
- None automatable: the change is skill prose. Verified by reading the diff against the acceptance criteria and by the deep-review pass in ship.

## Steps
- [x] Add References to step 2, the context block, and the validator inputs in step 5.
- [x] Add retry-once and not-run handling to steps 3 and 5, and to the report in step 6.

## Test command
`python3 -m pytest`

## Out of scope
- Changing the agent definitions in `plugins/flow/agents/`.
- Auto-discovering clones outside the paths the user or the review text names.
- Version bump.

## Decisions
- Skipped the Explore subagent: the change is one file, already read in full - nothing else references these sections.
- References discovery is limited to the repo's ADR folder plus paths named in arguments, intent, spec, or standards files - scanning the disk for clones is guesswork; the orchestrator can't know which clone is relevant.
- A validator that fails twice keeps its file's findings as Likely "not validated", not dropped - dropping would hide findings the reviewers did make.
- "Can't start" means the launch is refused or errors, not a reviewer returning zero findings.

- Review F1 (UNSURE, Low): a subagent that starts but returns no report or no verdicts also counts as not run - fixing it serves #12's goal that a partial review never reads as full.
- Review F4 (pre-existing, CONFIRMED): validators also get the `Read files:` line - one clause in a sentence this change already edits.
- Review F2, F3 (Readability): refuted by the validator, not changed.

## Open questions

## Status
Approved - building

---
name: tdd
description: Test-driven development in red-green slices at agreed seams. Use when building a feature or fixing a bug test-first, or when the user mentions TDD or red-green-refactor.
---

Adapted from the `tdd` skill in mattpocock/skills (MIT).

## Seams

A seam is the public interface where a test observes behavior without
reaching inside. Test only at agreed seams: in a flow task, the ones listed
under `## Seams under test` in `plan.md`. Outside flow, propose the seams
with a one-line note on what each catches and misses, and confirm before
writing tests. A test needed at a seam nobody agreed on is a plan change:
escalate it.

## The loop

One slice at a time:

1. **Red:** write one failing test at a seam. Run it and see it fail for the
   right reason.
2. **Green:** write the least code that passes it. Run it.
3. Commit, and move to the next slice.

Refactoring is not part of the loop; it belongs to review.

## Good tests

- Test behavior through the public interface. A test that breaks on a
  refactor that kept behavior was testing internals.
- Expected values come from an independent source: a literal, a worked
  example, the spec. Never recompute them the way the code does
  (`expect(add(a, b)).toBe(a + b)` passes by construction).
- Mock only at system boundaries (network, clock, filesystem when needed),
  not your own collaborators.
- Don't write all tests first and all code after. Each test should respond
  to what the last slice taught you.
- Match the repo's existing test style, helpers, and layout.

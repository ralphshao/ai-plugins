---
name: pr-body
description: The shape of a code review description (pull request, Swarm review, or changelist description) - a minimal summary visual, before/after evidence, and a merge-danger call. Use when writing or updating one.
---

Adapted from the `pr` skill in mattpocock/skills (MIT), itself credited to
Humanlayer's `show-me`.

Template:

```markdown
## Summary

<the smallest visual that makes the change clear>

## Evidence

- **Before:** <failing test, output, or screenshot>
- **After:** <passing test, output, or screenshot>

## Merge danger

**Door:** <one-way | two-way>
**Blast radius:** <one word or short phrase>
<one or two lines on what breaks if this is wrong, when not obvious>

## Decisions

- <decision> - <reason>

Closes #<n>
```

Rules:

- No preamble. Keep prose short.
- **Summary:** pick one form: pseudocode for logic, a call tree for control
  flow, a file tree for layout changes, a short diff sketch for an API
  change. Don't restate the diff.
- **Evidence:** real output from this branch. A test that failed before and
  passes now is the best evidence.
- **Door:** one-way when merging is hard to undo (schema, data, public API,
  published artifacts); two-way otherwise.
- **Decisions:** from a flow plan, every decision made between the gates.
  Omit the section when there are none.
- `Closes #<n>` is the GitHub form; use the issue link the review host's
  `fetch-issue` names, and drop the line when there is no issue.

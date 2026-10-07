---
name: interview
description: Interview the user about a plan, design, or decision in rounds of numbered questions with recommended answers, until no decision is left open. Use when a plan has open decisions, or the user says "interview me", "grill me", or asks to stress-test an idea.
---

Adapted from the `grilling` skill in mattpocock/skills (MIT).

Map the decisions as a tree: each decision branches into the ones that
depend on it. The **frontier** is every open decision whose prerequisites
are settled.

## Rounds

Ask the whole frontier in one round, then wait for answers. Format:

```
**Q1 - <title>**: <question, with the options when there are several>
Recommended: <your answer, and why in one line>

**Q2 - <title>**: ...
Recommended: ...
```

- Word each question so "yes" accepts the recommendation.
- A question that depends on another one still open this round belongs to a
  later round.
- After each round, recompute the frontier from the answers and ask the next
  round.

## Facts versus decisions

Facts are yours to find: code, config, docs, tool output. Use a subagent to
look them up; never ask the user for something you can check. Only questions
downstream of a running lookup wait for it; ask the rest now.

Decisions are the user's. Put each one to them.

## Done

The interview ends when the frontier is empty. Summarize the decisions in
one list and confirm before acting on them.

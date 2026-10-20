---
max_turns: 60
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Agent]
---

/flow:flow add a `python3 -m calc divide 6 3` command that prints `6 / 3 = 2`. Leave dividing by zero as `divide` handles it today. The output and the usage message must also read naturally to a non-programmer.

---
name: setup
description: "Creates, shows, changes, or removes the weekly cloud scheduled task that runs memory-keeper:maintain. Run once, outside any project. Use for \"set up memory maintenance\", \"schedule memory maintenance\", or /memory-keeper:setup."
---

# Memory maintenance setup

Manages the scheduled task that runs the memory-keeper:maintain skill at account level, where it covers every project.

## Defaults

- **Prompt** (exactly): `Run the memory-keeper:maintain skill. If the skill isn't available, send a one-line SendUserMessage saying so and stop.`
- **Schedule:** weekly on Sunday, 8:45 AM in the user's local time zone. Use exactly this time; don't shift it.
- **Name:** `Account memory maintenance`.

## Workflow

1. **Check the context.** Project instructions present in this conversation → say setup must run outside a project and stop.
2. **Find the time zone.** Use the user's IANA time zone from the conversation context. If it isn't there, ask once.
3. **Find the scheduling tool.** Use a scheduled-task tool that runs in the cloud, with no need for the user's computer to be on (for example Routines: `create_trigger`, `list_triggers`, `update_trigger`, `delete_trigger`; load with ToolSearch if deferred). Never use a tool that runs on the user's machine. If no cloud scheduling tool is available, say so and stop.
4. **Look for an existing task** outside any project whose prompt runs memory-keeper:maintain. Never create a second one. Ignore leftover per-project tasks; tell the user they stop at the project guard and can be deleted.
5. **Act on the request:**
   - **Set up** (default): no task yet → show the name, schedule, time zone, and prompt, and create it after the user confirms. A task exists → show it and ask whether to change it.
   - **Show:** report the task's name, schedule, time zone, next run, and last run status.
   - **Change:** apply the schedule, time or name change the user asks for, keeping the task. Never change the prompt.
   - **Remove:** delete the task after the user confirms.
6. **Report** in one or two lines what changed and when the next run is.

Write cron in the user's local time with a time zone prefix, e.g. `CRON_TZ=America/New_York 45 8 * * 0`.

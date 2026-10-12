---
name: setup
description: "Creates, shows, changes, or removes the weekly cloud scheduled task that runs memory-keeper:maintain. Run once outside any project for account mode, and once inside each project that should get its own run. Use for \"set up memory maintenance\", \"schedule memory maintenance\", or /memory-keeper:setup."
---

# Memory maintenance setup

Manages the scheduled task that runs the memory-keeper:maintain skill in the current context: account mode outside a project, project mode inside one. The task's prompt is the same in both; where it runs decides the mode.

## Defaults

- **Prompt** (exactly): `Run the memory-keeper:maintain skill. If the skill isn't available, send a one-line SendUserMessage saying so and stop.`
- **Schedule:** weekly on Sunday, 8:45 AM for account mode, 9:00 AM for project mode, in the user's local time zone. Use exactly these times; don't shift them.
- **Name:** `Memory maintenance (account)` or `Memory maintenance (<project name>)`.

## Workflow

1. **Pick the mode.** Project instructions present in this conversation → project mode. Otherwise → account mode.
2. **Find the time zone.** Use the user's IANA time zone from the conversation context. If it isn't there, ask once.
3. **Find the scheduling tool.** Use a scheduled-task tool that runs in the cloud, with no need for the user's computer to be on (for example Routines: `create_trigger`, `list_triggers`, `update_trigger`, `delete_trigger`; load with ToolSearch if deferred). Never use a tool that runs on the user's machine. If no cloud scheduling tool is available, say so and stop.
4. **Look for an existing task** in this context whose prompt runs memory-keeper:maintain. Never create a second one.
5. **Act on the request:**
   - **Set up** (default): no task yet → show the name, schedule, time zone, and prompt, and create it after the user confirms. A task exists → show it and ask whether to change it.
   - **Show:** report the task's name, schedule, time zone, next run, and last run status.
   - **Change:** apply the schedule or time change the user asks for, keeping the task. Never change the prompt.
   - **Remove:** delete the task after the user confirms.
6. **Report** in one or two lines what changed and when the next run is.

Write cron in the user's local time with a time zone prefix, e.g. `CRON_TZ=America/New_York 45 8 * * 0` for account mode and `CRON_TZ=America/New_York 0 9 * * 0` for project mode.

---
name: ticktick
description: "Use when managing the user's TickTick tasks and reminders."
version: 1.0.0
platforms: [macos, linux]
metadata:
  hermes:
    tags: [ticktick, tasks, reminders, todo, calendar]
---

# TickTick integration

The user's task manager is TickTick. API token is stored in `~/.hermes/.env` as `TICKTICK_API_TOKEN` (never print it, never paste it into chat).

## Commands (run with the hermes venv python)

All commands print JSON to stdout.

```bash
P=/Users/vostrikovaleksand/.hermes/skills/productivity/ticktick/scripts/tick.py
py=$HOME/.hermes/hermes-agent/venv/bin/python3   # or plain python3 (stdlib only)

# Lists
$py $P projects
# Create task (all fields optional except title)
$py $P add --title "Купить молоко" --list "Дом" --due "2026-09-09T18:00:00+03:00" --remind 30 --priority 3 --note "2 пакета"
# List tasks: default = today's window
$py $P tasks --list "Дом" --from "2026-09-09T00:00:00+03:00" --to "2026-09-10T00:00:00+03:00"
$py $P get <taskId>
$py $P complete <taskId>
$py $P delete <taskId>
# Reminder-check (cron): tasks due within N minutes, deduped via state file
$py $P remind --within 90
# Morning digest text (cron)
$py $P digest
```

## Workflow rules

- **Creating a task from chat/voice**: parse the user's natural language (Russian). Resolve relative dates with the LOCAL timezone of the Mac (`python3 -c "import datetime; print(datetime.datetime.now().astimezone())"` shows offset; confirm city with the user once). Emit ISO with offset, e.g. `2026-09-09T18:00:00+03:00`. Confirm the parsed task with the user in one line BEFORE creating (show title, list, date/time). If due time is absent, default 09:00. If no list is named, use the configured default (currently: ask user / Личный until stated otherwise).
- **Priority words**: высокий/важно = 5, средний = 3, низкий = 1, none = 0.
- **`--remind N`** = N minutes before due; TickTick fires its own native notification, AND the Hermes cron reminder job (`remind --within`) covers Telegram reminders. Reminder output must be deduped: state file `~/.hermes/ticktick_reminded.json`.
- **complete**: mark done. Prefer fetching by task id; match by unique title substring as fallback.
- **Never** log or echo the token.
- Timezones: Mac is MSK (UTC+3) unless stated otherwise — compute ISO offsets from the Mac's local tz, not from guesswork.
- Completed tasks carry `status` != 0 (empirically 2); unfinished have status 0.

## Project map (names may include emoji — match by substring, emoji-insensitive)

See `assets/projects.json` for name→id map; refresh by running `projects` (fetch is live each run anyway).

## Cron jobs (owned by Hermes)

1. Morning digest: daily at 09:00 local → runs `digest`, delivers text to the user's Telegram DM.
2. Reminder checker: every 30 min → runs `remind --within 90`, delivers any reminder lines.

Do not create duplicate cron jobs; check existing ones first.

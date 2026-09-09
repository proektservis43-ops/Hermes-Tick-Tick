---
name: openwhispr
description: "Use when extracting meaning from OpenWhispr dictations."
version: 1.0.0
platforms: [macos]
metadata:
  hermes:
    tags: [openwhispr, dictation, transcription, voice]
---

# OpenWhispr (dictation) integration

OpenWhispr is the user's local dictation/meeting-notes app. Data stays on the Mac:

- SQLite DB: `~/Library/Application Support/open-whispr/transcriptions.db` (tables: `transcriptions`, `notes`, `folders`, `snippets`). Read-only access is safe while the app runs (WAL).
- Local bridge API: port/token in `~/.openwhispr/cli-bridge.json` (token is a secret — never print it). Official CLI `@openwhispr/cli` talks to it; local backend needs no cloud key.

## Read recent dictations

```bash
python3 ~/.hermes/skills/productivity/openwhispr/scripts/ow.py recent   # last 10 transcriptions, JSON
python3 ~/.hermes/skills/productivity/openwhispr/scripts/ow.py notes    # last 10 notes, JSON
```

## Workflow: dictation -> meaning -> TickTick tasks

1. User dictates something in OpenWhispr, then tells me to extract it.
2. Run `ow.py recent` (or `notes`) and take the NEWEST item(s) not yet processed.
3. Parse the text myself (Russian): extract tasks, decisions, dates, project hints. Split multi-item dictations into separate tasks.
4. Confirm the plan with the user in ONE message (list tasks + TickTick list + dates) BEFORE creating.
5. Create via the ticktick skill scripts (`tick.py add ...`), then confirm done.
6. Optionally tag the processed transcription id in `~/.hermes/openwhispr_processed.json` to avoid re-processing.

## Rules

- Never echo the bridge token.
- Respect privacy: the DB may hold personal/business audio text — only surface what the user asked about.
- Dictations are drafts: preserve meaning, fix disfluencies, do not invent specifics.

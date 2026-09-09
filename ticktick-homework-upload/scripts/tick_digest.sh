#!/bin/bash
# TickTick morning digest — stdout is delivered verbatim by cron.
exec python3 "$HOME/.hermes/skills/productivity/ticktick/scripts/tick.py" digest

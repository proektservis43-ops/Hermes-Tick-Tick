#!/bin/bash
# TickTick deadline checker — prints reminder lines only when something is due;
# empty stdout = cron sends nothing (watchdog pattern).
exec python3 "$HOME/.hermes/skills/productivity/ticktick/scripts/tick.py" remind --within 90

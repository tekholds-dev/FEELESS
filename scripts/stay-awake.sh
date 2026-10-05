#!/usr/bin/env bash
# 😴 Overnight mode (macOS): keeps the Mac awake AND every FEELESS backend service up (keep-alive restarts any that dies).
# Keep the Mac PLUGGED IN. Run in its own Terminal tab:  bash scripts/stay-awake.sh      Stop: Ctrl+C (the Mac can sleep again).
# Closing the lid still sleeps a MacBook unless an external display is attached — leave the lid open.
root="$(cd "$(dirname "$0")/.." && pwd)"
echo "😴 FEELESS overnight: Mac stays awake, services auto-restart. Log: /tmp/feeless-keepalive.log · Ctrl+C to stop."
exec caffeinate -dimsu bash "$root/scripts/keep-alive.sh" 2>&1 | tee -a /tmp/feeless-keepalive.log

#!/usr/bin/env bash
# Wait, with no agent in the loop, until the coordinator has something to act on.
#
# Usage:
#   watch.sh <state-file> [interval-seconds]
#
# Run it with Bash run_in_background. Every interval it may run:
#   - every 5th interval: poll-linear.py <state-file> (one headless Haiku call
#     that reads each ticket's Jaidev status comment) → prints Status/Timeline changes
#   - every 3rd interval: poll.py <state-file> (PRs, CI, merges) → prints its events
# It exits after printing, so the harness wakes the coordinator once per batch
# of events. Restart it after handling them.
set -u

STATE=$1
INTERVAL=${2:-60}
DIR=$(cd "$(dirname "$0")" && pwd)
LINEAR_EVERY=5
GH_EVERY=3

i=0
while true; do
  if [ $((i % LINEAR_EVERY)) -eq 0 ]; then
    out=$(python3 "$DIR/poll-linear.py" "$STATE" 2>&1)
    if [ -n "$out" ]; then
      echo "$out"
      exit 0
    fi
  fi

  if [ $((i % GH_EVERY)) -eq 0 ]; then
    out=$(python3 "$DIR/poll.py" "$STATE" 2>&1 | grep -v -e '^LINEAR ' -e '^NO EVENTS$')
    if [ -n "$out" ]; then
      echo "$out"
      exit 0
    fi
  fi

  i=$((i + 1))
  sleep "$INTERVAL"
done

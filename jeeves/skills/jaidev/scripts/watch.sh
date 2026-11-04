#!/usr/bin/env bash
# Wait, with no model in the loop, until the coordinator has something to act on.
#
# Usage:
#   watch.sh <state-file> <events-file> <poller-state-file> [interval-seconds]
#
# Run it with Bash run_in_background. Every interval it checks, in order:
#   1. new lines in <events-file> (appended by the Haiku poller) → prints them
#   2. every 3rd interval, poll.py <state-file> (PRs, CI, merges) → prints its events
#   3. <poller-state-file> older than 15 min → prints "POLLER STALE <age>s"
# It exits after printing, so the harness wakes the coordinator once per batch
# of events. Restart it after handling them.
set -u

STATE=$1
EVENTS=$2
POLLER_STATE=$3
INTERVAL=${4:-60}
DIR=$(cd "$(dirname "$0")" && pwd)
OFFSET="$EVENTS.offset"
STALE_AFTER=900
GH_EVERY=3

touch "$EVENTS"
[ -f "$OFFSET" ] || echo 0 > "$OFFSET"

age_of() {
  python3 -c 'import os, sys, time; print(int(time.time() - os.path.getmtime(sys.argv[1])))' "$1"
}

i=0
while true; do
  seen=$(cat "$OFFSET")
  total=$(wc -l < "$EVENTS" | tr -d ' ')
  if [ "$total" -gt "$seen" ]; then
    tail -n +"$((seen + 1))" "$EVENTS"
    echo "$total" > "$OFFSET"
    exit 0
  fi

  if [ $((i % GH_EVERY)) -eq 0 ] && [ -f "$STATE" ]; then
    out=$(python3 "$DIR/poll.py" "$STATE" 2>&1 | grep -v -e '^LINEAR ' -e '^NO EVENTS$')
    if [ -n "$out" ]; then
      echo "$out"
      exit 0
    fi
  fi

  if [ -f "$POLLER_STATE" ]; then
    age=$(age_of "$POLLER_STATE")
    if [ "$age" -gt "$STALE_AFTER" ]; then
      echo "POLLER STALE ${age}s"
      exit 0
    fi
  fi

  i=$((i + 1))
  sleep "$INTERVAL"
done

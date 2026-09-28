#!/usr/bin/env python3
"""Render Jenkins build JSON as a markdown table with status icons.

Reads a Jenkins API object on stdin — either a `builds[...]` list response or a
single build object — and prints a markdown table. Pass the job's base URL as
argv[1] to turn each build number into a clickable link.

    curl ... "$JENKINS_URL/job/<job>/api/json?tree=builds%5Bnumber,result,duration,timestamp%5D%7B0,10%7D" \
      | python3 scripts/build-table.py "$JENKINS_URL/job/<job>"
"""
import json, sys, time

ICON = {"SUCCESS": "✅", "FAILURE": "❌", "UNSTABLE": "⚠️", "ABORTED": "⛔", None: "⏳"}


def dur(ms):
    s = max(0, int(ms // 1000))
    return f"{s//60}m{s%60:02d}s" if s >= 60 else f"{s}s"


def started(ts):
    t = time.localtime(ts / 1000)
    return time.strftime("%-d %b ", t) + time.strftime("%-I:%M%p", t).lower()


d = json.load(sys.stdin)
base = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else ""
builds = d.get("builds", [d])

rows = []
for b in builds:
    result = b.get("result")
    # A build still running reports duration 0, so measure from its start.
    elapsed = b.get("duration") or (time.time() * 1000 - b["timestamp"])
    num = f"[#{b['number']}]({base}/{b['number']}/)" if base else f"#{b['number']}"
    rows.append(
        f"| {ICON.get(result, '❓')} {result or 'building'} | {num} "
        f"| {dur(elapsed)} | {started(b['timestamp'])} |"
    )

print("| Result | Build | Duration | Started |")
print("|---|---|---|---|")
print("\n".join(rows))

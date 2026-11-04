#!/usr/bin/env python3
"""Read each open ticket's Jaidev status comment with one headless Haiku call.

Usage:
  poll-linear.py <state-file> [list-comments-tool]

Runs `claude -p --model haiku` as a separate process, so no agent of the
coordinator's session stops or wakes. For each ticket in the state file that
is not merged, it reads Jaidev's status comment, compares the Status line
(without its live detail in brackets) and the last Timeline entry with
lastStatus and lastTimeline, stores the new values, and prints one line per
change that waits on the coordinator (a plan, a question, Blocked, PRs
created, Complete):

  ACC-1663 STATUS "Awaiting Plan Approval" TIMELINE "Plan v1 posted ($2.10) — awaiting approval"
  LINEAR POLL ERROR <message>        (the call or its JSON failed)

Changes while Jaidev works (Analyzing, Planning, Implementing, Addressing PR
Feedback) and Timeline entries the coordinator caused (Started by, Plan
approved by, Plan feedback received) update the state without a line. Prints nothing when
nothing changed. One call costs about $0.007 (measured 4 Nov 2026).
"""
import json
import subprocess
import sys
from pathlib import Path

DEFAULT_TOOL = "mcp__claude_ai_Linear__list_comments"
COORDINATOR_ENTRIES = ("Started by", "Plan approved by", "Plan feedback received")
# Jaidev is busy in these; the coordinator has nothing to do until it leaves them.
WORKING_STATUSES = {"Analyzing...", "Planning...", "Implementing...", "Addressing PR Feedback..."}


def status_key_of(status):
    """Drop the live detail in brackets, e.g. 'Planning... (Running: cat …)' → 'Planning...'."""
    return (status or "").split(" (")[0].strip()


def build_prompt(ticket_ids, tool):
    return (
        f"For each Linear issue in {json.dumps(ticket_ids)}, call {tool} with that issueId "
        "and limit 1. When that comment's body does not start with '**Jaidev — <ID>**', "
        "call it again with limit 3 and use the comment that does. Reply with only a JSON "
        'array, one object per issue: {"ticket": "<ID>", "status": "<text after **Status:**>", '
        '"timeline": "<last bullet under **Timeline**, without its timestamp>"}. Use null for '
        "status and timeline when the issue has no Jaidev status comment."
    )


def read_statuses(ticket_ids, tool):
    out = subprocess.run(
        ["claude", "-p", "--model", "haiku", "--allowedTools", tool,
         "--output-format", "json", build_prompt(ticket_ids, tool)],
        capture_output=True, text=True, timeout=240)
    if out.returncode != 0:
        raise RuntimeError((out.stderr or out.stdout).strip()[-200:])
    result = json.loads(out.stdout).get("result") or ""
    start, end = result.find("["), result.rfind("]")
    if start < 0 or end < start:
        raise RuntimeError(f"no JSON array in reply: {result[:120]}")
    return json.loads(result[start:end + 1])


def main(path, tool):
    state = json.loads(path.read_text())
    open_tickets = {k: v for k, v in state.get("tickets", {}).items() if not v.get("merged")}
    if not open_tickets:
        return
    try:
        rows = read_statuses(list(open_tickets), tool)
    except (RuntimeError, ValueError, subprocess.TimeoutExpired) as error:
        print(f"LINEAR POLL ERROR {str(error).splitlines()[0][:200]}")
        return
    lines = []
    for row in rows:
        ticket = open_tickets.get(row.get("ticket"))
        status, timeline = row.get("status"), row.get("timeline")
        if ticket is None or (status is None and timeline is None):
            continue
        status_key = status_key_of(status)
        if (status_key, timeline) == (ticket.get("lastStatus"), ticket.get("lastTimeline")):
            continue
        ticket["lastStatus"], ticket["lastTimeline"] = status_key, timeline
        if status_key in WORKING_STATUSES or (timeline or "").startswith(COORDINATOR_ENTRIES):
            continue
        lines.append(f'{row["ticket"]} STATUS "{status}" TIMELINE "{timeline}"')
    path.write_text(json.dumps(state, indent=2) + "\n")
    if lines:
        print("\n".join(lines))


if len(sys.argv) not in (2, 3):
    sys.exit(__doc__)
main(Path(sys.argv[1]), sys.argv[2] if len(sys.argv) == 3 else DEFAULT_TOOL)

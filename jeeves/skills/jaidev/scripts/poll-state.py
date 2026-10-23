#!/usr/bin/env python3
"""Read and update the per-ticket poll state file used by the Jaidev coordinator.

Usage:
  poll-state.py <state-file> get <ticket>
  poll-state.py <state-file> set <ticket> <field> <value>
  poll-state.py <state-file> init <ticket> <agent-id> <branch>

The state file holds {"parent": ..., "tickets": {<ticket>: {agent, branch,
lastJaidevCommentId, lastPrHead, lastReportedCiHead, mergedReported}}}.
A set value is read as JSON (true, false, null, a number) and falls back to a string.
"""
import json
import sys
from pathlib import Path

FIELDS = ("lastJaidevCommentId", "lastPrHead", "lastReportedCiHead", "mergedReported")


def main(argv):
    if len(argv) < 4:
        sys.exit(__doc__)
    path, action, ticket = Path(argv[1]), argv[2], argv[3]
    state = json.loads(path.read_text()) if path.exists() else {"tickets": {}}
    tickets = state.setdefault("tickets", {})
    if action == "get":
        print(json.dumps(tickets.get(ticket), indent=2))
        return
    if action == "init" and len(argv) == 6:
        tickets[ticket] = {"agent": argv[4], "branch": argv[5],
                           **{f: (False if f == "mergedReported" else None) for f in FIELDS}}
    elif action == "set" and len(argv) == 6:
        if ticket not in tickets:
            sys.exit(f"unknown ticket {ticket}; run init first")
        try:
            value = json.loads(argv[5])
        except json.JSONDecodeError:
            value = argv[5]
        tickets[ticket][argv[4]] = value
    else:
        sys.exit(__doc__)
    path.write_text(json.dumps(state, indent=2) + "\n")
    print(json.dumps(tickets[ticket]))


main(sys.argv)

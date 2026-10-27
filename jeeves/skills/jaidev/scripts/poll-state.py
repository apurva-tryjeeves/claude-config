#!/usr/bin/env python3
"""Read and update the per-ticket state file that poll.py and the coordinator share.

Usage:
  poll-state.py <state-file> init <ticket> <agent-id> <repo-dir>
  poll-state.py <state-file> get <ticket>
  poll-state.py <state-file> set <ticket> <field> <value>

Each ticket holds: agent, repoDir, color, prNumber, lastCiHead, lastTimeline,
merged. poll.py writes prNumber, lastCiHead and merged; the coordinator writes
color and lastTimeline. A set value is read as JSON (true, false, null, a
number) and falls back to a string.
"""
import json
import sys
from pathlib import Path


def main(argv):
    if len(argv) < 4:
        sys.exit(__doc__)
    path, action, ticket = Path(argv[1]), argv[2], argv[3]
    state = json.loads(path.read_text()) if path.exists() else {"tickets": {}}
    tickets = state.setdefault("tickets", {})
    if action == "get":
        print(json.dumps(tickets.get(ticket)))
        return
    if action == "init" and len(argv) == 6:
        tickets[ticket] = {"agent": argv[4], "repoDir": argv[5], "color": None,
                           "prNumber": None, "lastCiHead": None,
                           "lastTimeline": None, "merged": False}
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

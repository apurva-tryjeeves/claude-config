#!/usr/bin/env python3
"""One poll tick for the Jaidev coordinator: every GitHub check in one call.

Usage:
  poll.py <state-file>

For each ticket in the state file that is still open, reads its Jaidev PR
(branch jai-dev/<ticket-lowercase>) with gh, from the ticket's repoDir so gh
picks the right account. Updates the state file and prints only events:

  ACC-1634 PR opened #812 head=abc1234
  ACC-1634 CI passed head=abc1234     (printed once per head, when no check is pending)
  ACC-1634 MERGED #812
  LINEAR ACC-1636 last="Plan v1 posted"   (no PR yet: read its status comment)
  NO EVENTS                                (nothing else printed)
  ALL MERGED                               (every ticket merged: delete the cron)
"""
import json
import subprocess
import sys
from pathlib import Path

PENDING = {"IN_PROGRESS", "QUEUED", "PENDING", "WAITING", "REQUESTED", "EXPECTED"}
FAILED = {"FAILURE", "ERROR", "TIMED_OUT", "CANCELLED", "ACTION_REQUIRED", "STARTUP_FAILURE"}


def read_pr(ticket, repo_dir):
    out = subprocess.run(
        ["gh", "pr", "list", "--head", f"jai-dev/{ticket.lower()}", "--state", "all",
         "--json", "number,headRefOid,state,statusCheckRollup"],
        cwd=repo_dir, capture_output=True, text=True)
    if out.returncode != 0:
        return "error", out.stderr.strip().splitlines()[-1:] or ["gh failed"]
    prs = json.loads(out.stdout or "[]")
    return "ok", (prs[0] if prs else None)


def ci_result(checks):
    if not checks:
        return "pending"
    if any((c.get("status") or c.get("state") or "") in PENDING for c in checks):
        return "pending"
    if any((c.get("conclusion") or c.get("state") or "") in FAILED for c in checks):
        return "failed"
    return "passed"


def main(path):
    state = json.loads(path.read_text())
    tickets = state.get("tickets", {})
    lines = []
    for ticket, t in tickets.items():
        if t.get("merged"):
            continue
        status, pr = read_pr(ticket, t.get("repoDir", "."))
        if status == "error":
            lines.append(f"{ticket} gh error: {pr[0]}")
            continue
        if pr is None:
            lines.append(f'LINEAR {ticket} last="{t.get("lastTimeline") or ""}"')
            continue
        head = pr["headRefOid"][:7]
        if t.get("prNumber") != pr["number"]:
            t["prNumber"] = pr["number"]
            lines.append(f"{ticket} PR opened #{pr['number']} head={head}")
        if pr["state"] == "MERGED":
            t["merged"] = True
            lines.append(f"{ticket} MERGED #{pr['number']}")
            continue
        if pr["state"] == "CLOSED":
            t["merged"] = True
            lines.append(f"{ticket} CLOSED unmerged #{pr['number']}")
            continue
        ci = ci_result(pr.get("statusCheckRollup") or [])
        if ci != "pending" and t.get("lastCiHead") != head:
            t["lastCiHead"] = head
            lines.append(f"{ticket} CI {ci} head={head}")
    path.write_text(json.dumps(state, indent=2) + "\n")
    events = [l for l in lines if not l.startswith("LINEAR ")]
    if lines:
        print("\n".join(lines))
    if not events:
        print("NO EVENTS")
    if tickets and all(t.get("merged") for t in tickets.values()):
        print("ALL MERGED")


if len(sys.argv) != 2:
    sys.exit(__doc__)
main(Path(sys.argv[1]))

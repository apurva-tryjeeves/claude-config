"""Whole ticks with fake pollers and a fixed clock, plus the CLI commands."""

from __future__ import annotations

import contextlib
import io
import json
import shutil
import tempfile
import unittest
from collections.abc import Sequence
from datetime import datetime, timedelta
from pathlib import Path

from jaidev_watch import cli, policy, state_store
from jaidev_watch.ci_timing import load
from jaidev_watch.linear_poll import LinearPollError
from jaidev_watch.models import (
    CiTiming,
    GithubObservation,
    LinearObservation,
    Stage,
    TicketState,
    WaveState,
    parse_time,
)

WAVE2 = Path(__file__).resolve().parent / "fixtures" / "wave2-state.json"
TIMINGS = load()
REPO = "/x/ap-data-source-connector"


class FakePollers:
    """Records every call; Linear returns `status` unchanged unless told to fail."""

    def __init__(
        self, status: str = "Awaiting Plan Approval", timeline: str = "Plan v1 posted"
    ) -> None:
        self.status, self.timeline = status, timeline
        self.linear_calls: list[list[str]] = []
        self.github_calls: list[str] = []
        self.linear_error: str | None = None
        self.omit: set[str] = set()
        self.lowercase = False

    def read_linear(self, ticket_ids: Sequence[str]) -> Sequence[LinearObservation]:
        self.linear_calls.append(list(ticket_ids))
        if self.linear_error:
            raise LinearPollError(self.linear_error)
        return [
            LinearObservation(t.lower() if self.lowercase else t, self.status, self.timeline)
            for t in ticket_ids
            if t not in self.omit
        ]

    def read_github(
        self, ticket_id: str, repo_dir: Path, settles_on: Sequence[str]
    ) -> GithubObservation | None:
        self.github_calls.append(ticket_id)
        return None

    def pollers(self) -> cli.Pollers:
        def timing_for(ticket: TicketState) -> CiTiming:
            return TIMINGS.get("ap-data-source-connector", policy.FALLBACK_CI_TIMING)

        return cli.Pollers(timing_for, self.read_linear, self.read_github)


class TickTest(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.dir)
        self.path = self.dir / "wave-state.json"

    def write(self, tickets: dict[str, TicketState]) -> None:
        state_store.save(self.path, WaveState(tickets=tickets))

    def ticks(
        self, start: datetime, until: datetime, fake: FakePollers
    ) -> list[tuple[datetime, list[str]]]:
        printed: list[tuple[datetime, list[str]]] = []
        now = start
        while now <= until:
            result = cli.run_tick(self.path, now, fake.pollers())
            if result.events:
                printed.append((now, [e.render() for e in result.events]))
            now += timedelta(seconds=30)
        return printed

    def test_acc_1670_no_ack_then_no_more_haiku_calls(self) -> None:
        feedback = parse_time("2026-11-05T20:56:14Z")
        self.write(
            {
                "ACC-1670": TicketState(
                    repo_dir=REPO,
                    stage=Stage.PLAN_READY,
                    stage_since=feedback - timedelta(minutes=5),
                    last_status="Awaiting Plan Approval",
                    last_timeline="Plan v1 posted",
                    feedback_at=feedback,
                )
            }
        )
        fake = FakePollers()
        printed = self.ticks(feedback, feedback + timedelta(minutes=15), fake)
        self.assertEqual(
            printed,
            [
                (
                    parse_time("2026-11-05T20:57:14Z"),
                    ["ACC-1670 NO ACK stage=plan-feedback due=2026-11-05T20:57:14Z"],
                )
            ],
        )
        self.assertEqual(len(fake.linear_calls), 2)  # +30 s, then the read at the deadline
        self.assertEqual(fake.github_calls, [])
        ticket = state_store.load(self.path).tickets["ACC-1670"]
        self.assertTrue(cli.schedule.is_idle(ticket))

    def test_all_plan_ready_is_idle_on_the_first_tick(self) -> None:
        now = parse_time("2026-11-06T03:00:00Z")
        ticket = TicketState(repo_dir=REPO, stage=Stage.PLAN_READY, stage_since=now)
        self.write({"ACC-1": ticket, "ACC-2": ticket})
        fake = FakePollers()
        result = cli.run_tick(self.path, now, fake.pollers())
        self.assertEqual(result.events, ())
        self.assertTrue(result.idle)
        self.assertEqual((fake.linear_calls, fake.github_calls), ([], []))

    def test_malformed_haiku_reply_is_a_poll_error_and_leaves_state(self) -> None:
        start = parse_time("2026-11-06T03:00:00Z")
        self.write({"ACC-1": TicketState(repo_dir=REPO, started_at=start)})
        fake = FakePollers()
        cli.run_tick(self.path, start, fake.pollers())
        before = self.path.read_text()
        fake.linear_error = "no JSON array in reply: 'sorry'"
        result = cli.run_tick(self.path, start + timedelta(seconds=30), fake.pollers())
        self.assertEqual(
            [e.render() for e in result.events],
            ["LINEAR POLL ERROR no JSON array in reply: 'sorry'"],
        )
        self.assertEqual(self.path.read_text(), before)
        self.assertEqual(len(fake.linear_calls), 1)

    def test_one_haiku_call_for_every_due_ticket(self) -> None:
        start = parse_time("2026-11-06T03:00:00Z")
        self.write(
            {
                "ACC-1": TicketState(repo_dir=REPO, started_at=start),
                "ACC-2": TicketState(repo_dir=REPO, started_at=start),
                "ACC-3": TicketState(repo_dir=REPO, stage=Stage.PLAN_READY, stage_since=start),
            }
        )
        fake = FakePollers(status="Analyzing...", timeline="Started by A")
        result = cli.run_tick(self.path, start + timedelta(seconds=30), fake.pollers())
        self.assertEqual(fake.linear_calls, [["ACC-1", "ACC-2"]])
        self.assertEqual(result.events, ())
        stages = {k: t.stage for k, t in state_store.load(self.path).tickets.items()}
        self.assertEqual(
            stages, {"ACC-1": Stage.PLANNING, "ACC-2": Stage.PLANNING, "ACC-3": Stage.PLAN_READY}
        )

    def test_status_event_keeps_the_old_line_format(self) -> None:
        start = parse_time("2026-11-06T03:00:00Z")
        self.write({"ACC-1": TicketState(repo_dir=REPO, stage=Stage.PLANNING, stage_since=start)})
        fake = FakePollers(timeline="Plan v1 posted ($2.10) — awaiting approval")
        result = cli.run_tick(self.path, start + timedelta(minutes=3), fake.pollers())
        self.assertEqual(
            [e.render() for e in result.events],
            [
                'ACC-1 STATUS "Awaiting Plan Approval" '
                'TIMELINE "Plan v1 posted ($2.10) — awaiting approval"'
            ],
        )

    def test_an_omitted_row_is_no_read_and_confirms_no_deadline(self) -> None:
        start = parse_time("2026-11-06T03:00:00Z")
        self.write({"ACC-1": TicketState(repo_dir=REPO, started_at=start)})
        fake = FakePollers(status="Queued", timeline="Started by A")
        fake.omit = {"ACC-1"}
        printed = self.ticks(start, start + timedelta(minutes=2), fake)
        lines = [line for _, batch in printed for line in batch]
        self.assertNotIn("NO START", " ".join(lines))
        self.assertIn("LINEAR POLL ERROR ACC-1 missing from the reply", lines)
        ticket = state_store.load(self.path).tickets["ACC-1"]
        self.assertIsNone(ticket.last_linear_at)
        self.assertIsNone(ticket.queued_since)

    def test_reply_ids_match_case_insensitively(self) -> None:
        start = parse_time("2026-11-06T03:00:00Z")
        self.write({"ACC-1": TicketState(repo_dir=REPO, started_at=start)})
        fake = FakePollers(status="Analyzing...", timeline="Started by A")
        fake.lowercase = True
        cli.run_tick(self.path, start + timedelta(seconds=30), fake.pollers())
        self.assertIs(state_store.load(self.path).tickets["ACC-1"].stage, Stage.PLANNING)

    def test_wave2_prints_all_merged(self) -> None:
        shutil.copy(WAVE2, self.path)
        fake = FakePollers()
        result = cli.run_tick(self.path, parse_time("2026-11-06T03:00:00Z"), fake.pollers())
        self.assertEqual([e.render() for e in result.events], ["ALL MERGED"])
        self.assertEqual((fake.linear_calls, fake.github_calls), ([], []))


class CommandTest(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.dir)
        self.path = self.dir / "wave2-state.json"
        shutil.copy(WAVE2, self.path)

    def run_cli(self, *argv: str) -> tuple[int, str]:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cli.main(list(argv))
        return code, out.getvalue()

    def test_explain_wave2(self) -> None:
        code, out = self.run_cli("explain", str(self.path), "--at", "2026-11-06T03:00:00Z")
        self.assertEqual(code, 0)
        self.assertIn("ACC-1670 done", out)
        self.assertIn("ci=ap-data-source-connector", out)

    def test_state_init_set_get(self) -> None:
        path = str(self.path)
        self.assertEqual(self.run_cli("state", "init", path, "ACC-9", "agent-1", REPO)[0], 0)
        code, out = self.run_cli(
            "state", "set", path, "ACC-9", "approvedAt", "2026-11-06T02:40:00Z"
        )
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["approvedAt"], "2026-11-06T02:40:00Z")
        self.run_cli("state", "set", path, "ACC-9", "estimate", "2")
        code, out = self.run_cli("state", "get", path, "ACC-9")
        self.assertEqual(
            json.loads(out),
            {
                "agent": "agent-1",
                "repoDir": REPO,
                "merged": False,
                "approvedAt": "2026-11-06T02:40:00Z",
                "estimate": 2,
            },
        )
        self.assertEqual(json.loads(self.path.read_text())["schemaVersion"], 2)

    def test_state_set_on_an_unknown_ticket_is_a_usage_error(self) -> None:
        with self.assertLogs("jaidev_watch", "ERROR"):
            self.assertEqual(
                self.run_cli("state", "set", str(self.path), "ACC-0", "estimate", "1")[0], 2
            )

    def test_due_reports_none_for_wave2(self) -> None:
        self.assertEqual(self.run_cli("due", str(self.path)), (3, "NONE\n"))


if __name__ == "__main__":
    unittest.main()

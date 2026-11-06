"""Whole ticks with fake pollers and a fixed clock, plus the CLI commands."""

from __future__ import annotations

import contextlib
import io
import json
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from collections.abc import Sequence
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

from jaidev_watch import cli, state_store
from jaidev_watch.ci_derive import CiDeriveError, DerivedRow
from jaidev_watch.ci_timing import load
from jaidev_watch.linear_poll import LinearPollError
from jaidev_watch.models import (
    CiTiming,
    Event,
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
        def timing_for(ticket: TicketState) -> CiTiming | None:
            return TIMINGS["ap-data-source-connector"]

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
        after = json.loads(self.path.read_text())["tickets"]["ACC-1"]
        self.assertEqual(after.pop("lastLinearErrorAt"), "2026-11-06T03:00:30Z")
        self.assertEqual(after, json.loads(before)["tickets"]["ACC-1"])
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

    def test_events_print_before_the_state_commits(self) -> None:
        start = parse_time("2026-11-06T03:00:00Z")
        deadline = start + timedelta(minutes=1)
        self.write(
            {
                "ACC-1": TicketState(
                    repo_dir=REPO,
                    stage=Stage.APPROVED,
                    stage_since=start,
                    approved_at=start,
                    last_linear_at=deadline,
                )
            }
        )
        before = self.path.read_text()

        def broken_pipe(events: Sequence[Event]) -> None:
            raise BrokenPipeError

        with self.assertRaises(BrokenPipeError):
            cli.run_tick(self.path, deadline, FakePollers().pollers(), emit=broken_pipe)
        self.assertEqual(self.path.read_text(), before)
        printed: list[str] = []
        cli.run_tick(
            self.path,
            deadline,
            FakePollers().pollers(),
            emit=lambda events: printed.extend(e.render() for e in events),
        )
        self.assertEqual(printed, ["ACC-1 NO START stage=approved due=2026-11-06T03:01:00Z"])

    def test_a_failed_read_waits_two_minutes_before_the_retry(self) -> None:
        start = parse_time("2026-11-06T03:00:00Z")
        self.write({"ACC-1": TicketState(repo_dir=REPO, started_at=start)})
        fake = FakePollers()
        fake.linear_error = "boom"
        self.ticks(start, start + timedelta(seconds=140), fake)
        self.assertEqual(len(fake.linear_calls), 1)
        self.ticks(start + timedelta(seconds=150), start + timedelta(seconds=150), fake)
        self.assertEqual(len(fake.linear_calls), 2)

    def test_a_read_that_crosses_a_stamp_is_dropped(self) -> None:
        start = parse_time("2026-11-06T03:00:00Z")
        self.write({"ACC-1": TicketState(repo_dir=REPO, started_at=start)})
        stamp = start + timedelta(seconds=31)
        fake = FakePollers(status="Analyzing...", timeline="Started by A")
        read = fake.read_linear

        def read_while_stamping(ids: Sequence[str]) -> Sequence[LinearObservation]:
            state_store.update(
                self.path,
                lambda wave: replace(
                    wave,
                    tickets={"ACC-1": replace(wave.tickets["ACC-1"], feedback_at=stamp)},
                ),
            )
            return read(ids)

        fake.read_linear = read_while_stamping  # type: ignore[method-assign]
        cli.run_tick(self.path, start + timedelta(seconds=30), fake.pollers())
        ticket = state_store.load(self.path).tickets["ACC-1"]
        self.assertIs(ticket.stage, Stage.PLAN_FEEDBACK)
        self.assertIsNone(ticket.last_status)
        self.assertIsNone(ticket.last_linear_at)

    def test_wave2_prints_all_merged(self) -> None:
        shutil.copy(WAVE2, self.path)
        fake = FakePollers()
        result = cli.run_tick(self.path, parse_time("2026-11-06T03:00:00Z"), fake.pollers())
        self.assertEqual([e.render() for e in result.events], ["ALL MERGED"])
        self.assertEqual((fake.linear_calls, fake.github_calls), ([], []))


class CiRowsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.derived: list[str] = []
        self.written: list[str] = []

    def rows(self, fail: bool) -> cli.CiRows:
        def derive(repo: str) -> DerivedRow:
            self.derived.append(repo)
            if fail:
                raise CiDeriveError("no successful PR runs")
            return DerivedRow(
                replace(TIMINGS["ap-data-source-connector"], repo=repo), "unit-test.yml", 10
            )

        def write(row: DerivedRow) -> bool:
            self.written.append(row.timing.repo)
            return True

        return cli.CiRows({}, derive=derive, write=write, resolve=lambda d: "new-repo")

    def test_a_missing_row_is_derived_once_and_announced(self) -> None:
        rows = self.rows(fail=False)
        ticket = TicketState(repo_dir="/x/new-repo", stage=Stage.PR_CI)
        self.assertIsNotNone(rows.for_ticket(ticket))
        self.assertIsNotNone(rows.for_ticket(ticket))
        self.assertEqual(self.derived, ["new-repo"])
        self.assertEqual(self.written, ["new-repo"])
        self.assertEqual([e.render() for e in rows.notices()], ["CI ROW ADDED new-repo"])
        self.assertEqual(rows.notices(), [])

    def test_a_failed_derivation_turns_ci_polling_off(self) -> None:
        rows = self.rows(fail=True)
        ticket = TicketState(
            repo_dir="/x/new-repo",
            stage=Stage.PR_CI,
            stage_since=parse_time("2026-11-06T03:00:00Z"),
        )
        self.assertIsNone(rows.for_ticket(ticket))
        self.assertIsNone(rows.for_ticket(ticket))
        self.assertEqual(self.derived, ["new-repo"])
        self.assertEqual(
            [e.render() for e in rows.notices()],
            ["CI ROW MISSING new-repo no successful PR runs"],
        )
        decision = cli.schedule.decide(ticket, parse_time("2026-11-06T04:00:00Z"), None)
        self.assertFalse(decision.github_due)
        self.assertIsNone(decision.ticket.deadline)

    def test_stages_before_the_pr_derive_nothing(self) -> None:
        rows = self.rows(fail=False)
        self.assertIsNone(
            rows.for_ticket(TicketState(repo_dir="/x/new-repo", stage=Stage.PLANNING))
        )
        self.assertEqual(self.derived, [])


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

    def test_exit_codes_for_bad_input(self) -> None:
        path = str(self.path)
        cases = [
            (("due", path, "--at", "garbage"), cli.EXIT_USAGE),
            (("explain", path, "--at", "2026-13-40"), cli.EXIT_USAGE),
            (("state", "set", path, "ACC-1670", "prNumber", "abc"), cli.EXIT_USAGE),
            (("state", "set", path, "ACC-1670", "stage", "bogus"), cli.EXIT_USAGE),
            (("state", "set", path, "ACC-1670", "approvedAt", "yesterday"), cli.EXIT_USAGE),
            (("state", "get", str(self.dir / "missing" / "s.json"), "ACC-1"), cli.EXIT_ERROR),
            (("state", "init", path, "ACC-1670", "a", REPO), cli.EXIT_USAGE),
        ]
        for argv, code in cases:
            with self.subTest(argv=argv), self.assertLogs("jaidev_watch", "ERROR"):
                self.assertEqual(self.run_cli(*argv)[0], code)

    def test_init_keeps_an_existing_ticket_unless_forced(self) -> None:
        path = str(self.path)
        with self.assertLogs("jaidev_watch", "ERROR"):
            self.run_cli("state", "init", path, "ACC-1670", "new-agent", REPO)
        kept = state_store.load(self.path).tickets["ACC-1670"]
        self.assertEqual(kept.agent, "a40bb3fcdbb02da5b")
        self.assertEqual(
            self.run_cli("state", "init", path, "ACC-1670", "b", REPO, "--force")[0], 0
        )
        self.assertEqual(state_store.load(self.path).tickets["ACC-1670"].agent, "b")

    def test_sigterm_stops_the_watcher_with_exit_4(self) -> None:
        now = datetime.now(UTC).replace(microsecond=0)
        state = self.dir / "live.json"
        state_store.save(
            state,
            WaveState(
                tickets={
                    "ACC-1": TicketState(
                        repo_dir=str(self.dir),
                        stage=Stage.APPROVED,
                        stage_since=now,
                        approved_at=now,
                    )
                }
            ),
        )
        scripts = Path(__file__).resolve().parents[1]
        process = subprocess.Popen(
            [sys.executable, "-m", "jaidev_watch", "watch", str(state)],
            cwd=scripts,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        time.sleep(1.5)
        process.send_signal(signal.SIGTERM)
        out, err = process.communicate(timeout=10)
        self.assertEqual(process.returncode, cli.EXIT_STOPPED, err)
        self.assertEqual(out, "")
        self.assertNotIn("Traceback", err)

    def test_due_reports_none_for_wave2(self) -> None:
        self.assertEqual(self.run_cli("due", str(self.path)), (3, "NONE\n"))


if __name__ == "__main__":
    unittest.main()

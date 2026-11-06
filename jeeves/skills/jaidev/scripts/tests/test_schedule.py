"""Stage derivation, deadlines and check cadence, with a fixed clock."""

from __future__ import annotations

import unittest
from dataclasses import replace
from datetime import datetime, timedelta

from jaidev_watch import schedule
from jaidev_watch.ci_timing import DEFAULT_PATH, load
from jaidev_watch.models import (
    CiResult,
    EventKind,
    GithubObservation,
    LinearObservation,
    PrState,
    Stage,
    TicketState,
    parse_time,
)

CI = load(DEFAULT_PATH)["ap-data-source-connector"]
T0 = parse_time("2026-11-05T13:22:08Z")


def at(seconds: float) -> datetime:
    return T0 + timedelta(seconds=seconds)


def obs(
    status: str | None, timeline: str | None = None, attempt: int | None = None
) -> LinearObservation:
    return LinearObservation("ACC-1", status, timeline, attempt)


def pr(
    head: str, ci: CiResult = CiResult.PENDING, state: PrState = PrState.OPEN
) -> GithubObservation:
    return GithubObservation(number=96, head=head, state=state, ci=ci, sonar_findings=False)


class DeriveStageTest(unittest.TestCase):
    def test_table(self) -> None:
        cases = [
            # (current, last status, observation, expected)
            (Stage.STARTING, None, obs("Analyzing..."), Stage.PLANNING),
            (Stage.STARTING, None, obs("Queued"), Stage.STARTING),
            (
                Stage.PLANNING,
                "Planning...",
                obs("Gathering Info (Waiting for Answers)"),
                Stage.QUESTIONS,
            ),
            (
                Stage.PLANNING,
                "Planning...",
                obs("Awaiting Plan Approval", "Plan v1 posted"),
                Stage.PLAN_READY,
            ),
            (
                Stage.PLAN_FEEDBACK,
                "Awaiting Plan Approval",
                obs("Planning... (Running: x)"),
                Stage.PLAN_FEEDBACK,
            ),
            (
                Stage.PLAN_FEEDBACK,
                "Awaiting Plan Approval",
                obs("Awaiting Plan Approval", "Plan feedback received"),
                Stage.PLAN_FEEDBACK,
            ),
            (
                Stage.PLAN_FEEDBACK,
                "Planning...",
                obs("Awaiting Plan Approval", "Revised plan v2 posted"),
                Stage.PLAN_READY,
            ),
            (
                Stage.APPROVED,
                "Awaiting Plan Approval",
                obs("Awaiting Plan Approval", "Plan approved by A"),
                Stage.IMPLEMENTING,
            ),
            (
                Stage.APPROVED,
                "Awaiting Plan Approval",
                obs("Implementing... (attempt 1/5)"),
                Stage.IMPLEMENTING,
            ),
            (
                Stage.IMPLEMENTING,
                "Implementing...",
                obs("🚫 Blocked — Needs Human Help"),
                Stage.BLOCKED,
            ),
            (Stage.IMPLEMENTING, "Implementing...", obs("PRs Created"), Stage.PR_CI),
            (
                Stage.PR_REVIEW_SENT,
                "PRs Created",
                obs("Addressing PR Feedback..."),
                Stage.PR_REVISING,
            ),
            (Stage.PR_READY, "PRs Created", obs("Complete ✅"), Stage.PR_READY),
            (
                Stage.PR_REVIEW_SENT,
                "Addressing PR Feedback...",
                obs("PRs Created"),
                Stage.PR_REVISING,
            ),
            (Stage.STARTING, None, obs(None, "Started by A"), Stage.PLANNING),
        ]
        for current, last, observation, expected in cases:
            with self.subTest(
                current=current, status=observation.status, timeline=observation.timeline
            ):
                ticket = TicketState(stage=current, stage_since=T0, last_status=last)
                self.assertIs(schedule.derive_stage(ticket, observation), expected)

    def test_unchanged_text_keeps_the_stage(self) -> None:
        ticket = TicketState(
            stage=Stage.APPROVED,
            stage_since=T0,
            last_status="Awaiting Plan Approval",
            last_timeline="Plan v1 posted",
        )
        self.assertIs(
            schedule.derive_stage(ticket, obs("Awaiting Plan Approval", "Plan v1 posted")),
            Stage.APPROVED,
        )


class ReconcileTest(unittest.TestCase):
    def test_latest_stamp_sets_the_stage(self) -> None:
        cases = [
            (TicketState(started_at=T0), Stage.STARTING),
            (TicketState(started_at=T0, feedback_at=at(300)), Stage.PLAN_FEEDBACK),
            (TicketState(started_at=T0, feedback_at=at(300), approved_at=at(600)), Stage.APPROVED),
            (TicketState(approved_at=at(600), review_at=at(1200)), Stage.PR_REVIEW_SENT),
            (TicketState(approved_at=T0, merged=True), Stage.DONE),
            (TicketState(pr_number=5, last_ci_head="abc1234"), Stage.PR_READY),
            (TicketState(), None),
        ]
        for ticket, expected in cases:
            with self.subTest(expected=expected):
                self.assertIs(schedule.reconcile(ticket, at(2000)).stage, expected)

    def test_a_newer_stamp_rearms_a_fired_stage(self) -> None:
        ticket = TicketState(
            stage=Stage.PLAN_FEEDBACK,
            stage_since=T0,
            feedback_at=T0,
            fired_event=EventKind.NO_ACK,
        )
        nudged = schedule.reconcile(replace(ticket, feedback_at=at(120)), at(120))
        self.assertIsNone(nudged.fired_event)
        self.assertEqual(nudged.stage_since, at(120))


class CadenceTest(unittest.TestCase):
    def test_acc_1669_first_github_check_after_approval(self) -> None:
        """2 points, approved 13:22:08 → first GitHub check 13:26:08."""
        ticket = TicketState(approved_at=T0, estimate=2)
        ticket, _ = schedule.apply_linear(
            schedule.reconcile(ticket, at(30)), obs("Implementing..."), at(30)
        )
        self.assertIs(ticket.stage, Stage.IMPLEMENTING)
        decision = schedule.decide(ticket, at(30), CI)
        self.assertEqual(decision.ticket.next_github_at, parse_time("2026-11-05T13:26:08Z"))
        self.assertFalse(schedule.decide(ticket, at(239), CI).github_due)
        self.assertTrue(schedule.decide(ticket, at(240), CI).github_due)

    def test_implementing_github_slows_after_twice_pr_due(self) -> None:
        ticket = TicketState(stage=Stage.IMPLEMENTING, stage_since=T0, estimate=2)
        cases = [(None, at(240)), (at(240), at(300)), (at(480), at(600))]
        for last, expected in cases:
            with self.subTest(last=last):
                checked = replace(ticket, last_github_at=last)
                self.assertEqual(
                    schedule.decide(checked, at(1), CI).ticket.next_github_at, expected
                )

    def test_planning_first_check_by_pre_estimate(self) -> None:
        cases = [(1, 120), (2, 180), (3, 180), (5, 240), (None, 180)]
        for pre_estimate, seconds in cases:
            with self.subTest(pre_estimate=pre_estimate):
                ticket = TicketState(started_at=T0, pre_estimate=pre_estimate)
                ticket, _ = schedule.apply_linear(
                    schedule.reconcile(ticket, at(30)), obs("Analyzing..."), at(30)
                )
                self.assertEqual(ticket.stage_since, T0)
                self.assertEqual(
                    schedule.decide(ticket, at(30), CI).ticket.next_linear_at, at(seconds)
                )

    def test_ci_cadence_on_ap_data_source_connector(self) -> None:
        """Push → checks at +2 min, then every 2 min; CI LATE at +7 min 21 s."""
        ticket, _ = schedule.apply_github(
            TicketState(stage=Stage.PR_REVISING, stage_since=T0), pr("aaaaaaa"), T0
        )
        self.assertIs(ticket.stage, Stage.PR_CI)
        expected_checks = [at(120), at(240), at(360)]
        now = T0
        for expected in expected_checks:
            decision = schedule.decide(ticket, now, CI)
            self.assertEqual(decision.ticket.next_github_at, expected)
            now = expected
            ticket, _ = schedule.apply_github(decision.ticket, pr("aaaaaaa"), now)
        self.assertEqual(schedule.decide(ticket, now, CI).ticket.deadline, at(441))
        late = schedule.decide(ticket, at(441), CI)
        self.assertTrue(late.github_due)
        self.assertEqual(late.events, ())
        ticket, _ = schedule.apply_github(late.ticket, pr("aaaaaaa"), at(441))
        fired = schedule.decide(ticket, at(441), CI)
        self.assertEqual([e.kind for e in fired.events], [EventKind.CI_LATE])

    def test_new_head_resets_the_ci_clock(self) -> None:
        ticket, _ = schedule.apply_github(
            TicketState(stage=Stage.IMPLEMENTING, stage_since=T0), pr("aaaaaaa"), T0
        )
        ticket, _ = schedule.apply_github(ticket, pr("bbbbbbb"), at(200))
        self.assertEqual(ticket.stage_since, at(200))
        self.assertEqual(schedule.decide(ticket, at(200), CI).ticket.deadline, at(641))

    def test_settled_ci_prints_once_and_moves_to_pr_ready(self) -> None:
        ticket, _ = schedule.apply_github(
            TicketState(stage=Stage.IMPLEMENTING, stage_since=T0), pr("aaaaaaa"), T0
        )
        ticket, events = schedule.apply_github(ticket, pr("aaaaaaa", CiResult.PASSED), at(120))
        self.assertEqual(
            [e.render() for e in schedule.with_ticket_id(events, "ACC-1")],
            ["ACC-1 CI passed #96 head=aaaaaaa"],
        )
        self.assertIs(ticket.stage, Stage.PR_READY)
        ticket, events = schedule.apply_github(ticket, pr("aaaaaaa", CiResult.PASSED), at(240))
        self.assertEqual(events, ())

    def test_merge_ends_the_ticket(self) -> None:
        ticket = TicketState(stage=Stage.PR_READY, stage_since=T0, pr_head="aaaaaaa")
        ticket, events = schedule.apply_github(ticket, pr("aaaaaaa", state=PrState.MERGED), at(60))
        self.assertIs(ticket.stage, Stage.DONE)
        self.assertTrue(ticket.merged)
        self.assertEqual([e.render() for e in events], ["MERGED #96"])

    def test_pr_ready_reads_linear_once_only_after_sonar_findings(self) -> None:
        for findings, expected in ((True, at(60)), (False, None)):
            with self.subTest(findings=findings):
                ticket = TicketState(stage=Stage.PR_READY, stage_since=T0, sonar_findings=findings)
                self.assertEqual(schedule.decide(ticket, T0, CI).ticket.next_linear_at, expected)
        merge_watch = schedule.decide(
            TicketState(stage=Stage.PR_READY, stage_since=T0), T0, CI, merge_watch=True
        )
        self.assertEqual(merge_watch.ticket.next_github_at, at(900))


class DeadlineTest(unittest.TestCase):
    def test_deadline_table(self) -> None:
        cases = [
            (TicketState(stage=Stage.STARTING), 120, EventKind.NO_START),
            (TicketState(stage=Stage.PLANNING), 600, EventKind.PLAN_LATE),
            (
                TicketState(stage=Stage.PLANNING, names_bytes=44 * 1024, repo_count=2),
                900,
                EventKind.PLAN_LATE,
            ),
            (TicketState(stage=Stage.PLAN_FEEDBACK), 60, EventKind.NO_ACK),
            (
                TicketState(stage=Stage.PLAN_FEEDBACK, ack_at=at(12), feedback_bytes=6000),
                360,
                EventKind.PLAN_LATE,
            ),
            (TicketState(stage=Stage.APPROVED), 60, EventKind.NO_START),
            (TicketState(stage=Stage.IMPLEMENTING, estimate=3), 1080, EventKind.PR_LATE),
            (TicketState(stage=Stage.IMPLEMENTING, estimate=3, attempt=3), 1800, EventKind.PR_LATE),
            (TicketState(stage=Stage.PR_REVIEW_SENT), 120, EventKind.NO_ACK),
            (TicketState(stage=Stage.PR_REVISING, review_comments=3), 300, EventKind.FIX_LATE),
            (TicketState(stage=Stage.PR_REVISING, review_comments=20), 600, EventKind.FIX_LATE),
        ]
        for ticket, seconds, kind in cases:
            with self.subTest(stage=ticket.stage, kind=kind, seconds=seconds):
                deadline = schedule.pending_deadline(replace(ticket, stage_since=T0), CI)
                assert deadline is not None
                self.assertEqual((deadline.at, deadline.kind), (at(seconds), kind))

    def test_waiting_stages_have_no_deadline_and_no_checks(self) -> None:
        for stage in (Stage.QUESTIONS, Stage.PLAN_READY, Stage.BLOCKED, Stage.DONE):
            with self.subTest(stage=stage):
                decision = schedule.decide(TicketState(stage=stage, stage_since=T0), at(9999), CI)
                self.assertTrue(schedule.is_idle(decision.ticket))

    def test_queue_time_pauses_the_deadline(self) -> None:
        ticket = TicketState(started_at=T0)
        ticket, _ = schedule.apply_linear(schedule.reconcile(ticket, at(30)), obs("Queued"), at(30))
        self.assertEqual(ticket.queued_since, at(30))
        paused = schedule.decide(ticket, at(400), CI)
        self.assertEqual(paused.events, ())
        self.assertEqual(paused.ticket.next_linear_at, at(150))
        ticket, _ = schedule.apply_linear(ticket, obs("Analyzing..."), at(330))
        self.assertIs(ticket.stage, Stage.PLANNING)
        self.assertEqual(ticket.paused_seconds, 300)
        deadline = schedule.pending_deadline(ticket, CI)
        assert deadline is not None
        self.assertEqual(deadline.at, at(600 + 300))

    def test_fired_deadline_stops_linear_reads(self) -> None:
        ticket = TicketState(stage=Stage.APPROVED, stage_since=T0, last_linear_at=at(60))
        decision = schedule.decide(ticket, at(60), CI)
        self.assertEqual([e.kind for e in decision.events], [EventKind.NO_START])
        self.assertIsNone(decision.ticket.next_linear_at)
        self.assertFalse(schedule.decide(decision.ticket, at(600), CI).linear_due)


if __name__ == "__main__":
    unittest.main()


class PauseCarryOverTest(unittest.TestCase):
    def test_queue_time_stays_in_the_stage_it_was_spent_in(self) -> None:
        ticket = TicketState(
            stage=Stage.IMPLEMENTING,
            stage_since=T0,
            approved_at=T0,
            estimate=1,
            last_status="Implementing...",
            last_timeline="x",
        )
        ticket, _ = schedule.apply_linear(ticket, obs("Queued", "waiting"), at(300))
        ticket, _ = schedule.apply_linear(ticket, obs("PRs Created", "opened"), at(2100))
        self.assertIs(ticket.stage, Stage.PR_CI)
        self.assertEqual(ticket.paused_seconds, 0)
        self.assertIsNone(ticket.queued_since)

    def test_a_stamp_while_queued_restarts_the_queue_clock(self) -> None:
        ticket = TicketState(
            stage=Stage.PLANNING,
            stage_since=T0,
            started_at=T0,
            last_status="Queued",
            last_timeline="q",
            queued_since=at(60),
        )
        ticket = schedule.reconcile(replace(ticket, approved_at=at(1800)), at(1860))
        self.assertIs(ticket.stage, Stage.APPROVED)
        self.assertIsNone(ticket.queued_since)
        ticket, _ = schedule.apply_linear(ticket, obs("Queued", "q"), at(1890))
        self.assertEqual(ticket.queued_since, at(1890))
        ticket, _ = schedule.apply_linear(ticket, obs("Implementing...", "go"), at(1950))
        self.assertEqual(ticket.paused_seconds, 60)

    def test_pause_shifts_the_implementing_checks(self) -> None:
        ticket = TicketState(
            stage=Stage.IMPLEMENTING, stage_since=T0, estimate=2, paused_seconds=120
        )
        decision = schedule.decide(ticket, T0, CI)
        self.assertEqual(decision.ticket.next_github_at, at(240 + 120))
        self.assertEqual(decision.ticket.next_linear_at, at(240 + 120))
        late = replace(ticket, last_github_at=at(480 + 60))
        self.assertEqual(schedule.decide(late, T0, CI).ticket.next_github_at, at(600))


class ChangeDetectionTest(unittest.TestCase):
    def test_reworded_reads_of_the_same_entry_are_unchanged(self) -> None:
        cases = [
            ("Complete ✅", "2026-11-05T13:33:41Z — Complete", obs("Complete ✅", "Complete")),
            (
                "Awaiting Plan Approval",
                "Plan v1 posted ($2.10) — awaiting approval",
                obs("awaiting plan  approval", "Plan v1 posted ($2.11) —  Awaiting approval"),
            ),
        ]
        for last_status, last_timeline, observation in cases:
            with self.subTest(timeline=observation.timeline):
                ticket = TicketState(
                    stage=Stage.PR_READY,
                    stage_since=T0,
                    last_status=last_status,
                    last_timeline=last_timeline,
                )
                _, events = schedule.apply_linear(ticket, observation, at(60))
                self.assertEqual(events, ())


class BaselineTest(unittest.TestCase):
    def test_an_old_status_comment_is_the_baseline_of_a_new_start(self) -> None:
        ticket = TicketState(stage=Stage.STARTING, stage_since=T0, started_at=T0)
        ticket, events = schedule.apply_linear(
            ticket, obs("Awaiting Plan Approval", "Plan posted"), at(30)
        )
        self.assertIs(ticket.stage, Stage.STARTING)
        self.assertEqual(events, ())
        self.assertEqual(ticket.last_status, "Awaiting Plan Approval")

    def test_a_new_run_leaves_starting(self) -> None:
        cases = [
            (obs("Analyzing..."), Stage.PLANNING),
            (obs(None, "Started by A"), Stage.PLANNING),
            (obs("Gathering Info (Waiting for Answers)", "Question posted"), Stage.QUESTIONS),
        ]
        for observation, expected in cases:
            with self.subTest(status=observation.status):
                ticket = TicketState(stage=Stage.STARTING, stage_since=T0, started_at=T0)
                ticket, _ = schedule.apply_linear(ticket, observation, at(30))
                self.assertIs(ticket.stage, expected)


class BaselineOnlyFirstReadTest(unittest.TestCase):
    def test_only_the_first_read_is_the_baseline(self) -> None:
        ticket = TicketState(stage=Stage.STARTING, stage_since=T0, started_at=T0)
        ticket, events = schedule.apply_linear(ticket, obs("Complete ✅", "Merged"), at(30))
        self.assertEqual((ticket.stage, events), (Stage.STARTING, ()))
        ticket, events = schedule.apply_linear(
            ticket, obs("Awaiting Plan Approval", "Plan v1 posted"), at(60)
        )
        self.assertIs(ticket.stage, Stage.PLAN_READY)
        self.assertEqual(len(events), 1)

    def test_new_run_statuses_match_case_insensitively(self) -> None:
        ticket = TicketState(stage=Stage.STARTING, stage_since=T0, started_at=T0)
        ticket, _ = schedule.apply_linear(ticket, obs("analyzing...", "started by A"), at(30))
        self.assertIs(ticket.stage, Stage.PLANNING)

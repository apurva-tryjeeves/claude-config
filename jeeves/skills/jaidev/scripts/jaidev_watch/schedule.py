"""Pure stage and schedule logic: no I/O, and the clock is always a parameter."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from typing import Final, TypeVar

from jaidev_watch import policy
from jaidev_watch.models import (
    CiResult,
    CiTiming,
    Decision,
    Event,
    EventKind,
    GithubObservation,
    LinearObservation,
    PrState,
    Source,
    Stage,
    TicketState,
    format_time,
)

# Jaidev is busy in these; the coordinator has nothing to do until it leaves them.
WORKING_STATUSES: Final = frozenset(
    {"Analyzing...", "Planning...", "Implementing...", "Addressing PR Feedback..."}
)
# The GitHub poll reports these, with the PR number and CI result.
GITHUB_REPORTED_STATUSES: Final = frozenset({"PRs Created"})
# Timeline entries the coordinator caused.
COORDINATOR_ENTRIES: Final = ("Started by", "Plan approved by", "Plan feedback received")
PLAN_APPROVED_ENTRY: Final = "Plan approved by"
FEEDBACK_ENTRY: Final = "Plan feedback received"
PLANNING_STATUSES: Final = frozenset({"Analyzing...", "Planning..."})
PR_STAGES: Final = frozenset({Stage.PR_CI, Stage.PR_READY, Stage.PR_REVIEW_SENT, Stage.PR_REVISING})
# Status prefix → stage, checked in order.
STATUS_STAGES: Final[tuple[tuple[str, Stage], ...]] = (
    ("Gathering Info", Stage.QUESTIONS),
    ("Awaiting Plan Approval", Stage.PLAN_READY),
    ("Implementing", Stage.IMPLEMENTING),
    ("Addressing PR Feedback", Stage.PR_REVISING),
)
# Stages that wait on the coordinator: nothing to read, even while queued.
WAITING_STAGES: Final = frozenset({Stage.QUESTIONS, Stage.PLAN_READY, Stage.BLOCKED, Stage.DONE})
# In these stages any change on the status comment is Jaidev's reply.
REPLY_STAGES: Final[Mapping[Stage, Stage]] = {
    Stage.STARTING: Stage.PLANNING,
    Stage.APPROVED: Stage.IMPLEMENTING,
    Stage.PR_REVIEW_SENT: Stage.PR_REVISING,
}
# Deadlines that wait for the status comment to go quiet.
QUIET_KINDS: Final = frozenset({EventKind.PR_LATE, EventKind.FIX_LATE})
# Moves that keep the stage clock: planning runs from startedAt, implementing
# from approvedAt.
CONTINUING: Final = frozenset(
    {(Stage.STARTING, Stage.PLANNING), (Stage.APPROVED, Stage.IMPLEMENTING)}
)


# A new run's first status comment shows one of these, or a "Started by" entry;
# anything else on the first read after startedAt is the previous run's comment.
NEW_RUN_PREFIXES: Final = ("Queued", "Analyzing", "Planning", "Gathering Info")
STARTED_ENTRY: Final = "Started by"
_TIMESTAMP: Final = re.compile(r"^\s*\d{4}-\d{2}-\d{2}[T ][0-9:.]+Z?\s*[\u2014\u2013-]\s*")
_COST: Final = re.compile(r"\(\$\d+(?:\.\d+)?\)")


_T = TypeVar("_T")


def _need(value: _T | None, what: str) -> _T:
    """A policy table entry the stage relies on; a gap is a bug in policy.py."""
    if value is None:
        raise RuntimeError(f"policy.py is missing {what}")
    return value


@dataclass(frozen=True, slots=True)
class Deadline:
    """The pending deadline of a ticket's current stage."""

    at: datetime
    kind: EventKind
    source: Source


def status_key_of(status: str | None) -> str:
    """Drop the live detail in brackets: 'Planning... (Running: cat)' → 'Planning...'."""
    return (status or "").split(" (")[0].strip()


def is_paused(observation: LinearObservation) -> bool:
    """True while Jaidev waits in its queue or retries an overloaded API provider."""
    return status_key_of(observation.status).startswith(policy.QUEUED_STATUS) or (
        policy.OVERLOADED_MARKER in (observation.timeline or "")
    )


def _plain(text: str) -> str:
    return " ".join(text.split()).lower()


def timeline_kind(timeline: str | None) -> str:
    """The timeline entry without its timestamp, costs, case and extra whitespace."""
    return _plain(_COST.sub("", _TIMESTAMP.sub("", timeline or "")))


def _changed(ticket: TicketState, observation: LinearObservation) -> bool:
    now_seen = (_plain(status_key_of(observation.status)), timeline_kind(observation.timeline))
    before = (_plain(ticket.last_status or ""), timeline_kind(ticket.last_timeline))
    return now_seen != before


def is_baseline(ticket: TicketState, observation: LinearObservation) -> bool:
    """True for the first read after startedAt when it still shows the previous run's comment."""
    if ticket.stage is not Stage.STARTING or ticket.last_linear_at is not None:
        return False
    status_key = _plain(status_key_of(observation.status))
    timeline = _plain(observation.timeline or "")
    new_run = status_key.startswith(tuple(p.lower() for p in NEW_RUN_PREFIXES))
    new_run = new_run or "blocked" in status_key
    return not (new_run or timeline.startswith(STARTED_ENTRY.lower()))


def _stage_for_status(status_key: str, current: Stage | None) -> Stage | None:
    if status_key in PLANNING_STATUSES:
        return Stage.PLAN_FEEDBACK if current is Stage.PLAN_FEEDBACK else Stage.PLANNING
    if "Blocked" in status_key:
        return Stage.BLOCKED
    if status_key in GITHUB_REPORTED_STATUSES:
        return current if current in PR_STAGES else Stage.PR_CI
    for prefix, stage in STATUS_STAGES:
        if status_key.startswith(prefix):
            return stage
    return current


def derive_stage(ticket: TicketState, observation: LinearObservation) -> Stage | None:
    """The stage a Linear observation puts the ticket in; unchanged text keeps the stage."""
    current = ticket.stage
    if is_paused(observation):
        return current or Stage.STARTING
    if not _changed(ticket, observation) or is_baseline(ticket, observation):
        return current
    timeline = observation.timeline or ""
    if timeline.startswith(PLAN_APPROVED_ENTRY):
        return Stage.IMPLEMENTING
    if timeline.startswith(FEEDBACK_ENTRY):
        return Stage.PLAN_FEEDBACK
    stage = _stage_for_status(status_key_of(observation.status), current)
    if current is not None and stage is current:
        return REPLY_STAGES.get(current, current)
    return stage


def enter(
    ticket: TicketState, stage: Stage, at: datetime, *, keep_pause: bool = False
) -> TicketState:
    """Move the ticket into a stage whose clock starts at `at`."""
    return replace(
        ticket,
        stage=stage,
        stage_since=at,
        fired_event=None,
        ack_at=None,
        last_activity_at=None,
        last_linear_at=None,
        last_github_at=None,
        next_linear_at=None,
        next_github_at=None,
        deadline=None,
        deadline_event=None,
        paused_seconds=ticket.paused_seconds if keep_pause else 0,
        queued_since=ticket.queued_since if keep_pause else None,
    )


def _legacy_stage(ticket: TicketState) -> Stage | None:
    if ticket.pr_number is not None:
        return Stage.PR_READY if ticket.last_ci_head else Stage.PR_CI
    if ticket.last_status:
        return _stage_for_status(ticket.last_status, None)
    return None


def reconcile(ticket: TicketState, now: datetime) -> TicketState:
    """Apply the coordinator's stamps and merges, and place a ticket from an older state file."""
    if ticket.merged:
        return ticket if ticket.stage is Stage.DONE else enter(ticket, Stage.DONE, now)
    stamps = [
        (at, stage)
        for at, stage in (
            (ticket.started_at, Stage.STARTING),
            (ticket.feedback_at, Stage.PLAN_FEEDBACK),
            (ticket.approved_at, Stage.APPROVED),
            (ticket.review_at, Stage.PR_REVIEW_SENT),
        )
        if at is not None
    ]
    if stamps:
        at, stage = max(stamps, key=lambda pair: pair[0])
        if ticket.stage is None or ticket.stage_since is None or at > ticket.stage_since:
            return enter(ticket, stage, at)
    if ticket.stage is None:
        legacy = _legacy_stage(ticket)
        if legacy is not None:
            return enter(ticket, legacy, now)
    return ticket


def _once(at: datetime, last: datetime | None) -> datetime | None:
    return at if last is None or last < at else None


def _cadence(first: datetime, every: timedelta, last: datetime | None) -> datetime:
    return first if last is None or last < first else last + every


def _next_linear(ticket: TicketState) -> datetime | None:
    stage, since, last = ticket.stage, ticket.stage_since, ticket.last_linear_at
    if stage is None or since is None or ticket.fired_event is not None:
        return None
    if stage in WAITING_STAGES:
        return None
    if ticket.queued_since is not None:
        return (last or ticket.queued_since) + policy.QUEUED_LINEAR_EVERY
    rules = policy.STAGE_POLICY[stage]
    first = since + rules.linear_first if rules.linear_first is not None else None
    every = rules.linear_every
    if stage is Stage.PLANNING:
        first = since + policy.plan_first_check(ticket.pre_estimate)
    elif stage is Stage.PLAN_FEEDBACK and ticket.ack_at is not None:
        first = ticket.ack_at + _need(rules.after_ack_first, "plan-feedback after_ack_first")
        every = _need(rules.after_ack_every, "plan-feedback after_ack_every")
    elif stage is Stage.IMPLEMENTING:
        first = since + policy.pr_due(ticket.estimate) + _paused(ticket)
    if first is None:
        return None
    return _once(first, last) if every is None else _cadence(first, every, last)


def _paused(ticket: TicketState) -> timedelta:
    return timedelta(seconds=ticket.paused_seconds)


def _next_pr_check(ticket: TicketState, since: datetime, last: datetime | None) -> datetime:
    """Implementing: first at PR due, every 1 min, every 2 min after 2x PR due, after queue time."""
    rules = policy.STAGE_POLICY[Stage.IMPLEMENTING]
    every = _need(rules.github_every, "implementing github_every")
    every_late = _need(rules.github_every_late, "implementing github_every_late")
    due = policy.pr_due(ticket.estimate)
    start = since + _paused(ticket)
    first = start + due
    if last is None or last < first:
        return first
    late = last >= start + due * policy.GITHUB_LATE_FACTOR
    return last + (every_late if late else every)


def _next_github(ticket: TicketState, ci: CiTiming | None, merge_watch: bool) -> datetime | None:
    stage, since, last = ticket.stage, ticket.stage_since, ticket.last_github_at
    if stage is None or since is None:
        return None
    rules = policy.STAGE_POLICY[stage]
    if stage is Stage.IMPLEMENTING:
        return _next_pr_check(ticket, since, last)
    if stage is Stage.PR_CI:
        return None if ci is None else _cadence(since + ci.first_check, ci.interval, last)
    if stage is Stage.PR_READY and not merge_watch:
        return None
    if rules.github_first is None or rules.github_every is None:
        return None
    return _cadence(since + rules.github_first, rules.github_every, last)


def _steps(size: int | None, free: int, step: int) -> int:
    return math.ceil(max(0, (size or 0) - free) / step)


def _base_deadline(ticket: TicketState, ci: CiTiming | None) -> tuple[timedelta, EventKind] | None:
    stage = ticket.stage
    if stage is None:
        return None
    rules = policy.STAGE_POLICY[stage]
    if stage is Stage.PLAN_FEEDBACK and ticket.ack_at is None:
        return (
            _need(rules.ack_deadline, "plan-feedback ack_deadline"),
            _need(rules.ack_event, "plan-feedback ack_event"),
        )
    if rules.deadline_event is None:
        return None
    if stage is Stage.IMPLEMENTING:
        due = policy.pr_due(ticket.estimate)
        extra_attempts = max(0, (ticket.attempt or 1) - 1)
        return due * policy.PR_LATE_FACTOR + due * extra_attempts, rules.deadline_event
    if stage is Stage.PR_CI:
        return None if ci is None else (ci.maximum * policy.CI_LATE_FACTOR, rules.deadline_event)
    deadline = _need(rules.deadline, f"{stage} deadline")
    units = 0
    if stage is Stage.PLANNING:
        units = _steps(ticket.names_bytes, policy.NAMES_FREE_BYTES, policy.NAMES_STEP_BYTES)
        units += max(0, (ticket.repo_count or 1) - 1)
    elif stage is Stage.PLAN_FEEDBACK:
        units = _steps(ticket.feedback_bytes, 0, policy.FEEDBACK_STEP_BYTES)
    elif stage is Stage.PR_REVISING:
        units = ticket.review_comments or 0
    after = deadline + rules.deadline_step * units
    if rules.deadline_cap is not None:
        after = min(after, rules.deadline_cap)
    return after, rules.deadline_event


def pending_deadline(ticket: TicketState, ci: CiTiming | None) -> Deadline | None:
    """The stage's deadline, shifted by time spent queued; None once it has fired."""
    if ticket.stage_since is None or ticket.fired_event is not None:
        return None
    base = _base_deadline(ticket, ci)
    if base is None:
        return None
    after, kind = base
    source = policy.STAGE_POLICY[ticket.stage or Stage.DONE].deadline_source
    if kind is EventKind.NO_ACK:
        source = Source.LINEAR
    at = ticket.stage_since + after + _paused(ticket)
    if kind in QUIET_KINDS and ticket.last_activity_at is not None:
        at = max(at, ticket.last_activity_at + policy.QUIET_BEFORE_LATE)
    return Deadline(at=at, kind=kind, source=source)


def decide(
    ticket: TicketState,
    now: datetime,
    ci_timing: CiTiming | None,
    *,
    merge_watch: bool = False,
) -> Decision:
    """Which checks are due now, and which deadline events fire.

    A deadline fires only once its source was read at or after the deadline, so
    a reached deadline first makes that check due and fires on the read after it.
    """
    ticket = reconcile(ticket, now)
    events: list[Event] = []
    next_linear = _next_linear(ticket)
    next_github = _next_github(ticket, ci_timing, merge_watch)
    linear_due = next_linear is not None and next_linear <= now
    github_due = next_github is not None and next_github <= now
    linear_held = _held(ticket.last_linear_error_at, now)
    github_held = _held(ticket.last_github_error_at, now)
    deadline = pending_deadline(ticket, ci_timing)
    if deadline is not None and ticket.queued_since is None and now >= deadline.at:
        last = ticket.last_linear_at if deadline.source is Source.LINEAR else ticket.last_github_at
        if last is not None and last >= deadline.at:
            detail = f"stage={ticket.stage} due={format_time(deadline.at)}"
            events.append(Event(deadline.kind, ticket=None, detail=detail))
            ticket = replace(ticket, fired_event=deadline.kind)
            next_linear = _next_linear(ticket)
            linear_due = next_linear is not None and next_linear <= now
            deadline = None
        elif deadline.source is Source.LINEAR:
            linear_due = True
        else:
            github_due = True
    linear_due = linear_due and not linear_held
    github_due = github_due and not github_held
    ticket = replace(
        ticket,
        next_linear_at=next_linear,
        next_github_at=next_github,
        deadline=deadline.at if deadline else None,
        deadline_event=deadline.kind if deadline else None,
    )
    return Decision(
        ticket=ticket, linear_due=linear_due, github_due=github_due, events=tuple(events)
    )


def _held(failed_at: datetime | None, now: datetime) -> bool:
    return failed_at is not None and now < failed_at + policy.POLL_ERROR_RETRY


def record_poll_error(ticket: TicketState, source: Source, now: datetime) -> TicketState:
    """Note a failed read, so its retry waits POLL_ERROR_RETRY."""
    if source is Source.LINEAR:
        return replace(ticket, last_linear_error_at=now)
    return replace(ticket, last_github_error_at=now)


def with_ticket_id(events: tuple[Event, ...], ticket_id: str) -> tuple[Event, ...]:
    """Stamp the ticket id on events built without one."""
    return tuple(replace(event, ticket=event.ticket or ticket_id) for event in events)


def _status_event(ticket_id: str, observation: LinearObservation) -> Event | None:
    status_key = status_key_of(observation.status)
    timeline = observation.timeline or ""
    quiet = WORKING_STATUSES | GITHUB_REPORTED_STATUSES
    if status_key in quiet or status_key.startswith(policy.QUEUED_STATUS):
        return None
    if timeline.startswith(COORDINATOR_ENTRIES):
        return None
    detail = f'"{observation.status}" TIMELINE "{observation.timeline}"'
    return Event(EventKind.STATUS, ticket=ticket_id, detail=detail)


def _track_pause(ticket: TicketState, observation: LinearObservation, now: datetime) -> TicketState:
    if is_paused(observation):
        return ticket if ticket.queued_since else replace(ticket, queued_since=now)
    if ticket.queued_since is None:
        return ticket
    paused = int((now - ticket.queued_since).total_seconds())
    return replace(ticket, queued_since=None, paused_seconds=ticket.paused_seconds + paused)


def _note_activity(ticket: TicketState, observation: LinearObservation) -> TicketState:
    """Remember the newest status-comment update; it moves the quiet-before-late deadline."""
    seen = observation.updated_at
    if seen is None or (ticket.last_activity_at is not None and seen <= ticket.last_activity_at):
        return ticket
    return replace(ticket, last_activity_at=seen)


def apply_linear(
    ticket: TicketState, observation: LinearObservation, now: datetime
) -> tuple[TicketState, tuple[Event, ...]]:
    """Fold one Linear read into the ticket; returns the STATUS event when one waits on you."""
    ticket = replace(ticket, last_linear_error_at=None)
    if observation.status is None and observation.timeline is None:
        return replace(ticket, last_linear_at=now), ()
    stage = derive_stage(ticket, observation)
    changed = _changed(ticket, observation) and not is_baseline(ticket, observation)
    if stage is not None and stage is not ticket.stage:
        continuing = (ticket.stage, stage) in CONTINUING and ticket.stage_since is not None
        at = ticket.stage_since if continuing and ticket.stage_since else now
        ticket = enter(ticket, stage, at, keep_pause=continuing)
    ticket = _track_pause(ticket, observation, now)
    if stage is Stage.PLAN_FEEDBACK and changed and ticket.ack_at is None:
        ticket = replace(ticket, ack_at=now)
    ticket = replace(
        ticket,
        last_linear_at=now,
        attempt=observation.attempt if observation.attempt is not None else ticket.attempt,
        last_status=status_key_of(observation.status),
        last_timeline=observation.timeline,
    )
    ticket = _note_activity(ticket, observation)
    event = _status_event(observation.ticket, observation) if changed else None
    return ticket, (event,) if event else ()


def apply_github(
    ticket: TicketState, pr: GithubObservation | None, now: datetime
) -> tuple[TicketState, tuple[Event, ...]]:
    """Fold one GitHub read into the ticket: a new head restarts the CI clock."""
    ticket = replace(ticket, last_github_error_at=None)
    if pr is None:
        return replace(ticket, last_github_at=now), ()
    ticket = replace(ticket, pr_number=pr.number)
    if pr.state in (PrState.MERGED, PrState.CLOSED):
        ticket = enter(replace(ticket, merged=True), Stage.DONE, now)
        kind = EventKind.MERGED if pr.state is PrState.MERGED else EventKind.CLOSED
        detail = f"#{pr.number}" if kind is EventKind.MERGED else f"unmerged #{pr.number}"
        return replace(ticket, last_github_at=now), (Event(kind, None, detail),)
    if pr.head != ticket.pr_head:
        if pr.head != ticket.last_ci_head:
            ticket = enter(ticket, Stage.PR_CI, now)
        ticket = replace(ticket, pr_head=pr.head)
    ticket = replace(ticket, last_github_at=now)
    if ticket.stage is not Stage.PR_CI or pr.ci is CiResult.PENDING:
        return ticket, ()
    events: tuple[Event, ...] = ()
    if ticket.last_ci_head != pr.head:
        detail = f"{pr.ci} #{pr.number} head={pr.head}"
        if pr.known_failed:
            detail += f" (known: {', '.join(pr.known_failed)})"
        events = (Event(EventKind.CI, None, detail),)
    ticket = replace(ticket, last_ci_head=pr.head, sonar_findings=pr.sonar_findings)
    if pr.ci is CiResult.FAILED:
        # Jaidev fixes a failed head on its own; poll GitHub for its push.
        ticket = replace(enter(ticket, Stage.PR_REVISING, now), review_comments=None)
    else:
        ticket = enter(ticket, Stage.PR_READY, now)
    return replace(ticket, last_github_at=now), events


def is_idle(ticket: TicketState) -> bool:
    """True when the ticket has no next check and no pending deadline."""
    return (
        ticket.next_linear_at is None and ticket.next_github_at is None and ticket.deadline is None
    )

"""Typed values shared by the watcher: stages, events, observations and ticket state."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Final

ZERO: Final = timedelta(0)


class Stage(StrEnum):
    """Where a ticket stands in a Jaidev run."""

    STARTING = "starting"
    PLANNING = "planning"
    QUESTIONS = "questions"
    PLAN_READY = "plan-ready"
    PLAN_FEEDBACK = "plan-feedback"
    APPROVED = "approved"
    IMPLEMENTING = "implementing"
    BLOCKED = "blocked"
    PR_CI = "pr-ci"
    PR_READY = "pr-ready"
    PR_REVIEW_SENT = "pr-review-sent"
    PR_REVISING = "pr-revising"
    DONE = "done"


class EventKind(StrEnum):
    """The keyword of an event line on stdout."""

    STATUS = "STATUS"
    CI = "CI"
    MERGED = "MERGED"
    CLOSED = "CLOSED"
    NO_START = "NO START"
    PLAN_LATE = "PLAN LATE"
    NO_ACK = "NO ACK"
    PR_LATE = "PR LATE"
    CI_LATE = "CI LATE"
    FIX_LATE = "FIX LATE"
    LINEAR_POLL_ERROR = "LINEAR POLL ERROR"
    GITHUB_POLL_ERROR = "GITHUB POLL ERROR"
    ALL_MERGED = "ALL MERGED"
    IDLE = "IDLE"


POLL_ERRORS: Final = frozenset({EventKind.LINEAR_POLL_ERROR, EventKind.GITHUB_POLL_ERROR})


class Source(StrEnum):
    """Where the scheduler looks for an answer."""

    LINEAR = "linear"
    GITHUB = "github"


class CiResult(StrEnum):
    """The settled outcome of a PR head's checks."""

    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"


class PrState(StrEnum):
    """GitHub pull request state."""

    OPEN = "OPEN"
    MERGED = "MERGED"
    CLOSED = "CLOSED"


@dataclass(frozen=True, slots=True)
class Event:
    """One line the coordinator reads on stdout."""

    kind: EventKind
    ticket: str | None = None
    detail: str = ""

    def render(self) -> str:
        """Format the event as its stdout line."""
        if self.kind in POLL_ERRORS:
            parts = [str(self.kind), self.ticket or "", self.detail]
        else:
            parts = [self.ticket or "", str(self.kind), self.detail]
        return " ".join(part for part in parts if part)


@dataclass(frozen=True, slots=True)
class CiTiming:
    """One repo's row of `ci-check-timing.md`."""

    repo: str
    check_name: str
    settles_on: tuple[str, ...]
    minimum: timedelta
    maximum: timedelta
    mean: timedelta
    first_check: timedelta
    interval: timedelta


@dataclass(frozen=True, slots=True)
class StagePolicy:
    """The fixed numbers of one stage; schedule.py adds the dynamic inputs."""

    linear_first: timedelta | None = None
    linear_every: timedelta | None = None
    github_first: timedelta | None = None
    github_every: timedelta | None = None
    github_every_late: timedelta | None = None
    ack_deadline: timedelta | None = None
    ack_event: EventKind | None = None
    after_ack_first: timedelta | None = None
    after_ack_every: timedelta | None = None
    deadline: timedelta | None = None
    deadline_event: EventKind | None = None
    deadline_source: Source = Source.LINEAR
    deadline_step: timedelta = ZERO
    deadline_cap: timedelta | None = None


@dataclass(frozen=True, slots=True)
class LinearObservation:
    """One ticket's Jaidev status comment, as the Haiku call read it."""

    ticket: str
    status: str | None
    timeline: str | None
    attempt: int | None = None


@dataclass(frozen=True, slots=True)
class GithubObservation:
    """One ticket's Jaidev PR, with its CI already judged by the settle rule."""

    number: int
    head: str
    state: PrState
    ci: CiResult
    sonar_findings: bool


@dataclass(frozen=True, slots=True)
class TicketState:
    """One ticket's entry in the state file; unknown keys ride along in `extra`."""

    agent: str | None = None
    repo_dir: str | None = None
    color: str | None = None
    pr_number: int | None = None
    pr_head: str | None = None
    last_ci_head: str | None = None
    last_status: str | None = None
    last_timeline: str | None = None
    merged: bool = False
    stage: Stage | None = None
    stage_since: datetime | None = None
    started_at: datetime | None = None
    feedback_at: datetime | None = None
    approved_at: datetime | None = None
    review_at: datetime | None = None
    pre_estimate: int | None = None
    names_bytes: int | None = None
    feedback_bytes: int | None = None
    estimate: int | None = None
    review_comments: int | None = None
    repo_count: int | None = None
    attempt: int | None = None
    queued_since: datetime | None = None
    paused_seconds: int = 0
    ack_at: datetime | None = None
    sonar_findings: bool | None = None
    last_linear_at: datetime | None = None
    last_github_at: datetime | None = None
    next_linear_at: datetime | None = None
    next_github_at: datetime | None = None
    deadline: datetime | None = None
    deadline_event: EventKind | None = None
    fired_event: EventKind | None = None
    extra: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class WaveState:
    """The whole state file."""

    tickets: Mapping[str, TicketState] = field(default_factory=dict)
    extra: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Decision:
    """What one tick does for one ticket: the checks due, and the events to print."""

    ticket: TicketState
    linear_due: bool
    github_due: bool
    events: tuple[Event, ...] = ()


def parse_time(text: str) -> datetime:
    """Parse an ISO 8601 timestamp into an aware UTC datetime; a naive value counts as UTC."""
    value = datetime.fromisoformat(text.strip().replace("Z", "+00:00"))
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def format_time(value: datetime) -> str:
    """Format an aware datetime as `YYYY-MM-DDTHH:MM:SSZ`."""
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

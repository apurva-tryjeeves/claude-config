"""Every number the scheduler uses: the per-stage table and the estimate tables.

Each stage's clock starts at its `stageSince`: the coordinator's stamp for
`starting`, `plan-feedback`, `approved` and `pr-review-sent`, `startedAt` for
`planning`, `approvedAt` for `implementing`, and the moment the watcher saw the
change for the rest. A stage moves to measured values once
`jaidev-run-timings.md` holds 3 runs of it.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import timedelta
from types import MappingProxyType
from typing import Final

from jaidev_watch.models import CiTiming, EventKind, Source, Stage, StagePolicy


def _s(seconds: int) -> timedelta:
    return timedelta(seconds=seconds)


def _m(minutes: int) -> timedelta:
    return timedelta(minutes=minutes)


STAGE_POLICY: Final[Mapping[Stage, StagePolicy]] = MappingProxyType(
    {
        Stage.STARTING: StagePolicy(
            linear_first=_s(30),
            deadline=_m(2),
            deadline_event=EventKind.NO_START,
        ),
        # linear_first comes from PLAN_FIRST_CHECK; deadline_step is per 10 KB of
        # names comment over 10 KB and per extra repo.
        Stage.PLANNING: StagePolicy(
            linear_every=_m(1),
            deadline=_m(10),
            deadline_event=EventKind.PLAN_LATE,
            deadline_step=_m(1),
        ),
        Stage.QUESTIONS: StagePolicy(),
        Stage.PLAN_READY: StagePolicy(),
        # deadline_step is per 5 KB of feedback.
        Stage.PLAN_FEEDBACK: StagePolicy(
            linear_first=_s(30),
            ack_deadline=_m(1),
            ack_event=EventKind.NO_ACK,
            after_ack_first=_m(1),
            after_ack_every=_s(30),
            deadline=_m(4),
            deadline_event=EventKind.PLAN_LATE,
            deadline_step=_m(1),
        ),
        Stage.APPROVED: StagePolicy(
            linear_first=_s(30),
            deadline=_m(1),
            deadline_event=EventKind.NO_START,
        ),
        # First checks and the deadline come from PR_DUE_BY_ESTIMATE.
        Stage.IMPLEMENTING: StagePolicy(
            linear_every=_m(3),
            github_every=_m(1),
            github_every_late=_m(2),
            deadline_event=EventKind.PR_LATE,
            deadline_source=Source.GITHUB,
        ),
        Stage.BLOCKED: StagePolicy(),
        # Cadence and deadline come from the repo's CiTiming.
        Stage.PR_CI: StagePolicy(
            deadline_event=EventKind.CI_LATE,
            deadline_source=Source.GITHUB,
        ),
        # The Linear check runs only when SonarCloud reported findings; the
        # GitHub check runs only with --merge-watch.
        Stage.PR_READY: StagePolicy(
            linear_first=_m(1),
            github_first=_m(15),
            github_every=_m(15),
        ),
        Stage.PR_REVIEW_SENT: StagePolicy(
            linear_first=_s(30),
            linear_every=_m(1),
            deadline=_m(2),
            deadline_event=EventKind.NO_ACK,
        ),
        # deadline_step is per review comment posted.
        Stage.PR_REVISING: StagePolicy(
            github_first=_m(1),
            github_every=_m(1),
            deadline=_m(2),
            deadline_event=EventKind.FIX_LATE,
            deadline_source=Source.GITHUB,
            deadline_step=_m(1),
            deadline_cap=_m(10),
        ),
        Stage.DONE: StagePolicy(),
    }
)

# While Jaidev's timeline shows "Queued" or the overload retry, deadlines pause
# and Linear is read at this pace until it recovers.
QUEUED_LINEAR_EVERY: Final = _m(2)
QUEUED_STATUS: Final = "Queued"
OVERLOADED_MARKER: Final = "API provider overloaded"

# Planning: first Linear check after startedAt, by the pre-plan Linear estimate.
PLAN_FIRST_CHECK: Final[tuple[tuple[int, timedelta], ...]] = ((1, _m(2)), (3, _m(3)))
PLAN_FIRST_CHECK_LARGE: Final = _m(4)
PLAN_FIRST_CHECK_UNKNOWN: Final = _m(3)
NAMES_FREE_BYTES: Final = 10 * 1024
NAMES_STEP_BYTES: Final = 10 * 1024
FEEDBACK_STEP_BYTES: Final = 5 * 1024

# Implementing: first GitHub check after plan:approved, by Jaidev's estimate.
PR_DUE_BY_ESTIMATE: Final[tuple[tuple[int, timedelta], ...]] = (
    (1, _m(4)),
    (2, _m(4)),
    (3, _m(6)),
)
PR_DUE_LARGE: Final = _m(8)
GITHUB_LATE_FACTOR: Final = 2
PR_LATE_FACTOR: Final = 3

# PR CI: the deadline is this multiple of the repo's slowest observed run.
CI_LATE_FACTOR: Final = 1.5

# Used for a repo with no ci-check-timing.md row until the coordinator adds one.
FALLBACK_CI_TIMING: Final = CiTiming(
    repo="(no row)",
    check_name="",
    settles_on=(),
    minimum=_m(1),
    maximum=_m(20),
    mean=_m(10),
    first_check=_m(2),
    interval=_m(3),
)


def plan_first_check(pre_estimate: int | None) -> timedelta:
    """Delay from startedAt to the first planning check, by the pre-plan estimate."""
    if pre_estimate is None:
        return PLAN_FIRST_CHECK_UNKNOWN
    for ceiling, delay in PLAN_FIRST_CHECK:
        if pre_estimate <= ceiling:
            return delay
    return PLAN_FIRST_CHECK_LARGE


def pr_due(estimate: int | None) -> timedelta:
    """Delay from plan:approved to the first GitHub check, by Jaidev's estimate."""
    if estimate is None:
        return PR_DUE_LARGE
    for ceiling, delay in PR_DUE_BY_ESTIMATE:
        if estimate <= ceiling:
            return delay
    return PR_DUE_LARGE

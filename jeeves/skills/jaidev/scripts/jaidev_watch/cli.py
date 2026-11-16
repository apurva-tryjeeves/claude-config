"""Command line: `watch`, `due`, `explain` and `state get|set|init`.

Events go to stdout, one per line; diagnostics go to stderr through logging.
Exit codes: 0 events printed, 1 runtime error, 2 usage error, 3 idle, 4 stopped by a signal.
"""

from __future__ import annotations

import argparse
import json
import logging
import signal
import sys
import time
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path
from types import FrameType
from typing import Final

from jaidev_watch import ci_derive, ci_timing, github_poll, linear_poll, schedule, state_store
from jaidev_watch.models import (
    CiTiming,
    Event,
    EventKind,
    GithubObservation,
    LinearObservation,
    Source,
    Stage,
    TicketState,
    WaveState,
    format_time,
    parse_time,
)
from jaidev_watch.policy import POLL_ERROR_RETRY

EXIT_EVENT: Final = 0
EXIT_ERROR: Final = 1
EXIT_USAGE: Final = 2
EXIT_IDLE: Final = 3
EXIT_STOPPED: Final = 4
TICK_SECONDS: Final = 30
ERROR_CHARS: Final = 200
INPUT_KEYS: Final = frozenset(
    {"preEstimate", "namesBytes", "feedbackBytes", "estimate", "reviewComments", "repoCount"}
    | {"attempt", "prNumber"}
)

log = logging.getLogger("jaidev_watch")

Emit = Callable[[Sequence[Event]], None]
LinearReader = Callable[[Sequence[str]], Sequence[LinearObservation]]
GithubReader = Callable[[str, Path, Sequence[str] | None], GithubObservation | None]
TimingLookup = Callable[[TicketState], CiTiming | None]
Notices = Callable[[], Sequence[Event]]


class UsageError(Exception):
    """A command was given arguments it cannot use."""


class StopRequested(Exception):
    """SIGTERM or SIGINT arrived while watching."""


@dataclass(frozen=True, slots=True)
class Pollers:
    """The shell's readers, injected so tests run without subprocesses."""

    timing_for: TimingLookup
    read_linear: LinearReader
    read_github: GithubReader
    notices: Notices = lambda: ()
    requeue: Callable[[Sequence[Event]], None] = lambda events: None


@dataclass(frozen=True, slots=True)
class TickResult:
    """What one tick printed, and whether every ticket has gone quiet."""

    events: tuple[Event, ...]
    idle: bool


def utc_now() -> datetime:
    """The current time in UTC, to the second."""
    return datetime.now(UTC).replace(microsecond=0)


# Stages that read CI, and so need the repo's timing row.
CI_STAGES: Final = frozenset(
    {Stage.IMPLEMENTING, Stage.PR_CI, Stage.PR_READY, Stage.PR_REVIEW_SENT, Stage.PR_REVISING}
)


@dataclass(frozen=True, slots=True)
class RowDeriver:
    """How CiRows derives, writes and holds a missing row."""

    derive: Callable[[str], ci_derive.DerivedRow]
    write: Callable[[ci_derive.DerivedRow], bool]
    hold: Path | None = None
    now: Callable[[], datetime] = utc_now


class CiRows:
    """Each ticket's CI row by repo; a missing row is derived once, the git-preferences way."""

    def __init__(
        self,
        timings: Mapping[str, CiTiming],
        deriver: RowDeriver | None = None,
        resolve: Callable[[str | None], str] = ci_derive.resolve_repo,
    ) -> None:
        self._timings = dict(timings)
        self._resolve = resolve
        self._derive = deriver.derive if deriver else None
        self._write = deriver.write if deriver else None
        self._hold = deriver.hold if deriver else None
        self._now = deriver.now if deriver else utc_now
        self._repos: dict[str, str] = {}
        self._missing: set[str] = set()
        self._notices: list[Event] = []

    def _repo(self, repo_dir: str | None) -> str:
        key = repo_dir or "."
        if key not in self._repos:
            self._repos[key] = self._resolve(repo_dir)
        return self._repos[key]

    def for_ticket(self, ticket: TicketState) -> CiTiming | None:
        """The ticket's row; None until a row exists for its repo."""
        repo = self._repo(ticket.repo_dir)
        found = self._timings.get(repo)
        if found is not None or self._derive is None:
            return found
        if ticket.stage not in CI_STAGES or repo in self._missing or self._held(repo):
            return None
        try:
            row = self._derive(repo)
        except ci_derive.CiDeriveError as error:
            self._missing.add(repo)
            self._record_failure(repo)
            self._notices.append(Event(EventKind.CI_ROW_MISSING, detail=f"{repo} {error}"))
            return None
        self._timings[repo] = row.timing
        self._notices.append(Event(EventKind.CI_ROW_ADDED, detail=self._write_detail(row)))
        return row.timing

    def _write_detail(self, row: ci_derive.DerivedRow) -> str:
        repo, line = row.timing.repo, ci_derive.format_row(row)
        try:
            written = self._write(row) if self._write else False
        except OSError as error:
            return f"{repo} (not written: {error.strerror or error}) {line}"
        return repo if written else f"{repo} (not written) {line}"

    def _failures(self) -> dict[str, str]:
        if self._hold is None:
            return {}
        try:
            data = json.loads(self._hold.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return {str(k): str(v) for k, v in data.items()} if isinstance(data, dict) else {}

    def _held(self, repo: str) -> bool:
        """True within POLL_ERROR_RETRY of a failed derivation, across watch runs."""
        failed = self._failures().get(repo)
        try:
            return failed is not None and self._now() < parse_time(failed) + POLL_ERROR_RETRY
        except ValueError:
            return False

    def _record_failure(self, repo: str) -> None:
        if self._hold is None:
            return
        failures = {**self._failures(), repo: format_time(self._now())}
        try:
            state_store.write_text_atomic(self._hold, json.dumps(failures) + "\n")
        except OSError as error:
            log.warning("cannot record the CI row failure in %s: %s", self._hold, error)

    def notices(self) -> list[Event]:
        """The row events since the last call."""
        out, self._notices = self._notices, []
        return out

    def requeue(self, events: Sequence[Event]) -> None:
        """Put back row events whose print failed."""
        self._notices = [*events, *self._notices]


def _settles_on(timing: CiTiming | None) -> Sequence[str] | None:
    return None if timing is None else timing.settles_on


def _first_line(error: Exception) -> str:
    text = str(error).strip()
    return (text.splitlines()[0] if text else type(error).__name__)[:ERROR_CHARS]


def _due_checks(
    wave: WaveState, now: datetime, timing_for: TimingLookup, merge_watch: bool
) -> tuple[list[str], list[str]]:
    linear: list[str] = []
    github: list[str] = []
    for ticket_id, ticket in wave.tickets.items():
        decision = schedule.decide(ticket, now, timing_for(ticket), merge_watch=merge_watch)
        if decision.linear_due:
            linear.append(ticket_id)
        if decision.github_due:
            github.append(ticket_id)
    return linear, github


def _ignore(events: Sequence[Event]) -> None:
    """An emitter that prints nothing."""


def print_events(events: Sequence[Event]) -> None:
    """Print event lines and flush, so they are out before the state commits."""
    print("\n".join(event.render() for event in events), flush=True)


@dataclass(slots=True)
class Reads:
    """What phase 2 of a tick read, and which reads failed."""

    linear: dict[str, LinearObservation] = field(default_factory=dict)
    github: dict[str, GithubObservation | None] = field(default_factory=dict)
    linear_failed: set[str] = field(default_factory=set)
    github_failed: set[str] = field(default_factory=set)
    events: list[Event] = field(default_factory=list)


def _read_linear(reads: Reads, linear_ids: Sequence[str], read_linear: LinearReader) -> None:
    try:
        replies = {obs.ticket.upper(): obs for obs in read_linear(linear_ids)}
    except linear_poll.LinearPollError as error:
        reads.events.append(Event(EventKind.LINEAR_POLL_ERROR, detail=_first_line(error)))
        reads.linear_failed.update(linear_ids)
        return
    for ticket_id in linear_ids:
        row = replies.get(ticket_id.upper())
        if row is None:
            reads.events.append(
                Event(EventKind.LINEAR_POLL_ERROR, ticket_id, "missing from the reply")
            )
            reads.linear_failed.add(ticket_id)
        else:
            reads.linear[ticket_id] = replace(row, ticket=ticket_id)


def _read_github(
    reads: Reads, wave: WaveState, github_ids: Sequence[str], pollers: Pollers
) -> None:
    for ticket_id in github_ids:
        ticket = wave.tickets[ticket_id]
        try:
            reads.github[ticket_id] = pollers.read_github(
                ticket_id, Path(ticket.repo_dir or "."), _settles_on(pollers.timing_for(ticket))
            )
        except github_poll.GithubPollError as error:
            reads.events.append(Event(EventKind.GITHUB_POLL_ERROR, ticket_id, _first_line(error)))
            reads.github_failed.add(ticket_id)


def _apply_reads(
    ticket_id: str, ticket: TicketState, reads: Reads, now: datetime, fresh_read: bool
) -> tuple[TicketState, list[Event]]:
    """Fold one ticket's reads in; a read that crossed a stage change is dropped."""
    events: list[Event] = []
    if ticket_id in reads.linear_failed:
        ticket = schedule.record_poll_error(ticket, Source.LINEAR, now)
    if ticket_id in reads.github_failed:
        ticket = schedule.record_poll_error(ticket, Source.GITHUB, now)
    if not fresh_read:
        return ticket, events
    if ticket_id in reads.linear:
        ticket, found = schedule.apply_linear(ticket, reads.linear[ticket_id], now)
        events.extend(found)
    if ticket_id in reads.github:
        ticket, found = schedule.apply_github(ticket, reads.github[ticket_id], now)
        events.extend(schedule.with_ticket_id(found, ticket_id))
    return ticket, events


def run_tick(
    path: Path,
    now: datetime,
    pollers: Pollers,
    *,
    emit: Emit = _ignore,
    merge_watch: bool = False,
) -> TickResult:
    """One tick: decide, poll the due tickets without the lock, then apply under it.

    The events are emitted before the new state is saved, so a failed print
    leaves the old state and the next tick emits them again.
    """
    with state_store.locked(path):
        wave = state_store.load(path)
    linear_ids, github_ids = _due_checks(wave, now, pollers.timing_for, merge_watch)
    read_from = {tid: schedule.reconcile(t, now) for tid, t in wave.tickets.items()}
    reads = Reads()
    if linear_ids:
        _read_linear(reads, linear_ids, pollers.read_linear)
    _read_github(reads, wave, github_ids, pollers)
    events = reads.events

    def apply(fresh: WaveState) -> WaveState:
        tickets: dict[str, TicketState] = {}
        for ticket_id, stored in fresh.tickets.items():
            ticket = schedule.reconcile(stored, now)
            before = read_from.get(ticket_id)
            same_stage = before is not None and (ticket.stage, ticket.stage_since) == (
                before.stage,
                before.stage_since,
            )
            ticket, found = _apply_reads(ticket_id, ticket, reads, now, same_stage)
            events.extend(found)
            timing = pollers.timing_for(ticket)
            decision = schedule.decide(ticket, now, timing, merge_watch=merge_watch)
            events.extend(schedule.with_ticket_id(decision.events, ticket_id))
            tickets[ticket_id] = decision.ticket
        notices = list(pollers.notices())
        events.extend(notices)
        if tickets and all(t.stage is Stage.DONE for t in tickets.values()):
            events.append(Event(EventKind.ALL_MERGED))
        if events:
            try:
                emit(tuple(events))
            except BaseException:
                pollers.requeue(notices)
                raise
        return replace(fresh, tickets=tickets)

    after = state_store.update(path, apply)
    idle = all(schedule.is_idle(t) for t in after.tickets.values())
    return TickResult(events=tuple(events), idle=idle)


@contextmanager
def stop_on_signals() -> Iterator[None]:
    """Turn SIGTERM and SIGINT into StopRequested for the duration."""

    def handler(signum: int, frame: FrameType | None) -> None:
        raise StopRequested(signal.Signals(signum).name)

    previous = {sig: signal.signal(sig, handler) for sig in (signal.SIGTERM, signal.SIGINT)}
    try:
        yield
    finally:
        for sig, old in previous.items():
            signal.signal(sig, old)


def live_pollers(path: Path, tool: str, timings: Mapping[str, CiTiming], table: Path) -> Pollers:
    """Pollers that run claude, gh and git, and derive missing CI rows."""
    deriver = RowDeriver(
        derive=ci_derive.derive_row,
        write=lambda row: ci_derive.write_row(row, table),
        hold=path.with_suffix(".ci-hold.json"),
    )
    rows = CiRows(timings, deriver)
    usage_log = path.with_suffix(".usage.log")

    def read_linear(ticket_ids: Sequence[str]) -> Sequence[LinearObservation]:
        return linear_poll.read_statuses(ticket_ids, usage_log, utc_now(), tool=tool)

    def read_github(
        ticket_id: str, repo_dir: Path, settles_on: Sequence[str] | None
    ) -> GithubObservation | None:
        return github_poll.read_pr(ticket_id, repo_dir, settles_on)

    return Pollers(rows.for_ticket, read_linear, read_github, rows.notices, rows.requeue)


def cmd_watch(args: argparse.Namespace) -> int:
    """Tick until events, idle or a stop signal."""
    path: Path = args.state_file
    pollers = live_pollers(path, args.tool, ci_timing.load(args.ci_timing), args.ci_timing)
    try:
        with stop_on_signals():
            while True:
                result = run_tick(
                    path, utc_now(), pollers, emit=print_events, merge_watch=args.merge_watch
                )
                if result.events:
                    return EXIT_EVENT
                if result.idle:
                    print(EventKind.IDLE, flush=True)
                    return EXIT_IDLE
                time.sleep(TICK_SECONDS)
    except StopRequested as stop:
        log.info("stopped by %s", stop)
        return EXIT_STOPPED


def _at(args: argparse.Namespace) -> datetime:
    if not args.at:
        return utc_now()
    try:
        return parse_time(args.at)
    except ValueError as error:
        raise UsageError(f"--at: {error}") from error


def _show(value: datetime | None) -> str:
    return format_time(value) if value else "—"


def cmd_due(args: argparse.Namespace) -> int:
    """Print the checks a tick would run now; poll nothing."""
    with state_store.locked(args.state_file):
        wave = state_store.load(args.state_file)
    timing_for = CiRows(ci_timing.load(args.ci_timing)).for_ticket
    linear, github = _due_checks(wave, _at(args), timing_for, args.merge_watch)
    lines = [f"{t} linear" for t in linear] + [f"{t} github" for t in github]
    print("\n".join(lines) if lines else "NONE")
    return EXIT_EVENT if lines else EXIT_IDLE


def cmd_explain(args: argparse.Namespace) -> int:
    """Print each ticket's stage, next checks and deadline as a tick would see them."""
    with state_store.locked(args.state_file):
        wave = state_store.load(args.state_file)
    timing_for = CiRows(ci_timing.load(args.ci_timing)).for_ticket
    now = _at(args)
    print(f"at {format_time(now)}")
    for ticket_id, stored in wave.tickets.items():
        timing = timing_for(stored)
        decision = schedule.decide(stored, now, timing, merge_watch=args.merge_watch)
        t = decision.ticket
        flags = (("linear", decision.linear_due), ("github", decision.github_due))
        due = [name for name, flag in flags if flag]
        inputs = {
            key: value for key, value in state_store.ticket_to_json(t).items() if key in INPUT_KEYS
        }
        print(
            f"{ticket_id} {t.stage or '—'} since={_show(t.stage_since)} "
            f"linear={_show(t.next_linear_at)} github={_show(t.next_github_at)} "
            f"deadline={_show(t.deadline)} {t.deadline_event or ''}".rstrip()
        )
        print(
            f"  ci={timing.repo if timing else '(no row)'} due-now={','.join(due) or 'none'} "
            f"fired={t.fired_event or 'none'} inputs={json.dumps(inputs)}"
        )
        for event in schedule.with_ticket_id(decision.events, ticket_id):
            print(f"  would print: {event.render()}")
    return EXIT_EVENT


def _require(wave: WaveState, ticket_id: str) -> TicketState:
    ticket = wave.tickets.get(ticket_id)
    if ticket is None:
        raise UsageError(f"unknown ticket {ticket_id}; run state init first")
    return ticket


def _print_ticket(ticket: TicketState | None) -> None:
    data = None if ticket is None else state_store.ticket_to_json(ticket)
    print(json.dumps(data, ensure_ascii=False))


def cmd_state(args: argparse.Namespace) -> int:
    """Read or change one ticket under the shared lock."""
    path: Path = args.state_file
    ticket_id: str = args.ticket
    now = utc_now()
    if args.action == "get":
        with state_store.locked(path):
            _print_ticket(state_store.load(path).tickets.get(ticket_id))
        return EXIT_EVENT

    def change(wave: WaveState) -> WaveState:
        if args.action == "init":
            if ticket_id in wave.tickets and not args.force:
                raise UsageError(f"{ticket_id} exists; pass --force to replace it")
            ticket = TicketState(agent=args.agent, repo_dir=args.repo_dir)
        else:
            ticket = _require(wave, ticket_id)
            value = state_store.parse_value(args.field, args.value, now)
            if args.field == "stage" and isinstance(value, Stage):
                ticket = schedule.enter(ticket, value, now)
            else:
                ticket = state_store.set_field(ticket, args.field, value)
        return replace(wave, tickets={**wave.tickets, ticket_id: ticket})

    after = state_store.update(path, change)
    _print_ticket(after.tickets[ticket_id])
    return EXIT_EVENT


def build_parser() -> argparse.ArgumentParser:
    """The argparse tree for every subcommand."""
    parser = argparse.ArgumentParser(prog="python3 -m jaidev_watch", description=__doc__)
    parser.add_argument("-v", "--verbose", action="store_true", help="log INFO to stderr")
    commands = parser.add_subparsers(dest="command", required=True)

    def with_schedule_options(sub: argparse.ArgumentParser) -> None:
        sub.add_argument("state_file", type=Path)
        sub.add_argument("--ci-timing", type=Path, default=ci_timing.table_path())
        sub.add_argument(
            "--merge-watch", action="store_true", help="check pr-ready PRs for merges every 15 min"
        )

    watch = commands.add_parser("watch", help="tick every 30 s until an event or idle")
    with_schedule_options(watch)
    watch.add_argument("--tool", default=linear_poll.DEFAULT_TOOL, help="Linear list_comments tool")
    watch.set_defaults(handler=cmd_watch)

    for name, handler, text in (
        ("due", cmd_due, "print the checks due now; poll nothing"),
        ("explain", cmd_explain, "print each ticket's stage, next checks and deadline"),
    ):
        sub = commands.add_parser(name, help=text)
        with_schedule_options(sub)
        sub.add_argument("--at", help="evaluate at this ISO time instead of now")
        sub.set_defaults(handler=handler)

    state = commands.add_parser("state", help="read or change the state file")
    actions = state.add_subparsers(dest="action", required=True)
    get = actions.add_parser("get", help="print one ticket")
    get.add_argument("state_file", type=Path)
    get.add_argument("ticket")
    put = actions.add_parser("set", help="set one field: `now` for times, `null` clears")
    put.add_argument("state_file", type=Path)
    put.add_argument("ticket")
    put.add_argument("field")
    put.add_argument("value")
    init = actions.add_parser("init", help="add a ticket")
    init.add_argument("state_file", type=Path)
    init.add_argument("ticket")
    init.add_argument("agent")
    init.add_argument("repo_dir")
    init.add_argument("--force", action="store_true", help="replace an existing ticket")
    state.set_defaults(handler=cmd_state)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Parse arguments, run the subcommand, and map errors to exit codes."""
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        stream=sys.stderr,
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    handler: Callable[[argparse.Namespace], int] = args.handler
    try:
        return handler(args)
    except (UsageError, ValueError) as error:
        log.error("%s", error)
        return EXIT_USAGE
    except (state_store.StateFileError, ci_timing.CiTimingError, OSError) as error:
        log.error("%s", error)
        return EXIT_ERROR

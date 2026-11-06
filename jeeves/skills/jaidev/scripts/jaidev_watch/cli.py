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
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from types import FrameType
from typing import Final

from jaidev_watch import ci_timing, github_poll, linear_poll, policy, schedule, state_store
from jaidev_watch.models import (
    CiTiming,
    Event,
    EventKind,
    GithubObservation,
    LinearObservation,
    Stage,
    TicketState,
    WaveState,
    format_time,
    parse_time,
)

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

LinearReader = Callable[[Sequence[str]], Sequence[LinearObservation]]
GithubReader = Callable[[str, Path, Sequence[str]], GithubObservation | None]
TimingLookup = Callable[[TicketState], CiTiming]


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


@dataclass(frozen=True, slots=True)
class TickResult:
    """What one tick printed, and whether every ticket has gone quiet."""

    events: tuple[Event, ...]
    idle: bool


def utc_now() -> datetime:
    """The current time in UTC, to the second."""
    return datetime.now(UTC).replace(microsecond=0)


def timing_lookup(timings: Mapping[str, CiTiming]) -> TimingLookup:
    """Pick each ticket's CI row by its repo; warn once for a repo without a row."""
    warned: set[str] = set()

    def lookup(ticket: TicketState) -> CiTiming:
        repo = ci_timing.repo_name(ticket.repo_dir)
        found = timings.get(repo)
        if found is not None:
            return found
        if repo not in warned:
            warned.add(repo)
            log.warning("no ci-check-timing.md row for %s; add one, using the fallback", repo)
        return policy.FALLBACK_CI_TIMING

    return lookup


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


def run_tick(
    path: Path, now: datetime, pollers: Pollers, *, merge_watch: bool = False
) -> TickResult:
    """One tick: decide, poll the due tickets without the lock, then apply under it."""
    timing_for, read_linear, read_github = (
        pollers.timing_for,
        pollers.read_linear,
        pollers.read_github,
    )
    with state_store.locked(path):
        wave = state_store.load(path)
    linear_ids, github_ids = _due_checks(wave, now, timing_for, merge_watch)

    events: list[Event] = []
    linear_obs: dict[str, LinearObservation] = {}
    if linear_ids:
        try:
            replies = {obs.ticket.upper(): obs for obs in read_linear(linear_ids)}
            for ticket_id in linear_ids:
                found_row = replies.get(ticket_id.upper())
                if found_row is None:
                    events.append(
                        Event(EventKind.LINEAR_POLL_ERROR, ticket_id, "missing from the reply")
                    )
                    continue
                linear_obs[ticket_id] = replace(found_row, ticket=ticket_id)
        except linear_poll.LinearPollError as error:
            events.append(Event(EventKind.LINEAR_POLL_ERROR, detail=_first_line(error)))
    github_obs: dict[str, GithubObservation | None] = {}
    for ticket_id in github_ids:
        ticket = wave.tickets[ticket_id]
        try:
            github_obs[ticket_id] = read_github(
                ticket_id, Path(ticket.repo_dir or "."), timing_for(ticket).settles_on
            )
        except github_poll.GithubPollError as error:
            events.append(Event(EventKind.GITHUB_POLL_ERROR, ticket_id, _first_line(error)))

    def apply(fresh: WaveState) -> WaveState:
        tickets: dict[str, TicketState] = {}
        for ticket_id, stored in fresh.tickets.items():
            ticket = schedule.reconcile(stored, now)
            found: tuple[Event, ...] = ()
            if ticket_id in linear_obs:
                ticket, found = schedule.apply_linear(ticket, linear_obs[ticket_id], now)
                events.extend(found)
            if ticket_id in github_obs:
                ticket, found = schedule.apply_github(ticket, github_obs[ticket_id], now)
                events.extend(schedule.with_ticket_id(found, ticket_id))
            decision = schedule.decide(ticket, now, timing_for(ticket), merge_watch=merge_watch)
            events.extend(schedule.with_ticket_id(decision.events, ticket_id))
            tickets[ticket_id] = decision.ticket
        return replace(fresh, tickets=tickets)

    after = state_store.update(path, apply)
    tickets = after.tickets.values()
    if tickets and all(t.stage is Stage.DONE for t in tickets):
        events.append(Event(EventKind.ALL_MERGED))
    idle = all(schedule.is_idle(t) for t in tickets)
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


def live_pollers(path: Path, tool: str, timings: Mapping[str, CiTiming]) -> Pollers:
    usage_log = path.with_suffix(".usage.log")

    def read_linear(ticket_ids: Sequence[str]) -> Sequence[LinearObservation]:
        return linear_poll.read_statuses(ticket_ids, usage_log, utc_now(), tool=tool)

    def read_github(
        ticket_id: str, repo_dir: Path, settles_on: Sequence[str]
    ) -> GithubObservation | None:
        return github_poll.read_pr(ticket_id, repo_dir, settles_on)

    return Pollers(timing_lookup(timings), read_linear, read_github)


def cmd_watch(args: argparse.Namespace) -> int:
    """Tick until events, idle or a stop signal."""
    path: Path = args.state_file
    pollers = live_pollers(path, args.tool, ci_timing.load(args.ci_timing))
    try:
        with stop_on_signals():
            while True:
                result = run_tick(path, utc_now(), pollers, merge_watch=args.merge_watch)
                if result.events:
                    print("\n".join(event.render() for event in result.events), flush=True)
                    return EXIT_EVENT
                if result.idle:
                    print(EventKind.IDLE, flush=True)
                    return EXIT_IDLE
                time.sleep(args.tick)
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
    timing_for = timing_lookup(ci_timing.load(args.ci_timing))
    linear, github = _due_checks(wave, _at(args), timing_for, args.merge_watch)
    lines = [f"{t} linear" for t in linear] + [f"{t} github" for t in github]
    print("\n".join(lines) if lines else "NONE")
    return EXIT_EVENT if lines else EXIT_IDLE


def cmd_explain(args: argparse.Namespace) -> int:
    """Print each ticket's stage, next checks and deadline as a tick would see them."""
    with state_store.locked(args.state_file):
        wave = state_store.load(args.state_file)
    timing_for = timing_lookup(ci_timing.load(args.ci_timing))
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
            f"  ci={timing.repo} due-now={','.join(due) or 'none'} "
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
        sub.add_argument("--ci-timing", type=Path, default=ci_timing.DEFAULT_PATH)
        sub.add_argument(
            "--merge-watch", action="store_true", help="check pr-ready PRs for merges every 15 min"
        )

    watch = commands.add_parser("watch", help="tick every 30 s until an event or idle")
    with_schedule_options(watch)
    watch.add_argument("--tick", type=float, default=TICK_SECONDS, help=argparse.SUPPRESS)
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

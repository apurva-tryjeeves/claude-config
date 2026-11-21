"""Load and save the state file under a shared lock, with atomic writes."""

from __future__ import annotations

import fcntl
import json
import os
import tempfile
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import fields, replace
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Final

from jaidev_watch.models import (
    EventKind,
    Stage,
    TicketState,
    WaveState,
    format_time,
    parse_time,
)

SCHEMA_VERSION: Final = 2


class StateFileError(Exception):
    """The state file is unreadable, or a value in it has the wrong type."""


class FieldValueError(ValueError):
    """A `state set` value does not fit its field."""


class Kind(StrEnum):
    """How a field is stored in JSON."""

    STR = "str"
    INT = "int"
    BOOL = "bool"
    TIME = "time"
    STAGE = "stage"
    EVENT = "event"


# Python field → (JSON key, kind). Every TicketState field except `extra`.
FIELDS: Final[Mapping[str, tuple[str, Kind]]] = {
    "agent": ("agent", Kind.STR),
    "repo_dir": ("repoDir", Kind.STR),
    "color": ("color", Kind.STR),
    "pr_number": ("prNumber", Kind.INT),
    "pr_head": ("prHead", Kind.STR),
    "last_ci_head": ("lastCiHead", Kind.STR),
    "last_status": ("lastStatus", Kind.STR),
    "last_timeline": ("lastTimeline", Kind.STR),
    "merged": ("merged", Kind.BOOL),
    "stage": ("stage", Kind.STAGE),
    "stage_since": ("stageSince", Kind.TIME),
    "started_at": ("startedAt", Kind.TIME),
    "feedback_at": ("feedbackAt", Kind.TIME),
    "approved_at": ("approvedAt", Kind.TIME),
    "review_at": ("reviewAt", Kind.TIME),
    "pre_estimate": ("preEstimate", Kind.INT),
    "names_bytes": ("namesBytes", Kind.INT),
    "feedback_bytes": ("feedbackBytes", Kind.INT),
    "estimate": ("estimate", Kind.INT),
    "review_comments": ("reviewComments", Kind.INT),
    "repo_count": ("repoCount", Kind.INT),
    "attempt": ("attempt", Kind.INT),
    "queued_since": ("queuedSince", Kind.TIME),
    "paused_seconds": ("pausedSeconds", Kind.INT),
    "ack_at": ("ackAt", Kind.TIME),
    "sonar_findings": ("sonarFindings", Kind.BOOL),
    "last_activity_at": ("lastActivityAt", Kind.TIME),
    "last_linear_at": ("lastLinearAt", Kind.TIME),
    "last_github_at": ("lastGithubAt", Kind.TIME),
    "last_linear_error_at": ("lastLinearErrorAt", Kind.TIME),
    "last_github_error_at": ("lastGithubErrorAt", Kind.TIME),
    "next_linear_at": ("nextLinearAt", Kind.TIME),
    "next_github_at": ("nextGithubAt", Kind.TIME),
    "deadline": ("deadline", Kind.TIME),
    "deadline_event": ("deadlineEvent", Kind.EVENT),
    "fired_event": ("firedEvent", Kind.EVENT),
}
BY_KEY: Final[Mapping[str, tuple[str, Kind]]] = {
    key: (name, kind) for name, (key, kind) in FIELDS.items()
}
# Written even when they hold their default, so older readers see them.
ALWAYS_WRITTEN: Final = frozenset({"merged"})
STAGE_VALUES: Final = frozenset(stage.value for stage in Stage)
EVENT_VALUES: Final = frozenset(kind.value for kind in EventKind)


_ACCEPTS: Final[Mapping[Kind, Callable[[object], bool]]] = {
    Kind.STR: lambda raw: isinstance(raw, str),
    Kind.INT: lambda raw: isinstance(raw, int) and not isinstance(raw, bool),
    Kind.BOOL: lambda raw: isinstance(raw, bool),
    Kind.TIME: lambda raw: isinstance(raw, str),
    Kind.STAGE: lambda raw: isinstance(raw, str) and raw in STAGE_VALUES,
    Kind.EVENT: lambda raw: isinstance(raw, str) and raw in EVENT_VALUES,
}
_CONVERT: Final[Mapping[Kind, Callable[[str], object]]] = {
    Kind.TIME: parse_time,
    Kind.STAGE: Stage,
    Kind.EVENT: EventKind,
}


def _decode(kind: Kind, key: str, raw: object) -> object:
    """Turn one JSON value into its Python type, or raise StateFileError."""
    if raw is None:
        return None
    if not _ACCEPTS[kind](raw):
        raise StateFileError(f"{key}: expected {kind}, got {raw!r}")
    convert = _CONVERT.get(kind)
    if convert is None:
        return raw
    try:
        return convert(str(raw))
    except ValueError as error:
        raise StateFileError(f"{key}: {error}") from error


def _encode(value: object) -> object:
    if isinstance(value, datetime):
        return format_time(value)
    if isinstance(value, StrEnum):
        return str(value)
    return value


def ticket_from_json(data: Mapping[str, object]) -> TicketState:
    """Parse one ticket's JSON object; unknown keys are kept in `extra`."""
    known: dict[str, Any] = {}
    extra: dict[str, object] = {}
    for key, raw in data.items():
        if key in BY_KEY:
            name, kind = BY_KEY[key]
            value = _decode(kind, key, raw)
            if value is not None:
                known[name] = value
        else:
            extra[key] = raw
    return TicketState(**known, extra=extra)


def ticket_to_json(ticket: TicketState) -> dict[str, object]:
    """Serialise a ticket; fields at None (or their default) are left out."""
    defaults = TicketState()
    data: dict[str, object] = {}
    for item in fields(TicketState):
        if item.name == "extra":
            continue
        value = getattr(ticket, item.name)
        unset = value is None or (
            value == getattr(defaults, item.name) and item.name not in ALWAYS_WRITTEN
        )
        if not unset:
            data[FIELDS[item.name][0]] = _encode(value)
    data.update(ticket.extra)
    return data


def wave_from_json(data: object) -> WaveState:
    """Parse the whole file; schema 1 (no version) and 2 are accepted."""
    if not isinstance(data, dict):
        raise StateFileError("the state file holds no JSON object")
    version = data.get("schemaVersion", 1)
    if not isinstance(version, int) or version > SCHEMA_VERSION:
        raise StateFileError(f"schemaVersion {version!r} is newer than {SCHEMA_VERSION}")
    raw_tickets = data.get("tickets", {})
    if not isinstance(raw_tickets, dict):
        raise StateFileError("tickets is not an object")
    tickets: dict[str, TicketState] = {}
    for ticket_id, raw in raw_tickets.items():
        if not isinstance(raw, dict):
            raise StateFileError(f"{ticket_id} is not an object")
        tickets[ticket_id] = ticket_from_json(raw)
    extra = {k: v for k, v in data.items() if k not in ("schemaVersion", "tickets")}
    return WaveState(tickets=tickets, extra=extra)


def wave_to_json(wave: WaveState) -> dict[str, object]:
    """Serialise the whole file with the current schemaVersion."""
    tickets = {ticket_id: ticket_to_json(t) for ticket_id, t in wave.tickets.items()}
    return {"schemaVersion": SCHEMA_VERSION, "tickets": tickets, **wave.extra}


def lock_path(path: Path) -> Path:
    """The sidecar lock file; the state file itself is swapped by os.replace."""
    return path.with_name(path.name + ".lock")


@contextmanager
def locked(path: Path) -> Iterator[None]:
    """Hold the exclusive lock that every reader-writer of this state file takes."""
    with lock_file(lock_path(path)):
        yield


@contextmanager
def lock_file(lock: Path) -> Iterator[None]:
    """Hold an exclusive `fcntl.flock` on this lock file."""
    with lock.open("a") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def load(path: Path) -> WaveState:
    """Read the state file; a missing file is an empty wave. Call under `locked`."""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return WaveState()
    except OSError as error:
        raise StateFileError(f"cannot read {path}: {error}") from error
    try:
        return wave_from_json(json.loads(text))
    except json.JSONDecodeError as error:
        raise StateFileError(f"{path} is not JSON: {error}") from error


def save(path: Path, wave: WaveState) -> None:
    """Write the state file atomically."""
    write_text_atomic(path, json.dumps(wave_to_json(wave), indent=2, ensure_ascii=False) + "\n")


def write_text_atomic(path: Path, text: str) -> None:
    """Write a temp file in the same directory, then os.replace, so readers see old or new."""
    descriptor, temp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    temp = Path(temp_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    except BaseException:
        temp.unlink(missing_ok=True)
        raise


def update(path: Path, change: Callable[[WaveState], WaveState]) -> WaveState:
    """Load, change and save under one lock, so concurrent writers lose no update."""
    with locked(path):
        before = load(path)
        after = change(before)
        if after != before or not path.exists():
            save(path, after)
        return after


def parse_value(key: str, text: str, now: datetime) -> object:
    """Parse a `state set` value for a field: `now` for times, `null` clears.

    An unknown field takes the text as JSON, or as a plain string.
    """
    if text == "null":
        return None
    if key not in BY_KEY:
        try:
            parsed: object = json.loads(text)
        except json.JSONDecodeError:
            parsed = text
        return parsed
    _, kind = BY_KEY[key]
    if kind is Kind.TIME and text == "now":
        return now
    raw: object = text
    try:
        if kind in (Kind.INT, Kind.BOOL):
            raw = json.loads(text)
        return _decode(kind, key, raw)
    except (json.JSONDecodeError, StateFileError) as error:
        raise FieldValueError(f"{key}: expected {kind}, got {text!r}") from error


def set_field(ticket: TicketState, key: str, value: object) -> TicketState:
    """Set one field by its JSON key; an unknown key goes to `extra`."""
    if key in BY_KEY:
        name, _ = BY_KEY[key]
        if name == "paused_seconds" and value is None:
            value = 0
        if name == "merged" and value is None:
            value = False
        changes: dict[str, Any] = {name: value}
        return replace(ticket, **changes)
    extra = dict(ticket.extra)
    if value is None:
        extra.pop(key, None)
    else:
        extra[key] = value
    return replace(ticket, extra=extra)

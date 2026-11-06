#!/usr/bin/env python3
"""Render Jenkins build JSON as a markdown table with status icons.

Reads a Jenkins API object on stdin — either a `builds[...]` list response or a
single build object — and prints a markdown table. Pass the job's base URL as
argv[1] to turn each build number into a clickable link.

    curl ... "$JENKINS_URL/job/<job>/api/json?tree=builds%5Bnumber,result,duration,\
timestamp%5D%7B0,10%7D" \
      | python3 scripts/build-table.py "$JENKINS_URL/job/<job>"
"""

from __future__ import annotations

import json
import logging
import sys
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Final, TextIO

LOG: Final = logging.getLogger("build-table")
MS_PER_S: Final = 1000
SECONDS_PER_MINUTE: Final = 60
UNKNOWN_ICON: Final = "❓"
BUILDING_ICON: Final = "⏳"
BUILDING_LABEL: Final = "building"
HEADER: Final = ("| Result | Build | Duration | Started |", "|---|---|---|---|")


class TableError(Exception):
    """An expected, user-facing failure: reported as a message and exit code 1."""


class Result(StrEnum):
    """Jenkins build results with a documented icon."""

    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    UNSTABLE = "UNSTABLE"
    ABORTED = "ABORTED"


ICONS: Final[Mapping[str, str]] = {
    Result.SUCCESS: "✅",
    Result.FAILURE: "❌",
    Result.UNSTABLE: "⚠️",
    Result.ABORTED: "⛔",
}


@dataclass(frozen=True, slots=True)
class Build:
    """The fields of a Jenkins build object the table uses."""

    number: int
    result: str | None
    duration_ms: float
    timestamp_ms: float


def dur(ms: float) -> str:
    s = max(0, int(ms // MS_PER_S))
    if s >= SECONDS_PER_MINUTE:
        return f"{s // SECONDS_PER_MINUTE}m{s % SECONDS_PER_MINUTE:02d}s"
    return f"{s}s"


def started(ts: float) -> str:
    t = time.localtime(ts / MS_PER_S)
    return time.strftime("%-d %b ", t) + time.strftime("%-I:%M%p", t).lower()


def icon_for(result: str | None) -> str:
    if result is None:
        return BUILDING_ICON
    return ICONS.get(result, UNKNOWN_ICON)


def parse_builds(payload: object) -> list[Build]:
    """Accept a `builds[...]` list response or a single build object."""
    if not isinstance(payload, dict):
        raise TableError("expected a JSON object on stdin")
    items: Sequence[object] = payload.get("builds", [payload])
    try:
        return [_parse_build(item) for item in items]
    except (KeyError, TypeError, AttributeError) as exc:
        raise TableError(f"build JSON is missing or malformed field: {exc!r}") from exc


def _parse_build(item: object) -> Build:
    if not isinstance(item, dict):
        raise TypeError(item)
    raw: dict[str, Any] = item
    return Build(
        number=raw["number"],
        result=raw.get("result"),
        duration_ms=raw.get("duration") or 0,
        timestamp_ms=raw["timestamp"],
    )


def format_row(build: Build, base: str, now_ms: float) -> str:
    # A build still running reports duration 0, so measure from its start.
    elapsed = build.duration_ms or (now_ms - build.timestamp_ms)
    num = f"[#{build.number}]({base}/{build.number}/)" if base else f"#{build.number}"
    return (
        f"| {icon_for(build.result)} {build.result or BUILDING_LABEL} | {num} "
        f"| {dur(elapsed)} | {started(build.timestamp_ms)} |"
    )


def render(builds: Sequence[Build], base: str, now_ms: float) -> str:
    rows = [format_row(b, base, now_ms) for b in builds]
    return "\n".join([*HEADER, "\n".join(rows)])


def read_payload(stream: TextIO) -> object:
    try:
        return json.load(stream)
    except json.JSONDecodeError as exc:
        raise TableError(f"stdin is not valid JSON: {exc}") from exc


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stderr, force=True)
    args = list(sys.argv[1:] if argv is None else argv)
    base = args[0].rstrip("/") if args else ""
    try:
        builds = parse_builds(read_payload(sys.stdin))
    except TableError as exc:
        LOG.error("build-table: %s", exc)
        return 1
    print(render(builds, base, time.time() * MS_PER_S))
    return 0


if __name__ == "__main__":
    sys.exit(main())

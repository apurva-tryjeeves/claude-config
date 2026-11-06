"""Read the due tickets' Jaidev status comments with one headless Haiku call.

`claude -p --model haiku` runs as its own process, so no agent of the
coordinator's session wakes. Each call appends its cost and token counts to
`<state-file stem>.usage.log`.
"""

from __future__ import annotations

import json
import logging
import re
import subprocess
from collections.abc import Callable, Sequence
from datetime import datetime
from pathlib import Path
from typing import Final

from jaidev_watch.models import LinearObservation, format_time

DEFAULT_TOOL: Final = "mcp__claude_ai_Linear__list_comments"
TIMEOUT_SECONDS: Final = 240
_DIGITS: Final = re.compile(r"\d+")

log = logging.getLogger("jaidev_watch")

Runner = Callable[..., "subprocess.CompletedProcess[str]"]


class LinearPollError(Exception):
    """The Haiku call failed, or its reply did not hold the expected JSON."""


def build_prompt(ticket_ids: Sequence[str], tool: str) -> str:
    """The instruction Haiku follows for these tickets."""
    return (
        f"For each Linear issue in {json.dumps(list(ticket_ids))}, call {tool} with that "
        "issueId and limit 1. When that comment's body does not start with "
        "'**Jaidev — <ID>**', call it again with limit 3 and use the comment that does. "
        "Reply with only a JSON array, one object per issue: "
        '{"ticket": "<ID>", "status": "<text after **Status:**>", '
        '"timeline": "<last bullet under **Timeline**, without its timestamp>", '
        '"attempt": <N from the last "attempt N/5" in that comment, as a number>}. '
        "Use null for status and timeline when the issue has no Jaidev status comment, "
        "and null for attempt when the comment names no attempt."
    )


def build_command(ticket_ids: Sequence[str], tool: str) -> list[str]:
    """The argument list; the prompt goes last, as a positional argument."""
    return [
        "claude",
        "-p",
        "--model",
        "haiku",
        "--allowedTools",
        tool,
        "--output-format",
        "json",
        build_prompt(ticket_ids, tool),
    ]


def usage_line(reply: dict[str, object], now: datetime) -> str:
    """One usage-log line: time, cost and token counts."""
    usage = reply.get("usage")
    counts = usage if isinstance(usage, dict) else {}
    cost = reply.get("total_cost_usd", 0)
    return (
        f"{format_time(now)} "
        f"cost_usd={float(cost) if isinstance(cost, int | float) else 0.0:.4f} "
        f"input={counts.get('input_tokens', 0)} "
        f"cache_write={counts.get('cache_creation_input_tokens', 0)} "
        f"cache_read={counts.get('cache_read_input_tokens', 0)} "
        f"output={counts.get('output_tokens', 0)} "
        f"duration_ms={reply.get('duration_ms', 0)}\n"
    )


def parse_envelope(stdout: str) -> dict[str, object]:
    """Parse `claude --output-format json` output into its reply object."""
    try:
        reply = json.loads(stdout)
    except json.JSONDecodeError as error:
        raise LinearPollError(f"reply is not JSON: {stdout[:120]!r}") from error
    if not isinstance(reply, dict):
        raise LinearPollError("reply is not a JSON object")
    return reply


def _optional_str(row: dict[str, object], key: str) -> str | None:
    value = row.get(key)
    if value is None or isinstance(value, str):
        return value
    raise LinearPollError(f"{key} is not a string: {value!r}")


def _attempt(value: object) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, str) and (match := _DIGITS.search(value)):
        return int(match.group())
    return None


def parse_result(result: object) -> tuple[LinearObservation, ...]:
    """Validate the model's text into typed observations."""
    if not isinstance(result, str):
        raise LinearPollError("reply has no result text")
    start, end = result.find("["), result.rfind("]")
    if start < 0 or end < start:
        raise LinearPollError(f"no JSON array in reply: {result[:120]!r}")
    try:
        rows = json.loads(result[start : end + 1])
    except json.JSONDecodeError as error:
        raise LinearPollError(f"array is not JSON: {error}") from error
    if not isinstance(rows, list):
        raise LinearPollError("reply array is not a list")
    observations: list[LinearObservation] = []
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("ticket"), str):
            raise LinearPollError(f"row without a ticket: {row!r}")
        observations.append(
            LinearObservation(
                ticket=row["ticket"],
                status=_optional_str(row, "status"),
                timeline=_optional_str(row, "timeline"),
                attempt=_attempt(row.get("attempt")),
            )
        )
    return tuple(observations)


def read_statuses(
    ticket_ids: Sequence[str],
    usage_log: Path,
    now: datetime,
    *,
    tool: str = DEFAULT_TOOL,
    runner: Runner = subprocess.run,
) -> tuple[LinearObservation, ...]:
    """Run the Haiku call for these tickets and return what it read."""
    try:
        out = runner(
            build_command(ticket_ids, tool),
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise LinearPollError(str(error)) from error
    if out.returncode != 0:
        raise LinearPollError((out.stderr or out.stdout or "claude failed").strip()[-200:])
    reply = parse_envelope(out.stdout)
    try:
        with usage_log.open("a", encoding="utf-8") as handle:
            handle.write(usage_line(reply, now))
    except OSError as error:
        log.warning("cannot write the usage log %s: %s", usage_log, error)
    return parse_result(reply.get("result"))

"""Read the per-repo CI cadence from `ci-check-timing.md` in the memory directory."""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from datetime import timedelta
from pathlib import Path
from typing import Final

from jaidev_watch.models import CiTiming

PATH_ENV: Final = "JEEVES_CI_TIMING"
MEMORY_DIR_ENV: Final = "JEEVES_MEMORY_DIR"
DEFAULT_MEMORY_DIR: Final = Path.home() / ".claude" / "memory"
FILE_NAME: Final = "ci-check-timing.md"
TEMPLATE: Final = "\n".join(
    (
        "---",
        "name: ci-check-timing",
        "description: Per-repo PR check settle times (long-pole workflow, check names,"
        " min/max/mean, first check, interval); read before starting a checks poller or"
        " a Jaidev CI watch, and add or refine a repo's row after its checks settle",
        "metadata:",
        "  type: reference",
        "---",
        "",
        "# CI check timing",
        "",
        "One row per JeevesInc repo; the git-preferences skill's references/pr-pollers.md"
        ' "Checks poller" section derives and refines rows.',
        "",
        "| Repo | Long-pole workflow | Check name | Settles on | Min | Max | Mean"
        " | Sample size | First check | Interval | Known failures |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
        "",
    )
)
KNOWN_COLUMN: Final = "Known failures"
_PIPE: Final = re.compile(r"(?<!\\)\|")
_DURATION: Final = re.compile(r"^(?:(\d+)m(?:in)?)?(?:(\d+)s)?$")
_COLUMNS: Final = (
    "Repo",
    "Check name",
    "Settles on",
    "Min",
    "Max",
    "Mean",
    "First check",
    "Interval",
)


class CiTimingError(Exception):
    """The timing file or one of its cells could not be read."""


def parse_duration(text: str) -> timedelta:
    """Parse `2m12s`, `14min`, `45s` or `3m` into a timedelta."""
    match = _DURATION.match(text.strip())
    if match is None or not any(match.groups()):
        raise CiTimingError(f"unreadable duration {text!r}")
    minutes, seconds = (int(group or 0) for group in match.groups())
    return timedelta(minutes=minutes, seconds=seconds)


def _cells(line: str) -> list[str]:
    """Split a table row on unescaped pipes; `\\|` inside a cell is a literal pipe."""
    parts = _PIPE.split(line.strip())
    if parts and not parts[0].strip():
        parts = parts[1:]
    if parts and not parts[-1].strip():
        parts = parts[:-1]
    return [part.strip().replace("\\|", "|") for part in parts]


def _names(cell: str) -> tuple[str, ...]:
    return tuple(re.findall(r"`([^`]+)`", cell))


def parse_table(text: str) -> dict[str, CiTiming]:
    """Parse the markdown table into one CiTiming per repo."""
    lines = [line for line in text.splitlines() if line.lstrip().startswith("|")]
    header_index = next(
        (i for i, line in enumerate(lines) if set(_COLUMNS) <= set(_cells(line))), None
    )
    if header_index is None:
        raise CiTimingError("no table with the columns " + ", ".join(_COLUMNS))
    header = _cells(lines[header_index])
    column = {name: header.index(name) for name in _COLUMNS}
    known_at = header.index(KNOWN_COLUMN) if KNOWN_COLUMN in header else None
    timings: dict[str, CiTiming] = {}
    for line in lines[header_index + 1 :]:
        cells = _cells(line)
        if set("".join(cells)) <= set("-: ") or len(cells) <= max(column.values()):
            continue
        repo = cells[column["Repo"]]
        check_names = _names(cells[column["Check name"]])
        known = _names(cells[known_at]) if known_at is not None and known_at < len(cells) else ()
        timings[repo] = CiTiming(
            repo=repo,
            check_name=check_names[0] if check_names else "",
            settles_on=_names(cells[column["Settles on"]]),
            minimum=parse_duration(cells[column["Min"]]),
            maximum=parse_duration(cells[column["Max"]]),
            mean=parse_duration(cells[column["Mean"]]),
            first_check=parse_duration(cells[column["First check"]]),
            interval=parse_duration(cells[column["Interval"]]),
            known_failures=known,
        )
    return timings


def table_path() -> Path:
    """The timing table: `$JEEVES_CI_TIMING`, else `$JEEVES_MEMORY_DIR`'s file.

    `$JEEVES_MEMORY_DIR` defaults to `~/.claude/memory`.
    """
    if explicit := os.environ.get(PATH_ENV):
        return Path(explicit).expanduser()
    return Path(os.environ.get(MEMORY_DIR_ENV) or DEFAULT_MEMORY_DIR).expanduser() / FILE_NAME


def load(path: Path | None = None) -> Mapping[str, CiTiming]:
    """Read and parse the timing file; an absent file holds no rows yet."""
    path = path or table_path()
    if not path.exists():
        return {}
    try:
        return parse_table(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise CiTimingError(f"cannot read {path}: {error}") from error

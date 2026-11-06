"""Read the per-repo CI cadence from git-preferences' `ci-check-timing.md`."""

from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import timedelta
from pathlib import Path
from typing import Final

from jaidev_watch.models import CiTiming

# scripts/jaidev_watch/ci_timing.py → skills/git-preferences/references/ci-check-timing.md
DEFAULT_PATH: Final = (
    Path(__file__).resolve().parents[3] / "git-preferences" / "references" / "ci-check-timing.md"
)
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


class CiTimingError(ValueError):
    """The timing file or one of its cells could not be read."""


def parse_duration(text: str) -> timedelta:
    """Parse `2m12s`, `14min`, `45s` or `3m` into a timedelta."""
    match = _DURATION.match(text.strip())
    if match is None or not any(match.groups()):
        raise CiTimingError(f"unreadable duration {text!r}")
    minutes, seconds = (int(group or 0) for group in match.groups())
    return timedelta(minutes=minutes, seconds=seconds)


def _cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


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
    timings: dict[str, CiTiming] = {}
    for line in lines[header_index + 1 :]:
        cells = _cells(line)
        if set("".join(cells)) <= set("-: ") or len(cells) < len(header):
            continue
        repo = cells[column["Repo"]]
        check_names = _names(cells[column["Check name"]])
        timings[repo] = CiTiming(
            repo=repo,
            check_name=check_names[0] if check_names else "",
            settles_on=_names(cells[column["Settles on"]]),
            minimum=parse_duration(cells[column["Min"]]),
            maximum=parse_duration(cells[column["Max"]]),
            mean=parse_duration(cells[column["Mean"]]),
            first_check=parse_duration(cells[column["First check"]]),
            interval=parse_duration(cells[column["Interval"]]),
        )
    return timings


def load(path: Path = DEFAULT_PATH) -> Mapping[str, CiTiming]:
    """Read and parse the timing file."""
    try:
        return parse_table(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise CiTimingError(f"cannot read {path}: {error}") from error


def repo_name(repo_dir: str | None) -> str:
    """The repo a ticket's `repoDir` points at: its last path part."""
    return Path(repo_dir or ".").resolve().name

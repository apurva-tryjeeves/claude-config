"""Derive a missing `ci-check-timing.md` row the git-preferences way.

The steps follow git-preferences' references/pr-pollers.md "Checks poller"
and "Write back a timing row": time the last 10 successful PR runs of each
PR-check workflow, take the long pole, read the check names from a recent PR's
rollup, and write the row into the memory directory's timing table, creating the table
on its first row.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import subprocess
import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Final

from jaidev_watch import ci_timing, state_store
from jaidev_watch.models import CiTiming, parse_time

ORG: Final = "JeevesInc"
RUN_LIMIT: Final = 10
MAX_RUN: Final = timedelta(hours=2)
MIN_FIRST_CHECK: Final = timedelta(minutes=1)
MIN_INTERVAL: Final = timedelta(minutes=1)
MAX_INTERVAL: Final = timedelta(minutes=3)
TIMEOUT_SECONDS: Final = 60
MERGED_PRS: Final = 5
WORKFLOW_DIR: Final = ".github/workflows/"
_REMOTE: Final = re.compile(r"[/:]([^/:]+?)(?:\.git)?/?$")

Runner = Callable[..., "subprocess.CompletedProcess[str]"]


class CiDeriveError(Exception):
    """The repo's CI history gave no row."""


@dataclass(frozen=True, slots=True)
class DerivedRow:
    """A derived timing, with the facts its table row records."""

    timing: CiTiming
    workflow: str
    sample_size: int


def repo_from_remote(url: str) -> str | None:
    """`git@github.com:JeevesInc/x.git` or `https://github.com/JeevesInc/x` → `x`."""
    match = _REMOTE.search(url.strip())
    return match.group(1) if match else None


def run_durations(runs: object) -> list[timedelta]:
    """Durations of `gh run list` rows, dropping runs over 2 h and unreadable rows."""
    durations: list[timedelta] = []
    if not isinstance(runs, list):
        return durations
    for run in runs:
        if not isinstance(run, dict):
            continue
        try:
            took = parse_time(str(run["updatedAt"])) - parse_time(str(run["createdAt"]))
        except (KeyError, ValueError):
            continue
        if timedelta(0) <= took <= MAX_RUN:
            durations.append(took)
    return durations


def _mean(durations: Sequence[timedelta]) -> timedelta:
    return sum(durations, timedelta(0)) / len(durations)


def long_pole(per_workflow: Mapping[str, Sequence[timedelta]]) -> str | None:
    """The workflow with the slowest mean run."""
    timed = {name: _mean(runs) for name, runs in per_workflow.items() if runs}
    return max(timed, key=lambda name: timed[name]) if timed else None


def _when(check: Mapping[str, object], key: str) -> datetime | None:
    value = check.get(key)
    try:
        return parse_time(value) if isinstance(value, str) and value else None
    except ValueError:
        return None


def rollup_names(rollup: object, workflow_name: str) -> tuple[str, tuple[str, ...]]:
    """The long-pole check and the checks created after it finished (`Settles on`)."""
    checks = [c for c in rollup if isinstance(c, dict)] if isinstance(rollup, list) else []
    timed = [
        (str(c.get("name") or ""), start, end, str(c.get("workflowName") or ""))
        for c in checks
        if (start := _when(c, "startedAt")) and (end := _when(c, "completedAt"))
    ]
    if not timed:
        raise CiDeriveError("the latest PR has no timed checks")
    own = [t for t in timed if t[3] == workflow_name] or timed
    name, _, finished, _ = max(own, key=lambda t: t[2] - t[1])
    later = tuple(n for n, start, _, _ in sorted(timed, key=lambda t: t[1]) if start >= finished)
    return name, later or (name,)


def _whole_minutes(value: timedelta) -> timedelta:
    return timedelta(minutes=int(value.total_seconds() // 60))


def derive_timing(
    repo: str, check_name: str, settles_on: tuple[str, ...], durations: Sequence[timedelta]
) -> CiTiming:
    """First check a little under the fastest run; interval from the spread.

    First check: the fastest run's whole minutes, one less when it is an exact
    minute, at least 1 min (2m12s → 2min, 33m00s → 32min). Interval: half the
    spread between fastest and slowest, rounded up, from 1 to 3 min.
    """
    if not durations:
        raise CiDeriveError("no successful PR runs")
    fastest, slowest = min(durations), max(durations)
    first = _whole_minutes(fastest)
    if first == fastest:
        first -= timedelta(minutes=1)
    half_spread = math.ceil((slowest - fastest).total_seconds() / 120)
    interval = min(MAX_INTERVAL, max(MIN_INTERVAL, timedelta(minutes=half_spread)))
    return CiTiming(
        repo=repo,
        check_name=check_name,
        settles_on=settles_on,
        minimum=fastest,
        maximum=slowest,
        mean=_mean(durations),
        first_check=max(MIN_FIRST_CHECK, first),
        interval=interval,
    )


def _escape(text: str) -> str:
    return text.replace("|", "\\|")


def _span(value: timedelta) -> str:
    seconds = round(value.total_seconds())
    return f"{seconds // 60}m{seconds % 60:02d}s"


def format_row(row: DerivedRow) -> str:
    """The markdown table row, in the table's column order."""
    t = row.timing
    settles = ", ".join(f"`{_escape(name)}`" for name in t.settles_on)
    cells = [
        _escape(t.repo),
        _escape(row.workflow),
        f"`{_escape(t.check_name)}`",
        settles,
        _span(t.minimum),
        _span(t.maximum),
        _span(t.mean),
        str(row.sample_size),
        f"{int(t.first_check.total_seconds() // 60)}min",
        f"{int(t.interval.total_seconds() // 60)}min",
    ]
    return "| " + " | ".join(cells) + " |"


def insert_row(text: str, row: str) -> str:
    """Add the row after the table's last row."""
    lines = text.splitlines(keepends=True)
    header = next((i for i, line in enumerate(lines) if line.startswith("| Repo |")), None)
    if header is None:
        raise CiDeriveError("the timing file has no table")
    end = header
    while end + 1 < len(lines) and lines[end + 1].startswith("|"):
        end += 1
    if not lines[end].endswith("\n"):
        lines[end] += "\n"
    lines.insert(end + 1, row + "\n")
    return "".join(lines)


def _run_json(command: list[str], runner: Runner, cwd: Path | None = None) -> object:
    try:
        out = runner(
            command, cwd=cwd, capture_output=True, text=True, timeout=TIMEOUT_SECONDS, check=False
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise CiDeriveError(str(error)) from error
    if out.returncode != 0:
        lines = (out.stderr or "command failed").strip().splitlines()
        raise CiDeriveError(lines[-1] if lines else "command failed")
    try:
        return json.loads(out.stdout or "null")
    except json.JSONDecodeError as error:
        raise CiDeriveError(f"output is not JSON: {error}") from error


def resolve_repo(repo_dir: str | None, runner: Runner = subprocess.run) -> str:
    """The repo name from `git remote get-url origin`, else the directory name."""
    folder = Path(repo_dir or ".")
    try:
        out = runner(
            ["git", "-C", str(folder), "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return folder.resolve().name
    name = repo_from_remote(out.stdout) if out.returncode == 0 else None
    return name or folder.resolve().name


def _names_from_prs(prs: object, workflow_name: str) -> tuple[str, tuple[str, ...]]:
    """Check names from the newest of the last merged PRs that has timed checks."""
    for pr in prs if isinstance(prs, list) else []:
        rollup = pr.get("statusCheckRollup") if isinstance(pr, dict) else None
        try:
            return rollup_names(rollup, workflow_name)
        except CiDeriveError:
            continue
    raise CiDeriveError(f"none of the last {MERGED_PRS} merged PRs has timed checks")


def derive_row(repo: str, runner: Runner = subprocess.run) -> DerivedRow:
    """Time the repo's PR-check workflows with `gh` and build its row."""
    slug = f"{ORG}/{repo}"
    workflows = _run_json(
        ["gh", "workflow", "list", "--repo", slug, "--json", "name,path,state"], runner
    )
    names: dict[str, str] = {}
    per_workflow: dict[str, list[timedelta]] = {}
    for workflow in workflows if isinstance(workflows, list) else []:
        if not isinstance(workflow, dict) or workflow.get("state") != "active":
            continue
        path = str(workflow.get("path") or "")
        if not path.startswith(WORKFLOW_DIR):
            continue
        file = Path(path).name
        runs = _run_json(
            [
                *("gh", "run", "list", "--repo", slug, "--workflow", file),
                *("--status", "success", "--event", "pull_request"),
                *("--limit", str(RUN_LIMIT), "--json", "createdAt,updatedAt"),
            ],
            runner,
        )
        per_workflow[file] = run_durations(runs)
        names[file] = str(workflow.get("name") or "")
    pole = long_pole(per_workflow)
    if pole is None:
        raise CiDeriveError("no successful PR runs")
    prs = _run_json(
        [
            *("gh", "pr", "list", "--repo", slug, "--state", "merged"),
            *("--limit", str(MERGED_PRS), "--json", "statusCheckRollup"),
        ],
        runner,
    )
    check_name, settles_on = _names_from_prs(prs, names[pole])
    durations = per_workflow[pole]
    timing = derive_timing(repo, check_name, settles_on, durations)
    return DerivedRow(timing=timing, workflow=pole, sample_size=len(durations))


def _has_row(text: str, repo: str) -> bool:
    return any(line.startswith(f"| {_escape(repo)} |") for line in text.splitlines())


def _table_lock(path: Path) -> Path:
    digest = hashlib.sha256(str(path.resolve()).encode()).hexdigest()[:16]
    return Path(tempfile.gettempdir()) / f"jaidev-ci-table-{digest}.lock"


def write_row(row: DerivedRow, path: Path) -> bool:
    """Add the row to the table once, under a lock, atomically; create the table when absent.

    The lock file sits in the system temp directory, beside nothing it would clutter.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with state_store.lock_file(_table_lock(path)):
        text = path.read_text(encoding="utf-8") if path.exists() else ci_timing.TEMPLATE
        if not _has_row(text, row.timing.repo):
            state_store.write_text_atomic(path, insert_row(text, format_row(row)))
    return True

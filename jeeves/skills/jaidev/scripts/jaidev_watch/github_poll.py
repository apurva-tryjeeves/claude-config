"""Read a ticket's Jaidev PR with `gh`, and judge its CI by the settle rule."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from jaidev_watch.models import CiResult, GithubObservation, PrState

PENDING: Final = frozenset({"IN_PROGRESS", "QUEUED", "PENDING", "WAITING", "REQUESTED", "EXPECTED"})
FAILED: Final = frozenset(
    {"FAILURE", "ERROR", "TIMED_OUT", "CANCELLED", "ACTION_REQUIRED", "STARTUP_FAILURE"}
)
SONAR_CHECK: Final = "SonarCloud Code Analysis"
SONAR_CLEAN: Final = frozenset({"SUCCESS", "NEUTRAL", "SKIPPED"})
TIMEOUT_SECONDS: Final = 60
SHORT_HEAD: Final = 7

Runner = Callable[..., "subprocess.CompletedProcess[str]"]


class GithubPollError(Exception):
    """`gh` failed, or its output did not hold the expected JSON."""


@dataclass(frozen=True, slots=True)
class Check:
    """One entry of a PR's status check rollup."""

    name: str
    status: str
    conclusion: str


def branch_for(ticket_id: str) -> str:
    """Jaidev's branch for a ticket."""
    return f"jai-dev/{ticket_id.lower()}"


def build_command(ticket_id: str) -> list[str]:
    """The `gh pr list` argument list for a ticket's branch."""
    return [
        "gh",
        "pr",
        "list",
        "--head",
        branch_for(ticket_id),
        "--state",
        "all",
        "--json",
        "number,headRefOid,state,statusCheckRollup",
    ]


def parse_checks(rollup: object) -> tuple[Check, ...]:
    """Normalise CheckRun and StatusContext entries."""
    if not isinstance(rollup, list):
        return ()
    checks: list[Check] = []
    for entry in rollup:
        if not isinstance(entry, dict):
            continue
        state = str(entry.get("state") or "")
        checks.append(
            Check(
                name=str(entry.get("name") or entry.get("context") or ""),
                status=str(entry.get("status") or state),
                conclusion=str(entry.get("conclusion") or state),
            )
        )
    return tuple(checks)


def known_failed(checks: Sequence[Check], known_failures: Sequence[str]) -> tuple[str, ...]:
    """Names of the known-failure checks that failed on this head."""
    return tuple(c.name for c in checks if c.name in known_failures and c.conclusion in FAILED)


def ci_result(
    checks: Sequence[Check],
    settles_on: Sequence[str] | None,
    known_failures: Sequence[str] = (),
) -> CiResult:
    """Settled only when every check completed and every `Settles on` check is present.

    Without a timing row (`settles_on` None) CI stays pending. A failed check named
    in `known_failures` still has to complete, but does not make the head FAILED.
    """
    if settles_on is None or not checks or any(check.status in PENDING for check in checks):
        return CiResult.PENDING
    names = {check.name for check in checks}
    if any(name not in names for name in settles_on):
        return CiResult.PENDING
    if any(c.conclusion in FAILED and c.name not in known_failures for c in checks):
        return CiResult.FAILED
    return CiResult.PASSED


def sonar_findings(checks: Sequence[Check]) -> bool:
    """True when SonarCloud reported anything other than a clean pass."""
    return any(c.name == SONAR_CHECK and c.conclusion not in SONAR_CLEAN for c in checks)


def parse_pr_list(
    stdout: str, settles_on: Sequence[str] | None, known_failures: Sequence[str] = ()
) -> GithubObservation | None:
    """Turn `gh pr list` JSON into the newest PR's observation, or None without a PR."""
    try:
        prs = json.loads(stdout or "[]")
    except json.JSONDecodeError as error:
        raise GithubPollError(f"gh output is not JSON: {error}") from error
    if not isinstance(prs, list):
        raise GithubPollError("gh output is not a list")
    if not prs:
        return None
    pr = prs[0]
    try:
        number = int(pr["number"])
        head = str(pr["headRefOid"])[:SHORT_HEAD]
        state = PrState(pr["state"])
    except (KeyError, TypeError, ValueError) as error:
        raise GithubPollError(f"unexpected PR fields: {error}") from error
    checks = parse_checks(pr.get("statusCheckRollup"))
    return GithubObservation(
        number=number,
        head=head,
        state=state,
        ci=ci_result(checks, settles_on, known_failures),
        sonar_findings=sonar_findings(checks),
        known_failed=known_failed(checks, known_failures),
    )


def read_pr(
    ticket_id: str,
    repo_dir: Path,
    settles_on: Sequence[str] | None,
    known_failures: Sequence[str] = (),
    *,
    runner: Runner = subprocess.run,
) -> GithubObservation | None:
    """Run `gh pr list` from the ticket's repo, so gh picks that repo's account."""
    try:
        out = runner(
            build_command(ticket_id),
            cwd=repo_dir,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise GithubPollError(str(error)) from error
    if out.returncode != 0:
        lines = (out.stderr or "gh failed").strip().splitlines()
        raise GithubPollError(lines[-1] if lines else "gh failed")
    return parse_pr_list(out.stdout, settles_on, known_failures)

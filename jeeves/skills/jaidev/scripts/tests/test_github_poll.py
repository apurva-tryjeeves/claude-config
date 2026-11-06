"""The gh call and the CI settle rule."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path
from typing import Any

from jaidev_watch import github_poll
from jaidev_watch.github_poll import Check
from jaidev_watch.models import CiResult, PrState

SETTLES_ON = ("test / Scan for secrets", "SonarCloud Code Analysis")


def done(name: str, conclusion: str = "SUCCESS") -> Check:
    return Check(name, "COMPLETED", conclusion)


class CiResultTest(unittest.TestCase):
    def test_settle_rule(self) -> None:
        unit, secrets, sonar = (
            done("test / Unit Test"),
            done("test / Scan for secrets"),
            done("SonarCloud Code Analysis"),
        )
        cases = [
            ([], CiResult.PENDING),
            ([unit, secrets], CiResult.PENDING),  # every check completed, SonarCloud absent
            (
                [unit, secrets, Check("SonarCloud Code Analysis", "IN_PROGRESS", "")],
                CiResult.PENDING,
            ),
            ([unit, done("test / Scan for secrets", "FAILURE")], CiResult.PENDING),
            ([unit, secrets, sonar], CiResult.PASSED),
            ([done("test / Unit Test", "FAILURE"), secrets, sonar], CiResult.FAILED),
        ]
        for checks, expected in cases:
            with self.subTest(names=[c.name for c in checks], expected=expected):
                self.assertIs(github_poll.ci_result(checks, SETTLES_ON), expected)

    def test_sonar_findings(self) -> None:
        self.assertTrue(github_poll.sonar_findings([done("SonarCloud Code Analysis", "FAILURE")]))
        self.assertFalse(github_poll.sonar_findings([done("SonarCloud Code Analysis")]))
        self.assertFalse(github_poll.sonar_findings([]))


class ReadPrTest(unittest.TestCase):
    def test_runs_gh_in_the_repo_and_parses(self) -> None:
        calls: list[dict[str, Any]] = []
        payload = [
            {
                "number": 96,
                "headRefOid": "ae165dd149edad55",
                "state": "OPEN",
                "statusCheckRollup": [
                    {"name": "test / Unit Test", "status": "COMPLETED", "conclusion": "SUCCESS"},
                    {
                        "name": "test / Scan for secrets",
                        "status": "COMPLETED",
                        "conclusion": "SUCCESS",
                    },
                    {"context": "SonarCloud Code Analysis", "state": "SUCCESS"},
                ],
            }
        ]

        def runner(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:  # noqa: ANN401
            calls.append({"args": args, **kwargs})
            return subprocess.CompletedProcess(args, 0, json.dumps(payload), "")

        got = github_poll.read_pr("ACC-1670", Path("/repo"), SETTLES_ON, runner=runner)
        assert got is not None
        self.assertEqual(
            (got.number, got.head, got.state, got.ci),
            (96, "ae165dd", PrState.OPEN, CiResult.PASSED),
        )
        self.assertEqual(calls[0]["cwd"], Path("/repo"))
        self.assertIn("jai-dev/acc-1670", calls[0]["args"])
        self.assertFalse(calls[0]["check"])

    def test_no_pr_and_errors(self) -> None:
        def empty(args: list[str], **_: object) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(args, 0, "[]", "")

        def failing(args: list[str], **_: object) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(args, 1, "", "HTTP 401\nauth required")

        self.assertIsNone(github_poll.read_pr("ACC-1", Path("."), SETTLES_ON, runner=empty))
        with self.assertRaisesRegex(github_poll.GithubPollError, "auth required"):
            github_poll.read_pr("ACC-1", Path("."), SETTLES_ON, runner=failing)


if __name__ == "__main__":
    unittest.main()

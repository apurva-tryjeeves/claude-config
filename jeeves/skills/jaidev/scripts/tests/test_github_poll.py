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

    def test_known_failures_do_not_fail_the_head(self) -> None:
        unit, secrets, sonar = (
            done("test / Unit Test"),
            done("test / Scan for secrets"),
            done("SonarCloud Code Analysis"),
        )
        locale = done("Validate Localization", "FAILURE")
        known = ("Validate Localization",)
        cases = [
            ([unit, secrets, sonar, locale], known, CiResult.PASSED),
            ([unit, secrets, sonar, locale], (), CiResult.FAILED),
            ([done("test / Unit Test", "FAILURE"), secrets, sonar, locale], known, CiResult.FAILED),
            (
                [unit, secrets, done("SonarCloud Code Analysis", "FAILURE"), locale],
                known,
                CiResult.FAILED,
            ),
            (
                [unit, secrets, sonar, Check("Validate Localization", "IN_PROGRESS", "")],
                known,
                CiResult.PENDING,
            ),
        ]
        for checks, known_failures, expected in cases:
            with self.subTest(expected=expected, known=known_failures):
                result = github_poll.ci_result(checks, SETTLES_ON, known_failures)
                self.assertIs(result, expected)
        self.assertEqual(github_poll.known_failed([unit, locale], known), known)
        self.assertEqual(github_poll.known_failed([unit, done("Validate Localization")], known), ())

    def test_sonar_findings(self) -> None:
        self.assertTrue(github_poll.sonar_findings([done("SonarCloud Code Analysis", "FAILURE")]))
        self.assertFalse(github_poll.sonar_findings([done("SonarCloud Code Analysis")]))
        self.assertFalse(github_poll.sonar_findings([]))


class ParsePrListTest(unittest.TestCase):
    def test_known_failure_is_reported_on_the_observation(self) -> None:
        rollup = [
            {"name": "test / Unit Test", "status": "COMPLETED", "conclusion": "SUCCESS"},
            {"name": "test / Scan for secrets", "status": "COMPLETED", "conclusion": "SUCCESS"},
            {"name": "SonarCloud Code Analysis", "status": "COMPLETED", "conclusion": "SUCCESS"},
            {"name": "Validate Localization", "status": "COMPLETED", "conclusion": "FAILURE"},
        ]
        payload = [
            {"number": 3, "headRefOid": "ee05750abc", "state": "OPEN", "statusCheckRollup": rollup}
        ]
        seen = github_poll.parse_pr_list(
            json.dumps(payload), SETTLES_ON, ("Validate Localization",)
        )
        assert seen is not None
        self.assertIs(seen.ci, CiResult.PASSED)
        self.assertEqual(seen.known_failed, ("Validate Localization",))
        failed = github_poll.parse_pr_list(json.dumps(payload), SETTLES_ON)
        assert failed is not None
        self.assertIs(failed.ci, CiResult.FAILED)

    def test_completed_rollup_without_a_settles_on_check_is_pending(self) -> None:
        payload = [
            {
                "number": 1,
                "headRefOid": "abcdef0123",
                "state": "OPEN",
                "statusCheckRollup": [
                    {"name": "test / Unit Test", "status": "COMPLETED", "conclusion": "SUCCESS"},
                    {
                        "name": "test / Scan for secrets",
                        "status": "COMPLETED",
                        "conclusion": "SUCCESS",
                    },
                ],
            }
        ]
        got = github_poll.parse_pr_list(json.dumps(payload), SETTLES_ON)
        assert got is not None
        self.assertIs(got.ci, CiResult.PENDING)

    def test_no_row_keeps_ci_pending(self) -> None:
        payload = [
            {
                "number": 1,
                "headRefOid": "abc",
                "state": "OPEN",
                "statusCheckRollup": [
                    {"name": "x", "status": "COMPLETED", "conclusion": "SUCCESS"}
                ],
            }
        ]
        got = github_poll.parse_pr_list(json.dumps(payload), None)
        assert got is not None
        self.assertIs(got.ci, CiResult.PENDING)


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

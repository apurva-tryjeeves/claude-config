"""Deriving a missing ci-check-timing.md row, with fixtures in place of gh."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from typing import Any

from jaidev_watch import ci_derive, ci_timing
from jaidev_watch.ci_derive import CiDeriveError, DerivedRow

ROLLUP = json.loads((Path(__file__).parent / "fixtures" / "acc-1670-rollup.json").read_text())


def s(seconds: int) -> timedelta:
    return timedelta(seconds=seconds)


def run(created: str, updated: str) -> dict[str, str]:
    return {"createdAt": f"2026-11-06T{created}Z", "updatedAt": f"2026-11-06T{updated}Z"}


class PureTest(unittest.TestCase):
    def test_run_durations_drop_runs_over_two_hours(self) -> None:
        runs = [run("01:00:00", "01:02:12"), run("01:00:00", "03:30:00"), {"x": 1}]
        self.assertEqual(ci_derive.run_durations(runs), [s(132)])

    def test_derive_timing_matches_the_ap_data_source_connector_row(self) -> None:
        timing = ci_derive.derive_timing("r", "c", ("c",), [s(132), s(294), s(200)])
        self.assertEqual((timing.first_check, timing.interval), (s(120), s(120)))
        self.assertEqual((timing.minimum, timing.maximum), (s(132), s(294)))

    def test_derive_timing_table(self) -> None:
        cases = [
            ([s(120), s(130)], s(60), s(60)),
            ([s(30)], s(60), s(60)),
            ([s(60), s(1200)], s(60), s(180)),
        ]
        for durations, first, interval in cases:
            with self.subTest(durations=durations):
                timing = ci_derive.derive_timing("r", "c", ("c",), durations)
                self.assertEqual((timing.first_check, timing.interval), (first, interval))
        with self.assertRaises(CiDeriveError):
            ci_derive.derive_timing("r", "c", ("c",), [])

    def test_rollup_names_from_the_acc_1670_pr(self) -> None:
        name, settles = ci_derive.rollup_names(ROLLUP, "Unit Test")
        self.assertEqual(name, "test / Unit Test")
        self.assertEqual(settles, ("test / Code Analysis", "SonarCloud Code Analysis"))

    def test_long_pole_and_remote(self) -> None:
        self.assertEqual(
            ci_derive.long_pole({"a.yml": [s(60)], "b.yml": [s(300)], "c.yml": []}), "b.yml"
        )
        self.assertIsNone(ci_derive.long_pole({"a.yml": []}))
        for url in (
            "git@github.com:JeevesInc/ap-x.git",
            "https://github.com/JeevesInc/ap-x",
            "https://github.com/JeevesInc/ap-x.git\n",
        ):
            with self.subTest(url=url):
                self.assertEqual(ci_derive.repo_from_remote(url), "ap-x")

    def test_row_round_trips_through_the_table(self) -> None:
        timing = ci_derive.derive_timing(
            "new-repo", "test / Unit Test", ("SonarCloud Code Analysis",), [s(132), s(294)]
        )
        row = DerivedRow(timing=timing, workflow="unit-test.yml", sample_size=2)
        text = ci_derive.insert_row(ci_timing.DEFAULT_PATH.read_text(), ci_derive.format_row(row))
        parsed = ci_timing.parse_table(text)["new-repo"]
        self.assertEqual(parsed.settles_on, timing.settles_on)
        self.assertEqual(
            (parsed.first_check, parsed.interval, parsed.maximum),
            (timing.first_check, timing.interval, timing.maximum),
        )


class DeriveRowTest(unittest.TestCase):
    def fake_gh(self, runs: list[dict[str, str]]) -> Any:  # noqa: ANN401
        replies = {
            "workflow": [
                {"name": "Unit Test", "path": ".github/workflows/unit-test.yml", "state": "active"}
            ],
            "run": runs,
            "pr": [{"statusCheckRollup": ROLLUP}],
        }

        def runner(args: list[str], **_: object) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(args, 0, json.dumps(replies[args[1]]), "")

        return runner

    def test_derives_a_row_from_gh(self) -> None:
        row = ci_derive.derive_row(
            "ap-x", self.fake_gh([run("01:00:00", "01:02:12"), run("01:00:00", "01:04:54")])
        )
        self.assertEqual((row.workflow, row.sample_size), ("unit-test.yml", 2))
        self.assertEqual(row.timing.maximum, s(294))

    def test_no_runs_raise(self) -> None:
        with self.assertRaisesRegex(CiDeriveError, "no successful PR runs"):
            ci_derive.derive_row("ap-x", self.fake_gh([]))

    def test_write_row_only_into_an_existing_table(self) -> None:
        folder = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, folder)
        table = folder / "ci-check-timing.md"
        row = ci_derive.derive_row("ap-x", self.fake_gh([run("01:00:00", "01:02:12")]))
        self.assertFalse(ci_derive.write_row(row, table))
        shutil.copy(ci_timing.DEFAULT_PATH, table)
        self.assertTrue(ci_derive.write_row(row, table))
        self.assertIn("ap-x", ci_timing.load(table))


if __name__ == "__main__":
    unittest.main()

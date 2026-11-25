"""Parsing ci-check-timing.md."""

from __future__ import annotations

import os
import unittest
from datetime import timedelta
from pathlib import Path
from unittest import mock

from jaidev_watch import ci_timing

FIXTURE = Path(__file__).parent / "fixtures" / "ci-check-timing.md"


class CiTimingTest(unittest.TestCase):
    def test_parse_duration(self) -> None:
        cases = [("2m12s", 132), ("14min", 840), ("45s", 45), ("3m", 180), ("1m17s", 77)]
        for text, seconds in cases:
            with self.subTest(text=text):
                self.assertEqual(ci_timing.parse_duration(text), timedelta(seconds=seconds))
        for text in ("", "soon", "2h"):
            with self.subTest(text=text), self.assertRaises(ci_timing.CiTimingError):
                ci_timing.parse_duration(text)

    def test_reads_the_ap_data_source_connector_row(self) -> None:
        row = ci_timing.load(FIXTURE)["ap-data-source-connector"]
        self.assertEqual(row.check_name, "test / Unit Test")
        self.assertEqual(row.settles_on, ("test / Scan for secrets", "SonarCloud Code Analysis"))
        self.assertEqual(row.maximum, timedelta(minutes=4, seconds=54))
        self.assertEqual((row.first_check, row.interval), (timedelta(minutes=2),) * 2)

    def test_every_row_parses(self) -> None:
        timings = ci_timing.load(FIXTURE)
        self.assertGreaterEqual(len(timings), 9)
        for repo, row in timings.items():
            with self.subTest(repo=repo):
                self.assertTrue(row.settles_on)
                self.assertLessEqual(row.minimum, row.maximum)

    def test_known_failures_column(self) -> None:
        timings = ci_timing.load(FIXTURE)
        self.assertEqual(timings["jeeves-web"].known_failures, ("Validate Localization",))
        self.assertEqual(timings["ap-data-source-connector"].known_failures, ())

    def test_known_failures_column_absent_or_short(self) -> None:
        head = (
            "| Repo | Check name | Settles on | Min | Max | Mean | First check"
            " | Interval{extra} |\n"
            "|---|---|---|---|---|---|---|---|{sep}\n"
        )
        row = "| a | `U` | `S` | 1m | 2m | 90s | 1min | 2min |"
        cases = [
            (head.format(extra="", sep="") + row + "\n", ()),
            (head.format(extra=" | Known failures", sep="---|") + row + "\n", ()),
            (head.format(extra=" | Known failures", sep="---|") + row + "  |\n", ()),
            (
                head.format(extra=" | Known failures", sep="---|") + row + " `X`, `Y` |\n",
                ("X", "Y"),
            ),
        ]
        for text, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(ci_timing.parse_table(text)["a"].known_failures, expected)

    def test_missing_columns_raise(self) -> None:
        with self.assertRaises(ci_timing.CiTimingError):
            ci_timing.parse_table("| Repo | Max |\n|---|---|\n| a | 1m |\n")


if __name__ == "__main__":
    unittest.main()


class TablePathTest(unittest.TestCase):
    def _path(self, env: dict[str, str]) -> Path:
        names = (ci_timing.PATH_ENV, ci_timing.MEMORY_DIR_ENV)
        clean = {k: v for k, v in os.environ.items() if k not in names}
        with mock.patch.dict(os.environ, {**clean, **env}, clear=True):
            return ci_timing.table_path()

    def test_defaults_to_claude_memory(self) -> None:
        expected = Path.home() / ".claude" / "memory" / "ci-check-timing.md"
        self.assertEqual(self._path({}), expected)

    def test_memory_dir_env(self) -> None:
        path = self._path({"JEEVES_MEMORY_DIR": "/tmp/mem"})
        self.assertEqual(path, Path("/tmp/mem/ci-check-timing.md"))

    def test_ci_timing_env_wins(self) -> None:
        env = {"JEEVES_MEMORY_DIR": "/tmp/mem", "JEEVES_CI_TIMING": "/tmp/other.md"}
        self.assertEqual(self._path(env), Path("/tmp/other.md"))

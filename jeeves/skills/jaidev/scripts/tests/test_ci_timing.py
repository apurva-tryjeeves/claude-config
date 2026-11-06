"""Parsing ci-check-timing.md."""

from __future__ import annotations

import unittest
from datetime import timedelta

from jaidev_watch import ci_timing


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
        row = ci_timing.load()["ap-data-source-connector"]
        self.assertEqual(row.check_name, "test / Unit Test")
        self.assertEqual(row.settles_on, ("test / Scan for secrets", "SonarCloud Code Analysis"))
        self.assertEqual(row.maximum, timedelta(minutes=4, seconds=54))
        self.assertEqual((row.first_check, row.interval), (timedelta(minutes=2),) * 2)

    def test_every_row_parses(self) -> None:
        timings = ci_timing.load()
        self.assertGreaterEqual(len(timings), 9)
        for repo, row in timings.items():
            with self.subTest(repo=repo):
                self.assertTrue(row.settles_on)
                self.assertLessEqual(row.minimum, row.maximum)

    def test_missing_columns_raise(self) -> None:
        with self.assertRaises(ci_timing.CiTimingError):
            ci_timing.parse_table("| Repo | Max |\n|---|---|\n| a | 1m |\n")


if __name__ == "__main__":
    unittest.main()

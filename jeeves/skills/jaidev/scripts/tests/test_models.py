"""Event lines and time parsing."""

from __future__ import annotations

import unittest
from datetime import UTC, datetime

from jaidev_watch.models import Event, EventKind, format_time, parse_time


class ModelsTest(unittest.TestCase):
    def test_event_lines(self) -> None:
        cases = [
            (
                Event(EventKind.CI, "ACC-1", "passed #96 head=ae165dd"),
                "ACC-1 CI passed #96 head=ae165dd",
            ),
            (
                Event(EventKind.NO_ACK, "ACC-1", "stage=plan-feedback due=x"),
                "ACC-1 NO ACK stage=plan-feedback due=x",
            ),
            (Event(EventKind.LINEAR_POLL_ERROR, None, "boom"), "LINEAR POLL ERROR boom"),
            (Event(EventKind.GITHUB_POLL_ERROR, "ACC-1", "401"), "GITHUB POLL ERROR ACC-1 401"),
            (Event(EventKind.ALL_MERGED), "ALL MERGED"),
        ]
        for event, line in cases:
            with self.subTest(line=line):
                self.assertEqual(event.render(), line)

    def test_parse_time_is_utc(self) -> None:
        cases = ["2026-11-06T02:41:33Z", "2026-11-06T08:11:33+05:30", "2026-11-06T02:41:33"]
        for text in cases:
            with self.subTest(text=text):
                self.assertEqual(parse_time(text), datetime(2026, 11, 6, 2, 41, 33, tzinfo=UTC))
        self.assertEqual(format_time(parse_time(cases[1])), cases[0])


if __name__ == "__main__":
    unittest.main()

"""The Haiku call: command shape, usage log and reply validation."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Any

from jaidev_watch import linear_poll
from jaidev_watch.models import LinearObservation, parse_time

NOW = parse_time("2026-11-06T03:00:00Z")


def envelope(result: str) -> str:
    return json.dumps(
        {
            "result": result,
            "total_cost_usd": 0.0057,
            "duration_ms": 9000,
            "usage": {"input_tokens": 8, "cache_creation_input_tokens": 100, "output_tokens": 50},
        }
    )


class FakeRunner:
    def __init__(self, stdout: str, returncode: int = 0) -> None:
        self.stdout, self.returncode = stdout, returncode
        self.calls: list[tuple[list[str], dict[str, Any]]] = []

    def __call__(self, args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:  # noqa: ANN401
        self.calls.append((args, kwargs))
        return subprocess.CompletedProcess(args, self.returncode, self.stdout, "boom")


class LinearPollTest(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.dir)
        self.log = self.dir / "wave-state.usage.log"

    def test_command_keeps_the_prompt_last(self) -> None:
        command = linear_poll.build_command(["ACC-1"], linear_poll.DEFAULT_TOOL)
        self.assertEqual(
            command[:8],
            [
                "claude",
                "-p",
                "--model",
                "haiku",
                "--allowedTools",
                linear_poll.DEFAULT_TOOL,
                "--output-format",
                "json",
            ],
        )
        self.assertIn('["ACC-1"]', command[8])
        self.assertIn("attempt N/5", command[8])

    def test_reads_rows_and_logs_usage(self) -> None:
        row = {
            "ticket": "ACC-1",
            "status": "Implementing...",
            "timeline": "Plan approved by A",
            "attempt": "2/5",
        }
        rows = json.dumps([row])
        runner = FakeRunner(envelope(f"Here you go:\n{rows}"))
        got = linear_poll.read_statuses(["ACC-1"], self.log, NOW, runner=runner)
        self.assertEqual(
            got, (LinearObservation("ACC-1", "Implementing...", "Plan approved by A", 2),)
        )
        self.assertEqual(runner.calls[0][1]["timeout"], linear_poll.TIMEOUT_SECONDS)
        self.assertFalse(runner.calls[0][1]["check"])
        self.assertTrue(
            self.log.read_text().startswith("2026-11-06T03:00:00Z cost_usd=0.0057 input=8")
        )

    def test_an_unwritable_usage_log_still_returns_the_rows(self) -> None:
        rows = json.dumps([{"ticket": "ACC-1", "status": "Planning...", "timeline": "t"}])
        log = self.dir / "missing" / "wave-state.usage.log"
        with self.assertLogs("jaidev_watch", "WARNING"):
            got = linear_poll.read_statuses(["ACC-1"], log, NOW, runner=FakeRunner(envelope(rows)))
        self.assertEqual(got[0].status, "Planning...")

    def test_malformed_replies_raise(self) -> None:
        cases = [
            ("not json at all", 0),
            (envelope("no array here"), 0),
            (envelope('[{"status": "x"}]'), 0),
            (envelope('[{"ticket": "ACC-1", "status": 5}]'), 0),
            (envelope("[1, 2"), 0),
            ("", 1),
        ]
        for stdout, code in cases:
            with (
                self.subTest(stdout=stdout[:40], code=code),
                self.assertRaises(linear_poll.LinearPollError),
            ):
                linear_poll.read_statuses(["ACC-1"], self.log, NOW, runner=FakeRunner(stdout, code))

    def test_timeout_raises_linear_poll_error(self) -> None:
        def slow(args: list[str], **_: object) -> subprocess.CompletedProcess[str]:
            raise subprocess.TimeoutExpired(args, 240)

        with self.assertRaises(linear_poll.LinearPollError):
            linear_poll.read_statuses(["ACC-1"], self.log, NOW, runner=slow)


if __name__ == "__main__":
    unittest.main()

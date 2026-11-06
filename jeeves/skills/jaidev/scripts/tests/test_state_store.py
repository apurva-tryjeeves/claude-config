"""Load, save, locking and the wave2 state file."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from jaidev_watch import state_store
from jaidev_watch.models import EventKind, Stage, TicketState, parse_time

SCRIPTS = Path(__file__).resolve().parents[1]
WAVE2 = Path(__file__).resolve().parent / "fixtures" / "wave2-state.json"
NOW = parse_time("2026-11-06T03:00:00Z")

INCREMENT = """
import sys
from dataclasses import replace
from pathlib import Path
from jaidev_watch import state_store

path = Path(sys.argv[1])
for _ in range(int(sys.argv[2])):
    def bump(wave):
        ticket = wave.tickets["ACC-1"]
        count = int(ticket.extra.get("count", 0)) + 1
        ticket = state_store.set_field(ticket, "count", count)
        return replace(wave, tickets={**wave.tickets, "ACC-1": ticket})
    state_store.update(path, bump)
"""


class StateStoreTest(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.dir)

    def test_wave2_loads_and_round_trips_with_schema_version_2(self) -> None:
        path = self.dir / "wave2-state.json"
        shutil.copy(WAVE2, path)
        original = json.loads(path.read_text())
        wave = state_store.load(path)
        self.assertEqual(wave.tickets["ACC-1670"].approved_at, parse_time("2026-11-06T02:41:33Z"))
        self.assertEqual(wave.tickets["ACC-1670"].extra["mergeCommit"], "0ac0f14")
        state_store.save(path, wave)
        saved = json.loads(path.read_text())
        self.assertEqual(saved["schemaVersion"], 2)
        self.assertEqual(saved["tickets"], original["tickets"])
        self.assertEqual(state_store.load(path), wave)
        self.assertIn("🟦", path.read_text())

    def test_every_field_round_trips(self) -> None:
        ticket = TicketState(
            agent="a1",
            repo_dir="/r",
            stage=Stage.PR_CI,
            stage_since=NOW,
            estimate=2,
            paused_seconds=30,
            sonar_findings=False,
            deadline_event=EventKind.CI_LATE,
            fired_event=EventKind.NO_ACK,
            extra={"agentNote": "x"},
        )
        data = state_store.ticket_to_json(ticket)
        self.assertEqual(data["stage"], "pr-ci")
        self.assertEqual(data["stageSince"], "2026-11-06T03:00:00Z")
        self.assertEqual(state_store.ticket_from_json(data), ticket)

    def test_wrong_types_raise_state_file_error(self) -> None:
        cases = [
            {"prNumber": "96"},
            {"stage": "nowhere"},
            {"approvedAt": "yesterday"},
            {"merged": 1},
        ]
        for data in cases:
            with self.subTest(data=data), self.assertRaises(state_store.StateFileError):
                state_store.ticket_from_json(data)

    def test_newer_schema_is_refused(self) -> None:
        with self.assertRaises(state_store.StateFileError):
            state_store.wave_from_json({"schemaVersion": 3, "tickets": {}})

    def test_parse_value(self) -> None:
        cases = [
            ("approvedAt", "now", NOW),
            ("approvedAt", "2026-11-06T02:40:00Z", parse_time("2026-11-06T02:40:00Z")),
            ("estimate", "3", 3),
            ("merged", "true", True),
            ("stage", "plan-ready", Stage.PLAN_READY),
            ("color", "🟦", "🟦"),
            ("agentNote", "free text", "free text"),
            ("estimate", "null", None),
        ]
        for key, text, expected in cases:
            with self.subTest(key=key, text=text):
                self.assertEqual(state_store.parse_value(key, text, NOW), expected)

    def test_failed_write_keeps_the_old_file(self) -> None:
        path = self.dir / "state.json"
        state_store.save(path, state_store.wave_from_json({"tickets": {"ACC-1": {}}}))
        before = path.read_text()
        bad = state_store.wave_from_json({"tickets": {}, "x": object()})
        with self.assertRaises(TypeError):
            state_store.save(path, bad)
        self.assertEqual(path.read_text(), before)
        self.assertEqual([p.name for p in self.dir.iterdir() if p.name.startswith(".")], [])

    def test_two_writers_lose_no_update(self) -> None:
        path = self.dir / "state.json"
        state_store.save(path, state_store.wave_from_json({"tickets": {"ACC-1": {}}}))
        writers, rounds = 4, 25
        processes = [
            subprocess.Popen([sys.executable, "-c", INCREMENT, str(path), str(rounds)], cwd=SCRIPTS)
            for _ in range(writers)
        ]
        for process in processes:
            self.assertEqual(process.wait(timeout=60), 0)
        count = state_store.load(path).tickets["ACC-1"].extra["count"]
        self.assertEqual(count, writers * rounds)


if __name__ == "__main__":
    unittest.main()

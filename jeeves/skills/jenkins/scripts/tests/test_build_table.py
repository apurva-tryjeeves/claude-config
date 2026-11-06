"""Tests for build-table.py, loaded by path because of its hyphenated name."""

from __future__ import annotations

import importlib.util
import io
import json
import os
import sys
import time
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import ModuleType
from unittest import mock

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures"


def load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("build_table", HERE.parent / "build-table.py")
    assert spec is not None
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


bt = load_module()


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text()


def run_cli(argv: list[str], stdin: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with (
        redirect_stdout(out),
        redirect_stderr(err),
        mock.patch.object(sys, "stdin", io.StringIO(stdin)),
    ):
        code = bt.main(argv)
    return code, out.getvalue(), err.getvalue()


class TestFormatting(unittest.TestCase):
    def test_dur(self) -> None:
        for ms, expected in [
            (0, "0s"),
            (-5000, "0s"),
            (999, "0s"),
            (5000, "5s"),
            (59999, "59s"),
            (60000, "1m00s"),
            (567000, "9m27s"),
            (1109000, "18m29s"),
        ]:
            with self.subTest(ms=ms):
                self.assertEqual(bt.dur(ms), expected)

    def test_icon_for(self) -> None:
        for result, icon in [
            ("SUCCESS", "✅"),
            ("FAILURE", "❌"),
            ("UNSTABLE", "⚠️"),
            ("ABORTED", "⛔"),
            (None, "⏳"),
            ("WEIRD", "❓"),
        ]:
            with self.subTest(result=result):
                self.assertEqual(bt.icon_for(result), icon)


class TestParse(unittest.TestCase):
    def test_list_and_single(self) -> None:
        listed = bt.parse_builds(json.loads(fixture("builds_list.json")))
        self.assertEqual([b.number for b in listed], [45269, 45268, 45267, 45266])
        single = bt.parse_builds(json.loads(fixture("build_running.json")))
        self.assertEqual(single, [bt.Build(45270, None, 0, 1700000100000)])

    def test_malformed(self) -> None:
        for payload in [[], "x", {"builds": [{"number": 1}]}, {"builds": [1]}, {"builds": None}]:
            with self.subTest(payload=payload), self.assertRaises(bt.TableError):
                bt.parse_builds(payload)


class TestRender(unittest.TestCase):
    def setUp(self) -> None:
        self._tz = os.environ.get("TZ")
        os.environ["TZ"] = "UTC"
        time.tzset()

    def tearDown(self) -> None:
        if self._tz is None:
            del os.environ["TZ"]
        else:
            os.environ["TZ"] = self._tz
        time.tzset()

    def test_list_with_base(self) -> None:
        builds = bt.parse_builds(json.loads(fixture("builds_list.json")))
        text = bt.render(builds, "https://j/job/x", 0)
        self.assertEqual(
            text.splitlines(),
            [
                "| Result | Build | Duration | Started |",
                "|---|---|---|---|",
                "| ⛔ ABORTED | [#45269](https://j/job/x/45269/) | 18m29s | 14 Nov 10:13pm |",
                "| ✅ SUCCESS | [#45268](https://j/job/x/45268/) | 9m27s | 14 Nov 7:26pm |",
                "| ❌ FAILURE | [#45267](https://j/job/x/45267/) | 42s | 14 Nov 4:40pm |",
                "| ⚠️ UNSTABLE | [#45266](https://j/job/x/45266/) | 5s | 14 Nov 1:53pm |",
            ],
        )

    def test_running_build_measures_from_start_without_base(self) -> None:
        builds = bt.parse_builds(json.loads(fixture("build_running.json")))
        now_ms = 1700000100000 + 200_000
        row = bt.render(builds, "", now_ms).splitlines()[2]
        self.assertEqual(row, "| ⏳ building | #45270 | 3m20s | 14 Nov 10:15pm |")


class TestCli(unittest.TestCase):
    def test_base_trailing_slash_stripped(self) -> None:
        code, out, _ = run_cli(["https://j/job/x/"], fixture("build_running.json"))
        self.assertEqual(code, 0)
        self.assertIn("[#45270](https://j/job/x/45270/)", out)

    def test_invalid_json_is_clean_error(self) -> None:
        code, out, err = run_cli([], "garbage")
        self.assertEqual((code, out), (1, ""))
        self.assertIn("not valid JSON", err)
        self.assertNotIn("Traceback", err)

    def test_missing_field_is_clean_error(self) -> None:
        code, out, err = run_cli([], '{"builds":[{"number":1}]}')
        self.assertEqual((code, out), (1, ""))
        self.assertIn("malformed", err)


if __name__ == "__main__":
    unittest.main()

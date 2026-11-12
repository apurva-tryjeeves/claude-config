"""Tests for build-params.py, loaded by path because of its hyphenated name."""

from __future__ import annotations

import importlib.util
import io
import json
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import ModuleType
from typing import Any
from unittest import mock

SCRIPTS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS))

import modules  # noqa: E402


def load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("build_params", SCRIPTS / "build-params.py")
    assert spec is not None
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


bp = load_module()


def modules_string(*services: str) -> str:
    sets = [modules.parse_set(f"{name}=development") for name in services]
    return modules.render(modules.build(sets))


def build(number: int, **extra: Any) -> dict[str, Any]:
    params = [{"name": k, "value": v} for k, v in extra.pop("params", {}).items()]
    return {"number": number, "actions": [{}, {"parameters": params}], **extra}


def run_cli(argv: list[str], stdin: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with (
        redirect_stdout(out),
        redirect_stderr(err),
        mock.patch.object(sys, "stdin", io.StringIO(stdin)),
    ):
        code = bp.main(argv)
    return code, out.getvalue(), err.getvalue()


def run_builds(argv: list[str], builds: list[dict[str, Any]]) -> tuple[int, str, str]:
    return run_cli(argv, json.dumps({"builds": builds}))


class TestParams(unittest.TestCase):
    def test_build_params_shapes(self) -> None:
        for actions, expected in [
            ([], {}),
            ([{}], {}),
            ([{"parameters": None}], {}),
            ([{"_class": "x"}, {"parameters": [{"name": "A", "value": "1"}]}], {"A": "1"}),
            (None, {}),
        ]:
            with self.subTest(actions=actions):
                self.assertEqual(bp.build_params({"actions": actions}), expected)
        self.assertEqual(bp.build_params({}), {})


class TestBuilding(unittest.TestCase):
    def test_building_only(self) -> None:
        code, out, _ = run_builds(
            ["--building"],
            [
                build(5, building=True, params={"ENVIRONMENT": "develop-07"}),
                build(4, building=False, params={"ENVIRONMENT": "develop-08"}),
                {"number": 3, "building": True, "actions": [{}]},
            ],
        )
        self.assertEqual(code, 0)
        self.assertEqual(out, "building: 5 develop-07\nbuilding: 3 None\n")


class TestSingleService(unittest.TestCase):
    def test_selection(self) -> None:
        one = modules_string("notification")
        two = modules_string("notification", "api")
        none = modules_string()
        ok = {"result": "SUCCESS", "duration": 1234}
        code, out, err = run_builds(
            ["--single-service"],
            [
                build(10, **ok, params={"MODULES": one}),
                build(9, **ok, params={"MODULES": two}),
                build(8, **ok, params={"MODULES": none}),
                build(7, result="FAILURE", duration=5, params={"MODULES": one}),
                build(6, result="SUCCESS", duration=0, params={"MODULES": one}),
                build(5, **ok, params={"MODULES": "true,x"}),
                build(4, **ok),
            ],
        )
        self.assertEqual(code, 0)
        self.assertEqual(out, "notification 10 1234\n")
        self.assertIn("build 5", err)
        self.assertIn("cannot decode MODULES", err)


class TestDefault(unittest.TestCase):
    def test_tab_separated_with_dashes(self) -> None:
        code, out, _ = run_builds(
            [],
            [
                build(2, building=False, result="SUCCESS", duration=9, params={"ENVIRONMENT": "e"}),
                {"number": 1, "building": True},
            ],
        )
        self.assertEqual(code, 0)
        self.assertEqual(out, "2\tFalse\tSUCCESS\t9\te\n1\tTrue\t-\t-\t-\n")


class TestBadInput(unittest.TestCase):
    def test_bad_json(self) -> None:
        code, out, err = run_cli([], "not json")
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertIn("not valid JSON", err)

    def test_missing_builds(self) -> None:
        code, _, err = run_cli([], "{}")
        self.assertEqual(code, 1)
        self.assertIn("builds", err)

    def test_modes_exclusive(self) -> None:
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as ctx:
            run_cli(["--building", "--single-service"], "{}")
        self.assertEqual(ctx.exception.code, 2)


if __name__ == "__main__":
    unittest.main()

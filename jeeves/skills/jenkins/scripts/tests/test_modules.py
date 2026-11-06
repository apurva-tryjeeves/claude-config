"""Tests for modules.py (pure logic and CLI)."""

from __future__ import annotations

import io
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import modules


def run_cli(*argv: str, stdin: str = "") -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with (
        redirect_stdout(out),
        redirect_stderr(err),
        mock.patch.object(sys, "stdin", io.StringIO(stdin)),
    ):
        try:
            code = modules.main(list(argv))
        except SystemExit as exc:
            code = int(exc.code) if isinstance(exc.code, int) else 1
    return code, out.getvalue(), err.getvalue()


class TestDefaults(unittest.TestCase):
    def test_default_branch(self) -> None:
        for name, expected in [
            ("api", "development"),
            ("gemini", "main"),
            ("aiweb", "main"),
            ("simulationserver", "main"),
        ]:
            with self.subTest(name=name):
                self.assertEqual(modules.default_branch(name), expected)

    def test_service_table_is_consistent(self) -> None:
        self.assertEqual(len(modules.NAMES), len(set(modules.NAMES)))
        self.assertEqual(len(modules.SERVICES), 45)


class TestParseSet(unittest.TestCase):
    def test_valid(self) -> None:
        cases = [
            ("api=development", ("api", "development", modules.Mode.LATEST)),
            ("api=feat/X", ("api", "feat/X", modules.Mode.REBUILD)),
            ("web=development:rebuild", ("web", "development", modules.Mode.REBUILD)),
            ("web=feat/X:latest", ("web", "feat/X", modules.Mode.LATEST)),
        ]
        for item, (name, branch, mode) in cases:
            with self.subTest(item=item):
                req = modules.parse_set(item)
                self.assertEqual((req.name, req.branch, req.mode), (name, branch, mode))

    def test_errors(self) -> None:
        cases = [
            ("api", "needs a branch"),
            ("api=", "needs a branch"),
            ("nope=x", "unknown service 'nope'"),
            ("api=x:zzz", "mode 'zzz' is not one of latest, rebuild"),
        ]
        for item, text in cases:
            with self.subTest(item=item), self.assertRaises(modules.ModulesError) as ctx:
                modules.parse_set(item)
            self.assertIn(text, str(ctx.exception))


class TestRoundTrip(unittest.TestCase):
    def test_build_render_parse(self) -> None:
        reqs = [modules.parse_set("accounting=feat/A"), modules.parse_set("api=development")]
        triples = modules.build(reqs)
        packed = modules.render(triples)
        self.assertTrue(packed.endswith(","))
        self.assertEqual(packed.count(","), 45 * 3)
        parsed = modules.parse(packed)
        self.assertEqual(parsed, triples)
        enabled = [modules.NAMES[i] for i, t in enumerate(parsed) if t.enabled]
        self.assertEqual(enabled, ["api", "accounting"])

    def test_disabled_services_keep_default_branch(self) -> None:
        triples = modules.build([])
        self.assertEqual(
            triples[modules.NAMES.index("gemini")].fields(), ("false", "main", "latest")
        )
        self.assertEqual(triples[0].fields(), ("false", "development", "latest"))

    def test_parse_wrong_count(self) -> None:
        with self.assertRaises(modules.ModulesError) as ctx:
            modules.parse("a,b,c,d")
        self.assertIn("holds 4 fields (1.33 triples)", str(ctx.exception))

    def test_summarize(self) -> None:
        self.assertEqual(modules.summarize(modules.build([])), "  (no service enabled)")
        line = modules.summarize(modules.build([modules.parse_set("api=a")]))
        self.assertEqual(line, "  position  1 api                    branch a mode rebuild")


class TestCli(unittest.TestCase):
    def test_set_stdout_value_stderr_summary(self) -> None:
        code, out, err = run_cli("--set", "api=a")
        self.assertEqual(code, 0)
        self.assertTrue(out.startswith("true,a,rebuild,false,development,latest,"))
        self.assertIn("45 services, enabled:", err)
        self.assertNotIn("45 services", out)

    def test_decode_arg_and_stdin(self) -> None:
        packed = run_cli("--set", "api=a")[1].strip()
        for args, stdin in [(("--decode", packed), ""), (("--decode", "-"), packed + "\n")]:
            with self.subTest(args=args):
                code, out, _ = run_cli(*args, stdin=stdin)
                self.assertEqual(code, 0)
                self.assertTrue(out.startswith("45 services, enabled:\n  position  1 api"))

    def test_list(self) -> None:
        code, out, _ = run_cli("--list")
        lines = out.splitlines()
        self.assertEqual(code, 0)
        self.assertEqual(len(lines), 46)
        self.assertEqual(lines[0], f"{'#':>3}  {'Service':<22} {'Default':<12} Repo")
        self.assertIn("backend", lines[1])

    def test_failures_exit_one_with_message_no_traceback(self) -> None:
        for args in [("--set", "nope=x"), ("--set", "api"), ("--decode", "bad")]:
            with self.subTest(args=args):
                code, out, err = run_cli(*args)
                self.assertEqual((code, out), (1, ""))
                self.assertNotIn("Traceback", err)
                self.assertTrue(err.strip())

    def test_no_arguments_is_usage_error(self) -> None:
        code, _, err = run_cli()
        self.assertEqual(code, 2)
        self.assertIn("choose --set, --decode, or --list", err)


if __name__ == "__main__":
    unittest.main()

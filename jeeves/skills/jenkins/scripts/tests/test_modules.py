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
            ("apex", "development"),
            ("aiweb", "main"),
            ("simulationserver", "main"),
            ("webdemo", "master"),
        ]:
            with self.subTest(name=name):
                self.assertEqual(modules.default_branch(name), expected)

    def test_service_table_is_consistent(self) -> None:
        self.assertEqual(len(modules.NAMES), len(set(modules.NAMES)))
        self.assertEqual(len(modules.SERVICES), 46)


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
        self.assertEqual(packed.count(","), 46 * 3)
        parsed = modules.parse(packed)
        self.assertEqual(parsed, triples)
        enabled = [modules.NAMES[i] for i, t in enumerate(parsed) if t.enabled]
        self.assertEqual(enabled, ["api", "accounting"])

    def test_disabled_services_keep_default_branch(self) -> None:
        triples = modules.build([])
        self.assertEqual(
            triples[modules.NAMES.index("aiweb")].fields(), ("false", "main", "latest")
        )
        self.assertEqual(triples[0].fields(), ("false", "development", "latest"))

    def test_parse_wrong_count(self) -> None:
        with self.assertRaises(modules.ModulesError) as ctx:
            modules.parse("a,b,c,d")
        self.assertIn("holds 4 fields (1.33 triples)", str(ctx.exception))

    def test_parse_drops_trailing_form_triples(self) -> None:
        triples = modules.build([modules.parse_set("apex=feat/X")])
        packed = modules.render(triples) + "false,main,latest,false,main,rebuild,"
        self.assertEqual(modules.parse(packed), triples)

    def test_summarize(self) -> None:
        self.assertEqual(modules.summarize(modules.build([])), "  (no service enabled)")
        line = modules.summarize(modules.build([modules.parse_set("api=a")]))
        self.assertEqual(line, "  position  1 api                    branch a mode rebuild")


def groovy_for(names: list[str]) -> str:
    """A minimal jeevesPlatformInfo.groovy holding these modules plus two skipped ones."""
    entries = [
        f"  '{n}': [\n    'giturl':'git@github.com:JeevesInc/{n}-repo',\n  ]," for n in names
    ]
    entries.insert(1, "  'nogit': [\n    'giturl':'',\n  ],")
    entries.append(
        "  'calm': [\n    'giturl':'git@github.com:JeevesInc/CALM',\n"
        "    'standaloneHelmRelease': [\n      'file': 'x.yml',\n    ]\n  ],"
    )
    return "def modules = [\n" + "\n".join(entries) + "\n]\n"


class TestCheckLibrary(unittest.TestCase):
    def test_library_services_filters_like_the_pipeline(self) -> None:
        services = modules.library_services(groovy_for(["api", "web"]))
        self.assertEqual(
            services, [modules.Service("api", "api-repo"), modules.Service("web", "web-repo")]
        )

    def test_in_sync(self) -> None:
        self.assertEqual(
            modules.check_library(groovy_for(list(modules.NAMES))),
            "SERVICES matches jenkins-library (46 services)",
        )

    def test_drift_lists_changes_and_replacement(self) -> None:
        names = [n for n in modules.NAMES if n != "apex"] + ["newsvc"]
        with self.assertRaises(modules.ModulesError) as ctx:
            modules.check_library(groovy_for(names))
        text = str(ctx.exception)
        self.assertIn("added there: newsvc", text)
        self.assertIn("removed there: apex", text)
        self.assertIn('    Service("newsvc", "newsvc-repo"),', text)

    def test_missing_map(self) -> None:
        with self.assertRaises(modules.ModulesError):
            modules.library_services("def other = []")

    def test_cli_check_stdin(self) -> None:
        code, out, _ = run_cli("--check", "-", stdin=groovy_for(list(modules.NAMES)))
        self.assertEqual(code, 0)
        self.assertIn("matches jenkins-library", out)


class TestCli(unittest.TestCase):
    def test_set_stdout_value_stderr_summary(self) -> None:
        code, out, err = run_cli("--set", "api=a")
        self.assertEqual(code, 0)
        self.assertTrue(out.startswith("true,a,rebuild,false,development,latest,"))
        self.assertIn("46 services, enabled:", err)
        self.assertNotIn("46 services", out)

    def test_decode_arg_and_stdin(self) -> None:
        packed = run_cli("--set", "api=a")[1].strip()
        for args, stdin in [(("--decode", packed), ""), (("--decode", "-"), packed + "\n")]:
            with self.subTest(args=args):
                code, out, _ = run_cli(*args, stdin=stdin)
                self.assertEqual(code, 0)
                self.assertTrue(out.startswith("46 services, enabled:\n  position  1 api"))

    def test_list(self) -> None:
        code, out, _ = run_cli("--list")
        lines = out.splitlines()
        self.assertEqual(code, 0)
        self.assertEqual(len(lines), 47)
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
        self.assertIn("choose --set, --decode, --list, or --check", err)


if __name__ == "__main__":
    unittest.main()

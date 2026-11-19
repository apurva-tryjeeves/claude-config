import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from update_local_installs import (
    Install,
    StepError,
    load_installed,
    local_installs,
    main,
    run_in,
)


class LocalInstallsTest(unittest.TestCase):
    def test_keeps_only_local_scope_of_the_plugin(self) -> None:
        data: dict[str, object] = {
            "version": 2,
            "plugins": {
                "jeeves@jeeves-local": [
                    {"scope": "local", "projectPath": "/a", "version": "3.7.38"},
                    {"scope": "user", "version": "3.7.39"},
                    {"scope": "local", "projectPath": "/b", "version": "3.7.40"},
                ],
                "other@market": [
                    {"scope": "local", "projectPath": "/c", "version": "1.0.0"},
                ],
            },
        }
        self.assertEqual(
            local_installs(data, "jeeves@jeeves-local"),
            [Install(Path("/a"), "3.7.38"), Install(Path("/b"), "3.7.40")],
        )

    def test_reads_a_file_without_the_plugins_wrapper(self) -> None:
        data: dict[str, object] = {
            "jeeves@jeeves-local": [
                {"scope": "local", "projectPath": "/a", "version": "3.7.38"},
            ]
        }
        self.assertEqual(
            local_installs(data, "jeeves@jeeves-local"),
            [Install(Path("/a"), "3.7.38")],
        )

    def test_returns_empty_for_a_missing_plugin(self) -> None:
        self.assertEqual(local_installs({"plugins": {}}, "jeeves@jeeves-local"), [])


class ErrorHandlingTest(unittest.TestCase):
    def test_missing_installed_file_is_a_step_error(self) -> None:
        with self.assertRaisesRegex(StepError, "not found"):
            load_installed(Path("/nonexistent/installed_plugins.json"))

    def test_invalid_json_is_a_step_error(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".json") as handle:
            handle.write("{not json")
            handle.flush()
            with self.assertRaisesRegex(StepError, "cannot read"):
                load_installed(Path(handle.name))

    def test_missing_cli_is_a_step_error(self) -> None:
        with (
            mock.patch("subprocess.run", side_effect=FileNotFoundError),
            self.assertRaisesRegex(StepError, "not found on PATH"),
        ):
            run_in(Path("/"), ["update", "x"])

    def test_timeout_is_a_step_error(self) -> None:
        timeout = subprocess.TimeoutExpired(cmd="claude", timeout=1)
        with (
            mock.patch("subprocess.run", side_effect=timeout),
            self.assertRaisesRegex(StepError, "no answer"),
        ):
            run_in(Path("/"), ["update", "x"])

    def test_nonzero_exit_reports_last_output_line(self) -> None:
        failed = subprocess.CompletedProcess([], 1, stdout="a\nmarketplace down\n")
        with (
            mock.patch("subprocess.run", return_value=failed),
            self.assertRaisesRegex(StepError, "marketplace down"),
        ):
            run_in(Path("/"), ["update", "x"])

    def test_one_failure_does_not_stop_the_rest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp, "a"), Path(tmp, "b")
            a.mkdir()
            b.mkdir()
            installed = Path(tmp, "installed.json")
            entries = [
                {"scope": "local", "projectPath": str(p), "version": "1.0.0"}
                for p in (a, b)
            ]
            installed.write_text(json.dumps({"plugins": {"p@m": entries}}))
            results = [
                subprocess.CompletedProcess([], 1, stdout="boom"),
                subprocess.CompletedProcess([], 0, stdout="ok"),
            ]
            with (
                mock.patch("subprocess.run", side_effect=results) as run,
                mock.patch("sys.stdout"),
            ):
                code = main(["--plugin", "p@m", "--installed", str(installed)])
            self.assertEqual(run.call_count, 2)
            self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()

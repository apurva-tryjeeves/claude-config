"""Update every local-scope install of the jeeves plugin to the marketplace version.

Reads ~/.claude/plugins/installed_plugins.json, runs
`claude plugin update <plugin> --scope local` inside each project that has the
plugin installed, and uninstalls it from projects whose folder no longer exists
(or that are passed with --remove).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

PLUGIN = "jeeves@jeeves-local"
INSTALLED = Path.home() / ".claude" / "plugins" / "installed_plugins.json"


@dataclass(frozen=True)
class Install:
    project: Path
    version: str


def local_installs(data: dict[str, object], plugin: str) -> list[Install]:
    """Return the plugin's local-scope installs, one per project path."""
    plugins = data.get("plugins", data)
    if not isinstance(plugins, dict):
        return []
    entries = plugins.get(plugin, [])
    if not isinstance(entries, list):
        return []
    installs: list[Install] = []
    for entry in entries:
        if not isinstance(entry, dict) or entry.get("scope") != "local":
            continue
        project = entry.get("projectPath")
        version = entry.get("version")
        if isinstance(project, str) and isinstance(version, str):
            installs.append(Install(Path(project), version))
    return installs


TIMEOUT_SECONDS = 120


class StepError(Exception):
    """One install's update or uninstall failed; the run moves on to the next."""


def load_installed(path: Path) -> dict[str, object]:
    """Read installed_plugins.json, raising StepError with a readable reason."""
    try:
        data = json.loads(path.read_text())
    except FileNotFoundError as exc:
        raise StepError(f"{path} not found — is the plugin installed?") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise StepError(f"cannot read {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise StepError(f"{path} holds {type(data).__name__}, expected an object")
    return data


def run_in(project: Path, args: list[str]) -> str:
    """Run `claude plugin <args>` in a project and return its last output line."""
    try:
        result = subprocess.run(
            ["claude", "plugin", *args],
            cwd=project,
            capture_output=True,
            text=True,
            check=False,
            timeout=TIMEOUT_SECONDS,
        )
    except FileNotFoundError as exc:
        raise StepError("`claude` CLI not found on PATH") from exc
    except subprocess.TimeoutExpired as exc:
        raise StepError(f"no answer after {TIMEOUT_SECONDS}s") from exc
    except OSError as exc:
        raise StepError(str(exc)) from exc
    output = "\n".join(part or "" for part in (result.stdout, result.stderr))
    lines = output.strip().splitlines()
    last = lines[-1] if lines else ""
    if result.returncode != 0:
        raise StepError(last or f"exit code {result.returncode}")
    return last


def uninstall(project: Path, plugin: str) -> str:
    """Uninstall from a project, recreating its folder briefly when it is gone."""
    created = not project.exists()
    if created:
        try:
            project.mkdir(parents=True)
        except OSError as exc:
            raise StepError(f"cannot recreate folder to uninstall: {exc}") from exc
    try:
        return run_in(project, ["uninstall", plugin, "--scope", "local"])
    finally:
        if created:
            try:
                project.rmdir()
            except OSError as exc:
                print(f"warning: left {project} in place: {exc}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plugin", default=PLUGIN)
    parser.add_argument("--installed", type=Path, default=INSTALLED)
    parser.add_argument(
        "--remove",
        type=Path,
        action="append",
        default=[],
        help="project path to uninstall from instead of updating (repeatable)",
    )
    args = parser.parse_args(argv)

    try:
        data = load_installed(args.installed)
    except StepError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    remove = {path.resolve() for path in args.remove}
    failed: list[tuple[Path, str]] = []
    for install in local_installs(data, args.plugin):
        try:
            if install.project.resolve() in remove or not install.project.exists():
                uninstall(install.project, args.plugin)
                status = "removed"
            else:
                run_in(install.project, ["update", args.plugin, "--scope", "local"])
                status = "updated"
        except StepError as exc:
            failed.append((install.project, str(exc)))
            status = "FAILED"
        print(f"{install.version:>8}  {status:<8}  {install.project}", flush=True)

    if failed:
        print(f"\n{len(failed)} failed — rerun the script to retry them:")
        for project, reason in failed:
            print(f"  {project}: {reason}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

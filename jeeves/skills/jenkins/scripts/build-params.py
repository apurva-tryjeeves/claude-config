#!/usr/bin/env python3
"""Extract build parameters from a Jenkins `builds[...]` JSON response.

Reads the response on stdin; each build's parameters live in
`actions[*].parameters[*]` as `{name, value}`.

    jenkins-api "job/deploy-DEVELOP-environment/api/json?tree=builds[number,building,\
result,duration,actions[parameters[name,value]]]{0,10}" \
      | python3 scripts/build-params.py [--building | --single-service]

Modes (mutually exclusive):
  --building        `building: <number> <ENVIRONMENT>` per running build
  --single-service  `<service> <number> <duration>` per SUCCESS build whose MODULES
                    enables exactly one service
  (none)            tab-separated `number building result duration ENVIRONMENT`
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Final, TextIO

sys.path.insert(0, str(Path(__file__).resolve().parent))

import modules  # noqa: E402

LOG: Final = logging.getLogger("build-params")
MISSING: Final = "-"
SUCCESS: Final = "SUCCESS"


class ParamsError(Exception):
    """An expected, user-facing failure: reported as a message and exit code 1."""


def read_builds(stream: TextIO) -> list[Mapping[str, Any]]:
    """Parse stdin into the list of build objects."""
    try:
        payload = json.load(stream)
    except json.JSONDecodeError as exc:
        raise ParamsError(f"stdin is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("builds"), list):
        raise ParamsError("expected a JSON object with a `builds` list on stdin")
    builds: list[Mapping[str, Any]] = payload["builds"]
    return builds


def build_params(build: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten `actions[*].parameters[*]` into a name -> value dict."""
    params: dict[str, Any] = {}
    for action in build.get("actions") or []:
        for param in (action or {}).get("parameters") or []:
            if isinstance(param, dict) and "name" in param:
                params[param["name"]] = param.get("value")
    return params


def _show(value: object) -> str:
    return MISSING if value is None else str(value)


def building_lines(builds: Sequence[Mapping[str, Any]]) -> list[str]:
    return [
        f"building: {b.get('number')} {build_params(b).get('ENVIRONMENT')}"
        for b in builds
        if b.get("building") is True
    ]


def single_service(build: Mapping[str, Any]) -> str | None:
    """Return the one enabled service of a SUCCESS build, else None."""
    if build.get("result") != SUCCESS or not build.get("duration"):
        return None
    raw = build_params(build).get("MODULES")
    if not raw:
        return None
    try:
        triples = modules.parse(str(raw))
    except modules.ModulesError as exc:
        LOG.warning("build-params: build %s: cannot decode MODULES: %s", build.get("number"), exc)
        return None
    enabled = [name for name, t in zip(modules.NAMES, triples, strict=True) if t.enabled]
    return enabled[0] if len(enabled) == 1 else None


def single_service_lines(builds: Sequence[Mapping[str, Any]]) -> list[str]:
    lines: list[str] = []
    for b in builds:
        service = single_service(b)
        if service is not None:
            lines.append(f"{service} {b.get('number')} {b.get('duration')}")
    return lines


def default_lines(builds: Sequence[Mapping[str, Any]]) -> list[str]:
    return [
        "\t".join(
            _show(v)
            for v in (
                b.get("number"),
                b.get("building"),
                b.get("result"),
                b.get("duration"),
                build_params(b).get("ENVIRONMENT"),
            )
        )
        for b in builds
    ]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="build-params.py", description="Read build parameters.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--building", action="store_true", help="list running builds")
    group.add_argument(
        "--single-service", action="store_true", help="list single-service SUCCESS builds"
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stderr, force=True)
    args = build_parser().parse_args(argv)
    try:
        builds = read_builds(sys.stdin)
    except ParamsError as exc:
        LOG.error("build-params: %s", exc)
        return 1
    if args.building:
        lines = building_lines(builds)
    elif args.single_service:
        lines = single_service_lines(builds)
    else:
        lines = default_lines(builds)
    for line in lines:
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())

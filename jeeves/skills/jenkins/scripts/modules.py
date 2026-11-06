#!/usr/bin/env python3
"""Build and decode the packed MODULES parameter for `deploy-DEVELOP-environment`.

MODULES is one comma-separated string holding three fields per service —
`enable,branch,mode` — in a fixed positional order with no names, plus a
trailing comma. Build it here so the field count and every service's position
are checked, and read an existing value back with --decode.

Only the services passed with --set are enabled. Every other service gets the
disabled triple `false,<default branch>,latest`, and the pipeline
leaves disabled services untouched in the environment.

    # deploy these services, nothing else
    python3 scripts/modules.py --set accounting=feat/ACC-1568 --set web=feat/ACC-1603

    # read a string back, or list the service order
    python3 scripts/modules.py --decode "$MODULES"
    python3 scripts/modules.py --list

The built string goes to stdout and a summary to stderr, so
`MODULES=$(python3 scripts/modules.py ...)` captures the value alone.
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Final

LOG: Final = logging.getLogger("modules")


class ModulesError(Exception):
    """An expected, user-facing failure: reported as a message and exit code 1."""


class Mode(StrEnum):
    """Build mode field of a service's triple."""

    LATEST = "latest"
    REBUILD = "rebuild"


@dataclass(frozen=True, slots=True)
class Service:
    """One deployable service: its MODULES key and its git repo ('' when none)."""

    name: str
    repo: str


@dataclass(frozen=True, slots=True)
class Triple:
    """The `enable,branch,mode` fields the job reads for one service."""

    enabled: bool
    branch: str
    mode: str

    def fields(self) -> tuple[str, str, str]:
        return ("true" if self.enabled else "false", self.branch, self.mode)


@dataclass(frozen=True, slots=True)
class SetRequest:
    """One parsed `--set SERVICE=BRANCH[:MODE]` argument."""

    name: str
    branch: str
    mode: Mode


# Positional order the job reads MODULES in. Source of truth: jenkins-library
# vars/jeevesPlatformInfo.groovy, the `modules` map filtered to a non-empty
# `giturl` and no `standaloneHelmRelease`. Update this list when that changes.
SERVICES: Final[tuple[Service, ...]] = (
    Service("api", "backend"),
    Service("frontend", ""),
    Service("cms", "cms"),
    Service("bankingservice", ""),
    Service("pts", ""),
    Service("cashbackservice", ""),
    Service("lumenengine", "lumen-engine"),
    Service("trunarrative", "trunarrative-service"),
    Service("creditstatements", ""),
    Service("driveservice", ""),
    Service("btgintegration", ""),
    Service("authenticationservice", "authentication-service"),
    Service("loanservice", "loan-service"),
    Service("openbanking", "open-banking-service"),
    Service("flows", ""),
    Service("cardsgateway", ""),
    Service("web", "jeeves-web"),
    Service("expensemanagement", "expense-management-service"),
    Service("productaccount", "product-account-service"),
    Service("wallet", "wallet-service"),
    Service("billpay", "billpay-service"),
    Service("ocr", ""),
    Service("cards", "cards-service"),
    Service("simulationserver", "jeeves-simulation-server"),
    Service("accounting", "accounting-service"),
    Service("notification", "notification-service"),
    Service("risk", ""),
    Service("underwriting", "underwriting-service"),
    Service("transactions", "transactions-service"),
    Service("pricing", ""),
    Service("apdataconnector", "ap-data-source-connector"),
    Service("reconciliation", ""),
    Service("publicapi", "public-api-service"),
    Service("utvservice", ""),
    Service("aiweb", ""),
    Service("healthcheckservice", ""),
    Service("company", ""),
    Service("aiservice", "jeeves-ai"),
    Service("jeevesmcpserver", ""),
    Service("credit", ""),
    Service("merchantdatacleaner", ""),
    Service("rfiservice", ""),
    Service("stablecoinservice", "stablecoin-service"),
    Service("gemini", "gemini"),
    Service("jeeveserpservice", "jeeves-erp-service"),
)
NAMES: Final[tuple[str, ...]] = tuple(s.name for s in SERVICES)
FIELDS_PER_SERVICE: Final = 3

# Branch the form pre-fills in a disabled triple: `main` for these, `development`
# for the rest. The pipeline builds and deploys only enabled services, so a
# disabled triple's branch and mode are never read.
MAIN_BRANCH: Final = frozenset({"simulationserver", "aiweb", "gemini"})


def default_branch(name: str) -> str:
    return "main" if name in MAIN_BRANCH else "development"


def disabled_triple(name: str) -> Triple:
    return Triple(enabled=False, branch=default_branch(name), mode=Mode.LATEST)


def parse(modules: str) -> list[Triple]:
    """Split a MODULES string into one triple per service."""
    fields = modules.strip().rstrip(",").split(",")
    expected = len(SERVICES) * FIELDS_PER_SERVICE
    if len(fields) != expected:
        raise ModulesError(
            f"MODULES holds {len(fields)} fields ({len(fields) / 3:.2f} triples); "
            f"the job reads {expected} ({len(SERVICES)} services x 3). "
            "Rebuild it with --set so every service keeps its position, and re-check "
            "SERVICES against jenkins-library jeevesPlatformInfo."
        )
    return [
        Triple(fields[i] == "true", fields[i + 1], fields[i + 2])
        for i in range(0, expected, FIELDS_PER_SERVICE)
    ]


def render(triples: Sequence[Triple]) -> str:
    """Join triples back into the packed string, with the form's trailing comma."""
    if len(triples) != len(SERVICES):
        raise ModulesError(f"built {len(triples)} triples, need {len(SERVICES)}")
    return ",".join(",".join(t.fields()) for t in triples) + ","


def summarize(triples: Sequence[Triple]) -> str:
    enabled = [
        f"  position {i + 1:>2} {NAMES[i]:<22} branch {t.branch or '(none)'} mode {t.mode}"
        for i, t in enumerate(triples)
        if t.enabled
    ]
    return "\n".join(enabled) if enabled else "  (no service enabled)"


def service_index(name: str) -> int:
    if name not in NAMES:
        raise ModulesError(f"unknown service {name!r} — run --list for the service order")
    return NAMES.index(name)


def parse_set(item: str) -> SetRequest:
    """Parse `SERVICE=BRANCH[:MODE]`, applying the default mode for the branch."""
    name, _, spec = item.partition("=")
    branch, _, mode_text = spec.partition(":")
    if not branch:
        raise ModulesError(f"--set {item!r} needs a branch, as SERVICE=BRANCH[:MODE]")
    service_index(name)
    # The pipeline rebuilds every branch except `development`; `latest` there
    # only adds ecr.resolveLatestTag, which can fail the build.
    mode_text = mode_text or (Mode.LATEST if branch == "development" else Mode.REBUILD)
    try:
        mode = Mode(mode_text)
    except ValueError:
        choices = ", ".join(m.value for m in Mode)
        raise ModulesError(f"mode {mode_text!r} is not one of {choices}") from None
    return SetRequest(name, branch, mode)


def build(requests: Sequence[SetRequest]) -> list[Triple]:
    """All services disabled except those requested, each at its own position."""
    triples = [disabled_triple(name) for name in NAMES]
    for req in requests:
        triples[service_index(req.name)] = Triple(True, req.branch, req.mode)
    return triples


def list_services() -> str:
    lines = [f"{'#':>3}  {'Service':<22} {'Default':<12} Repo"]
    lines.extend(
        f"{i:>3}  {s.name:<22} {default_branch(s.name):<12} {s.repo or '-'}"
        for i, s in enumerate(SERVICES, 1)
    )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument(
        "--set",
        metavar="SERVICE=BRANCH[:MODE]",
        action="append",
        default=[],
        help="enable a service at a branch; repeatable. MODE defaults to latest on "
        "`development` and rebuild on any other branch",
    )
    p.add_argument(
        "--decode",
        metavar="MODULES",
        help="print what a MODULES string resolves to; '-' reads stdin",
    )
    p.add_argument("--list", action="store_true", help="print the positional service order")
    return p


def run(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    if args.list:
        print(list_services())
        return

    if args.decode is not None:
        value = sys.stdin.read() if args.decode == "-" else args.decode
        triples = parse(value)
        print(f"{len(triples)} services, enabled:")
        print(summarize(triples))
        return

    if not args.set:
        parser.error("choose --set, --decode, or --list")

    triples = build([parse_set(item) for item in args.set])
    modules = render(triples)
    LOG.info("%d services, enabled:\n%s", len(triples), summarize(triples))
    print(modules)


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stderr, force=True)
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        run(args, parser)
    except ModulesError as exc:
        LOG.error("%s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

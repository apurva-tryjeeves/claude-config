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
import argparse, sys

# Positional order the job reads MODULES in. Source of truth: jenkins-library
# vars/jeevesPlatformInfo.groovy, the `modules` map filtered to a non-empty
# `giturl` and no `standaloneHelmRelease`. Update this list when that changes.
SERVICES = [
    ("api", "backend"),
    ("frontend", ""),
    ("cms", "cms"),
    ("bankingservice", ""),
    ("pts", ""),
    ("cashbackservice", ""),
    ("lumenengine", "lumen-engine"),
    ("trunarrative", "trunarrative-service"),
    ("creditstatements", ""),
    ("driveservice", ""),
    ("btgintegration", ""),
    ("authenticationservice", "authentication-service"),
    ("loanservice", "loan-service"),
    ("openbanking", "open-banking-service"),
    ("flows", ""),
    ("cardsgateway", ""),
    ("web", "jeeves-web"),
    ("expensemanagement", "expense-management-service"),
    ("productaccount", "product-account-service"),
    ("wallet", "wallet-service"),
    ("billpay", "billpay-service"),
    ("ocr", ""),
    ("cards", "cards-service"),
    ("simulationserver", "jeeves-simulation-server"),
    ("accounting", "accounting-service"),
    ("notification", "notification-service"),
    ("risk", ""),
    ("underwriting", "underwriting-service"),
    ("transactions", "transactions-service"),
    ("pricing", ""),
    ("apdataconnector", "ap-data-source-connector"),
    ("reconciliation", ""),
    ("publicapi", "public-api-service"),
    ("utvservice", ""),
    ("aiweb", ""),
    ("healthcheckservice", ""),
    ("company", ""),
    ("aiservice", "jeeves-ai"),
    ("jeevesmcpserver", ""),
    ("credit", ""),
    ("merchantdatacleaner", ""),
    ("rfiservice", ""),
    ("stablecoinservice", "stablecoin-service"),
    ("gemini", "gemini"),
    ("jeeveserpservice", "jeeves-erp-service"),
]
NAMES = [s for s, _ in SERVICES]
MODES = ("latest", "rebuild")

# Branch the form pre-fills in a disabled triple: `main` for these, `development`
# for the rest. The pipeline builds and deploys only enabled services, so a
# disabled triple's branch and mode are never read.
MAIN_BRANCH = {"simulationserver", "aiweb", "gemini"}


def default_branch(name):
    return "main" if name in MAIN_BRANCH else "development"


def disabled_triple(name):
    return ["false", default_branch(name), "latest"]


def parse(modules):
    """Split a MODULES string into one [enable, branch, mode] triple per service."""
    fields = modules.strip().rstrip(",").split(",")
    expected = len(SERVICES) * 3
    if len(fields) != expected:
        sys.exit(
            f"MODULES holds {len(fields)} fields ({len(fields)/3:.2f} triples); "
            f"the job reads {expected} ({len(SERVICES)} services x 3). "
            "Rebuild it with --set so every service keeps its position, and re-check "
            "SERVICES against jenkins-library jeevesPlatformInfo."
        )
    return [fields[i : i + 3] for i in range(0, expected, 3)]


def render(triples):
    """Join triples back into the packed string, with the form's trailing comma."""
    if len(triples) != len(SERVICES):
        sys.exit(f"built {len(triples)} triples, need {len(SERVICES)}")
    return ",".join(",".join(t) for t in triples) + ","


def summarize(triples):
    enabled = [
        f"  position {i + 1:>2} {NAMES[i]:<22} branch {t[1] or '(none)'} mode {t[2]}"
        for i, t in enumerate(triples)
        if t[0] == "true"
    ]
    return "\n".join(enabled) if enabled else "  (no service enabled)"


def service_index(name):
    if name not in NAMES:
        sys.exit(f"unknown service {name!r} — run --list for the service order")
    return NAMES.index(name)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--set", metavar="SERVICE=BRANCH[:MODE]", action="append", default=[],
                   help="enable a service at a branch; repeatable. MODE defaults to latest on "
                        "`development` and rebuild on any other branch")
    p.add_argument("--decode", metavar="MODULES", help="print what a MODULES string resolves to; '-' reads stdin")
    p.add_argument("--list", action="store_true", help="print the positional service order")
    args = p.parse_args()

    if args.list:
        print(f"{'#':>3}  {'Service':<22} {'Default':<12} Repo")
        for i, (name, repo) in enumerate(SERVICES, 1):
            print(f"{i:>3}  {name:<22} {default_branch(name):<12} {repo or '-'}")
        return

    if args.decode is not None:
        value = sys.stdin.read() if args.decode == "-" else args.decode
        triples = parse(value)
        print(f"{len(triples)} services, enabled:")
        print(summarize(triples))
        return

    if not args.set:
        p.error("choose --set, --decode, or --list")

    triples = [disabled_triple(name) for name in NAMES]
    for item in args.set:
        name, _, spec = item.partition("=")
        branch, _, mode = spec.partition(":")
        if not branch:
            sys.exit(f"--set {item!r} needs a branch, as SERVICE=BRANCH[:MODE]")
        idx = service_index(name)
        # The pipeline rebuilds every branch except `development`; `latest` there
        # only adds ecr.resolveLatestTag, which can fail the build.
        mode = mode or ("latest" if branch == "development" else "rebuild")
        if mode not in MODES:
            sys.exit(f"mode {mode!r} is not one of {', '.join(MODES)}")
        triples[idx] = ["true", branch, mode]

    modules = render(triples)
    print(f"{len(triples)} services, enabled:\n{summarize(triples)}", file=sys.stderr)
    print(modules)


if __name__ == "__main__":
    main()

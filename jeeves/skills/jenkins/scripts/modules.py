#!/usr/bin/env python3
"""Build and decode the packed MODULES parameter for `deploy-DEVELOP-environment`.

MODULES is one comma-separated string holding three fields per service —
`enable,branch,mode` — in a fixed positional order with no names. Build it here
so the field count and every service's position are checked, and read an
existing value back with --decode.

    # one service, everything else off
    python3 scripts/modules.py --only web --branch fix/ACC-1527

    # keep a baseline captured from a prior build on the same environment
    python3 scripts/modules.py --set web=fix/ACC-1527 --baseline "$(cat baseline.txt)"

    # read a string back, or list the service order
    python3 scripts/modules.py --decode "$(cat baseline.txt)"
    python3 scripts/modules.py --list

The built string goes to stdout and a summary to stderr, so
`MODULES=$(python3 scripts/modules.py ...)` captures the value alone.
"""
import argparse, sys

# Positional order the job reads MODULES in. The table in
# references/deploy-develop-environment.md lists the same services — update
# both together when the job's service list changes.
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
]
NAMES = [s for s, _ in SERVICES]
MODES = ("latest", "rebuild")


def parse(modules):
    """Split a MODULES string into one [enable, branch, mode] triple per service."""
    fields = modules.strip().rstrip(",").split(",")
    expected = len(SERVICES) * 3
    if len(fields) != expected:
        sys.exit(
            f"MODULES holds {len(fields)} fields ({len(fields)/3:.2f} triples); "
            f"the job reads {expected} ({len(SERVICES)} services x 3). "
            "Rebuild it with --only/--set so every service keeps its position."
        )
    return [fields[i : i + 3] for i in range(0, expected, 3)]


def render(triples):
    """Join triples back into the packed string, checking the count once more."""
    if len(triples) != len(SERVICES):
        sys.exit(f"built {len(triples)} triples, need {len(SERVICES)}")
    return ",".join(",".join(t) for t in triples)


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
    p.add_argument("--only", metavar="SERVICE", help="enable just this service; every other service off")
    p.add_argument("--set", metavar="SERVICE=BRANCH[:MODE]", action="append", default=[],
                   help="enable a service at a branch, keeping the rest of the baseline; repeatable")
    p.add_argument("--branch", help="branch for --only")
    p.add_argument("--mode", choices=MODES, default="latest", help="build mode (default: latest)")
    p.add_argument("--baseline", metavar="MODULES", help="start from this MODULES string; '-' reads stdin")
    p.add_argument("--decode", metavar="MODULES", help="print what a MODULES string resolves to; '-' reads stdin")
    p.add_argument("--list", action="store_true", help="print the positional service order")
    args = p.parse_args()

    if args.list:
        print(f"{'#':>3}  {'Service':<22} Repo")
        for i, (name, repo) in enumerate(SERVICES, 1):
            print(f"{i:>3}  {name:<22} {repo or '-'}")
        return

    if args.decode is not None:
        value = sys.stdin.read() if args.decode == "-" else args.decode
        triples = parse(value)
        print(f"{len(triples)} services, enabled:")
        print(summarize(triples))
        return

    if args.only:
        if not args.branch:
            sys.exit("--only needs --branch")
        triples = [["false", "", "latest"] for _ in SERVICES]
        triples[service_index(args.only)] = ["true", args.branch, args.mode]
    elif args.set:
        if not args.baseline:
            sys.exit(
                "--set needs --baseline: capture MODULES from a recent build on the same "
                "ENVIRONMENT so every other service keeps its current triple. Use --only "
                "when the environment is running nothing else."
            )
        value = sys.stdin.read() if args.baseline == "-" else args.baseline
        triples = parse(value)
        for item in args.set:
            name, _, spec = item.partition("=")
            branch, _, mode = spec.partition(":")
            if not branch:
                sys.exit(f"--set {item!r} needs a branch, as SERVICE=BRANCH[:MODE]")
            mode = mode or args.mode
            if mode not in MODES:
                sys.exit(f"mode {mode!r} is not one of {', '.join(MODES)}")
            triples[service_index(name)] = ["true", branch, mode]
    else:
        p.error("choose --only, --set, --decode, or --list")

    modules = render(triples)
    print(f"{len(triples)} services, enabled:\n{summarize(triples)}", file=sys.stderr)
    print(modules)


if __name__ == "__main__":
    main()

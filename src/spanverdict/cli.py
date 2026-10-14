"""Local checks, explicit baseline capture and CI exit codes."""

import argparse
from pathlib import Path
import sys

from . import __version__
from .baseline import capture_baseline
from .engine import evaluate
from .html_report import html_report
from .jsonio import InputError, read_json
from .otlp import load_spans
from .policy import fingerprint, load_policy
from .reports import OutputError, atomic_write, json_report, junit_report, protect_destinations


def _bound(maximum):
    def parse(value):
        try:
            number = int(value)
        except ValueError:
            raise argparse.ArgumentTypeError("Expected an integer") from None
        if not 1 <= number <= maximum:
            raise argparse.ArgumentTypeError(f"Expected 1 to {maximum}")
        return number
    return parse


def parser():
    root = argparse.ArgumentParser(prog="spanverdict", description="Check recorded OTLP agent runs against reviewed release contracts.")
    root.add_argument("--version", action="version", version=f"SpanVerdict {__version__}")
    commands = root.add_subparsers(dest="command", required=True)
    lint = commands.add_parser("lint", help="Validate a policy without reading telemetry")
    lint.add_argument("policy")
    for command in ("check", "baseline"):
        sub = commands.add_parser(command, help="Check a candidate" if command == "check" else "Capture a baseline for review")
        sub.add_argument("policy")
        sub.add_argument("traces")
        sub.add_argument("--format", choices=["jsonl", "json"], default="jsonl")
        sub.add_argument("--max-bytes", type=_bound(256 * 1024 * 1024), default=64 * 1024 * 1024)
        sub.add_argument("--max-spans", type=_bound(200_000), default=100_000)
        sub.add_argument("--quiet", action="store_true")
        if command == "baseline":
            sub.add_argument("--output", required=True)
            sub.add_argument("--replace", action="store_true", help="Explicitly replace an existing baseline")
        else:
            sub.add_argument("--baseline")
            sub.add_argument("--json-report")
            sub.add_argument("--junit")
            sub.add_argument("--html-report")
    return root


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        policy = load_policy(args.policy)
        if args.command == "lint":
            print(f"VALID {policy['name']} policy={fingerprint(policy)}")
            return 0
        protected = [args.policy, args.traces]
        if args.command == "baseline":
            paths = [args.output]
        else:
            paths = [p for p in (args.json_report, args.junit, args.html_report) if p]
            if args.baseline:
                protected.append(args.baseline)
        protect_destinations(paths, protected)
        spans = load_spans(args.traces, format=args.format, max_bytes=args.max_bytes, max_spans=args.max_spans)
        if args.command == "baseline":
            result = capture_baseline(policy, spans)
            atomic_write(args.output, json_report(result), protected=protected, overwrite=args.replace)
            if not args.quiet:
                print("BASELINE CAPTURED: review the artifact before approving it in version control")
            return 0
        baseline = read_json(args.baseline,8 * 1024 * 1024) if args.baseline else None
        result = evaluate(policy, spans, baseline=baseline)
        for path, render in ((args.json_report,json_report),(args.junit,junit_report),(args.html_report,html_report)):
            if path:
                atomic_write(path,render(result),protected=protected)
        if not args.quiet:
            for case in result["cases"]:
                failures = len(case["issues"]) + sum(len(run["issues"]) for run in case["runs"])
                print(f"{'FAIL' if failures else 'PASS'} {case['id']}: runs={len(case['runs'])} failed_checks={failures}")
                for issue in case["issues"]:
                    print(f"  {issue['code']}" + (f" / {issue['metric']}" if 'metric' in issue else ''))
                for run in case["runs"]:
                    for issue in run["issues"]:
                        print(f"  {issue['code']}" + (f" / {issue['metric']}" if 'metric' in issue else ''))
            print("ACCEPTED recorded execution" if result["passed"] else "BLOCKED recorded execution")
        return 0 if result["passed"] else 1
    except (InputError, OutputError) as exc:
        print(f"ERROR: {exc}",file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

"""CLI for the GraphLens authorization regression benchmark."""
from __future__ import annotations

import argparse
import sys

from engine.benchmark import IntegrationUnavailable, run_benchmark
from engine.contracts import Verdict
from engine.reporting import generate_report


def _render(report) -> str:
    counts = report.counts
    lines = [
        "GraphLens authorization benchmark",
        f"Units: {len(report.results)}/{report.expected_units}; failed: {len(report.failed_units)}",
        f"PASS: {counts[Verdict.PASS.value]}  POLICY_VIOLATION: {counts[Verdict.POLICY_VIOLATION.value]}  INCONCLUSIVE: {counts[Verdict.INCONCLUSIVE.value]}",
        f"Runtime: {report.runtime_ms:.3f} ms",
        "Per configuration:",
    ]
    for config_id, stats in report.per_configuration().items():
        verdict_counts = stats["counts"]
        lines.append(
            f"  {config_id}: PASS {verdict_counts['PASS']}, "
            f"violation {verdict_counts['POLICY_VIOLATION']}, "
            f"inconclusive {verdict_counts['INCONCLUSIVE']}, failed {stats['failed_units']}"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run GraphLens against the integrated synthetic GraphQL API")
    parser.add_argument("--output", default="results/latest.json", help="path for measured JSON output")
    args = parser.parse_args(argv)
    try:
        report = run_benchmark()
    except IntegrationUnavailable as exc:
        print(f"GraphLens benchmark is not runnable yet: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"GraphLens benchmark setup failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    try:
        output = generate_report(report, args.output)
    except OSError as exc:
        print(f"GraphLens could not write the JSON report to {args.output!r}: {exc}", file=sys.stderr)
        return 2
    print(_render(report))
    print(f"JSON report: {output.resolve()}")
    return 1 if report.failed_units else 0


if __name__ == "__main__":
    raise SystemExit(main())

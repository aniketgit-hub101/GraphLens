"""CLI for the GraphLens authorization regression benchmark."""
from __future__ import annotations

import argparse
import sys

from engine.benchmark import run_benchmark
from engine.contracts import BenchmarkReport
from engine.reporting import generate_report


def _render(report: BenchmarkReport) -> str:
    counts = report.counts
    lines = [
        "GraphLens authorization benchmark",
        f"Units: {len(report.results)}/{report.expected_units}; failed: {len(report.failed_units)}",
        f"PASS: {counts['PASS']}  POLICY_VIOLATION: {counts['POLICY_VIOLATION']}  INCONCLUSIVE: {counts['INCONCLUSIVE']}",
        f"Gate: {report.gate_status}",
        f"Runtime: {report.runtime_ms:.3f} ms",
        "Per configuration:",
    ]
    for config_id, stats in report.per_configuration().items():
        values = stats["counts"]
        lines.append(f"  {config_id}: PASS {values['PASS']}, violation {values['POLICY_VIOLATION']}, inconclusive {values['INCONCLUSIVE']}, failed {stats['failed_units']}")
    if report.gate_findings:
        lines.extend(("Gate findings:", *(f"  - {finding}" for finding in report.gate_findings)))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run GraphLens against the integrated synthetic GraphQL API")
    parser.add_argument("--output", default="results/latest.json", help="path for measured JSON output")
    args = parser.parse_args(argv)
    try:
        report = run_benchmark()
    except Exception as exc:
        # Preserve a machine-readable failed gate even if setup aborts before
        # any unit can execute. No benchmark result rows are fabricated.
        report = BenchmarkReport((), 72, 0.0, "FAILED", (f"benchmark setup failed: {type(exc).__name__}: {exc}",))
        print(report.gate_findings[0], file=sys.stderr)
    try:
        output = generate_report(report, args.output)
    except OSError as exc:
        print(f"GraphLens could not write the JSON report to {args.output!r}: {exc}", file=sys.stderr)
        return 2
    print(_render(report))
    print(f"JSON report: {output.resolve()}")
    return 0 if report.gate_status == "PASSED" and not report.failed_units else 1


if __name__ == "__main__":
    raise SystemExit(main())

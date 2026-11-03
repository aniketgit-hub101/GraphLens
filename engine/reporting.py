"""Serialize measured benchmark reports as JSON."""
from __future__ import annotations

import json
from pathlib import Path

from engine.contracts import BenchmarkReport


def generate_report(report: BenchmarkReport, destination: str | Path) -> Path:
    """Write the actual report object; this function never computes or fabricates results."""
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_dict(), indent=2) + "\n", encoding="utf-8")
    return path

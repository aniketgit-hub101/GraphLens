# GraphLens

GraphLens is a Python harness for regression testing GraphQL authorization against seeded BOLA and BOPLA defects. It executes a fixed synthetic API, evaluates returned data and structured GraphQL errors, and reports measured results. It is a controlled test fixture, not a production vulnerability scanner.

## Backend

- `api/` implements deterministic invoice/customer data, the GraphQL schema, and the engine response adapter.
- `tests/corpus.py` defines T01–T12; `mutants/` defines M1–M4 and C0–C5.
- `engine/integration.py` adapts corpus/configuration objects to engine contracts.
- `policies/` evaluates observed response evidence. Missing evidence and relevant errors remain `INCONCLUSIVE`.
- `engine/benchmark.py` runs each test/configuration pair once and records execution failures separately from verdicts.
- `engine/reporting.py` writes the measured report as JSON.

There are exactly three verdicts: `PASS`, `POLICY_VIOLATION`, and `INCONCLUSIVE`. Expected outcomes describe policy intent; observed GraphQL responses determine verdicts.

## Setup and run

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m compileall -q .
python -m pytest -q
python main.py
```

The CLI runs the complete 72-unit matrix and writes the actual result to `results/latest.json`. Use `python main.py --output path/to/report.json` to select another JSON destination. `results/` contains generated output and is ignored by Git.

## Validation scope

The corpus has 12 unique cases and six configurations: C0 baseline, C1 root BOLA (M1), C2 nested BOLA (M2), C3 BOPLA (M3), C4 authentication bypass (M4), and C5 all four mutants. Counts and runtimes are computed from each execution; no benchmark distribution is predetermined.

The project is backend-only for this milestone. Dashboard and other UI work is deferred.

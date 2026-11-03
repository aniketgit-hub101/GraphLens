# GraphLens project status

Snapshot: 2026-11-03. Release candidate branch: `integration/mvp`. The backend MVP is ready for review before UI development; this work does not modify `main`.

## Completed backend

- Deterministic GraphQL invoice/customer API with structured response data and error paths.
- Canonical adapters for the fixed corpus and configurations, with GraphQL variable forwarding.
- Four independently switchable mutants: root BOLA, nested BOLA, BOPLA, and authentication bypass.
- Evidence-based evaluator with `PASS`, `POLICY_VIOLATION`, and `INCONCLUSIVE`. Missing paths and relevant errors do not become PASS.
- Benchmark runner with exact 72-pair accounting, measured runtimes, and execution failures separate from verdicts.
- Terminal CLI, JSON output, error handling, real API/evaluator integration tests, and updated backend documentation.
- Dashboard, frontend, Flask, and visual components remain outside this backend milestone.

## Final validation

- `python -m compileall -q .`: passed.
- `python -m pytest -q`: 29 passed, 12 subtests passed.
- `python -m pytest api/tests -v`: 12 passed.
- `python main.py`: 72/72 pairs, zero execution failures; 51 PASS, 15 POLICY_VIOLATION, 6 INCONCLUSIVE; measured runtime 62.797 ms.
- Report audit: 12 unique tests, 6 unique configurations, 72 unique pairs; every configuration has 12 rows and counts reconcile to the result rows.
- T04 is explicitly INCONCLUSIVE in all configurations, with its object-level evidence limitation recorded in each result.
- JSON report: `results/latest.json`.
- CLI report-write error path returns nonzero and reports the destination problem.

## Remaining limitations

- The API is a deterministic in-process fixture, not a deployed HTTP service.
- T04 intentionally has no single-object target; the empty collection response cannot establish an object-level decision.

Generated benchmark output under `results/` is ignored by Git. The backend release commit and push target `integration/mvp`; `main` remains untouched.

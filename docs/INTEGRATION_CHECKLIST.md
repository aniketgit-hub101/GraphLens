# GraphLens backend integration checklist

Branch `integration/mvp`; backend-only scope. No UI components are part of this milestone.

## Interface and source checks

- [x] API returns actual `GraphQLResponse` data and structured GraphQL errors.
- [x] API runner accepts query, normalized identity, configuration, and variable mapping.
- [x] Corpus T01–T12 maps to engine cases without changing expected outcomes.
- [x] Configurations C0–C5 map to no mutants, M1, M2, M3, M4, and all four respectively.
- [x] All corpus operations validate against the actual GraphQL schema.
- [x] Missing response paths/properties and relevant errors remain INCONCLUSIVE.
- [x] Evidence output reports observed facts, not requirement labels presented as proof.

## Real API security checks

- [x] Alice reads her invoice under C0 → PASS.
- [x] Bob reads Alice's invoice under C0 → PASS.
- [x] Bob reads Alice's invoice under C1/M1 → POLICY_VIOLATION.
- [x] Nested BOLA is independently exercised by T06 under C2/M2.
- [x] BOPLA is independently exercised by T12 under C3/M3.
- [x] Authentication bypass is independently exercised by T08 under C4/M4.

## Full benchmark acceptance

- [x] Exactly 12 unique tests and 6 unique configurations.
- [x] Exactly 72 unique test/configuration pairs; no omissions or duplicates.
- [x] Execution failures are represented separately from verdict counts.
- [x] Verdict counts and per-configuration totals derive from the actual report rows.
- [x] Runtime is measured with `perf_counter`; no expected distribution is hardcoded.
- [x] JSON output generated at `results/latest.json` and checked for reconciliation.

Measured latest run: 72 rows, 0 execution failures, 51 PASS, 15 POLICY_VIOLATION, 6 INCONCLUSIVE; 62.797 ms wall runtime. T04 accounts for the six INCONCLUSIVE rows.

## Validation

- [x] `python -m compileall -q .`
- [x] `python -m pytest -q` — 29 passed, 12 subtests passed.
- [x] `python main.py` — successful 72-unit run.
- [x] CLI report-write failure path returns nonzero and reports the destination error.

`results/latest.json` is generated output and is ignored by Git. See `docs/INTEGRATION_CONTRACT.md` and `docs/architecture.md` for the current boundary and design.

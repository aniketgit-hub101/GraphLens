# GraphLens project status

Snapshot: 2026-11-03. Security corrections are under local validation on `fix/security-audit`, based on the preserved `integration/mvp` release commit `ef2758c535bcf63f6fa8cb883496d82dec7558f5`. No merge or push is part of this work.

## Backend corrections

- Canonical strict configuration and identity validation rejects unknown names, duplicate mutants, malformed inputs, and unsupported identities.
- M1, M2, M3, and M4 are isolated to root BOLA, nested BOLA, property exposure, and anonymous authentication bypass respectively.
- T10 uses a shared invoice so Bob's parent access is independently evidenced from `internalNotes`; T12 continues to deny `confidentialCode` to its owner unless M3 is enabled.
- The evaluator uses actual response evidence. Missing parent/property evidence and relevant GraphQL errors remain `INCONCLUSIVE`; T04 evaluates real collection evidence.
- The behavioral benchmark gate checks declared mutant kills, unexpected vulnerability cells, cross-mutant contamination, resolver bindings, strict invalid-input rejection, execution failures, and exact pair accounting.
- CLI setup and gate failures produce a JSON report with `gate.status = FAILED` and nonzero exit status. No UI components are included.

## Latest measured validation

- `python main.py`: 72/72 unique test/configuration units, zero execution failures, gate PASSED; 54 PASS, 14 POLICY_VIOLATION, 4 INCONCLUSIVE; measured runtime 54.312 ms.
- Matrix audit: 12 unique tests × 6 unique configurations; all 72 pairs occur once. T04 is INCONCLUSIVE for C0–C3 with empty collection evidence and POLICY_VIOLATION for C4–C5 with returned protected invoice IDs.
- Representative observed violations include T02/C1 and T06/C2 unauthorized objects, T10/C3 and T12/C3 non-null restricted properties, and T04/C4 anonymous collection disclosure.
- Focused suites last run: `python -m pytest api/tests -v` — 26 passed; `python -m pytest engine -v` — 22 passed; `python -m pytest tests/test_definitions.py -q` — 4 passed, 12 subtests passed.
- `python -m compileall -q .`: passed. `python -m pytest -q`: 58 passed, 12 subtests passed.

## Limitations

The API is a deterministic in-process GraphQL fixture rather than a deployed HTTP service. T04 detects a non-empty returned protected collection; an empty collection cannot prove per-object authorization and remains inconclusive.

Generated benchmark output under `results/` is ignored by Git. Nothing has been committed, merged, or pushed.

# GraphLens project status

Security audit commit `5188685260ff697df29e324a411585e48093af17` was published on `fix/security-audit`; PR base is `integration/mvp`. This document preserves validation reported before the current cleanup revision. Those results are historical and are not validation of this cleanup revision.

## Historical validation (before this cleanup revision)

- `python -m compileall -q .`: passed.
- `python -m pytest -q`: 72 passed, 24 subtests passed.
- `python -m pytest api/tests -v`: 27 passed, 12 subtests passed.
- `python -m pytest engine -v`: 35 passed.
- `python main.py`: 72/72 test/configuration pairs, gate PASSED.
- Historical verdict counts: 54 PASS, 14 POLICY_VIOLATION, 4 INCONCLUSIVE.

## Backend and limitations

The backend has strict canonical identity validation, isolated M1–M4 behavior, an evidence-based evaluator, a response-backed benchmark kill gate, exact 72-pair accounting, resolver-binding checks, and CLI failure-report behavior. T04 remains INCONCLUSIVE for empty collections in C0–C3 and is a violation in C4–C5 only when protected invoice IDs are actually returned.

The API is an in-process synthetic GraphQL fixture, not a deployed HTTP service.

## Cleanup revision validation

- `python -m compileall -q .`: passed.
- `python -m pytest -q`: 70 passed, 24 subtests passed after removing the two duplicate tests.
- `python -m pytest api/tests -v`: 27 passed, 12 subtests passed.
- `python -m pytest engine -v`: 33 passed.
- `python main.py`: 72/72 pairs, gate PASSED; 54 PASS, 14 POLICY_VIOLATION, 4 INCONCLUSIVE.
- `git diff --check`: passed.

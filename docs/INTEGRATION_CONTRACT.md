# GraphLens integration contract

This document records the implemented integration boundary. The security corrections are being validated on `fix/security-audit` from the immutable `integration/mvp` release checkpoint.

## Engine contracts

- `GraphQLResponse(data: Mapping[str, object] | None, errors: tuple[GraphQLErrorInfo, ...], http_status: int | None)` carries actual API output. Each error has `message`, optional `path`, and `locations`.
- Engine `TestCase` fields: `test_id`, `description`, exact lowercase `identity` (only `alice`, `bob`, or `anonymous`; no case or whitespace normalization). The legacy API wrapper alone maps historical title-case names to lowercase., GraphQL `operation`, variables mapping, optional structured `Target`, `expected_outcome`, `evidence_requirements`, and optional `inconclusive_reason`.
- Engine `Target` fields: response path, object ID, optional property name/path, optional owner evidence path/expected owner ID, `is_collection`, `requires_authentication`, and `object_id_field`. Collection targets retain evidence paths even when the expected intent is inconclusive.
- Engine `Configuration` fields: `configuration_id`, `name`, and `enabled_mutants: frozenset[str]`.

## Source package shapes and adapters

`engine.integration` adapts source corpus test cases to the engine fields without changing expected outcomes. It derives target paths from corpus target metadata, maps property-category denial to `deny_property`, other denial to `deny_object`, and preserves T04's rationale as its inconclusive reason and adapts its `invoices` field into a collection target. Corpus variables are converted to a mapping and passed unchanged to the API runner.

The mutant package returns six immutable configurations:

| Configuration | Enabled mutants |
| --- | --- |
| C0 | none |
| C1 | M1 root BOLA |
| C2 | M2 nested BOLA |
| C3 | M3 BOPLA |
| C4 | M4 authentication bypass |
| C5 | M1, M2, M3, M4 |

`api.runner.execute_graphql(query, identity, config, variables=None)` forwards `variables` to graphql-core and maps M1–M4 to API mutant switches. API errors remain structured and are not translated to PASS.

## Verdict and evidence rules

Expected outcomes state policy intent; observed responses determine verdicts. Returned unauthorized objects or non-null restricted properties are `POLICY_VIOLATION`. A denial is `PASS` only when the relevant response path/property was selected and absent or null without a relevant GraphQL error. Missing paths, absent evidence, identity mismatch, and relevant errors are `INCONCLUSIVE`. T04 is evidence-driven: empty/null/malformed collections are inconclusive, while a non-empty protected collection actually returned to anonymous is a violation, even though its corpus intent is inconclusive. Evaluator evidence describes observations, not unverified requirement labels.

## Test and benchmark scope

The corpus is T01–T12 and the configuration matrix is C0–C5. The benchmark produces each pair exactly once (72 units), derives verdict counts from actual API/evaluator output, records execution failures separately, and measures elapsed runtime. The gate uses `tests.corpus.MUTANT_KILL_MAP` to require each configured mutant kill, flags unexpected violations, checks resolver bindings and invalid-input rejection, and writes a failed-gate report on setup or acceptance failure. `python main.py` runs this measured benchmark and writes JSON under `results/` by default.

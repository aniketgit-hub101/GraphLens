# GraphLens integration contract

This document records the implemented backend integration boundary on `integration/mvp`.

## Engine contracts

- `GraphQLResponse(data: Mapping[str, object] | None, errors: tuple[GraphQLErrorInfo, ...], http_status: int | None)` carries actual API output. Each error has `message`, optional `path`, and `locations`.
- Engine `TestCase` fields: `test_id`, `description`, lowercase `identity`, GraphQL `operation`, variables mapping, optional structured `Target`, `expected_outcome`, `evidence_requirements`, and optional `inconclusive_reason`.
- Engine `Target` fields: response path, object ID (optional only for explicitly inconclusive cases), optional property name/path, and optional owner evidence path/expected owner ID.
- Engine `Configuration` fields: `configuration_id`, `name`, and `enabled_mutants: frozenset[str]`.

## Source package shapes and adapters

`engine.integration` adapts source corpus test cases to the engine fields without changing expected outcomes. It derives target paths from corpus target metadata, maps property-category denial to `deny_property`, other denial to `deny_object`, and preserves T04's rationale as its inconclusive reason. Corpus variables are converted to a mapping and passed unchanged to the API runner.

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

Expected outcomes state policy intent; observed responses determine verdicts. Returned unauthorized objects or non-null restricted properties are `POLICY_VIOLATION`. A denial is `PASS` only when the relevant response path/property was selected and absent or null without a relevant GraphQL error. Missing paths, absent evidence, identity mismatch, and relevant errors are `INCONCLUSIVE`. Evaluator evidence describes observations, not unverified requirement labels.

## Test and benchmark scope

The corpus is T01–T12 and the configuration matrix is C0–C5. The benchmark produces each pair exactly once (72 units), derives verdict counts from actual API/evaluator output, records execution failures separately, and measures elapsed runtime. `python main.py` runs this measured benchmark and writes JSON under `results/` by default.

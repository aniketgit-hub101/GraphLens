# GraphLens architecture (working draft)

Status: **engine implementation draft; shared interfaces still require approval from Adeel (API) and Abhay (security tests).** This document is not approval on their behalf. Code in `engine/` and `policies/` uses the proposed types from `engine/contracts.py` while preserving adapter boundaries so their modules can be integrated without editing their owned files.

## Boundaries and owners

- `api/` (Adeel) supplies `execute_graphql(query, identity, config) -> GraphQLResponse`. It executes the actual schema/resolvers and returns real `data` and GraphQL errors. It must not return a verdict.
- `tests/` (Abhay) supplies `get_test_corpus() -> tuple[TestCase, ...]`. Cases specify target response path/object ID/property, expected policy outcome, evidence requirements, and explicit inconclusive reason where applicable.
- `mutants/` (Abhay/API coordination) supplies `get_configurations() -> tuple[Configuration, ...]` for C0–C5. Enabled mutants alter API behavior; the evaluator never uses mutant flags to decide verdicts.
- `policies/evaluator.py` evaluates observed response data against the case's expected outcome and target.
- `engine/benchmark.py` validates T01–T12 and C0–C5, executes each pair once, records runtime/evidence/errors, and records failures separately from verdicts.
- `engine/reporting.py` implements `generate_report(report, destination) -> Path`; it serializes only a completed `BenchmarkReport`.
- `main.py` wires integrations, prints measured counts, and writes JSON only after an actual run.

## Proposed shared schemas

Canonical provisional value objects are in `engine/contracts.py`:

- `Identity`: literal values `alice`, `bob`, `anonymous`.
- `Configuration`: `configuration_id`, `name`, `enabled_mutants`.
- `Target`: `response_path` (GraphQL response keys, including aliases), required `object_id`, optional `property_name`, and optional `property_path` relative to the object.
- `GraphQLResponse`: `data`, `errors` with message/path, optional HTTP status. Status code never determines a verdict.
- `TestCase`: `test_id`, `description`, `identity`, `operation`, `target`, `expected_outcome`, `evidence_requirements`, optional `inconclusive_reason`.
- `Evaluation`: one of exactly `PASS`, `POLICY_VIOLATION`, `INCONCLUSIVE`, plus evidence, expected outcome, and actual observation.
- `BenchmarkResult`: one test/configuration pair, identity, expected outcome, observation, optional verdict (absent only for failed units), evidence, runtime, GraphQL errors, and execution error.

The proposed import locations are `api.runner.execute_graphql`, `tests.corpus.get_test_corpus`, and `mutants.configurations.get_configurations`. These names and the `Target` shape need explicit owner approval before they are treated as final. Owners can request changes before implementation lands on their branches.

## Policy evaluation rules

`policies/rules.json` documents the three supported expected outcomes. `evaluate_policy(identity, operation, response)` examines the object/property at the target response path:

- `allow`: PASS only when the requested target and any expected property are evidenced. Missing evidence is INCONCLUSIVE.
- `deny_object`: POLICY_VIOLATION if the targeted object is returned; PASS for absent/null data only when no relevant GraphQL error undermines classification.
- `deny_property`: POLICY_VIOLATION if a selected restricted property has a non-null returned value; PASS when selected and null without a relevant error. Missing selection/evidence is INCONCLUSIVE.

Partial data can still prove exposure. Relevant field errors, pathless errors, or missing data prevent a denial from being mistaken for a clean policy result. HTTP 200 is ignored by the classifier.

## Benchmark accounting

Default execution requires exactly 12 cases and six configurations, and rejects duplicate or missing IDs. It records one result for every pair in config-major order. Executor/evaluator exceptions become failed units with no verdict; they do not count as PASS, POLICY_VIOLATION, or INCONCLUSIVE. Counts and per-configuration statistics derive only from result objects.

## Current integration limitation

The checked out remote feature branches contain no API, corpus, or mutant implementation. Consequently `python main.py` will clearly report missing integrations until those packages expose the proposed functions. The engine does not fabricate fixture responses, corpus cases, configurations, or benchmark counts.

# GraphLens backend architecture

## Execution flow

```text
T01–T12 corpus ─┐
                ├─> engine.integration adapters ─> benchmark runner ─> JSON report
C0–C5 configs ──┘                                     │
                                                     v
                                   real GraphQL API -> policy evaluator
```

### API

`api.runner.execute_graphql(query, identity, config, variables=None)` passes the provided variables to graphql-core and returns `engine.contracts.GraphQLResponse`. The response carries actual data and structured `GraphQLErrorInfo(message, path, locations)` values. Configurations enable API behavior only; the evaluator never reads mutant flags.

### Corpus and configurations

The source corpus has 12 stable IDs and uses `operation`, tuple-pair variables, a structured corpus `Target`, lowercase identity strings, and `allow` / `deny` / `inconclusive` intent. The configuration source exposes C0–C5 with immutable mutant sets. `engine.integration` converts these values into canonical engine `TestCase`, `Target`, and `Configuration` objects. T04 remains explicitly inconclusive and needs no single-object target.

T05–T08 query the customer resolver directly. Its authorization is tied to linked invoice ownership, so M2 can be exercised independently of the root invoice resolver.

### Policy evaluator

The evaluator classifies observations, not declared outcomes alone:

- An allowed target must be present; configured owner evidence must also match.
- A returned denied object or non-null restricted property is a policy violation.
- An explicitly selected null/withheld target can establish denial only without a relevant GraphQL error.
- Missing response paths, missing property selections, mismatched target identity, and relevant execution errors are inconclusive.

Evidence output contains observed facts and errors, not unverified requirement labels. `policies/rules.json` documents these semantics; the Python evaluator implements them.

### Benchmark and reporting

The runner validates the exact T01–T12 and C0–C5 sets, executes 72 unique pairs, and measures elapsed time with `perf_counter`. Executor/evaluator exceptions create result rows with `verdict=None` and `execution_error`, separate from verdict counts. The report checks pair uniqueness and derives all counts from result rows. `main.py` runs the benchmark, prints a summary, writes JSON, and returns a nonzero status for failed units or setup/report errors.

## Backend boundary

No dashboard, frontend, Flask app, or visual component is part of this backend milestone.

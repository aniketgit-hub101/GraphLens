# GraphLens backend architecture

## Execution flow

The T01–T12 corpus and C0–C5 immutable configurations are adapted to canonical engine contracts. The benchmark executes each of the 72 pairs against the real GraphQL schema, then sends the actual structured response and errors to the policy evaluator. Every unit records its verdict, the actual response data used as structured evidence, GraphQL errors, runtime, and any execution failure. The kill gate checks returned IDs and property values against corpus targets and fixture authorization relationships.

## Identity contract

Canonical API and engine identities are exact lowercase values: `alice`, `bob`, and `anonymous`. Whitespace, casing variants, empty strings, non-strings, and unknown names are rejected. The legacy compatibility wrapper alone case-folds historical title-case identifiers.

## Authorization boundaries

- M1 bypasses ownership only at the root `invoice(id)` resolver.
- M2 bypasses authorization only for nested customer resolution.
- M3 exposes restricted properties only.
- M4 permits anonymous access through authentication checks. It does not alter authenticated Bob's object or property access.
- Bob is an explicit viewer of Alice's shared invoice `invoice-alice-002`; its parent is readable while owner-only `internalNotes` remains withheld unless M3 is enabled.

## Evidence and outcomes

The evaluator uses returned data, selected paths, object identifiers, and structured GraphQL error paths. It does not infer observed verdicts from expected outcomes. An explicit null object can evidence object denial only when no relevant GraphQL error exists. Property denial requires the parent object and selected property to be present; a null selected property without relevant errors is PASS, while a missing parent or property is INCONCLUSIVE. T04 checks the real `invoices` collection: empty, null, or malformed evidence is INCONCLUSIVE; a non-empty protected collection returned to an anonymous identity is a violation.

## Benchmark gate and reports

`tests.corpus.MUTANT_KILL_MAP` declares the behavioral cases each seeded mutant must violate. For each configuration the gate intersects that map with enabled mutants, checks every declared kill, flags unexpected violations as possible cross-mutant contamination, checks all 72 unique pairs, detects execution failures and unbound authorization resolvers, and verifies strict rejection of invalid identity/configuration inputs. Counts come from actual result rows. Setup and gate failures are serialized with `gate.status = FAILED`; the CLI exits nonzero. Runtime is measured with `perf_counter`.

No dashboard, frontend, Flask interface, or visual components are part of this backend.

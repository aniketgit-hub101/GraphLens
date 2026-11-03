"""Execute the fixed GraphLens corpus and enforce behavioral mutant kills."""
from __future__ import annotations

from importlib import import_module
from time import perf_counter
from typing import Any, Callable, Iterable

from engine.contracts import BenchmarkReport, BenchmarkResult, Configuration, Evaluation, GraphQLResponse, TestCaseLike, Verdict

_EXPECTED_TEST_IDS = tuple(f"T{number:02d}" for number in range(1, 13))
_EXPECTED_MUTANTS = {
    "C0": frozenset(), "C1": frozenset({"M1"}), "C2": frozenset({"M2"}),
    "C3": frozenset({"M3"}), "C4": frozenset({"M4"}),
    "C5": frozenset({"M1", "M2", "M3", "M4"}),
}


class IntegrationUnavailable(RuntimeError):
    """Raised when a required integrated package is unavailable."""


def _load_integrations():
    specifications = (("api.runner", "execute_graphql"), ("tests.corpus", "get_test_corpus"), ("mutants.configurations", "get_configurations"))
    loaded: dict[str, Any] = {}
    missing: list[str] = []
    for module_name, function_name in specifications:
        try:
            module = import_module(module_name)
            loaded[function_name] = getattr(module, function_name)
        except (ImportError, AttributeError) as exc:
            missing.append(f"{module_name}.{function_name} ({exc})")
    if missing:
        raise IntegrationUnavailable("Required integrations are missing: " + "; ".join(missing))
    from engine.integration import adapt_configurations, adapt_corpus
    from policies.evaluator import evaluate_policy
    return adapt_corpus(loaded["get_test_corpus"]()), adapt_configurations(loaded["get_configurations"]()), loaded["execute_graphql"], evaluate_policy


def _validate(corpus: Iterable[TestCaseLike], configurations: Iterable[Configuration]) -> tuple[tuple[TestCaseLike, ...], tuple[Configuration, ...]]:
    cases, configs = tuple(corpus), tuple(configurations)
    test_ids = tuple(case.test_id for case in cases)
    config_ids = tuple(config.configuration_id for config in configs)
    if len(test_ids) != len(set(test_ids)):
        raise ValueError("Test corpus contains duplicate test_id values")
    if len(config_ids) != len(set(config_ids)):
        raise ValueError("Configuration list contains duplicate configuration_id values")
    if set(test_ids) != set(_EXPECTED_TEST_IDS) or len(test_ids) != 12:
        raise ValueError("Benchmark corpus must contain T01–T12 exactly once")
    if set(config_ids) != set(_EXPECTED_MUTANTS) or len(config_ids) != 6:
        raise ValueError("Benchmark configurations must contain C0–C5 exactly once")
    for case in cases:
        if case.identity not in ("alice", "bob", "anonymous"):
            raise ValueError(f"{case.test_id} has unsupported identity {case.identity!r}")
        if case.expected_outcome not in ("allow", "deny_object", "deny_property", "inconclusive"):
            raise ValueError(f"{case.test_id} has unsupported expected_outcome {case.expected_outcome!r}")
        if not isinstance(case.operation, str) or not case.operation.strip():
            raise ValueError(f"{case.test_id} operation must be a non-empty GraphQL document")
        if not hasattr(case.variables, "items"):
            raise ValueError(f"{case.test_id} variables must be a mapping")
        if case.expected_outcome != "inconclusive":
            if case.target is None or not case.target.response_path or case.target.object_id is None:
                raise ValueError(f"{case.test_id} target requires response_path and object_id")
            if case.expected_outcome == "deny_property" and not (case.target.property_name or case.target.property_path):
                raise ValueError(f"{case.test_id} deny_property target requires a property path")
    for config in configs:
        if frozenset(config.enabled_mutants) != _EXPECTED_MUTANTS[config.configuration_id]:
            raise ValueError(f"{config.configuration_id} has incorrect enabled_mutants mapping")
    return cases, configs


def audit_resolver_bindings(schema: Any = None) -> tuple[str, ...]:
    """Report missing authorization resolvers on fields required by the corpus."""
    if schema is None:
        schema = import_module("api.schema")._SCHEMA
    from graphql.execution.execute import default_field_resolver
    required = {
        "Query": ("invoice", "invoices", "customer"),
        "Invoice": ("customer", "internalNotes", "confidentialCode"),
    }
    findings: list[str] = []
    for type_name, field_names in required.items():
        graph_type = schema.get_type(type_name)
        if graph_type is None:
            findings.append(f"required GraphQL type {type_name} is missing")
            continue
        for field_name in field_names:
            field = graph_type.fields.get(field_name)
            if field is None:
                findings.append(f"required resolver field {type_name}.{field_name} is missing")
            elif field.resolve is None or field.resolve is default_field_resolver:
                findings.append(f"authorization resolver is unbound for {type_name}.{field_name}")
    return tuple(findings)


def _invalid_input_findings() -> tuple[str, ...]:
    from api.schema import normalize_identity
    from mutants.configurations import normalize_configuration
    findings: list[str] = []
    invalid_inputs = (
        ("unknown identity", lambda: normalize_identity("mallory")),
        ("unknown config", lambda: normalize_configuration({"configuration_id": "C9", "enabled_mutants": []})),
        ("unknown mutant", lambda: normalize_configuration({"configuration_id": "C0", "enabled_mutants": ["M9"]})),
        ("duplicate mutants", lambda: normalize_configuration({"configuration_id": "C1", "enabled_mutants": ["M1", "M1"]})),
        ("mismatched mutants", lambda: normalize_configuration({"configuration_id": "C0", "enabled_mutants": ["M1"]})),
    )
    for label, call in invalid_inputs:
        try:
            call()
        except (TypeError, ValueError):
            continue
        findings.append(f"invalid input was accepted: {label}")
    return tuple(findings)


def _declared_outcome_verdict(outcome: str) -> Verdict:
    return Verdict.INCONCLUSIVE if outcome == "inconclusive" else Verdict.PASS


def _gate_findings(cases: tuple[TestCaseLike, ...], configs: tuple[Configuration, ...], results: tuple[BenchmarkResult, ...], resolver_findings: tuple[str, ...] | None = None, validation_findings: tuple[str, ...] | None = None) -> tuple[str, ...]:
    from tests.corpus import MUTANT_KILL_MAP
    findings = list(resolver_findings if resolver_findings is not None else audit_resolver_bindings())
    findings.extend(validation_findings if validation_findings is not None else _invalid_input_findings())
    expected_pairs = {(config.configuration_id, case.test_id) for config in configs for case in cases}
    actual_pairs = [(result.configuration_id, result.test_id) for result in results]
    if len(actual_pairs) != len(expected_pairs):
        findings.append(f"benchmark has {len(actual_pairs)} rows; expected {len(expected_pairs)} unique pairs")
    if len(actual_pairs) != len(set(actual_pairs)):
        findings.append("benchmark contains duplicate test/configuration pairs")
    missing = expected_pairs - set(actual_pairs)
    extra = set(actual_pairs) - expected_pairs
    if missing:
        findings.append(f"benchmark is missing pairs: {sorted(missing)}")
    if extra:
        findings.append(f"benchmark contains unexpected pairs: {sorted(extra)}")
    cases_by_id = {case.test_id: case for case in cases}
    configs_by_id = {config.configuration_id: config for config in configs}
    for row in results:
        if row.execution_error or row.verdict is None:
            findings.append(f"{row.configuration_id}/{row.test_id} execution failed: {row.execution_error or 'no verdict'}")
            continue
        case, config = cases_by_id.get(row.test_id), configs_by_id.get(row.configuration_id)
        if case is None or config is None:
            continue
        should_kill = any(row.test_id in MUTANT_KILL_MAP.get(mutant, frozenset()) for mutant in config.enabled_mutants)
        expected_verdict = Verdict.POLICY_VIOLATION if should_kill else _declared_outcome_verdict(case.expected_outcome)
        if should_kill:
            evidence_error = _kill_evidence_error(case, row)
            if evidence_error:
                findings.append(f"{row.configuration_id}/{row.test_id}: {evidence_error}")
        if row.verdict != expected_verdict:
            if should_kill:
                findings.append(f"{row.configuration_id}/{row.test_id}: declared mutant kill was not observed (got {row.verdict.value})")
            elif row.verdict == Verdict.POLICY_VIOLATION:
                findings.append(f"{row.configuration_id}/{row.test_id}: unexpected vulnerability verdict; possible cross-mutant contamination")
            else:
                findings.append(f"{row.configuration_id}/{row.test_id}: expected {expected_verdict.value} from corpus intent, got {row.verdict.value}")
    return tuple(findings)



def _value_at_path(value: Any, path: tuple[str | int, ...]) -> tuple[bool, Any]:
    current = value
    for part in path:
        if isinstance(current, dict) and isinstance(part, str) and part in current:
            current = current[part]
        elif isinstance(current, (list, tuple)) and isinstance(part, int) and 0 <= part < len(current):
            current = current[part]
        else:
            return False, None
    return True, current


def _kill_evidence_error(case: TestCaseLike, row: BenchmarkResult) -> str | None:
    """Require kill evidence from retained GraphQL data, independent of prose."""
    target = case.target
    data = row.response_data
    if target is None or data is None:
        return "kill lacks retained response data or a declared target"
    if target.is_collection:
        present, values = _value_at_path(data, tuple(target.response_path))
        if not present:
            return "collection kill lacks a non-empty response collection: response path is missing"
        if values is None:
            return "collection kill lacks a non-empty response collection: response is null"
        if not isinstance(values, list):
            return "collection kill response is malformed: expected a list; lacks a non-empty response collection"
        if not values:
            return "collection kill lacks a non-empty response collection"
        from api.data import INVOICES
        protected_ids = set(INVOICES)
        returned_ids = []
        for value in values:
            if not isinstance(value, dict) or value.get(target.object_id_field) is None:
                return "collection kill contains malformed object evidence"
            returned_ids.append(value[target.object_id_field])
        if case.identity != "anonymous" or not target.requires_authentication:
            return "collection target does not declare anonymous authentication protection"
        if not any(object_id in protected_ids for object_id in returned_ids):
            return "collection kill does not contain protected target IDs"
        return None

    present, obj = _value_at_path(data, tuple(target.response_path))
    if not present or not isinstance(obj, dict):
        return "kill target object is absent at the declared response path"
    if obj.get(target.object_id_field) != target.object_id:
        return "kill response object ID does not match the declared target"
    from api.data import CUSTOMERS, INVOICES
    identity_ids = {"alice": "user-alice", "bob": "user-bob"}
    if case.expected_outcome == "deny_object":
        if case.identity == "anonymous":
            return None
        if str(target.response_path[0]) == "invoice":
            protected = INVOICES.get(str(target.object_id))
            authorized = protected is not None and (protected["owner_id"] == identity_ids.get(case.identity) or identity_ids.get(case.identity) in protected["viewer_ids"])
        elif str(target.response_path[0]) == "customer":
            protected_customer = CUSTOMERS.get(str(target.object_id))
            linked = [invoice for invoice in INVOICES.values() if protected_customer and invoice["customer_id"] == protected_customer["id"]]
            authorized = any(invoice["owner_id"] == identity_ids.get(case.identity) or identity_ids.get(case.identity) in invoice["viewer_ids"] for invoice in linked)
        else:
            return "object kill has no applicable object authorization policy"
        return "kill object is not unauthorized under the fixture policy" if authorized else None
    if case.expected_outcome == "deny_property":
        resource = INVOICES.get(str(target.object_id))
        if resource is None or identity_ids.get(case.identity) is None or (resource["owner_id"] != identity_ids[case.identity] and identity_ids[case.identity] not in resource["viewer_ids"]):
            return "property kill parent is not accessible to the declared identity"
        property_path = tuple(target.property_path or ((target.property_name,) if target.property_name else ()))
        has_property, value = _value_at_path(obj, property_path)
        if not property_path or not has_property or value is None:
            return "property kill lacks the selected non-null restricted property"
        property_name = str(property_path[-1])
        property_authorized = property_name != "confidentialCode" and resource["owner_id"] == identity_ids[case.identity]
        if property_authorized:
            return "property kill identity is authorized for the restricted property"
        return None

    return "kill target does not declare an object or property denial policy"

def run_benchmark(*, corpus: Iterable[TestCaseLike] | None = None, configurations: Iterable[Configuration] | None = None, execute_graphql: Callable[[str, str, Configuration, dict[str, object]], GraphQLResponse] | None = None, policy_evaluator: Callable[[str, TestCaseLike, GraphQLResponse], Evaluation] | None = None) -> BenchmarkReport:
    """Run all 72 real API/corpus pairs; failures and behavioral gate results are retained."""
    if corpus is None or configurations is None or execute_graphql is None:
        loaded_corpus, loaded_configurations, loaded_executor, loaded_evaluator = _load_integrations()
        corpus = corpus if corpus is not None else loaded_corpus
        configurations = configurations if configurations is not None else loaded_configurations
        execute_graphql = execute_graphql or loaded_executor
        policy_evaluator = policy_evaluator or loaded_evaluator
    if policy_evaluator is None:
        policy_evaluator = import_module("policies.evaluator").evaluate_policy
    cases, configs = _validate(corpus, configurations)
    started = perf_counter()
    results: list[BenchmarkResult] = []
    for config in configs:
        for case in cases:
            unit_started = perf_counter()
            response: GraphQLResponse | None = None
            try:
                response = execute_graphql(case.operation, case.identity, config, dict(case.variables))
                if not isinstance(response, GraphQLResponse):
                    raise TypeError("execute_graphql must return engine.contracts.GraphQLResponse")
                evaluation = policy_evaluator(case.identity, case, response)
                if not isinstance(evaluation, Evaluation):
                    raise TypeError("policy_evaluator must return engine.contracts.Evaluation")
                results.append(BenchmarkResult(case.test_id, config.configuration_id, case.identity, case.expected_outcome, evaluation.actual_observation, evaluation.verdict, evaluation.evidence, round((perf_counter()-unit_started)*1000, 3), tuple(response.errors), response_data=response.data))
            except Exception as exc:
                errors = tuple(getattr(response, "errors", ())) if response is not None else ()
                results.append(BenchmarkResult(case.test_id, config.configuration_id, case.identity, case.expected_outcome, "unit execution or evaluation failed", None, (f"{type(exc).__name__}: {exc}",), round((perf_counter()-unit_started)*1000, 3), errors, f"{type(exc).__name__}: {exc}"))
    expected_units = len(cases) * len(configs)
    rows = tuple(results)
    try:
        findings = _gate_findings(cases, configs, rows)
    except Exception as exc:
        findings = (f"benchmark gate evaluation failed: {type(exc).__name__}: {exc}",)
    elapsed_ms = round((perf_counter()-started)*1000, 3)
    return BenchmarkReport(rows, expected_units, elapsed_ms, "PASSED" if not findings else "FAILED", findings)

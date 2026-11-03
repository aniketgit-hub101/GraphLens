"""Execute the fixed corpus against the provided API/configuration implementations."""
from __future__ import annotations

from importlib import import_module
from time import perf_counter
from typing import Any, Callable, Iterable

from engine.contracts import (
    BenchmarkReport,
    BenchmarkResult,
    Configuration,
    Evaluation,
    GraphQLResponse,
    TestCaseLike,
)

_EXPECTED_TEST_IDS = tuple(f"T{number:02d}" for number in range(1, 13))
_EXPECTED_MUTANTS = {
    "C0": frozenset(),
    "C1": frozenset({"M1"}),
    "C2": frozenset({"M2"}),
    "C3": frozenset({"M3"}),
    "C4": frozenset({"M4"}),
    "C5": frozenset({"M1", "M2", "M3", "M4"}),
}


class IntegrationUnavailable(RuntimeError):
    """Raised when a teammate-owned package has not exposed the agreed API yet."""


def _load_integrations():
    specifications = (
        ("api.runner", "execute_graphql"),
        ("tests.corpus", "get_test_corpus"),
        ("mutants.configurations", "get_configurations"),
    )
    loaded: dict[str, Any] = {}
    missing: list[str] = []
    for module_name, function_name in specifications:
        try:
            module = import_module(module_name)
            loaded[function_name] = getattr(module, function_name)
        except (ImportError, AttributeError) as exc:
            missing.append(f"{module_name}.{function_name} ({exc})")
    if missing:
        raise IntegrationUnavailable("Required teammate integrations are missing: " + "; ".join(missing))
    from policies.evaluator import evaluate_policy
    return loaded["get_test_corpus"](), loaded["get_configurations"](), loaded["execute_graphql"], evaluate_policy


def _validate(corpus: Iterable[TestCaseLike], configurations: Iterable[Configuration]) -> tuple[tuple[TestCaseLike, ...], tuple[Configuration, ...]]:
    cases = tuple(corpus)
    configs = tuple(configurations)
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
        if case.expected_outcome not in ("allow", "deny_object", "deny_property"):
            raise ValueError(f"{case.test_id} has unsupported expected_outcome {case.expected_outcome!r}")
        if not case.target.response_path or case.target.object_id is None:
            raise ValueError(f"{case.test_id} target requires response_path and object_id")
        if case.expected_outcome == "deny_property" and not (case.target.property_name or case.target.property_path):
            raise ValueError(f"{case.test_id} deny_property target requires a property path")
    for config in configs:
        if frozenset(config.enabled_mutants) != _EXPECTED_MUTANTS[config.configuration_id]:
            raise ValueError(f"{config.configuration_id} has incorrect enabled_mutants mapping")
    return cases, configs


def run_benchmark(
    *,
    corpus: Iterable[TestCaseLike] | None = None,
    configurations: Iterable[Configuration] | None = None,
    execute_graphql: Callable[[str, str, Configuration], GraphQLResponse] | None = None,
    policy_evaluator: Callable[[str, TestCaseLike, GraphQLResponse], Evaluation] | None = None,
) -> BenchmarkReport:
    """Run all 72 pairs. Missing integrations are reported, never fabricated."""
    if corpus is None or configurations is None or execute_graphql is None:
        loaded_corpus, loaded_configurations, loaded_executor, loaded_evaluator = _load_integrations()
        corpus = corpus if corpus is not None else loaded_corpus
        configurations = configurations if configurations is not None else loaded_configurations
        execute_graphql = execute_graphql or loaded_executor
        policy_evaluator = policy_evaluator or loaded_evaluator
    if policy_evaluator is None:
        from policies.evaluator import evaluate_policy
        policy_evaluator = evaluate_policy
    cases, configs = _validate(corpus, configurations)

    started = perf_counter()
    results: list[BenchmarkResult] = []
    for config in configs:
        for case in cases:
            unit_started = perf_counter()
            response: GraphQLResponse | None = None
            try:
                response = execute_graphql(case.operation, case.identity, config)
                if not isinstance(response, GraphQLResponse):
                    raise TypeError("execute_graphql must return engine.contracts.GraphQLResponse")
                evaluation = policy_evaluator(case.identity, case, response)
                if not isinstance(evaluation, Evaluation):
                    raise TypeError("policy_evaluator must return engine.contracts.Evaluation")
                results.append(BenchmarkResult(
                    test_id=case.test_id,
                    configuration_id=config.configuration_id,
                    identity=case.identity,
                    expected_outcome=case.expected_outcome,
                    actual_observation=evaluation.actual_observation,
                    verdict=evaluation.verdict,
                    evidence=evaluation.evidence,
                    runtime_ms=round((perf_counter() - unit_started) * 1000, 3),
                    graphql_errors=tuple(response.errors),
                ))
            except Exception as exc:
                errors = tuple(getattr(response, "errors", ())) if response is not None else ()
                results.append(BenchmarkResult(
                    test_id=case.test_id,
                    configuration_id=config.configuration_id,
                    identity=case.identity,
                    expected_outcome=case.expected_outcome,
                    actual_observation="unit execution or evaluation failed",
                    verdict=None,
                    evidence=(f"{type(exc).__name__}: {exc}",),
                    runtime_ms=round((perf_counter() - unit_started) * 1000, 3),
                    graphql_errors=errors,
                    execution_error=f"{type(exc).__name__}: {exc}",
                ))

    expected_units = len(cases) * len(configs)
    pairs = [(item.configuration_id, item.test_id) for item in results]
    if len(results) != expected_units or len(set(pairs)) != expected_units:
        raise RuntimeError("Benchmark pair accounting failed; each pair must appear exactly once")
    return BenchmarkReport(tuple(results), expected_units, round((perf_counter() - started) * 1000, 3))

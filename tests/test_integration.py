"""End-to-end authorization checks using the real API and policy evaluator."""

import json

from graphql import parse, validate

from api.runner import execute_graphql
from api.schema import _SCHEMA
from engine.contracts import Verdict
from engine.benchmark import run_benchmark
from engine.integration import adapt_configurations, adapt_corpus
from engine.reporting import generate_report
from mutants.configurations import get_configurations as get_raw_configurations
from policies.evaluator import evaluate_policy
from tests.corpus import get_test_corpus as get_raw_corpus


CASES = {case.test_id: case for case in adapt_corpus(get_raw_corpus())}
CONFIGS = {config.configuration_id: config for config in adapt_configurations(get_raw_configurations())}


def _execute(test_id: str, configuration_id: str):
    case = CASES[test_id]
    response = execute_graphql(case.operation, case.identity, CONFIGS[configuration_id], case.variables)
    evaluation = evaluate_policy(case.identity, case, response)
    return response, evaluation


def test_all_corpus_operations_are_valid_against_the_real_schema():
    for case in CASES.values():
        assert not validate(_SCHEMA, parse(case.operation)), case.test_id


def test_required_root_bola_vertical_slice():
    alice_response, alice = _execute("T01", "C0")
    assert alice_response.data["invoice"]["ownerId"] == "user-alice"
    assert alice.verdict is Verdict.PASS
    assert any("owner" in item for item in alice.evidence)

    bob_denied_response, bob_denied = _execute("T02", "C0")
    assert bob_denied_response.data == {"invoice": None}
    assert bob_denied.verdict is Verdict.PASS

    bob_exposed_response, bob_exposed = _execute("T02", "C1")
    assert bob_exposed_response.data["invoice"]["id"] == "invoice-alice-001"
    assert bob_exposed.verdict is Verdict.POLICY_VIOLATION

    root_only_response, root_only = _execute("T10", "C1")
    assert root_only_response.data["invoice"]["internalNotes"] is None
    assert root_only.verdict is Verdict.PASS


def test_nested_bola_is_independently_mutated():
    baseline_response, baseline = _execute("T06", "C0")
    assert baseline_response.data == {"customer": None}
    assert baseline.verdict is Verdict.PASS

    mutant_response, mutant = _execute("T06", "C2")
    assert mutant_response.data["customer"]["id"] == "customer-alice"
    assert mutant.verdict is Verdict.POLICY_VIOLATION


def test_bopla_is_independently_mutated():
    baseline_response, baseline = _execute("T12", "C0")
    assert baseline_response.data["invoice"]["confidentialCode"] is None
    assert baseline.verdict is Verdict.PASS

    mutant_response, mutant = _execute("T12", "C3")
    assert mutant_response.data["invoice"]["confidentialCode"] == "CONF-ALICE-001"
    assert mutant.verdict is Verdict.POLICY_VIOLATION


def test_authentication_bypass_is_independently_mutated():
    baseline_response, baseline = _execute("T08", "C0")
    assert baseline_response.data == {"customer": None}
    assert baseline.verdict is Verdict.PASS

    mutant_response, mutant = _execute("T08", "C4")
    assert mutant_response.data["customer"]["id"] == "customer-alice"
    assert mutant.verdict is Verdict.POLICY_VIOLATION


def test_full_real_benchmark_accounts_and_serializes_all_pairs(tmp_path):
    report = run_benchmark()
    pairs = {(row.test_id, row.configuration_id) for row in report.results}
    assert report.expected_units == 72
    assert len(report.results) == len(pairs) == 72
    assert {row.test_id for row in report.results} == {f"T{i:02d}" for i in range(1, 13)}
    assert {row.configuration_id for row in report.results} == {f"C{i}" for i in range(6)}
    assert not report.failed_units
    assert sum(report.counts.values()) + len(report.failed_units) == 72
    t04_rows = [row for row in report.results if row.test_id == "T04"]
    assert len(t04_rows) == 6
    assert {row.configuration_id for row in t04_rows} == {f"C{i}" for i in range(6)}
    assert all(row.verdict is Verdict.INCONCLUSIVE for row in t04_rows)
    assert all(any("cannot establish an object-level decision" in item for item in row.evidence) for row in t04_rows)

    destination = generate_report(report, tmp_path / "actual-report.json")
    serialized = json.loads(destination.read_text(encoding="utf-8"))
    assert serialized["summary"]["total_units"] == 72
    assert serialized["summary"]["counts"] == report.counts
    assert len(serialized["results"]) == 72

"""Behavioral benchmark gate and report regression tests."""
import json
from dataclasses import replace
from typing import Any, cast

from graphql import build_schema

from engine.benchmark import _gate_findings, audit_resolver_bindings, run_benchmark
from engine.contracts import BenchmarkReport, Verdict
from engine.integration import adapt_corpus
from engine.reporting import generate_report
from mutants.configurations import get_configurations
from tests.corpus import get_test_corpus


def test_benchmark_runs_all_pairs_and_gate_passes():
    report = run_benchmark()
    assert len(report.results) == 72
    assert len({(row.test_id, row.configuration_id) for row in report.results}) == 72
    assert not report.failed_units
    assert report.gate_status == "PASSED"
    assert report.gate_findings == ()


def test_gate_detects_a_mutant_that_did_not_kill_its_declared_case():
    report = run_benchmark()
    rows = list(report.results)
    index = next(i for i, row in enumerate(rows) if row.configuration_id == "C1" and row.test_id == "T02")
    rows[index] = replace(rows[index], verdict=Verdict.PASS)
    findings = _gate_findings(
        cast(Any, adapt_corpus(get_test_corpus())), get_configurations(), tuple(rows),
        resolver_findings=(), validation_findings=(),
    )
    assert any("declared mutant kill was not observed" in finding for finding in findings)


def test_gate_detects_unexpected_vulnerability_contamination():
    report = run_benchmark()
    rows = list(report.results)
    index = next(i for i, row in enumerate(rows) if row.configuration_id == "C1" and row.test_id == "T01")
    rows[index] = replace(rows[index], verdict=Verdict.POLICY_VIOLATION)
    findings = _gate_findings(
        cast(Any, adapt_corpus(get_test_corpus())), get_configurations(), tuple(rows),
        resolver_findings=(), validation_findings=(),
    )
    assert any("cross-mutant contamination" in finding for finding in findings)


def test_resolver_audit_detects_unbound_authorization_resolver():
    schema = build_schema("type Query { invoice: String, invoices: String, customer: String } type Invoice { customer: String, internalNotes: String, confidentialCode: String }")
    findings = audit_resolver_bindings(schema)
    assert any("Query.invoice" in finding for finding in findings)


def test_report_serializes_failed_gate(tmp_path):
    failed = BenchmarkReport((), 72, 0.0, "FAILED", ("deliberate regression fixture",))
    target = generate_report(failed, tmp_path / "failed.json")
    data = json.loads(target.read_text(encoding="utf-8"))
    assert data["gate"]["status"] == "FAILED"
    assert data["gate"]["findings"] == ["deliberate regression fixture"]


def test_repeated_runs_have_deterministic_verdict_evidence():
    first, second = run_benchmark(), run_benchmark()
    project = lambda report: [(row.test_id, row.configuration_id, row.verdict, row.evidence, row.execution_error) for row in report.results]
    assert project(first) == project(second)


def test_cli_preserves_measured_rows_when_gate_fails(tmp_path, monkeypatch):
    import engine.benchmark as benchmark
    import main

    monkeypatch.setattr(benchmark, "_gate_findings", lambda *_args: ("fixture gate failure",))
    target = tmp_path / "failed.json"
    assert main.main(["--output", str(target)]) == 1
    data = json.loads(target.read_text(encoding="utf-8"))
    assert data["gate"]["status"] == "FAILED"
    assert data["summary"]["total_units"] == 72
    assert data["gate"]["findings"] == ["fixture gate failure"]


def test_cli_preserves_failed_report_when_benchmark_setup_raises(tmp_path, monkeypatch):
    import main

    def fail():
        raise ValueError("invalid corpus fixture")

    monkeypatch.setattr(main, "run_benchmark", fail)
    target = tmp_path / "setup-failed.json"
    assert main.main(["--output", str(target)]) == 1
    data = json.loads(target.read_text(encoding="utf-8"))
    assert data["gate"]["status"] == "FAILED"
    assert data["results"] == []
    assert "invalid corpus fixture" in data["gate"]["findings"][0]


def test_cli_returns_nonzero_when_report_cannot_be_written(monkeypatch, capsys):
    import main

    monkeypatch.setattr(main, "run_benchmark", lambda: BenchmarkReport((), 0, 0.0, "PASSED"))
    monkeypatch.setattr(main, "generate_report", lambda *_args: (_ for _ in ()).throw(OSError("read-only")))
    assert main.main(["--output", "unwritable.json"]) == 2
    assert "could not write" in capsys.readouterr().err


def test_execution_exceptions_remain_separate_from_verdict_counts():
    from engine.integration import adapt_configurations

    def failing_executor(*_args):
        raise RuntimeError("executor unavailable")

    report = run_benchmark(
        corpus=adapt_corpus(get_test_corpus()),
        configurations=adapt_configurations(get_configurations()),
        execute_graphql=failing_executor,
    )
    assert len(report.results) == 72
    assert len(report.failed_units) == 72
    assert sum(report.counts.values()) == 0
    assert report.gate_status == "FAILED"
    assert all("executor unavailable" in row.execution_error for row in report.failed_units)


def _kill_row(report, configuration_id, test_id):
    return next(row for row in report.results if row.configuration_id == configuration_id and row.test_id == test_id)


def _gate_with_replaced_row(report, row):
    rows = tuple(row if item.test_id == row.test_id and item.configuration_id == row.configuration_id else item for item in report.results)
    return _gate_findings(adapt_corpus(get_test_corpus()), get_configurations(), rows, resolver_findings=(), validation_findings=())


def test_kill_verdict_without_object_response_data_fails_gate():
    report = run_benchmark(); row = _kill_row(report, "C1", "T02")
    assert row.verdict is Verdict.POLICY_VIOLATION
    assert any("absent at the declared response path" in f for f in _gate_with_replaced_row(report, replace(row, response_data={"invoice": None})))


def test_object_kill_with_wrong_response_id_fails_gate():
    report = run_benchmark(); row = _kill_row(report, "C1", "T02")
    altered = replace(row, response_data={"invoice": {**row.response_data["invoice"], "id": "invoice-bob-001"}})
    assert any("does not match the declared target" in f for f in _gate_with_replaced_row(report, altered))


def test_property_kill_without_selected_property_fails_gate():
    report = run_benchmark(); row = _kill_row(report, "C3", "T10")
    altered = replace(row, response_data={"invoice": {k: v for k, v in row.response_data["invoice"].items() if k != "internalNotes"}})
    assert any("non-null restricted property" in f for f in _gate_with_replaced_row(report, altered))


def test_property_kill_with_null_value_fails_gate():
    report = run_benchmark(); row = _kill_row(report, "C3", "T10")
    altered = replace(row, response_data={"invoice": {**row.response_data["invoice"], "internalNotes": None}})
    assert any("non-null restricted property" in f for f in _gate_with_replaced_row(report, altered))


def test_collection_kill_with_empty_or_missing_collection_fails_gate():
    report = run_benchmark(); row = _kill_row(report, "C4", "T04")
    for data in ({"invoices": []}, {}):
        assert any("non-empty response collection" in f for f in _gate_with_replaced_row(report, replace(row, response_data=data)))


def test_collection_objects_without_protected_ids_fail_gate():
    report = run_benchmark(); row = _kill_row(report, "C4", "T04")
    altered = replace(row, response_data={"invoices": [{"id": "not-a-protected-invoice"}]})
    assert any("protected target IDs" in f for f in _gate_with_replaced_row(report, altered))


def test_missing_required_benchmark_pair_fails_gate():
    report = run_benchmark(); rows = tuple(r for r in report.results if not (r.configuration_id == "C1" and r.test_id == "T02"))
    findings = _gate_findings(adapt_corpus(get_test_corpus()), get_configurations(), rows, resolver_findings=(), validation_findings=())
    assert any("missing pairs" in f for f in findings)


def test_duplicate_benchmark_pair_fails_gate():
    report = run_benchmark(); rows = report.results + (report.results[0],)
    findings = _gate_findings(adapt_corpus(get_test_corpus()), get_configurations(), rows, resolver_findings=(), validation_findings=())
    assert any("duplicate test/configuration pairs" in f for f in findings)


def test_kill_evidence_for_different_declared_target_fails_gate():
    report = run_benchmark(); row = _kill_row(report, "C1", "T02")
    altered = replace(row, response_data={"invoice": {**row.response_data["invoice"], "id": "invoice-alice-002"}})
    assert any("does not match the declared target" in f for f in _gate_with_replaced_row(report, altered))
def test_malformed_collection_evidence_fails_gate():
    report = run_benchmark()
    row = _kill_row(report, "C4", "T04")
    altered = replace(row, response_data={"invoices": "not-a-list"})
    assert any(
        "non-empty response collection" in f
        for f in _gate_with_replaced_row(report, altered)
    )


def test_property_kill_with_wrong_parent_object_fails_gate():
    report = run_benchmark()
    row = _kill_row(report, "C3", "T10")
    altered = replace(
        row,
        response_data={
            "invoice": {
                **row.response_data["invoice"],
                "id": "invoice-bob-001",
            }
        },
    )
    assert _gate_with_replaced_row(report, altered)

def test_malformed_collection_evidence_fails_with_specific_finding():
    report = run_benchmark(); row = _kill_row(report, "C4", "T04")
    assert row.verdict is Verdict.POLICY_VIOLATION
    altered = replace(row, response_data={"invoices": "not-a-list"})
    findings = _gate_with_replaced_row(report, altered)
    assert any("collection kill response is malformed: expected a list" in finding for finding in findings)


def test_property_kill_with_wrong_parent_object_fails_target_check():
    report = run_benchmark(); row = _kill_row(report, "C3", "T10")
    altered = replace(row, response_data={"invoice": {**row.response_data["invoice"], "id": "invoice-bob-001"}})
    findings = _gate_with_replaced_row(report, altered)
    assert any("kill response object ID does not match the declared target" in finding for finding in findings)

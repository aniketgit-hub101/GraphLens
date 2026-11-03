"""Regression checks for evidence-sensitive authorization verdicts."""
from types import SimpleNamespace

from engine.contracts import GraphQLErrorInfo, GraphQLResponse, Target, Verdict
from policies.evaluator import evaluate_policy


def _case(outcome: str, *, identity: str = "bob", target_path=("invoice",), target_id="invoice-alice-001", property_name=None):
    return SimpleNamespace(
        test_id="engine-unit",
        description="evaluator unit fixture",
        identity=identity,
        operation="query { invoice { id } }",
        target=Target(target_path, target_id, property_name=property_name),
        expected_outcome=outcome,
        evidence_requirements=("target response path selected",),
        inconclusive_reason=None,
    )


def test_denied_object_explicit_null_without_error_is_pass():
    case = _case("deny_object")
    result = evaluate_policy("bob", case, GraphQLResponse({"invoice": None}))
    assert result.verdict is Verdict.PASS


def test_denied_object_missing_response_path_is_inconclusive():
    case = _case("deny_object")
    result = evaluate_policy("bob", case, GraphQLResponse({}))
    assert result.verdict is Verdict.INCONCLUSIVE


def test_denied_object_relevant_graphql_error_is_inconclusive():
    case = _case("deny_object")
    response = GraphQLResponse({"invoice": None}, (GraphQLErrorInfo("resolver failed", ("invoice",)),))
    assert evaluate_policy("bob", case, response).verdict is Verdict.INCONCLUSIVE


def test_denied_property_missing_parent_path_is_inconclusive():
    case = _case("deny_property", property_name="internalNotes")
    result = evaluate_policy("bob", case, GraphQLResponse({}))
    assert result.verdict is Verdict.INCONCLUSIVE


def test_denied_property_absent_parent_is_inconclusive():
    case = _case("deny_property", property_name="internalNotes")
    result = evaluate_policy("bob", case, GraphQLResponse({"invoice": None}))
    assert result.verdict is Verdict.INCONCLUSIVE


def test_denied_property_selected_null_is_pass():
    case = _case("deny_property", property_name="internalNotes")
    result = evaluate_policy("bob", case, GraphQLResponse({"invoice": {"id": "invoice-alice-001", "internalNotes": None}}))
    assert result.verdict is Verdict.PASS


def test_denied_property_non_null_value_is_violation():
    case = _case("deny_property", property_name="internalNotes")
    result = evaluate_policy("bob", case, GraphQLResponse({"invoice": {"id": "invoice-alice-001", "internalNotes": "synthetic"}}))
    assert result.verdict is Verdict.POLICY_VIOLATION


def _collection_case():
    return SimpleNamespace(
        test_id="T04", identity="anonymous", expected_outcome="inconclusive",
        target=Target(("invoices",), None, is_collection=True, requires_authentication=True),
        evidence_requirements=("collection evidence",),
        inconclusive_reason="An empty collection cannot establish an object-level decision.",
    )


def test_t04_empty_collection_is_inconclusive_for_evidence_reasons():
    result = evaluate_policy("anonymous", _collection_case(), GraphQLResponse({"invoices": []}))
    assert result.verdict is Verdict.INCONCLUSIVE
    assert "empty" in result.evidence[0].casefold()
    assert "object-level decision" in result.evidence[0]


def test_t04_null_collection_is_inconclusive():
    result = evaluate_policy("anonymous", _collection_case(), GraphQLResponse({"invoices": None}))
    assert result.verdict is Verdict.INCONCLUSIVE


def test_t04_nonempty_collection_is_violation_despite_inconclusive_policy_intent():
    response = GraphQLResponse({"invoices": [{"id": "invoice-alice-001", "ownerId": "user-alice"}]})
    result = evaluate_policy("anonymous", _collection_case(), response)
    assert result.verdict is Verdict.POLICY_VIOLATION
    assert "invoice-alice-001" in result.evidence[0]


def test_t04_malformed_collection_object_is_inconclusive():
    response = GraphQLResponse({"invoices": [{"ownerId": "user-alice"}]})
    assert evaluate_policy("anonymous", _collection_case(), response).verdict is Verdict.INCONCLUSIVE


def test_unclassified_case_without_a_target_is_inconclusive():
    case = SimpleNamespace(
        test_id="T04", identity="anonymous", expected_outcome="inconclusive",
        target=None, inconclusive_reason=None, evidence_requirements=(),
    )
    assert evaluate_policy("anonymous", case, GraphQLResponse({"invoices": []})).verdict is Verdict.INCONCLUSIVE

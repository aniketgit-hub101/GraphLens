"""Evidence-based classifier for GraphLens authorization responses."""
from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from engine.contracts import Evaluation, GraphQLResponse, TestCaseLike, Verdict

_RULES_PATH = Path(__file__).with_name("rules.json")


def _load_rules() -> dict[str, Any]:
    try:
        with _RULES_PATH.open(encoding="utf-8") as source:
            rules = json.load(source)
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Cannot load GraphLens policy rules at {_RULES_PATH}: {exc}") from exc
    outcomes = rules.get("outcomes", {})
    if not all(key in outcomes for key in ("allow", "deny_object", "deny_property", "inconclusive")):
        raise RuntimeError("Policy rules must define allow, deny_object, deny_property, and inconclusive")
    return rules


_RULES = _load_rules()


def _get(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(key, default)
    return getattr(value, key, default)


def _at_path(value: Any, path: Sequence[str | int]) -> Any:
    current = value
    for part in path:
        if isinstance(current, Mapping) and isinstance(part, str):
            current = current.get(part)
        elif isinstance(current, Sequence) and not isinstance(current, (str, bytes)) and isinstance(part, int):
            current = current[part] if 0 <= part < len(current) else None
        else:
            return None
    return current


def _contains_path(value: Any, path: Sequence[str | int]) -> bool:
    current = value
    for part in path:
        if isinstance(current, Mapping) and isinstance(part, str) and part in current:
            current = current[part]
        elif isinstance(current, Sequence) and not isinstance(current, (str, bytes)) and isinstance(part, int) and 0 <= part < len(current):
            current = current[part]
        else:
            return False
    return True


def _find_target(data: Mapping[str, object] | None, target: Any) -> tuple[Mapping[str, object] | None, tuple[str | int, ...] | None, bool]:
    if data is None:
        return None, None, False
    response_path = tuple(_get(target, "response_path", ()))
    if not _contains_path(data, response_path):
        return None, None, False
    node = _at_path(data, response_path)
    if node is None:
        return None, None, False
    object_id = _get(target, "object_id")
    if isinstance(node, Mapping):
        if "id" not in node:
            return None, None, True
        if node.get("id") == object_id:
            return node, response_path, False
        return None, None, False
    if isinstance(node, Sequence) and not isinstance(node, (str, bytes)):
        unidentified = False
        for index, candidate in enumerate(node):
            if not isinstance(candidate, Mapping):
                continue
            if "id" not in candidate:
                unidentified = True
            elif candidate.get("id") == object_id:
                return candidate, response_path + (index,), False
        return None, None, unidentified
    return None, None, True


def _property_path(target: Any) -> tuple[str | int, ...]:
    property_name = _get(target, "property_name")
    property_path = tuple(_get(target, "property_path", ()))
    if property_path:
        return property_path
    return (property_name,) if property_name is not None else ()


def _error_path(error: Any) -> tuple[str | int, ...] | None:
    raw_path = _get(error, "path")
    return tuple(raw_path) if raw_path is not None else None


def _has_relevant_error(errors: Sequence[Any], path: tuple[str | int, ...]) -> bool:
    for error in errors:
        error_path = _error_path(error)
        if error_path is None:
            return True
        common = min(len(path), len(error_path))
        if path[:common] == error_path[:common]:
            return True
    return False


def _evidence(case: Any, response: GraphQLResponse, actual: str) -> tuple[str, ...]:
    messages = tuple(str(_get(error, "message", "GraphQL error")) for error in response.errors)
    # Requirements describe what to inspect; only observed facts belong in evidence.
    return (actual,) + tuple(f"GraphQL error: {message}" for message in messages)


def evaluate_policy(identity: str, operation: TestCaseLike, response: GraphQLResponse) -> Evaluation:
    """Classify observed data; HTTP status and execution success alone do not prove access.

    The operation argument is a test case following the provisional integration
    proposal. GraphQL partial data is evaluated at the target field/path only.
    """
    case = operation
    expected = str(_get(case, "expected_outcome", ""))
    case_identity = _get(case, "identity")
    target = _get(case, "target")
    inconclusive_reason = _get(case, "inconclusive_reason")
    if case_identity is not None and case_identity != identity:
        return Evaluation(Verdict.INCONCLUSIVE, ("Evaluator identity does not match the case identity",), expected, "identity mismatch")
    if inconclusive_reason:
        return Evaluation(Verdict.INCONCLUSIVE, (str(inconclusive_reason),), expected, "case designated inconclusive")
    if expected == "inconclusive":
        return Evaluation(Verdict.INCONCLUSIVE, ("Case policy explicitly requires an inconclusive classification",), expected, "case outcome is inconclusive")
    if expected not in _RULES["outcomes"] or target is None:
        return Evaluation(Verdict.INCONCLUSIVE, ("Case lacks a supported expected outcome or target description",), expected, "unclassified case")

    response_path = tuple(_get(target, "response_path", ()))
    property_path = _property_path(target)
    found_target = _find_target(response.data, target)
    target_object = found_target[0]
    observed_target_path = found_target[1] or response_path
    target_unidentified = found_target[2]

    if response.data is None and response.errors:
        return Evaluation(Verdict.INCONCLUSIVE, _evidence(case, response, "No GraphQL data payload was available"), expected, "no data with GraphQL errors")
    if target_unidentified:
        return Evaluation(Verdict.INCONCLUSIVE, _evidence(case, response, "Response object was returned without the target identifier"), expected, "target identity absent")

    if expected == "allow":
        if target_object is None:
            detail = "Expected target object was not present in returned data"
            if _has_relevant_error(response.errors, response_path):
                detail += "; a relevant GraphQL error prevents reliable classification"
            return Evaluation(Verdict.INCONCLUSIVE, _evidence(case, response, detail), expected, "expected access not evidenced")
        owner_path = tuple(_get(target, "owner_path", ()))
        expected_owner_id = _get(target, "expected_owner_id")
        owner_evidence = ""
        if owner_path and expected_owner_id is not None:
            if not _contains_path(target_object, owner_path):
                return Evaluation(Verdict.INCONCLUSIVE, _evidence(case, response, "Expected owner evidence was not present in the response"), expected, "owner evidence absent")
            if _at_path(target_object, owner_path) != expected_owner_id:
                return Evaluation(Verdict.INCONCLUSIVE, _evidence(case, response, "Returned object owner did not match the case identity"), expected, "owner mismatch")
            owner_evidence = f"; owner path matched {expected_owner_id}"
        if property_path:
            property_present = _contains_path(target_object, property_path)
            property_value = _at_path(target_object, property_path)
            if not property_present:
                return Evaluation(Verdict.INCONCLUSIVE, _evidence(case, response, "Expected property was not present in the response"), expected, "expected property absent")
            if property_value is None:
                detail = "Expected property is null; response cannot distinguish a valid null from withheld data"
                if _has_relevant_error(response.errors, observed_target_path + property_path):
                    detail += " and has a relevant GraphQL error"
                return Evaluation(Verdict.INCONCLUSIVE, _evidence(case, response, detail), expected, "property null")
            return Evaluation(Verdict.PASS, _evidence(case, response, "Expected object and property were returned" + owner_evidence), expected, "target and property returned")
        return Evaluation(Verdict.PASS, _evidence(case, response, "Expected target object was returned" + owner_evidence), expected, "target returned")

    if expected in ("deny_object", "deny_property"):
        if response.data is None:
            return Evaluation(Verdict.INCONCLUSIVE, _evidence(case, response, "No response data is available to establish denial"), expected, "missing response data")
        if not _contains_path(response.data, response_path):
            return Evaluation(Verdict.INCONCLUSIVE, _evidence(case, response, "Target response path is absent; denial is not evidenced"), expected, "target path missing")

    if expected == "deny_object":
        if target_object is not None:
            return Evaluation(Verdict.POLICY_VIOLATION, _evidence(case, response, "Unauthorized target object was returned"), expected, "target returned")
        if _has_relevant_error(response.errors, response_path):
            return Evaluation(Verdict.INCONCLUSIVE, _evidence(case, response, "Target is absent but a relevant GraphQL error prevents distinguishing denial from execution failure"), expected, "target absent with relevant error")
        return Evaluation(Verdict.PASS, _evidence(case, response, "Unauthorized target object was absent or null"), expected, "target absent")

    if expected == "deny_property":
        if target_object is None:
            if _has_relevant_error(response.errors, response_path):
                return Evaluation(Verdict.INCONCLUSIVE, _evidence(case, response, "Parent object is absent with a relevant GraphQL error"), expected, "parent unavailable with relevant error")
            return Evaluation(Verdict.PASS, _evidence(case, response, "Parent object was withheld; restricted property was not exposed"), expected, "parent absent")
        if not property_path:
            return Evaluation(Verdict.INCONCLUSIVE, _evidence(case, response, "Restricted property path is missing from the case target"), expected, "property path missing")
        property_present = _contains_path(target_object, property_path)
        if not property_present:
            return Evaluation(Verdict.INCONCLUSIVE, _evidence(case, response, "Restricted property was omitted or not selected"), expected, "property absent")
        if _has_relevant_error(response.errors, observed_target_path + property_path):
            return Evaluation(Verdict.INCONCLUSIVE, _evidence(case, response, "Restricted property has a relevant GraphQL error"), expected, "property resolution uncertain")
        property_value = _at_path(target_object, property_path)
        if property_value is not None:
            return Evaluation(Verdict.POLICY_VIOLATION, _evidence(case, response, "Restricted property has a non-null returned value"), expected, "restricted value returned")
        return Evaluation(Verdict.PASS, _evidence(case, response, "Restricted property was selected and returned null without a relevant error"), expected, "property withheld")

    return Evaluation(Verdict.INCONCLUSIVE, ("No evaluator rule matches the expected outcome",), expected, "unclassified")

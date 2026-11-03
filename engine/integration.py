"""Adapters from the API, corpus, and mutant packages to engine contracts."""
from __future__ import annotations

from typing import Iterable

from engine.contracts import Configuration, Target, TestCase

_OWNER_IDS = {"alice": "user-alice", "bob": "user-bob"}


def adapt_test_case(source: object) -> TestCase:
    """Translate the published security corpus shape without changing its intent."""
    identity = str(getattr(source, "identity")).casefold()
    if identity not in ("alice", "bob", "anonymous"):
        raise ValueError(f"Unsupported corpus identity: {identity!r}")

    variables_method = getattr(source, "variable_map", None)
    variables = variables_method() if callable(variables_method) else dict(getattr(source, "variables", ()))
    raw_target = getattr(source, "target")
    raw_outcome = getattr(source, "expected_outcome")
    outcome = getattr(raw_outcome, "value", raw_outcome)
    category = getattr(getattr(source, "category", ""), "value", getattr(source, "category", ""))

    if outcome == "inconclusive" or getattr(raw_target, "is_collection", False):
        expected_outcome = "inconclusive"
        target = None
    else:
        if outcome == "allow":
            expected_outcome = "allow"
        elif outcome == "deny" and category == "property_bopla":
            expected_outcome = "deny_property"
        elif outcome == "deny":
            expected_outcome = "deny_object"
        else:
            raise ValueError(f"Unsupported corpus expected outcome: {outcome!r}")

        resource_type = str(getattr(raw_target, "resource_type"))
        resource_id = getattr(raw_target, "resource_id")
        response_path = (resource_type, *tuple(getattr(raw_target, "object_path", ())))
        property_name = getattr(raw_target, "property_name", None)
        owner_path: tuple[str | int, ...] = ()
        expected_owner_id = None
        if expected_outcome == "allow" and "ownerId" in getattr(source, "operation", ""):
            owner_path = ("ownerId",)
            expected_owner_id = _OWNER_IDS.get(identity)
        target = Target(
            response_path=response_path,
            object_id=resource_id,
            property_name=property_name,
            property_path=(property_name,) if property_name else (),
            owner_path=owner_path,
            expected_owner_id=expected_owner_id,
        )

    return TestCase(
        test_id=str(getattr(source, "test_id")),
        description=str(getattr(source, "rationale", getattr(source, "description", ""))),
        identity=identity,  # type: ignore[arg-type]
        operation=str(getattr(source, "operation")),
        variables=dict(variables),
        target=target,
        expected_outcome=expected_outcome,  # type: ignore[arg-type]
        evidence_requirements=tuple(getattr(source, "evidence_requirements", ())),
        inconclusive_reason=(
            str(getattr(source, "rationale", "Evidence is insufficient for a definitive classification"))
            if expected_outcome == "inconclusive"
            else None
        ),
    )


def adapt_corpus(corpus: Iterable[object]) -> tuple[TestCase, ...]:
    return tuple(adapt_test_case(case) for case in corpus)


def adapt_configurations(configurations: Iterable[object]) -> tuple[Configuration, ...]:
    """Normalize the mutant package's id/set objects to engine configurations."""
    normalized = []
    for source in configurations:
        configuration_id = str(getattr(source, "configuration_id", getattr(source, "id", "")))
        enabled_mutants = frozenset(str(item) for item in getattr(source, "enabled_mutants"))
        normalized.append(Configuration(configuration_id, configuration_id, enabled_mutants))
    return tuple(normalized)

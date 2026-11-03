"""Shared value objects for the provisional GraphLens integration boundary."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Literal, Mapping, Protocol, TypeAlias

Identity: TypeAlias = Literal["alice", "bob", "anonymous"]
ExpectedOutcome: TypeAlias = Literal["allow", "deny_object", "deny_property", "inconclusive"]


class Verdict(str, Enum):
    PASS = "PASS"
    POLICY_VIOLATION = "POLICY_VIOLATION"
    INCONCLUSIVE = "INCONCLUSIVE"


@dataclass(frozen=True)
class Target:
    """Response target; paths use GraphQL response keys (including aliases)."""

    response_path: tuple[str | int, ...]
    object_id: str | int | None
    property_name: str | None = None
    property_path: tuple[str | int, ...] = ()
    owner_path: tuple[str | int, ...] = ()
    expected_owner_id: str | None = None
    is_collection: bool = False
    requires_authentication: bool = False
    object_id_field: str = "id"


@dataclass(frozen=True)
class Configuration:
    configuration_id: str
    name: str
    enabled_mutants: frozenset[str]


@dataclass(frozen=True)
class GraphQLErrorInfo:
    message: str
    path: tuple[str | int, ...] | None = None
    locations: tuple[tuple[int, int], ...] = ()


@dataclass(frozen=True)
class GraphQLResponse:
    data: Mapping[str, object] | None
    errors: tuple[GraphQLErrorInfo, ...] = ()
    http_status: int | None = None


@dataclass(frozen=True)
class Evaluation:
    verdict: Verdict
    evidence: tuple[str, ...]
    expected_outcome: str
    actual_observation: str


class TestCaseLike(Protocol):
    test_id: str
    description: str
    identity: Identity
    operation: str
    variables: Mapping[str, object]
    target: Target | None
    expected_outcome: ExpectedOutcome
    evidence_requirements: tuple[str, ...]
    inconclusive_reason: str | None


@dataclass(frozen=True)
class TestCase:
    """Canonical engine case created from the stable security corpus."""

    test_id: str
    description: str
    identity: Identity
    operation: str
    variables: Mapping[str, object]
    target: Target | None
    expected_outcome: ExpectedOutcome
    evidence_requirements: tuple[str, ...]
    inconclusive_reason: str | None = None


@dataclass(frozen=True)
class BenchmarkResult:
    test_id: str
    configuration_id: str
    identity: str
    expected_outcome: str
    actual_observation: str
    verdict: Verdict | None
    evidence: tuple[str, ...]
    runtime_ms: float
    graphql_errors: tuple[GraphQLErrorInfo, ...] = ()
    execution_error: str | None = None
    response_data: Mapping[str, object] | None = None

    def to_dict(self) -> dict[str, object]:
        value = asdict(self)
        value["verdict"] = self.verdict.value if self.verdict else None
        return value


@dataclass(frozen=True)
class BenchmarkReport:
    results: tuple[BenchmarkResult, ...]
    expected_units: int
    runtime_ms: float
    gate_status: str = "NOT_RUN"
    gate_findings: tuple[str, ...] = ()

    @property
    def counts(self) -> dict[str, int]:
        return {
            verdict.value: sum(result.verdict == verdict for result in self.results)
            for verdict in Verdict
        }

    @property
    def failed_units(self) -> tuple[BenchmarkResult, ...]:
        return tuple(result for result in self.results if result.verdict is None)

    def per_configuration(self) -> dict[str, dict[str, object]]:
        groups: dict[str, list[BenchmarkResult]] = {}
        for result in self.results:
            groups.setdefault(result.configuration_id, []).append(result)
        output: dict[str, dict[str, object]] = {}
        for configuration_id, rows in groups.items():
            output[configuration_id] = {
                "total": len(rows),
                "counts": {verdict.value: sum(r.verdict == verdict for r in rows) for verdict in Verdict},
                "failed_units": sum(r.verdict is None for r in rows),
                "runtime_ms": round(sum(r.runtime_ms for r in rows), 3),
            }
        return output

    def to_dict(self) -> dict[str, object]:
        return {
            "summary": {
                "total_units": len(self.results),
                "expected_units": self.expected_units,
                "completed_units": len(self.results) - len(self.failed_units),
                "failed_units": len(self.failed_units),
                "counts": self.counts,
                "runtime_ms": round(self.runtime_ms, 3),
            },
            "gate": {"status": self.gate_status, "findings": list(self.gate_findings)},
            "configurations": self.per_configuration(),
            "results": [result.to_dict() for result in self.results],
        }

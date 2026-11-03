"""Declarative mutant catalog and benchmark configuration matrix.

This module selects conceptual mutant profiles only. Engine/API wiring is left
to the integration adapter; it does not fabricate run results or verdict counts.
"""

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True, slots=True)
class Mutant:
    id: str
    name: str
    target: str
    behavior: str


@dataclass(frozen=True, slots=True)
class Configuration:
    id: str
    enabled_mutants: tuple[str, ...]


MUTANTS: Final[tuple[Mutant, ...]] = (
    Mutant(
        id="M1",
        name="root_ownership_bypass",
        target="root invoice resolver",
        behavior="Skip the owner check when resolving invoice(id: ...).",
    ),
    Mutant(
        id="M2",
        name="nested_ownership_bypass",
        target="nested invoice object resolver",
        behavior="Skip or lose the parent invoice ownership check during nested traversal.",
    ),
    Mutant(
        id="M3",
        name="restricted_property_exposure",
        target="restricted invoice properties",
        behavior="Expose internalNotes or confidentialCode without applying its property policy.",
    ),
    Mutant(
        id="M4",
        name="authentication_authorization_bypass",
        target="authentication and authorization boundary",
        behavior="Treat an unauthenticated or unauthorized request as authorized.",
    ),
)

MUTANT_IDS: Final[frozenset[str]] = frozenset(mutant.id for mutant in MUTANTS)

CONFIGURATIONS: Final[tuple[Configuration, ...]] = (
    Configuration(id="C0", enabled_mutants=()),
    Configuration(id="C1", enabled_mutants=("M1",)),
    Configuration(id="C2", enabled_mutants=("M2",)),
    Configuration(id="C3", enabled_mutants=("M3",)),
    Configuration(id="C4", enabled_mutants=("M4",)),
    Configuration(id="C5", enabled_mutants=("M1", "M2", "M3", "M4")),
)

CONFIGS_BY_ID: Final[dict[str, Configuration]] = {
    configuration.id: configuration for configuration in CONFIGURATIONS
}


def enabled_mutants(configuration_id: str) -> tuple[Mutant, ...]:
    """Resolve a configuration to its mutant specs; unknown IDs fail clearly."""
    configuration = CONFIGS_BY_ID[configuration_id]
    by_id = {mutant.id: mutant for mutant in MUTANTS}
    return tuple(by_id[mutant_id] for mutant_id in configuration.enabled_mutants)

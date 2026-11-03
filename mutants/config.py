"""Mutant definitions and C0–C5 configuration interface."""

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True, slots=True)
class Mutant:
    mutant_id: str
    name: str
    target: str
    behavior: str


@dataclass(frozen=True, slots=True)
class Configuration:
    configuration_id: str
    enabled_mutants: frozenset[str]


MUTANTS: Final[tuple[Mutant, ...]] = (
    Mutant("M1", "root_ownership_bypass", "root invoice resolver", "Skip owner authorization for invoice(id: ...)."),
    Mutant("M2", "nested_ownership_bypass", "nested invoice resolver", "Skip parent ownership authorization during nested traversal."),
    Mutant("M3", "restricted_property_exposure", "restricted invoice properties", "Expose internalNotes or confidentialCode without its property policy."),
    Mutant("M4", "authentication_authorization_bypass", "authentication boundary", "Allow a request through without required authentication or authorization."),
)
MUTANT_IDS: Final[frozenset[str]] = frozenset(mutant.mutant_id for mutant in MUTANTS)

CONFIGURATIONS: Final[tuple[Configuration, ...]] = (
    Configuration("C0", frozenset()),
    Configuration("C1", frozenset({"M1"})),
    Configuration("C2", frozenset({"M2"})),
    Configuration("C3", frozenset({"M3"})),
    Configuration("C4", frozenset({"M4"})),
    Configuration("C5", frozenset({"M1", "M2", "M3", "M4"})),
)

CONFIGS_BY_ID: Final[dict[str, Configuration]] = {
    configuration.configuration_id: configuration for configuration in CONFIGURATIONS
}

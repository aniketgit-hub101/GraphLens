"""Canonical validator and C0–C5 configurations."""

from collections.abc import Mapping, Sequence
from typing import Any

from engine.contracts import Configuration
from .config import CONFIGURATIONS, CONFIGS_BY_ID, MUTANT_IDS

_MUTANT_SWITCHES = {
    "M1": "ROOT_BOLA",
    "M2": "NESTED_BOLA",
    "M3": "BOPLA",
    "M4": "AUTH_BYPASS",
}
_SWITCH_TO_MUTANT = {switch: mutant for mutant, switch in _MUTANT_SWITCHES.items()}


def get_configurations() -> tuple[Configuration, ...]:
    """Return configs in stable C0–C5 order; mutant sets are immutable."""
    return CONFIGURATIONS


def normalize_configuration(value: Any) -> Configuration:
    """Validate a canonical config or adapt the explicit corpus config mapping.

    The mapping adapter accepts only ``configuration_id`` and an ordered
    ``enabled_mutants`` collection. Unknown IDs/names, duplicate entries,
    malformed containers, and mutant sets that do not match C0–C5 are errors.
    """
    if isinstance(value, Configuration):
        configuration_id = value.configuration_id
        enabled = value.enabled_mutants
        if not isinstance(enabled, frozenset):
            raise TypeError("enabled_mutants must be a frozenset")
    elif isinstance(value, Mapping):
        if set(value) != {"configuration_id", "enabled_mutants"}:
            raise ValueError("configuration mapping must contain exactly configuration_id and enabled_mutants")
        configuration_id = value["configuration_id"]
        raw_enabled = value["enabled_mutants"]
        if not isinstance(raw_enabled, Sequence) or isinstance(raw_enabled, (str, bytes)):
            raise TypeError("mapped enabled_mutants must be a sequence")
        normalized: list[str] = []
        for item in raw_enabled:
            if not isinstance(item, str):
                raise TypeError("mutant names must be strings")
            name = item.strip().upper()
            mutant_id = name if name in MUTANT_IDS else _SWITCH_TO_MUTANT.get(name)
            if mutant_id is None:
                raise ValueError(f"unknown mutant name: {item!r}")
            normalized.append(mutant_id)
        if len(normalized) != len(set(normalized)):
            raise ValueError("enabled_mutants contains duplicate entries")
        enabled = frozenset(normalized)
    else:
        raise TypeError("configuration must be an engine Configuration or validated mapping")

    if not isinstance(configuration_id, str) or configuration_id not in CONFIGS_BY_ID:
        raise ValueError(f"unknown configuration_id: {configuration_id!r}")
    canonical = CONFIGS_BY_ID[configuration_id]
    if enabled != canonical.enabled_mutants:
        raise ValueError(
            f"{configuration_id} requires mutants {sorted(canonical.enabled_mutants)}, got {sorted(enabled)}"
        )
    return canonical

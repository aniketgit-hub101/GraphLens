"""Canonical evaluator interface for C0–C5."""

from .config import CONFIGURATIONS, Configuration


def get_configurations() -> tuple[Configuration, ...]:
    """Return configs in stable C0–C5 order; mutant sets are immutable."""
    return CONFIGURATIONS

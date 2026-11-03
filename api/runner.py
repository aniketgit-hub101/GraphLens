"""Adapter from the synthetic schema to the engine's response contract."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from graphql import graphql_sync
from engine.contracts import GraphQLErrorInfo, GraphQLResponse
from mutants.configurations import normalize_configuration

from .schema import _SCHEMA, _build_context, normalize_identity


def _enabled_mutants(config: Any) -> set[str]:
    normalized = normalize_configuration(config)
    mapping = {"M1": "ROOT_BOLA", "M2": "NESTED_BOLA", "M3": "BOPLA", "M4": "AUTH_BYPASS"}
    return {mapping[mutant_id] for mutant_id in normalized.enabled_mutants}


def execute_graphql(
    query: str,
    identity: str,
    config: Any,
    variables: Mapping[str, object] | None = None,
) -> GraphQLResponse:
    """Execute a query and return engine-compatible data and GraphQL errors."""
    normalized_identity = normalize_identity(identity)
    enabled_mutants = _enabled_mutants(config)
    context = _build_context(normalized_identity, {"mutants": sorted(enabled_mutants)})
    result = graphql_sync(_SCHEMA, query, context_value=context, variable_values=dict(variables or {}))
    errors = tuple(
        GraphQLErrorInfo(
            message=error.message,
            path=tuple(error.path) if error.path is not None else None,
            locations=tuple((location.line, location.column) for location in error.locations or ()),
        )
        for error in (result.errors or ())
    )
    return GraphQLResponse(data=result.data, errors=errors)

"""Adapter from the synthetic schema to the engine's response contract."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .schema import _SCHEMA
from graphql import graphql_sync

try:
    from engine.contracts import GraphQLErrorInfo, GraphQLResponse
except ImportError:  # Allows the API branch to be tested before engine integration.
    @dataclass(frozen=True)
    class GraphQLErrorInfo:
        message: str
        path: tuple[str | int, ...] | None = None
        locations: tuple[tuple[int, int], ...] = ()

    @dataclass(frozen=True)
    class GraphQLResponse:
        data: dict[str, Any] | None
        errors: tuple[GraphQLErrorInfo, ...] = ()
        http_status: int | None = None

from .schema import _build_context


def _enabled_mutants(config: Any) -> set[str]:
    values = getattr(config, "enabled_mutants", None)
    if values is not None:
        mapping = {"M1": "ROOT_BOLA", "M2": "NESTED_BOLA", "M3": "BOPLA", "M4": "AUTH_BYPASS"}
        return {mapping.get(str(value).upper(), str(value)) for value in values}
    if isinstance(config, dict):
        values = config.get("mutants", ())
        if isinstance(values, str):
            values = (values,)
        return {str(value) for value in values}
    return set()


def execute_graphql(query: str, identity: str, config: Any) -> GraphQLResponse:
    """Execute a query and return engine-compatible data and GraphQL errors."""
    context = _build_context(identity, {"mutants": sorted(_enabled_mutants(config))})
    result = graphql_sync(_SCHEMA, query, context_value=context)
    errors = tuple(
        GraphQLErrorInfo(
            message=error.message,
            path=tuple(error.path) if error.path is not None else None,
            locations=tuple((location.line, location.column) for location in error.locations or ()),
        )
        for error in (result.errors or ())
    )
    return GraphQLResponse(data=result.data, errors=errors)

"""GraphQL schema, resolvers, and authorization-aware execution entry point."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from graphql import build_schema

from .data import CUSTOMERS, INVOICES, USERS, Customer, Invoice, User, identity_user

SCHEMA_SDL = """
type Query {
  me: User
  invoice(id: ID!): Invoice
  invoices: [Invoice!]!
  customer(id: ID!): Customer
}

type User {
  id: ID!
  name: String!
  invoices: [Invoice!]!
}

type Invoice {
  id: ID!
  ownerId: ID!
  number: String!
  amount: Float!
  currency: String!
  status: String!
  owner: User!
  customer: Customer!
  internalNotes: String
  paymentReference: String
  confidentialCode: String
}

type Customer {
  id: ID!
  name: String!
  email: String
  taxId: String
}
"""

_SCHEMA = build_schema(SCHEMA_SDL)

_IDENTITIES = frozenset({"alice", "bob", "anonymous"})


def normalize_identity(identity: object) -> str:
    """Return a supported normalized identity or reject the input."""
    if not isinstance(identity, str):
        raise TypeError("identity must be a string")
    if identity not in _IDENTITIES:
        raise ValueError(f"unknown identity or non-canonical identity value: {identity!r}")
    return identity


def _enabled_mutants(config: Mapping[str, Any] | None) -> set[str]:
    if not config:
        return set()
    raw = config.get("mutants", ())
    if isinstance(raw, str):
        raw = (raw,)
    if not isinstance(raw, (list, tuple, set, frozenset)):
        return set()
    return {str(item).strip().casefold().replace("-", "_") for item in raw}


def _mutant_enabled(config: Mapping[str, Any], *names: str) -> bool:
    active = _enabled_mutants(config)
    return any(name.casefold().replace("-", "_") in active for name in names)


def _anonymous_m4_enabled(context: Mapping[str, Any]) -> bool:
    return context.get("identity") == "anonymous" and _mutant_enabled(context.get("config"), "AUTH_BYPASS")


def _is_authenticated(context: Mapping[str, Any]) -> bool:
    return context.get("user") is not None or _anonymous_m4_enabled(context)


def _object_access_allowed(invoice: Invoice, context: Mapping[str, Any], scope: str = "root") -> bool:
    config = context.get("config")
    if _anonymous_m4_enabled(context):
        return True
    if scope == "nested" and _mutant_enabled(config, "NESTED_BOLA"):
        return True
    if scope == "root" and _mutant_enabled(config, "ROOT_BOLA"):
        return True
    user = context.get("user")
    return user is not None and (
        invoice["owner_id"] == user["id"] or user["id"] in invoice["viewer_ids"]
    )


def _field_access_allowed(invoice: Invoice, context: Mapping[str, Any]) -> bool:
    config = context.get("config")
    if _mutant_enabled(config, "BOPLA"):
        return True
    # Root BOLA and nested BOLA mutants affect object access only. They must not
    # silently turn an owner-scoped property into a BOPLA mutant.
    user = context.get("user")
    return user is not None and invoice["owner_id"] == user["id"]


def _visible_invoice(invoice: Invoice, context: Mapping[str, Any], scope: str = "root") -> bool:
    if not _is_authenticated(context):
        return False
    return _object_access_allowed(invoice, context, scope)


def _resolve_me(_root: Any, info: Any) -> User | None:
    return info.context["user"]


def _resolve_invoice(_root: Any, info: Any, id: str) -> Invoice | None:
    invoice = INVOICES.get(id)
    return invoice if invoice is not None and _visible_invoice(invoice, info.context) else None


def _resolve_invoices(_root: Any, info: Any) -> list[Invoice]:
    if not _is_authenticated(info.context):
        return []
    return [invoice for invoice in INVOICES.values() if _visible_invoice(invoice, info.context, "collection")]


def _resolve_customer(_root: Any, info: Any, id: str) -> Customer | None:
    customer = CUSTOMERS.get(id)
    if customer is None:
        return None
    linked = [invoice for invoice in INVOICES.values() if invoice["customer_id"] == id]
    return customer if any(_visible_invoice(invoice, info.context, "nested") for invoice in linked) else None


def _resolve_user_invoices(user: User, info: Any) -> list[Invoice]:
    return [
        invoice for invoice in INVOICES.values()
        if invoice["owner_id"] == user["id"] and _visible_invoice(invoice, info.context)
    ]


def _resolve_invoice_customer(invoice: Invoice, info: Any) -> Customer | None:
    if not _visible_invoice(invoice, info.context, "nested"):
        return None
    return CUSTOMERS[invoice["customer_id"]]


def _resolve_invoice_owner(invoice: Invoice, info: Any) -> User:
    owner = next(user for user in USERS.values() if user["id"] == invoice["owner_id"])
    return owner


def _resolve_restricted_invoice_field(invoice: Invoice, info: Any, field: str) -> str | None:
    if not _field_access_allowed(invoice, info.context):
        return None
    return invoice[field]


def _resolve_confidential_code(invoice: Invoice, info: Any) -> str | None:
    config = info.context.get("config")
    if _mutant_enabled(config, "BOPLA"):
        return invoice["confidential_code"]
    return None


def _resolve_customer_email(customer: Customer, info: Any) -> str | None:
    return _resolve_customer_private_field(customer, info, "email")


def _resolve_customer_tax_id(customer: Customer, info: Any) -> str | None:
    return _resolve_customer_private_field(customer, info, "tax_id")


def _resolve_customer_private_field(customer: Customer, info: Any, field: str) -> str | None:
    if _mutant_enabled(info.context.get("config"), "BOPLA"):
        return customer[field]
    user = info.context.get("user")
    owns_customer = user is not None and any(
        invoice["customer_id"] == customer["id"] and invoice["owner_id"] == user["id"]
        for invoice in INVOICES.values()
    )
    return customer[field] if owns_customer else None


def _build_context(identity: str, config: Mapping[str, Any] | None) -> dict[str, Any]:
    normalized_identity = normalize_identity(identity)
    user = None if normalized_identity == "anonymous" else identity_user(normalized_identity)
    return {"user": user, "identity": normalized_identity, "config": config or {}}


_SCHEMA.type_map["Query"].fields["me"].resolve = _resolve_me
_SCHEMA.type_map["Query"].fields["invoice"].resolve = _resolve_invoice
_SCHEMA.type_map["Query"].fields["invoices"].resolve = _resolve_invoices
_SCHEMA.type_map["Query"].fields["customer"].resolve = _resolve_customer
_SCHEMA.type_map["User"].fields["invoices"].resolve = _resolve_user_invoices
_SCHEMA.type_map["Invoice"].fields["owner"].resolve = _resolve_invoice_owner
_SCHEMA.type_map["Invoice"].fields["ownerId"].resolve = lambda invoice, _info: invoice["owner_id"]
_SCHEMA.type_map["Invoice"].fields["customer"].resolve = _resolve_invoice_customer
_SCHEMA.type_map["Invoice"].fields["internalNotes"].resolve = lambda obj, info: _resolve_restricted_invoice_field(obj, info, "internal_notes")
_SCHEMA.type_map["Invoice"].fields["paymentReference"].resolve = lambda obj, info: _resolve_restricted_invoice_field(obj, info, "payment_reference")
_SCHEMA.type_map["Invoice"].fields["confidentialCode"].resolve = _resolve_confidential_code
_SCHEMA.type_map["Customer"].fields["email"].resolve = _resolve_customer_email
_SCHEMA.type_map["Customer"].fields["taxId"].resolve = _resolve_customer_tax_id


def execute_graphql(
    query: str,
    identity: str,
    config: Any,
    variables: Mapping[str, object] | None = None,
) -> dict[str, Any]:
    """Compatibility adapter returning the legacy data/errors/status mapping."""
    from .runner import execute_graphql as execute_with_contract

    # Preserve historical title-case aliases only at this legacy boundary.
    legacy_identity = identity.casefold() if isinstance(identity, str) else identity
    response = execute_with_contract(query, legacy_identity, config, variables)
    errors = [error.message for error in response.errors]
    status = "error" if errors and response.data is None else "partial" if errors else "success"
    return {"data": response.data, "errors": errors, "status": status}

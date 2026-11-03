"""Deterministic in-memory GraphLens fixture data."""

from __future__ import annotations

from typing import TypedDict


class User(TypedDict):
    id: str
    name: str
    identity: str


class Customer(TypedDict):
    id: str
    name: str
    email: str
    tax_id: str


class Invoice(TypedDict):
    id: str
    number: str
    owner_id: str
    amount: float
    currency: str
    status: str
    internal_notes: str
    payment_reference: str
    customer_id: str


USERS: dict[str, User] = {
    "alice": {"id": "user-alice", "name": "Alice", "identity": "alice"},
    "bob": {"id": "user-bob", "name": "Bob", "identity": "bob"},
}

CUSTOMERS: dict[str, Customer] = {
    "customer-alice": {
        "id": "customer-alice", "name": "Alice Cooper",
        "email": "alice.customer@example.test", "tax_id": "ALICE-TAX-001",
    },
    "customer-bob": {
        "id": "customer-bob", "name": "Bob Builder",
        "email": "bob.customer@example.test", "tax_id": "BOB-TAX-002",
    },
}

INVOICES: dict[str, Invoice] = {
    "invoice-alice-001": {
        "id": "invoice-alice-001", "number": "INV-ALICE-001", "owner_id": "user-alice",
        "amount": 1250.00, "currency": "USD", "status": "PAID",
        "internal_notes": "Priority account; renewal discussion pending.",
        "payment_reference": "PAY-ALICE-SECRET-001", "customer_id": "customer-alice",
    },
    "invoice-alice-002": {
        "id": "invoice-alice-002", "number": "INV-ALICE-002", "owner_id": "user-alice",
        "amount": 89.50, "currency": "USD", "status": "OPEN",
        "internal_notes": "Discount approved by finance.",
        "payment_reference": "PAY-ALICE-SECRET-002", "customer_id": "customer-alice",
    },
    "invoice-bob-001": {
        "id": "invoice-bob-001", "number": "INV-BOB-001", "owner_id": "user-bob",
        "amount": 640.00, "currency": "USD", "status": "OVERDUE",
        "internal_notes": "Contact customer before escalation.",
        "payment_reference": "PAY-BOB-SECRET-001", "customer_id": "customer-bob",
    },
}


def identity_user(identity: str | None) -> User | None:
    """Resolve a synthetic identity, accepting names and ``user-`` IDs."""
    if not isinstance(identity, str):
        return None
    key = identity.strip().casefold().removeprefix("user-")
    return USERS.get(key)

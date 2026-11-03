"""Deterministic T01–T12 authorization corpus using the integration contract."""

from dataclasses import dataclass
from enum import Enum
from typing import Final, Literal


Identity = Literal["alice", "bob", "anonymous"]


class Category(str, Enum):
    ROOT_BOLA = "root_bola"
    NESTED_BOLA = "nested_bola"
    PROPERTY_BOPLA = "property_bopla"
    AUTHENTICATION = "authentication"


class ExpectedOutcome(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    INCONCLUSIVE = "inconclusive"


@dataclass(frozen=True, slots=True)
class Target:
    """Machine-readable object/property under test."""

    resource_type: str
    resource_id: str | None
    object_path: tuple[str, ...] = ()
    property_name: str | None = None
    is_collection: bool = False
    collection_field: str | None = None


@dataclass(frozen=True, slots=True)
class TestCase:
    test_id: str
    category: Category
    operation_name: str
    operation: str
    variables: tuple[tuple[str, str], ...]
    identity: Identity
    target: Target
    expected_outcome: ExpectedOutcome
    evidence_requirements: tuple[str, ...]
    rationale: str

    @property
    def expected_policy_behavior(self) -> ExpectedOutcome:
        """Return policy intent; it is not an observed benchmark verdict."""
        return self.expected_outcome

    def variable_map(self) -> dict[str, str]:
        return dict(self.variables)


def _invoice_target(invoice_id: str, *, path: tuple[str, ...] = (), property_name: str | None = None) -> Target:
    return Target("invoice", invoice_id, object_path=path, property_name=property_name)


TEST_CASES: Final[tuple[TestCase, ...]] = (
    TestCase("T01", Category.ROOT_BOLA, "T01AliceReadsOwnInvoice", """query T01AliceReadsOwnInvoice($id: ID!) { invoice(id: $id) { id ownerId amount } }""", (("id", "invoice-alice-001"),), "alice", _invoice_target("invoice-alice-001"), ExpectedOutcome.ALLOW, ("returned invoice id", "owner id matches Alice"), "Positive control: Alice reads ordinary fields on her invoice."),
    TestCase("T02", Category.ROOT_BOLA, "T02BobReadsAlicesInvoice", """query T02BobReadsAlicesInvoice($id: ID!) { invoice(id: $id) { id ownerId amount } }""", (("id", "invoice-alice-001"),), "bob", _invoice_target("invoice-alice-001"), ExpectedOutcome.DENY, ("requested invoice id", "no Alice invoice data disclosed", "authorization error or null result evidence"), "Milestone case: Bob must not read Alice's invoice at the root resolver."),
    TestCase("T03", Category.ROOT_BOLA, "T03BobReadsOwnInvoice", """query T03BobReadsOwnInvoice($id: ID!) { invoice(id: $id) { id ownerId amount } }""", (("id", "invoice-bob-001"),), "bob", _invoice_target("invoice-bob-001"), ExpectedOutcome.ALLOW, ("returned invoice id", "owner id matches Bob"), "Positive control: Bob can read his own invoice."),
    TestCase("T04", Category.AUTHENTICATION, "T04AnonymousListsInvoices", """query T04AnonymousListsInvoices { invoices { id ownerId } }""", (), "anonymous", Target("invoice", None, is_collection=True, collection_field="invoices"), ExpectedOutcome.INCONCLUSIVE, ("collection response or GraphQL errors", "fixture invoice ids if returned", "reason no per-object decision can be established"), "An empty or rejected collection query cannot establish an object-level decision."),
    TestCase("T05", Category.NESTED_BOLA, "T05AliceReadsOwnInvoiceCustomer", """query T05AliceReadsOwnInvoiceCustomer($id: ID!) { customer(id: $id) { id name } }""", (("id", "customer-alice"),), "alice", Target("customer", "customer-alice"), ExpectedOutcome.ALLOW, ("returned customer id", "customer name returned"), "Positive control for nested authorization through Alice's linked invoice."),
    TestCase("T06", Category.NESTED_BOLA, "T06BobReadsAlicesInvoiceCustomer", """query T06BobReadsAlicesInvoiceCustomer($id: ID!) { customer(id: $id) { id name } }""", (("id", "customer-alice"),), "bob", Target("customer", "customer-alice"), ExpectedOutcome.DENY, ("requested customer id", "no Alice customer data disclosed", "authorization error or null result evidence"), "A non-owner must not resolve a customer linked to Alice's invoice."),
    TestCase("T07", Category.NESTED_BOLA, "T07BobReadsOwnInvoiceCustomer", """query T07BobReadsOwnInvoiceCustomer($id: ID!) { customer(id: $id) { id name } }""", (("id", "customer-bob"),), "bob", Target("customer", "customer-bob"), ExpectedOutcome.ALLOW, ("returned customer id", "customer name returned"), "Positive control for nested access through Bob's linked invoice."),
    TestCase("T08", Category.AUTHENTICATION, "T08AnonymousReadsAlicesInvoiceCustomer", """query T08AnonymousReadsAlicesInvoiceCustomer($id: ID!) { customer(id: $id) { id name } }""", (("id", "customer-alice"),), "anonymous", Target("customer", "customer-alice"), ExpectedOutcome.DENY, ("requested customer id", "no Alice customer data disclosed", "authentication denial evidenced by a null customer result or structured authorization error"), "Anonymous callers may not resolve a customer protected by its linked invoice."),
    TestCase("T09", Category.PROPERTY_BOPLA, "T09AliceReadsOwnInternalNotes", """query T09AliceReadsOwnInternalNotes($id: ID!) { invoice(id: $id) { id ownerId internalNotes } }""", (("id", "invoice-alice-001"),), "alice", _invoice_target("invoice-alice-001", property_name="internalNotes"), ExpectedOutcome.ALLOW, ("returned invoice id", "owner id matches Alice", "internalNotes field is present"), "Positive control: owner may read their own internal notes under this fixture policy."),
    TestCase("T10", Category.PROPERTY_BOPLA, "T10BobReadsSharedInvoiceInternalNotes", """query T10BobReadsSharedInvoiceInternalNotes($id: ID!) { invoice(id: $id) { id ownerId internalNotes } }""", (("id", "invoice-alice-002"),), "bob", _invoice_target("invoice-alice-002", property_name="internalNotes"), ExpectedOutcome.DENY, ("shared parent invoice is returned to Bob", "internalNotes value is not disclosed", "selected internalNotes field is null without a relevant GraphQL error"), "Bob is an approved viewer of Alice's shared invoice but must not read its owner-only internal notes."),
    TestCase("T11", Category.AUTHENTICATION, "T11AnonymousReadsAlicesInvoice", """query T11AnonymousReadsAlicesInvoice($id: ID!) { invoice(id: $id) { id ownerId amount } }""", (("id", "invoice-alice-001"),), "anonymous", _invoice_target("invoice-alice-001"), ExpectedOutcome.DENY, ("requested invoice id", "no Alice invoice data disclosed", "authentication denial evidenced by a null invoice result or structured authorization error"), "Anonymous callers must not read Alice's invoice."),
    TestCase("T12", Category.PROPERTY_BOPLA, "T12AliceReadsOwnConfidentialCode", """query T12AliceReadsOwnConfidentialCode($id: ID!) { invoice(id: $id) { id confidentialCode } }""", (("id", "invoice-alice-001"),), "alice", _invoice_target("invoice-alice-001", property_name="confidentialCode"), ExpectedOutcome.DENY, ("requested invoice id", "confidentialCode value not disclosed", "field error or null-field evidence"), "Fixture policy denies confidentialCode even to the invoice owner."),
)


# Approved behavioral kill map for the independently seeded mutants. These
# pairs describe what each mutant is intended to break; the benchmark gate
# derives expected cells by intersecting this map with each configuration.
MUTANT_KILL_MAP: Final[dict[str, frozenset[str]]] = {
    "M1": frozenset({"T02"}),
    "M2": frozenset({"T06"}),
    "M3": frozenset({"T10", "T12"}),
    "M4": frozenset({"T04", "T08", "T11"}),
}

def get_test_corpus() -> tuple[TestCase, ...]:
    """Return T01–T12 in stable order for the evaluator."""
    return TEST_CASES

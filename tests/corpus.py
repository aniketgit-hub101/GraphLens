"""Deterministic T01–T12 authorization corpus using the integration contract."""

from dataclasses import dataclass
from enum import Enum
from typing import Final, Literal


Identity = Literal["alice", "bob", "anonymous"]


class Category(str, Enum):
    ROOT_BOLA = "root_bola"
    NESTED_BOLA = "nested_bola"
    PROPERTY_BOPLA = "property_bopla"


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
    TestCase("T04", Category.ROOT_BOLA, "T04AnonymousListsInvoices", """query T04AnonymousListsInvoices { invoices { id ownerId } }""", (), "anonymous", Target("invoice", None, is_collection=True), ExpectedOutcome.INCONCLUSIVE, ("collection response or GraphQL errors", "fixture invoice ids if returned", "reason no per-object decision can be established"), "An empty or rejected collection query cannot establish an object-level decision."),
    TestCase("T05", Category.NESTED_BOLA, "T05AliceReadsOwnInvoiceCustomer", """query T05AliceReadsOwnInvoiceCustomer($id: ID!) { invoice(id: $id) { id customer { id name } } }""", (("id", "invoice-alice-001"),), "alice", _invoice_target("invoice-alice-001", path=("customer",)), ExpectedOutcome.ALLOW, ("parent invoice id", "nested customer id and name", "parent owner id matches Alice"), "Positive control for nested traversal on an owned invoice."),
    TestCase("T06", Category.NESTED_BOLA, "T06BobReadsAlicesInvoiceCustomer", """query T06BobReadsAlicesInvoiceCustomer($id: ID!) { invoice(id: $id) { id customer { id name } } }""", (("id", "invoice-alice-001"),), "bob", _invoice_target("invoice-alice-001", path=("customer",)), ExpectedOutcome.DENY, ("parent invoice id", "no nested customer data disclosed", "authorization error or null result evidence"), "A nested resolver must preserve the parent invoice ownership boundary."),
    TestCase("T07", Category.NESTED_BOLA, "T07BobReadsOwnInvoiceCustomer", """query T07BobReadsOwnInvoiceCustomer($id: ID!) { invoice(id: $id) { id customer { id name } } }""", (("id", "invoice-bob-001"),), "bob", _invoice_target("invoice-bob-001", path=("customer",)), ExpectedOutcome.ALLOW, ("parent invoice id", "nested customer id and name", "parent owner id matches Bob"), "Positive control for nested access on Bob's invoice."),
    TestCase("T08", Category.NESTED_BOLA, "T08AnonymousReadsAlicesInvoiceCustomer", """query T08AnonymousReadsAlicesInvoiceCustomer($id: ID!) { invoice(id: $id) { id customer { id name } } }""", (("id", "invoice-alice-001"),), "anonymous", _invoice_target("invoice-alice-001", path=("customer",)), ExpectedOutcome.DENY, ("requested parent invoice id", "no nested customer data disclosed", "authentication or authorization error evidence"), "Anonymous callers may not traverse a protected invoice."),
    TestCase("T09", Category.PROPERTY_BOPLA, "T09AliceReadsOwnInternalNotes", """query T09AliceReadsOwnInternalNotes($id: ID!) { invoice(id: $id) { id ownerId internalNotes } }""", (("id", "invoice-alice-001"),), "alice", _invoice_target("invoice-alice-001", property_name="internalNotes"), ExpectedOutcome.ALLOW, ("returned invoice id", "owner id matches Alice", "internalNotes field is present"), "Positive control: owner may read their own internal notes under this fixture policy."),
    TestCase("T10", Category.PROPERTY_BOPLA, "T10BobReadsAlicesInternalNotes", """query T10BobReadsAlicesInternalNotes($id: ID!) { invoice(id: $id) { id internalNotes } }""", (("id", "invoice-alice-001"),), "bob", _invoice_target("invoice-alice-001", property_name="internalNotes"), ExpectedOutcome.DENY, ("requested invoice id", "internalNotes value not disclosed", "field error or null-field evidence"), "Non-owner must not read the restricted property."),
    TestCase("T11", Category.PROPERTY_BOPLA, "T11AnonymousReadsAlicesInternalNotes", """query T11AnonymousReadsAlicesInternalNotes($id: ID!) { invoice(id: $id) { id internalNotes } }""", (("id", "invoice-alice-001"),), "anonymous", _invoice_target("invoice-alice-001", property_name="internalNotes"), ExpectedOutcome.DENY, ("requested invoice id", "internalNotes value not disclosed", "authentication or authorization error evidence"), "Anonymous caller must not read a restricted property."),
    TestCase("T12", Category.PROPERTY_BOPLA, "T12AliceReadsOwnConfidentialCode", """query T12AliceReadsOwnConfidentialCode($id: ID!) { invoice(id: $id) { id confidentialCode } }""", (("id", "invoice-alice-001"),), "alice", _invoice_target("invoice-alice-001", property_name="confidentialCode"), ExpectedOutcome.DENY, ("requested invoice id", "confidentialCode value not disclosed", "field error or null-field evidence"), "Fixture policy denies confidentialCode even to the invoice owner."),
)


def get_test_corpus() -> tuple[TestCase, ...]:
    """Return T01–T12 in stable order for the evaluator."""
    return TEST_CASES

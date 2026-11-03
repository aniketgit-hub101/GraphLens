"""Deterministic GraphLens authorization query corpus.

These definitions describe policy expectations, not measured benchmark results.
The API adapter can consume them once the execution interface is agreed.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Final


class Identity(str, Enum):
    ALICE = "alice"
    BOB = "bob"
    ANONYMOUS = "anonymous"


class ExpectedOutcome(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    INCONCLUSIVE = "inconclusive"


class Category(str, Enum):
    ROOT_BOLA = "root_bola"
    NESTED_BOLA = "nested_bola"
    PROPERTY_BOPLA = "property_bopla"


@dataclass(frozen=True, slots=True)
class TestCase:
    id: str
    category: Category
    operation_name: str
    query: str
    variables: tuple[tuple[str, str], ...]
    identity: Identity
    target_resource: str
    expected_outcome: ExpectedOutcome
    evidence_requirements: tuple[str, ...]
    rationale: str

    def variable_map(self) -> dict[str, str]:
        """Return a fresh variables mapping suitable for a GraphQL executor."""
        return dict(self.variables)


# Fixed synthetic fixture contract:
#   invoice-alice-001 belongs to Alice; invoice-bob-001 belongs to Bob.
#   Each invoice has customer { id, name }, internalNotes and confidentialCode.
#   Owner access is allowed for ordinary fields and internalNotes. The
#   confidentialCode property is denied to all three identities.
# These IDs and property rules are test data; they do not claim API behavior.
TEST_CASES: Final[tuple[TestCase, ...]] = (
    TestCase(
        id="T01",
        category=Category.ROOT_BOLA,
        operation_name="T01AliceReadsOwnInvoice",
        query="""query T01AliceReadsOwnInvoice($id: ID!) {
  invoice(id: $id) { id ownerId amount }
}""",
        variables=(("id", "invoice-alice-001"),),
        identity=Identity.ALICE,
        target_resource="invoice-alice-001",
        expected_outcome=ExpectedOutcome.ALLOW,
        evidence_requirements=("returned invoice id", "owner id matches Alice"),
        rationale="Positive control: an owner reads ordinary fields on their invoice.",
    ),
    TestCase(
        id="T02",
        category=Category.ROOT_BOLA,
        operation_name="T02BobReadsAlicesInvoice",
        query="""query T02BobReadsAlicesInvoice($id: ID!) {
  invoice(id: $id) { id ownerId amount }
}""",
        variables=(("id", "invoice-alice-001"),),
        identity=Identity.BOB,
        target_resource="invoice-alice-001",
        expected_outcome=ExpectedOutcome.DENY,
        evidence_requirements=("requested invoice id", "no Alice invoice data disclosed", "authorization error or null result evidence"),
        rationale="Milestone case: Bob must not read Alice's invoice at the root resolver.",
    ),
    TestCase(
        id="T03",
        category=Category.ROOT_BOLA,
        operation_name="T03BobReadsOwnInvoice",
        query="""query T03BobReadsOwnInvoice($id: ID!) {
  invoice(id: $id) { id ownerId amount }
}""",
        variables=(("id", "invoice-bob-001"),),
        identity=Identity.BOB,
        target_resource="invoice-bob-001",
        expected_outcome=ExpectedOutcome.ALLOW,
        evidence_requirements=("returned invoice id", "owner id matches Bob"),
        rationale="Positive control: the BOLA denial must not reject the rightful owner.",
    ),
    TestCase(
        id="T04",
        category=Category.ROOT_BOLA,
        operation_name="T04AnonymousListsInvoices",
        query="""query T04AnonymousListsInvoices {
  invoices { id ownerId }
}""",
        variables=(),
        identity=Identity.ANONYMOUS,
        target_resource="invoice collection (no single target id)",
        expected_outcome=ExpectedOutcome.INCONCLUSIVE,
        evidence_requirements=("collection response or GraphQL errors", "fixture invoice ids if any are returned", "reason the response cannot establish a per-object authorization decision"),
        rationale="An empty or schema-rejected list cannot identify a specific object-level decision.",
    ),
    TestCase(
        id="T05",
        category=Category.NESTED_BOLA,
        operation_name="T05AliceReadsOwnInvoiceCustomer",
        query="""query T05AliceReadsOwnInvoiceCustomer($id: ID!) {
  invoice(id: $id) { id customer { id name } }
}""",
        variables=(("id", "invoice-alice-001"),),
        identity=Identity.ALICE,
        target_resource="invoice-alice-001.customer",
        expected_outcome=ExpectedOutcome.ALLOW,
        evidence_requirements=("parent invoice id", "nested customer id and name", "parent owner id matches Alice"),
        rationale="Positive control for nested resolver traversal on an owned invoice.",
    ),
    TestCase(
        id="T06",
        category=Category.NESTED_BOLA,
        operation_name="T06BobReadsAlicesInvoiceCustomer",
        query="""query T06BobReadsAlicesInvoiceCustomer($id: ID!) {
  invoice(id: $id) { id customer { id name } }
}""",
        variables=(("id", "invoice-alice-001"),),
        identity=Identity.BOB,
        target_resource="invoice-alice-001.customer",
        expected_outcome=ExpectedOutcome.DENY,
        evidence_requirements=("parent invoice id", "no nested customer data disclosed", "authorization error or null result evidence"),
        rationale="A nested resolver must preserve the parent's ownership boundary.",
    ),
    TestCase(
        id="T07",
        category=Category.NESTED_BOLA,
        operation_name="T07BobReadsOwnInvoiceCustomer",
        query="""query T07BobReadsOwnInvoiceCustomer($id: ID!) {
  invoice(id: $id) { id customer { id name } }
}""",
        variables=(("id", "invoice-bob-001"),),
        identity=Identity.BOB,
        target_resource="invoice-bob-001.customer",
        expected_outcome=ExpectedOutcome.ALLOW,
        evidence_requirements=("parent invoice id", "nested customer id and name", "parent owner id matches Bob"),
        rationale="Positive control for the nested-object ownership check.",
    ),
    TestCase(
        id="T08",
        category=Category.NESTED_BOLA,
        operation_name="T08AnonymousReadsAlicesInvoiceCustomer",
        query="""query T08AnonymousReadsAlicesInvoiceCustomer($id: ID!) {
  invoice(id: $id) { id customer { id name } }
}""",
        variables=(("id", "invoice-alice-001"),),
        identity=Identity.ANONYMOUS,
        target_resource="invoice-alice-001.customer",
        expected_outcome=ExpectedOutcome.DENY,
        evidence_requirements=("requested parent invoice id", "no nested customer data disclosed", "authentication or authorization error evidence"),
        rationale="Anonymous callers may not traverse a protected invoice to its customer.",
    ),
    TestCase(
        id="T09",
        category=Category.PROPERTY_BOPLA,
        operation_name="T09AliceReadsOwnInternalNotes",
        query="""query T09AliceReadsOwnInternalNotes($id: ID!) {
  invoice(id: $id) { id ownerId internalNotes }
}""",
        variables=(("id", "invoice-alice-001"),),
        identity=Identity.ALICE,
        target_resource="invoice-alice-001.internalNotes",
        expected_outcome=ExpectedOutcome.ALLOW,
        evidence_requirements=("returned invoice id", "owner id matches Alice", "internalNotes field is present"),
        rationale="Positive control: the fixture policy permits an owner to read their own internal notes.",
    ),
    TestCase(
        id="T10",
        category=Category.PROPERTY_BOPLA,
        operation_name="T10BobReadsAlicesInternalNotes",
        query="""query T10BobReadsAlicesInternalNotes($id: ID!) {
  invoice(id: $id) { id internalNotes }
}""",
        variables=(("id", "invoice-alice-001"),),
        identity=Identity.BOB,
        target_resource="invoice-alice-001.internalNotes",
        expected_outcome=ExpectedOutcome.DENY,
        evidence_requirements=("requested invoice id", "internalNotes value is not disclosed", "field error or null-field evidence"),
        rationale="A non-owner must not read the restricted property even if the root object is resolved.",
    ),
    TestCase(
        id="T11",
        category=Category.PROPERTY_BOPLA,
        operation_name="T11AnonymousReadsAlicesInternalNotes",
        query="""query T11AnonymousReadsAlicesInternalNotes($id: ID!) {
  invoice(id: $id) { id internalNotes }
}""",
        variables=(("id", "invoice-alice-001"),),
        identity=Identity.ANONYMOUS,
        target_resource="invoice-alice-001.internalNotes",
        expected_outcome=ExpectedOutcome.DENY,
        evidence_requirements=("requested invoice id", "internalNotes value is not disclosed", "authentication or authorization error evidence"),
        rationale="An anonymous caller must not read a restricted property.",
    ),
    TestCase(
        id="T12",
        category=Category.PROPERTY_BOPLA,
        operation_name="T12AliceReadsOwnConfidentialCode",
        query="""query T12AliceReadsOwnConfidentialCode($id: ID!) {
  invoice(id: $id) { id confidentialCode }
}""",
        variables=(("id", "invoice-alice-001"),),
        identity=Identity.ALICE,
        target_resource="invoice-alice-001.confidentialCode",
        expected_outcome=ExpectedOutcome.DENY,
        evidence_requirements=("requested invoice id", "confidentialCode value is not disclosed", "field error or null-field evidence"),
        rationale="The fixture policy treats confidentialCode as unavailable even to the invoice owner.",
    ),
)

CASES_BY_ID: Final[dict[str, TestCase]] = {case.id: case for case in TEST_CASES}

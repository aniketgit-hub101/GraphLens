"""Independent API authorization regression tests (run with unittest)."""

import unittest

from api import execute_graphql


class ExecuteGraphqlTests(unittest.TestCase):
    def test_alice_can_read_owned_invoice_and_private_fields(self):
        result = execute_graphql(
            '{ invoice(id: "inv-alice-001") { number internalNotes paymentReference customer { name email taxId } } }',
            "Alice", {},
        )
        self.assertEqual(result["status"], "success")
        invoice = result["data"]["invoice"]
        self.assertEqual(invoice["number"], "INV-ALICE-001")
        self.assertIsNotNone(invoice["internalNotes"])
        self.assertEqual(invoice["customer"]["email"], "alice.customer@example.test")

    def test_bob_cannot_read_alice_invoice_or_nested_customer(self):
        result = execute_graphql(
            '{ invoice(id: "inv-alice-001") { id customer { id email } } customer(id: "customer-alice") { id } }',
            "Bob", {},
        )
        self.assertEqual(result["status"], "success")
        self.assertIsNone(result["data"]["invoice"])
        self.assertIsNone(result["data"]["customer"])

    def test_anonymous_cannot_list_or_read_protected_invoices(self):
        result = execute_graphql(
            '{ invoices { id } invoice(id: "inv-alice-001") { id } }', "Anonymous", {},
        )
        self.assertEqual(result["data"]["invoices"], [])
        self.assertIsNone(result["data"]["invoice"])

    def test_user_list_is_owner_scoped_and_nested_private_data_is_scoped(self):
        result = execute_graphql(
            '{ me { name invoices { id customer { name email } } } }', "Bob", {},
        )
        self.assertEqual([item["id"] for item in result["data"]["me"]["invoices"]], ["inv-bob-001"])
        self.assertEqual(result["data"]["me"]["invoices"][0]["customer"]["email"], "bob.customer@example.test")

    def test_bola_and_bopla_mutants_can_be_activated(self):
        query = '{ invoice(id: "inv-alice-001") { internalNotes paymentReference customer { email } } }'
        result = execute_graphql(query, "Bob", {"mutants": ["BOLA", "BOPLA"]})
        self.assertIsNotNone(result["data"]["invoice"])
        self.assertIsNotNone(result["data"]["invoice"]["internalNotes"])
        self.assertIsNotNone(result["data"]["invoice"]["customer"]["email"])

    def test_root_bola_is_independently_configurable(self):
        result = execute_graphql('{ invoice(id: "inv-alice-001") { id } }', "Bob", {"mutants": ["ROOT_BOLA"]})
        self.assertEqual(result["data"]["invoice"]["id"], "inv-alice-001")

    def test_nested_bola_is_independently_configurable(self):
        result = execute_graphql('{ customer(id: "customer-alice") { id name } }', "Bob", {"mutants": ["NESTED_BOLA"]})
        self.assertEqual(result["data"]["customer"]["id"], "customer-alice")

    def test_auth_bypass_allows_anonymous_protected_access(self):
        result = execute_graphql('{ invoice(id: "inv-alice-001") { id internalNotes } }', "Anonymous", {"mutants": ["AUTH_BYPASS"]})
        self.assertEqual(result["data"]["invoice"]["id"], "inv-alice-001")
        self.assertIsNotNone(result["data"]["invoice"]["internalNotes"])

    def test_graphql_errors_have_consistent_shape(self):
        result = execute_graphql("{ fieldThatDoesNotExist }", "Alice", {})
        self.assertEqual(set(result), {"data", "errors", "status"})
        self.assertEqual(result["status"], "error")
        self.assertTrue(result["errors"])


if __name__ == "__main__":
    unittest.main()

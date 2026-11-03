"""Independent API authorization regression tests (run with unittest)."""

import unittest

from api import execute_graphql
from api.runner import execute_graphql as execute_engine_graphql
from engine.contracts import Configuration
from mutants.config import CONFIGS_BY_ID


class ExecuteGraphqlTests(unittest.TestCase):
    def test_alice_can_read_owned_invoice_and_private_fields(self):
        result = execute_graphql(
            '{ invoice(id: "invoice-alice-001") { number internalNotes paymentReference customer { name email taxId } } }',
            "Alice", CONFIGS_BY_ID["C0"],
        )
        self.assertEqual(result["status"], "success")
        invoice = result["data"]["invoice"]
        self.assertEqual(invoice["number"], "INV-ALICE-001")
        self.assertIsNotNone(invoice["internalNotes"])
        self.assertEqual(invoice["customer"]["email"], "alice.customer@example.test")

    def test_bob_cannot_read_alice_invoice_or_nested_customer(self):
        result = execute_graphql(
            '{ invoice(id: "invoice-alice-001") { id customer { id email } } customer(id: "customer-alice") { id } }',
            "Bob", CONFIGS_BY_ID["C0"],
        )
        self.assertEqual(result["status"], "success")
        self.assertIsNone(result["data"]["invoice"])
        self.assertIsNone(result["data"]["customer"])

    def test_anonymous_cannot_list_or_read_protected_invoices(self):
        result = execute_graphql(
            '{ invoices { id } invoice(id: "invoice-alice-001") { id } }', "Anonymous", CONFIGS_BY_ID["C0"],
        )
        self.assertEqual(result["data"]["invoices"], [])
        self.assertIsNone(result["data"]["invoice"])

    def test_user_list_is_owner_scoped_and_nested_private_data_is_scoped(self):
        result = execute_graphql(
            '{ me { name invoices { id customer { name email } } } }', "Bob", CONFIGS_BY_ID["C0"],
        )
        self.assertEqual([item["id"] for item in result["data"]["me"]["invoices"]], ["invoice-bob-001"])
        self.assertEqual(result["data"]["me"]["invoices"][0]["customer"]["email"], "bob.customer@example.test")

    def test_bola_and_bopla_mutants_can_be_activated(self):
        query = '{ invoice(id: "invoice-alice-001") { internalNotes paymentReference customer { email } } }'
        result = execute_graphql(query, "Bob", CONFIGS_BY_ID["C5"])
        self.assertIsNotNone(result["data"]["invoice"])
        self.assertIsNotNone(result["data"]["invoice"]["internalNotes"])
        self.assertIsNotNone(result["data"]["invoice"]["customer"]["email"])

    def test_root_bola_is_independently_configurable(self):
        result = execute_graphql('{ invoice(id: "invoice-alice-001") { id } }', "Bob", CONFIGS_BY_ID["C1"])
        self.assertEqual(result["data"]["invoice"]["id"], "invoice-alice-001")

    def test_nested_bola_is_independently_configurable(self):
        result = execute_graphql('{ customer(id: "customer-alice") { id name } }', "Bob", CONFIGS_BY_ID["C2"])
        self.assertEqual(result["data"]["customer"]["id"], "customer-alice")

    def test_auth_bypass_allows_anonymous_protected_access(self):
        result = execute_graphql('{ invoice(id: "invoice-alice-001") { id internalNotes } invoices { id ownerId } }', "Anonymous", CONFIGS_BY_ID["C4"])
        self.assertEqual(result["data"]["invoice"]["id"], "invoice-alice-001")
        self.assertIsNone(result["data"]["invoice"]["internalNotes"])
        self.assertEqual(len(result["data"]["invoices"]), 3)

    def test_m4_does_not_bypass_authenticated_bob_object_authorization(self):
        response = execute_graphql('{ invoice(id: "invoice-alice-001") { id } }', "Bob", CONFIGS_BY_ID["C4"])
        self.assertIsNone(response["data"]["invoice"])

    def test_m1_is_limited_to_root_invoice_and_not_collection_queries(self):
        baseline = execute_graphql("{ invoices { id } }", "Bob", CONFIGS_BY_ID["C0"])
        root_mutant = execute_graphql("{ invoices { id } }", "Bob", CONFIGS_BY_ID["C1"])
        self.assertEqual(baseline["data"], root_mutant["data"])
        self.assertEqual(["invoice-alice-002", "invoice-bob-001"], [row["id"] for row in root_mutant["data"]["invoices"]])

    def test_bob_can_read_shared_parent_but_not_internal_notes_without_m3(self):
        response = execute_engine_graphql(
            'query($id: ID!) { invoice(id: $id) { id ownerId internalNotes } }',
            "bob", CONFIGS_BY_ID["C0"], {"id": "invoice-alice-002"},
        )
        self.assertEqual(response.data["invoice"]["id"], "invoice-alice-002")
        self.assertEqual(response.data["invoice"]["ownerId"], "user-alice")
        self.assertIsNone(response.data["invoice"]["internalNotes"])

    def test_m3_exposes_shared_property_without_changing_parent_visibility(self):
        response = execute_engine_graphql(
            'query($id: ID!) { invoice(id: $id) { id ownerId internalNotes } }',
            "bob", CONFIGS_BY_ID["C3"], {"id": "invoice-alice-002"},
        )
        self.assertEqual(response.data["invoice"]["id"], "invoice-alice-002")
        self.assertEqual(response.data["invoice"]["internalNotes"], "Discount approved by finance.")

    def test_m4_does_not_leak_into_property_mutation_for_authenticated_users(self):
        response = execute_engine_graphql(
            'query($id: ID!) { invoice(id: $id) { id internalNotes } }',
            "bob", CONFIGS_BY_ID["C4"], {"id": "invoice-alice-002"},
        )
        self.assertIsNone(response.data["invoice"]["internalNotes"])

    def test_exact_c0_to_c5_mutant_activation_matrix(self):
        configs = [CONFIGS_BY_ID[f"C{i}"] for i in range(6)]
        root = [execute_engine_graphql('{ invoice(id: "invoice-alice-001") { id } }', "bob", config).data["invoice"] is not None for config in configs]
        nested = [execute_engine_graphql('{ customer(id: "customer-alice") { id } }', "bob", config).data["customer"] is not None for config in configs]
        notes = [execute_engine_graphql('{ invoice(id: "invoice-alice-002") { id internalNotes } }', "bob", config).data["invoice"]["internalNotes"] is not None for config in configs]
        anonymous = [len(execute_engine_graphql("{ invoices { id } }", "anonymous", config).data["invoices"]) > 0 for config in configs]
        self.assertEqual([False, True, False, False, False, True], root)
        self.assertEqual([False, False, True, False, False, True], nested)
        self.assertEqual([False, False, False, True, False, True], notes)
        self.assertEqual([False, False, False, False, True, True], anonymous)

    def test_t12_confidential_code_is_denied_to_owner_except_m3(self):
        from engine.integration import adapt_corpus
        from policies.evaluator import evaluate_policy
        case = next(item for item in adapt_corpus(__import__("tests.corpus", fromlist=["get_test_corpus"]).get_test_corpus()) if item.test_id == "T12")
        baseline = execute_engine_graphql(case.operation, case.identity, CONFIGS_BY_ID["C0"], case.variables)
        mutant = execute_engine_graphql(case.operation, case.identity, CONFIGS_BY_ID["C3"], case.variables)
        self.assertIsNone(baseline.data["invoice"]["confidentialCode"])
        self.assertEqual("CONF-ALICE-001", mutant.data["invoice"]["confidentialCode"])
        self.assertEqual("PASS", evaluate_policy(case.identity, case, baseline).verdict.value)
        self.assertEqual("POLICY_VIOLATION", evaluate_policy(case.identity, case, mutant).verdict.value)

    def test_graphql_errors_have_consistent_shape(self):
        result = execute_graphql("{ fieldThatDoesNotExist }", "Alice", CONFIGS_BY_ID["C0"])
        self.assertEqual(set(result), {"data", "errors", "status"})
        self.assertEqual(result["status"], "error")
        self.assertTrue(result["errors"])

    def test_engine_adapter_returns_structured_response_for_c0_identities(self):
        query = '{ invoice(id: "invoice-alice-001") { id ownerId amount } }'
        alice = execute_engine_graphql(query, "alice", CONFIGS_BY_ID["C0"])
        bob = execute_engine_graphql(query, "bob", CONFIGS_BY_ID["C0"])
        anonymous = execute_engine_graphql(query, "anonymous", CONFIGS_BY_ID["C0"])
        self.assertEqual(alice.data["invoice"]["id"], "invoice-alice-001")
        self.assertEqual(alice.data["invoice"]["ownerId"], "user-alice")
        self.assertIsNone(bob.data["invoice"])
        self.assertIsNone(anonymous.data["invoice"])
        self.assertEqual(alice.errors, ())

    def test_engine_m1_configuration_exposes_root_bola(self):
        config = CONFIGS_BY_ID["C1"]
        response = execute_engine_graphql('{ invoice(id: "invoice-alice-001") { id } }', "bob", config)
        self.assertEqual(response.data["invoice"]["id"], "invoice-alice-001")

    def test_engine_adapter_preserves_graphql_error_paths(self):
        response = execute_engine_graphql("{ missingField }", "alice", CONFIGS_BY_ID["C0"])
        self.assertIsNone(response.data)
        self.assertTrue(response.errors)
        self.assertTrue(response.errors[0].message)

    def test_engine_configuration_is_the_single_canonical_class(self):
        from mutants.config import Configuration as MutantConfiguration

        self.assertIs(MutantConfiguration, Configuration)
        self.assertIsInstance(CONFIGS_BY_ID["C0"], Configuration)

    def test_unknown_identity_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "unknown identity"):
            execute_engine_graphql("{ me { id } }", "mallory", CONFIGS_BY_ID["C0"])

    def test_canonical_identity_requires_exact_lowercase_identifier(self):
        from api.schema import normalize_identity
        for identity in ("alice", "bob", "anonymous"):
            self.assertEqual(identity, normalize_identity(identity))
        for identity in ("Alice", "ALICE", " alice", "alice ", "", "mallory"):
            with self.subTest(identity=identity), self.assertRaises(ValueError):
                normalize_identity(identity)
            with self.subTest(runner_identity=identity), self.assertRaises(ValueError):
                execute_engine_graphql("{ me { id } }", identity, CONFIGS_BY_ID["C0"])
        with self.assertRaises(TypeError):
            normalize_identity(None)
        # Title-case compatibility belongs to the legacy wrapper only.
        self.assertEqual("success", execute_graphql("{ me { id } }", "Alice", CONFIGS_BY_ID["C0"]) ["status"])

    def test_non_string_identity_is_rejected(self):
        with self.assertRaisesRegex(TypeError, "identity must be a string"):
            execute_engine_graphql("{ me { id } }", None, CONFIGS_BY_ID["C0"])

    def test_duplicate_mutants_are_rejected(self):
        malformed = {"configuration_id": "C1", "enabled_mutants": ["M1", "M1"]}
        with self.assertRaisesRegex(ValueError, "duplicate"):
            execute_engine_graphql("{ me { id } }", "alice", malformed)

    def test_unknown_mutant_is_rejected(self):
        malformed = {"configuration_id": "C1", "enabled_mutants": ["M9"]}
        with self.assertRaisesRegex(ValueError, "unknown mutant"):
            execute_engine_graphql("{ me { id } }", "alice", malformed)

    def test_mismatched_or_malformed_configuration_is_rejected(self):
        malformed = {"configuration_id": "C1", "enabled_mutants": []}
        with self.assertRaisesRegex(ValueError, "requires mutants"):
            execute_engine_graphql("{ me { id } }", "alice", malformed)
        with self.assertRaisesRegex(ValueError, "exactly"):
            execute_engine_graphql("{ me { id } }", "alice", {"mutants": []})

    def test_invalid_inputs_never_produce_a_graphql_pass_response(self):
        with self.assertRaises((TypeError, ValueError)):
            execute_engine_graphql('{ invoice(id: "invoice-alice-001") { id } }', "unknown", CONFIGS_BY_ID["C0"])


if __name__ == "__main__":
    unittest.main()

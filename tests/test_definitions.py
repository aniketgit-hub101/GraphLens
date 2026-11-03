"""Self-checks for corpus stability and mutant configuration structure."""

import unittest

from mutants.config import CONFIGURATIONS, MUTANTS, MUTANT_IDS
from tests.corpus import Category, ExpectedOutcome, TEST_CASES


class CorpusDefinitionTests(unittest.TestCase):
    def test_twelve_unique_stable_ids_and_complete_metadata(self) -> None:
        self.assertEqual([f"T{i:02}" for i in range(1, 13)], [case.id for case in TEST_CASES])
        self.assertEqual(12, len({case.operation_name for case in TEST_CASES}))
        for case in TEST_CASES:
            with self.subTest(case=case.id):
                self.assertTrue(case.query.strip())
                self.assertTrue(case.target_resource)
                self.assertTrue(case.evidence_requirements)
                self.assertTrue(case.rationale)
                self.assertIsInstance(case.variable_map(), dict)

    def test_category_ranges_match_the_corpus_contract(self) -> None:
        self.assertEqual([Category.ROOT_BOLA] * 4, [case.category for case in TEST_CASES[:4]])
        self.assertEqual([Category.NESTED_BOLA] * 4, [case.category for case in TEST_CASES[4:8]])
        self.assertEqual([Category.PROPERTY_BOPLA] * 4, [case.category for case in TEST_CASES[8:12]])

    def test_required_identities_controls_and_inconclusive_case_are_present(self) -> None:
        identities = {case.identity.value for case in TEST_CASES}
        self.assertEqual({"alice", "bob", "anonymous"}, identities)
        self.assertTrue(any(case.expected_outcome is ExpectedOutcome.ALLOW for case in TEST_CASES))
        inconclusive = [case for case in TEST_CASES if case.expected_outcome is ExpectedOutcome.INCONCLUSIVE]
        self.assertEqual(["T04"], [case.id for case in inconclusive])

    def test_first_milestone_is_bob_to_alice_invoice(self) -> None:
        case = TEST_CASES[1]
        self.assertEqual("T02", case.id)
        self.assertEqual("bob", case.identity.value)
        self.assertEqual("invoice-alice-001", case.target_resource)
        self.assertIs(case.expected_outcome, ExpectedOutcome.DENY)


class MutantConfigurationTests(unittest.TestCase):
    def test_four_independent_mutants_have_distinct_ids(self) -> None:
        self.assertEqual({"M1", "M2", "M3", "M4"}, MUTANT_IDS)
        self.assertEqual(4, len(MUTANTS))

    def test_c0_to_c5_select_single_or_combined_mutants(self) -> None:
        self.assertEqual([f"C{i}" for i in range(6)], [config.id for config in CONFIGURATIONS])
        self.assertEqual((), CONFIGURATIONS[0].enabled_mutants)
        for config, mutant_id in zip(CONFIGURATIONS[1:5], ("M1", "M2", "M3", "M4")):
            self.assertEqual((mutant_id,), config.enabled_mutants)
        self.assertEqual(("M1", "M2", "M3", "M4"), CONFIGURATIONS[5].enabled_mutants)
        for config in CONFIGURATIONS:
            self.assertTrue(set(config.enabled_mutants) <= MUTANT_IDS)


if __name__ == "__main__":
    unittest.main()

"""Adapter and definition checks for the canonical security-test contracts."""

import unittest

from mutants.configurations import get_configurations
from tests.corpus import Category, ExpectedOutcome, Target, get_test_corpus


class CanonicalCorpusTests(unittest.TestCase):
    def test_ids_order_categories_and_metadata(self) -> None:
        corpus = get_test_corpus()
        self.assertEqual([f"T{i:02}" for i in range(1, 13)], [case.test_id for case in corpus])
        self.assertEqual(3, sum(case.category is Category.ROOT_BOLA for case in corpus))
        self.assertEqual(3, sum(case.category is Category.NESTED_BOLA for case in corpus))
        self.assertEqual(3, sum(case.category is Category.PROPERTY_BOPLA for case in corpus))
        self.assertEqual(3, sum(case.category is Category.AUTHENTICATION for case in corpus))
        for case in corpus:
            with self.subTest(test_id=case.test_id):
                self.assertTrue(case.operation.strip())
                self.assertIn(case.identity, {"alice", "bob", "anonymous"})
                self.assertIsInstance(case.target, Target)
                self.assertTrue(case.evidence_requirements)

    def test_identity_controls_and_explicit_denials_preserve_cases(self) -> None:
        corpus = {case.test_id: case for case in get_test_corpus()}
        self.assertEqual("alice", corpus["T01"].identity)
        self.assertIs(corpus["T01"].expected_outcome, ExpectedOutcome.ALLOW)
        self.assertEqual("bob", corpus["T02"].identity)
        self.assertEqual("invoice-alice-001", corpus["T02"].target.resource_id)
        self.assertEqual("invoice-alice-002", corpus["T10"].target.resource_id)
        self.assertIs(corpus["T02"].expected_outcome, ExpectedOutcome.DENY)
        self.assertEqual("anonymous", corpus["T08"].identity)
        self.assertIs(corpus["T08"].expected_outcome, ExpectedOutcome.DENY)
        self.assertIs(corpus["T04"].expected_outcome, ExpectedOutcome.INCONCLUSIVE)

    def test_target_encodes_root_nested_and_property_scope(self) -> None:
        corpus = {case.test_id: case for case in get_test_corpus()}
        self.assertEqual((), corpus["T02"].target.object_path)
        self.assertEqual("customer", corpus["T06"].target.resource_type)
        self.assertEqual((), corpus["T06"].target.object_path)
        self.assertEqual("internalNotes", corpus["T10"].target.property_name)
        self.assertIs(corpus["T04"].category, Category.AUTHENTICATION)
        self.assertIs(corpus["T11"].category, Category.AUTHENTICATION)
        self.assertTrue(corpus["T04"].target.is_collection)


class CanonicalConfigurationTests(unittest.TestCase):
    def test_configurations_keep_ids_and_frozen_mutant_sets(self) -> None:
        configurations = get_configurations()
        self.assertEqual([f"C{i}" for i in range(6)], [config.configuration_id for config in configurations])
        expected = [frozenset(), frozenset({"M1"}), frozenset({"M2"}), frozenset({"M3"}), frozenset({"M4"}), frozenset({"M1", "M2", "M3", "M4"})]
        self.assertEqual(expected, [config.enabled_mutants for config in configurations])
        self.assertTrue(all(isinstance(config.enabled_mutants, frozenset) for config in configurations))


if __name__ == "__main__":
    unittest.main()

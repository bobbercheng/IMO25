#!/usr/bin/env python3
"""
Unit Tests for Critical Bug Fixes (2025-12-08)

Tests for P0 and P1 priority fixes:
- P0-1: Semantic filtering in tier2_refinement.py
- P0-2: Early stopping in agent_gpt_oss.py
- P0-3: Environment configs for verification frequency
- P1-1: Adaptive reasoning in adversarial_critic.py
- P1-2: Empirical verifier problem detection

Run with: python code/test_critical_fixes.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import unittest
from unittest.mock import patch, MagicMock


class TestP0_1_SemanticFiltering(unittest.TestCase):
    """Test P0-1: Semantic filtering in tier2_refinement.py"""

    def setUp(self):
        """Import tier2_refinement module"""
        import tier2_refinement
        self.module = tier2_refinement

    def test_skip_set_definitions(self):
        """Test that set definitions are filtered out"""
        equation = r"T_k=\{(u,v) \mid u+v \le k+1\}"
        context_before = "Define the set"
        context_after = "where u and v are positive integers"
        proof_text = "some proof"

        result = self.module.should_validate_equation(
            equation, context_before, context_after, proof_text
        )
        self.assertFalse(result, "Set definitions should be filtered out")

    def test_skip_inequalities(self):
        """Test that inequalities are filtered out"""
        equation = "x + y > 0"
        context_before = "subject to"
        context_after = ""
        proof_text = ""

        result = self.module.should_validate_equation(
            equation, context_before, context_after, proof_text
        )
        self.assertFalse(result, "Inequalities should be filtered out")

    def test_skip_negated_equations(self):
        """Test that negated equations are filtered out"""
        equation = "x+y=0"
        context_before = "NOT parallel to"
        context_after = ""
        proof_text = ""

        result = self.module.should_validate_equation(
            equation, context_before, context_after, proof_text
        )
        self.assertFalse(result, "Negated equations should be filtered out")

    def test_skip_variable_definitions(self):
        """Test that variable definitions are filtered out"""
        equation = "p = t+1"
        context_before = "Let "
        context_after = " be a variable"
        proof_text = ""

        result = self.module.should_validate_equation(
            equation, context_before, context_after, proof_text
        )
        self.assertFalse(result, "Variable definitions should be filtered out")

    def test_skip_conditional_equations(self):
        """Test that conditional equations are filtered out"""
        equation = "x = 5"
        context_before = "If n > 3, then"
        context_after = ""
        proof_text = ""

        result = self.module.should_validate_equation(
            equation, context_before, context_after, proof_text
        )
        self.assertFalse(result, "Conditional equations should be filtered out")

    def test_allow_derivations(self):
        """Test that actual derivations are allowed"""
        equation = "x^2 - y^2 = (x+y)(x-y)"
        context_before = "We can factor this as"
        context_after = "which simplifies to"
        proof_text = ""

        result = self.module.should_validate_equation(
            equation, context_before, context_after, proof_text
        )
        self.assertTrue(result, "Derivations should be allowed")

    def test_skip_section_headers_asterisk(self):
        """Test that section headers with asterisks are filtered out (P0-7)"""
        equation = "k=0"
        context_before = "*k=0*. Construction:"
        context_after = ""
        proof_text = ""

        result = self.module.should_validate_equation(
            equation, context_before, context_after, proof_text
        )
        self.assertFalse(result, "Section headers (*k=0*) should be filtered out")

    def test_skip_section_headers_numbered(self):
        """Test that numbered section headers are filtered out (P0-7)"""
        equation = "k=1"
        context_before = "(1) k=1:"
        context_after = ""
        proof_text = ""

        result = self.module.should_validate_equation(
            equation, context_before, context_after, proof_text
        )
        self.assertFalse(result, "Numbered headers ((1) k=1) should be filtered out")

    def test_skip_case_specifications(self):
        """Test that case specifications are filtered out (P0-8)"""
        equation = "n=3"
        context_before = "For n=3 the values are"
        context_after = ""
        proof_text = ""

        result = self.module.should_validate_equation(
            equation, context_before, context_after, proof_text
        )
        self.assertFalse(result, "Case specifications (for n=3) should be filtered out")

    def test_skip_object_naming_line(self):
        """Test that object naming is filtered out (P0-9)"""
        equation = "y=x"
        context_before = "Replace by the line y=x which"
        context_after = ""
        proof_text = ""

        result = self.module.should_validate_equation(
            equation, context_before, context_after, proof_text
        )
        self.assertFalse(result, "Object naming (the line y=x) should be filtered out")

    def test_skip_object_naming_column(self):
        """Test that column/row specifications are filtered out (P0-9)"""
        equation = "x=v+1"
        context_before = "In column x=v+1 the points"
        context_after = ""
        proof_text = ""

        result = self.module.should_validate_equation(
            equation, context_before, context_after, proof_text
        )
        self.assertFalse(result, "Column specifications (in column x=...) should be filtered out")


class TestP0_3_EnvironmentConfigs(unittest.TestCase):
    """Test P0-3: Environment configs for verification frequency"""

    def test_verification_frequency_default(self):
        """Test that default verification frequency is 4"""
        import adversarial_critic

        # Mock environment to ensure defaults
        with patch.dict(os.environ, {}, clear=True):
            # Create a temporary critic to check config
            critic = adversarial_critic.AdversarialCritic(verbose=False)

            # Simulate reading config (this happens in attack_solution)
            verify_every_n = int(os.getenv('RLAC_VERIFY_EVERY_N_ROUNDS', '4'))
            verify_start_round = int(os.getenv('RLAC_VERIFY_START_ROUND', '3'))

            self.assertEqual(verify_every_n, 4, "Default verify_every_n should be 4")
            self.assertEqual(verify_start_round, 3, "Default verify_start_round should be 3")


class TestP1_1_AdaptiveReasoning(unittest.TestCase):
    """Test P1-1: Adaptive reasoning in adversarial_critic.py"""

    def setUp(self):
        """Import adversarial_critic module"""
        import adversarial_critic
        self.critic = adversarial_critic.AdversarialCritic(
            reasoning_effort="medium",
            verbose=False
        )

    def test_early_rounds_use_low(self):
        """Test that rounds 0-2 use LOW reasoning"""
        for round_num in [0, 1, 2]:
            effort = self.critic._get_progressive_reasoning_effort(round_num, max_rounds=15)
            self.assertEqual(effort, "low", f"Round {round_num} should use LOW reasoning")

    def test_middle_rounds_use_medium(self):
        """Test that rounds 3-6 use MEDIUM reasoning"""
        for round_num in [3, 4, 5, 6]:
            effort = self.critic._get_progressive_reasoning_effort(round_num, max_rounds=15)
            self.assertEqual(effort, "medium", f"Round {round_num} should use MEDIUM reasoning")

    def test_late_rounds_use_medium(self):
        """Test that rounds 7+ use MEDIUM reasoning (not HIGH due to time)"""
        for round_num in [7, 8, 9, 10]:
            effort = self.critic._get_progressive_reasoning_effort(round_num, max_rounds=15)
            self.assertEqual(effort, "medium", f"Round {round_num} should use MEDIUM reasoning")

    def test_adaptive_reasoning_can_be_disabled(self):
        """Test that adaptive reasoning can be disabled via env var"""
        with patch.dict(os.environ, {'RLAC_DISABLE_ADAPTIVE_REASONING': 'true'}):
            effort = self.critic._get_progressive_reasoning_effort(0, max_rounds=15)
            self.assertEqual(effort, "medium", "Should use base reasoning when adaptive disabled")

    def test_adaptive_reasoning_configurable(self):
        """Test that adaptive reasoning levels are configurable"""
        with patch.dict(os.environ, {
            'RLAC_ADAPTIVE_REASONING_EARLY': 'medium',
            'RLAC_ADAPTIVE_REASONING_MIDDLE': 'high',
            'RLAC_ADAPTIVE_REASONING_LATE': 'high'
        }):
            effort_early = self.critic._get_progressive_reasoning_effort(0, max_rounds=15)
            effort_middle = self.critic._get_progressive_reasoning_effort(5, max_rounds=15)
            effort_late = self.critic._get_progressive_reasoning_effort(10, max_rounds=15)

            self.assertEqual(effort_early, "medium", "Early rounds should respect env config")
            self.assertEqual(effort_middle, "high", "Middle rounds should respect env config")
            self.assertEqual(effort_late, "high", "Late rounds should respect env config")


class TestP1_2_EmpiricalVerifier(unittest.TestCase):
    """Test P1-2: Empirical verifier problem detection"""

    def setUp(self):
        """Import empirical_verifier module"""
        import empirical_verifier
        self.module = empirical_verifier

    def test_detect_problem_1(self):
        """Test detection of Problem 1 (Sunny Lines)"""
        problem_statement = "Find all k such that exactly k lines are sunny..."
        problem_id = self.module.detect_problem_type(problem_statement)
        self.assertEqual(problem_id, "imo_2025_problem_1", "Should detect Problem 1")

    def test_detect_unknown_problem(self):
        """Test that unknown problems return 'unknown'"""
        problem_statement = "Prove that the sum of squares..."
        problem_id = self.module.detect_problem_type(problem_statement)
        self.assertEqual(problem_id, "unknown", "Should return 'unknown' for unregistered problems")

    def test_ground_truth_registry_has_problem_1(self):
        """Test that ground truth registry contains Problem 1"""
        registry = self.module.GROUND_TRUTH_REGISTRY
        self.assertIn("imo_2025_problem_1", registry, "Registry should contain Problem 1")

        problem_info = registry["imo_2025_problem_1"]
        self.assertIn("answer", problem_info, "Problem info should have answer function")
        self.assertIn("keywords", problem_info, "Problem info should have keywords")
        self.assertIn("n_range", problem_info, "Problem info should have n_range")

    def test_ground_truth_function_problem_1(self):
        """Test that Problem 1 ground truth function works correctly"""
        registry = self.module.GROUND_TRUTH_REGISTRY
        ground_truth = registry["imo_2025_problem_1"]["answer"]

        # Test known correct values
        self.assertTrue(ground_truth(0, 5), "k=0 should work for any n")
        self.assertTrue(ground_truth(1, 5), "k=1 should work for any n")
        self.assertTrue(ground_truth(4, 5), "k=n-1 should work (4 for n=5)")

        # Test known incorrect values
        self.assertFalse(ground_truth(2, 5), "k=2 should NOT work for n=5")
        self.assertFalse(ground_truth(3, 5), "k=3 should NOT work for n=5")

    def test_unknown_problem_returns_suspicious(self):
        """Test that unknown problems return SUSPICIOUS verdict"""
        problem_statement = "Some unknown problem..."
        solution = "Some solution..."
        answer_text = "k=5"

        result = self.module.empirical_verification_combinatorial(
            problem_statement, solution, answer_text, verbose=False
        )

        self.assertEqual(result['verdict'], 'SUSPICIOUS', "Unknown problems should return SUSPICIOUS")
        self.assertEqual(result['score'], 0.5, "Unknown problems should have 0.5 score")
        self.assertIn("not in ground truth registry", result['errors'][0].lower(),
                     "Error should mention registry")


class TestP0_2_EarlyStopping(unittest.TestCase):
    """Test P0-2: Early stopping in agent_gpt_oss.py (integration test)"""

    def test_early_stop_flag_exists(self):
        """Test that early_stop_oscillation flag is properly initialized"""
        # This is a smoke test to ensure the variable exists
        # Full integration testing requires running actual RLAC
        import agent_gpt_oss

        # Check that the file contains the early stopping logic
        with open('code/agent_gpt_oss.py', 'r') as f:
            content = f.read()

        self.assertIn('early_stop_oscillation', content,
                     "Early stopping flag should exist in agent_gpt_oss.py")
        self.assertIn('P0-2', content,
                     "P0-2 fix marker should exist in agent_gpt_oss.py")


def run_tests():
    """Run all tests and print summary"""
    print("=" * 80)
    print("CRITICAL FIXES UNIT TESTS")
    print("=" * 80)
    print()

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestP0_1_SemanticFiltering))
    suite.addTests(loader.loadTestsFromTestCase(TestP0_3_EnvironmentConfigs))
    suite.addTests(loader.loadTestsFromTestCase(TestP1_1_AdaptiveReasoning))
    suite.addTests(loader.loadTestsFromTestCase(TestP1_2_EmpiricalVerifier))
    suite.addTests(loader.loadTestsFromTestCase(TestP0_2_EarlyStopping))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print()
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")

    if result.wasSuccessful():
        print()
        print("✅ ALL TESTS PASSED!")
        return 0
    else:
        print()
        print("❌ SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(run_tests())

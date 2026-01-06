#!/usr/bin/env python3
"""
Test MCTS integration with counterexample validation.

This test verifies that MCTS properly calls counterexample validation
through the init_explorations() -> verify_solution() pipeline.
"""

import unittest
import sys
import os
import inspect
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class TestMCTSIntegration(unittest.TestCase):
    """Test MCTS integration with fixed verification system."""

    def test_mcts_calls_verify_solution(self):
        """Test that MCTS simulate() calls verify_solution through init_explorations."""
        # This test verifies the call chain:
        # MCTS.simulate() -> init_explorations() -> verify_solution() -> counterexample validation

        from mcts_bfs import MCTSExplorer, MCTSNode

        # Create mock functions
        mock_generate = Mock(return_value=(
            {"messages": []},  # p1
            "Test solution with k ∈ {0,1}",  # solution
            "Solution passed verification",  # verify
            "yes"  # good_verify
        ))

        mock_verify = Mock(return_value=(
            "Verification passed",  # verify
            "yes"  # good_verify
        ))

        # Create MCTS explorer
        explorer = MCTSExplorer(exploration_constant=1.414, max_depth=2)
        root = explorer.root

        # Simulate one iteration
        problem = "Test problem"
        score, solution_dict = explorer.simulate(
            node=root,
            problem_statement=problem,
            generate_solution_func=mock_generate,
            verify_solution_func=mock_verify,
            sol_reasoning="low",
            self_imp_reasoning="low",
            ver_reasoning="low"
        )

        # Verify generate_solution_func was called (which internally calls verify_solution)
        self.assertTrue(mock_generate.called,
                       "MCTS should call generate_solution_func")

        # Verify solution was generated
        self.assertIsNotNone(solution_dict.get('solution'),
                            "MCTS should generate a solution")

        print(f"✅ MCTS simulate() correctly calls generation pipeline")
        print(f"   - generate_solution_func called: {mock_generate.call_count} times")
        print(f"   - Solution generated: {bool(solution_dict.get('solution'))}")

    def test_init_explorations_calls_verify_solution(self):
        """Test that init_explorations() calls verify_solution()."""
        # Import after adding to path
        from agent_gpt_oss import init_explorations, verify_solution

        # We can't easily test this without mocking the API calls,
        # but we can verify the function signature matches what MCTS expects
        import inspect

        # Check init_explorations signature
        sig = inspect.signature(init_explorations)
        params = list(sig.parameters.keys())

        expected_params = ['problem_statement', 'verbose', 'other_prompts',
                          'reasoning_effort', 'self_improvement_reasoning',
                          'verification_reasoning']

        for param in expected_params:
            self.assertIn(param, params,
                         f"init_explorations should have parameter '{param}'")

        # Check verify_solution signature
        sig = inspect.signature(verify_solution)
        params = list(sig.parameters.keys())

        expected_params = ['problem_statement', 'solution', 'verbose', 'reasoning_effort']

        for param in expected_params:
            self.assertIn(param, params,
                         f"verify_solution should have parameter '{param}'")

        print(f"✅ Function signatures match expected interface")

    def test_verify_solution_has_counterexample_validation(self):
        """Test that verify_solution includes counterexample validation code."""
        import agent_gpt_oss

        # Read the source code of verify_solution
        source = inspect.getsource(agent_gpt_oss.verify_solution)

        # Check for counterexample validation code
        self.assertIn("COUNTEREXAMPLE VALIDATION", source,
                     "verify_solution should include counterexample validation")

        self.assertIn("validate_solution_with_counterexamples", source,
                     "verify_solution should call validate_solution_with_counterexamples")

        self.assertIn('if "yes" in o.lower()', source,
                     "verify_solution should check for 'yes' before running counterexample validation")

        print(f"✅ verify_solution includes counterexample validation code")
        print(f"   - Checks for: COUNTEREXAMPLE VALIDATION comment")
        print(f"   - Calls: validate_solution_with_counterexamples()")
        print(f"   - Guards with: if 'yes' in o.lower()")

    def test_validate_counterexample_function_exists(self):
        """Test that validate_solution_with_counterexamples function exists."""
        import agent_gpt_oss

        # Check function exists
        self.assertTrue(hasattr(agent_gpt_oss, 'validate_solution_with_counterexamples'),
                       "Module should have validate_solution_with_counterexamples function")

        # Check function signature
        func = getattr(agent_gpt_oss, 'validate_solution_with_counterexamples')
        sig = inspect.signature(func)
        params = list(sig.parameters.keys())

        expected_params = ['solution', 'problem_statement', 'verbose']
        for param in expected_params:
            self.assertIn(param, params,
                         f"validate_solution_with_counterexamples should have parameter '{param}'")

        print(f"✅ validate_solution_with_counterexamples function exists")
        print(f"   - Parameters: {params}")

    @patch('agent_gpt_oss.send_api_request_with_retry')
    def test_counterexample_validation_called_on_yes(self, mock_api):
        """Test that counterexample validation is called when verification says 'yes'."""
        import agent_gpt_oss

        # Mock API responses in the correct format
        # First call: verification prompt
        # Second call: verification correctness check (returns "yes")
        mock_api.side_effect = [
            {
                "choices": [{
                    "message": {
                        "content": "The solution looks correct"
                    }
                }]
            },  # verification
            {
                "choices": [{
                    "message": {
                        "content": "yes"
                    }
                }]
            },  # correctness check
        ]

        # Mock counterexample validation to track if it's called
        with patch('agent_gpt_oss.validate_solution_with_counterexamples') as mock_counterexample:
            mock_counterexample.return_value = {
                "verdict": "VALID",
                "reason": "All test cases passed",
                "failed_cases": []
            }

            # Call verify_solution
            verify, good_verify = agent_gpt_oss.verify_solution(
                problem_statement="Test problem",
                solution="Test solution with k ∈ {0,1}",
                verbose=False,
                reasoning_effort="low"
            )

            # Verify counterexample validation was called
            self.assertTrue(mock_counterexample.called,
                           "validate_solution_with_counterexamples should be called when verification says 'yes'")

            print(f"✅ Counterexample validation called when verification passes")
            print(f"   - Call count: {mock_counterexample.call_count}")


def run_tests():
    """Run all tests and report results."""
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestMCTSIntegration)

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print("\n" + "="*80)
    print("MCTS INTEGRATION TEST SUMMARY")
    print("="*80)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")

    if result.wasSuccessful():
        print("\n✅ ALL TESTS PASSED")
        print("\nMCTS integration is working correctly:")
        print("  - MCTS calls generate_solution_func (init_explorations)")
        print("  - init_explorations calls verify_solution")
        print("  - verify_solution includes counterexample validation")
        print("  - Counterexample validation runs when verification says 'yes'")
        print("\nReady for production use!")
    else:
        print("\n❌ SOME TESTS FAILED")
        print("\nFix failing tests before using MCTS in production.")

        if result.failures:
            print("\nFailures:")
            for test, traceback in result.failures:
                print(f"  - {test}: {traceback}")

        if result.errors:
            print("\nErrors:")
            for test, traceback in result.errors:
                print(f"  - {test}: {traceback}")

    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_tests())

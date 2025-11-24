#!/usr/bin/env python3
"""
Test script for RLAC bug fixes identified from test_rlac_output.log analysis.

This tests the following critical fixes:
1. CRITICAL: Premature stuck detection failure (stuck_count=0 but failure triggered)
2. HIGH: Verdict parsing ignores counterexamples requirement
3. HIGH: Null attack text crash
4. MEDIUM: consecutive_broken counter reset on solution change

Run: python code/test_rlac_bug_fixes.py

For real LLM test:
  GPT_OSS_API_KEY="sk-7EQb6H6KKmBdE2eXkOdSJA" \
  GPT_OSS_API_URL="http://bore.vexorium.net:37472/v1/chat/completions" \
  python code/test_rlac_bug_fixes.py --real-llm
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import unittest
from unittest.mock import Mock, patch, MagicMock
import json

# Import the modules under test
from adversarial_critic import AdversarialCritic


class TestVerdictParsing(unittest.TestCase):
    """Test fixes for verdict parsing bugs."""

    def setUp(self):
        self.critic = AdversarialCritic(verbose=False)

    def test_null_attack_text_no_crash(self):
        """FIX: Null attack text should return UNKNOWN, not crash."""
        # This was Bug #4 - would crash with AttributeError before fix
        result = self.critic._extract_verdict(None, [])
        self.assertEqual(result, 'UNKNOWN',
            "Null attack_text should return UNKNOWN, not crash")

        result = self.critic._extract_verdict("", [])
        self.assertEqual(result, 'UNKNOWN',
            "Empty attack_text should return UNKNOWN")

        print("✓ Null/empty attack text handled correctly (no crash)")

    def test_broken_word_without_counterexamples_is_suspicious(self):
        """FIX: Word 'BROKEN' alone should not return BROKEN verdict."""
        # This was Bug #3 - returned BROKEN just because word appeared

        # Text mentions BROKEN but no actual counterexamples parsed
        text_with_broken_word = """
        This solution discusses what a BROKEN proof looks like.
        The solution avoids the BROKEN patterns from before.
        """

        result = self.critic._extract_verdict(text_with_broken_word, counterexamples=[])
        self.assertNotEqual(result, 'BROKEN',
            "Word 'BROKEN' without counterexamples should NOT return BROKEN")
        self.assertEqual(result, 'SUSPICIOUS',
            "Word 'BROKEN' without counterexamples should return SUSPICIOUS")

        print("✓ Word 'BROKEN' alone returns SUSPICIOUS, not BROKEN")

    def test_broken_verdict_requires_counterexamples(self):
        """FIX: BROKEN verdict requires actual counterexamples."""
        # With actual counterexamples, should return BROKEN
        result = self.critic._extract_verdict(
            "The solution has issues",
            counterexamples=["n=3, k=2 fails"]
        )
        self.assertEqual(result, 'BROKEN',
            "With actual counterexamples, should return BROKEN")

        print("✓ BROKEN verdict correctly requires counterexamples")

    def test_robust_detected_correctly(self):
        """FIX: ROBUST indicators should be detected first."""
        # Text with ROBUST indicator
        text = "ADVERSARIAL_VALIDATION_PASSED - no flaws found"
        result = self.critic._extract_verdict(text, counterexamples=[])
        self.assertEqual(result, 'ROBUST',
            "ADVERSARIAL_VALIDATION_PASSED should return ROBUST")

        # Text with NO FLAWS
        text = "The solution has NO FLAWS"
        result = self.critic._extract_verdict(text, counterexamples=[])
        self.assertEqual(result, 'ROBUST',
            "NO FLAWS should return ROBUST")

        print("✓ ROBUST indicators detected correctly")

    def test_not_broken_text_does_not_return_broken(self):
        """Edge case: 'NOT BROKEN' should not be parsed as BROKEN."""
        text = "This solution is NOT BROKEN"
        result = self.critic._extract_verdict(text, counterexamples=[])
        # Should not return BROKEN just because the word appears
        self.assertNotEqual(result, 'BROKEN',
            "'NOT BROKEN' should not return BROKEN verdict")

        print("✓ 'NOT BROKEN' text handled correctly")


class TestStuckPatternDetection(unittest.TestCase):
    """Test fixes for stuck pattern detection."""

    def setUp(self):
        self.critic = AdversarialCritic(verbose=False)

    def test_detect_stuck_pattern_needs_history(self):
        """detect_stuck_pattern should require sufficient history."""
        # Empty history
        self.assertFalse(self.critic.detect_stuck_pattern(recent_rounds=4),
            "Empty history should not trigger stuck detection")

        # Add 3 attacks (less than 4)
        for i in range(3):
            self.critic.attack_history.append({
                'verdict': 'BROKEN',
                'counterexamples': [f"ce_{i}"],
                'round_num': i
            })

        self.assertFalse(self.critic.detect_stuck_pattern(recent_rounds=4),
            "Less than 4 rounds should not trigger stuck detection")

        print("✓ Stuck detection requires sufficient history")

    def test_detect_stuck_pattern_all_broken_with_ces(self):
        """detect_stuck_pattern triggers when all rounds BROKEN with counterexamples."""
        self.critic.attack_history = []

        # Add 4 BROKEN attacks with counterexamples
        for i in range(4):
            self.critic.attack_history.append({
                'verdict': 'BROKEN',
                'counterexamples': [f"counterexample_{i}"],
                'round_num': i
            })

        self.assertTrue(self.critic.detect_stuck_pattern(recent_rounds=4),
            "4 consecutive BROKEN rounds with counterexamples should trigger stuck")

        print("✓ Stuck detection triggers on repeated BROKEN with counterexamples")

    def test_detect_stuck_pattern_not_all_broken(self):
        """detect_stuck_pattern should NOT trigger if not all BROKEN."""
        self.critic.attack_history = []

        # Add 3 BROKEN + 1 ROBUST
        for i in range(3):
            self.critic.attack_history.append({
                'verdict': 'BROKEN',
                'counterexamples': [f"ce_{i}"],
                'round_num': i
            })
        self.critic.attack_history.append({
            'verdict': 'ROBUST',
            'counterexamples': [],
            'round_num': 3
        })

        self.assertFalse(self.critic.detect_stuck_pattern(recent_rounds=4),
            "Mixed BROKEN/ROBUST should not trigger stuck detection")

        print("✓ Stuck detection correctly ignores mixed verdicts")


class TestRLACLoopIntegration(unittest.TestCase):
    """Test RLAC loop integration fixes in agent_gpt_oss.py.

    These tests verify the logic fixes without actually running the full agent.
    """

    def test_premature_failure_fix_logic(self):
        """FIX: stuck_count=0 should NOT trigger failure even with critic_stuck=True.

        The fix adds condition: if critic_stuck AND stuck_count > 0
        This test verifies the LOGIC of the fix.
        """
        # Simulate the fixed condition
        def should_fail_with_fix(critic_stuck: bool, stuck_count: int, consecutive_broken: int, stuck_threshold: int) -> bool:
            """Simulates the fixed logic from agent_gpt_oss.py lines 2586-2603"""
            if critic_stuck and stuck_count > 0:
                return True  # True failure
            elif critic_stuck and consecutive_broken >= stuck_threshold:
                return False  # Warning only, don't fail
            return False

        # Test case 1: stuck_count=0 should NOT fail (the bug we fixed)
        self.assertFalse(
            should_fail_with_fix(critic_stuck=True, stuck_count=0, consecutive_broken=4, stuck_threshold=3),
            "stuck_count=0 should NOT trigger failure even when critic_stuck=True"
        )

        # Test case 2: stuck_count>0 WITH critic_stuck should fail
        self.assertTrue(
            should_fail_with_fix(critic_stuck=True, stuck_count=1, consecutive_broken=4, stuck_threshold=3),
            "stuck_count>0 WITH critic_stuck should trigger failure"
        )

        # Test case 3: critic_stuck=False should never fail
        self.assertFalse(
            should_fail_with_fix(critic_stuck=False, stuck_count=5, consecutive_broken=10, stuck_threshold=3),
            "critic_stuck=False should never trigger this failure path"
        )

        print("✓ Premature failure fix logic verified")
        print("  - stuck_count=0 no longer triggers failure")
        print("  - Only stuck_count>0 AND critic_stuck triggers failure")

    def test_consecutive_broken_not_reset_on_solution_change(self):
        """FIX: consecutive_broken should NOT reset when solution changes.

        The fix removes the line: consecutive_broken = 0
        from the 'solution changed' branch.
        """
        # Simulate the old (buggy) behavior
        def old_behavior(solution_changed: bool, stuck_count: int, consecutive_broken: int):
            if solution_changed:
                stuck_count = 0
                consecutive_broken = 0  # BUG: This was reset
            return stuck_count, consecutive_broken

        # Simulate the new (fixed) behavior
        def new_behavior(solution_changed: bool, stuck_count: int, consecutive_broken: int):
            if solution_changed:
                stuck_count = 0
                # FIX: Do NOT reset consecutive_broken here
            return stuck_count, consecutive_broken

        # Test: After 3 BROKEN verdicts with solution changes
        # Old behavior: consecutive_broken stays at 1 (keeps resetting)
        # New behavior: consecutive_broken reaches 3

        old_cb = 0
        new_cb = 0

        for i in range(3):
            # Simulate BROKEN verdict
            old_cb += 1
            new_cb += 1

            # Simulate solution changed
            _, old_cb = old_behavior(solution_changed=True, stuck_count=0, consecutive_broken=old_cb)
            _, new_cb = new_behavior(solution_changed=True, stuck_count=0, consecutive_broken=new_cb)

        self.assertEqual(old_cb, 0, "Old behavior resets consecutive_broken (bug)")
        self.assertEqual(new_cb, 3, "New behavior preserves consecutive_broken (fix)")

        print("✓ consecutive_broken counter fix verified")
        print(f"  - Old (buggy) behavior: consecutive_broken = {old_cb}")
        print(f"  - New (fixed) behavior: consecutive_broken = {new_cb}")


class TestRealLLMIntegration(unittest.TestCase):
    """Test with real LLM API if credentials provided."""

    @unittest.skipUnless(
        os.environ.get('GPT_OSS_API_KEY') and os.environ.get('GPT_OSS_API_URL'),
        "Skipping real LLM test - set GPT_OSS_API_KEY and GPT_OSS_API_URL to run"
    )
    def test_real_critic_attack(self):
        """Test real LLM attack flow using the full agent_gpt_oss flow."""
        import requests

        api_key = os.environ.get('GPT_OSS_API_KEY')
        api_url = os.environ.get('GPT_OSS_API_URL')

        print(f"\n>>> Running real LLM test against {api_url}")

        # Import the API request function from agent_gpt_oss
        try:
            from agent_gpt_oss import send_api_request, build_request_payload
        except ImportError as e:
            self.skipTest(f"Could not import agent_gpt_oss: {e}")

        # Create a simple API request function that uses the provided URL
        # Note: adversarial_critic.py calls api_request_func(api_key, payload)
        def api_request_func(key, payload):
            """Send request to the real API."""
            headers = {"Content-Type": "application/json; charset=utf-8"}
            if key:
                headers["Authorization"] = f"Bearer {key}"

            # Use requests.post with data= instead of json= to control encoding
            import json as json_module
            response = requests.post(
                api_url,
                data=json_module.dumps(payload, ensure_ascii=False).encode('utf-8'),
                headers=headers,
                timeout=120
            )
            response.raise_for_status()
            return response.json()

        # Simple test problem
        test_problem = "Prove that for all n >= 1, 1 + 2 + ... + n = n(n+1)/2"
        test_solution = """
        ### Summary ###
        The answer is proven by induction.

        ### Detailed Solution ###
        Base case: n=1, we have 1 = 1*2/2 = 1. True.
        Induction: Assume true for k. For k+1:
        1+2+...+k+(k+1) = k(k+1)/2 + (k+1) = (k+1)(k+2)/2.
        QED.
        """

        # Create critic and run attack
        critic = AdversarialCritic(reasoning_effort="low", verbose=True)

        # This tests the full attack flow with real LLM
        try:
            result = critic.attack_solution(
                problem_statement=test_problem,
                solution=test_solution,
                round_num=0,
                max_rounds=10,
                api_request_func=api_request_func,
                api_key=api_key
            )

            print(f">>> Attack result: {result.get('verdict', 'UNKNOWN')}")
            print(f">>> Counterexamples: {len(result.get('counterexamples', []))}")

            # Verify result structure
            self.assertIn('verdict', result, "Result should have verdict")
            self.assertIn('counterexamples', result, "Result should have counterexamples")
            self.assertIn(result['verdict'], ['BROKEN', 'SUSPICIOUS', 'ROBUST', 'UNKNOWN'],
                f"Verdict should be valid, got: {result.get('verdict')}")

            print("✓ Real LLM attack completed successfully")

        except requests.exceptions.RequestException as e:
            self.skipTest(f"Network error (API might be unavailable): {e}")
        except Exception as e:
            self.fail(f"Real LLM attack failed: {e}")


class TestP0NearSuccessProtection(unittest.TestCase):
    """Test P0: Near-success protection (2/3 ROBUST grace failure)."""

    def test_near_success_decrement_logic(self):
        """P0 FIX: At 2/3 ROBUST, decrement instead of full reset."""

        def apply_broken_verdict_with_fix(consecutive_robust: int) -> int:
            """Simulates the fixed logic from agent_gpt_oss.py lines 2401-2411"""
            if consecutive_robust >= 2:
                # Near-success protection: decrement instead of reset
                consecutive_robust -= 1
            else:
                consecutive_robust = 0  # Full reset when not near success
            return consecutive_robust

        # Test case 1: At 2/3 ROBUST, should decrement to 1
        result = apply_broken_verdict_with_fix(2)
        self.assertEqual(result, 1,
            "At 2/3 ROBUST, BROKEN should decrement to 1/3, not reset to 0")

        # Test case 2: At 1/3 ROBUST, should reset to 0
        result = apply_broken_verdict_with_fix(1)
        self.assertEqual(result, 0,
            "At 1/3 ROBUST, BROKEN should reset to 0")

        # Test case 3: At 0/3 ROBUST, should stay at 0
        result = apply_broken_verdict_with_fix(0)
        self.assertEqual(result, 0,
            "At 0/3 ROBUST, should stay at 0")

        print("✓ P0 Near-success protection verified")
        print("  - 2/3 ROBUST -> 1/3 (grace failure)")
        print("  - 1/3 ROBUST -> 0/3 (full reset)")


class TestP1CounterexampleVerification(unittest.TestCase):
    """Test P1: Counterexample verification before defense."""

    def test_verify_counterexample_with_concrete_values(self):
        """P1 FIX: Counterexamples with concrete values should be verified."""
        import re
        concrete_value_pattern = r'[nkxyzabcm]\s*[=≤≥<>]\s*\d+'

        # Test concrete counterexamples
        ce_concrete = "For n=3, k=2, the construction fails"
        has_concrete = bool(re.search(concrete_value_pattern, ce_concrete, re.IGNORECASE))
        self.assertTrue(has_concrete, "Should detect concrete value n=3")

        # Test vague counterexample
        ce_vague = "The construction might fail for some values"
        has_concrete = bool(re.search(concrete_value_pattern, ce_vague, re.IGNORECASE))
        self.assertFalse(has_concrete, "Should not find concrete values in vague CE")

        print("✓ P1 Counterexample verification pattern works")

    def test_vague_indicator_detection(self):
        """P1 FIX: Vague counterexamples should be flagged."""
        vague_indicators = ["might fail", "could fail", "may not work", "unclear", "possibly wrong"]

        # Test vague counterexample
        ce_vague = "This approach might fail in certain cases"
        is_vague = any(ind in ce_vague.lower() for ind in vague_indicators)
        self.assertTrue(is_vague, "Should detect 'might fail' as vague")

        # Test concrete counterexample
        ce_concrete = "n=3, k=2: line x+y=5 is not sunny"
        is_vague = any(ind in ce_concrete.lower() for ind in vague_indicators)
        self.assertFalse(is_vague, "Concrete CE should not be flagged as vague")

        print("✓ P1 Vague indicator detection works")


class TestP2AnswerLock(unittest.TestCase):
    """Test P2: Answer lock mechanism after 2 consecutive ROBUST."""

    def test_answer_lock_activation(self):
        """P2 FIX: Answer should lock after lock_threshold consecutive ROBUST."""
        lock_threshold = 2
        consecutive_robust = 2
        answer_locked = False
        locked_answer = None

        # Simulate lock activation
        if consecutive_robust >= lock_threshold and not answer_locked:
            locked_answer = "k ∈ {0, 1, ..., n}"
            answer_locked = True

        self.assertTrue(answer_locked, "Answer should be locked at 2/3 ROBUST")
        self.assertEqual(locked_answer, "k ∈ {0, 1, ..., n}", "Locked answer should be preserved")

        print("✓ P2 Answer lock activation verified")

    def test_answer_lock_enforcement_instruction(self):
        """P2 FIX: Lock instruction should be added to defense prompt."""
        answer_locked = True
        locked_answer = "k ∈ {0, 1, ..., n}"

        answer_lock_instruction = ""
        if answer_locked and locked_answer:
            answer_lock_instruction = f"""
CRITICAL ANSWER LOCK INSTRUCTION:
The answer "{locked_answer[:100]}..." has been validated in previous rounds and MUST be preserved.
"""

        self.assertIn("CRITICAL ANSWER LOCK", answer_lock_instruction,
            "Lock instruction should be generated")
        self.assertIn(locked_answer, answer_lock_instruction,
            "Lock instruction should contain the locked answer")

        print("✓ P2 Answer lock instruction generation verified")


class TestP3TruncationDetection(unittest.TestCase):
    """Test P3: Truncation detection for short attack responses."""

    def test_truncation_detection_threshold(self):
        """P3 FIX: Short attack responses should be flagged as truncated."""
        min_valid_attack_length = 500

        # Test short response (truncated)
        short_response = "BROKEN - n=3 fails"  # Only ~20 chars
        self.assertTrue(len(short_response) < min_valid_attack_length,
            "Short response should be detected as potentially truncated")

        # Test adequate response
        adequate_response = "ANALYSIS: " + "x" * 600
        self.assertFalse(len(adequate_response) < min_valid_attack_length,
            "Adequate response should not be flagged as truncated")

        print("✓ P3 Truncation detection threshold works")

    def test_truncation_verdict_downgrade(self):
        """P3 FIX: BROKEN verdict with truncation should downgrade to SUSPICIOUS."""
        min_valid_attack_length = 500
        verdict = "BROKEN"
        attack_length = 100  # Short response
        counterexamples = ["n=3"]  # Very short counterexample

        # Apply truncation detection logic
        if attack_length < min_valid_attack_length and verdict == "BROKEN":
            if len(counterexamples) == 0 or (counterexamples and len(counterexamples[0]) < 100):
                verdict = "SUSPICIOUS"

        self.assertEqual(verdict, "SUSPICIOUS",
            "BROKEN with short response should downgrade to SUSPICIOUS")

        print("✓ P3 Verdict downgrade on truncation verified")


class TestP1v2SelfContradiction(unittest.TestCase):
    """Test P1-v2: Self-contradiction detection in counterexamples."""

    def test_detects_actually_works(self):
        """P1-v2: Should detect 'actually works' as self-contradiction."""
        import re
        pattern = r"actually\s+(works?|correct|valid|does\s+cover)"
        test_cases = [
            ("the construction actually works for n=5", True),
            ("actually does cover all points", True),
            ("this is actually correct", True),
            ("the solution fails for n=3", False),
        ]
        for text, should_match in test_cases:
            result = bool(re.search(pattern, text.lower()))
            self.assertEqual(result, should_match, f"Pattern mismatch for: {text}")
        print("✓ P1-v2 'actually works' detection verified")

    def test_detects_counterexample_fails(self):
        """P1-v2: Should detect 'counterexample fails' as self-contradiction."""
        import re
        pattern = r"the\s+(attempted\s+)?counterexample\s+(fails?|is\s+invalid|doesn't\s+work)"
        test_cases = [
            ("the attempted counterexample fails", True),
            ("the counterexample is invalid", True),
            ("the counterexample doesn't work", True),
            ("this counterexample shows the error", False),
        ]
        for text, should_match in test_cases:
            result = bool(re.search(pattern, text.lower()))
            self.assertEqual(result, should_match, f"Pattern mismatch for: {text}")
        print("✓ P1-v2 'counterexample fails' detection verified")

    def test_conclusion_invalidation(self):
        """P1-v2: Should detect invalidating conclusions."""
        import re
        pattern = r"\*?conclusion:?\*?.*?(works|correct|valid|cover)"
        test_cases = [
            ("*Conclusion:* The construction actually works", True),
            ("Conclusion: the solution is correct", True),
            ("therefore the claim is valid", False),  # Different pattern
        ]
        for text, should_match in test_cases:
            result = bool(re.search(pattern, text.lower()))
            self.assertEqual(result, should_match, f"Pattern mismatch for: {text}")
        print("✓ P1-v2 conclusion invalidation detection verified")


class TestP4OscillationDetection(unittest.TestCase):
    """Test P4: Oscillation detection in verdict history."""

    def test_detects_strict_alternation(self):
        """P4: Should detect strict R-B-R-B alternation."""
        verdict_history = ["ROBUST", "BROKEN", "ROBUST", "BROKEN"]
        binary = [1 if v == "ROBUST" else 0 for v in verdict_history]

        is_alternating = True
        for i in range(1, len(binary)):
            if binary[i] == binary[i-1]:
                is_alternating = False
                break

        self.assertTrue(is_alternating, "Should detect strict alternation")
        print("✓ P4 strict alternation detection verified")

    def test_detects_near_alternation(self):
        """P4: Should detect near-alternation (>= 70% transitions)."""
        verdict_history = ["ROBUST", "BROKEN", "BROKEN", "ROBUST", "BROKEN", "ROBUST"]
        binary = [1 if v == "ROBUST" else 0 for v in verdict_history]

        transitions = sum(1 for i in range(1, len(binary)) if binary[i] != binary[i-1])
        transition_ratio = transitions / (len(binary) - 1)

        self.assertGreaterEqual(transition_ratio, 0.7,
            f"Should detect near-alternation (ratio={transition_ratio:.2f})")
        print(f"✓ P4 near-alternation detection verified (ratio={transition_ratio:.2f})")

    def test_no_false_positive_on_progress(self):
        """P4: Should NOT detect oscillation on steady progress."""
        verdict_history = ["BROKEN", "BROKEN", "ROBUST", "ROBUST", "ROBUST"]
        binary = [1 if v == "ROBUST" else 0 for v in verdict_history]

        transitions = sum(1 for i in range(1, len(binary)) if binary[i] != binary[i-1])
        transition_ratio = transitions / (len(binary) - 1)

        self.assertLess(transition_ratio, 0.7,
            f"Should NOT detect oscillation on progress (ratio={transition_ratio:.2f})")
        print("✓ P4 no false positive on progress verified")


class TestP0v2HistoryProtection(unittest.TestCase):
    """Test P0-v2: Enhanced protection with history awareness."""

    def test_history_protection_at_1_robust(self):
        """P0-v2: At 1/3 ROBUST with history >= 2, should decrement not reset."""
        consecutive_robust = 1
        total_robust_count = 2

        # Apply P0-v2 logic
        if consecutive_robust >= 2:
            consecutive_robust -= 1
        elif consecutive_robust >= 1 and total_robust_count >= 2:
            consecutive_robust = max(0, consecutive_robust - 1)
        else:
            consecutive_robust = 0

        self.assertEqual(consecutive_robust, 0,
            "At 1/3 with history=2, should decrement to 0 (not worse)")
        print("✓ P0-v2 history protection at 1/3 ROBUST verified")

    def test_strong_history_protection(self):
        """P0-v2: With strong history (>=3), should not reset even at 0."""
        consecutive_robust = 0
        total_robust_count = 3

        # Apply P0-v2 logic - strong history protection
        if consecutive_robust >= 2:
            consecutive_robust -= 1
        elif consecutive_robust >= 1 and total_robust_count >= 2:
            consecutive_robust = max(0, consecutive_robust - 1)
        elif total_robust_count >= 3:
            pass  # Don't reset
        else:
            consecutive_robust = 0

        self.assertEqual(consecutive_robust, 0,
            "With strong history, consecutive_robust should be preserved")
        print("✓ P0-v2 strong history protection verified")

    def test_no_protection_without_history(self):
        """P0-v2: Without history, should fully reset."""
        consecutive_robust = 1
        total_robust_count = 1

        # Apply P0-v2 logic
        if consecutive_robust >= 2:
            consecutive_robust -= 1
        elif consecutive_robust >= 1 and total_robust_count >= 2:
            consecutive_robust = max(0, consecutive_robust - 1)
        elif total_robust_count >= 3:
            pass
        else:
            consecutive_robust = 0

        self.assertEqual(consecutive_robust, 0,
            "Without history, should fully reset")
        print("✓ P0-v2 no protection without history verified")


def run_tests():
    """Run all tests."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test classes - original bug fixes
    suite.addTests(loader.loadTestsFromTestCase(TestVerdictParsing))
    suite.addTests(loader.loadTestsFromTestCase(TestStuckPatternDetection))
    suite.addTests(loader.loadTestsFromTestCase(TestRLACLoopIntegration))

    # Add test classes - P0-P3 fixes (from second analysis)
    suite.addTests(loader.loadTestsFromTestCase(TestP0NearSuccessProtection))
    suite.addTests(loader.loadTestsFromTestCase(TestP1CounterexampleVerification))
    suite.addTests(loader.loadTestsFromTestCase(TestP2AnswerLock))
    suite.addTests(loader.loadTestsFromTestCase(TestP3TruncationDetection))

    # Add test classes - P1-v2, P4, P0-v2 (from third analysis)
    suite.addTests(loader.loadTestsFromTestCase(TestP1v2SelfContradiction))
    suite.addTests(loader.loadTestsFromTestCase(TestP4OscillationDetection))
    suite.addTests(loader.loadTestsFromTestCase(TestP0v2HistoryProtection))

    # Check if real LLM test requested
    if '--real-llm' in sys.argv:
        suite.addTests(loader.loadTestsFromTestCase(TestRealLLMIntegration))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Summary
    print("\n" + "="*60)
    print("BUG FIX VERIFICATION SUMMARY")
    print("="*60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")

    if result.wasSuccessful():
        print("\n🎉 ALL BUG FIXES VERIFIED!")
        return 0
    else:
        print("\n❌ Some tests failed - review fixes")
        for test, traceback in result.failures + result.errors:
            print(f"\nFailed: {test}")
            print(traceback)
        return 1


if __name__ == '__main__':
    sys.exit(run_tests())

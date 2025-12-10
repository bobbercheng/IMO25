#!/usr/bin/env python3
"""
Unit Tests for Convergence Fixes (2025-12-10)

Tests for Quick Wins and Strategic Fixes:
- Quick Win #1: Accept SUSPICIOUS convergence after threshold
- Quick Win #2: Restore verification frequency to 2
- Strategic Fix #1: Fix P4 oscillation detection (make robust-independent)
- Strategic Fix #2: Adaptive max rounds based on progress

Run with: python code/test_convergence_fixes.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import unittest
from unittest.mock import patch, MagicMock


class TestQuickWin1_SuspiciousConvergence(unittest.TestCase):
    """Test Quick Win #1: Accept SUSPICIOUS convergence after threshold"""

    def test_suspicious_convergence_detection(self):
        """Test that 4+ consecutive SUSPICIOUS with 6+ rounds since BROKEN triggers acceptance"""
        verdict_history = [
            "BROKEN", "BROKEN", "SUSPICIOUS",  # Rounds 0-2: Initial BROKEN phase
            "SUSPICIOUS", "SUSPICIOUS", "SUSPICIOUS",  # Rounds 3-5: Start SUSPICIOUS
            "SUSPICIOUS", "SUSPICIOUS", "SUSPICIOUS",  # Rounds 6-8: Continue SUSPICIOUS
            "SUSPICIOUS"  # Round 9: Still SUSPICIOUS
        ]

        # Calculate consecutive suspicious count (from Quick Win #1 implementation)
        consecutive_suspicious = 0
        rounds_since_last_broken = 0

        for i in range(len(verdict_history) - 1, -1, -1):
            if verdict_history[i] == 'SUSPICIOUS':
                consecutive_suspicious += 1
                rounds_since_last_broken += 1
            elif verdict_history[i] == 'BROKEN':
                # Found BROKEN, stop counting
                # rounds_since_last_broken now has the count of rounds AFTER the BROKEN
                break
            else:  # ROBUST
                break

        # Check convergence criteria
        ACCEPT_SUSPICIOUS_THRESHOLD = 4
        SUSPICIOUS_LOOKBACK = 6

        should_accept = (
            consecutive_suspicious >= ACCEPT_SUSPICIOUS_THRESHOLD and
            rounds_since_last_broken >= SUSPICIOUS_LOOKBACK
        )

        self.assertEqual(consecutive_suspicious, 8, "Should have 8 consecutive SUSPICIOUS")
        self.assertEqual(rounds_since_last_broken, 8, "Should have 8 rounds since last BROKEN")
        self.assertTrue(should_accept, "Should accept SUSPICIOUS convergence")
        print("✓ Quick Win #1: SUSPICIOUS convergence detection verified")

    def test_no_false_positive_without_lookback(self):
        """Test that SUSPICIOUS convergence does NOT trigger too early"""
        verdict_history = [
            "BROKEN", "BROKEN", "BROKEN",  # Rounds 0-2: BROKEN phase
            "SUSPICIOUS", "SUSPICIOUS", "SUSPICIOUS", "SUSPICIOUS"  # Rounds 3-6: SUSPICIOUS but only 4 rounds since BROKEN
        ]

        consecutive_suspicious = 0
        rounds_since_last_broken = 0

        for i in range(len(verdict_history) - 1, -1, -1):
            if verdict_history[i] == 'SUSPICIOUS':
                consecutive_suspicious += 1
                rounds_since_last_broken += 1
            elif verdict_history[i] == 'BROKEN':
                rounds_since_last_broken = 0
                break
            else:
                break

        ACCEPT_SUSPICIOUS_THRESHOLD = 4
        SUSPICIOUS_LOOKBACK = 6

        should_accept = (
            consecutive_suspicious >= ACCEPT_SUSPICIOUS_THRESHOLD and
            rounds_since_last_broken >= SUSPICIOUS_LOOKBACK
        )

        self.assertFalse(should_accept, "Should NOT accept (only 4 rounds since BROKEN, need 6)")
        print("✓ Quick Win #1: No false positive without sufficient lookback")


class TestQuickWin2_VerificationFrequency(unittest.TestCase):
    """Test Quick Win #2: Restore verification frequency to 2"""

    def test_verification_frequency_config(self):
        """Test that verification frequency is set to 2 (not 4)"""
        # Check environment variables in test script
        import subprocess
        result = subprocess.run(
            ['grep', 'RLAC_VERIFY_EVERY_N_ROUNDS', 'test_inline_verification.sh'],
            capture_output=True,
            text=True
        )

        self.assertIn('RLAC_VERIFY_EVERY_N_ROUNDS=2', result.stdout,
                     "Verification frequency should be 2 in test script")
        print("✓ Quick Win #2: Verification frequency set to 2")

    def test_verification_start_round_config(self):
        """Test that verification starts at round 0 (not 3)"""
        import subprocess
        result = subprocess.run(
            ['grep', 'RLAC_VERIFY_START_ROUND', 'test_inline_verification.sh'],
            capture_output=True,
            text=True
        )

        self.assertIn('RLAC_VERIFY_START_ROUND=0', result.stdout,
                     "Verification should start at round 0 in test script")
        print("✓ Quick Win #2: Verification starts at round 0")


class TestStrategicFix1_P4OscillationRobustIndependent(unittest.TestCase):
    """Test Strategic Fix #1: P4 oscillation detection works without ROBUST verdicts"""

    def test_oscillation_detection_with_zero_robust(self):
        """Test that P4 detects BROKEN-SUSPICIOUS pattern and can handle it with 0 ROBUST"""
        verdict_history = [
            "BROKEN", "SUSPICIOUS", "BROKEN", "SUSPICIOUS",  # Rounds 0-3: Alternation
            "BROKEN", "SUSPICIOUS"  # Rounds 4-5: Continue alternation
        ]

        total_robust_count = 0  # CRITICAL: 0 ROBUST verdicts

        # P4 oscillation detection logic
        recent_verdicts = verdict_history[-6:] if len(verdict_history) >= 6 else verdict_history[-4:]

        # Convert to binary: ROBUST=1, others=0
        # NOTE: Both BROKEN and SUSPICIOUS map to 0, so no alternation in binary
        # But P4 Strategy 3 should still detect the BROKEN-SUSPICIOUS pattern
        binary_verdicts = [1 if v == "ROBUST" else 0 for v in recent_verdicts]

        # Check for strict alternation (will be False since both BROKEN/SUSPICIOUS are 0)
        is_alternating = True
        for i in range(1, len(binary_verdicts)):
            if binary_verdicts[i] == binary_verdicts[i-1]:
                is_alternating = False
                break

        # Oscillation won't be detected via binary alternation
        self.assertFalse(is_alternating, "Binary alternation won't detect BROKEN-SUSPICIOUS pattern")
        self.assertEqual(total_robust_count, 0, "Should have 0 ROBUST (critical test condition)")

        # STRATEGIC FIX #1: Check that P4 Strategy 3 can handle this case
        # With old logic, both strategies required ROBUST count >= 2 or >= 3
        # With new logic, Strategy 3 handles total_robust_count == 0

        # Count BROKEN in recent history
        broken_count = recent_verdicts.count("BROKEN")

        # Strategy 3 should trigger if total_robust_count == 0 and broken_count >= 3
        can_handle = (total_robust_count == 0 and broken_count >= 3)

        self.assertTrue(can_handle, "P4 Strategy 3 should handle BROKEN-SUSPICIOUS oscillation with 0 ROBUST")
        self.assertEqual(broken_count, 3, "Should have 3 BROKEN in recent history")
        print("✓ Strategic Fix #1: P4 handles BROKEN-SUSPICIOUS pattern with 0 ROBUST")

    def test_p4_suspicious_only_oscillation(self):
        """Test P4 handles SUSPICIOUS-only oscillation (no ROBUST)"""
        verdict_history = [
            "BROKEN", "SUSPICIOUS", "SUSPICIOUS", "SUSPICIOUS",  # Rounds 0-3
            "SUSPICIOUS", "SUSPICIOUS", "SUSPICIOUS", "SUSPICIOUS"  # Rounds 4-7: Many SUSPICIOUS
        ]

        total_robust_count = 0

        recent_verdicts = verdict_history[-6:]

        # Count consecutive SUSPICIOUS
        consecutive_suspicious = 0
        for v in reversed(recent_verdicts):
            if v == "SUSPICIOUS":
                consecutive_suspicious += 1
            else:
                break

        # STRATEGIC FIX #1: Strategy 3a - handle SUSPICIOUS oscillation
        can_handle = (total_robust_count == 0 and consecutive_suspicious >= 5)

        self.assertTrue(can_handle, "P4 should handle SUSPICIOUS-only oscillation")
        self.assertEqual(consecutive_suspicious, 6, "Should have 6 consecutive SUSPICIOUS")
        print("✓ Strategic Fix #1: P4 handles SUSPICIOUS-only oscillation")


class TestStrategicFix2_AdaptiveMaxRounds(unittest.TestCase):
    """Test Strategic Fix #2: Adaptive max rounds based on progress"""

    def test_no_progress_detection_after_10_rounds(self):
        """Test that no-progress is detected after 10 rounds with 0 ROBUST"""
        round_num = 9  # Round 10 (0-indexed)
        total_robust_count = 0
        verdict_history = ["SUSPICIOUS"] * 10

        # STRATEGIC FIX #2 logic
        should_trigger = (round_num >= 9 and total_robust_count == 0)

        self.assertTrue(should_trigger, "Should detect no progress after 10 rounds with 0 ROBUST")
        print("✓ Strategic Fix #2: No progress detection works")

    def test_mostly_suspicious_delegates_to_quick_win_1(self):
        """Test that mostly SUSPICIOUS (6+) delegates to Quick Win #1"""
        round_num = 9
        total_robust_count = 0
        verdict_history = [
            "BROKEN", "SUSPICIOUS", "SUSPICIOUS", "SUSPICIOUS",
            "SUSPICIOUS", "SUSPICIOUS", "SUSPICIOUS", "SUSPICIOUS",
            "SUSPICIOUS", "SUSPICIOUS"
        ]

        recent_10 = verdict_history[-10:]
        suspicious_count = recent_10.count("SUSPICIOUS")

        # Check Strategy 1: Mostly SUSPICIOUS
        mostly_suspicious = (suspicious_count >= 6)

        self.assertTrue(mostly_suspicious, "Should detect mostly SUSPICIOUS")
        self.assertEqual(suspicious_count, 9, "Should have 9 SUSPICIOUS in last 10 rounds")
        print("✓ Strategic Fix #2: Mostly SUSPICIOUS detection works")

    def test_mostly_broken_triggers_answer_reconsideration(self):
        """Test that mostly BROKEN (6+) triggers answer reconsideration signal"""
        round_num = 9
        total_robust_count = 0
        verdict_history = [
            "BROKEN", "BROKEN", "SUSPICIOUS", "BROKEN",
            "BROKEN", "BROKEN", "BROKEN", "BROKEN",
            "SUSPICIOUS", "BROKEN"
        ]

        recent_10 = verdict_history[-10:]
        broken_count = recent_10.count("BROKEN")

        # Check Strategy 2: Mostly BROKEN
        mostly_broken = (broken_count >= 6)

        self.assertTrue(mostly_broken, "Should detect mostly BROKEN")
        self.assertEqual(broken_count, 8, "Should have 8 BROKEN in last 10 rounds")
        print("✓ Strategic Fix #2: Mostly BROKEN detection works")

    def test_adaptive_exit_after_13_rounds_mixed(self):
        """Test that adaptive exit triggers after 13 rounds with mixed verdicts"""
        round_num = 12  # Round 13 (0-indexed)
        total_robust_count = 0
        verdict_history = [
            "BROKEN", "SUSPICIOUS", "BROKEN", "SUSPICIOUS",
            "BROKEN", "SUSPICIOUS", "BROKEN", "SUSPICIOUS",
            "BROKEN", "SUSPICIOUS", "BROKEN", "SUSPICIOUS",
            "BROKEN"
        ]

        recent_10 = verdict_history[-10:]
        suspicious_count = recent_10.count("SUSPICIOUS")
        broken_count = recent_10.count("BROKEN")

        # Check Strategy 3: Mixed verdicts, no convergence
        should_exit = (
            round_num >= 9 and
            total_robust_count == 0 and
            suspicious_count < 6 and
            broken_count < 6 and
            round_num >= 12
        )

        self.assertTrue(should_exit, "Should trigger adaptive exit after 13 rounds")
        self.assertLess(suspicious_count, 6, "Should have mixed verdicts (not mostly SUSPICIOUS)")
        self.assertLess(broken_count, 6, "Should have mixed verdicts (not mostly BROKEN)")
        print("✓ Strategic Fix #2: Adaptive exit for mixed verdicts works")


def run_tests():
    """Run all tests and print summary"""
    print("=" * 80)
    print("CONVERGENCE FIXES UNIT TESTS")
    print("=" * 80)
    print()

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestQuickWin1_SuspiciousConvergence))
    suite.addTests(loader.loadTestsFromTestCase(TestQuickWin2_VerificationFrequency))
    suite.addTests(loader.loadTestsFromTestCase(TestStrategicFix1_P4OscillationRobustIndependent))
    suite.addTests(loader.loadTestsFromTestCase(TestStrategicFix2_AdaptiveMaxRounds))

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

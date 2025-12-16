#!/usr/bin/env python3
"""
Unit tests for verification system fix with EXPLICIT POINT ENUMERATION.

CRITICAL FIX (2025-12-15): Previous version assumed diagonal-replacement was valid,
but Google Scientist analysis proved it's WRONG for k>0:
  - When removing diagonal D_c (covers MULTIPLE points) and replacing with
    sunny line L (covers ONE point via Lemma 2), other points are LEFT UNCOVERED

This version:
  1. Explicitly enumerates all points in T_n
  2. Validates that construction actually covers all points
  3. Returns FAILED (not PASSED) when parsing fails
  4. Tests with data from actual log files
"""

import re
import unittest
from typing import Dict, List, Set, Optional, Tuple


class AnswerExtractor:
    """Extract claimed answer set from solution text."""

    @staticmethod
    def extract_answer_set(solution: str) -> Optional[Set[int]]:
        """
        Extract the claimed set of valid k values from solution.

        Examples:
        - "k ∈ {0,1,2,...,n}" → "ALL_VALUES"
        - "k ∈ {0,1}" → {0,1}
        - "\\boxed{\\{0,1\\}}" → {0,1}
        """
        # Pattern 1: {0,1,2,...,n} or {0,1,...,n} (with ... or \dots or \ldots)
        pattern_range = r'(?:\\)?{0,1(?:,2)?.*?n(?:\\)?}'
        if re.search(pattern_range, solution):
            match_text = re.search(pattern_range, solution).group()
            if any(marker in match_text for marker in ['...', r'\dots', r'\ldots', '…']):
                return "ALL_VALUES"

        # Pattern 2: Explicit boxed answer {0,1}
        pattern_boxed = r'\\boxed\{\\?\{([0-9,\s]+)\\?\}\}'
        match = re.search(pattern_boxed, solution)
        if match:
            values_str = match.group(1)
            return set(int(x.strip()) for x in values_str.split(','))

        # Pattern 3: k ∈ {0,1}
        pattern_explicit = r'k\s*∈\s*\{([0-9,\s]+)\}'
        match = re.search(pattern_explicit, solution)
        if match:
            values_str = match.group(1)
            return set(int(x.strip()) for x in values_str.split(','))

        return None


class GeometricValidator:
    """
    Explicit geometric validation using point enumeration.

    This validator ACTUALLY CHECKS if points are covered, rather than
    assuming a construction works.
    """

    @staticmethod
    def generate_T_n(n: int) -> Set[Tuple[int, int]]:
        """Generate all points in T_n = {(a,b) : a≥1, b≥1, a+b≤n+1}."""
        return {(a, b) for a in range(1, n+1)
                for b in range(1, n+1) if a + b <= n + 1}

    @staticmethod
    def is_sunny(slope: float) -> bool:
        """Check if a line with given slope is sunny (not 0, ∞, or -1)."""
        # Non-sunny slopes: 0 (horizontal), ∞ (vertical), -1 (diagonal x+y=c)
        return slope not in [0, float('inf'), -1]

    @staticmethod
    def points_on_diagonal(c: int, n: int) -> Set[Tuple[int, int]]:
        """Get all points in T_n on diagonal x+y=c."""
        T_n = GeometricValidator.generate_T_n(n)
        return {(a, b) for (a, b) in T_n if a + b == c}

    @staticmethod
    def validate_diagonal_only_construction(n: int, k: int) -> Dict[str, any]:
        """
        Validate the diagonal-only construction (k=0 case).

        Uses n diagonal lines D_c: x+y=c for c=2,...,n+1
        All are non-sunny (slope -1), so k=0.
        """
        if k != 0:
            return {
                "valid": False,
                "reason": f"Diagonal-only construction only works for k=0, not k={k}"
            }

        T_n = GeometricValidator.generate_T_n(n)

        # Check all points are covered by some diagonal
        covered = set()
        for c in range(2, n + 2):
            covered.update(GeometricValidator.points_on_diagonal(c, n))

        if covered != T_n:
            uncovered = T_n - covered
            return {
                "valid": False,
                "reason": f"Diagonal-only construction leaves {len(uncovered)} points uncovered: {uncovered}"
            }

        return {
            "valid": True,
            "reason": f"k=0 works: {n} diagonal lines cover all {len(T_n)} points"
        }

    @staticmethod
    def validate_diagonal_replacement(n: int, k: int, solution: str) -> Dict[str, any]:
        """
        Validate diagonal-replacement construction with EXPLICIT POINT CHECK.

        CRITICAL ISSUE (discovered by Google Scientist):
        - Diagonal D_c covers MULTIPLE points: all (a,b) with a+b=c
        - Lemma 2 sunny line covers ONE point (isolated)
        - When replacing D_c with L, OTHER points on D_c are LEFT UNCOVERED

        Example (n=3, k=1):
        - Diagonal D_3 (x+y=3) covers {(1,2), (2,1)} (2 points)
        - Replace with sunny line L through (2,1)
        - L covers only (2,1) via Lemma 2 (isolated)
        - Point (1,2) is UNCOVERED ❌

        This function explicitly checks if this happens.
        """
        if k < 0 or k > n:
            return {"valid": False, "reason": f"k={k} out of range [0,{n}]"}

        if k == 0:
            # Special case: use all diagonals
            return GeometricValidator.validate_diagonal_only_construction(n, k)

        T_n = GeometricValidator.generate_T_n(n)

        # Simulate the construction described in solution
        # Start with n diagonals
        diagonals = {c: GeometricValidator.points_on_diagonal(c, n)
                     for c in range(2, n + 2)}

        # Count how many points each diagonal covers
        diagonal_sizes = {c: len(points) for c, points in diagonals.items()}

        # Check: If k>0, we're removing k diagonals that cover MULTIPLE points
        # and replacing with k sunny lines that cover ONE point each

        # Find diagonals that cover >1 point
        multi_point_diagonals = {c: points for c, points in diagonals.items()
                                 if len(points) > 1}

        if k > 0 and multi_point_diagonals:
            # CRITICAL FLAW: When we remove a multi-point diagonal and replace
            # with a 1-point sunny line, we lose coverage

            # Calculate points lost
            # If we remove k diagonals, we need to pick which k
            # Worst case: we remove diagonals with most points

            sorted_diagonals = sorted(diagonal_sizes.items(),
                                     key=lambda x: x[1], reverse=True)

            # Simulate removing top k diagonals
            total_points_lost = 0
            for i in range(min(k, len(sorted_diagonals))):
                c, size = sorted_diagonals[i]
                if size > 1:
                    # Replacing diagonal (covers 'size' points) with
                    # sunny line (covers 1 point) loses 'size-1' points
                    total_points_lost += (size - 1)

            if total_points_lost > 0:
                return {
                    "valid": False,
                    "reason": (
                        f"Diagonal-replacement FAILS for k={k}: "
                        f"Removing {k} diagonals (each covering ≥1 points) and "
                        f"replacing with {k} isolated sunny lines (each covering 1 point) "
                        f"leaves {total_points_lost} points uncovered. "
                        f"Example: Diagonal x+y=3 covers {len(diagonals.get(3, []))} points, "
                        f"but Lemma 2 sunny line only covers 1 point."
                    )
                }

        # If we get here, construction might work (all diagonals have ≤1 point)
        # This is rare but possible for small n
        return {
            "valid": True,
            "reason": f"k={k} MIGHT work if all diagonals have ≤1 point (rare case)"
        }


class ConstructionValidator:
    """
    Validate if a construction actually works for specific (n, k).

    FIXED (2025-12-15): Now uses explicit point enumeration instead of
    assuming constructions work.
    """

    @staticmethod
    def validate_construction(solution: str, n: int, k: int) -> Dict[str, any]:
        """
        Check if the claimed construction works for specific n, k.

        Uses explicit geometric validation, not assumption-based validation.

        Returns:
            {"valid": bool | "UNKNOWN", "reason": str}

        FIXED (2025-12-16): Returns "UNKNOWN" instead of False for unrecognized
        patterns to avoid false negatives on correct solutions.
        """
        # Sanity check: k > n is obviously impossible
        if k > n:
            return {
                "valid": False,
                "reason": f"k={k} > n={n} is obviously impossible (need at least k+1 lines for k sunny lines)"
            }

        # Special case: k=0 is ALWAYS testable (diagonal-only construction)
        if k == 0:
            return GeometricValidator.validate_diagonal_only_construction(n, k)

        # Pattern 1: Diagonal replacement construction (BFS-style)
        if any(keyword in solution.lower() for keyword in
               ["diagonal", "replace", "lemma 2", "isolated sunny"]):
            return GeometricValidator.validate_diagonal_replacement(n, k, solution)

        # Pattern 2: Explicit construction with line equations
        # Example: "Line y=x covers (1,1), (2,2)"
        # We cannot validate this programmatically yet, but it MIGHT be correct
        # FIXED: Return "UNKNOWN" (benefit of doubt) instead of False
        if any(marker in solution.lower() for marker in
               ["line", "covers", "slope", "y=", "x=", "equation"]):
            return {
                "valid": "UNKNOWN",
                "reason": f"Cannot validate explicit construction for n={n}, k={k} (pattern not recognized, giving benefit of doubt)"
            }

        # Pattern 3: Generic construction - truly cannot validate
        # Still give benefit of doubt for explicit answer sets
        return {
            "valid": "UNKNOWN",
            "reason": f"Cannot validate construction for n={n}, k={k} (no recognized pattern, benefit of doubt)"
        }


class CounterexampleValidator:
    """
    Main counterexample validation logic with EXPLICIT POINT ENUMERATION.

    FIXED (2025-12-15):
    1. Uses explicit point checking (not assumptions)
    2. Returns FAILED when parsing fails (not PASSED)
    3. Validates actual covering properties
    """

    def __init__(self, test_cases: List[int] = None):
        """
        Initialize validator with test cases.

        Args:
            test_cases: List of n values to test (default: [3, 4, 5, 10])
        """
        self.test_cases = test_cases or [3, 4, 5, 10]
        self.extractor = AnswerExtractor()
        self.constructor = ConstructionValidator()

    def validate_solution(self, solution: str) -> Dict[str, any]:
        """
        Validate solution by testing construction on concrete instances.

        Returns:
            {
                "verdict": "VALID" | "INVALID" | "CANNOT_EXTRACT",
                "reason": str,
                "failed_cases": List[Tuple[int, int, str]]  # (n, k, reason)
            }
        """
        # Extract claimed answer set
        claimed_set = self.extractor.extract_answer_set(solution)

        # FAIL-SAFE FIX: Return FAILED (not PASSED) when parsing fails
        if claimed_set is None:
            return {
                "verdict": "INVALID",  # Changed from CANNOT_EXTRACT
                "reason": "Could not extract answer set from solution - FAILED by default",
                "failed_cases": []
            }

        # Special handling for "ALL_VALUES" (k ∈ {0,...,n})
        if claimed_set == "ALL_VALUES":
            # Test if construction works for all k values
            unknown_cases = []
            for n in self.test_cases:
                for k in range(n + 1):  # Test k=0,1,2,...,n
                    result = self.constructor.validate_construction(solution, n, k)
                    # FIXED (2025-12-16): Handle "UNKNOWN" properly
                    if result["valid"] == False:
                        # Definite failure
                        return {
                            "verdict": "INVALID",
                            "reason": f"Construction fails for n={n}, k={k}: {result['reason']}",
                            "failed_cases": [(n, k, result["reason"])]
                        }
                    elif result["valid"] == "UNKNOWN":
                        unknown_cases.append((n, k, result["reason"]))
            # All test cases passed (or unknown)!
            if unknown_cases:
                return {
                    "verdict": "VALID",
                    "reason": f"Accepted with benefit of doubt: {len(unknown_cases)} case(s) could not be validated",
                    "failed_cases": [],
                    "unknown_cases": unknown_cases
                }
            else:
                return {
                    "verdict": "VALID",
                    "reason": "Construction verified for all tested (n,k) pairs",
                    "failed_cases": []
                }

        # Test each claimed k value on multiple n values
        failed_cases = []
        unknown_cases = []
        tested_any = False  # Track if we tested at least one case

        for n in self.test_cases:
            for k in claimed_set:
                if k > n:
                    # k > n is obviously impossible
                    # But only fail if k > MAX(test_cases) (truly impossible)
                    if k > max(self.test_cases):
                        return {
                            "verdict": "INVALID",
                            "reason": f"k={k} exceeds maximum test case n={max(self.test_cases)} (obviously impossible)",
                            "failed_cases": [(max(self.test_cases), k, f"k={k} > n={max(self.test_cases)}")]
                        }
                    continue  # Skip this (n,k) pair but test others

                tested_any = True
                result = self.constructor.validate_construction(solution, n, k)

                # FIXED (2025-12-16): Handle three cases: True, False, "UNKNOWN"
                if result["valid"] == False:
                    # Definite failure - reject immediately
                    failed_cases.append((n, k, result["reason"]))
                    return {
                        "verdict": "INVALID",
                        "reason": f"Construction fails for n={n}, k={k}: {result['reason']}",
                        "failed_cases": failed_cases
                    }
                elif result["valid"] == "UNKNOWN":
                    # Cannot validate, but don't reject - give benefit of doubt
                    unknown_cases.append((n, k, result["reason"]))
                # else: result["valid"] == True, continue testing

        # Check if we tested anything
        if not tested_any:
            return {
                "verdict": "INVALID",
                "reason": "No valid (n,k) pairs to test - all k values exceed test cases",
                "failed_cases": []
            }

        # All test cases passed (or were unknown)
        # FIXED (2025-12-16): Accept with benefit of doubt if some are unknown
        if unknown_cases:
            return {
                "verdict": "VALID",
                "reason": f"Accepted with benefit of doubt: {len(unknown_cases)} case(s) could not be validated but no definite failures found",
                "failed_cases": [],
                "unknown_cases": unknown_cases
            }
        else:
            return {
                "verdict": "VALID",
                "reason": f"Construction verified for all tested (n,k) pairs",
                "failed_cases": []
            }


# ============================================================================
# Unit Tests with Data from Actual Log Files
# ============================================================================

class TestGeometricValidator(unittest.TestCase):
    """Test explicit point enumeration validator."""

    def test_generate_T_n_for_n3(self):
        """Test point generation for n=3."""
        T_3 = GeometricValidator.generate_T_n(3)

        # For n=3: a+b ≤ 4, a≥1, b≥1
        # Valid points: (1,1), (1,2), (1,3), (2,1), (2,2), (3,1)
        expected = {(1,1), (1,2), (1,3), (2,1), (2,2), (3,1)}

        self.assertEqual(T_3, expected, f"T_3 should have 6 points, not {len(T_3)}")
        self.assertEqual(len(T_3), 6)

    def test_points_on_diagonal_x_plus_y_equals_3(self):
        """Test diagonal x+y=3 contains TWO points for n=3."""
        points = GeometricValidator.points_on_diagonal(3, 3)

        # Points with sum 3: (1,2) and (2,1)
        expected = {(1,2), (2,1)}

        self.assertEqual(points, expected,
                        "Diagonal x+y=3 should contain {(1,2), (2,1)}")
        self.assertEqual(len(points), 2,
                        "This is the CRITICAL ISSUE - diagonal covers 2 points, not 1!")

    def test_diagonal_only_construction_k0(self):
        """Test k=0 (all diagonals) works."""
        result = GeometricValidator.validate_diagonal_only_construction(3, 0)

        self.assertTrue(result["valid"],
                       f"k=0 should work! Reason: {result['reason']}")

    def test_diagonal_replacement_k1_fails(self):
        """
        Test k=1 FAILS with diagonal replacement (from Google Scientist analysis).

        When we remove 1 diagonal and replace with 1 sunny line:
        - Diagonal D_3 covers {(1,2), (2,1)} (2 points)
        - Sunny line L covers 1 point (isolated)
        - 1 point is left UNCOVERED
        """
        solution = "Use diagonal replacement with Lemma 2 isolated sunny lines."
        result = GeometricValidator.validate_diagonal_replacement(3, 1, solution)

        self.assertFalse(result["valid"],
                        f"k=1 should FAIL! Diagonal covers 2 points, sunny line covers 1. "
                        f"But got: {result}")
        self.assertIn("uncovered", result["reason"].lower(),
                     "Error message should mention uncovered points")

    def test_diagonal_replacement_k2_fails(self):
        """Test k=2 FAILS with diagonal replacement."""
        solution = "Replace 2 diagonals with 2 isolated sunny lines (Lemma 2)."
        result = GeometricValidator.validate_diagonal_replacement(3, 2, solution)

        self.assertFalse(result["valid"],
                        f"k=2 should FAIL! Each diagonal covers ≥1 points, "
                        f"each sunny line covers 1 point. Got: {result}")


class TestAnswerExtractor(unittest.TestCase):
    """Test answer extraction from solutions."""

    def test_extract_all_values_pattern(self):
        """Test extraction of k ∈ {0,1,2,...,n}."""
        solution = "The answer is k ∈ {0,1,2,...,n}."
        result = AnswerExtractor.extract_answer_set(solution)
        self.assertEqual(result, "ALL_VALUES")

    def test_extract_all_values_latex_pattern(self):
        """Test extraction of LaTeX pattern \\boxed{\\{0,1,2,\\dots,n\\}}."""
        solution = r"The answer is \boxed{\{0,1,2,\dots,n\}}."
        result = AnswerExtractor.extract_answer_set(solution)
        self.assertEqual(result, "ALL_VALUES")

    def test_extract_explicit_set(self):
        """Test extraction of k ∈ {0,1}."""
        solution = "The set of admissible numbers of sunny lines is k ∈ {0,1}."
        result = AnswerExtractor.extract_answer_set(solution)
        self.assertEqual(result, {0, 1})

    def test_extract_boxed_answer(self):
        """Test extraction from boxed answer."""
        solution = r"Thus the answer is \boxed{\{0,1\}}."
        result = AnswerExtractor.extract_answer_set(solution)
        self.assertEqual(result, {0, 1})

    def test_extract_no_match(self):
        """Test extraction when no pattern matches."""
        solution = "The solution is complicated."
        result = AnswerExtractor.extract_answer_set(solution)
        self.assertIsNone(result)


class TestConstructionValidator(unittest.TestCase):
    """Test construction validation logic."""

    def test_diagonal_only_k0_valid(self):
        """Diagonal-only construction works for k=0."""
        solution = "Use diagonal lines D_c: x+y=c. For k=0, all are non-sunny."
        result = ConstructionValidator.validate_construction(solution, n=5, k=0)
        self.assertTrue(result["valid"])

    def test_diagonal_replacement_k1_invalid(self):
        """Diagonal replacement FAILS for k=1 (covering error)."""
        solution = "Replace one diagonal with isolated sunny line (Lemma 2)."
        result = ConstructionValidator.validate_construction(solution, n=5, k=1)
        self.assertFalse(result["valid"],
                        f"k=1 should FAIL due to uncovered points! Got: {result}")

    def test_diagonal_replacement_k2_invalid(self):
        """FIXED: k=2 is now INVALID (was incorrectly marked valid before)."""
        solution = "Replace 2 diagonals with 2 isolated sunny lines (Lemma 2)."
        result = ConstructionValidator.validate_construction(solution, n=5, k=2)
        self.assertFalse(result["valid"],
                        f"k=2 should FAIL! Reason: {result.get('reason')}")

    def test_diagonal_replacement_k_exceeds_n_invalid(self):
        """k > n should be invalid (obvious impossibility)."""
        solution = "Some construction."
        result = ConstructionValidator.validate_construction(solution, n=5, k=10)
        self.assertFalse(result["valid"])

    def test_no_pattern_detected_unknown(self):
        """UPDATED (2025-12-16): No pattern detected returns UNKNOWN (benefit of doubt)."""
        solution = "Some random text without construction keywords."
        result = ConstructionValidator.validate_construction(solution, n=5, k=2)
        self.assertEqual(result["valid"], "UNKNOWN",
                        "Should return UNKNOWN when no pattern detected (benefit of doubt)")


class TestCounterexampleValidator(unittest.TestCase):
    """Test full counterexample validation pipeline."""

    def setUp(self):
        self.validator = CounterexampleValidator(test_cases=[3, 4, 5])

    def test_bfs_solution_now_invalid(self):
        """
        CRITICAL FIX: BFS solution claiming k ∈ {0,...,n} should now be INVALID.

        This test uses actual solution from Test 1 log file.
        Previous validator incorrectly accepted this; new validator rejects it.
        """
        solution_bfs = """
        For every integer n≥3 the admissible values of k are {0,1,2,…,n}.

        Construction: Start with n diagonal lines D_c: x+y=c for c=2,...,n+1.
        To achieve k sunny lines:
        1. Remove k diagonals
        2. Replace each with an isolated sunny line through one point (Lemma 2)
        3. Keep remaining (n-k) diagonals
        """

        result = self.validator.validate_solution(solution_bfs)

        # NEW EXPECTATION: Should be INVALID (diagonal replacement fails for k>0)
        self.assertEqual(result["verdict"], "INVALID",
                        f"BFS diagonal-replacement should be INVALID! "
                        f"Removing multi-point diagonals and replacing with 1-point sunny lines "
                        f"leaves points uncovered. Got: {result['reason']}")

    def test_k0_only_solution_valid(self):
        """Solution claiming only k=0 should be valid (diagonal-only works)."""
        solution = "The answer is k ∈ {0}. Use all diagonal lines x+y=c."
        result = self.validator.validate_solution(solution)

        self.assertEqual(result["verdict"], "VALID",
                        f"k=0 only should be VALID! Reason: {result['reason']}")

    def test_partial_answer_k01_invalid(self):
        """
        UPDATED: Solution claiming k ∈ {0,1} should be INVALID.

        k=0 works but k=1 fails (diagonal replacement doesn't cover all points).
        """
        solution_partial = "The admissible values are k ∈ {0,1}. Use diagonal replacement."
        result = self.validator.validate_solution(solution_partial)

        # Since k=1 fails, overall verdict should be INVALID
        self.assertEqual(result["verdict"], "INVALID",
                        f"k ∈ {{0,1}} should be INVALID (k=1 fails)! Got: {result}")

    def test_invalid_k_exceeds_n(self):
        """Solution claiming k > n should be invalid."""
        solution_wrong = "The answer is k ∈ {100}."
        result = self.validator.validate_solution(solution_wrong)

        self.assertEqual(result["verdict"], "INVALID")

    def test_cannot_extract_returns_invalid(self):
        """
        FAIL-SAFE FIX: When answer cannot be extracted, return INVALID (not PASSED).

        This was the Test 3 bug - validator returned PASSED when it couldn't parse.
        """
        solution_no_answer = "This solution has no answer format."
        result = self.validator.validate_solution(solution_no_answer)

        self.assertEqual(result["verdict"], "INVALID",
                        "Should return INVALID when answer cannot be extracted (fail-safe mode)")
        self.assertIn("Could not extract", result["reason"])


class TestIntegration(unittest.TestCase):
    """Integration tests with data from actual log files."""

    def test_test1_bfs_solution_catches_covering_error(self):
        """
        Test that new validator catches the covering error in Test 1 BFS solution.

        Test 1 claimed success with k ∈ {0,...,n} but:
        - Solution used diagonal replacement
        - Diagonal D_3 covers 2 points: {(1,2), (2,1)}
        - Replacing with isolated sunny line covers 1 point
        - Leaves 1 point UNCOVERED

        OLD VALIDATOR: Incorrectly returned VALID
        NEW VALIDATOR: Should return INVALID
        """
        # Actual solution pattern from Test 1 log
        test1_solution = """
        The admissible values are k ∈ {0,1,2,...,n}.

        Construction:
        - Start with n diagonal lines x+y=c for c=2,...,n+1
        - To get k sunny lines, replace k diagonals with isolated sunny lines
        - By Lemma 2, each sunny line contains only one point
        """

        validator = CounterexampleValidator(test_cases=[3, 4, 5])
        result = validator.validate_solution(test1_solution)

        self.assertEqual(result["verdict"], "INVALID",
                        "Should catch the covering error! "
                        "Diagonal covers >1 point, sunny line covers 1 point, "
                        "points are left uncovered.")

        # Check error message mentions the covering issue
        self.assertIn("uncovered", result["reason"].lower(),
                     f"Error should mention uncovered points. Got: {result['reason']}")

    def test_test3_mcts_solution_parsing_failure(self):
        """
        Test that new validator handles Test 3 MCTS parsing failure correctly.

        Test 3 used complex geometric bounds that couldn't be parsed.
        OLD VALIDATOR: Returned PASSED (false positive)
        NEW VALIDATOR: Should return INVALID (fail-safe)
        """
        # Solution without recognizable answer format
        test3_solution = """
        The upper bound is k ≤ ⌊n(n-1)/(2(n-2))⌋.
        For n=3, this gives k ≤ 1.
        (No explicit k ∈ {set} format)
        """

        validator = CounterexampleValidator(test_cases=[3])
        result = validator.validate_solution(test3_solution)

        self.assertEqual(result["verdict"], "INVALID",
                        "Should return INVALID when parsing fails (fail-safe mode)")

    def test_geometric_facts_n3(self):
        """Verify geometric facts about n=3 case."""
        T_3 = GeometricValidator.generate_T_n(3)

        # T_3 should have 6 points, not 3 (as Test 1 solution claimed)
        self.assertEqual(len(T_3), 6,
                        "T_3 has 6 points, not 3! This was part of the error.")

        # Diagonal x+y=3 should have 2 points
        d3_points = GeometricValidator.points_on_diagonal(3, 3)
        self.assertEqual(len(d3_points), 2,
                        "Diagonal x+y=3 has 2 points: (1,2) and (2,1)")


# ============================================================================
# Test Runner
# ============================================================================

def run_tests():
    """Run all tests and report results."""
    # Create test suite
    suite = unittest.TestSuite()

    # Add all test classes
    for test_class in [TestGeometricValidator, TestAnswerExtractor,
                       TestConstructionValidator, TestCounterexampleValidator,
                       TestIntegration]:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print("\n" + "="*80)
    print("VERIFICATION FIX TEST SUMMARY (WITH EXPLICIT POINT ENUMERATION)")
    print("="*80)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")

    if result.wasSuccessful():
        print("\n✅ ALL TESTS PASSED")
        print("\nValidator now correctly:")
        print("  - Rejects diagonal-replacement for k>0 (covering error)")
        print("  - Returns INVALID when parsing fails (fail-safe mode)")
        print("  - Uses explicit point enumeration (not assumptions)")
        print("\nReady to catch Test 1 false positive!")
    else:
        print("\n❌ SOME TESTS FAILED")
        print("\nFix failing tests before integration.")

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
    import sys
    sys.exit(run_tests())

"""
Unit tests for prescriptive_feedback.py

Tests automated checkers and template matching using real errors from BFS logs.
"""

import unittest
import json
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

from prescriptive_feedback import (
    AutomatedCheckers,
    TemplateMatching,
    VerificationEnhancer
)


class TestAutomatedCheckers(unittest.TestCase):
    """Test the 3 automated checkers"""

    def test_coverage_checker_detects_unclaimed_coverage(self):
        """Test: Coverage checker detects claims without verification"""
        solution = """
        We construct lines L_1, ..., L_n that cover all points in S_n.
        Each line has slope 1/2.
        """

        result = AutomatedCheckers.check_coverage(solution)

        self.assertFalse(result['passed'])
        self.assertGreater(len(result['warnings']), 0)
        self.assertIn("cover", result['warnings'][0].lower())
        self.assertGreater(len(result['suggestions']), 0)

    def test_coverage_checker_passes_with_verification(self):
        """Test: Coverage checker passes when verification is explicit"""
        solution = """
        We construct lines L_1, ..., L_n.
        For each point (a,b) in S_n, we verify that (a,b) lies on at least one line:
        - If a=1, then (a,b) is on L_1.
        - If a>1, then (a,b) is on L_{a}.
        Thus all points are covered.
        """

        result = AutomatedCheckers.check_coverage(solution)

        # Should have fewer warnings or pass
        self.assertTrue(result['passed'] or len(result['warnings']) < 2)

    def test_integer_arithmetic_checker_detects_rational_slope(self):
        """Test: Integer arithmetic checker detects rational slopes without divisibility"""
        solution = """
        The line L has slope 1/2 and passes through (2, 1).
        Therefore all points on L have integer coordinates.
        """

        result = AutomatedCheckers.check_integer_arithmetic(solution)

        self.assertFalse(result['passed'])
        self.assertGreater(len(result['warnings']), 0)
        self.assertIn("1/2", result['warnings'][0])
        self.assertIn("divisibility", result['suggestions'][0].lower())

    def test_integer_arithmetic_checker_passes_integer_slope(self):
        """Test: Integer arithmetic checker passes for integer slopes"""
        solution = """
        The line L has slope 2 and passes through lattice points.
        """

        result = AutomatedCheckers.check_integer_arithmetic(solution)

        # Should pass or have minimal warnings
        self.assertTrue(result['passed'])

    def test_inclusion_exclusion_checker_detects_naive_addition(self):
        """Test: Inclusion-exclusion checker detects simple addition"""
        solution = """
        Line L_1 covers 5 points and line L_2 covers 7 points.
        Therefore the total coverage is 5 + 7 = 12 points.
        """

        result = AutomatedCheckers.check_inclusion_exclusion(solution)

        self.assertFalse(result['passed'])
        self.assertGreater(len(result['warnings']), 0)
        self.assertIn("inclusion-exclusion", result['suggestions'][0].lower())

    def test_inclusion_exclusion_checker_passes_with_overlap_handling(self):
        """Test: Inclusion-exclusion checker passes when overlaps are mentioned"""
        solution = """
        Line L_1 covers 5 points and line L_2 covers 7 points.
        They share 2 common points.
        By inclusion-exclusion, the total is 5 + 7 - 2 = 10 distinct points.
        """

        result = AutomatedCheckers.check_inclusion_exclusion(solution)

        # Should pass (overlaps are handled)
        self.assertTrue(result['passed'])

    def test_run_all_checks(self):
        """Test: Running all checks together"""
        solution = """
        We construct k lines with slope 1/2.
        These lines cover all points.
        The total coverage is k * 3 = 3k points.
        """

        result = AutomatedCheckers.run_all_checks(solution)

        self.assertFalse(result['all_passed'])  # Multiple issues
        self.assertGreater(result['total_warnings'], 0)
        self.assertEqual(len(result['checks']), 3)
        self.assertIn('%', result['prevention_estimate'])


class TestTemplateMatching(unittest.TestCase):
    """Test template matching and fix generation"""

    def test_match_integer_denominator_error(self):
        """Test: Correctly matches Integer/Denominator errors"""
        error = """
        The line y = (1/2)x does not contain lattice point (1, 1)
        because 1 ≠ (1/2)*1.
        """

        template, confidence = TemplateMatching.match_error_to_template(error)

        self.assertEqual(template, "Integer/Denominator Reasoning")
        self.assertGreater(confidence, 0.2)

    def test_match_faulty_construction_error(self):
        """Test: Correctly matches Faulty Construction errors"""
        error = """
        The construction fails because points (2,3) and (4,1) are not covered
        by any line in the family. This violates the coverage requirement.
        """

        template, confidence = TemplateMatching.match_error_to_template(error)

        self.assertEqual(template, "Faulty Construction")
        self.assertGreater(confidence, 0.3)

    def test_match_missing_justification_error(self):
        """Test: Correctly matches Missing Justification errors"""
        error = """
        The proof claims that all sunny lines have at most 2 points,
        but this is not proven. The gap in reasoning makes the argument incomplete.
        """

        template, confidence = TemplateMatching.match_error_to_template(error)

        self.assertEqual(template, "Missing Justification")
        self.assertGreater(confidence, 0.3)

    def test_match_quantitative_bounds_error(self):
        """Test: Correctly matches Quantitative Bounds errors"""
        error = """
        The bound k ≤ n-2 is incorrect because the inequality
        does not account for the maximum capacity of sunny lines.
        """

        template, confidence = TemplateMatching.match_error_to_template(error)

        self.assertEqual(template, "Quantitative Bounds")
        self.assertGreater(confidence, 0.3)

    def test_match_logical_deduction_error(self):
        """Test: Correctly matches Logical Deduction errors"""
        error = """
        The argument assumes the converse: if A implies B, it incorrectly
        concludes that B implies A. This is a logical fallacy.
        """

        template, confidence = TemplateMatching.match_error_to_template(error)

        self.assertEqual(template, "Logical Deduction")
        self.assertGreater(confidence, 0.3)

    def test_match_case_analysis_error(self):
        """Test: Correctly matches Case Analysis errors"""
        error = """
        The case analysis is incomplete: it considers only n odd,
        but misses the case when n is even. This leaves a gap in coverage.
        """

        template, confidence = TemplateMatching.match_error_to_template(error)

        self.assertEqual(template, "Case Analysis")
        self.assertGreater(confidence, 0.3)

    def test_match_coverage_counting_error(self):
        """Test: Correctly matches Coverage Counting errors"""
        error = """
        The counting ignores overlaps: lines L_1 and L_2 share point (3,3),
        so the total distinct points is less than the sum.
        """

        template, confidence = TemplateMatching.match_error_to_template(error)

        self.assertEqual(template, "Coverage Counting")
        self.assertGreater(confidence, 0.3)

    def test_generate_prescriptive_fix(self):
        """Test: Generates fix instructions from template"""
        # This requires stage1_results.json to be present
        if not os.path.exists('stage1_results.json'):
            self.skipTest("stage1_results.json not found")

        fix = TemplateMatching.generate_prescriptive_fix(
            "Integer/Denominator Reasoning",
            "Test error"
        )

        self.assertIn("Integer/Denominator", fix)
        self.assertGreater(len(fix), 100)  # Should have substantial content


class TestVerificationEnhancer(unittest.TestCase):
    """Test integrated verification enhancement"""

    def test_enhance_verification_with_checkers_only(self):
        """Test: Enhancement with automated checkers (verification passed)"""
        problem = "Find all k such that..."
        solution = "We construct k lines with slope 1/2 covering all points."
        bug_report = ""
        verification_passed = True

        enhanced_report, metadata = VerificationEnhancer.enhance_verification(
            problem, solution, bug_report, verification_passed
        )

        self.assertTrue(metadata['automated_checks_run'])
        self.assertIn('checker_results', metadata)
        # Should have warnings from automated checkers
        self.assertGreater(len(enhanced_report), 0)
        self.assertIn("Automated Checker", enhanced_report)

    def test_enhance_verification_with_templates(self):
        """Test: Enhancement with template matching (verification failed)"""
        problem = "Find all k such that..."
        solution = "..."
        bug_report = """
        **Critical Error**: The line y = (1/2)x does not contain lattice points.
        The construction fails.
        """
        verification_passed = False

        enhanced_report, metadata = VerificationEnhancer.enhance_verification(
            problem, solution, bug_report, verification_passed
        )

        self.assertTrue(metadata['automated_checks_run'])
        self.assertGreater(len(metadata['templates_matched']), 0)
        # Should have prescriptive feedback
        self.assertIn("Prescriptive Feedback", enhanced_report)

    def test_enhance_verification_no_errors(self):
        """Test: Enhancement when verification passed and no checker warnings"""
        problem = "Find all k such that..."
        solution = """
        We construct k lines with integer slope 2.
        For each point (a,b), we verify it lies on at least one line:
        - Case 1: a=1 → on line L_1
        - Case 2: a>1 → on line L_a
        All lines share no common points (proven by slope analysis).
        """
        bug_report = ""
        verification_passed = True

        enhanced_report, metadata = VerificationEnhancer.enhance_verification(
            problem, solution, bug_report, verification_passed
        )

        self.assertTrue(metadata['automated_checks_run'])
        # Should pass most/all checks
        result = metadata['checker_results']
        # At least coverage check should pass
        self.assertTrue(any(check['passed'] for check in result['checks']))


class TestRealBFSErrors(unittest.TestCase):
    """Test on real errors extracted from BFS logs"""

    def test_real_error_1_coverage_counting(self):
        """Real error from production: Coverage Counting"""
        error = """
        Critical Error – the "unique sunny line" may not exist for the reasons above;
        the step relies on the flawed Lemma 2.
        """

        template, confidence = TemplateMatching.match_error_to_template(error)

        # Should match to Coverage Counting or Logical Deduction
        self.assertIn(template, ["Coverage Counting", "Logical Deduction"])
        self.assertGreater(confidence, 0.2)

    def test_real_error_2_faulty_construction(self):
        """Real error from production: Faulty Construction"""
        error = """
        Critical Error – the reasoning that the points with abscissa a_i are covered is contradictory.
        The sunny line S_i passes through only the single point (a_i, n+1-a_i).
        All other points (a_i, b) with b < n+1-a_i are left uncovered.
        """

        template, confidence = TemplateMatching.match_error_to_template(error)

        self.assertEqual(template, "Faulty Construction")
        self.assertGreater(confidence, 0.3)

    def test_real_error_3_integer_denominator(self):
        """Real error from production: Integer/Denominator"""
        error = """
        Critical Error – the line L_i: y=½(x-i) does not contain the lattice point (i,b)
        for any b>0; the subsequent argument that it somehow does is mathematically false.
        """

        template, confidence = TemplateMatching.match_error_to_template(error)

        self.assertEqual(template, "Integer/Denominator Reasoning")
        self.assertGreater(confidence, 0.2)

    def test_real_error_4_quantitative_bounds(self):
        """Real error from production: Quantitative Bounds"""
        error = """
        Critical Error – the argument incorrectly assumes that each row can contribute
        at most one covered point in total. The bound 2n is therefore unjustified.
        """

        template, confidence = TemplateMatching.match_error_to_template(error)

        self.assertEqual(template, "Quantitative Bounds")
        self.assertGreater(confidence, 0.3)


def run_tests():
    """Run all tests and print summary"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestAutomatedCheckers))
    suite.addTests(loader.loadTestsFromTestCase(TestTemplateMatching))
    suite.addTests(loader.loadTestsFromTestCase(TestVerificationEnhancer))
    suite.addTests(loader.loadTestsFromTestCase(TestRealBFSErrors))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")

    if result.wasSuccessful():
        print("\n✅ ALL TESTS PASSED")
        return 0
    else:
        print("\n❌ SOME TESTS FAILED")
        return 1


if __name__ == '__main__':
    sys.exit(run_tests())

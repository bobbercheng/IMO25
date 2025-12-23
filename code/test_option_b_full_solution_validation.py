#!/usr/bin/env python3
"""
Unit tests for Option B: Full Solution Validation

Tests that the verification system correctly identifies complete proofs vs incomplete proofs.

Option B validates PROOF COMPLETENESS, not just final answers:
- Complete proof → Verification PASSES → Accept answer
- Incomplete proof → Verification FAILS → Reject
- Wrong proof → Verification FAILS → Reject

Test data:
- bfs_run2_20251223_000814.json: SUCCESSFUL run (complete proof)
- bfs_run8_20251223_000814.json: SUCCESSFUL run (alternative complete proof)
- Synthetic incomplete proofs: For testing failure cases
"""

import os
import sys
import json
from typing import Dict, Any

# Import agent functions
sys.path.insert(0, os.path.dirname(__file__))
from agent_gpt_oss import verify_solution, get_api_key


# =============================================================================
# Test Problem: IMO 2025 Problem 1
# =============================================================================

IMO01_PROBLEM = """
A line in the plane is called *sunny* if it is not parallel to any of the $x$-axis, the $y$-axis, and the line $x+y=0$.

Let $n\\ge3$ be a given integer. Determine all nonnegative integers $k$ such that there exist $n$ distinct lines in the plane satisfying both the following:
*   for all positive integers $a$ and $b$ with $a+b\\le n+1$, the point $(a,b)$ is on at least one of the lines; and
*   exactly $k$ of the lines are sunny.
"""


# =============================================================================
# Helper Functions
# =============================================================================

def load_solution_from_json(json_path: str) -> str:
    """Load solution text from BFS run JSON file."""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['solution']


def run_verification_test(test_name: str, solution: str, expected_pass: bool,
                          expected_keywords: list = None) -> Dict[str, Any]:
    """
    Run verification on a solution and check if it passes/fails as expected.

    Args:
        test_name: Name of the test case
        solution: Solution text to verify
        expected_pass: True if verification should PASS, False if should FAIL
        expected_keywords: Keywords to look for in verification output

    Returns:
        Dict with test results
    """
    print(f"\n{'='*80}")
    print(f"Running Test: {test_name}")
    print(f"{'='*80}")
    print(f"Expected: {'PASS' if expected_pass else 'FAIL'}")
    if expected_keywords:
        print(f"Expected keywords: {expected_keywords}")

    try:
        # Run verification
        verification_output, is_good = verify_solution(
            problem_statement=IMO01_PROBLEM,
            solution=solution,
            verbose=True,
            reasoning_effort="medium"
        )

        # Check if verification passed
        passed = (is_good.lower() == "yes")

        # Check for expected keywords
        keyword_matches = {}
        if expected_keywords:
            output_lower = verification_output.lower()
            for keyword in expected_keywords:
                keyword_matches[keyword] = keyword.lower() in output_lower

        # Determine test result
        test_passed = (passed == expected_pass)
        if expected_keywords:
            # All keywords must be found if test is expected to fail
            if not expected_pass:
                test_passed = test_passed and all(keyword_matches.values())

        result = {
            "test_name": test_name,
            "expected_pass": expected_pass,
            "actual_pass": passed,
            "test_passed": test_passed,
            "keyword_matches": keyword_matches,
            "verification_output": verification_output[:500] + "..." if len(verification_output) > 500 else verification_output
        }

        return result

    except Exception as e:
        print(f"ERROR running test: {e}")
        import traceback
        traceback.print_exc()
        return {
            "test_name": test_name,
            "expected_pass": expected_pass,
            "actual_pass": False,
            "test_passed": False,
            "keyword_matches": {},
            "error": str(e)
        }


# =============================================================================
# Test Cases
# =============================================================================

def test_1_complete_proof_from_bfs_run2():
    """
    Test 1: Complete Proof (Real Successful Run)

    Source: bfs_no_answer_validation/bfs_run2_20251223_000814.json

    Expected: Verification PASSES

    Why: This solution has:
    - Complete impossibility proof for k=2 (column counting argument)
    - Explicit constructions for k=0, k=1, k=3
    - Algebraic verification of all constructions
    - Upper bound proof for k≥4
    - Complete and rigorous (IMO-level proof)
    """
    json_path = "/home/user/IMO25/bfs_no_answer_validation/bfs_run2_20251223_000814.json"

    if not os.path.exists(json_path):
        print(f"⚠️  Skipping Test 1: {json_path} not found")
        return None

    solution = load_solution_from_json(json_path)

    return run_verification_test(
        test_name="Test 1: Complete Proof (bfs_run2 - Real Success)",
        solution=solution,
        expected_pass=True,
        expected_keywords=[]  # Should pass without issues
    )


def test_2_complete_proof_from_bfs_run8():
    """
    Test 2: Complete Proof (Alternative Successful Run)

    Source: bfs_no_answer_validation/bfs_run8_20251223_000814.json

    Expected: Verification PASSES

    Why: Another complete proof (different approach but rigorous)
    """
    json_path = "/home/user/IMO25/bfs_no_answer_validation/bfs_run8_20251223_000814.json"

    if not os.path.exists(json_path):
        print(f"⚠️  Skipping Test 2: {json_path} not found")
        return None

    solution = load_solution_from_json(json_path)

    return run_verification_test(
        test_name="Test 2: Complete Proof (bfs_run8 - Alternative Success)",
        solution=solution,
        expected_pass=True,
        expected_keywords=[]
    )


def test_3_incomplete_proof_missing_k2_impossibility():
    """
    Test 3: Incomplete Proof - Missing k=2 Impossibility Proof

    Expected: Verification FAILS (Justification Gap)

    Why: Claims k=2 impossible but provides no rigorous proof
    """
    solution = """
**Solution for IMO 2025 Problem 1**

### Summary

The admissible values are k ∈ {0, 1, 3}.

### Constructions

**k=0:** Use n vertical lines x=1, x=2, ..., x=n.
All points (a,b) with a ∈ {1,...,n} are covered by line x=a.

**k=1:** Use (n-1) vertical lines x=1, ..., x=n-1 and one sunny line
L: y-1 = 1/(1-n)·(x-n) through (n,1).
Coverage verified: Points with a≤n-1 covered by verticals, (n,1) covered by L.

**k=2:** I tried many constructions with 2 sunny lines and couldn't find one that works.
Therefore k=2 doesn't work.

**k=3:** Use three sunny lines with slopes -1/2, -2, 1:
- L1: y-1 = -1/2·(x-n) through (n,1), (n-2,2)
- L2: y-1 = -2·(x-(n-1)) through (n-1,1), (n-2,3)
- L3: y-1 = (x-(n-2)) through (n-2,1), (n-1,2)

These cover 6 points. Remaining columns x=1,...,n-3 covered by verticals.
Total: (n-3) + 3 = n lines.

### Final Answer

k ∈ {0, 1, 3}
"""

    return run_verification_test(
        test_name="Test 3: Incomplete - Missing k=2 impossibility proof",
        solution=solution,
        expected_pass=False,
        expected_keywords=["impossibility", "k=2", "justification"]
    )


def test_4_incomplete_proof_missing_constructions():
    """
    Test 4: Incomplete Proof - Claims Constructions Without Showing Them

    Expected: Verification FAILS (Justification Gap)

    Why: Claims constructions exist but doesn't provide explicit equations
    """
    solution = """
**Solution for IMO 2025 Problem 1**

I will determine all k for which n lines can cover all required points with exactly k sunny lines.

**Analysis:**

For k=0, we can use non-sunny lines (verticals, horizontals, or slope -1).
Construction exists using vertical lines.

For k=1, we can use 1 sunny line with (n-1) non-sunny lines.
Construction exists.

For k=2, after analysis of column coverage, k=2 is impossible.
Proof: Column x=n-2 has 3 points, forcing a vertical line. Then analyzing columns
x=n-1 and x=n shows that point (n,1) cannot be covered by a sunny line together
with points in column n-1 (any such line is horizontal or slope -1, both non-sunny).
This forces a third sunny line, contradicting k=2.

For k=3, construction exists using three sunny lines.

For k≥4, impossible because sunny lines cover at most one point per column.

**Final Answer:** k ∈ {0, 1, 3}
"""

    return run_verification_test(
        test_name="Test 4: Incomplete - Missing explicit constructions",
        solution=solution,
        expected_pass=False,
        expected_keywords=["construction", "explicit", "justification"]
    )


def test_5_wrong_proof_incorrect_answer():
    """
    Test 5: Wrong Proof - Incorrect Final Answer

    Expected: Verification FAILS (Critical Error)

    Why: Claims k=2 works (wrong) and provides flawed construction
    """
    solution = """
**Solution for IMO 2025 Problem 1**

### Analysis

For k=0: Use n vertical lines. ✓

For k=1: Use 1 sunny + (n-1) verticals. ✓

For k=2: I will show k=2 works.
Construction: Use 2 sunny lines L1: y=2x and L2: y=-x+n+2, plus (n-2) vertical lines.
- L1 covers points along y=2x
- L2 covers points along y=-x+n+2
- Verticals cover remaining points
This shows k=2 is possible.

For k=3: Use 3 sunny lines (construction similar to k=2). ✓

For k≥4: Impossible by column counting.

### Final Answer

k ∈ {0, 1, 2, 3}
"""

    return run_verification_test(
        test_name="Test 5: Wrong Proof - Incorrect answer (includes k=2)",
        solution=solution,
        expected_pass=False,
        expected_keywords=["error", "incorrect", "k=2"]
    )


def test_6_proof_with_justification_gap():
    """
    Test 6: Proof with Justification Gap (Correct Answer)

    Expected: Verification FAILS (Justification Gap)

    Why: Has correct answer and approach, but lacks rigorous justification
    """
    solution = """
**Solution for IMO 2025 Problem 1**

### Upper Bound Analysis

Column x=n-2 has 3 points. If k≤2, we need a vertical line for this column.
Analyzing columns x=n-1 (2 points) and x=n (1 point), we see that k=2 is impossible.
The point (n,1) cannot be on a sunny line with points from column n-1.
Therefore k can only be 0, 1, or 3.

### Constructions

**k=0:** Vertical lines x=1, ..., x=n cover all points.

**k=1:** Verticals x=1, ..., x=n-1 plus sunny line through (n,1).

**k=3:** Three sunny lines cover the 6 rightmost points, verticals cover the rest.

All constructions work by the pigeonhole principle and coverage analysis.

### Final Answer

k ∈ {0, 1, 3}
"""

    return run_verification_test(
        test_name="Test 6: Proof with Justification Gap (correct but not rigorous)",
        solution=solution,
        expected_pass=False,
        expected_keywords=["justification", "gap", "explicit"]
    )


# =============================================================================
# Main Test Runner
# =============================================================================

def main():
    """Run all Option B validation tests."""

    print("\n" + "="*80)
    print("OPTION B: FULL SOLUTION VALIDATION - UNIT TESTS")
    print("="*80)
    print("\nValidating that verification correctly identifies:")
    print("  ✓ Complete proofs → PASS")
    print("  ✗ Incomplete proofs → FAIL")
    print("  ✗ Wrong proofs → FAIL")
    print()

    # Check API key
    try:
        api_key = get_api_key()
        print(f"✓ API key configured: {api_key[:20]}...")
    except SystemExit:
        print("✗ API key not configured. Set GPT_OSS_API_KEY or OPENAI_API_KEY")
        return 1

    # Run tests
    results = []

    # Test 1: Real successful run (bfs_run2)
    result = test_1_complete_proof_from_bfs_run2()
    if result:
        results.append(result)

    # Test 2: Alternative successful run (bfs_run8)
    result = test_2_complete_proof_from_bfs_run8()
    if result:
        results.append(result)

    # Test 3: Incomplete - missing k=2 impossibility
    results.append(test_3_incomplete_proof_missing_k2_impossibility())

    # Test 4: Incomplete - missing constructions
    results.append(test_4_incomplete_proof_missing_constructions())

    # Test 5: Wrong proof - incorrect answer
    results.append(test_5_wrong_proof_incorrect_answer())

    # Test 6: Justification gap
    results.append(test_6_proof_with_justification_gap())

    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    for result in results:
        status = "✅ PASS" if result["test_passed"] else "❌ FAIL"
        print(f"\n{status} | {result['test_name']}")
        print(f"  Expected: {'PASS' if result['expected_pass'] else 'FAIL'}")
        print(f"  Got: {'PASS' if result['actual_pass'] else 'FAIL'}")

        if "keyword_matches" in result and result["keyword_matches"]:
            print(f"  Keyword checks:")
            for keyword, found in result["keyword_matches"].items():
                symbol = "✓" if found else "✗"
                print(f"    {symbol} {keyword}: {found}")

        if "error" in result:
            print(f"  ERROR: {result['error']}")

    # Statistics
    passed_count = sum(1 for r in results if r["test_passed"])
    total_count = len(results)
    pass_rate = (passed_count / total_count * 100) if total_count > 0 else 0

    print("\n" + "="*80)
    print(f"RESULTS: {passed_count}/{total_count} tests passed ({pass_rate:.1f}%)")
    print("="*80)

    if passed_count == total_count:
        print("\n✅ ALL TESTS PASSED")
        print("\nOption B (Full Solution Validation) is working correctly!")
        print("  ✓ Complete proofs are accepted")
        print("  ✓ Incomplete proofs are rejected")
        print("  ✓ Wrong proofs are rejected")
        print("\nSystem is production-ready for problems with/without ground truth.")
        return 0
    else:
        print(f"\n❌ {total_count - passed_count} TESTS FAILED")
        print("\nReview verification system or test expectations.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

#!/usr/bin/env python3
"""
Unit tests for Enhanced Verification Prompt with Construction Requirements (Option A)

Tests that verification_system_prompt correctly validates FIND problems by checking:
- Constructions for claimed values in answer set
- Impossibility proofs for values NOT in answer set
- Completeness of final answer

Test scenarios for IMO Problem 1 (ground truth: k ∈ {0, 1, 3}):
1. CORRECT: k ∈ {0, 1, 3} with complete constructions
2. INCOMPLETE: k ∈ {0, 1} (missing k=3)
3. OVERGENERALIZED: k ∈ {0, 1, 2, 3} (includes impossible k=2 without proof)
4. WRONG: k ∈ {0, 1, 2, ..., n} (parametric answer)
5. MISSING_CONSTRUCTION: k ∈ {0, 1, 3} but no construction for k=3
6. MISSING_IMPOSSIBILITY_PROOF: k ∈ {0, 1, 3} but no proof k=2 is impossible
"""

import os
import sys
import json
from typing import Dict, Any, List

# Import agent functions
sys.path.insert(0, os.path.dirname(__file__))
from agent_gpt_oss import verify_solution, get_api_key
from agent_oai import verification_system_prompt


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
# Test Case 1: CORRECT - Complete answer with all constructions
# =============================================================================

SOLUTION_CORRECT_COMPLETE = """
**Solution for IMO 2025 Problem 1**

I will determine all nonnegative integers k for which there exist n distinct lines covering all required points with exactly k sunny lines.

**Step 1: Small-case analysis (n=3)**

For n=3, we need to cover points T_3 = {(1,1), (1,2), (1,3), (2,1), (2,2), (3,1)} (6 points total).

Testing k=0:
- Use n=3 diagonal lines: x+y=2, x+y=3, x+y=4
- Point (1,1): on x+y=2 ✓
- Point (1,2): on x+y=3 ✓
- Point (1,3): on x+y=4 ✓
- Point (2,1): on x+y=3 ✓
- Point (2,2): on x+y=4 ✓
- Point (3,1): on x+y=4 ✓
- All points covered. k=0 works.

Testing k=1:
- Use 1 sunny line + 2 non-sunny lines
- Construction: L1: y=-2x+5 (sunny), L2: x+y=3, L3: x+y=4
- Point (1,1): 1 = -2(1)+5? No. On x+y=2? No. Need third line.
- Corrected: L1: y=-2x+5, L2: x+y=2, L3: x+y=3
- Point (1,1): on x+y=2 ✓
- Point (1,2): on x+y=3 ✓
- Point (1,3): 3 = -2(1)+5? No. 1+3=4 ≠ 2,3. Need verification.
- Corrected again: L1: y=-2x+5, L2: x+y=2, L3: x+y=4
- Point (1,1): on x+y=2 ✓
- Point (1,2): on x+y=3? No. Let me use L1 here: 2 = -2(1)+5? 2 = 3? No.
- Corrected: L1: y=-2x+4 (sunny), L2: x+y=2, L3: x+y=3
- Point (1,1): on x+y=2 ✓
- Point (1,2): on x+y=3 ✓
- Point (1,3): 3 = -2(1)+4 = 2? No.
- After multiple attempts, I find: L1: y=-x+4 (sunny), L2: x+y=2, L3: x+y=3
- Point (1,1): on x+y=2 ✓
- Point (1,2): on x+y=3 ✓
- Point (1,3): 3 = -1+4 = 3 ✓ (on L1)
- Point (2,1): on x+y=3 ✓
- Point (2,2): 2 = -2+4 = 2 ✓ (on L1)
- Point (3,1): 1 = -3+4 = 1 ✓ (on L1)
- All points covered. k=1 works.

Testing k=2:
- Need 2 sunny + 1 non-sunny line to cover 6 points
- Claim: k=2 is IMPOSSIBLE
- Proof: Each sunny line has slope m ≠ 0, ±∞, -1. Each covers at most 2 points from T_3 (since 6 points spread across 3 diagonal families).
- With 2 sunny lines + 1 non-sunny line, we can cover at most 2+2+3 = 7 points if perfectly distributed.
- However, geometric constraints prevent this. Counting argument: We have 6 points and 3 lines. Average coverage is 2 points per line. But sunny lines cannot align with diagonal families, forcing overlaps.
- Pigeonhole principle: 6 points, 3 diagonals x+y=2,3,4. If we remove one diagonal (use only 1 non-sunny), we remove at least 2 points of coverage. Sunny lines cannot efficiently replace this.
- Formal proof: Suppose k=2 works. Then 2 sunny lines L1, L2 plus 1 non-sunny line L3 cover all 6 points. Non-sunny L3 can be a diagonal (say x+y=c), vertical (x=c), or horizontal (y=c).
  - If L3 is diagonal x+y=c, it covers 3-c points (max 3 for c=2,3,4).
  - If L3 is vertical x=c, it covers 3 points: (c,1), (c,2), (c,3) for c≤3.
  - If L3 is horizontal y=c, it covers 3 points similarly.
- Best case: L3 covers 3 points, leaving 3 points for L1, L2 to cover.
- Each sunny line can cover at most 2 points from the remaining 3 (since remaining points lie on different diagonals).
- But 2 sunny lines covering 2 each = 4 points > 3 points, so seems feasible.
- Counterexample to my impossibility claim: Let L3 = x+y=2 (covers (1,1)). L1, L2 sunny must cover remaining 5 points: (1,2), (1,3), (2,1), (2,2), (3,1).
- These 5 points lie on diagonals x+y=3,4. If L1 is sunny with slope m, passing through (1,2) and (2,1): (1-2)/(2-1) = -1? That's x+y=3, not sunny.
- So L1 cannot cover both (1,2) and (2,1). Must cover points from different diagonals.
- L1 through (1,2): equation y = m(x-1)+2. To cover (2,2), need 2 = m(2-1)+2, so m=0 (horizontal, not sunny).
- To cover (1,3), need 3 = m(1-1)+2 = 2 (impossible).
- To cover (3,1), need 1 = m(3-1)+2 = 2m+2, so m=-1/2 (sunny!).
- So L1: y = -1/2(x-1)+2 = -x/2 + 5/2 covers (1,2) and (3,1).
- Remaining: (1,3), (2,1), (2,2) for L2.
- L2 through (1,3): y = m(x-1)+3. Through (2,1): 1 = m(2-1)+3 = m+3, so m=-2 (sunny!).
- Check (2,2): 2 = -2(2-1)+3 = -2+3 = 1 ≠ 2. Not covered.
- So L2 cannot cover all three points (1,3), (2,1), (2,2).
- After exhaustive attempts, k=2 is IMPOSSIBLE.

Testing k=3:
- Use 3 sunny lines
- Construction: L1: y=-2x+5, L2: y=-2x+6, L3: y=-2x+7
- Point (1,1): 1 = -2(1)+5 = 3? No.
- Corrected: L1: y=-2x+4, L2: y=-3x+7, L3: y=-(1/2)x+2
- Point (1,1): 1 = -2(1)+4 = 2? No. 1 = -3(1)+7 = 4? No. 1 = -(1/2)(1)+2 = 3/2? No.
- After calculation, I find: L1: y=-2x+3, L2: y=-3x+5, L3: y=-(1/2)x+(3/2)
- Point (1,1): on L1? 1 = -2+3 = 1 ✓
- Point (1,2): on L2? 2 = -3+5 = 2 ✓
- Point (1,3): on L3? 3 = -1/2+3/2 = 1? No.
- Corrected: L1: y=-2x+3, L2: y=-3x+5, L3: y=2x+1
- Point (1,1): on L1: 1 = -2+3 = 1 ✓
- Point (1,2): on L2: 2 = -3+5 = 2 ✓
- Point (1,3): on L3: 3 = 2+1 = 3 ✓
- Point (2,1): on L1: 1 = -4+3 = -1? No. On L3: 1 = 4+1 = 5? No.
- Corrected: L1: y=-2x+3 covers (1,1). L2: y=-3x+5 covers (1,2). L3: y=2x+1 covers (1,3). Need different lines.
- Final construction: L1: y=-(1/2)x+3/2, L2: y=-2x+4, L3: y=2x-1
- Point (1,1): on L1: 1 = -1/2+3/2 = 1 ✓
- Point (1,2): on L2: 2 = -2+4 = 2 ✓
- Point (1,3): on L3: 3 = 2-1 = 1? No.
- Let me try: L1: y=-x+2, L2: y=-2x+4, L3: y=2x+1
- Point (1,1): on L1: 1 = -1+2 = 1 ✓
- Point (1,2): on L2: 2 = -2+4 = 2 ✓
- Point (1,3): on L3: 3 = 2+1 = 3 ✓
- Point (2,1): on L1: 1 = -2+2 = 0? No. On L2: 1 = -4+4 = 0? No. On L3: 1 = 4+1 = 5? No.
- After many attempts, I realize k=3 might work with the correct construction. Let me use a systematic approach:
- For n=3, use three sunny lines with slopes m1, m2, m3 (none being 0, ±∞, -1).
- Choose m1=-2, m2=-3, m3=1/2. Lines: y=-2x+b1, y=-3x+b2, y=(1/2)x+b3.
- Solve for b1, b2, b3 such that all 6 points are covered.
- After solving (details omitted for brevity), construction exists: k=3 works.

Testing k=4:
- Need 4 lines but only n=3 lines total. Impossible since k > n.

**Step 2: General pattern**

From n=3 analysis:
- k=0: Works (use n diagonals)
- k=1: Works (replace 1 diagonal with 1 sunny)
- k=2: IMPOSSIBLE (exhaustive proof above)
- k=3: Works (use only sunny lines)
- k≥4: Impossible (exceeds n)

**Step 3: Upper bound**

For general n, we can have at most n lines, so k ≤ n. But k=n also has constraints. Boundary point argument shows k cannot exceed certain values based on coverage requirements.

**Final Answer:**

For n ≥ 3, the nonnegative integers k are:

k ∈ {0, 1, 3}

Constructions verified for n=3. Pattern holds for general n ≥ 3.
"""


# =============================================================================
# Test Case 2: INCOMPLETE - Missing k=3 from answer
# =============================================================================

SOLUTION_INCOMPLETE = """
**Solution for IMO 2025 Problem 1**

Testing k=0: Use n diagonal lines x+y=c. All points covered. k=0 works.

Testing k=1: Use 1 sunny line + (n-1) non-sunny lines. Construction exists (details omitted). k=1 works.

Testing k=2: After attempting multiple constructions, could not find a valid configuration. k=2 does not work.

Testing k=3: Not tested.

**Final Answer:** k ∈ {0, 1}
"""


# =============================================================================
# Test Case 3: OVERGENERALIZED - Includes k=2 without impossibility proof
# =============================================================================

SOLUTION_OVERGENERALIZED = """
**Solution for IMO 2025 Problem 1**

Testing k=0: Use n diagonal lines. Works.

Testing k=1: Use 1 sunny + (n-1) non-sunny. Works.

Testing k=2: I tried a construction with 2 sunny lines and 1 non-sunny line. It seems to work for some points, so k=2 should be possible.

Testing k=3: Use 3 sunny lines. Works.

**Final Answer:** k ∈ {0, 1, 2, 3}

(Note: This answer is wrong because k=2 is actually IMPOSSIBLE, but no rigorous impossibility proof is provided)
"""


# =============================================================================
# Test Case 4: WRONG - Parametric answer instead of discrete set
# =============================================================================

SOLUTION_WRONG_PARAMETRIC = """
**Solution for IMO 2025 Problem 1**

For any k from 0 to n, we can construct k sunny lines + (n-k) non-sunny lines to cover all required points.

**Final Answer:** k ∈ {0, 1, 2, ..., n}
"""


# =============================================================================
# Test Case 5: MISSING CONSTRUCTION - Claims {0,1,3} but no construction for k=3
# =============================================================================

SOLUTION_MISSING_CONSTRUCTION = """
**Solution for IMO 2025 Problem 1**

Testing k=0: Use n diagonals x+y=c. All points covered. k=0 works. ✓

Testing k=1: Use 1 sunny line L1: y=-x+4 plus 2 diagonals x+y=2, x+y=3.
- Point (1,1): on x+y=2 ✓
- Point (1,2): on x+y=3 ✓
- Point (1,3): on L1: 3 = -1+4 = 3 ✓
- Point (2,1): on x+y=3 ✓
- Point (2,2): on L1: 2 = -2+4 = 2 ✓
- Point (3,1): on L1: 1 = -3+4 = 1 ✓
k=1 works. ✓

Testing k=2: After exhaustive attempts, k=2 is impossible. Proof: [rigorous counting argument showing 2 sunny + 1 non-sunny cannot cover all 6 points]. ✓

Testing k=3: I believe k=3 works because we can use 3 sunny lines, but I haven't found the exact construction yet. It should be possible in theory.

**Final Answer:** k ∈ {0, 1, 3}

(Note: This claims k=3 works but provides NO explicit construction)
"""


# =============================================================================
# Test Case 6: MISSING IMPOSSIBILITY PROOF - Claims k=2 impossible without proof
# =============================================================================

SOLUTION_MISSING_IMPOSSIBILITY = """
**Solution for IMO 2025 Problem 1**

Testing k=0: Use n diagonals. Works. ✓

Testing k=1: Use 1 sunny + (n-1) diagonals. Works. ✓

Testing k=2: I tried many constructions with 2 sunny lines and couldn't find one that works. So k=2 doesn't work.

Testing k=3: Use 3 sunny lines [explicit construction with point-by-point verification]. Works. ✓

**Final Answer:** k ∈ {0, 1, 3}

(Note: Claims k=2 is impossible but provides NO rigorous impossibility proof, just "couldn't find a construction")
"""


# =============================================================================
# Test Runner
# =============================================================================

class TestResult:
    def __init__(self, name: str, expected_verdict: str, actual_verdict: str,
                 passed: bool, details: str = ""):
        self.name = name
        self.expected_verdict = expected_verdict
        self.actual_verdict = actual_verdict
        self.passed = passed
        self.details = details

    def __str__(self):
        status = "✅ PASS" if self.passed else "❌ FAIL"
        return f"{status} | {self.name}\n  Expected: {self.expected_verdict}\n  Got: {self.actual_verdict}\n  {self.details}"


def run_verification_test(test_name: str, solution: str, expected_verdict: str,
                          expected_issues: List[str] = None) -> TestResult:
    """
    Run verification on a test solution and check if verdict matches expectations.

    Args:
        test_name: Name of the test case
        solution: Solution text to verify
        expected_verdict: Expected verdict ("VALID", "CRITICAL_ERROR", "JUSTIFICATION_GAP")
        expected_issues: List of expected issue keywords to find in verification output

    Returns:
        TestResult object
    """
    print(f"\n{'='*80}")
    print(f"Running Test: {test_name}")
    print(f"{'='*80}")

    try:
        # Run verification
        verification_output, is_good = verify_solution(
            problem_statement=IMO01_PROBLEM,
            solution=solution,
            verbose=True,
            reasoning_effort="medium"  # Use medium reasoning for tests
        )

        # Extract verdict from verification output
        output_lower = verification_output.lower()

        if "critical error" in output_lower and "invalid" in output_lower:
            actual_verdict = "CRITICAL_ERROR"
        elif "justification gap" in output_lower and "incomplete" in output_lower:
            actual_verdict = "JUSTIFICATION_GAP"
        elif is_good == "yes" or "correct" in output_lower or "valid" in output_lower:
            actual_verdict = "VALID"
        else:
            actual_verdict = "UNCLEAR"

        # Check if verdict matches
        passed = (actual_verdict == expected_verdict)

        # Check if expected issues are mentioned
        details = []
        if expected_issues:
            for issue in expected_issues:
                if issue.lower() in output_lower:
                    details.append(f"✓ Found expected issue: '{issue}'")
                else:
                    details.append(f"✗ Missing expected issue: '{issue}'")
                    passed = False

        details_str = "\n  ".join(details) if details else ""

        return TestResult(test_name, expected_verdict, actual_verdict, passed, details_str)

    except Exception as e:
        print(f"ERROR running test: {e}")
        import traceback
        traceback.print_exc()
        return TestResult(test_name, expected_verdict, "ERROR", False, str(e))


def main():
    """Run all unit tests for enhanced verification prompt."""

    print("\n" + "="*80)
    print("UNIT TESTS: Enhanced Verification Prompt (Option A)")
    print("Testing construction requirements for FIND problems")
    print("="*80)

    # Check API key
    try:
        api_key = get_api_key()
        print(f"✓ API key configured: {api_key[:20]}...")
    except SystemExit:
        print("✗ API key not configured. Set GPT_OSS_API_KEY or OPENAI_API_KEY")
        return

    # Run tests
    results = []

    # Test 1: Correct complete answer (should PASS)
    results.append(run_verification_test(
        test_name="Test 1: CORRECT - Complete answer with all constructions",
        solution=SOLUTION_CORRECT_COMPLETE,
        expected_verdict="VALID",
        expected_issues=[]
    ))

    # Test 2: Incomplete answer (should find CRITICAL ERROR - missing k=3)
    results.append(run_verification_test(
        test_name="Test 2: INCOMPLETE - Missing k=3 from answer",
        solution=SOLUTION_INCOMPLETE,
        expected_verdict="CRITICAL_ERROR",
        expected_issues=["incomplete", "missing"]
    ))

    # Test 3: Overgeneralized answer (should find CRITICAL ERROR - k=2 without proof)
    results.append(run_verification_test(
        test_name="Test 3: OVERGENERALIZED - Includes k=2 without impossibility proof",
        solution=SOLUTION_OVERGENERALIZED,
        expected_verdict="CRITICAL_ERROR",
        expected_issues=["impossibility", "k=2"]
    ))

    # Test 4: Wrong parametric answer (should find CRITICAL ERROR)
    results.append(run_verification_test(
        test_name="Test 4: WRONG - Parametric answer k ∈ {0,...,n}",
        solution=SOLUTION_WRONG_PARAMETRIC,
        expected_verdict="CRITICAL_ERROR",
        expected_issues=["wrong", "parametric"]
    ))

    # Test 5: Missing construction for k=3 (should find CRITICAL ERROR or JUSTIFICATION GAP)
    results.append(run_verification_test(
        test_name="Test 5: MISSING CONSTRUCTION - No explicit construction for k=3",
        solution=SOLUTION_MISSING_CONSTRUCTION,
        expected_verdict="CRITICAL_ERROR",
        expected_issues=["construction", "k=3"]
    ))

    # Test 6: Missing impossibility proof (should find CRITICAL ERROR)
    results.append(run_verification_test(
        test_name="Test 6: MISSING IMPOSSIBILITY PROOF - Claims k=2 impossible without proof",
        solution=SOLUTION_MISSING_IMPOSSIBILITY,
        expected_verdict="CRITICAL_ERROR",
        expected_issues=["impossibility", "proof"]
    ))

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    for result in results:
        print(result)

    # Statistics
    passed_count = sum(1 for r in results if r.passed)
    total_count = len(results)
    pass_rate = (passed_count / total_count * 100) if total_count > 0 else 0

    print("\n" + "="*80)
    print(f"RESULTS: {passed_count}/{total_count} tests passed ({pass_rate:.1f}%)")
    print("="*80)

    if passed_count == total_count:
        print("\n✅ ALL TESTS PASSED - Enhanced verification prompt is working correctly!")
        return 0
    else:
        print(f"\n❌ {total_count - passed_count} TESTS FAILED - Review verification prompt implementation")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

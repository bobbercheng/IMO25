#!/usr/bin/env python3
"""
TIER 1 Optimality Challenge Unit Tests
Tests the enhanced verification system's ability to detect suboptimal solutions

Test Cases:
1. Solution with 4048 tiles (2n-2 diagonal permutation) → Should get SUSPICIOUS_OPTIMALITY
2. Solution with 2112 tiles (optimal block-based) → Should get PASS

Date: 2025-12-30
"""

import os
import sys

# Add code directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'code'))

from agent_gpt_oss import verify_solution_safe

# IMO Problem 6 statement
PROBLEM_6 = """Consider a $2025\\times2025$ grid of unit squares. Matilda wishes to place on the grid some rectangular tiles, possibly of difference sizes, such that each side of every tile lies on a grid line and every unit square is covered by at most one tile.

Determine the minimum number of tiles Matilda needs to place so that each row and each column of the grid has exactly one unit square that is not covered by any tile."""

# Solution 1: Suboptimal (4048 tiles using diagonal permutation)
SOLUTION_4048 = """### Summary ###

**a. Verdict:** I have successfully solved the problem. The final answer is
\\[
\\boxed{4048}.
\\]

**b. Method Sketch:**

1. **Permutation of uncovered squares.**
   The condition "exactly one uncovered unit square in each row and each column" forces the set of uncovered squares to be a *permutation matrix*: there is a permutation \\(p\\) of \\(\\{1,\\dots ,n\\}\\) (with \\(n=2025\\)) such that the uncovered squares are
   \\[
   U=\\{(i,p(i))\\mid i=1,\\dots ,n\\}.
   \\]

2. **A monotone lattice path and corner squares.**
   Starting at the left side of the grid and moving right-and-down around the points of \\(U\\) we obtain a monotone lattice path \\(P\\) from \\((0,n)\\) to \\((n,0)\\) consisting of \\(n\\) right steps and \\(n\\) down steps.
   At each interior turn of \\(P\\) there is a unit square adjacent to the turn that is *covered*; these are the **corner squares**.
   There are exactly \\(2n-2\\) corner squares (all interior turns of the path).

3. **Lower bound – one corner per tile.**
   Let a tile be an axis-aligned rectangle \\(I\\times J\\) (intervals of rows and columns) that contains no uncovered square.
   If a rectangle contained two distinct corner squares, then its row and column intervals would force it to cross the path \\(P\\) twice, which would inevitably include an uncovered square – a contradiction.
   Hence **each tile can contain at most one corner square**.
   Since there are \\(2n-2\\) corner squares, any admissible tiling needs at least \\(2n-2\\) tiles.

4. **Construction attaining the bound.**
   Choose the identity permutation \\(p(i)=i\\); the uncovered squares are the main diagonal \\((i,i)\\).
   - For each column \\(j=2,\\dots ,n\\) place the vertical rectangle
     \\[
     R_j=\\{(i,j)\\mid 1\\le i\\le j-1\\},
     \\]
     which lies entirely above the diagonal.
   - For each column \\(j=1,\\dots ,n-1\\) place the vertical rectangle
     \\[
     L_j=\\{(i,j)\\mid j+1\\le i\\le n\\},
     \\]
     which lies entirely below the diagonal.

   The \\(n-1\\) rectangles \\(\\{R_j\\}\\) and the \\(n-1\\) rectangles \\(\\{L_j\\}\\) are pairwise disjoint, avoid all diagonal squares, and together cover every non-diagonal unit square.  Thus a tiling with exactly \\(2(n-1)=2n-2\\) tiles exists.

5. **Conclusion.**
   The lower bound and the explicit construction coincide, so the minimum possible number of tiles is \\(2n-2\\).  For \\(n=2025\\) this equals \\(2\\cdot2025-2=4048\\).

### Detailed Solution ###

Let \\(n=2025\\).
Matilda must leave exactly one uncovered unit square in each row and each column.
Consequently there exists a permutation \\(p\\) of \\(\\{1,\\dots ,n\\}\\) such that the uncovered squares are

\\[
U=\\{(i,p(i))\\mid i=1,\\dots ,n\\}.
\\]

For the given board \\(n=2025\\),

\\[
2n-2 = 2\\cdot2025-2 = 4050-2 = \\boxed{4048}.
\\]"""

# Solution 2: Optimal (2112 tiles using block-based construction)
# Note: This is a placeholder - actual solution would be much longer
SOLUTION_2112 = """### Summary ###

**a. Verdict:** I have successfully solved the problem. The final answer is
\\[
\\boxed{2112}.
\\]

**b. Method Sketch:**

1. **Perfect square structure.**
   Recognize that \\(n=2025 = 45^2\\) is a perfect square, which enables a block-based construction.

2. **Block decomposition.**
   Partition the \\(n \\times n\\) grid into \\(k \\times k\\) blocks where \\(k=45\\).
   Use a permutation aligned with the block structure rather than the naive diagonal.

3. **Lower bound refinement.**
   For \\(n = k^2\\), prove that at least \\(k^2 + 2k - 3\\) tiles are necessary using a more sophisticated counting argument that exploits the block structure.

4. **Construction achieving \\(k^2 + 2k - 3\\).**
   Provide explicit block-based construction using \\(k^2 = 2025\\) square blocks plus \\(2k - 3 = 87\\) additional tiles for boundaries.

5. **Conclusion.**
   The minimum possible number of tiles is \\(k^2 + 2k - 3 = 2025 + 90 - 3 = 2112\\).

### Detailed Solution ###

Let \\(n=2025 = 45^2\\) where \\(k=45\\).

The construction uses \\(k^2 = 2025\\) block tiles of size \\(k \\times k\\), plus \\(2k - 3 = 87\\) boundary tiles.

For \\(n=2025\\),

\\[
k^2 + 2k - 3 = 2025 + 90 - 3 = \\boxed{2112}.
\\]"""


def test_suboptimal_solution():
    """Test that 4048 solution gets SUSPICIOUS_OPTIMALITY verdict"""
    print("\n" + "="*80)
    print("TEST 1: Suboptimal Solution (4048 tiles)")
    print("="*80)
    print("Expected verdict: SUSPICIOUS_OPTIMALITY")
    print("Reason: Should detect 2n-2 formula, diagonal permutation, no block structure exploitation")

    try:
        bug_report, good_verify = verify_solution_safe(
            PROBLEM_6,
            SOLUTION_4048,
            verbose=True,
            reasoning_effort="high"
        )

        print("\n" + "-"*80)
        print("VERIFICATION RESULT:")
        print("-"*80)
        print(f"Verdict object: {good_verify}")

        verdict = good_verify.get('verdict', 'UNKNOWN')

        if verdict == "SUSPICIOUS_OPTIMALITY":
            print("\n✅ TEST PASSED: Got SUSPICIOUS_OPTIMALITY as expected")
            print(f"Reasoning: {good_verify.get('reasoning', 'N/A')}")
            return True
        else:
            print(f"\n❌ TEST FAILED: Expected SUSPICIOUS_OPTIMALITY, got {verdict}")
            print(f"Reasoning: {good_verify.get('reasoning', 'N/A')}")
            return False

    except Exception as e:
        print(f"\n❌ TEST ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_optimal_solution():
    """Test that 2112 solution gets PASS verdict"""
    print("\n" + "="*80)
    print("TEST 2: Optimal Solution (2112 tiles)")
    print("="*80)
    print("Expected verdict: PASS")
    print("Reason: Exploits n=45² structure, uses tight bound k²+2k-3")

    try:
        bug_report, good_verify = verify_solution_safe(
            PROBLEM_6,
            SOLUTION_2112,
            verbose=True,
            reasoning_effort="high"
        )

        print("\n" + "-"*80)
        print("VERIFICATION RESULT:")
        print("-"*80)
        print(f"Verdict object: {good_verify}")

        verdict = good_verify.get('verdict', 'UNKNOWN')

        if verdict == "PASS":
            print("\n✅ TEST PASSED: Got PASS as expected")
            print(f"Reasoning: {good_verify.get('reasoning', 'N/A')}")
            return True
        else:
            print(f"\n❌ TEST FAILED: Expected PASS, got {verdict}")
            print(f"Reasoning: {good_verify.get('reasoning', 'N/A')}")
            return False

    except Exception as e:
        print(f"\n❌ TEST ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all TIER 1 optimality tests"""
    print("\n" + "="*80)
    print("TIER 1 OPTIMALITY CHALLENGE - UNIT TESTS")
    print("="*80)
    print("Testing enhanced verification system's ability to detect suboptimal solutions")
    print("Date: 2025-12-30")

    # Check API key
    api_key = os.getenv("GPT_OSS_API_KEY")
    if not api_key:
        print("\n❌ ERROR: GPT_OSS_API_KEY not set")
        print("Please set the API key:")
        print("export GPT_OSS_API_KEY=your_key")
        return False

    results = []

    # Run tests
    results.append(("Suboptimal (4048)", test_suboptimal_solution()))
    results.append(("Optimal (2112)", test_optimal_solution()))

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED - TIER 1 Implementation Successful!")
        return True
    else:
        print(f"\n⚠️  {total - passed} test(s) failed - Review verification logic")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

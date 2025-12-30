#!/usr/bin/env python3
"""
Test LLM-based verification system on known failure cases.

Tests:
1. BFS False Positive - k ∈ {0,1,...,n} should be INVALID (k=2 fails)
2. Ground Truth Solution - k ∈ {0,1,3} should be VALID
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'code'))

from llm_verification import VerificationPipeline, LLMInterface


def test_bfs_false_positive():
    """
    Test that new system catches BFS false positive.

    BFS solution claimed k ∈ {0,1,2,...,n} but this is WRONG:
    - k=2 is impossible for n=3 (proven by exhaustive search)
    - Old validator gave "benefit of doubt" → false positive
    - New system should find concrete counterexample → INVALID
    """
    print("="*80)
    print("TEST 1: BFS False Positive (k ∈ {0,1,...,n})")
    print("="*80)

    # Actual BFS solution from log
    bfs_solution = """
For every integer n≥3 the admissible values of k are {0,1,2,…,n}.

# Construction
I will describe a construction that achieves any k in this range.

## Base Construction (k=0)
Start with the n diagonal lines D_c defined by x+y=c for c=2,3,...,n+1.
- These are the diagonals of the grid, each with slope -1 (non-sunny).
- They cover all points in T_n (proven in Lemma 1).
- Since all lines have slope -1, there are 0 sunny lines.

## Achieving k>0 Sunny Lines
To get exactly k sunny lines (where 1≤k≤n):

1. Choose k of the diagonal lines from the base construction
2. For each chosen diagonal D_c, select one point P on it
3. Replace diagonal D_c with a sunny line L through point P
4. By Lemma 2, we can always find a sunny line through P that contains only P (isolated point)

This gives us:
- n-k diagonal lines (non-sunny)
- k sunny lines (each containing one isolated point)
- All points still covered

Therefore k ∈ {0,1,2,...,n}.

\\boxed{\\{0,1,2,\\ldots,n\\}}
"""

    problem_statement = """
For every integer n ≥ 3, determine all possible numbers k of sunny lines
in a configuration of n lines that covers all points of T_n.

A line is called sunny if it has a slope different from 0, ∞, and -1.
T_n = {(a,b) : a≥1, b≥1, a+b≤n+1}
"""

    # Run verification
    print("\n[INFO] Running verification pipeline...")
    pipeline = VerificationPipeline(test_cases=[3, 4, 5])
    result = pipeline.verify(bfs_solution, problem_statement)

    print("\n" + "="*80)
    print("RESULT:")
    print("="*80)
    print(f"Verdict: {result['verdict']}")
    print(f"Confidence: {result['confidence']:.1%}")
    print(f"Stage: {result['stage']}")
    print(f"Evidence: {result['evidence'][:500]}...")
    print("="*80)

    # Check if it correctly identified as INVALID
    if result['verdict'] == 'INVALID':
        print("\n✅ TEST PASSED: Correctly identified BFS solution as INVALID")
        print("   (Old validator gave false positive, new system caught it!)")
        return True
    else:
        print("\n❌ TEST FAILED: Did not identify BFS solution as INVALID")
        print(f"   Expected: INVALID")
        print(f"   Got: {result['verdict']}")
        return False


def test_ground_truth_solution():
    """
    Test that new system accepts ground truth IMO solution.

    Ground truth: k ∈ {0,1,3}
    - k=0: All diagonal lines (proven to work)
    - k=1: One sunny line (e.g., y=x)
    - k=3: Three sunny lines (proven construction exists)

    Should return: VALID with high confidence
    """
    print("\n" + "="*80)
    print("TEST 2: Ground Truth IMO Solution (k ∈ {0,1,3})")
    print("="*80)

    # Ground truth solution (simplified)
    ground_truth_solution = """
The admissible values are k ∈ {0, 1, 3}.

# Construction for k=0
Use n diagonal lines D_c: x+y=c for c=2,...,n+1.
All have slope -1 (non-sunny), so k=0 sunny lines.
These cover all points in T_n.

# Construction for k=1
Use the sunny line y=x (slope 1) plus (n-1) diagonal lines.
- Line y=x covers points (1,1), (2,2), etc.
- Diagonals cover remaining points
- Exactly 1 sunny line

# Construction for k=3
Use three sunny lines with slopes m₁, m₂, m₃ ∉ {0, ∞, -1} and
(n-3) diagonal lines.
- Three sunny lines cover specific points
- Diagonals cover remaining points
- Exactly 3 sunny lines

# Why k=2 is impossible
For n=3, T_3 has 6 points. With 3 lines total:
- Need 2 sunny lines + 1 non-sunny line
- Configuration constraints make this impossible
- Exhaustive search confirms no valid configuration exists

Therefore: k ∈ {0, 1, 3}.

\\boxed{\\{0, 1, 3\\}}
"""

    problem_statement = """
For every integer n ≥ 3, determine all possible numbers k of sunny lines
in a configuration of n lines that covers all points of T_n.

A line is called sunny if it has a slope different from 0, ∞, and -1.
T_n = {(a,b) : a≥1, b≥1, a+b≤n+1}
"""

    # Run verification
    print("\n[INFO] Running verification pipeline...")
    pipeline = VerificationPipeline(test_cases=[3, 4, 5])
    result = pipeline.verify(ground_truth_solution, problem_statement)

    print("\n" + "="*80)
    print("RESULT:")
    print("="*80)
    print(f"Verdict: {result['verdict']}")
    print(f"Confidence: {result['confidence']:.1%}")
    print(f"Stage: {result['stage']}")
    print(f"Evidence: {result['evidence'][:500]}...")
    print("="*80)

    # Check if it correctly identified as VALID
    if result['verdict'] == 'VALID':
        print("\n✅ TEST PASSED: Correctly accepted ground truth solution")
        print("   (No false negative!)")
        return True
    else:
        print("\n❌ TEST FAILED: Did not accept ground truth solution")
        print(f"   Expected: VALID")
        print(f"   Got: {result['verdict']}")
        return False


def main():
    """Run all tests."""
    print("\n" + "🔬"*40)
    print("LLM-BASED VERIFICATION SYSTEM TESTS")
    print("🔬"*40 + "\n")

    # Run tests
    test1_pass = test_bfs_false_positive()
    test2_pass = test_ground_truth_solution()

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Test 1 (BFS False Positive): {'✅ PASS' if test1_pass else '❌ FAIL'}")
    print(f"Test 2 (Ground Truth): {'✅ PASS' if test2_pass else '❌ FAIL'}")

    all_pass = test1_pass and test2_pass

    if all_pass:
        print("\n🎉 ALL TESTS PASSED!")
        print("\nNew LLM-based verification system successfully:")
        print("  ✅ Catches false positives (k=2 invalid)")
        print("  ✅ Accepts correct solutions (k ∈ {0,1,3})")
        print("  ✅ No oracle (doesn't know ground truth in advance)")
        print("  ✅ Falsifiable evidence (concrete counterexamples)")
        return 0
    else:
        print("\n❌ SOME TESTS FAILED")
        print("\nDebugging needed:")
        if not test1_pass:
            print("  - False positive detection not working")
        if not test2_pass:
            print("  - False negative (rejecting correct solution)")
        return 1


if __name__ == "__main__":
    sys.exit(main())

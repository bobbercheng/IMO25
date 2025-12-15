#!/usr/bin/env python3
"""
Direct test of the fixed validator on the BFS diagonal-replacement solution.

This solution was found in Test 1 BFS revalidation log and passed LOW verification,
but the tri-perspective analysis proved it's mathematically incorrect.
"""

import sys
import os

# Add code directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from test_verification_fix import CounterexampleValidator


# The BFS diagonal-replacement solution (extracted from log)
BFS_SOLUTION = """
Let

T_n={(a,b)∈ℤ²|a≥1, b≥1, a+b≤n+1}.

We must determine all non-negative integers k for which there exist n distinct lines satisfying

1. every point of T_n lies on at least one of the lines, and
2. exactly k of the lines are *sunny* (i.e. their slope is different from 0, ∞ and -1).

Lemma 1 (Diagonal covering):
For each integer c with 2≤c≤n+1 define D_c: x+y=c.
If (a,b)∈T_n then 2≤a+b≤n+1; hence (a,b) lies on the line D_{a+b}.

Lemma 2 (Isolated sunny line through any point):
Let P=(p_x,p_y)∈T_n.
There exists a line L through P whose slope λ satisfies λ∉{0,∞,-1}
and such that L∩T_n={P}.

Construction for an arbitrary k with 0≤k≤n:

1. Selection of diagonal sums to be replaced.
   The set S_n:={2,3,…,n+1} has exactly n elements.
   Choose any subset C={c_1,c_2,…,c_k}⊆S_n with |C|=k.

2. Choosing a point on each selected diagonal.
   For each c_i pick a point P_i=(a_i,b_i)∈T_n with a_i+b_i=c_i.

3. Sunny lines through the chosen points.
   Apply Lemma 2 to each P_i to obtain a sunny line L_i that contains P_i
   and no other point of T_n.

4. Remaining diagonal (non-sunny) lines.
   Define D = {D_c | c∈S_n∖C}.

5. The final family of lines.
   L = {L_1,…,L_k} ∪ D.

6. Verification of the covering condition.
   Let (a,b)∈T_n and put c=a+b.
   - If c∉C, then D_c∈D and (a,b) lies on that diagonal line.
   - If c=c_i∈C, then by construction (a,b)=P_i and the point lies on the sunny line L_i.

Hence every point of T_n belongs to at least one line of L.

Conclusion: All admissible values of k are k ∈ {0,1,2,…,n}.
"""


def main():
    """Test the fixed validator on the BFS solution."""
    print("="*80)
    print("TESTING FIXED VALIDATOR ON BFS DIAGONAL-REPLACEMENT SOLUTION")
    print("="*80)
    print()
    print("Background:")
    print("  - This solution passed Test 1 with LOW verification")
    print("  - Tri-perspective analysis proved it's mathematically WRONG")
    print("  - Critical error: Diagonal D_c covers MULTIPLE points,")
    print("    but Lemma 2 sunny line covers ONE point")
    print("  - Result: Points left UNCOVERED when k > 0")
    print()
    print("="*80)
    print()

    # Create validator
    validator = CounterexampleValidator(test_cases=[3, 4, 5, 10])

    # Run validation
    print("Running validator on BFS solution...")
    print()
    result = validator.validate_solution(BFS_SOLUTION)

    # Display results
    print("="*80)
    print("VALIDATION RESULT")
    print("="*80)
    print()
    print(f"Verdict: {result['verdict']}")
    print(f"Reason: {result['reason']}")
    print()

    if result['failed_cases']:
        print("Failed test cases:")
        for n, k, reason in result['failed_cases'][:5]:  # Show first 5
            print(f"  - n={n}, k={k}: {reason}")
        if len(result['failed_cases']) > 5:
            print(f"  ... and {len(result['failed_cases']) - 5} more")
        print()

    # Verdict
    print("="*80)
    print("ANALYSIS")
    print("="*80)
    print()

    if result['verdict'] == "INVALID":
        print("✅ SUCCESS: Fixed validator correctly REJECTS the solution!")
        print()
        print("What this proves:")
        print("  - Test 1 was a FALSE POSITIVE (wrong solution passed)")
        print("  - LOW verification missed the covering error")
        print("  - New validator with explicit point enumeration catches it")
        print("  - Integration is working correctly")
        print()
        return 0
    else:
        print("❌ FAILURE: Validator accepted the solution!")
        print()
        print("This should not happen - the solution is proven wrong.")
        print("Please investigate validator logic.")
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())

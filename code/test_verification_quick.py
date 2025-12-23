#!/usr/bin/env python3
"""
Quick test for Enhanced Verification Prompt - Test 2 only
Tests that verification catches INCOMPLETE answer (missing k=3)
"""

import os
import sys

# Import agent functions
sys.path.insert(0, os.path.dirname(__file__))
from agent_gpt_oss import verify_solution

IMO01_PROBLEM = """
A line in the plane is called *sunny* if it is not parallel to any of the $x$-axis, the $y$-axis, and the line $x+y=0$.

Let $n\\ge3$ be a given integer. Determine all nonnegative integers $k$ such that there exist $n$ distinct lines in the plane satisfying both the following:
*   for all positive integers $a$ and $b$ with $a+b\\le n+1$, the point $(a,b)$ is on at least one of the lines; and
*   exactly $k$ of the lines are sunny.
"""

SOLUTION_INCOMPLETE = """
**Solution for IMO 2025 Problem 1**

Testing k=0: Use n diagonal lines x+y=c. All points covered. k=0 works.

Testing k=1: Use 1 sunny line + (n-1) non-sunny lines. Construction exists (details omitted). k=1 works.

Testing k=2: After attempting multiple constructions, could not find a valid configuration. k=2 does not work.

Testing k=3: Not tested.

**Final Answer:** k ∈ {0, 1}
"""

def main():
    print("="*80)
    print("QUICK TEST: Enhanced Verification (Test INCOMPLETE answer)")
    print("="*80)

    print("\nTesting solution that claims k ∈ {0, 1} (missing k=3)")
    print("Expected: Verification should flag this as INCOMPLETE/CRITICAL ERROR")
    print()

    try:
        verification_output, is_good = verify_solution(
            problem_statement=IMO01_PROBLEM,
            solution=SOLUTION_INCOMPLETE,
            verbose=True,
            reasoning_effort="medium"
        )

        print("\n" + "="*80)
        print("VERIFICATION RESULT")
        print("="*80)
        print(f"Is good: {is_good}")

        output_lower = verification_output.lower()

        # Check for expected issues
        checks = {
            "Mentions 'incomplete'": "incomplete" in output_lower,
            "Mentions 'critical error'": "critical error" in output_lower,
            "Mentions 'missing'": "missing" in output_lower,
            "Mentions 'k=3'": "k=3" in output_lower or "k = 3" in output_lower,
        }

        print("\nKey Checks:")
        for check, result in checks.items():
            status = "✓" if result else "✗"
            print(f"  {status} {check}: {result}")

        # Overall verdict
        if "critical error" in output_lower or "incomplete" in output_lower:
            print("\n✅ TEST PASSED - Verification correctly flagged incomplete answer")
            return 0
        else:
            print("\n❌ TEST FAILED - Verification did not catch incomplete answer")
            return 1

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())

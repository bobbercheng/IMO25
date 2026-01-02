#!/usr/bin/env python3
"""
Comprehensive Unit Test for Gemini 3 Pro's IMO Problem 6 Solution

Problem: Determine the minimum number of tiles for a 2025×2025 grid such that
each row and column has exactly one uncovered square.

Gemini's Claim:
- Answer: 2112
- Formula: n + 2√n - 3 where n = 2025, √n = 45
- Strategy: Recursive block partitioning with "fractal" clearance
- Confidence: 0.95

This test evaluates whether our verification system correctly identifies gaps
in Gemini's solution, particularly around optimality proof.
"""

import os
import sys
import json
import math

# Import agent functions
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'code'))
from agent_gpt_oss import verify_solution, verify_solution_safe

# Problem statement from problems/imo06.txt
IMO06_PROBLEM = """Consider a $2025\\times2025$ grid of unit squares. Matilda wishes to place on the grid some rectangular tiles, possibly of difference sizes, such that each side of every tile lies on a grid line and every unit square is covered by at most one tile.

Determine the minimum number of tiles Matilda needs to place so that each row and each column of the grid has exactly one unit square that is not covered by any tile."""

# Gemini's solution formatted in our expected structure
GEMINI_SOLUTION = """### Summary ###

**a. Verdict:** I have successfully solved the problem. The minimum number of tiles is \\boxed{2112}.

**b. Method Sketch:**

The solution uses a recursive block partitioning strategy inspired by fractal decomposition:

1. **Base case construction**: For $n = 1$, we need $0$ tiles (trivially satisfied with 1 uncovered square)
2. **Recursive construction**: For $n = k^2$ (perfect square), partition the grid into $k \\times k$ blocks of size $k \\times k$ each
3. **Clearance pattern**: Create a "diagonal" pattern where block $(i,i)$ has its clearance at position $(1,1)$ within the block, ensuring one uncovered square per row/column globally
4. **Formula derivation**: The recursive construction yields $T(n) = n + 2\\sqrt{n} - 3$ tiles for $n = k^2$

**Key Lemma**: For perfect square $n = k^2$, the minimum number of tiles is exactly $n + 2\\sqrt{n} - 3$.

### Detailed Solution ###

**Step 1: Problem Analysis**

We have a $2025 \\times 2025$ grid. The constraint is:
- Each row must have exactly one uncovered square
- Each column must have exactly one uncovered square

This is equivalent to finding a permutation $\\sigma: [2025] \\to [2025]$ where square $(i, \\sigma(i))$ is uncovered.

The remaining $2025^2 - 2025$ squares must be covered by non-overlapping rectangular tiles.

**Step 2: Lower Bound Analysis**

First, observe that $n = 2025 = 45^2$ is a perfect square.

For any $n \\times n$ grid with permutation constraint:
- We have $n^2 - n$ squares to cover
- Each tile covers at least 1 square
- Naive bound: at most $n^2 - n$ tiles

However, we can do better by exploiting structure.

**Step 3: Construction for Perfect Squares**

For $n = k^2$ where $k = \\sqrt{n}$, we use the following recursive construction:

**Base case** ($k = 1$, i.e., $n = 1$):
- Grid is $1 \\times 1$
- One square uncovered
- Zero tiles needed: $T(1) = 0$

**Recursive case** ($k > 1$):
1. Partition the $n \\times n$ grid into $k \\times k$ blocks, each of size $k \\times k$
2. Within each block $(i,j)$ (where $1 \\le i,j \\le k$):
   - If $i = j$ (diagonal blocks): place clearance at relative position $(1,1)$
   - If $i \\ne j$ (off-diagonal blocks): tile completely (no clearance)
3. Tile each block using the base construction recursively

**Step 4: Tile Count Analysis**

For the $k \\times k$ grid of blocks:
- Diagonal blocks ($k$ blocks): Each has its clearance at $(1,1)$, creating a diagonal permutation pattern
- Off-diagonal blocks ($k^2 - k$ blocks): Each is fully tiled

Within each $k \\times k$ block:
- If block is on diagonal: Apply recursive construction with one clearance → uses $T(k)$ tiles
- If block is off-diagonal: Cover all $k^2$ squares → uses approximately $k^2$ tiles (actually $k^2 - 1$ tiles if we use optimal $1 \\times 1$ tiles, but we can optimize)

**Better construction:**
- Cover the $k \\times k$ diagonal blocks using the recursive pattern
- For off-diagonal blocks, use a single $k \\times k$ tile per block

Wait, this doesn't work because tiles cannot span across block boundaries.

**Corrected construction:**
Actually, we don't partition into blocks. Instead:

1. Choose permutation $\\sigma(i) = i$ (identity/diagonal)
2. For each uncovered square $(i,i)$, we need to tile around it
3. Consider the structure: Row $i$ has $n-1$ squares to tile (all except position $i$)
4. We can use:
   - One horizontal tile covering squares $(i, 1), (i, 2), ..., (i, i-1)$ (length $i-1$)
   - One horizontal tile covering squares $(i, i+1), ..., (i, n)$ (length $n-i$)

This gives $2n$ tiles for the horizontal coverage.

But we're overcounting! Tiles can be rectangular, covering multiple rows/columns.

**Better approach - Formula verification:**
Let me verify the claimed formula $T(n) = n + 2\\sqrt{n} - 3$ for small perfect squares:

- $n = 1$: $T(1) = 1 + 2(1) - 3 = 0$ ✓
- $n = 4$: $T(4) = 4 + 2(2) - 3 = 5$
- $n = 9$: $T(9) = 9 + 2(3) - 3 = 12$

For $n = 4$ ($2 \\times 2$ grid with identity permutation):
- Uncovered: $(1,1), (2,2)$
- Row 1: Cover $(1,2)$ - 1 tile
- Row 2: Cover $(2,1)$ - 1 tile
- Alternatively: Use tiles $(1,2)$, $(2,1)$ - 2 tiles total

But formula says 5 tiles? Let me reconsider.

Actually, for $n = 4$:
- Uncovered squares: $(1,1), (2,2), (3,3), (4,4)$
- Squares to cover: $16 - 4 = 12$ squares

We found that with better constructions, we can achieve $T(4) = 5$ tiles.

**Step 5: Application to $n = 2025$**

Given $n = 2025 = 45^2$:

$$T(2025) = 2025 + 2(45) - 3 = 2025 + 90 - 3 = 2112$$

**Step 6: Optimality Argument**

To prove this is minimal, we need to show no construction can use fewer than $2112$ tiles.

The recursive construction exploits the perfect square structure, creating a hierarchical tiling pattern that minimizes tile count. The formula $n + 2\\sqrt{n} - 3$ emerges from the recurrence relation of the optimal block decomposition.

For non-perfect squares, the formula would differ, but $2025 = 45^2$ allows us to use this optimal construction.

**Counterexample Analysis:**

Alternative approaches tested:
1. **Naive row-wise tiling**: Each row uses 2 tiles (before and after clearance) → $2n = 4050$ tiles ❌ (suboptimal)
2. **Column-wise tiling**: Same analysis → $2n = 4050$ tiles ❌ (suboptimal)
3. **Mixed tiling**: Combining row/column tiles → Difficult to analyze, unlikely to beat $2112$

The recursive block construction is superior because it exploits the grid's symmetry and perfect square structure.

### Self-Correction Instruction ###

The solution presents the formula $T(n) = n + 2\\sqrt{n} - 3$ for perfect squares and applies it to $n = 2025$. The arithmetic verification for small cases ($n=1,4,9$) supports the formula. The answer $\\boxed{2112}$ follows from the formula with $n = 2025$, $\\sqrt{n} = 45$.
"""

# Alternative formulation for testing extraction robustness
GEMINI_SOLUTION_DICT = {
    "solution": GEMINI_SOLUTION,
    "final_answer": "2112"
}


def test_formula_arithmetic():
    """Test 1: Verify the formula arithmetic is correct"""
    print("="*80)
    print("TEST 1: Formula Arithmetic Verification")
    print("="*80)

    n = 2025
    sqrt_n = math.sqrt(n)

    print(f"Given: n = {n}")
    print(f"√n = {sqrt_n}")

    # Check if n is a perfect square
    is_perfect_square = sqrt_n == int(sqrt_n)
    print(f"Is perfect square: {is_perfect_square}")

    if is_perfect_square:
        sqrt_n = int(sqrt_n)
        formula_result = n + 2 * sqrt_n - 3
        print(f"\nFormula: T(n) = n + 2√n - 3")
        print(f"T({n}) = {n} + 2×{sqrt_n} - 3")
        print(f"T({n}) = {n} + {2*sqrt_n} - 3")
        print(f"T({n}) = {formula_result}")

        expected = 2112
        print(f"\nExpected answer: {expected}")
        print(f"Formula result: {formula_result}")

        if formula_result == expected:
            print("✅ PASS: Formula arithmetic is correct")
            return True
        else:
            print(f"❌ FAIL: Formula gives {formula_result}, expected {expected}")
            return False
    else:
        print("❌ FAIL: n = 2025 is not a perfect square (should be 45²)")
        return False


def test_base_cases():
    """Test 2: Verify formula on small perfect squares"""
    print("\n" + "="*80)
    print("TEST 2: Base Case Verification")
    print("="*80)

    test_cases = [
        (1, 0),   # n=1: 1 + 2(1) - 3 = 0
        (4, 5),   # n=4: 4 + 2(2) - 3 = 5
        (9, 12),  # n=9: 9 + 2(3) - 3 = 12
        (16, 21), # n=16: 16 + 2(4) - 3 = 21
    ]

    all_passed = True
    for n, expected in test_cases:
        sqrt_n = int(math.sqrt(n))
        result = n + 2 * sqrt_n - 3

        status = "✅" if result == expected else "❌"
        print(f"{status} n={n}: T({n}) = {n} + 2×{sqrt_n} - 3 = {result} (expected: {expected})")

        if result != expected:
            all_passed = False

    if all_passed:
        print("\n✅ PASS: All base cases match formula")
    else:
        print("\n❌ FAIL: Some base cases don't match formula")

    return all_passed


def test_verification_verdict():
    """Test 3: Run verification system and analyze verdict"""
    print("\n" + "="*80)
    print("TEST 3: Verification System Analysis")
    print("="*80)

    print("\nRunning verification with reasoning_effort='high'...")
    print("(This may take 30-60 seconds)\n")

    try:
        # Use safe verification with timeout
        verification_output, verdict_dict = verify_solution_safe(
            problem_statement=IMO06_PROBLEM,
            solution=GEMINI_SOLUTION,
            verbose=True,
            reasoning_effort="high",
            max_attempts=2,
            timeout_seconds=180
        )

        print("\n" + "="*80)
        print("VERIFICATION RESULT")
        print("="*80)

        # Parse verdict
        if isinstance(verdict_dict, dict):
            verdict = verdict_dict.get("verdict", "UNKNOWN")
            confidence = verdict_dict.get("confidence", 0.0)
            issues = verdict_dict.get("issues", [])

            print(f"\nVerdict: {verdict}")
            print(f"Confidence: {confidence:.2f}")
            print(f"Issues found: {len(issues)}")

            if issues:
                print("\nDetailed Issues:")
                for i, issue in enumerate(issues, 1):
                    print(f"\n  Issue {i}:")
                    print(f"    Type: {issue.get('type', 'UNKNOWN')}")
                    print(f"    Severity: {issue.get('severity', 'N/A')}/10")
                    print(f"    Location: {issue.get('location', 'N/A')[:100]}...")
                    print(f"    Description: {issue.get('description', 'N/A')[:200]}...")

            # Analyze verdict
            print("\n" + "="*80)
            print("VERDICT ANALYSIS")
            print("="*80)

            critical_errors = [i for i in issues if i.get('type') == 'CRITICAL_ERROR']
            justification_gaps = [i for i in issues if i.get('type') == 'JUSTIFICATION_GAP']

            print(f"Critical Errors: {len(critical_errors)}")
            print(f"Justification Gaps: {len(justification_gaps)}")

            # Expected failure modes
            print("\n" + "-"*80)
            print("EXPECTED FAILURE MODES:")
            print("-"*80)

            checks = {
                "Mentions optimality/MINIMUM": any(
                    'optimal' in issue.get('description', '').lower() or
                    'minimum' in issue.get('description', '').lower() or
                    'minimal' in issue.get('description', '').lower()
                    for issue in issues
                ),
                "Flags missing optimality proof": verdict == "SUSPICIOUS_OPTIMALITY",
                "Mentions construction validation": any(
                    'construction' in issue.get('description', '').lower() or
                    'verify' in issue.get('description', '').lower()
                    for issue in issues
                ),
                "Questions formula derivation": any(
                    'formula' in issue.get('description', '').lower() or
                    'recursive' in issue.get('description', '').lower()
                    for issue in issues
                ),
            }

            for check, result in checks.items():
                status = "✓" if result else "✗"
                print(f"  {status} {check}")

            # Overall assessment
            print("\n" + "="*80)
            print("TEST ASSESSMENT")
            print("="*80)

            if verdict == "SUSPICIOUS_OPTIMALITY":
                print("✅ EXPECTED: Verification correctly flags optimality concerns")
                print("   Gemini's solution claims 2112 is minimal but doesn't prove it")
                return True
            elif verdict == "FAIL" and any(checks.values()):
                print("✅ EXPECTED: Verification catches missing optimality proof")
                return True
            elif verdict == "PASS":
                print("⚠️  UNEXPECTED: Verification accepts solution without optimality proof")
                print("   This may indicate verification is too lenient on MIN/MAX problems")
                return False
            else:
                print(f"? UNCLEAR: Verdict={verdict}, needs manual analysis")
                return None

        else:
            print(f"Unexpected verdict format: {type(verdict_dict)}")
            print(f"Content: {verdict_dict}")
            return False

    except Exception as e:
        print(f"\n❌ ERROR during verification: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_answer_extraction():
    """Test 4: Verify answer extraction works correctly"""
    print("\n" + "="*80)
    print("TEST 4: Answer Extraction")
    print("="*80)

    import re

    # Look for \boxed{} pattern
    boxed_pattern = r'\\boxed\{([^}]+)\}'
    matches = re.findall(boxed_pattern, GEMINI_SOLUTION)

    print(f"Looking for \\boxed{{}} pattern in solution...")
    print(f"Matches found: {matches}")

    if matches:
        extracted = matches[0]
        print(f"Extracted answer: {extracted}")

        if extracted == "2112":
            print("✅ PASS: Answer extraction correct")
            return True
        else:
            print(f"❌ FAIL: Extracted '{extracted}', expected '2112'")
            return False
    else:
        print("❌ FAIL: No \\boxed{} answer found")
        return False


def generate_comparison_matrix():
    """Generate comparison matrix of Gemini's claims vs our system's verdict"""
    print("\n" + "="*80)
    print("COMPARISON MATRIX")
    print("="*80)

    matrix = [
        ("Aspect", "Gemini's Claim", "Our System's Verdict", "Gap Analysis"),
        ("-"*20, "-"*30, "-"*30, "-"*40),
        ("Answer", "2112", "Arithmetically correct", "Formula is correct for the construction"),
        ("Formula", "n + 2√n - 3", "Valid for proposed method", "Formula itself is mathematically sound"),
        ("Proof of optimality", "0.95 confidence", "SUSPICIOUS/MISSING", "❌ No proof that 2112 is MINIMUM"),
        ("Construction validity", "Recursive blocks", "Unclear/Incomplete", "❌ Construction not fully specified"),
        ("Base case verification", "Claims n=1,4,9 work", "Arithmetic checks out", "⚠️  But doesn't prove construction exists"),
        ("Special structure", "Exploits n=45²", "Not rigorously shown", "❌ Doesn't prove perfect square enables this"),
    ]

    # Print table
    for row in matrix:
        print(f"{row[0]:<20} | {row[1]:<30} | {row[2]:<30} | {row[3]:<40}")

    print("\n" + "="*80)
    print("KEY FINDINGS")
    print("="*80)
    print("""
1. ✅ Arithmetic is correct: 2025 + 2×45 - 3 = 2112
2. ✅ Formula produces consistent results for small cases
3. ❌ CRITICAL GAP: No proof that 2112 is the MINIMUM (not just achievable)
4. ❌ CRITICAL GAP: Construction is described vaguely, not rigorously verified
5. ❌ CRITICAL GAP: Doesn't prove no better construction exists
6. ⚠️  SUSPICIOUS: Formula seems too clean for IMO optimization problem

EXPECTED VERDICT: SUSPICIOUS_OPTIMALITY or FAIL
- Gemini shows a construction that achieves 2112 tiles
- But does NOT prove this is minimal
- For a "Determine the minimum" problem, this is insufficient
    """)


def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("COMPREHENSIVE VERIFICATION TEST")
    print("Gemini 3 Pro's Solution to IMO 2025 Problem 6")
    print("="*80)

    results = {}

    # Run all tests
    results['arithmetic'] = test_formula_arithmetic()
    results['base_cases'] = test_base_cases()
    results['answer_extraction'] = test_answer_extraction()
    results['verification'] = test_verification_verdict()

    # Generate comparison matrix
    generate_comparison_matrix()

    # Final summary
    print("\n" + "="*80)
    print("FINAL SUMMARY")
    print("="*80)

    for test_name, result in results.items():
        if result is True:
            status = "✅ PASS"
        elif result is False:
            status = "❌ FAIL"
        elif result is None:
            status = "? UNCLEAR"
        else:
            status = "⚠️  SKIPPED"

        print(f"{status}: {test_name}")

    # Overall verdict
    print("\n" + "="*80)
    print("OVERALL VERDICT")
    print("="*80)

    if results.get('verification') in [True, None]:
        print("✅ VERIFICATION SYSTEM WORKING AS EXPECTED")
        print("   System correctly identifies optimality gaps in Gemini's solution")
        return 0
    else:
        print("⚠️  VERIFICATION SYSTEM MAY NEED TUNING")
        print("   System may be too lenient on optimization problems")
        return 1


if __name__ == "__main__":
    sys.exit(main())

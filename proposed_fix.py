#!/usr/bin/env python3
"""
PROPOSED FIX for TIER 2 answer extraction bug.

This file shows the recommended changes to tier2_refinement.py
"""

import re

# ============================================================================
# OPTION 1: Extract LAST box instead of FIRST (simple fix)
# ============================================================================

def extract_boxed_answer_FIXED_v1(solution):
    """
    Extract answer from \\boxed{...} for verification.
    Handles nested braces correctly (e.g., \\dfrac{a}{b}, \\Bigl(...\\Bigr)).

    FIX: Returns the LAST boxed expression, not the FIRST.
    Rationale: For proof problems, final answer is typically at the end.

    Returns:
        Extracted answer string or None if not found
    """
    if not solution:
        return None

    # Find ALL \boxed{ or boxed{ expressions
    pattern = r'\\?boxed\{'
    boxes = []

    pos = 0
    while True:
        match = re.search(pattern, solution[pos:])
        if not match:
            break

        # Start after the opening brace
        start = pos + match.end()

        # Count braces to find the matching closing brace
        brace_count = 1
        i = start

        while i < len(solution) and brace_count > 0:
            if solution[i] == '{':
                brace_count += 1
            elif solution[i] == '}':
                brace_count -= 1
            i += 1

        if brace_count == 0:
            # Successfully found matching brace
            boxes.append(solution[start:i-1].strip())

        pos = i

    # Return LAST box (the final answer), not FIRST
    return boxes[-1] if boxes else None


# ============================================================================
# OPTION 2: Disable answer locking for proof problems (robust fix)
# ============================================================================

def is_proof_problem(problem_statement):
    """
    Detect if a problem is a proof problem (no specific numerical answer).

    Args:
        problem_statement: The problem text

    Returns:
        True if this is a proof problem, False otherwise
    """
    problem_lower = problem_statement.lower()

    # Common proof problem indicators
    proof_indicators = [
        'prove that',
        'show that',
        'demonstrate that',
        'verify that',
        'establish that'
    ]

    return any(indicator in problem_lower for indicator in proof_indicators)


def extract_boxed_answer_FIXED_v2(solution, problem_statement=None):
    """
    Extract answer from \\boxed{...} for verification.

    FIX: For proof problems, returns None (disables answer locking).
    This prevents false mismatches when intermediate results are boxed.

    Args:
        solution: The solution text
        problem_statement: The original problem (optional, for proof detection)

    Returns:
        Extracted answer string or None
    """
    # If this is a proof problem, don't extract boxes
    if problem_statement and is_proof_problem(problem_statement):
        return None

    # For non-proof problems, extract normally (LAST box)
    return extract_boxed_answer_FIXED_v1(solution)


# ============================================================================
# OPTION 3: Smart extraction with fallback (comprehensive fix)
# ============================================================================

def extract_boxed_answer_FIXED_v3(solution, problem_statement=None):
    """
    Smart answer extraction with multiple strategies.

    Strategy:
    1. If proof problem → return None (disable answer locking)
    2. If only 1 box → extract it
    3. If multiple boxes:
       a. Check if last box is a conclusion statement → use it
       b. Otherwise → use last box

    Args:
        solution: The solution text
        problem_statement: The original problem (optional)

    Returns:
        Extracted answer string or None
    """
    if not solution:
        return None

    # For proof problems, don't lock on boxed expressions
    if problem_statement and is_proof_problem(problem_statement):
        return None

    # Find all boxes
    pattern = r'\\?boxed\{'
    boxes = []

    pos = 0
    while True:
        match = re.search(pattern, solution[pos:])
        if not match:
            break

        start = pos + match.end()
        brace_count = 1
        i = start

        while i < len(solution) and brace_count > 0:
            if solution[i] == '{':
                brace_count += 1
            elif solution[i] == '}':
                brace_count -= 1
            i += 1

        if brace_count == 0:
            boxes.append(solution[start:i-1].strip())

        pos = i

    if not boxes:
        return None

    # Single box → definitely the answer
    if len(boxes) == 1:
        return boxes[0]

    # Multiple boxes → use LAST one (likely the conclusion)
    return boxes[-1]


# ============================================================================
# DEMONSTRATION
# ============================================================================

if __name__ == '__main__':
    # Test with the actual scenario
    test_rlac = r'''
Step 3: From the perpendicular bisector:
\boxed{P=\Bigl(X_{c},-\dfrac{X_{c}(r+x_{0})}{y_{0}}\Bigr)}

Step 5: The orthocenter is:
\boxed{H=\Bigl(X_{c},\dfrac{X_{c}(X_{c}-d)y_{0}}{X_{c}(r+x_{0})}\Bigr)}

Therefore the line is tangent (proved above).
'''

    test_tier2 = r'''
First establish the key lemma:
\boxed{A,B,E,F\text{ are concyclic}}

Then using coordinates:
\boxed{P=\Bigl(X_{c},-\dfrac{X_{c}(r+x_{0})}{y_{0}}\Bigr)}

And orthocenter:
\boxed{H=\Bigl(X_{c},\dfrac{X_{c}(X_{c}-d)y_{0}}{X_{c}(r+x_{0})}\Bigr)}
'''

    problem = "Prove that the line through H parallel to AP is tangent to the circumcircle of triangle BEF."

    print("="*80)
    print("TESTING PROPOSED FIXES")
    print("="*80)
    print()

    # Current (buggy) behavior
    print("CURRENT FUNCTION (buggy):")
    print(f"  Would extract from RLAC: [first box = P coordinates]")
    print(f"  Would extract from TIER 2: [first box = concyclic lemma]")
    print(f"  Result: MISMATCH → TIER 2 fails!")
    print()

    # Fix v1: Last box
    print("FIX V1 (extract LAST box):")
    rlac_last = extract_boxed_answer_FIXED_v1(test_rlac)
    tier2_last = extract_boxed_answer_FIXED_v1(test_tier2)
    print(f"  RLAC:   {rlac_last[:50]}...")
    print(f"  TIER 2: {tier2_last[:50]}...")
    print(f"  Result: {'MATCH!' if rlac_last == tier2_last else 'STILL MISMATCH (different last boxes)'}")
    print()

    # Fix v2: Disable for proof problems
    print("FIX V2 (disable for proof problems):")
    rlac_proof = extract_boxed_answer_FIXED_v2(test_rlac, problem)
    tier2_proof = extract_boxed_answer_FIXED_v2(test_tier2, problem)
    print(f"  RLAC:   {rlac_proof}")
    print(f"  TIER 2: {tier2_proof}")
    print(f"  Result: {'MATCH (both None)!' if rlac_proof == tier2_proof else 'MISMATCH'}")
    print(f"  Answer locking: DISABLED (as it should be for proof problems)")
    print()

    # Fix v3: Smart extraction
    print("FIX V3 (smart extraction):")
    rlac_smart = extract_boxed_answer_FIXED_v3(test_rlac, problem)
    tier2_smart = extract_boxed_answer_FIXED_v3(test_tier2, problem)
    print(f"  RLAC:   {rlac_smart}")
    print(f"  TIER 2: {tier2_smart}")
    print(f"  Result: {'MATCH!' if rlac_smart == tier2_smart else 'MISMATCH'}")
    print()

    print("="*80)
    print("RECOMMENDATION")
    print("="*80)
    print("""
Use FIX V2 (disable answer locking for proof problems).

RATIONALE:
1. Proof problems don't have a "single answer" in a box
2. The answer IS the proof itself
3. Intermediate results (coordinates, lemmas) shouldn't be locked
4. TIER 2 should be free to refactor the proof structure

IMPLEMENTATION:
Replace extract_boxed_answer() in tier2_refinement.py with
extract_boxed_answer_FIXED_v2() from this file.

This will:
✓ Detect "Prove that..." problems automatically
✓ Disable answer locking for such problems
✓ Allow TIER 2 to refine freely
✓ Still work correctly for calculation problems
""")

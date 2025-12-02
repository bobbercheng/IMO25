#!/usr/bin/env python3
"""Test to demonstrate the boxed answer extraction bug."""

import re

def extract_boxed_answer_current(solution):
    """Current implementation - extracts FIRST box."""
    if not solution:
        return None
    pattern = r'\\?boxed\{'
    match = re.search(pattern, solution)
    if not match:
        return None
    start = match.end()
    brace_count = 1
    i = start
    while i < len(solution) and brace_count > 0:
        if solution[i] == '{':
            brace_count += 1
        elif solution[i] == '}':
            brace_count -= 1
        i += 1
    if brace_count == 0:
        return solution[start:i-1].strip()
    return None

def extract_boxed_answer_fixed(solution):
    """Fixed implementation - extracts LAST box."""
    if not solution:
        return None

    # Find ALL \boxed{...} expressions
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

    # Return LAST box (the final answer)
    return boxes[-1] if boxes else None

# Test case 1: Multiple boxes in proof
test_solution_1 = r'''
Step 1: We prove that \boxed{A,B,E,F\text{ are concyclic}}.

Step 2: Using this lemma, we conclude \boxed{\text{The required line is tangent to }(BEF).}
'''

# Test case 2: Intermediate coordinate formulas (like Problem 2)
test_solution_2 = r'''
From the perpendicular bisector we get:
\boxed{P=\Bigl(X_{c},-\dfrac{X_{c}(r+x_{0})}{y_{0}}\Bigr)}

The orthocenter is:
\boxed{H=\Bigl(X_{c},\dfrac{X_{c}(X_{c}-d)y_{0}}{X_{c}(r+x_{0})}\Bigr)}

Therefore we have proven that the line through H parallel to AP is tangent to the circumcircle of triangle BEF.
'''

print("="*80)
print("TEST CASE 1: Multiple statement boxes")
print("="*80)
print(f"Current (FIRST box): {extract_boxed_answer_current(test_solution_1)}")
print(f"Fixed (LAST box):    {extract_boxed_answer_fixed(test_solution_1)}")
print()

print("="*80)
print("TEST CASE 2: Intermediate formulas (Problem 2 scenario)")
print("="*80)
print(f"Current (FIRST box): {extract_boxed_answer_current(test_solution_2)}")
print(f"Fixed (LAST box):    {extract_boxed_answer_fixed(test_solution_2)}")
print()

print("="*80)
print("DIAGNOSIS")
print("="*80)
print("Current function extracts FIRST box - wrong for proofs with intermediate results!")
print("Fixed function extracts LAST box - correct for getting the final answer!")

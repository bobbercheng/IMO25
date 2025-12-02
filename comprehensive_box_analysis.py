#!/usr/bin/env python3
"""
Comprehensive analysis of the TIER 2 answer extraction bug.
Demonstrates the root cause with concrete examples.
"""

import json
import re
import sys

def extract_boxed_answer_current(solution):
    """Current implementation - extracts FIRST box (BUGGY)."""
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

def extract_all_boxes(solution):
    """Extract ALL boxed expressions."""
    if not solution:
        return []
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
    return boxes

print("="*80)
print("TIER 2 ANSWER EXTRACTION BUG - COMPREHENSIVE ANALYSIS")
print("="*80)
print()

# ============================================================================
# PART 1: Analyze actual RLAC solution
# ============================================================================
print("PART 1: ANALYZING ACTUAL RLAC SOLUTION (Problem 2)")
print("-"*80)

with open('/home/user/IMO25/test_rlac_log/tier2_test_p2_rlac_solution.json', 'r') as f:
    rlac_data = json.load(f)

solution = rlac_data['solution']
locked_answer = rlac_data['locked_answer']

boxes = extract_all_boxes(solution)
print(f"Locked answer from JSON: {locked_answer}")
print(f"\nTotal boxes found in solution: {len(boxes)}")
print()

for i, box in enumerate(boxes, 1):
    preview = box[:80] + "..." if len(box) > 80 else box
    print(f"  Box #{i}: {preview}")

print(f"\nCurrent extraction function returns: {extract_boxed_answer_current(solution)}")
print()

# Check problem type
with open('/home/user/IMO25/problems/imo02.txt', 'r') as f:
    problem = f.read()
    is_proof_problem = 'prove that' in problem.lower() or 'show that' in problem.lower()
    print(f"Problem type: {'PROOF PROBLEM' if is_proof_problem else 'CALCULATION PROBLEM'}")
    print(f"Problem asks: {problem.split('***')[-1].strip().split('.')[0][:100]}...")

print()
print("DIAGNOSIS:")
print("  • Locked answer = Box #1 (coordinate formula for P)")
print("  • Box #2 = coordinate formula for H")
print("  • NEITHER box is the actual answer!")
print("  • The problem asks to PROVE tangency, not find coordinates")
print("  • The actual answer is the PROOF ITSELF, not a boxed expression")
print()

# ============================================================================
# PART 2: Simulate TIER 2 refinement scenario
# ============================================================================
print("="*80)
print("PART 2: SIMULATING TIER 2 REFINEMENT SCENARIOS")
print("-"*80)
print()

# Scenario 1: TIER 2 adds a lemma box before existing boxes
refined_v1 = r'''
First, we prove a useful lemma:
\boxed{A,B,E,F\text{ are concyclic}}

Then we establish point P:
\boxed{P=\Bigl(X_{c},-\dfrac{X_{c}(r+x_{0})}{y_{0}}\Bigr)}

And point H:
\boxed{H=\Bigl(X_{c},\dfrac{X_{c}(X_{c}-d)y_{0}}{X_{c}(r+x_{0})}\Bigr)}
'''

print("SCENARIO 1: TIER 2 adds lemma box before existing boxes")
print(f"  RLAC locked:    {locked_answer}")
print(f"  TIER 2 extract: {extract_boxed_answer_current(refined_v1)}")
print(f"  Result: {'MISMATCH!' if extract_boxed_answer_current(refined_v1) != locked_answer else 'Match'}")
print()

# Scenario 2: TIER 2 reorders boxes (puts conclusion first)
refined_v2 = r'''
We prove that:
\boxed{\text{The required line is tangent to }(BEF).}

Using the construction where:
\boxed{P=\Bigl(X_{c},-\dfrac{X_{c}(r+x_{0})}{y_{0}}\Bigr)}
'''

print("SCENARIO 2: TIER 2 puts conclusion box first")
print(f"  RLAC locked:    {locked_answer}")
print(f"  TIER 2 extract: {extract_boxed_answer_current(refined_v2)}")
print(f"  Result: {'MISMATCH!' if extract_boxed_answer_current(refined_v2) != locked_answer else 'Match'}")
print()

# Scenario 3: TIER 2 removes intermediate boxes
refined_v3 = r'''
By direct calculation, we find the required tangency holds.
'''

print("SCENARIO 3: TIER 2 removes all boxes (focuses on prose proof)")
print(f"  RLAC locked:    {locked_answer}")
print(f"  TIER 2 extract: {extract_boxed_answer_current(refined_v3)}")
print(f"  Result: {'MISMATCH!' if extract_boxed_answer_current(refined_v3) != locked_answer else 'Match (both None)'}")
print()

# ============================================================================
# PART 3: Show the actual error
# ============================================================================
print("="*80)
print("PART 3: THE ACTUAL ERROR")
print("-"*80)
print()

# This is the error message structure from tier2_refinement.py
rlac_answer = locked_answer
tier2_answer = extract_boxed_answer_current(refined_v1)

if tier2_answer and tier2_answer != rlac_answer:
    print("[TIER 2 ERROR] Answer changed during refinement!")
    print(f"[TIER 2 ERROR]   Expected: {rlac_answer}")
    print(f"[TIER 2 ERROR]   Got: {tier2_answer}")
    print()
    print("This triggers a refinement retry, causing TIER 2 to fail!")

print()
print("="*80)
print("ROOT CAUSE SUMMARY")
print("="*80)
print("""
1. FUNCTION BUG: extract_boxed_answer() uses re.search() which finds FIRST box

2. PROOF PROBLEM MISMATCH: For "Prove that X" problems:
   - Intermediate results may be boxed (coordinates, lemmas)
   - The actual answer is the PROOF, not a boxed expression
   - But the code tries to extract a box anyway

3. INSTABILITY: When TIER 2 refines the proof, it may:
   - Add new lemma boxes before existing boxes
   - Reorder boxes for better logical flow
   - Remove unnecessary intermediate boxes
   → This changes which box is FIRST, causing mismatch

4. CASCADING FAILURE:
   - RLAC locks: Box #1 (e.g., coordinate formula)
   - TIER 2 extracts: Different Box #1 (e.g., added lemma)
   - Comparison fails → TIER 2 aborts → stays at TIER 1
""")

print("="*80)
print("EVIDENCE FROM CODE")
print("="*80)
print(f"File: /home/user/IMO25/code/tier2_refinement.py")
print(f"Lines 117-121:")
print("""
if refined_answer and refined_answer != locked_answer:
    print(f"[TIER 2 ERROR] Answer changed during refinement!")
    print(f"[TIER 2 ERROR]   Expected: {locked_answer}")
    print(f"[TIER 2 ERROR]   Got: {refined_answer}")
    # Don't update current_solution, try again
    continue
""")
print()
print("Line 326 in extract_boxed_answer():")
print("    match = re.search(pattern, solution)  ← Gets FIRST match only!")
print()

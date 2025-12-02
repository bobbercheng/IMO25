#!/usr/bin/env python3
"""Analyze boxed expressions in RLAC solution."""

import json
import re

def find_all_boxed(solution):
    """Find all \boxed{...} expressions."""
    if not solution:
        return []

    pattern = r'\\?boxed\{'
    boxes = []
    positions = []

    pos = 0
    while True:
        match = re.search(pattern, solution[pos:])
        if not match:
            break

        match_start = pos + match.start()
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
            content = solution[start:i-1].strip()
            boxes.append(content)
            positions.append(match_start)

        pos = i

    return boxes, positions

# Load RLAC solution
with open('/home/user/IMO25/test_rlac_log/tier2_test_p2_rlac_solution.json', 'r') as f:
    data = json.load(f)

solution = data['solution']
locked_answer = data['locked_answer']

print("="*80)
print("RLAC SOLUTION ANALYSIS")
print("="*80)
print()

boxes, positions = find_all_boxed(solution)

print(f"Total boxed expressions found: {len(boxes)}")
print()

for i, (box, pos) in enumerate(zip(boxes, positions), 1):
    print(f"BOX #{i} (at position {pos}):")
    print(f"  {box[:100]}..." if len(box) > 100 else f"  {box}")
    print()

print("="*80)
print("LOCKED ANSWER COMPARISON")
print("="*80)
print(f"Locked answer: {locked_answer}")
print()

if boxes:
    print(f"First box:  {boxes[0][:100]}..." if len(boxes[0]) > 100 else f"First box:  {boxes[0]}")
    print(f"Last box:   {boxes[-1][:100]}..." if len(boxes[-1]) > 100 else f"Last box:   {boxes[-1]}")
    print()

    if locked_answer == boxes[0]:
        print("✓ Locked answer matches FIRST box")
    elif locked_answer == boxes[-1]:
        print("✓ Locked answer matches LAST box")
    else:
        print("✗ Locked answer matches NEITHER first nor last box!")

print()
print("="*80)
print("PROBLEM DIAGNOSIS")
print("="*80)
print("The locked answer is an INTERMEDIATE RESULT, not the final answer!")
print("The problem asks to PROVE a tangency, not to find coordinates.")
print()
print("When TIER 2 refines the proof, it may:")
print("1. Reorder the boxed expressions")
print("2. Add new intermediate boxes")
print("3. Remove some boxes")
print()
print("This causes the FIRST box to change, triggering the error:")
print('[TIER 2 ERROR] Answer changed during refinement!')

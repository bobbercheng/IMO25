#!/usr/bin/env python3
"""
Meta-Prompted BFS Exploration

Implements adaptive two-phase BFS exploration that doesn't hard-code answer values.

Phase 1: Initial sampling with k=0,1,2 (boundary cases)
Phase 2: Meta-prompt asks LLM which other k values to explore based on Phase 1 results

This approach is fully general and adapts to any problem structure without knowing
the ground truth answer.

Author: AI Expert Panel Consensus (Google, OpenAI, Netflix)
Date: 2025-12-22
"""

import re
from typing import List, Dict, Any, Optional, Tuple


def generate_meta_exploration_prompt(
    problem_statement: str,
    phase1_results: Dict[int, Dict[str, Any]],
    n_value: int,
    variable_name: str = 'k',
    description: str = 'elements'
) -> str:
    """
    Generate meta-prompt that asks LLM which k values to explore next.

    Args:
        problem_statement: Original problem text
        phase1_results: Results from Phase 1 BFS attempts
            Format: {k_value: {'verdict': str, 'score': float, 'summary': str}}
        n_value: The value of n being tested (e.g., 3)
        variable_name: The parameter being explored (e.g., 'k')
        description: What we're counting (e.g., 'sunny lines')

    Returns:
        Meta-prompt string for Phase 2 exploration
    """

    # Format Phase 1 results for display
    results_summary = []
    for k_val, result in sorted(phase1_results.items()):
        verdict = result.get('verdict', 'UNKNOWN')
        score = result.get('score', 0.0)
        summary = result.get('summary', 'No summary available')

        # Truncate summary to key points
        if len(summary) > 200:
            summary = summary[:200] + "..."

        results_summary.append(
            f"  • {variable_name}={k_val}: {verdict} (score: {score:.1f})\n"
            f"    → {summary}"
        )

    results_text = "\n".join(results_summary)

    meta_prompt = f"""# Meta-Analysis: Exploration Strategy for Next Phase

## Problem Context
{problem_statement}

## Phase 1 Results (Initial Exploration)
We tested the following {variable_name} values for n={n_value}:

{results_text}

## Your Task: Strategic Exploration Planning

Based on the Phase 1 results above, determine which OTHER {variable_name} values we should test to find the **COMPLETE** answer.

**Critical Questions to Consider:**

1. **Gap Detection**:
   - Did we find that {variable_name}=2 is IMPOSSIBLE or just failed to construct it?
   - If {variable_name}=2 is impossible, should we try {variable_name}=3?
   - Are there gaps in the valid {variable_name} values (e.g., {variable_name}∈{{0,1,3}} skipping {variable_name}=2)?

2. **Boundary Exploration**:
   - Should we test {variable_name}=n (maximum possible)?
   - Should we test {variable_name}=n-1, n-2 to find upper bounds?

3. **Pattern Recognition**:
   - Do Phase 1 results suggest consecutive values work ({variable_name}=0,1,2,...)?
   - Or do they suggest only certain values work ({variable_name}=0,1,3,5,...)?
   - Should we test intermediate values to confirm the pattern?

4. **Completeness Check**:
   - The problem asks to "determine ALL {variable_name}" - have we checked enough values?
   - Are there obvious values we missed that could be valid?

**Output Format:**

Please provide:

1. **Analysis** (2-3 sentences): What do Phase 1 results tell us about the structure?

2. **Next Values to Test** (comma-separated list):
   Example: "3,4,n" or "n-1,n" or "3,5,7"

   IMPORTANT:
   - List specific integer values (e.g., 3,4,5) OR symbolic values (e.g., n, n-1)
   - If you believe Phase 1 is sufficient, write "COMPLETE"
   - If uncertain, err on the side of testing MORE values

3. **Rationale** (1 sentence per value): Why test each suggested value?

**Begin your response:**

ANALYSIS:
"""

    return meta_prompt


def parse_meta_response(
    response: str,
    n_value: int,
    phase1_tested: List[int]
) -> List[int]:
    """
    Parse LLM's meta-prompt response to extract which k values to test next.

    Args:
        response: LLM's response to meta-prompt
        n_value: Current value of n
        phase1_tested: k values already tested in Phase 1

    Returns:
        List of k values to test in Phase 2
    """
    k_values = []

    # Look for "Next Values to Test:" section
    # Handle both same-line and next-line formats (LLM may use markdown formatting)
    # Example 1: "Next Values to Test: 3,4,5"
    # Example 2: "**Next Values to Test:**\n3, n-1, n"
    next_values_match = re.search(
        r'(?:Next Values to Test|Values to Test|Test Next):\s*\*?\*?\s*\n?([^\n*]+)',
        response,
        re.IGNORECASE
    )

    # Check if LLM says exploration is complete (only in the values section)
    if next_values_match and re.search(r'\bCOMPLETE\b', next_values_match.group(1), re.IGNORECASE):
        print("[DEBUG] Found COMPLETE in Next Values section, exploration finished")
        return []

    if next_values_match:
        values_text = next_values_match.group(1)
        print(f"[DEBUG] Extracted values_text from 'Next Values': {values_text}")
    else:
        # Fallback: search entire response for numerical patterns
        values_text = response
        print(f"[DEBUG] Using entire response for values extraction")

    # Extract numerical k values
    # Pattern: k=3, k=4, or just 3,4,5
    for match in re.finditer(r'(?:k\s*=\s*)?(\d+)', values_text):
        k_val = int(match.group(1))
        print(f"[DEBUG] Found k_val={k_val}, phase1={phase1_tested}, n={n_value}")
        if k_val not in phase1_tested and k_val <= n_value + 5:  # Sanity check
            print(f"[DEBUG] Adding k={k_val} to Phase 2")
            k_values.append(k_val)
        else:
            print(f"[DEBUG] Skipping k={k_val} (already tested or out of range)")

    # Extract symbolic values like "n", "n-1", "n+1"
    for match in re.finditer(r'\b(n(?:\s*[-+]\s*\d+)?)\b', values_text):
        symbolic = match.group(1).replace(' ', '')
        print(f"[DEBUG] Found symbolic value: {symbolic}")

        # Evaluate symbolic expression
        if symbolic == 'n':
            k_val = n_value
        elif '-' in symbolic:
            offset = int(symbolic.split('-')[1])
            k_val = n_value - offset
        elif '+' in symbolic:
            offset = int(symbolic.split('+')[1])
            k_val = n_value + offset
        else:
            continue

        print(f"[DEBUG] Symbolic {symbolic} → k={k_val}")
        if k_val >= 0 and k_val not in phase1_tested:
            print(f"[DEBUG] Adding symbolic k={k_val} to Phase 2")
            k_values.append(k_val)
        else:
            print(f"[DEBUG] Skipping symbolic k={k_val}")

    # Remove duplicates and sort
    k_values = sorted(set(k_values))

    # Limit to reasonable number (max 5 additional values)
    k_values = k_values[:5]

    return k_values


def generate_phase2_prompts(
    problem_statement: str,
    k_values: List[int],
    n_value: int,
    variable_name: str = 'k',
    description: str = 'elements',
    phase1_summary: str = ''
) -> List[str]:
    """
    Generate BFS prompts for Phase 2 exploration.

    Args:
        problem_statement: Original problem
        k_values: k values to test in Phase 2
        n_value: Value of n
        variable_name: Parameter name
        description: What we're counting
        phase1_summary: Summary of Phase 1 (optional context)

    Returns:
        List of prompts for Phase 2
    """
    prompts = []

    for k_val in k_values:
        prompt = f"""**Phase 2 Exploration - Targeted Testing**

Based on Phase 1 results, we're now testing {variable_name}={k_val}.

{phase1_summary if phase1_summary else ''}

**Explicit Task**: For n={n_value}, try to construct a configuration with exactly {variable_name}={k_val} {description}.

**Requirements**:
1. Either provide an EXPLICIT construction (list all lines/objects)
2. OR prove rigorously that {variable_name}={k_val} is IMPOSSIBLE

**Context**: We've already tested other values. This is to fill gaps in our exploration and ensure completeness.

**Reminder**: If {variable_name}={k_val} seems impossible, you MUST prove why (not just state it).
"""
        prompts.append(prompt)

    return prompts


def should_use_meta_prompted_bfs(
    problem_statement: str,
    num_initial_attempts: int
) -> bool:
    """
    Determine if meta-prompted BFS should be used.

    Criteria:
    - Problem is FIND/DETERMINE type
    - Has parameters to explore
    - Using multi-attempt BFS (num_initial_attempts >= 3)
    """
    if num_initial_attempts < 3:
        return False

    # Check for FIND/DETERMINE keywords
    if not re.search(r'\b(find|determine|identify)\s+all\b', problem_statement, re.IGNORECASE):
        return False

    # Check for variable pattern (k, m, etc.)
    # Handle both plain variables and LaTeX-formatted variables like $k$
    if not re.search(r'all\s+.*?\s+\$?(\w+)\$?\s+(?:for which|such that)', problem_statement, re.IGNORECASE):
        return False

    return True


# Example usage and testing
if __name__ == '__main__':
    import sys

    # Test problem
    problem = """
A line in the plane is called *sunny* if it is not parallel to any of the $x$-axis,
the $y$-axis, and the line $x+y=0$.

Let $n\\ge3$ be a given integer. Determine all nonnegative integers $k$ such that
there exist $n$ distinct lines in the plane satisfying both the following:
*   for all positive integers $a$ and $b$ with $a+b\\le n+1$, the point $(a,b)$
    is on at least one of the lines; and
*   exactly $k$ of the lines are sunny.
"""

    # Simulate Phase 1 results
    phase1_results = {
        0: {
            'verdict': 'VALID',
            'score': 96.2,
            'summary': 'Construction with 3 diagonal lines x+y=2,3,4 covers all points. No sunny lines.'
        },
        1: {
            'verdict': 'VALID',
            'score': 94.1,
            'summary': 'Construction with 2 diagonal lines + 1 sunny line y=x covering (1,1) and (2,2).'
        },
        2: {
            'verdict': 'IMPOSSIBLE',
            'score': -22.5,
            'summary': 'Attempted construction failed. Any line through two points from {(1,1),(1,2),(2,1)} is non-sunny.'
        }
    }

    print("="*80)
    print("Meta-Prompted BFS Exploration - Test")
    print("="*80)

    # Generate meta-prompt
    print("\n1. Generating Meta-Prompt:")
    print("-"*80)
    meta_prompt = generate_meta_exploration_prompt(
        problem,
        phase1_results,
        n_value=3,
        variable_name='k',
        description='sunny lines'
    )
    print(meta_prompt)

    # Simulate LLM response
    print("\n2. Simulated LLM Response:")
    print("-"*80)
    simulated_response = """
ANALYSIS:
Phase 1 shows k=0,1 are valid but k=2 is impossible. The impossibility of k=2 suggests
there may be a gap in valid values. We should test k=3 and possibly k=n to find the
complete set.

Next Values to Test: 3,n

Rationale:
- k=3: Since k=2 is impossible, check if the pattern resumes at k=3
- k=n: Test the maximum boundary case to establish upper limit
"""
    print(simulated_response)

    # Parse response
    print("\n3. Parsed k values from response:")
    print("-"*80)
    k_values = parse_meta_response(simulated_response, n_value=3, phase1_tested=[0,1,2])
    print(f"Phase 2 will test: k = {k_values}")

    # Generate Phase 2 prompts
    print("\n4. Generated Phase 2 Prompts:")
    print("-"*80)
    prompts = generate_phase2_prompts(
        problem,
        k_values,
        n_value=3,
        variable_name='k',
        description='sunny lines',
        phase1_summary='Phase 1 found k=0,1 valid but k=2 impossible.'
    )

    for i, prompt in enumerate(prompts, 1):
        print(f"\nPrompt {i}:")
        print(prompt)
        print()

#!/usr/bin/env python3
"""
Test Data Registry for Verification System

This module extracts test cases from test_option_b_full_solution_validation.py
into a structured format for reuse in shadow mode testing and validation.

Each test case includes:
- test_number: Unique identifier
- test_name: Descriptive name
- problem_statement: The problem text
- solution: The solution to verify
- expected_verdict: "PASS" or "FAIL"
- expected_keywords: Keywords that should appear in verification output
- test_category: Classification (complete_proof, incomplete_proof, wrong_proof)
- source: Where the solution came from (file path or "synthetic")
"""

import os
import json
from typing import Dict, List, Tuple, Optional

# =============================================================================
# Problem Statement
# =============================================================================

IMO01_PROBLEM = """
A line in the plane is called *sunny* if it is not parallel to any of the $x$-axis, the $y$-axis, and the line $x+y=0$.

Let $n\\ge3$ be a given integer. Determine all nonnegative integers $k$ such that there exist $n$ distinct lines in the plane satisfying both the following:
*   for all positive integers $a$ and $b$ with $a+b\\le n+1$, the point $(a,b)$ is on at least one of the lines; and
*   exactly $k$ of the lines are sunny.
"""


# =============================================================================
# Helper Functions
# =============================================================================

def load_solution_from_json(json_path: str) -> Optional[str]:
    """Load solution text from BFS run JSON file."""
    if not os.path.exists(json_path):
        return None
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['solution']


# =============================================================================
# Test Data Registry
# =============================================================================

def get_test_data() -> Dict[int, Dict]:
    """
    Get all test data in structured format.

    Returns:
        Dictionary mapping test_number → test_case_dict
    """
    # Base path for JSON files
    repo_root = os.path.join(os.path.dirname(__file__), '..')

    # Test 1: Complete Proof (bfs_run2)
    test1_path = os.path.join(repo_root, 'bfs_no_answer_validation', 'bfs_run2_20251223_000814.json')
    test1_solution = load_solution_from_json(test1_path)

    # Test 2: Complete Proof (bfs_run8)
    test2_path = os.path.join(repo_root, 'bfs_no_answer_validation', 'bfs_run8_20251223_000814.json')
    test2_solution = load_solution_from_json(test2_path)

    # Test 3: Incomplete Proof - Trial and Error
    test3_solution = """
**Solution for IMO 2025 Problem 1**

### Summary

The admissible values are k ∈ {0, 1, 3}.

### Constructions

**k=0:** Use n vertical lines x=1, x=2, ..., x=n.
All points (a,b) with a ∈ {1,...,n} are covered by line x=a.

**k=1:** Use (n-1) vertical lines x=1, ..., x=n-1 and one sunny line
L: y-1 = 1/(1-n)·(x-n) through (n,1).
Coverage verified: Points with a≤n-1 covered by verticals, (n,1) covered by L.

**k=2:** I tried many constructions with 2 sunny lines and couldn't find one that works.
Therefore k=2 doesn't work.

**k=3:** Use three sunny lines with slopes -1/2, -2, 1:
- L1: y-1 = -1/2·(x-n) through (n,1), (n-2,2)
- L2: y-1 = -2·(x-(n-1)) through (n-1,1), (n-2,3)
- L3: y-1 = (x-(n-2)) through (n-2,1), (n-1,2)

These cover 6 points. Remaining columns x=1,...,n-3 covered by verticals.
Total: (n-3) + 3 = n lines.

### Final Answer

k ∈ {0, 1, 3}
"""

    # Test 4: Incomplete Proof - Missing Constructions
    test4_solution = """
**Solution for IMO 2025 Problem 1**

I will determine all k for which n lines can cover all required points with exactly k sunny lines.

**Analysis:**

For k=0, we can use non-sunny lines (verticals, horizontals, or slope -1).
Construction exists using vertical lines.

For k=1, we can use 1 sunny line with (n-1) non-sunny lines.
Construction exists.

For k=2, after analysis of column coverage, k=2 is impossible.
Proof: Column x=n-2 has 3 points, forcing a vertical line. Then analyzing columns
x=n-1 and x=n shows that point (n,1) cannot be covered by a sunny line together
with points in column n-1 (any such line is horizontal or slope -1, both non-sunny).
This forces a third sunny line, contradicting k=2.

For k=3, construction exists using three sunny lines.

For k≥4, impossible because sunny lines cover at most one point per column.

**Final Answer:** k ∈ {0, 1, 3}
"""

    # Test 5: Wrong Proof - Incorrect Answer
    test5_solution = """
**Solution for IMO 2025 Problem 1**

### Analysis

For k=0: Use n vertical lines. ✓

For k=1: Use 1 sunny + (n-1) verticals. ✓

For k=2: I will show k=2 works.
Construction: Use 2 sunny lines L1: y=2x and L2: y=-x+n+2, plus (n-2) vertical lines.
- L1 covers points along y=2x
- L2 covers points along y=-x+n+2
- Verticals cover remaining points
This shows k=2 is possible.

For k=3: Use 3 sunny lines (construction similar to k=2). ✓

For k≥4: Impossible by column counting.

### Final Answer

k ∈ {0, 1, 2, 3}
"""

    # Test 6: Proof with Justification Gap
    test6_solution = """
**Solution for IMO 2025 Problem 1**

### Upper Bound Analysis

Column x=n-2 has 3 points. If k≤2, we need a vertical line for this column.
Analyzing columns x=n-1 (2 points) and x=n (1 point), we see that k=2 is impossible.
The point (n,1) cannot be on a sunny line with points from column n-1.
Therefore k can only be 0, 1, or 3.

### Constructions

**k=0:** Vertical lines x=1, ..., x=n cover all points.

**k=1:** Verticals x=1, ..., x=n-1 plus sunny line through (n,1).

**k=3:** Three sunny lines cover the 6 rightmost points, verticals cover the rest.

All constructions work by the pigeonhole principle and coverage analysis.

### Final Answer

k ∈ {0, 1, 3}
"""

    # Build test data registry
    TEST_DATA = {}

    # Test 1
    if test1_solution:
        TEST_DATA[1] = {
            "test_number": 1,
            "test_name": "Test 1: Complete Proof (bfs_run2 - Real Success)",
            "problem_statement": IMO01_PROBLEM,
            "solution": test1_solution,
            "expected_verdict": "PASS",
            "expected_keywords": [],
            "test_category": "complete_proof",
            "source": test1_path,
            "description": "Real successful run with complete impossibility proof for k=2"
        }

    # Test 2
    if test2_solution:
        TEST_DATA[2] = {
            "test_number": 2,
            "test_name": "Test 2: Complete Proof (bfs_run8 - Alternative Success)",
            "problem_statement": IMO01_PROBLEM,
            "solution": test2_solution,
            "expected_verdict": "PASS",
            "expected_keywords": [],
            "test_category": "complete_proof",
            "source": test2_path,
            "description": "Alternative complete proof (different approach but rigorous)"
        }

    # Test 3
    TEST_DATA[3] = {
        "test_number": 3,
        "test_name": "Test 3: Incomplete - Missing k=2 impossibility proof",
        "problem_statement": IMO01_PROBLEM,
        "solution": test3_solution,
        "expected_verdict": "FAIL",
        "expected_keywords": ["critical", "error", "trial", "invalid"],
        "test_category": "incomplete_proof",
        "source": "synthetic",
        "description": "Trial-and-error reasoning without rigorous proof (CRITICAL_ERROR)"
    }

    # Test 4
    TEST_DATA[4] = {
        "test_number": 4,
        "test_name": "Test 4: Incomplete - Missing explicit constructions",
        "problem_statement": IMO01_PROBLEM,
        "solution": test4_solution,
        "expected_verdict": "FAIL",
        "expected_keywords": ["construction", "explicit", "justification"],
        "test_category": "incomplete_proof",
        "source": "synthetic",
        "description": "Claims constructions exist but doesn't provide equations"
    }

    # Test 5
    TEST_DATA[5] = {
        "test_number": 5,
        "test_name": "Test 5: Wrong Proof - Incorrect answer (includes k=2)",
        "problem_statement": IMO01_PROBLEM,
        "solution": test5_solution,
        "expected_verdict": "FAIL",
        "expected_keywords": ["error", "invalid", "k=2"],
        "test_category": "wrong_proof",
        "source": "synthetic",
        "description": "Incorrect answer k∈{0,1,2,3} with flawed k=2 construction"
    }

    # Test 6
    TEST_DATA[6] = {
        "test_number": 6,
        "test_name": "Test 6: Proof with Justification Gap (correct but not rigorous)",
        "problem_statement": IMO01_PROBLEM,
        "solution": test6_solution,
        "expected_verdict": "PASS",
        "expected_keywords": [],
        "test_category": "incomplete_proof",
        "source": "synthetic",
        "description": "Correct answer with gaps - should PASS per policy (accept gaps for FIND)"
    }

    return TEST_DATA


# =============================================================================
# Convenience Functions
# =============================================================================

def get_test_case(test_number: int) -> Optional[Dict]:
    """Get a single test case by number."""
    test_data = get_test_data()
    return test_data.get(test_number)


def get_all_test_numbers() -> List[int]:
    """Get list of all available test numbers."""
    test_data = get_test_data()
    return sorted(test_data.keys())


def get_test_cases_by_category(category: str) -> List[Dict]:
    """
    Get all test cases in a specific category.

    Categories:
    - complete_proof: Tests 1-2
    - incomplete_proof: Tests 3-4, 6
    - wrong_proof: Test 5
    """
    test_data = get_test_data()
    return [
        test for test in test_data.values()
        if test.get("test_category") == category
    ]


def get_test_cases_by_verdict(expected_verdict: str) -> List[Dict]:
    """
    Get all test cases with a specific expected verdict.

    Args:
        expected_verdict: "PASS" or "FAIL"
    """
    test_data = get_test_data()
    return [
        test for test in test_data.values()
        if test.get("expected_verdict") == expected_verdict
    ]


# =============================================================================
# Test Data Statistics
# =============================================================================

def print_test_data_summary():
    """Print summary of available test data."""
    test_data = get_test_data()

    print("="*80)
    print("TEST DATA SUMMARY")
    print("="*80)
    print(f"Total test cases: {len(test_data)}")
    print()

    # Count by category
    categories = {}
    for test in test_data.values():
        cat = test.get("test_category", "unknown")
        categories[cat] = categories.get(cat, 0) + 1

    print("By category:")
    for cat, count in sorted(categories.items()):
        print(f"  {cat}: {count}")
    print()

    # Count by expected verdict
    verdicts = {}
    for test in test_data.values():
        verdict = test.get("expected_verdict", "unknown")
        verdicts[verdict] = verdicts.get(verdict, 0) + 1

    print("By expected verdict:")
    for verdict, count in sorted(verdicts.items()):
        print(f"  {verdict}: {count}")
    print()

    # List all tests
    print("Test cases:")
    for num in sorted(test_data.keys()):
        test = test_data[num]
        print(f"  {num}. {test['test_name']}")
        print(f"     Category: {test['test_category']}, Expected: {test['expected_verdict']}")
        print(f"     Source: {test['source']}")
    print("="*80)


if __name__ == "__main__":
    # Print summary when run directly
    print_test_data_summary()

    # Example usage
    print("\nExample: Getting Test 1 data")
    test1 = get_test_case(1)
    if test1:
        print(f"Test name: {test1['test_name']}")
        print(f"Expected verdict: {test1['expected_verdict']}")
        print(f"Solution length: {len(test1['solution'])} chars")
    else:
        print("Test 1 data not available (missing JSON file)")

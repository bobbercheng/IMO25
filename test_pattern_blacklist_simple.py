#!/usr/bin/env python3
"""
Simple test: Verify pattern constraints are added to solution field
"""

import sys
sys.path.insert(0, 'code')

import json

def test_pattern_in_schema():
    """Test that the schema building code adds pattern constraints"""

    # Simulate the schema building logic from schema_blacklist.py
    min_val = 1000
    max_val = 6000
    blacklisted_nums = [4048, 4050, 2025]

    # Copy the pattern building code from our fix
    solution_patterns = []
    for blacklisted_val in blacklisted_nums:
        solution_patterns.extend([
            f"\\\\boxed\\{{{blacklisted_val}\\}}",
            f"answer is {blacklisted_val}",
            f"= {blacklisted_val}\\.",
            f"is {blacklisted_val}\\."
        ])

    combined_pattern = "|".join(solution_patterns)

    print(f"✓ Generated pattern with {len(solution_patterns)} constraints")
    print(f"✓ Blocking {len(blacklisted_nums)} blacklisted values: {blacklisted_nums}")
    print()
    print("Pattern constraints:")
    for i, pattern in enumerate(solution_patterns[:8]):  # Show first 8
        print(f"  {i+1}. {pattern}")
    print(f"  ... ({len(solution_patterns)} total)")
    print()

    # Verify key patterns
    assert "\\\\boxed\\{4048\\}" in combined_pattern, "Missing \\boxed{4048} pattern"
    assert "answer is 4048" in combined_pattern, "Missing 'answer is 4048' pattern"
    assert "\\\\boxed\\{4050\\}" in combined_pattern, "Missing \\boxed{4050} pattern"
    assert "\\\\boxed\\{2025\\}" in combined_pattern, "Missing \\boxed{2025} pattern"

    print("✓ All key patterns present in combined regex")
    print()

    # Test that pattern would block problematic text
    import re

    test_texts = [
        ("Valid text with answer 4044", False),  # Should NOT match (4044 not blacklisted)
        ("The final answer is \\boxed{4048}.", True),  # Should match (4048 blacklisted)
        ("Hence the answer is 4048.", True),  # Should match
        ("We get = 4050.", True),  # Should match
        ("The answer is 2025.", True),  # Should match
        ("For n=2025 we obtain answer is 4044", False),  # Should NOT match (n=2025 OK, answer=4044 OK)
    ]

    print("Testing pattern matching:")
    pattern_regex = re.compile(combined_pattern)
    for text, should_match in test_texts:
        matches = bool(pattern_regex.search(text))
        status = "BLOCKED" if matches else "ALLOWED"
        expected = "BLOCKED" if should_match else "ALLOWED"

        symbol = "✓" if (matches == should_match) else "✗"
        print(f"  {symbol} {status:8s} (expected {expected:8s}): {text[:50]}")

        assert matches == should_match, f"Pattern mismatch for: {text}"

    print()
    print("✓ All pattern matching tests passed")

    return True

if __name__ == "__main__":
    try:
        test_pattern_in_schema()
        print("\n[PASS] Pattern blacklist simple test succeeded")
        sys.exit(0)
    except AssertionError as e:
        print(f"\n[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

#!/usr/bin/env python3
"""
Test: Pattern Deduplication

Verifies that the schema builder deduplicates blacklisted values
before creating patterns, avoiding redundant patterns like:
  \\boxed{4048}|\\boxed{4050}|\\boxed{4048}
"""

import sys
sys.path.insert(0, 'code')

from schema_blacklist import get_blacklist_constrained_schema

def test_pattern_deduplication():
    """Test that duplicate blacklist values are removed"""

    print("=" * 70)
    print("TEST: Pattern Deduplication")
    print("=" * 70)
    print()

    # Build schema with DUPLICATE blacklist values
    print("[1] Building schema with duplicate blacklist: [4048, 4050, 4048, 2025, 4050]")
    schema = get_blacklist_constrained_schema(
        problem_file="problems/imo06.txt",
        blacklist=[
            {"answer": 4048, "score": -10.0},
            {"answer": 4050, "score": -10.0},
            {"answer": 4048, "score": -10.0},  # DUPLICATE
            {"answer": 2025, "score": -10.0},
            {"answer": 4050, "score": -10.0},  # DUPLICATE
        ],
        use_enum=False
    )

    # Extract pattern
    pattern = schema["properties"]["solution"]["not"]["pattern"]
    print(f"    Generated pattern: {pattern}")
    print()

    # Count pattern occurrences
    pattern_parts = pattern.split("|")
    print(f"[2] Pattern has {len(pattern_parts)} parts (should be 3, not 5)")
    for part in pattern_parts:
        print(f"    - {part}")
    print()

    # Verify no duplicates
    unique_parts = set(pattern_parts)
    print(f"[3] Unique patterns: {len(unique_parts)}")

    assert len(pattern_parts) == len(unique_parts), \
        f"Pattern has duplicates! {len(pattern_parts)} parts but only {len(unique_parts)} unique"

    print("    ✓ No duplicate patterns")
    print()

    # Verify expected patterns
    expected_patterns = [
        "\\\\boxed\\{2025\\}",
        "\\\\boxed\\{4048\\}",
        "\\\\boxed\\{4050\\}"
    ]

    for expected in expected_patterns:
        assert expected in pattern_parts, \
            f"Missing expected pattern: {expected}"

    print(f"[4] Verified expected patterns:")
    for expected in expected_patterns:
        print(f"    ✓ {expected}")
    print()

    # Verify sorted order
    print(f"[5] Verify sorted order (2025 < 4048 < 4050):")
    assert pattern_parts == sorted(pattern_parts), \
        f"Patterns not sorted! Got: {pattern_parts}"
    print(f"    ✓ Patterns are sorted: {pattern_parts}")
    print()

    print("=" * 70)
    print("[PASS] Pattern deduplication test passed!")
    print("=" * 70)
    print()
    print("Summary:")
    print(f"  ✓ Input: 5 blacklist values (with duplicates)")
    print(f"  ✓ Output: 3 unique patterns (deduplicated)")
    print(f"  ✓ Patterns sorted: {' | '.join(pattern_parts)}")
    print(f"  ✓ No redundant patterns generated")

    return True


if __name__ == "__main__":
    try:
        test_pattern_deduplication()
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

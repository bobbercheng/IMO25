#!/usr/bin/env python3
"""
Test: Verify pattern constraints in schema blacklist

Tests that the schema correctly blocks blacklisted values in BOTH
the solution text field AND the final_answer JSON field.
"""

import sys
sys.path.insert(0, 'code')

from schema_blacklist import get_blacklist_constrained_schema
import json

def test_pattern_blacklist():
    """Test that solution field has pattern constraints"""

    # Build schema with blacklist
    blacklisted = [4048, 4050, 2025]
    schema_response = get_blacklist_constrained_schema(
        min_answer=1000,
        max_answer=6000,
        blacklisted_answers=blacklisted,
        use_enum=False  # Use anyOf (OPTION 2)
    )

    schema = schema_response["json_schema"]["schema"]

    # Verify solution field exists
    assert "solution" in schema["properties"], "Solution field missing"

    solution_schema = schema["properties"]["solution"]

    # Verify pattern constraint exists
    assert "not" in solution_schema, "Pattern constraint missing from solution field"
    assert "pattern" in solution_schema["not"], "Pattern field missing from 'not' constraint"

    # Extract pattern
    pattern = solution_schema["not"]["pattern"]

    # Verify pattern blocks all blacklisted values
    for blacklisted_val in blacklisted:
        assert f"\\\\boxed\\{{{blacklisted_val}\\}}" in pattern, \
            f"Pattern doesn't block \\boxed{{{blacklisted_val}}}"
        assert f"answer is {blacklisted_val}" in pattern, \
            f"Pattern doesn't block 'answer is {blacklisted_val}'"

    print("✓ Solution field has pattern constraint blocking blacklisted values")
    print(f"✓ Pattern blocks {len(blacklisted)} blacklisted values")
    print(f"✓ Pattern: {pattern[:100]}...")

    # Verify final_answer field also has anyOf constraint
    final_answer_schema = schema["properties"]["final_answer"]
    assert "anyOf" in final_answer_schema, "anyOf constraint missing from final_answer"

    print("✓ final_answer field has anyOf constraint")

    # Verify the anyOf ranges exclude blacklisted values
    anyof_ranges = final_answer_schema["anyOf"]
    print(f"✓ anyOf has {len(anyof_ranges)} range segments")

    # Check that blacklisted values are NOT in any range
    for blacklisted_val in blacklisted:
        found_in_range = False
        for range_segment in anyof_ranges:
            if "enum" in range_segment:
                if blacklisted_val in range_segment["enum"]:
                    found_in_range = True
            elif "minimum" in range_segment and "maximum" in range_segment:
                if range_segment["minimum"] <= blacklisted_val <= range_segment["maximum"]:
                    found_in_range = True

        assert not found_in_range, f"Blacklisted value {blacklisted_val} found in anyOf ranges!"

    print("✓ All blacklisted values excluded from anyOf ranges")

    # Print schema for inspection
    print("\n[SCHEMA SAMPLE]")
    print(json.dumps(schema, indent=2)[:500] + "...")

    return True

if __name__ == "__main__":
    try:
        test_pattern_blacklist()
        print("\n[PASS] Pattern blacklist test succeeded")
        sys.exit(0)
    except AssertionError as e:
        print(f"\n[FAIL] Pattern blacklist test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

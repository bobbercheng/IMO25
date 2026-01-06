#!/usr/bin/env python3
"""
Test: Single Source of Truth - Schema Blacklist Fix

Verifies that:
1. Schema excludes final_answer field when blacklist is active
2. Extraction logic extracts final_answer from \boxed{}
3. Downstream code receives final_answer in dict (backward compatible)
"""

import sys
sys.path.insert(0, 'code')

import json

def test_schema_structure():
    """Test that schema removes final_answer field for blacklist"""
    from schema_blacklist import get_blacklist_constrained_schema

    # Build schema with blacklist (should remove final_answer field)
    schema = get_blacklist_constrained_schema(
        problem_file="problems/imo06.txt",
        blacklist=[
            {"answer": 4048, "score": -10.0},
            {"answer": 4050, "score": -10.0},
            {"answer": 2025, "score": -10.0}
        ],
        use_enum=False
    )

    print("✓ Schema built successfully")
    print(f"  Properties: {list(schema['properties'].keys())}")

    # Verify final_answer field is REMOVED
    assert "final_answer" not in schema["properties"], \
        "final_answer field should be removed when blacklist is active!"

    print("✓ final_answer field REMOVED from schema (single source of truth)")

    # Verify solution field has pattern constraint
    assert "solution" in schema["properties"], "solution field missing"
    solution_schema = schema["properties"]["solution"]

    assert "not" in solution_schema, "Pattern constraint missing"
    assert "pattern" in solution_schema["not"], "Pattern field missing"

    pattern = solution_schema["not"]["pattern"]
    print(f"✓ Pattern constraint: {pattern}")

    # Verify pattern blocks blacklisted values in \boxed{}
    assert "\\\\boxed\\{4048\\}" in pattern, "Pattern doesn't block \\boxed{4048}"
    assert "\\\\boxed\\{4050\\}" in pattern, "Pattern doesn't block \\boxed{4050}"
    assert "\\\\boxed\\{2025\\}" in pattern, "Pattern doesn't block \\boxed{2025}"

    print("✓ Pattern blocks blacklisted values in \\boxed{} format only")

    # Verify required fields
    assert set(schema["required"]) == {"solution", "method"}, \
        f"Required fields should be ['solution', 'method'], got {schema['required']}"

    print("✓ Required fields: solution, method (final_answer excluded)")

    return True


def test_extraction_logic():
    """Test that parse_structured_solution extracts final_answer from \\boxed{}"""
    from agent_gpt_oss import parse_structured_solution

    # Test case 1: JSON WITHOUT final_answer (blacklist schema case)
    response_without_final_answer = json.dumps({
        "solution": "### Summary ###\n\nThe final answer is \\boxed{4044}.\n\n### Detailed Solution ###\n\nProof...",
        "method": "vertical_strips"
    })

    parsed = parse_structured_solution(response_without_final_answer)

    assert parsed is not None, "Should successfully parse response without final_answer"
    assert "final_answer" in parsed, "Should extract final_answer from \\boxed{}"
    assert parsed["final_answer"] == 4044, f"Should extract 4044, got {parsed['final_answer']}"

    print("✓ Extraction works: JSON without final_answer → extracted from \\boxed{4044}")

    # Test case 2: JSON WITH final_answer (non-blacklist schema case)
    response_with_final_answer = json.dumps({
        "solution": "### Summary ###\n\nThe final answer is \\boxed{4046}.\n\n### Detailed Solution ###\n\nProof...",
        "method": "antichain_method",
        "final_answer": 4046
    })

    parsed2 = parse_structured_solution(response_with_final_answer)

    assert parsed2 is not None, "Should successfully parse response with final_answer"
    assert parsed2["final_answer"] == 4046, f"Should use JSON final_answer, got {parsed2['final_answer']}"

    print("✓ Backward compatible: JSON with final_answer → uses JSON value")

    # Test case 3: Consistency check (both present, should use JSON value)
    response_both = json.dumps({
        "solution": "The answer is \\boxed{4046}.",
        "method": "test",
        "final_answer": 4046
    })

    parsed3 = parse_structured_solution(response_both)
    assert parsed3 is not None
    assert parsed3["final_answer"] == 4046

    print("✓ When both present, uses JSON value (backward compatible)")

    # Test case 4: No \\boxed{} in solution (should fail)
    response_no_boxed = json.dumps({
        "solution": "The answer is 4046.",
        "method": "test"
    })

    parsed4 = parse_structured_solution(response_no_boxed)
    assert parsed4 is None, "Should reject if no \\boxed{} and no final_answer"

    print("✓ Rejects solution without \\boxed{} when final_answer missing")

    return True


def test_end_to_end_flow():
    """Test complete flow: schema → API simulation → extraction → downstream"""

    print("\n[END-TO-END TEST]")

    # Simulate API response from blacklist schema (no final_answer field)
    api_response = {
        "solution": "### Summary ###\n\n**a. Verdict:** Complete solution found. The final answer is \\boxed{4044}.\n\n**b. Method:** Vertical strip tiling...",
        "method": "vertical_strips"
    }

    print(f"1. Simulated API response (no final_answer field)")
    print(f"   Keys: {list(api_response.keys())}")

    # Parse and extract
    from agent_gpt_oss import parse_structured_solution
    response_json = json.dumps(api_response)
    parsed = parse_structured_solution(response_json)

    print(f"2. After parse_structured_solution:")
    print(f"   Keys: {list(parsed.keys())}")
    print(f"   final_answer: {parsed['final_answer']}")

    # Verify downstream code sees final_answer
    assert "final_answer" in parsed, "Downstream code needs final_answer in dict"
    assert parsed["final_answer"] == 4044, "Extracted wrong value"
    assert isinstance(parsed["final_answer"], int), "Should be integer"

    print(f"3. ✓ Downstream code receives final_answer={parsed['final_answer']} (backward compatible)")

    return True


if __name__ == "__main__":
    try:
        print("=" * 60)
        print("Test 1: Schema Structure (removes final_answer field)")
        print("=" * 60)
        test_schema_structure()

        print("\n" + "=" * 60)
        print("Test 2: Extraction Logic (extracts from \\boxed{})")
        print("=" * 60)
        test_extraction_logic()

        print("\n" + "=" * 60)
        print("Test 3: End-to-End Flow")
        print("=" * 60)
        test_end_to_end_flow()

        print("\n" + "=" * 60)
        print("[PASS] All tests passed - Single Source of Truth implemented!")
        print("=" * 60)
        print("\nSummary:")
        print("  ✓ Schema removes final_answer field (prevents inconsistency)")
        print("  ✓ Extraction adds final_answer from \\boxed{} (single source)")
        print("  ✓ Downstream code works unchanged (backward compatible)")
        print("  ✓ Simple pattern: only blocks \\boxed{blacklisted_value}")

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

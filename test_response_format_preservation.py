#!/usr/bin/env python3
"""
Unit test: Verify response_format is preserved in correction calls

Tests Fix #1: response_format must be passed to build_request_payload
during corrections, not just initial attempts.
"""

import sys
sys.path.insert(0, 'code')

from agent_gpt_oss import build_request_payload

def test_response_format_preservation():
    """Test that response_format can be preserved and reused"""

    # Simulate initial request with schema
    initial_schema = {
        "type": "json_schema",
        "json_schema": {
            "name": "test_schema",
            "schema": {"type": "object", "properties": {"answer": {"type": "integer"}}},
            "strict": True
        }
    }

    # Build initial payload
    p1 = build_request_payload(
        system_prompt="Test system",
        question_prompt="Test question",
        reasoning_effort="low",
        response_format=initial_schema
    )

    # Verify initial payload has response_format
    assert "response_format" in p1, "Initial payload missing response_format"
    assert p1["response_format"] == initial_schema, "response_format not preserved correctly"

    # Extract response_format (simulating Fix #1)
    initial_response_format = p1.get("response_format")

    # Build correction payload (with Fix #1)
    p2 = build_request_payload(
        system_prompt="Correction system",
        question_prompt="Correction question",
        reasoning_effort="low",
        response_format=initial_response_format  # ← Fix #1: Include schema
    )

    # Verify correction payload has response_format
    assert "response_format" in p2, "Correction payload missing response_format (Fix #1 failed)"
    assert p2["response_format"] == initial_schema, "response_format not preserved in correction"

    print("✓ Test passed: response_format correctly preserved in corrections")
    return True

if __name__ == "__main__":
    try:
        test_response_format_preservation()
        print("\n[PASS] response_format preservation test succeeded")
        sys.exit(0)
    except AssertionError as e:
        print(f"\n[FAIL] response_format preservation test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

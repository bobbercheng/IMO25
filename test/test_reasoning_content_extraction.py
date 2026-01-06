#!/usr/bin/env python3
"""
Unit test: Verify reasoning_content extraction on truncation

Tests Fix #2: When finish_reason="length" and content="",
should extract from reasoning_content field.
"""

import sys
sys.path.insert(0, 'code')

from agent_gpt_oss import extract_text_from_response

def test_reasoning_content_extraction():
    """Test that reasoning_content is extracted when content is empty"""

    # Simulate truncated response (finish_reason: "length")
    truncated_response = {
        "choices": [{
            "message": {
                "content": "",  # Empty due to truncation
                "reasoning_content": "This is the actual response content from reasoning_content field",
                "role": "assistant"
            },
            "finish_reason": "length"  # Indicates truncation
        }]
    }

    # Extract text (should use Fix #2 to get reasoning_content)
    result = extract_text_from_response(truncated_response)

    # Verify result is from reasoning_content, not empty string
    assert result != "", "Failed to extract reasoning_content (got empty string)"
    assert "actual response content" in result, "Content not from reasoning_content field"
    assert len(result) > 0, "Extracted content is empty"

    print("✓ Test passed: reasoning_content extracted on truncation")

    # Test normal response (no truncation)
    normal_response = {
        "choices": [{
            "message": {
                "content": "Normal response content",
                "role": "assistant"
            },
            "finish_reason": "stop"
        }]
    }

    result2 = extract_text_from_response(normal_response)
    assert result2 == "Normal response content", "Normal response not handled correctly"

    print("✓ Test passed: Normal responses still work correctly")
    return True

if __name__ == "__main__":
    try:
        test_reasoning_content_extraction()
        print("\n[PASS] reasoning_content extraction test succeeded")
        sys.exit(0)
    except AssertionError as e:
        print(f"\n[FAIL] reasoning_content extraction test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

#!/usr/bin/env python3
"""Test script to verify clean_reasoning_tags function works correctly."""

import sys
import re

# Import the clean_reasoning_tags function
sys.path.insert(0, '/home/user/IMO25/code')
from agent_gpt_oss import clean_reasoning_tags

# Test cases
test_cases = [
    {
        "name": "Response with reasoning tags and 'no' verdict",
        "input": '<|channel|>analysis<|message|>We need to produce a final answer...<|end|><|start|>assistant<|channel|>final<|message|>**Final Verdict:** no',
        "expected_contains": "no",
        "should_not_contain": "<|channel|>"
    },
    {
        "name": "Response with reasoning tags and 'yes' verdict",
        "input": '<|channel|>analysis<|message|>The solution is correct...<|end|><|start|>assistant<|channel|>final<|message|>yes',
        "expected_contains": "yes",
        "should_not_contain": "<|channel|>"
    },
    {
        "name": "Simple response without tags",
        "input": "yes",
        "expected_contains": "yes",
        "should_not_contain": "<|channel|>"
    },
    {
        "name": "Response with multiple channels",
        "input": '<|channel|>thinking<|message|>Let me think...<|end|><|channel|>final<|message|>The answer is no',
        "expected_contains": "no",
        "should_not_contain": "<|channel|>"
    }
]

print("Testing clean_reasoning_tags function...")
print("=" * 80)

all_passed = True
for i, test in enumerate(test_cases, 1):
    print(f"\nTest {i}: {test['name']}")
    print(f"Input: {test['input'][:100]}...")

    result = clean_reasoning_tags(test['input'])
    print(f"Result: {result}")

    # Check if expected content is present
    if test['expected_contains'] in result.lower():
        print(f"✓ Contains expected '{test['expected_contains']}'")
    else:
        print(f"✗ FAILED: Does not contain expected '{test['expected_contains']}'")
        all_passed = False

    # Check if tags are removed
    if test['should_not_contain'] not in result:
        print(f"✓ Successfully removed '{test['should_not_contain']}'")
    else:
        print(f"✗ FAILED: Still contains '{test['should_not_contain']}'")
        all_passed = False

print("\n" + "=" * 80)
if all_passed:
    print("✓ All tests passed!")
else:
    print("✗ Some tests failed!")
    sys.exit(1)

#!/usr/bin/env python3
"""
Test script to verify OpenRouter API spec support.

Tests that reasoning parameters are placed correctly:
- Standard API: reasoning at top level
- OpenRouter API: reasoning in extra_body
"""

import sys
import os

# Set up path to import agent_gpt_oss
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'code'))

print("="*80)
print("OpenRouter Support Test")
print("="*80)

# Test 1: Standard model (no prefix or openai/ prefix)
print("\n[Test 1] Standard model: openai/gpt-oss-120b")
os.environ['GPT_OSS_MODEL_NAME'] = 'openai/gpt-oss-120b'

# Need to reload the module to pick up new env var
if 'agent_gpt_oss' in sys.modules:
    del sys.modules['agent_gpt_oss']

from agent_gpt_oss import build_request_payload

payload1 = build_request_payload(
    system_prompt="Test system prompt",
    question_prompt="Test question",
    reasoning_effort="high"
)

print(f"  Model: {payload1['model']}")
print(f"  Has 'reasoning' at top level: {'reasoning' in payload1}")
print(f"  Has 'extra_body': {'extra_body' in payload1}")

assert payload1['model'] == 'openai/gpt-oss-120b', "Model name incorrect"
assert 'reasoning' in payload1, "Should have reasoning at top level"
assert payload1['reasoning']['effort'] == 'high', "Reasoning effort incorrect"
assert 'extra_body' not in payload1, "Should NOT have extra_body for standard API"
print("  ✅ PASSED: Reasoning at top level (standard API)")

# Test 2: OpenRouter model (with prefix)
print("\n[Test 2] OpenRouter model: openrouter/openai/gpt-oss-120b")

# Reload module with new model name
os.environ['GPT_OSS_MODEL_NAME'] = 'openrouter/openai/gpt-oss-120b'
del sys.modules['agent_gpt_oss']

from agent_gpt_oss import build_request_payload

payload2 = build_request_payload(
    system_prompt="Test system prompt",
    question_prompt="Test question",
    reasoning_effort="medium"
)

print(f"  Model: {payload2['model']}")
print(f"  Has 'reasoning' at top level: {'reasoning' in payload2}")
print(f"  Has 'extra_body': {'extra_body' in payload2}")
if 'extra_body' in payload2:
    print(f"  extra_body['reasoning']: {payload2['extra_body'].get('reasoning')}")

assert payload2['model'] == 'openrouter/openai/gpt-oss-120b', "Model name incorrect"
assert 'extra_body' in payload2, "Should have extra_body for OpenRouter"
assert 'reasoning' in payload2['extra_body'], "Should have reasoning in extra_body"
assert payload2['extra_body']['reasoning']['effort'] == 'medium', "Reasoning effort incorrect"
assert 'reasoning' not in payload2, "Should NOT have reasoning at top level for OpenRouter"
print("  ✅ PASSED: Reasoning in extra_body (OpenRouter API)")

# Test 3: Another provider prefix (e.g., anthropic/claude-3)
print("\n[Test 3] Other provider: anthropic/claude-3-opus")

os.environ['GPT_OSS_MODEL_NAME'] = 'anthropic/claude-3-opus'
del sys.modules['agent_gpt_oss']

from agent_gpt_oss import build_request_payload

payload3 = build_request_payload(
    system_prompt="Test system prompt",
    question_prompt="Test question",
    reasoning_effort="low"
)

print(f"  Model: {payload3['model']}")
print(f"  Has 'reasoning' at top level: {'reasoning' in payload3}")
print(f"  Has 'extra_body': {'extra_body' in payload3}")

assert payload3['model'] == 'anthropic/claude-3-opus', "Model name incorrect"
assert 'extra_body' in payload3, "Should have extra_body for provider prefix"
assert 'reasoning' in payload3['extra_body'], "Should have reasoning in extra_body"
assert payload3['extra_body']['reasoning']['effort'] == 'low', "Reasoning effort incorrect"
print("  ✅ PASSED: Reasoning in extra_body (provider prefix)")

# Test 4: No prefix model (local deployment)
print("\n[Test 4] Local model: gpt-oss-120b (no prefix)")

os.environ['GPT_OSS_MODEL_NAME'] = 'gpt-oss-120b'
del sys.modules['agent_gpt_oss']

from agent_gpt_oss import build_request_payload

payload4 = build_request_payload(
    system_prompt="Test system prompt",
    question_prompt="Test question",
    reasoning_effort="high"
)

print(f"  Model: {payload4['model']}")
print(f"  Has 'reasoning' at top level: {'reasoning' in payload4}")
print(f"  Has 'extra_body': {'extra_body' in payload4}")

assert payload4['model'] == 'gpt-oss-120b', "Model name incorrect"
assert 'reasoning' in payload4, "Should have reasoning at top level"
assert payload4['reasoning']['effort'] == 'high', "Reasoning effort incorrect"
assert 'extra_body' not in payload4, "Should NOT have extra_body for local model"
print("  ✅ PASSED: Reasoning at top level (local model)")

print("\n" + "="*80)
print("✅ ALL TESTS PASSED")
print("="*80)
print("\nConclusion:")
print("  - Standard API (openai/*, no prefix): reasoning at top level ✅")
print("  - OpenRouter API (openrouter/*): reasoning in extra_body ✅")
print("  - Other providers (anthropic/*, etc): reasoning in extra_body ✅")
print("  - Local models (no prefix): reasoning at top level ✅")
print("\nOpenRouter support is working correctly!")
print("="*80)

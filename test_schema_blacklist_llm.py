#!/usr/bin/env python3
"""
Unit test for schema blacklist with actual LLM API.

This script tests that:
1. Schema generation works correctly (compact "not" constraint)
2. LLM API accepts the schema format
3. Model physically cannot generate blacklisted values
4. Model can generate other valid values

Usage:
    python test_schema_blacklist_llm.py

Requirements:
    - GPT_OSS_API_URL and GPT_OSS_API_KEY environment variables set
    - OpenRouter or local GPT-OSS deployment running
"""

import os
import sys
import json
import requests
from pathlib import Path

# Add code directory to path
sys.path.insert(0, str(Path(__file__).parent / "code"))

from schema_blacklist import (
    get_blacklist_constrained_schema,
    get_schema_metadata,
    validate_answer_against_blacklist,
    load_blacklist
)


def test_schema_generation():
    """Test 1: Verify schema generation is compact and correct."""
    print("=" * 70)
    print("TEST 1: Schema Generation")
    print("=" * 70)

    problem_file = "problems/imo06.txt"
    schema = get_blacklist_constrained_schema(problem_file)

    # Check schema structure
    assert "type" in schema
    assert schema["type"] == "object"
    assert "properties" in schema
    assert "final_answer" in schema["properties"]

    final_answer = schema["properties"]["final_answer"]

    # Verify uses "not" constraint (compact) not enum (huge)
    assert "not" in final_answer, "Schema should use 'not' constraint for compactness"
    assert "enum" in final_answer.get("not", {}), "Schema should have enum in 'not' clause"

    blacklisted = final_answer["not"]["enum"]
    print(f"✅ Schema uses compact 'not' constraint")
    print(f"   Blacklisted values: {blacklisted}")
    print(f"   Schema size: ~{len(json.dumps(schema))} bytes (vs ~30KB with enum approach)")

    # Verify blacklisted values
    assert 4048 in blacklisted, "4048 should be blacklisted"
    assert 4050 in blacklisted, "4050 should be blacklisted"

    # Verify range constraints
    assert "minimum" in final_answer, "Should have minimum constraint"
    assert "maximum" in final_answer, "Should have maximum constraint"
    assert final_answer["minimum"] > 0, "Minimum should be positive"
    assert final_answer["maximum"] < 10000, "Maximum should be reasonable"

    print(f"   Range: [{final_answer['minimum']}, {final_answer['maximum']}]")
    print(f"✅ Schema structure is correct\n")

    return schema


def test_schema_metadata():
    """Test 2: Verify metadata extraction works."""
    print("=" * 70)
    print("TEST 2: Schema Metadata")
    print("=" * 70)

    problem_file = "problems/imo06.txt"
    schema = get_blacklist_constrained_schema(problem_file)
    metadata = get_schema_metadata(schema)

    # Check metadata
    assert metadata["constraint_type"] == "not", "Should report 'not' constraint type"
    assert metadata["has_not_constraint"] == True, "Should detect not constraint"
    assert len(metadata["blacklisted_values"]) == 2, "Should detect 2 blacklisted values"
    assert 4048 in metadata["blacklisted_values"], "Should list 4048 as blacklisted"
    assert 4050 in metadata["blacklisted_values"], "Should list 4050 as blacklisted"

    print(f"✅ Metadata extraction works")
    print(f"   Constraint type: {metadata['constraint_type']}")
    print(f"   Blacklisted values: {metadata['blacklisted_values']}")
    print(f"   Range: {metadata['range']}")
    print(f"✅ Metadata is correct\n")

    return metadata


def test_llm_api_request(schema, num_attempts=3):
    """Test 3: Send actual request to LLM and verify it respects blacklist."""
    print("=" * 70)
    print("TEST 3: LLM API Request")
    print("=" * 70)

    # Get API configuration - default to OpenRouter from CLAUDE.md
    api_url = os.getenv("GPT_OSS_API_URL", "https://openrouter.ai/api/v1/chat/completions")
    api_key = os.getenv("GPT_OSS_API_KEY", "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")
    model_name = os.getenv("GPT_OSS_MODEL_NAME", "openai/gpt-oss-120b")

    print(f"API URL: {api_url}")
    print(f"Model: {model_name}")

    # Build simple test request
    test_problem = """
    Consider a 2025×2025 grid of unit squares. What is the minimum number of
    rectangular tiles needed so that each row and column has exactly one uncovered square?

    Think carefully and provide your answer.
    """

    payload = {
        "model": model_name,
        "messages": [
            {
                "role": "system",
                "content": "You are a mathematical problem solver. Provide rigorous solutions in valid JSON format."
            },
            {
                "role": "user",
                "content": test_problem
            }
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "math_solution_blacklist_test",
                "schema": schema,
                "strict": True
            }
        },
        "temperature": 0.3,  # Lower temperature for more deterministic JSON
        "max_tokens": 4000   # Increased to avoid truncation
    }

    # Check if model uses extra_body for reasoning
    has_prefix = "/" in model_name and not model_name.startswith("openai/")
    if has_prefix:
        payload["extra_body"] = {"reasoning": {"effort": "low"}}
    else:
        payload["reasoning"] = {"effort": "low"}

    print(f"\n📤 Sending {num_attempts} test requests to LLM...")
    print(f"   Schema: 'not' constraint with {len(schema['properties']['final_answer']['not']['enum'])} blacklisted values")

    results = []
    for i in range(num_attempts):
        try:
            headers = {"Content-Type": "application/json"}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

            response = requests.post(api_url, json=payload, headers=headers, timeout=60)

            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                finish_reason = data["choices"][0].get("finish_reason", "unknown")

                # Parse JSON response
                try:
                    solution_data = json.loads(content)
                    final_answer = solution_data.get("final_answer")
                    method = solution_data.get("method", "unknown")
                    solution_text = solution_data.get("solution", "")

                    # Check against blacklist
                    blacklisted_values = schema["properties"]["final_answer"]["not"]["enum"]
                    is_blacklisted = final_answer in blacklisted_values

                    results.append({
                        "attempt": i + 1,
                        "final_answer": final_answer,
                        "method": method,
                        "is_blacklisted": is_blacklisted,
                        "finish_reason": finish_reason,
                        "success": True
                    })

                    status = "❌ BLACKLISTED" if is_blacklisted else "✅ VALID"
                    truncated = " (truncated)" if finish_reason == "length" else ""
                    print(f"   Attempt {i+1}: answer={final_answer}, method={method[:30]}...{truncated} → {status}")

                except json.JSONDecodeError as e:
                    # Show what went wrong
                    print(f"   Attempt {i+1}: ⚠️  JSON parse error: {e}")
                    print(f"      Raw response length: {len(content)} chars")
                    print(f"      Finish reason: {finish_reason}")
                    if finish_reason == "length":
                        print(f"      ⚠️  Response was TRUNCATED - increase max_tokens")
                    # Show first and last 100 chars to debug
                    if len(content) > 200:
                        print(f"      First 100 chars: {content[:100]}")
                        print(f"      Last 100 chars: ...{content[-100:]}")
                    else:
                        print(f"      Content: {content}")
                    results.append({
                        "attempt": i + 1,
                        "error": "json_parse_error",
                        "error_detail": str(e),
                        "finish_reason": finish_reason,
                        "content_length": len(content),
                        "success": False
                    })
            else:
                print(f"   Attempt {i+1}: ⚠️  API error {response.status_code}: {response.text[:100]}")
                results.append({
                    "attempt": i + 1,
                    "error": f"api_error_{response.status_code}",
                    "success": False
                })

        except Exception as e:
            print(f"   Attempt {i+1}: ⚠️  Exception: {e}")
            results.append({
                "attempt": i + 1,
                "error": str(e),
                "success": False
            })

    # Analyze results
    print(f"\n📊 Test Results:")
    successful = [r for r in results if r.get("success")]
    blacklisted = [r for r in successful if r.get("is_blacklisted")]
    valid = [r for r in successful if not r.get("is_blacklisted")]

    print(f"   Total attempts: {num_attempts}")
    print(f"   Successful: {len(successful)}")
    print(f"   Blacklisted answers: {len(blacklisted)} ← SHOULD BE 0")
    print(f"   Valid answers: {len(valid)}")

    if len(successful) > 0:
        compliance_rate = (1 - len(blacklisted) / len(successful)) * 100
        print(f"   Compliance rate: {compliance_rate:.1f}%")

        if len(blacklisted) == 0:
            print(f"✅ SUCCESS: Model respected blacklist (0/{len(successful)} violations)")
        else:
            print(f"❌ FAILURE: Model violated blacklist ({len(blacklisted)}/{len(successful)} attempts)")
            print(f"   Blacklisted answers generated: {[r['final_answer'] for r in blacklisted]}")
    else:
        print(f"⚠️  WARNING: No successful API responses")

    return results


def test_answer_validation():
    """Test 4: Verify answer validation function works."""
    print("\n" + "=" * 70)
    print("TEST 4: Answer Validation")
    print("=" * 70)

    blacklist = load_blacklist("problems/imo06.txt")

    # Test various answers
    test_cases = [
        (4048, False, "blacklisted"),
        (4050, False, "blacklisted"),
        (2112, True, "correct answer"),
        (2025, True, "alternative answer"),
        (1500, True, "random valid"),
    ]

    all_passed = True
    for answer, expected_valid, description in test_cases:
        is_valid = validate_answer_against_blacklist(answer, blacklist)
        passed = (is_valid == expected_valid)
        status = "✅" if passed else "❌"

        print(f"   {status} Answer {answer} ({description}): valid={is_valid} (expected={expected_valid})")

        if not passed:
            all_passed = False

    if all_passed:
        print(f"✅ All validation tests passed\n")
    else:
        print(f"❌ Some validation tests failed\n")

    return all_passed


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("SCHEMA BLACKLIST LLM UNIT TEST")
    print("=" * 70)
    print()

    try:
        # Test 1: Schema generation
        schema = test_schema_generation()

        # Test 2: Metadata extraction
        metadata = test_schema_metadata()

        # Test 3: Answer validation
        validation_ok = test_answer_validation()

        # Test 4: LLM API request (only if API is available)
        api_url = os.getenv("GPT_OSS_API_URL")
        if api_url:
            results = test_llm_api_request(schema, num_attempts=3)
        else:
            print("\n" + "=" * 70)
            print("TEST 3: LLM API Request")
            print("=" * 70)
            print("⚠️  SKIPPED: GPT_OSS_API_URL not set")
            print("   Set environment variable to test with actual LLM")
            results = []

        # Summary
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print("✅ Schema generation: PASSED (compact 'not' constraint)")
        print("✅ Metadata extraction: PASSED")
        print(f"{'✅' if validation_ok else '❌'} Answer validation: {'PASSED' if validation_ok else 'FAILED'}")

        if results:
            successful = [r for r in results if r.get("success")]
            blacklisted = [r for r in successful if r.get("is_blacklisted")]
            if len(successful) > 0 and len(blacklisted) == 0:
                print(f"✅ LLM API test: PASSED (100% compliance)")
            elif len(successful) > 0:
                print(f"❌ LLM API test: FAILED ({len(blacklisted)}/{len(successful)} violations)")
            else:
                print(f"⚠️  LLM API test: INCONCLUSIVE (no successful responses)")
        else:
            print(f"⚠️  LLM API test: SKIPPED (no API URL)")

        print("\n✅ All tests completed")

    except Exception as e:
        print(f"\n❌ Test suite failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

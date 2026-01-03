#!/usr/bin/env python3
"""
Test OpenRouter's JSON Schema support with different constraint types.

This diagnostic script tests whether OpenRouter properly enforces:
1. "enum" constraints (positive list)
2. "not" constraints (negative list)
3. "minimum"/"maximum" range constraints
"""

import os
import json
import requests


def test_constraint_type(constraint_name, schema, num_tests=5):
    """Test a specific constraint type with OpenRouter."""
    print(f"\n{'='*70}")
    print(f"Testing: {constraint_name}")
    print(f"{'='*70}")

    api_url = os.getenv("GPT_OSS_API_URL", "https://openrouter.ai/api/v1/chat/completions")
    api_key = os.getenv("GPT_OSS_API_KEY", "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")
    model_name = os.getenv("GPT_OSS_MODEL_NAME", "openai/gpt-oss-120b")

    print(f"API: {api_url}")
    print(f"Model: {model_name}")
    print(f"\nSchema constraint:")
    print(json.dumps(schema["properties"]["answer"], indent=2))

    payload = {
        "model": model_name,
        "messages": [
            {
                "role": "user",
                "content": "What is 4000 + 48? Respond with your answer."
            }
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "answer_test",
                "schema": schema,
                "strict": True
            }
        },
        "temperature": 0.3,
        "max_tokens": 500
    }

    # Add reasoning parameter (standard OpenAI format for "openai/" prefix)
    payload["reasoning"] = {"effort": "low"}

    violations = []
    valid_responses = []

    print(f"\n🧪 Running {num_tests} tests...")
    for i in range(num_tests):
        try:
            headers = {"Content-Type": "application/json"}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

            response = requests.post(api_url, json=payload, headers=headers, timeout=30)

            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"]

                try:
                    result = json.loads(content)
                    answer = result.get("answer")

                    # Check if answer violates constraint
                    is_violation = False
                    if answer in [4048, 4050]:  # The values we're trying to forbid
                        is_violation = True
                        violations.append(answer)
                        print(f"   Test {i+1}: answer={answer} ❌ VIOLATION")
                    else:
                        valid_responses.append(answer)
                        print(f"   Test {i+1}: answer={answer} ✅ VALID")

                except json.JSONDecodeError as e:
                    print(f"   Test {i+1}: JSON parse error: {e}")
            else:
                print(f"   Test {i+1}: HTTP {response.status_code}")
                print(f"   Error: {response.text[:200]}")

        except Exception as e:
            print(f"   Test {i+1}: Exception: {e}")

    # Summary
    violation_rate = len(violations) / num_tests * 100
    print(f"\n📊 Results:")
    print(f"   Violations: {len(violations)}/{num_tests} ({violation_rate:.1f}%)")
    if violations:
        print(f"   Violation values: {violations}")
    print(f"   Valid responses: {valid_responses}")

    if violation_rate == 0:
        print(f"   ✅ PASS: Constraint is enforced")
    elif violation_rate < 20:
        print(f"   ⚠️  PARTIAL: Constraint is mostly enforced")
    else:
        print(f"   ❌ FAIL: Constraint is NOT enforced")

    return violation_rate


def main():
    print("="*70)
    print("OpenRouter JSON Schema Constraint Support Test")
    print("="*70)
    print("\nThis test checks which JSON Schema constraints work on OpenRouter.")
    print("We're testing if the model can avoid generating 4048 (answer to 4000+48).")

    # Test 1: "not" constraint (what we're currently using)
    schema_not = {
        "type": "object",
        "properties": {
            "answer": {
                "type": "integer",
                "minimum": 1000,
                "maximum": 5000,
                "not": {
                    "enum": [4048, 4050]
                },
                "description": "Answer to the math problem. FORBIDDEN: 4048, 4050"
            }
        },
        "required": ["answer"]
    }

    # Test 2: "enum" constraint (positive list - only allow a few values)
    schema_enum = {
        "type": "object",
        "properties": {
            "answer": {
                "type": "integer",
                "enum": [4047, 4049, 4051, 4052],  # Everything EXCEPT 4048, 4050
                "description": "Answer to the math problem. Only these specific values allowed."
            }
        },
        "required": ["answer"]
    }

    # Test 3: Range only (no blacklist)
    schema_range = {
        "type": "object",
        "properties": {
            "answer": {
                "type": "integer",
                "minimum": 1000,
                "maximum": 5000,
                "description": "Answer to the math problem."
            }
        },
        "required": ["answer"]
    }

    # Run tests
    results = {}

    results["not"] = test_constraint_type('"not" constraint (negative list)', schema_not, num_tests=5)
    results["enum"] = test_constraint_type('"enum" constraint (positive list)', schema_enum, num_tests=5)
    results["range"] = test_constraint_type('Range only (baseline)', schema_range, num_tests=3)

    # Final summary
    print("\n" + "="*70)
    print("FINAL SUMMARY")
    print("="*70)
    print(f"  'not' constraint:  {results['not']:.1f}% violation rate")
    print(f"  'enum' constraint: {results['enum']:.1f}% violation rate")
    print(f"  Range only:        {results['range']:.1f}% violation rate (baseline)")

    print("\nConclusions:")
    if results["not"] > 20:
        print("  ❌ OpenRouter does NOT properly enforce 'not' constraints")
        if results["enum"] < 20:
            print("  ✅ OpenRouter DOES enforce 'enum' constraints")
            print("  💡 RECOMMENDATION: Use 'enum' instead of 'not' for blacklisting")
        else:
            print("  ❌ OpenRouter also has issues with 'enum' constraints")
            print("  💡 RECOMMENDATION: Try local deployment or different provider")
    else:
        print("  ✅ OpenRouter properly enforces 'not' constraints")
        print("  🤔 The test failures might be due to other issues (temperature, etc.)")


if __name__ == "__main__":
    main()

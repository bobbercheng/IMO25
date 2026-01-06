#!/usr/bin/env python3
"""
Test whether OpenRouter enforces integer type in anyOf schemas.

This test checks if the model can bypass integer constraints by returning strings.
"""

import os
import json
import requests


def test_integer_enforcement():
    """Test that schema rejects string values for integer fields."""
    api_url = os.getenv("GPT_OSS_API_URL", "https://openrouter.ai/api/v1/chat/completions")
    api_key = os.getenv("GPT_OSS_API_KEY", "sk-or-...")

    # Schema WITH top-level type: integer
    schema_with_type = {
        "type": "object",
        "properties": {
            "answer": {
                "type": "integer",
                "anyOf": [
                    {"type": "integer", "minimum": 1, "maximum": 4047},
                    {"type": "integer", "enum": [4049]},
                    {"type": "integer", "minimum": 4051, "maximum": 5000}
                ],
                "description": "Integer answer (4048 and 4050 are forbidden)"
            }
        },
        "required": ["answer"]
    }

    # Schema WITHOUT top-level type (old version)
    schema_without_type = {
        "type": "object",
        "properties": {
            "answer": {
                "anyOf": [
                    {"type": "integer", "minimum": 1, "maximum": 4047},
                    {"type": "integer", "enum": [4049]},
                    {"type": "integer", "minimum": 4051, "maximum": 5000}
                ],
                "description": "Integer answer (4048 and 4050 are forbidden)"
            }
        },
        "required": ["answer"]
    }

    test_cases = [
        ("WITH top-level type", schema_with_type),
        ("WITHOUT top-level type", schema_without_type)
    ]

    for case_name, schema in test_cases:
        print(f"\n{'='*70}")
        print(f"Testing: {case_name}")
        print(f"{'='*70}")

        payload = {
            "model": "openai/gpt-oss-120b",
            "messages": [
                {
                    "role": "user",
                    "content": "What is 4000 + 48? Answer with the number only."
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
            "reasoning": {"effort": "low"},
            "temperature": 0.3,
            "max_tokens": 200
        }

        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }

            response = requests.post(api_url, json=payload, headers=headers, timeout=30)

            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                result = json.loads(content)
                answer = result.get("answer")

                print(f"✅ Response received")
                print(f"   Answer: {answer}")
                print(f"   Type: {type(answer).__name__}")

                if isinstance(answer, str):
                    print(f"   ⚠️  WARNING: Answer is a STRING (should be integer)")
                    if answer == "4048":
                        print(f"   ❌ CRITICAL: Model returned blacklisted value as string!")
                elif isinstance(answer, int):
                    print(f"   ✅ Answer is an INTEGER (correct)")
                    if answer == 4048:
                        print(f"   ❌ CRITICAL: Blacklisted value 4048 was generated!")
                    else:
                        print(f"   ✅ Answer is not blacklisted")

            else:
                print(f"❌ HTTP {response.status_code}")
                print(f"   Error: {response.text[:200]}")

        except Exception as e:
            print(f"❌ Exception: {e}")

    print(f"\n{'='*70}")
    print("CONCLUSION")
    print(f"{'='*70}")
    print("If 'WITH top-level type' enforces integer but 'WITHOUT' allows strings,")
    print("then the top-level 'type' field is critical for preventing string bypass.")


if __name__ == "__main__":
    test_integer_enforcement()

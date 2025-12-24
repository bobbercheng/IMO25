#!/usr/bin/env python3
"""
POC: Test OpenRouter GPT-OSS-120b Native Structured Outputs

This script validates that GPT-OSS-120b on OpenRouter supports
native JSON schema enforcement via response_format parameter.
"""

import json
import os
import re
import requests
import sys

# OpenRouter API Configuration
API_URL = "https://openrouter.ai/api/v1/chat/completions"
API_KEY = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("GPT_OSS_API_KEY")
MODEL = "openai/gpt-oss-120b"

if not API_KEY:
    print("ERROR: No API key found!")
    print("Please set one of these environment variables:")
    print("  export OPENROUTER_API_KEY=your_key_here")
    print("  export GPT_OSS_API_KEY=your_key_here")
    sys.exit(1)


def extract_json_from_harmony_format(content: str) -> str:
    """
    Extract JSON from GPT-OSS Harmony format responses.

    GPT-OSS sometimes outputs reasoning text before JSON. This function
    extracts the JSON portion by finding the first '{' and matching '}'.

    Handles cases like:
    - "prefix text.{\"key\":\"value\"}"  (simple prefix)
    - ".###{\n{\n\"key\":\"value\"\n}"   (nested braces / double brace)
    - "text{...}more text"               (extract first complete JSON)

    Args:
        content: Raw content from API response

    Returns:
        Extracted JSON string
    """
    # Find first '{' (start of JSON)
    first_brace = content.find('{')

    if first_brace == -1:
        raise ValueError("No JSON object found in content")

    # Extract from first '{' onward
    json_portion = content[first_brace:]

    # Check if second character is also '{' (double brace case)
    # In GPT-OSS sometimes outputs "{\n{" - skip first one
    if len(json_portion) > 1 and json_portion[1] in ['\n', '\r', ' ', '\t']:
        # Check if next non-whitespace is another '{'
        for i in range(1, min(10, len(json_portion))):
            if json_portion[i] == '{':
                # Found double brace, skip first one
                json_portion = json_portion[i:]
                break
            elif json_portion[i] not in ['\n', '\r', ' ', '\t']:
                # Found non-whitespace that's not '{', use original
                break

    # Try to parse incrementally to find matching '}'
    brace_count = 0
    in_string = False
    escape_next = False

    for i, char in enumerate(json_portion):
        if escape_next:
            escape_next = False
            continue

        if char == '\\':
            escape_next = True
            continue

        if char == '"' and not escape_next:
            in_string = not in_string
            continue

        if not in_string:
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    # Found matching closing brace
                    return json_portion[:i+1]

    # If no matching brace found, return from first '{' to end
    return json_portion

def test_basic_structured_output():
    """Test 1: Basic structured output with simple schema"""

    print("="*80)
    print("TEST 1: Basic Structured Output (Simple Schema)")
    print("="*80)

    schema = {
        "type": "json_schema",
        "json_schema": {
            "name": "simple_response",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "greeting": {"type": "string", "description": "A friendly greeting"},
                    "sentiment": {"type": "string", "enum": ["positive", "neutral", "negative"]},
                    "word_count": {"type": "integer", "description": "Number of words in the greeting"}
                },
                "required": ["greeting", "sentiment", "word_count"],
                "additionalProperties": False
            }
        }
    }

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "user", "content": "Say hello and tell me your sentiment!"}
        ],
        "response_format": schema
    }

    try:
        response = requests.post(
            API_URL,
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=60
        )

        response.raise_for_status()
        result = response.json()

        # Extract content
        content = result['choices'][0]['message']['content']

        print(f"\n✅ Response received:")
        print(f"Raw content: {content}")

        # Extract JSON (handle Harmony format prefix)
        if content.strip()[0] != '{':
            print(f"\n⚠️  Detected non-JSON prefix in response (Harmony format)")
            json_content = extract_json_from_harmony_format(content)
            print(f"Extracted JSON: {json_content}")
        else:
            json_content = content

        # Parse JSON
        parsed = json.loads(json_content)
        print(f"\n✅ Valid JSON parsed:")
        print(json.dumps(parsed, indent=2))

        # Validate schema compliance
        assert "greeting" in parsed, "Missing 'greeting' field"
        assert "sentiment" in parsed, "Missing 'sentiment' field"
        assert "word_count" in parsed, "Missing 'word_count' field"
        assert parsed["sentiment"] in ["positive", "neutral", "negative"], f"Invalid sentiment: {parsed['sentiment']}"
        assert isinstance(parsed["word_count"], int), f"word_count should be integer, got {type(parsed['word_count'])}"

        print(f"\n✅ Schema validation PASSED")
        print(f"   - Greeting: {parsed['greeting']}")
        print(f"   - Sentiment: {parsed['sentiment']}")
        print(f"   - Word Count: {parsed['word_count']}")

        return True

    except requests.exceptions.RequestException as e:
        print(f"\n❌ HTTP Error: {e}")
        if hasattr(e.response, 'text'):
            print(f"Response: {e.response.text}")
        return False
    except json.JSONDecodeError as e:
        print(f"\n❌ JSON Parsing Error: {e}")
        print(f"Content received: {content}")
        return False
    except AssertionError as e:
        print(f"\n❌ Schema Validation Error: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_verification_verdict_schema():
    """Test 2: Verification verdict schema (IMO use case)"""

    print("\n" + "="*80)
    print("TEST 2: Verification Verdict Schema (IMO Use Case)")
    print("="*80)

    schema = {
        "type": "json_schema",
        "json_schema": {
            "name": "verification_verdict",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "verdict": {
                        "type": "string",
                        "enum": ["PASS", "FAIL"],
                        "description": "Overall verification verdict"
                    },
                    "confidence": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                        "description": "Confidence in the verdict (0.0 to 1.0)"
                    },
                    "issues": {
                        "type": "array",
                        "description": "List of issues found in the solution",
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {
                                    "type": "string",
                                    "enum": ["CRITICAL_ERROR", "JUSTIFICATION_GAP"],
                                    "description": "Type of issue"
                                },
                                "location": {
                                    "type": "string",
                                    "description": "Quote from solution where issue occurs"
                                },
                                "description": {
                                    "type": "string",
                                    "description": "Explanation of the issue"
                                },
                                "severity": {
                                    "type": "integer",
                                    "minimum": 1,
                                    "maximum": 10,
                                    "description": "Severity rating (1=minor, 10=critical)"
                                }
                            },
                            "required": ["type", "location", "description", "severity"],
                            "additionalProperties": False
                        }
                    },
                    "answer_correctness": {
                        "type": "string",
                        "enum": ["CORRECT", "INCORRECT", "INCOMPLETE", "UNKNOWN"],
                        "description": "Correctness of the final answer"
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Brief explanation of the verdict"
                    }
                },
                "required": ["verdict", "confidence", "issues", "answer_correctness", "reasoning"],
                "additionalProperties": False
            }
        }
    }

    problem = """
Problem: Prove that for all positive integers n, the sum 1 + 2 + 3 + ... + n = n(n+1)/2.

Solution:
We use induction. Base case: n=1, sum is 1 = 1(1+1)/2 = 1. ✓
Inductive step: Assume true for n=k. For n=k+1:
Sum = 1 + 2 + ... + k + (k+1) = k(k+1)/2 + (k+1) = (k+1)(k+2)/2. ✓
Therefore, the formula holds for all n ≥ 1.
"""

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": f"""You are a mathematical proof verifier. Verify the following proof and return your verdict in JSON format.

{problem}

Analyze the proof step by step and identify any issues. Return your verdict as JSON."""
            }
        ],
        "response_format": schema
    }

    try:
        print("\n⏳ Sending verification request...")
        response = requests.post(
            API_URL,
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=120  # Longer timeout for reasoning
        )

        response.raise_for_status()
        result = response.json()

        # Extract content
        content = result['choices'][0]['message']['content']

        print(f"\n✅ Response received")
        print(f"Raw content (first 200 chars): {content[:200]}")

        # Extract JSON (handle Harmony format prefix)
        if content.strip()[0] != '{':
            print(f"\n⚠️  Detected non-JSON prefix in response (Harmony format)")
            json_content = extract_json_from_harmony_format(content)
            print(f"Extracted JSON (first 200 chars): {json_content[:200]}")
        else:
            json_content = content

        # Parse JSON
        parsed = json.loads(json_content)
        print(f"\n✅ Valid JSON parsed:")
        print(json.dumps(parsed, indent=2))

        # Validate schema compliance
        assert "verdict" in parsed, "Missing 'verdict' field"
        assert parsed["verdict"] in ["PASS", "FAIL"], f"Invalid verdict: {parsed['verdict']}"
        assert "confidence" in parsed, "Missing 'confidence' field"
        assert 0 <= parsed["confidence"] <= 1, f"Invalid confidence: {parsed['confidence']}"
        assert "issues" in parsed, "Missing 'issues' field"
        assert isinstance(parsed["issues"], list), "issues should be a list"
        assert "answer_correctness" in parsed, "Missing 'answer_correctness' field"
        assert parsed["answer_correctness"] in ["CORRECT", "INCORRECT", "INCOMPLETE", "UNKNOWN"]
        assert "reasoning" in parsed, "Missing 'reasoning' field"

        # Validate issues array
        for i, issue in enumerate(parsed["issues"]):
            assert "type" in issue, f"Issue {i} missing 'type'"
            assert issue["type"] in ["CRITICAL_ERROR", "JUSTIFICATION_GAP"], f"Invalid issue type: {issue['type']}"
            assert "location" in issue, f"Issue {i} missing 'location'"
            assert "description" in issue, f"Issue {i} missing 'description'"
            assert "severity" in issue, f"Issue {i} missing 'severity'"
            assert 1 <= issue["severity"] <= 10, f"Invalid severity: {issue['severity']}"

        print(f"\n✅ Schema validation PASSED")
        print(f"\n📊 Verdict Summary:")
        print(f"   - Verdict: {parsed['verdict']}")
        print(f"   - Confidence: {parsed['confidence']:.2f}")
        print(f"   - Answer Correctness: {parsed['answer_correctness']}")
        print(f"   - Issues Found: {len(parsed['issues'])}")
        for i, issue in enumerate(parsed["issues"]):
            print(f"     {i+1}. [{issue['type']}] Severity {issue['severity']}: {issue['description'][:60]}...")
        print(f"   - Reasoning: {parsed['reasoning'][:100]}...")

        return True

    except requests.exceptions.RequestException as e:
        print(f"\n❌ HTTP Error: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}")
        return False
    except json.JSONDecodeError as e:
        print(f"\n❌ JSON Parsing Error: {e}")
        print(f"Content received: {content}")
        return False
    except AssertionError as e:
        print(f"\n❌ Schema Validation Error: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_with_reasoning_effort():
    """Test 3: Structured output with reasoning effort parameter"""

    print("\n" + "="*80)
    print("TEST 3: Structured Output + Reasoning Effort (High)")
    print("="*80)

    schema = {
        "type": "json_schema",
        "json_schema": {
            "name": "analysis",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "conclusion": {"type": "string"},
                    "reasoning_quality": {"type": "string", "enum": ["excellent", "good", "fair", "poor"]}
                },
                "required": ["conclusion", "reasoning_quality"],
                "additionalProperties": False
            }
        }
    }

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "user", "content": "Analyze why 2+2=4 and rate your reasoning quality."}
        ],
        "response_format": schema,
        "extra_body": {
            "reasoning": {"effort": "high"}  # OpenRouter API spec
        }
    }

    try:
        print("\n⏳ Sending request with high reasoning effort...")
        print(f"Payload: {json.dumps(payload, indent=2)}")

        response = requests.post(
            API_URL,
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=180  # Long timeout for high reasoning
        )

        response.raise_for_status()
        result = response.json()

        print(f"\n✅ Response received")
        print(f"Full response: {json.dumps(result, indent=2)}")

        # Extract content
        content = result['choices'][0]['message']['content']

        print(f"\nContent (first 200 chars): {content[:200]}")
        print(f"Content length: {len(content)}")

        if not content or len(content.strip()) == 0:
            print("\n⚠️  Empty content received - likely API parameter issue")
            print("This may indicate that 'extra_body' parameter is not compatible with structured outputs")
            print("Or reasoning effort should be set differently for OpenRouter")
            return False

        # Extract JSON (handle Harmony format prefix)
        if content.strip()[0] != '{':
            print(f"\n⚠️  Detected non-JSON prefix in response (Harmony format)")
            json_content = extract_json_from_harmony_format(content)
            print(f"Extracted JSON: {json_content[:200]}")
        else:
            json_content = content

        # Parse JSON
        parsed = json.loads(json_content)
        print(f"\n✅ Valid JSON parsed:")
        print(json.dumps(parsed, indent=2))

        # Validate
        assert "conclusion" in parsed
        assert "reasoning_quality" in parsed
        assert parsed["reasoning_quality"] in ["excellent", "good", "fair", "poor"]

        print(f"\n✅ Reasoning effort + structured output WORKS")

        return True

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all POC tests"""

    print("\n" + "="*80)
    print("OpenRouter GPT-OSS-120b Structured Output POC")
    print("="*80)
    print(f"Model: {MODEL}")
    print(f"API: {API_URL}")
    print("="*80)

    results = []

    # Test 1: Basic structured output
    results.append(("Basic Schema", test_basic_structured_output()))

    # Test 2: Verification verdict schema
    results.append(("Verification Schema", test_verification_verdict_schema()))

    # Test 3: Structured output + reasoning effort
    results.append(("Reasoning + Structured", test_with_reasoning_effort()))

    # Summary
    print("\n" + "="*80)
    print("POC RESULTS SUMMARY")
    print("="*80)

    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} | {test_name}")

    total_passed = sum(1 for _, passed in results if passed)
    total_tests = len(results)

    print("="*80)
    print(f"Total: {total_passed}/{total_tests} tests passed")

    if total_passed == total_tests:
        print("\n🎉 SUCCESS: Native structured outputs WORK with OpenRouter GPT-OSS-120b!")
        print("✅ Feasibility CONFIRMED - proceed with Option C implementation")
        return 0
    else:
        print("\n⚠️  WARNING: Some tests failed - investigate before proceeding")
        return 1


if __name__ == "__main__":
    sys.exit(main())

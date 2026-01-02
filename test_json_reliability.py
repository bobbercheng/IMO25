#!/usr/bin/env python3
"""
Test JSON reliability for structured output with different reasoning levels.
Tests if GPT-OSS can reliably output valid JSON with low/medium/high reasoning.
"""

import os
import sys
import json

# Add code directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'code'))

# Import the GPT-OSS client
from agent_gpt_oss import send_api_request, build_request_payload, get_api_key, API_URL

def test_json_output(reasoning_effort="low"):
    """Test if GPT-OSS outputs valid JSON with given reasoning effort."""

    print(f"\n{'='*70}")
    print(f"Testing JSON reliability with reasoning_effort='{reasoning_effort}'")
    print('='*70)

    # Simple math problem with JSON output request
    system_prompt = "You are a mathematical problem solver. Always return responses in valid JSON format."

    question_prompt = """Solve this problem and return ONLY valid JSON:

Problem: What is the minimum number of L-shaped tiles needed to cover a 3×3 grid with one square uncovered?

Return your response as valid JSON with this exact structure:
{
  "solution": "your detailed mathematical reasoning here",
  "final_answer": "the numerical answer only"
}

IMPORTANT: Return ONLY the JSON object, no other text before or after."""

    try:
        # Build request with specified reasoning effort
        payload = build_request_payload(
            system_prompt=system_prompt,
            question_prompt=question_prompt,
            reasoning_effort=reasoning_effort
        )

        print(f"\nRequest payload reasoning effort: {reasoning_effort}")
        print(f"Sending request to GPT-OSS...")

        # Call the API
        api_key = get_api_key()
        response = send_api_request(api_key, payload, stream=False, request_label=f"JSON Test ({reasoning_effort})")

        # Extract content
        if isinstance(response, dict) and 'choices' in response:
            content = response['choices'][0]['message']['content']
        else:
            content = str(response)

        print(f"\nRaw response (first 500 chars):")
        print("-" * 70)
        print(content[:500])
        print("-" * 70)

        # Try to parse as JSON
        try:
            parsed = json.loads(content)

            print(f"\n✓ SUCCESS: Valid JSON parsed!")
            print(f"\nParsed structure:")
            print(json.dumps(parsed, indent=2))

            # Validate required fields
            if 'solution' in parsed and 'final_answer' in parsed:
                print(f"\n✓ PASS: Contains required fields 'solution' and 'final_answer'")
                print(f"\nExtracted answer: '{parsed['final_answer']}'")
                return True, parsed
            else:
                print(f"\n✗ FAIL: Missing required fields")
                print(f"  Found fields: {list(parsed.keys())}")
                return False, None

        except json.JSONDecodeError as e:
            print(f"\n✗ FAIL: Invalid JSON")
            print(f"  Error: {e}")
            print(f"\n  Attempting to find JSON in response...")

            # Try to extract JSON from markdown code block
            if "```json" in content:
                json_start = content.find("```json") + 7
                json_end = content.find("```", json_start)
                if json_end > json_start:
                    json_content = content[json_start:json_end].strip()
                    try:
                        parsed = json.loads(json_content)
                        print(f"\n✓ SUCCESS: Found valid JSON in markdown block!")
                        print(f"\nParsed structure:")
                        print(json.dumps(parsed, indent=2))

                        if 'solution' in parsed and 'final_answer' in parsed:
                            print(f"\n⚠ PARTIAL PASS: Valid JSON but wrapped in markdown")
                            return True, parsed
                    except:
                        pass

            return False, None

    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False, None


def test_all_reasoning_levels():
    """Test JSON output with all reasoning levels."""

    print("\n" + "="*70)
    print("JSON RELIABILITY TEST SUITE")
    print("="*70)
    print(f"\nAPI URL: {API_URL}")
    print(f"Model: {os.environ.get('GPT_OSS_MODEL_NAME')}")

    api_key = get_api_key()
    print(f"API Key: {'*' * 20}{api_key[-10:] if api_key else '(not set)'}")

    results = []

    for effort in ["low", "medium", "high"]:
        success, parsed = test_json_output(effort)
        results.append((effort, success, parsed))

    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)

    for effort, success, parsed in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: reasoning_effort='{effort}'")
        if parsed:
            answer = parsed.get('final_answer', 'N/A')
            print(f"       Answer extracted: '{answer}'")

    # Recommendation
    print("\n" + "="*70)
    print("RECOMMENDATION")
    print("="*70)

    low_success = results[0][1]
    medium_success = results[1][1]
    high_success = results[2][1]

    if low_success:
        print("\n✅ LOW reasoning produces valid JSON")
        print("   → Safe to use structured output with reasoning_effort='low'")
        print("   → Cost-effective for solution generation")
    elif medium_success:
        print("\n⚠ LOW reasoning fails, but MEDIUM succeeds")
        print("   → Use reasoning_effort='medium' for structured output")
        print("   → Slightly higher cost but reliable JSON")
    elif high_success:
        print("\n⚠ Only HIGH reasoning produces valid JSON")
        print("   → Use reasoning_effort='high' for structured output")
        print("   → Higher cost, consider fallback strategy")
    else:
        print("\n❌ NONE of the reasoning levels produce valid JSON")
        print("   → Structured output may not be reliable")
        print("   → Consider using regex extraction as fallback")
        print("   → OR: Try prompting improvements (e.g., 'You MUST output valid JSON')")

    return results


if __name__ == "__main__":
    results = test_all_reasoning_levels()

    # Exit with success code if at least one level works
    any_success = any(success for _, success, _ in results)
    sys.exit(0 if any_success else 1)

#!/usr/bin/env python3
"""
Test GPT-5 Responses API response structure

According to OpenAI documentation, the Responses API returns:
{
  "id": "resp_...",
  "output": [
    {
      "type": "message",
      "role": "assistant",
      "content": [
        {
          "type": "output_text",
          "text": "..."
        }
      ]
    }
  ],
  "usage": {...}
}

But agent_oai.py extract_text_from_response() expects this structure.
Let's verify if it handles edge cases correctly.
"""

import json

def extract_text_from_response_gpt5(response_data):
    """
    Exact copy from agent_oai.py (lines 547-573)
    """
    try:
        print(">>>>>> Response:")
        print(json.dumps(response_data, indent=2))

        output_array = response_data['output']
        for item in output_array:
            if item['type'] == 'message' and 'content' in item:
                content_array = item['content']
                for content_item in content_array:
                    if content_item['type'] == 'output_text':
                        return content_item['text']
        
        # Fallback: if no text found, return empty string
        return ""
    except (KeyError, IndexError, TypeError) as e:
        print("Error: Could not extract text from the API response.")
        print(f"Reason: {e}")
        print("Full API Response:")
        print(json.dumps(response_data, indent=2))
        raise e


# Test Case 1: Normal response (what we expect)
print("="*80)
print("TEST 1: Normal Responses API output")
print("="*80)
normal_response = {
    "id": "resp_123",
    "output": [
        {
            "type": "message",
            "role": "assistant",
            "content": [
                {
                    "type": "output_text",
                    "text": "**Verification Verdict: PASS**\n\nThe solution is correct."
                }
            ]
        }
    ],
    "usage": {
        "prompt_tokens": 5000,
        "completion_tokens": 100,
        "total_tokens": 5100
    }
}

result = extract_text_from_response_gpt5(normal_response)
print(f"\nExtracted text length: {len(result)} chars")
print(f"Result: {result[:100]}...")

# Test Case 2: Empty content (0 tokens scenario)
print("\n" + "="*80)
print("TEST 2: Response with empty content (0 completion tokens)")
print("="*80)
empty_response = {
    "id": "resp_456",
    "output": [
        {
            "type": "message",
            "role": "assistant",
            "content": []  # Empty content array
        }
    ],
    "usage": {
        "prompt_tokens": 5000,
        "completion_tokens": 0,  # 0 tokens generated
        "total_tokens": 5000
    }
}

result = extract_text_from_response_gpt5(empty_response)
print(f"\nExtracted text length: {len(result)} chars")
print(f"Result: '{result}'")
print(f"\n⚠️  Returns empty string - this could explain 'no' response from verification check")

# Test Case 3: Refusal response
print("\n" + "="*80)
print("TEST 3: Refusal response (model asks for clarification)")
print("="*80)
refusal_response = {
    "id": "resp_789",
    "output": [
        {
            "type": "message",
            "role": "assistant",
            "content": [
                {
                    "type": "output_text",
                    "text": "Please provide the statement to evaluate."
                }
            ]
        }
    ],
    "usage": {
        "prompt_tokens": 5000,
        "completion_tokens": 8,  # Very few tokens
        "total_tokens": 5008
    }
}

result = extract_text_from_response_gpt5(refusal_response)
print(f"\nExtracted text length: {len(result)} chars")
print(f"Result: '{result}'")
print(f"\n✓ This is what's happening in Tests 1, 2, 6!")

# Analysis
print("\n" + "="*80)
print("ANALYSIS: Why GPT-5 says 'Please provide the statement to evaluate.'")
print("="*80)
print("""
Root Cause Hypothesis:

GPT-5 o3 model is CORRECTLY responding to an ambiguous prompt.

When the verification prompt is structured as:
  System: [verification_system_prompt]
  
  User: [verification_constraint]
  
  ### Problem ###
  [problem_statement]
  
  ### Solution ###
  [empty or poorly formatted solution]
  
  [verification_reminder]

The o3 model (which uses extended thinking) may be:
1. Detecting that the solution section is empty/malformed
2. Asking for clarification: "Please provide the statement to evaluate."
3. This is CORRECT behavior for a reasoning model - it's asking for clarification

This differs from gpt-oss-120b which:
1. Uses a BUGFIX to return full solution if marker missing
2. Always has valid solution content in verification prompt
3. Never triggers the clarification response

SOLUTION:
Copy the BUGFIX from agent_gpt_oss.py to agent_oai.py:
- If marker not found, return full solution instead of empty string
""")
print("="*80)

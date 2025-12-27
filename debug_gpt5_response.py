#!/usr/bin/env python3
"""
GPT-5 Response Debugging Script

Minimal test to understand why GPT-5 returns "Please provide the statement to evaluate."
and 0 tokens across all tests.

This script:
1. Makes minimal API call to GPT-5
2. Logs full raw response
3. Tests different extraction methods
4. Identifies root cause of 0-token issue
"""

import os
import sys
import json
import requests
from datetime import datetime

# Configuration
API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    print("ERROR: OPENAI_API_KEY environment variable not set")
    sys.exit(1)

API_URL = "https://api.openai.com/v1/responses"
MODEL_NAME = "gpt-5"

print("="*80)
print("GPT-5 RESPONSE DEBUGGING")
print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*80)

# Test 1: Minimal query (sanity check)
print("\n" + "="*80)
print("TEST 1: Minimal Query (Sanity Check)")
print("="*80)

payload_minimal = {
    "model": MODEL_NAME,
    "input": "What is 2+2?",
    "reasoning": {
        "effort": "high"
    },
    "max_output_tokens": 8192
}

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}

print("\nRequest Payload:")
print(json.dumps(payload_minimal, indent=2))

try:
    response = requests.post(API_URL, headers=headers, json=payload_minimal, timeout=300)
    print(f"\nResponse Status: {response.status_code}")

    if response.status_code == 200:
        response_json = response.json()
        print("\nFull Raw Response:")
        print(json.dumps(response_json, indent=2))

        # Try different extraction methods
        print("\n" + "-"*80)
        print("EXTRACTION ATTEMPTS:")
        print("-"*80)

        # Method 1: agent_oai.py current approach
        print("\nMethod 1: response['output']['content']")
        try:
            content1 = response_json['output']['content']
            print(f"✓ SUCCESS: {len(content1)} chars")
            print(f"Preview: {content1[:200]}...")
        except Exception as e:
            print(f"✗ FAILED: {e}")

        # Method 2: Chat Completions format
        print("\nMethod 2: response['choices'][0]['message']['content']")
        try:
            content2 = response_json['choices'][0]['message']['content']
            print(f"✓ SUCCESS: {len(content2)} chars")
            print(f"Preview: {content2[:200]}...")
        except Exception as e:
            print(f"✗ FAILED: {e}")

        # Method 3: Direct text field
        print("\nMethod 3: response['text']")
        try:
            content3 = response_json['text']
            print(f"✓ SUCCESS: {len(content3)} chars")
            print(f"Preview: {content3[:200]}...")
        except Exception as e:
            print(f"✗ FAILED: {e}")

        # Method 4: Response content
        print("\nMethod 4: response['response']['content']")
        try:
            content4 = response_json['response']['content']
            print(f"✓ SUCCESS: {len(content4)} chars")
            print(f"Preview: {content4[:200]}...")
        except Exception as e:
            print(f"✗ FAILED: {e}")

        # Show available keys
        print("\n" + "-"*80)
        print("AVAILABLE KEYS IN RESPONSE:")
        print("-"*80)
        print(json.dumps(list(response_json.keys()), indent=2))

    else:
        print(f"\n✗ API ERROR: {response.status_code}")
        print(response.text)

except Exception as e:
    print(f"\n✗ REQUEST FAILED: {e}")

# Test 2: Verification-style prompt
print("\n" + "="*80)
print("TEST 2: Verification Prompt (Like agent_oai.py)")
print("="*80)

verification_prompt = """System: You are an expert mathematician verifying a solution.

User:

**CRITICAL CONSTRAINTS FOR VERIFICATION:**

1. **Output Length Limit:** Your verification reasoning MUST be ≤2000 tokens total.
2. **Evaluate, Don't Re-Prove:** Evaluate the solution, do NOT re-prove.

======================================================================
### Problem ###

Determine all nonnegative integers k such that n lines can cover all required points.

======================================================================
### Solution ###

The answer is k ∈ {0, 1, 3}.

For k=0: Use vertical lines x=1, x=2, ..., x=n.
For k=1: Use sunny line through (n,1) with slope 1/(1-n).
For k=3: Use three sunny lines with slopes -1/2, -2, and 1.

### Verification Task ###

Provide your verdict: PASS or FAIL.
"""

payload_verification = {
    "model": MODEL_NAME,
    "input": verification_prompt,
    "reasoning": {
        "effort": "high"
    },
    "max_output_tokens": 8192
}

print("\nRequest Payload:")
print(f"Model: {MODEL_NAME}")
print(f"Input length: {len(verification_prompt)} chars")
print(f"Max output tokens: 8192")

try:
    response = requests.post(API_URL, headers=headers, json=payload_verification, timeout=300)
    print(f"\nResponse Status: {response.status_code}")

    if response.status_code == 200:
        response_json = response.json()

        # Save full response to file
        with open('gpt5_verification_response_debug.json', 'w') as f:
            json.dump(response_json, f, indent=2)

        print("\n✓ Full response saved to: gpt5_verification_response_debug.json")

        # Try extraction
        print("\n" + "-"*80)
        print("EXTRACTION ATTEMPT:")
        print("-"*80)

        extracted = None
        extraction_method = None

        # Try all methods
        for method_name, key_path in [
            ("output.content", lambda r: r['output']['content']),
            ("choices[0].message.content", lambda r: r['choices'][0]['message']['content']),
            ("text", lambda r: r['text']),
            ("response.content", lambda r: r['response']['content']),
            ("output", lambda r: r['output']),
        ]:
            try:
                extracted = key_path(response_json)
                extraction_method = method_name
                print(f"✓ SUCCESS with: {method_name}")
                break
            except:
                pass

        if extracted:
            print(f"\nExtracted content ({len(str(extracted))} chars):")
            print(str(extracted)[:500])
            if len(str(extracted)) > 500:
                print(f"... ({len(str(extracted)) - 500} more chars)")

            # Check for "Please provide the statement to evaluate."
            if "Please provide" in str(extracted):
                print("\n⚠️  WARNING: Found 'Please provide the statement to evaluate.' in response")
                print("This suggests model is refusing or misunderstanding the prompt")
        else:
            print("\n✗ FAILED: Could not extract content with any method")
            print("\nAvailable keys:")
            print(json.dumps(list(response_json.keys()), indent=2))

    else:
        print(f"\n✗ API ERROR: {response.status_code}")
        print(response.text)

except Exception as e:
    print(f"\n✗ REQUEST FAILED: {e}")

print("\n" + "="*80)
print("DIAGNOSTIC COMPLETE")
print("="*80)

print("\nNext Steps:")
print("1. Review gpt5_verification_response_debug.json for full API response")
print("2. Identify correct extraction method")
print("3. Update agent_oai.py extract_text_from_response() accordingly")

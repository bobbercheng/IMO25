#!/usr/bin/env python3
"""
Test API connection for LLM verification system.
"""

import os
import sys
import requests
import json

def test_api_connection():
    """Test if the LLM API is accessible."""

    # Get configuration
    api_url = os.getenv("GPT_OSS_API_URL", "http://localhost:4000/v1/chat/completions")
    api_key = os.getenv("GPT_OSS_API_KEY", "")
    model = os.getenv("GPT_OSS_MODEL_NAME", "openai/gpt-oss-120b")

    print("="*80)
    print("API CONNECTION TEST")
    print("="*80)
    print(f"API URL: {api_url}")
    print(f"API Key: {api_key[:20]}... (truncated)" if api_key else "API Key: (not set)")
    print(f"Model: {model}")
    print()

    # Test 1: Check if API endpoint is reachable
    print("[Test 1] Checking if API endpoint is reachable...")
    try:
        base_url = api_url.rsplit('/v1/', 1)[0]
        response = requests.get(base_url, timeout=5)
        print(f"✅ API endpoint reachable (status: {response.status_code})")
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Cannot connect to API endpoint")
        print(f"   Error: {str(e)[:200]}")
        print()
        print("TROUBLESHOOTING:")
        print("1. Check if the API server is running")
        print("2. Verify the URL is correct")
        print(f"3. Try: curl {base_url}")
        return False
    except Exception as e:
        print(f"❌ Error checking endpoint: {str(e)[:200]}")
        return False

    print()

    # Test 2: Send a simple chat completion request
    print("[Test 2] Sending test chat completion request...")

    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": "Say 'test successful' if you can read this"}
        ],
        "temperature": 0.0
    }

    # Add reasoning for standard API
    if not any(prefix in model for prefix in ["openrouter/", "anthropic/", "google/"]):
        payload["reasoning"] = {"effort": "low"}

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        response = requests.post(api_url, json=payload, headers=headers, timeout=30)

        print(f"Response status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            print(f"✅ API call successful")
            print(f"   Response: {content[:200]}")
            return True
        else:
            print(f"❌ API call failed")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text[:500]}")
            return False

    except requests.exceptions.Timeout:
        print(f"❌ Request timeout after 30 seconds")
        print("   The API server may be overloaded or not responding")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Connection error")
        print(f"   Error: {str(e)[:200]}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)[:200]}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run API tests."""
    success = test_api_connection()

    print()
    print("="*80)
    if success:
        print("✅ API CONNECTION TEST PASSED")
        print()
        print("You can now run:")
        print("  python code/llm_verification.py /tmp/ground_truth.txt --problem problems/imo01.txt")
        return 0
    else:
        print("❌ API CONNECTION TEST FAILED")
        print()
        print("Fix the API connection before running verification.")
        print()
        print("Common issues:")
        print("1. API server not running - start your GPT-OSS server")
        print("2. Wrong URL - check GPT_OSS_API_URL")
        print("3. Wrong API key - check GPT_OSS_API_KEY")
        print("4. Firewall blocking connection")
        return 1

if __name__ == "__main__":
    sys.exit(main())

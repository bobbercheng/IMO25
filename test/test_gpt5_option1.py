#!/usr/bin/env python3
"""
GPT-5 Option 1 Constraint Validation Script

Tests whether GPT-5 (with max_output_tokens fix) can match gpt-oss-120b's
100% accuracy (6/6) with Option 1 Level 2 gate check constraints.

Usage:
    export OPENAI_API_KEY="sk-..."
    python test_gpt5_option1.py --test all
    python test_gpt5_option1.py --test 4  # Test specific test number
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime
from typing import Dict, List, Tuple

# Add code directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'code'))

# Import test data
from test_data import get_test_data, IMO01_PROBLEM

# Import GPT-5 agent
import agent_oai


def show_configuration():
    """Show current configuration"""
    print("=" * 80)
    print("GPT-5 OPTION 1 VALIDATION CONFIGURATION")
    print("=" * 80)
    print(f"API URL: {agent_oai.API_URL}")
    print(f"Model: {agent_oai.MODEL_NAME}")
    api_key = os.getenv("OPENAI_API_KEY", "NOT_SET")
    print(f"API Key: {api_key[:20]}... (truncated)" if api_key != "NOT_SET" else "API Key: NOT SET")
    print("=" * 80)
    print()


def build_verification_request(problem: str, solution: str) -> Dict:
    """
    Build verification request payload matching agent_gpt_oss.py constraints.

    CRITICAL: Must include Option 1 Level 2 gate check constraints.
    """
    # Import verification prompts from agent_gpt_oss
    # NOTE: We need to replicate the EXACT constraints to ensure fair comparison

    verification_system_prompt = """You are a mathematical proof verification expert. Your task is to rigorously check whether a proposed solution to a mathematical problem is correct and complete.

**CRITICAL HIERARCHICAL DECISION TREE:**

You must evaluate the solution using this three-level hierarchy:

**LEVEL 1 - Answer Correctness:**
- Is the final answer mathematically correct?
- If NO → verdict = FAIL (stop evaluation)
- If YES → proceed to Level 2

**LEVEL 2 - Method Validity:**
- Are the logical steps valid and mathematically sound?
- Are all claims justified (no unjustified existence claims)?
- If NO → verdict = FAIL (stop evaluation)
- If YES → proceed to Level 3

**CRITICAL LEVEL 2 ENHANCEMENT - Justification Completeness (MANDATORY GATE CHECK):**

For FIND/DETERMINE problems, unjustified existence claims are **INVALID METHODS** (Level 2 failure).

**YOU MUST check during Level 2 (Method Validity):**
- Does the solution make existence claims without justification?
- Examples of UNJUSTIFIED CLAIMS (these are INVALID METHODS):
  ❌ "Construction exists" (zero details)
  ❌ "k=X works" (no equations, no strategy shown)
  ❌ "k=X is achievable" (no construction provided)

**Classification Rules:**
- If solution claims "k=X is achievable" WITHOUT providing construction →
  **INVALID METHOD → FAIL Level 2**
- If solution provides strategy OR explicit construction →
  **VALID METHOD → proceed to Level 3**

**THIS IS A LEVEL 2 GATE CHECK, NOT LEVEL 3 PRESENTATION:**
- Unjustified existence = logically incomplete = INVALID METHOD = FAIL Level 2
- You MUST classify "construction exists" (without details) as INVALID_METHOD
- This triggers Level 2 FAIL - do NOT proceed to Level 3

**LEVEL 3 - Presentation Quality:**
- Is the explanation clear and well-organized?
- Are there minor presentation issues?
- If SIGNIFICANT issues → verdict = FAIL
- If minor/no issues → verdict = PASS

**Output Format:**
Return ONLY a JSON object with this structure:
{
  "verdict": "yes" or "no",
  "confidence": 0-100,
  "answer_correctness": "CORRECT" or "INCORRECT",
  "reasoning": "brief explanation",
  "issues": [
    {
      "type": "CRITICAL_ERROR" or "INVALID_METHOD" or "JUSTIFICATION_GAP",
      "severity": 1-10,
      "location": "quote from solution",
      "description": "what's wrong"
    }
  ]
}
"""

    user_prompt = f"""# Problem Statement

{problem}

# Proposed Solution

{solution}

# Verification Task

Evaluate the proposed solution using the HIERARCHICAL DECISION TREE.

**CRITICAL:** For FIND/DETERMINE problems, check Level 2 carefully:
- Does the solution make unjustified existence claims?
- If YES → INVALID_METHOD → verdict = "no"

Return ONLY the JSON verification object (no additional text).
"""

    return {
        "system_prompt": verification_system_prompt,
        "user_prompt": user_prompt
    }


def verify_with_gpt5(problem: str, solution: str, verbose: bool = True) -> Tuple[str, Dict]:
    """
    Verify solution using GPT-5 with Option 1 constraints.

    Returns:
        (verdict, full_response): verdict is "yes"/"no", full_response is parsed JSON
    """
    if verbose:
        print(f"\n{'─' * 80}")
        print("BUILDING VERIFICATION REQUEST...")
        print(f"{'─' * 80}")

    # Build request
    request = build_verification_request(problem, solution)

    # Call GPT-5 API
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")

    # Build payload (using agent_oai.build_request_payload)
    payload = agent_oai.build_request_payload(
        system_prompt=request["system_prompt"],
        question_prompt=request["user_prompt"],
        max_completion_tokens=8192  # Use fixed value after bug fix
    )

    if verbose:
        print(f"\n{'─' * 80}")
        print("SENDING REQUEST TO GPT-5...")
        print(f"{'─' * 80}")
        print(f"Reasoning effort: high")
        print(f"Max output tokens: 8192")

    start_time = time.time()

    try:
        response = agent_oai.send_api_request(api_key, payload)
    except Exception as e:
        if verbose:
            print(f"\n❌ ERROR: {e}")
        raise

    elapsed = time.time() - start_time

    if verbose:
        print(f"\n{'─' * 80}")
        print(f"RESPONSE RECEIVED (elapsed: {elapsed:.2f}s)")
        print(f"{'─' * 80}")

    # Extract content from response
    try:
        if 'output' in response and 'content' in response['output']:
            content = response['output']['content']
        elif 'choices' in response:  # Fallback to Chat Completions format
            content = response['choices'][0]['message']['content']
        else:
            raise ValueError(f"Unknown response format: {response.keys()}")

        if not content or content.strip() == "":
            raise ValueError("GPT-5 returned empty content (zero-token response)")

    except Exception as e:
        if verbose:
            print(f"\n❌ PARSING ERROR: {e}")
            print(f"Response structure: {json.dumps(response, indent=2)[:500]}")
        raise ValueError(f"Failed to extract content from GPT-5 response: {e}")

    if verbose:
        print(f"Content length: {len(content)} characters")
        print(f"Content preview: {content[:200]}...")

    # Parse JSON response
    try:
        # Extract JSON from content (may be wrapped in markdown)
        content_clean = content.strip()
        if content_clean.startswith("```json"):
            content_clean = content_clean[7:]
        if content_clean.startswith("```"):
            content_clean = content_clean[3:]
        if content_clean.endswith("```"):
            content_clean = content_clean[:-3]
        content_clean = content_clean.strip()

        result = json.loads(content_clean)

    except json.JSONDecodeError as e:
        if verbose:
            print(f"\n❌ JSON PARSING ERROR: {e}")
            print(f"Raw content:\n{content}")
        raise ValueError(f"GPT-5 returned invalid JSON: {e}")

    # Extract verdict
    verdict = result.get("verdict", "unknown").lower()
    if verdict not in ["yes", "no"]:
        if verbose:
            print(f"\n⚠️  WARNING: Unexpected verdict '{verdict}', treating as 'no'")
        verdict = "no"

    if verbose:
        print(f"\n{'─' * 80}")
        print(f"VERIFICATION RESULT:")
        print(f"{'─' * 80}")
        print(f"Verdict: {verdict}")
        print(f"Confidence: {result.get('confidence', 'N/A')}%")
        print(f"Answer Correctness: {result.get('answer_correctness', 'N/A')}")
        print(f"Issues Found: {len(result.get('issues', []))}")

    return verdict, result


def run_test(test_number: int, test_case: Dict, verbose: bool = True) -> Dict:
    """Run a single test case"""
    print(f"\n{'=' * 80}")
    print(f"TEST {test_number}: {test_case['test_name']}")
    print(f"{'=' * 80}")
    print(f"Expected verdict: {test_case['expected_verdict']}")

    start_time = time.time()

    try:
        verdict, result = verify_with_gpt5(
            IMO01_PROBLEM,
            test_case['solution'],
            verbose=verbose
        )

        elapsed = time.time() - start_time

        # Check if verdict matches expected
        passed = (verdict == "yes" and test_case['expected_verdict'] == "PASS") or \
                 (verdict == "no" and test_case['expected_verdict'] == "FAIL")

        print(f"\n{'─' * 80}")
        print(f"TEST RESULT:")
        print(f"{'─' * 80}")
        print(f"  Verdict: {verdict} ({'PASS' if verdict == 'yes' else 'FAIL'})")
        print(f"  Expected: {test_case['expected_verdict']}")
        print(f"  Match: {'✅ CORRECT' if passed else '❌ WRONG'}")
        print(f"  Elapsed: {elapsed:.2f}s")

        return {
            "test_number": test_number,
            "test_name": test_case['test_name'],
            "verdict": verdict,
            "expected": test_case['expected_verdict'],
            "match": passed,
            "elapsed_seconds": elapsed,
            "full_result": result,
            "error": None
        }

    except Exception as e:
        elapsed = time.time() - start_time

        print(f"\n{'─' * 80}")
        print(f"TEST ERROR:")
        print(f"{'─' * 80}")
        print(f"  Error: {e}")
        print(f"  Elapsed: {elapsed:.2f}s")

        return {
            "test_number": test_number,
            "test_name": test_case['test_name'],
            "verdict": "error",
            "expected": test_case['expected_verdict'],
            "match": False,
            "elapsed_seconds": elapsed,
            "full_result": None,
            "error": str(e)
        }


def run_all_tests(verbose: bool = True) -> Dict:
    """Run all 6 tests and return summary"""
    test_data = get_test_data()

    results = []
    for i, test_case in enumerate(test_data, 1):
        result = run_test(i, test_case, verbose=verbose)
        results.append(result)

        # Brief pause between tests
        if i < len(test_data):
            time.sleep(2)

    # Calculate summary statistics
    total_tests = len(results)
    completed = sum(1 for r in results if r['error'] is None)
    errors = sum(1 for r in results if r['error'] is not None)
    matches = sum(1 for r in results if r['match'])
    accuracy = matches / total_tests if total_tests > 0 else 0.0
    avg_time = sum(r['elapsed_seconds'] for r in results) / total_tests if total_tests > 0 else 0.0

    summary = {
        "timestamp": datetime.now().isoformat(),
        "test_type": "gpt5_option1_validation",
        "model": agent_oai.MODEL_NAME,
        "api_url": agent_oai.API_URL,
        "total_tests": total_tests,
        "completed": completed,
        "errors": errors,
        "matches": matches,
        "accuracy": accuracy,
        "avg_time_seconds": avg_time,
        "results": results
    }

    return summary


def print_summary(summary: Dict):
    """Print test summary"""
    print(f"\n\n{'=' * 80}")
    print("GPT-5 OPTION 1 VALIDATION SUMMARY")
    print(f"{'=' * 80}")
    print(f"Timestamp: {summary['timestamp']}")
    print(f"Model: {summary['model']}")
    print(f"Total Tests: {summary['total_tests']}")
    print(f"Completed: {summary['completed']}")
    print(f"Errors: {summary['errors']}")
    print(f"Matches: {summary['matches']}")
    print(f"Accuracy: {summary['accuracy'] * 100:.1f}%")
    print(f"Avg Time: {summary['avg_time_seconds']:.2f}s")
    print(f"{'=' * 80}")

    print(f"\nDETAILED RESULTS:")
    print(f"{'─' * 80}")

    for r in summary['results']:
        status = "✅" if r['match'] else ("❌" if r['error'] is None else "⚠️")
        print(f"{status} Test {r['test_number']}: {r['verdict']:6} (expected: {r['expected']:4}) "
              f"- {r['elapsed_seconds']:6.2f}s - {r['test_name']}")

        if r['error']:
            print(f"   ERROR: {r['error']}")

    print(f"{'─' * 80}")

    # Compare to gpt-oss-120b baseline
    print(f"\nCOMPARISON TO gpt-oss-120b BASELINE:")
    print(f"{'─' * 80}")
    print(f"gpt-oss-120b (Option 1): 100.0% accuracy (6/6 matches)")
    print(f"GPT-5 (this run):        {summary['accuracy'] * 100:5.1f}% accuracy "
          f"({summary['matches']}/{summary['total_tests']} matches)")

    if summary['accuracy'] >= 1.0:
        print(f"\n✅ GPT-5 MATCHES gpt-oss-120b (100% accuracy)")
        print(f"   → Proceed to latency and cost analysis")
    elif summary['accuracy'] >= 0.83:
        print(f"\n⚠️  GPT-5 CLOSE to gpt-oss-120b but NOT 100%")
        print(f"   → Need n=30 validation to confirm")
    else:
        print(f"\n❌ GPT-5 WORSE than gpt-oss-120b baseline")
        print(f"   → DO NOT DEPLOY - use gpt-oss-120b instead")

    print(f"{'=' * 80}")


def main():
    parser = argparse.ArgumentParser(description="GPT-5 Option 1 Constraint Validation")
    parser.add_argument("--test", type=str, default="all",
                        help="Test number to run (1-6) or 'all'")
    parser.add_argument("--verbose", action="store_true", default=True,
                        help="Verbose output (default: True)")
    parser.add_argument("--quiet", action="store_true",
                        help="Quiet mode (minimal output)")
    parser.add_argument("--save-results", type=str, default=None,
                        help="Save results to JSON file")

    args = parser.parse_args()

    # Check API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY environment variable not set")
        print("Please set it:")
        print("  export OPENAI_API_KEY='sk-...'")
        sys.exit(1)

    verbose = args.verbose and not args.quiet

    show_configuration()

    if args.test == "all":
        # Run all tests
        summary = run_all_tests(verbose=verbose)
        print_summary(summary)

        # Save results if requested
        if args.save_results:
            with open(args.save_results, 'w') as f:
                json.dump(summary, f, indent=2)
            print(f"\n✅ Results saved to: {args.save_results}")

    else:
        # Run single test
        test_num = int(args.test)
        if test_num < 1 or test_num > 6:
            print(f"ERROR: Test number must be 1-6 (got {test_num})")
            sys.exit(1)

        test_data = get_test_data()
        test_case = test_data[test_num - 1]

        result = run_test(test_num, test_case, verbose=verbose)

        print(f"\n{'=' * 80}")
        print("SINGLE TEST RESULT:")
        print(f"{'=' * 80}")
        print(f"Test: {result['test_name']}")
        print(f"Verdict: {result['verdict']}")
        print(f"Expected: {result['expected']}")
        print(f"Match: {'✅ CORRECT' if result['match'] else '❌ WRONG'}")
        print(f"Elapsed: {result['elapsed_seconds']:.2f}s")

        if result['error']:
            print(f"Error: {result['error']}")

        if args.save_results:
            with open(args.save_results, 'w') as f:
                json.dump(result, f, indent=2)
            print(f"\n✅ Result saved to: {args.save_results}")


if __name__ == "__main__":
    main()

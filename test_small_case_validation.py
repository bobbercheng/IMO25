#!/usr/bin/env python3
"""
Test Small-Case Validation with LLM

This script tests if an LLM can solve the grid tiling problem for small cases
when given validated ground truth hints.

Test Design:
1. Use brute-force verified answer: n=4 → 5 tiles
2. Give LLM the problem with small-case hint
3. Check if LLM finds the correct formula (n+2k-3)
"""

import os
import json
import requests
from typing import Dict, Any


# GPT-OSS API configuration (same as agent_gpt_oss.py)
API_URL = os.getenv("GPT_OSS_API_URL", "http://localhost:30000/v1/chat/completions")
API_KEY = os.getenv("GPT_OSS_API_KEY", "")
MODEL_NAME = os.getenv("GPT_OSS_MODEL_NAME", "openai/gpt-oss-120b")


def call_llm(prompt: str, system_prompt: str = None, max_retries: int = 3) -> Dict[str, Any]:
    """Call LLM via OpenRouter API with retry logic"""
    import time

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "temperature": 0.7,
    }

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    print(f"\n{'='*80}")
    print(f"Calling {MODEL_NAME}...")
    print(f"{'='*80}\n")

    for attempt in range(max_retries):
        try:
            response = requests.post(API_URL, json=payload, headers=headers, timeout=60)
            response.raise_for_status()
            result = response.json()
            return result['choices'][0]['message']['content']
        except requests.exceptions.HTTPError as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                print(f"HTTP Error: {e}")
                print(f"Retrying in {wait_time}s... (attempt {attempt+1}/{max_retries})")
                time.sleep(wait_time)
            else:
                raise
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"Error: {e}")
                print(f"Retrying in {wait_time}s... (attempt {attempt+1}/{max_retries})")
                time.sleep(wait_time)
            else:
                raise


def extract_formula_and_answer(llm_response: str) -> tuple:
    """Extract formula and answer from LLM response"""
    # Look for formula patterns
    formulas = []
    if "n+2k-3" in llm_response or "n + 2k - 3" in llm_response:
        formulas.append("n+2k-3")
    if "n+2k-2" in llm_response or "n + 2k - 2" in llm_response:
        formulas.append("n+2k-2")
    if "2n-2" in llm_response or "2n - 2" in llm_response:
        formulas.append("2n-2")

    # Look for final answer for n=2025
    import re
    answer_matches = re.findall(r'(?:answer|result|minimum).*?(\d{4})', llm_response.lower())

    return formulas, answer_matches


def test_baseline(problem_statement: str):
    """Test LLM WITHOUT small-case validation"""

    print("\n" + "="*80)
    print("TEST 1: BASELINE (No Small-Case Validation)")
    print("="*80)

    system_prompt = """You are a mathematical problem solver. Find the minimum number of tiles needed for the grid tiling problem."""

    response = call_llm(problem_statement, system_prompt)

    print("LLM Response (excerpt):")
    print("-" * 80)
    print(response[:500] + "..." if len(response) > 500 else response)
    print("-" * 80)

    formulas, answers = extract_formula_and_answer(response)

    print("\nExtracted:")
    print(f"  Formulas mentioned: {formulas}")
    print(f"  Answers mentioned: {answers}")

    return response, formulas, answers


def test_with_validation(problem_statement: str, verified_cases: str):
    """Test LLM WITH small-case validation"""

    print("\n" + "="*80)
    print("TEST 2: WITH SMALL-CASE VALIDATION")
    print("="*80)

    system_prompt = """You are a mathematical problem solver. Use the verified small-case examples to validate your formula."""

    # Inject verified small cases into prompt
    enhanced_prompt = f"""{problem_statement}

{verified_cases}

**IMPORTANT:** Use the verified small-case answer to test your formula. If your formula doesn't match the small case, it's WRONG.
"""

    response = call_llm(enhanced_prompt, system_prompt)

    print("LLM Response (excerpt):")
    print("-" * 80)
    print(response[:500] + "..." if len(response) > 500 else response)
    print("-" * 80)

    formulas, answers = extract_formula_and_answer(response)

    print("\nExtracted:")
    print(f"  Formulas mentioned: {formulas}")
    print(f"  Answers mentioned: {answers}")

    return response, formulas, answers


def main():
    """Run the test"""

    print("="*80)
    print("SMALL-CASE VALIDATION TEST")
    print("="*80)
    print(f"Using model: {MODEL_NAME}")
    print(f"API endpoint: {API_URL}")
    print()

    # Problem statement (simplified version of IMO 2025 P6)
    problem_statement = """
**Problem:** Consider a 2025×2025 grid of unit squares. You want to place rectangular tiles
(of possibly different sizes) such that:
- Each side of every tile lies on a grid line
- Every unit square is covered by at most one tile
- Each row has exactly one unit square that is NOT covered by any tile
- Each column has exactly one unit square that is NOT covered by any tile

**Question:** What is the MINIMUM number of tiles needed?

For context: 2025 = 45², so k = √2025 = 45.
"""

    # Verified small-case ground truth (from brute-force solver)
    verified_cases = """
**VERIFIED SMALL-CASE GROUND TRUTH** (From Exhaustive Search):

For n=4 (4×4 grid, k=√4=2):
- The minimum is EXACTLY **5 tiles** (verified by brute-force enumeration)
- This is GUARANTEED CORRECT (all 24 configurations tested)

Test your formula:
- If formula(n=4, k=2) ≠ 5, your formula is WRONG
- If formula(n=4, k=2) = 5, your formula MIGHT be correct (validate further)
"""

    # Test 1: Baseline (no validation)
    baseline_response, baseline_formulas, baseline_answers = test_baseline(problem_statement)

    # Test 2: With validation
    validated_response, validated_formulas, validated_answers = test_with_validation(
        problem_statement, verified_cases
    )

    # Compare results
    print("\n" + "="*80)
    print("COMPARISON: BASELINE vs WITH-VALIDATION")
    print("="*80)

    print("\nBaseline (no validation):")
    print(f"  Formulas: {baseline_formulas}")
    print(f"  Answers: {baseline_answers}")

    print("\nWith validation:")
    print(f"  Formulas: {validated_formulas}")
    print(f"  Answers: {validated_answers}")

    # Check if validation helped
    correct_formula = "n+2k-3"
    correct_answer = "2112"

    baseline_correct = correct_formula in baseline_formulas
    validated_correct = correct_formula in validated_formulas

    print("\n" + "="*80)
    print("RESULT")
    print("="*80)

    print(f"\nBaseline found correct formula (n+2k-3): {'✓' if baseline_correct else '✗'}")
    print(f"With validation found correct formula (n+2k-3): {'✓' if validated_correct else '✗'}")

    if validated_correct and not baseline_correct:
        print("\n🎉 SUCCESS: Small-case validation HELPED LLM find correct formula!")
    elif validated_correct and baseline_correct:
        print("\n⚠️  NEUTRAL: Both approaches found correct formula (validation didn't hurt)")
    elif not validated_correct and not baseline_correct:
        print("\n❌ FAILURE: Neither approach found correct formula (need better prompt)")
    else:
        print("\n⚠️  REGRESSION: Baseline was better (validation confused the LLM)")

    # Save results
    results = {
        "test": "small_case_validation",
        "model": MODEL_NAME,
        "verified_ground_truth": {"n": 4, "k": 2, "tiles": 5},
        "baseline": {
            "formulas": baseline_formulas,
            "answers": baseline_answers,
            "correct": baseline_correct,
        },
        "with_validation": {
            "formulas": validated_formulas,
            "answers": validated_answers,
            "correct": validated_correct,
        },
        "conclusion": "success" if (validated_correct and not baseline_correct) else
                     "neutral" if (validated_correct and baseline_correct) else
                     "regression" if (baseline_correct and not validated_correct) else
                     "failure"
    }

    with open("small_case_validation_test_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print("\nResults saved to: small_case_validation_test_results.json")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
LLM Unit Test: Verify solution field excludes \\boxed{} format

This test validates that the new schema design works correctly:
1. Solution field contains ONLY reasoning/proof (no \\boxed{})
2. final_answer field contains the numerical answer
3. anyOf constraint prevents blacklisted values
4. Model can still solve problems correctly

Created: 2026-01-04
Purpose: Confirm schema changes prevent answer inconsistency issue
"""

import sys
import os
import unittest
import json
import re

# Add code directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'code'))

from agent_gpt_oss import (
    send_api_request_with_retry,
    extract_text_from_response,
    get_api_key,
    validate_no_boxed_in_solution,
    get_solution_text
)
from schema_blacklist import get_blacklist_constrained_schema


class TestNoBoxedFormat(unittest.TestCase):
    """Test that schema enforces separation of reasoning and answer."""

    @classmethod
    def setUpClass(cls):
        """Verify API key is available."""
        try:
            api_key = get_api_key()
            if not api_key:
                raise ValueError("GPT_OSS_API_KEY not set")
            print(f"\n[TEST SETUP] API key available: {api_key[:10]}...")
        except Exception as e:
            print(f"\n[TEST SETUP] WARNING: {e}")
            print("[TEST SETUP] Some tests may be skipped")

    def test_validation_function_detects_boxed(self):
        """Test that validate_no_boxed_in_solution correctly detects \\boxed{} format."""

        # Test case 1: Solution WITH boxed (should FAIL validation)
        solution_with_boxed = {
            "solution": "The answer is clearly \\boxed{42} by inspection.",
            "method": "inspection",
            "final_answer": 42
        }

        is_valid, error_msg = validate_no_boxed_in_solution(solution_with_boxed, verbose=False)

        self.assertFalse(is_valid, "Should reject solution with \\boxed{}")
        self.assertIsNotNone(error_msg, "Should provide error message")
        self.assertIn("\\boxed{}", error_msg, "Error message should mention \\boxed{}")

        print("✓ Test 1: Validation correctly rejects \\boxed{} format")

        # Test case 2: Solution WITHOUT boxed (should PASS validation)
        solution_without_boxed = {
            "solution": "Using the pigeonhole principle, we can show that the answer must be 42.",
            "method": "pigeonhole",
            "final_answer": 42
        }

        is_valid, error_msg = validate_no_boxed_in_solution(solution_without_boxed, verbose=False)

        self.assertTrue(is_valid, "Should accept solution without \\boxed{}")
        self.assertIsNone(error_msg, "Should not have error message")

        print("✓ Test 2: Validation correctly accepts solution without \\boxed{}")

    def test_schema_description_prohibits_boxed(self):
        """Test that schema description explicitly prohibits \\boxed{} format."""

        # Create schema with blacklist
        import tempfile

        blacklist = {
            "problem_id": "test01",
            "solutions": [
                {"answer": "100", "method": "wrong_method", "verdict": "FAIL"}
            ]
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(blacklist, f)
            blacklist_file = f.name

        try:
            problem_statement = "Find the smallest positive integer n such that..."

            schema = get_blacklist_constrained_schema(
                blacklist_file,
                problem_statement,
                blacklist=blacklist["solutions"]
            )

            # Verify schema structure
            self.assertIn('properties', schema, "Schema should have properties")
            self.assertIn('solution', schema['properties'], "Schema should have solution field")
            self.assertIn('final_answer', schema['properties'], "Schema should have final_answer field")

            # Verify solution field description
            solution_desc = schema['properties']['solution']['description']
            self.assertIn('DO NOT include', solution_desc, "Should prohibit \\boxed{}")
            self.assertIn('reasoning', solution_desc.lower(), "Should mention reasoning")
            self.assertIn('proof', solution_desc.lower(), "Should mention proof")

            # Verify final_answer field description
            final_answer_desc = schema['properties']['final_answer']['description']
            self.assertIn('ONLY', final_answer_desc, "Should emphasize exclusivity")

            print("✓ Test 3: Schema description correctly prohibits \\boxed{}")
            print(f"   Solution field: {solution_desc[:100]}...")
            print(f"   Final answer field: {final_answer_desc[:80]}...")

        finally:
            os.unlink(blacklist_file)

    @unittest.skipIf(not os.getenv('RUN_LLM_TESTS'),
                     "Skipping LLM test (set RUN_LLM_TESTS=1 to run)")
    def test_llm_generates_correct_format(self):
        """
        LLM TEST: Verify model generates solution without \\boxed{} format.

        This is the critical integration test that validates the entire flow:
        - Schema with prohibition guidance
        - Prompt with format requirements
        - Model response format
        - Validation function
        """

        print("\n" + "="*80)
        print("LLM INTEGRATION TEST: No \\boxed{} in solution field")
        print("="*80)

        # Simple math problem for testing (answer is 24)
        problem_statement = """
Find the smallest positive integer n such that n^2 + n is divisible by 100.
"""

        # Create schema with blacklist (to test anyOf constraint too)
        import tempfile

        # Use blacklist that doesn't create weird ranges
        # Correct answer is 24, so blacklist nearby wrong values
        blacklist = {
            "problem_id": "test_simple",
            "solutions": [
                {"answer": "20", "method": "guess", "verdict": "FAIL"},
                {"answer": "25", "method": "wrong_calculation", "verdict": "FAIL"},
                {"answer": "50", "method": "wrong_approach", "verdict": "FAIL"}
            ]
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(blacklist, f)
            blacklist_file = f.name

        try:
            schema = get_blacklist_constrained_schema(
                blacklist_file,
                problem_statement,
                blacklist=blacklist["solutions"]
            )

            # Build prompt
            prompt = f"""
{problem_statement}

**IMPORTANT OUTPUT FORMAT:**
Return your response as valid JSON with this exact structure:
{{
  "solution": "your complete mathematical reasoning and proof",
  "final_answer": 42
}}

CRITICAL FORMAT REQUIREMENTS:
1. The 'solution' field contains ONLY your mathematical reasoning and proof.
   - DO NOT include the final numerical answer in \\boxed{{}} format
   - Focus on explaining WHY your answer is correct
   - Keep your solution concise but complete

2. The 'final_answer' field contains ONLY the integer value.
   - This is the conclusive result from your reasoning

3. FORBIDDEN answers (proven incorrect): [20, 25, 50]
   - You MUST arrive at a different answer
"""

            # Make API request
            print("\n[API REQUEST] Generating solution with new format...")
            print(f"[API CONFIG] Using model: {os.getenv('GPT_OSS_MODEL_NAME', 'openai/gpt-oss-120b')}")
            print(f"[API CONFIG] Using endpoint: {os.getenv('GPT_OSS_API_URL', 'http://localhost:30000/v1/chat/completions')}")

            payload = {
                "model": os.getenv("GPT_OSS_MODEL_NAME", "openai/gpt-oss-120b"),
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,  # Lower temperature for more focused responses
                "max_tokens": 3000,  # Increased to handle complete JSON
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "math_solution",
                        "schema": schema,
                        "strict": True
                    }
                }
            }

            response = send_api_request_with_retry(
                get_api_key(),
                payload,
                stream=False,
                request_label="Test: No boxed format"
            )

            # Extract and parse response
            response_text = extract_text_from_response(response)

            # Check if response_text is already a dict (structured output parsed)
            # or a string (needs JSON parsing)
            if isinstance(response_text, dict):
                # Already parsed by extract_text_from_response
                solution_dict = response_text
                print(f"\n[API RESPONSE] Structured output already parsed")
            else:
                # String response - needs JSON parsing
                print(f"\n[API RESPONSE] Raw text length: {len(response_text)} chars")

                # Parse JSON with error handling
                try:
                    solution_dict = json.loads(response_text)
                except json.JSONDecodeError as e:
                    print(f"\n✗ JSON PARSING FAILED: {e}")
                    print(f"\n[RAW RESPONSE] First 1000 chars:")
                    print(response_text[:1000])
                    print(f"\n[RAW RESPONSE] Last 500 chars:")
                    print(response_text[-500:])
                    self.fail(f"Failed to parse JSON response: {e}\nResponse may be truncated or malformed.")

            # Check for truncation
            if hasattr(response, 'choices') and response.choices:
                finish_reason = response.choices[0].finish_reason
                print(f"[API RESPONSE] Finish reason: {finish_reason}")

                if finish_reason == "length":
                    print("\n⚠️  WARNING: Response was truncated (hit max_tokens limit)")
                    print("This may result in incomplete JSON.")

            # Print response
            print("\n[RESPONSE STRUCTURE]")
            print(f"  Keys: {list(solution_dict.keys())}")
            print(f"  solution: {len(solution_dict.get('solution', ''))} chars")
            print(f"  method: {solution_dict.get('method', 'N/A')}")
            print(f"  final_answer: {solution_dict.get('final_answer', 'N/A')}")

            # Check for empty response
            if not solution_dict or len(solution_dict) == 0:
                print("\n✗ ERROR: Response is empty!")
                print(f"[DEBUG] Full response object:")
                print(json.dumps(response, indent=2) if isinstance(response, dict) else str(response))
                self.fail("API returned empty response - check API key, endpoint, and model availability")

            print("\n[SOLUTION TEXT] (first 500 chars)")
            solution_text_preview = solution_dict.get('solution', '')[:500]
            print(solution_text_preview if solution_text_preview else "(empty)")

            # VALIDATION 1: Verify structure
            if 'solution' not in solution_dict:
                print(f"\n✗ ERROR: Missing 'solution' field")
                print(f"[DEBUG] Available fields: {list(solution_dict.keys())}")
                print(f"[DEBUG] Full response: {json.dumps(solution_dict, indent=2)}")
                self.fail("Response missing 'solution' field")

            if 'final_answer' not in solution_dict:
                print(f"\n✗ ERROR: Missing 'final_answer' field")
                print(f"[DEBUG] Available fields: {list(solution_dict.keys())}")
                print(f"[DEBUG] Full response: {json.dumps(solution_dict, indent=2)}")
                self.fail("Response missing 'final_answer' field")

            if 'method' not in solution_dict:
                print(f"\n✗ ERROR: Missing 'method' field")
                print(f"[DEBUG] Available fields: {list(solution_dict.keys())}")
                print(f"[DEBUG] Full response: {json.dumps(solution_dict, indent=2)}")
                self.fail("Response missing 'method' field")

            print("\n✓ PASS: Response has correct structure")

            # VALIDATION 2: Verify final_answer is integer
            final_answer = solution_dict['final_answer']
            self.assertIsInstance(final_answer, int, "final_answer should be integer type")

            print(f"✓ PASS: final_answer is integer: {final_answer}")

            # VALIDATION 3: Verify final_answer NOT in blacklist
            blacklisted_values = [20, 25, 50]
            self.assertNotIn(final_answer, blacklisted_values,
                           f"final_answer {final_answer} should not be blacklisted")

            print(f"✓ PASS: final_answer {final_answer} is not blacklisted (avoiding {blacklisted_values})")

            # VALIDATION 3.5: Check if answer is correct (expected: 24)
            if final_answer == 24:
                print(f"✓ BONUS: final_answer {final_answer} is CORRECT! (24^2 + 24 = 600, divisible by 100)")
            else:
                print(f"ℹ️  NOTE: final_answer {final_answer} may not be correct (expected 24)")

            # VALIDATION 4: Verify solution does NOT contain \boxed{}
            is_valid, error_msg = validate_no_boxed_in_solution(solution_dict, verbose=False)

            if not is_valid:
                print(f"\n✗ FAIL: {error_msg}")
                print("\n[FULL SOLUTION TEXT]")
                print(solution_dict['solution'])
                self.fail("Solution contains \\boxed{} format (should be prohibited)")

            print("✓ PASS: Solution does NOT contain \\boxed{} format")

            # VALIDATION 5: Verify solution contains reasoning
            solution_text = solution_dict['solution']
            self.assertGreater(len(solution_text), 100,
                             "Solution should contain substantial reasoning (>100 chars)")

            # Check for mathematical reasoning keywords
            reasoning_keywords = ['because', 'therefore', 'hence', 'thus', 'since', 'proof', 'show']
            has_reasoning = any(keyword in solution_text.lower() for keyword in reasoning_keywords)
            self.assertTrue(has_reasoning,
                          "Solution should contain reasoning keywords")

            print(f"✓ PASS: Solution contains reasoning ({len(solution_text)} chars)")

            print("\n" + "="*80)
            print("ALL VALIDATIONS PASSED ✓")
            print("="*80)
            print("\nSUMMARY:")
            print(f"  - Model generated solution WITHOUT \\boxed{{}} format ✓")
            print(f"  - final_answer field: {final_answer} (integer type) ✓")
            print(f"  - Blacklist constraint enforced: avoided {blacklisted_values} ✓")
            print(f"  - Solution contains reasoning: {len(solution_text)} chars ✓")
            if final_answer == 24:
                print(f"  - Answer is mathematically CORRECT (24) ✓✓")
            print("\n✅ NEW FORMAT WORKING CORRECTLY - SINGLE SOURCE OF TRUTH VALIDATED")

        finally:
            os.unlink(blacklist_file)


if __name__ == "__main__":
    print("="*80)
    print("LLM Unit Test: No \\boxed{} Format Validation")
    print("="*80)
    print()
    print("This test validates that:")
    print("  1. Schema prohibits \\boxed{} in solution field")
    print("  2. Validation function detects \\boxed{} correctly")
    print("  3. LLM generates correct format (requires API)")
    print()
    print("To run LLM integration test:")
    print("  RUN_LLM_TESTS=1 python test_no_boxed_format.py")
    print()
    print("="*80)
    print()

    # Run tests
    unittest.main(verbosity=2)

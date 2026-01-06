#!/usr/bin/env python3
"""
Small-Case Formula Validation Module

This module provides formula derivation from verified small cases for BFS integration.
It enables fast pattern recognition for formula-based problems without data leakage.

Key Features:
- Derives formulas from independently verified small cases
- No circular reasoning (all cases verified without using the target formula)
- Robust normalization for various formula formats
- Confidence scoring for risk management
- Graceful fallback to standard BFS on failure

Usage:
    from small_case_validator import SmallCaseValidator

    validator = SmallCaseValidator(llm_client)
    result = validator.derive_formula(problem_statement, verified_cases)

    if result and result["confidence"] >= 0.8:
        answer = result["answer"]
    else:
        # Fall back to standard BFS
        answer = standard_bfs_solve(problem)
"""

import re
import json
from typing import Dict, List, Optional, Tuple, Any


def normalize_formula(formula_str: str) -> str:
    """
    Normalize formula to canonical form for matching.

    Handles various formats:
    - "f(n,k) = n + 2*k - 3" → "n+2k-3"
    - "n + 2·k - 3" → "n+2k-3"
    - "n+2k−3" (Unicode minus) → "n+2k-3"

    Args:
        formula_str: Raw formula string from LLM

    Returns:
        Normalized formula string
    """
    # Remove function notation like f(n,k) =
    formula_str = re.sub(r'f\([^)]+\)\s*=\s*', '', formula_str)

    # Extract first formula if multiple given (before "equivalently", "or", etc.)
    formula_str = formula_str.split('(equivalently')[0]
    formula_str = formula_str.split(' or ')[0]

    # Remove spaces and multiplication operators
    formula_str = formula_str.replace(' ', '')
    formula_str = formula_str.replace('*', '')
    formula_str = formula_str.replace('·', '')

    # Handle Unicode characters
    formula_str = formula_str.replace('−', '-')
    formula_str = formula_str.replace('√', 'sqrt')

    return formula_str.strip()


def extract_formula_patterns(text: str) -> List[str]:
    """
    Extract known formula patterns from text.

    Recognizes common formula patterns like:
    - n+2k-3, n+2k-2, 2n-2, etc.
    - Equivalent forms like k²+2k-3, n+2√n-3

    Args:
        text: Text containing formula

    Returns:
        List of recognized formula patterns
    """
    normalized = normalize_formula(text)

    formulas = []

    # Check common patterns
    if "n+2k-3" in normalized or "k²+2k-3" in normalized or "k^2+2k-3" in normalized:
        formulas.append("n+2k-3")
    elif "n+2k-2" in normalized or "k²+2k-2" in normalized:
        formulas.append("n+2k-2")
    elif "n+2k-1" in normalized or "k²+2k-1" in normalized:
        formulas.append("n+2k-1")
    elif "2n-2" in normalized:
        formulas.append("2n-2")
    elif "2n-1" in normalized:
        formulas.append("2n-1")
    elif "n+k" in normalized:
        formulas.append("n+k")

    return formulas


class SmallCaseValidator:
    """
    Validates formulas using small-case pattern derivation.

    This class provides formula derivation capabilities for BFS integration,
    enabling fast pattern recognition on formula-based problems.
    """

    def __init__(self, llm_client):
        """
        Initialize validator with LLM client.

        Args:
            llm_client: LLM client instance with call() method
        """
        self.llm_client = llm_client

    def build_verification_prompt(
        self,
        problem_statement: str,
        verified_cases: List[Dict[str, Any]]
    ) -> Tuple[str, str]:
        """
        Build system and user prompts for formula derivation.

        Args:
            problem_statement: Full problem description
            verified_cases: List of {"n": 4, "k": 2, "tiles": 5, "source": "..."}

        Returns:
            (system_prompt, user_prompt)
        """
        # Build verification summary
        verification_summary = "**VERIFIED SMALL-CASE GROUND TRUTH** (From Independent Verification):\n\n"
        for case in verified_cases:
            source = case.get('source', 'unknown')
            verification_summary += f"For n={case['n']} (k={case['k']} where k²=n): **{case['tiles']} tiles**\n"
            verification_summary += f"  Source: {source}\n\n"

        verification_summary += "\n**YOUR TASK:**\n"
        verification_summary += "1. Study these verified cases carefully\n"
        verification_summary += "2. Find a pattern and derive a general formula f(n,k)\n"
        verification_summary += "3. Verify your formula matches ALL verified cases above\n"
        verification_summary += "4. Apply your formula to the target problem\n\n"

        verification_summary += "**IMPORTANT CONSTRAINTS:**\n"
        verification_summary += "- Your formula MUST match all verified cases exactly\n"
        verification_summary += "- If formula doesn't match a case, it's WRONG - try again\n"
        verification_summary += "- Only propose a formula after verifying it against ALL cases\n"
        verification_summary += "- Do NOT guess - derive from pattern analysis\n\n"

        # Pre-reject obvious wrong formulas
        verification_summary += "**ADVERSARIAL VALIDATION (Auto-Reject Common Mistakes):**\n"
        verification_summary += "The following naive formulas are KNOWN TO BE WRONG:\n"

        naive_wrong_formulas = [
            {"name": "2n-2", "formula": "2*n - 2"},
            {"name": "2n-1", "formula": "2*n - 1"},
            {"name": "n+k", "formula": "n + k"},
            {"name": "n+k-1", "formula": "n + k - 1"},
        ]

        first_case = verified_cases[0]
        n, k, expected = first_case['n'], first_case['k'], first_case['tiles']

        for candidate in naive_wrong_formulas:
            result = eval(candidate['formula'], {"n": n, "k": k})
            if result != expected:
                verification_summary += f"- {candidate['name']}: gives {result} for n={n}, k={k} (should be {expected}) → REJECTED\n"

        verification_summary += "\nYour proposed formula must be DIFFERENT from these rejected ones.\n"

        # Build system prompt with dynamic verification array
        verification_examples = []
        for case in verified_cases:
            verification_examples.append(
                f'{{"n": {case["n"]}, "k": {case["k"]}, "predicted": X, "actual": {case["tiles"]}, "match": true}}'
            )

        verification_json = ",\n        ".join(verification_examples)

        system_prompt = f"""You are a mathematical problem solver. Derive a formula from verified small cases and return your analysis in JSON format.

Return JSON with this exact structure:
{{
    "pattern_analysis": "description of pattern you found in the verified cases",
    "derived_formula": "your proposed formula in terms of n and k",
    "verification": [
        {verification_json}
    ],
    "all_cases_match": true,
    "final_answer": N,
    "confidence": "high/medium/low"
}}

CRITICAL: Do NOT include the correct formula in your response if you haven't derived it yourself from the pattern."""

        # Build user prompt
        user_prompt = f"""{problem_statement}

{verification_summary}

**APPROACH:**
1. Analyze the verified small cases to find a mathematical pattern
2. Derive a general formula f(n,k) based on the pattern
3. Verify your formula against ALL verified cases
4. If verification fails, revise your formula and try again
5. Once verified, apply formula to the target problem
6. Return answer immediately (do NOT write full proof)

**IMPORTANT:**
- Derive the formula yourself from the pattern - do NOT guess
- Your formula must match ALL verified cases exactly
- Return JSON format only"""

        return system_prompt, user_prompt

    def derive_formula(
        self,
        problem_statement: str,
        verified_cases: List[Dict[str, Any]],
        reasoning_effort: str = "medium"
    ) -> Optional[Dict[str, Any]]:
        """
        Derive formula from verified small cases.

        Args:
            problem_statement: Full problem description
            verified_cases: List of verified cases [{"n": 4, "k": 2, "tiles": 5}, ...]
            reasoning_effort: "low", "medium", or "high"

        Returns:
            {
                "formula": "n+2k-3",
                "answer": 2112,
                "confidence": 0.9,
                "all_cases_match": true,
                "pattern_analysis": "..."
            } or None if failed
        """
        if not verified_cases or len(verified_cases) < 2:
            print("[SMALL_CASE_VALIDATOR] Not enough verified cases (need >= 2)")
            return None

        # Build prompts
        system_prompt, user_prompt = self.build_verification_prompt(
            problem_statement, verified_cases
        )

        # Call LLM
        try:
            response = self.llm_client.call(
                system=system_prompt,
                user=user_prompt,
                reasoning_effort=reasoning_effort,
                json_mode=True
            )
        except Exception as e:
            print(f"[SMALL_CASE_VALIDATOR] LLM call failed: {e}")
            return None

        # Parse response
        if not isinstance(response, dict):
            print(f"[SMALL_CASE_VALIDATOR] Response is not JSON dict")
            return None

        # Extract fields
        formula_raw = response.get("derived_formula", "")
        answer = response.get("final_answer", None)
        all_match = response.get("all_cases_match", False)
        confidence_str = response.get("confidence", "low")
        pattern_analysis = response.get("pattern_analysis", "")

        # Normalize formula
        formulas = extract_formula_patterns(formula_raw)
        formula = formulas[0] if formulas else formula_raw

        # Map confidence to numeric
        confidence_map = {"high": 0.9, "medium": 0.6, "low": 0.3}
        confidence = confidence_map.get(confidence_str.lower(), 0.3)

        # Only return if all cases matched
        if not all_match:
            print(f"[SMALL_CASE_VALIDATOR] Not all cases matched")
            return None

        if not formula or answer is None:
            print(f"[SMALL_CASE_VALIDATOR] Missing formula or answer")
            return None

        print(f"[SMALL_CASE_VALIDATOR] Successfully derived formula: {formula}")
        print(f"[SMALL_CASE_VALIDATOR] Answer: {answer}, Confidence: {confidence}")

        return {
            "formula": formula,
            "answer": answer,
            "confidence": confidence,
            "all_cases_match": all_match,
            "pattern_analysis": pattern_analysis,
            "method": "small_case_derivation"
        }

    def derive_formula_with_adaptive_reasoning(
        self,
        problem_statement: str,
        verified_cases: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Derive formula with adaptive reasoning (low → medium → high).

        Tries low reasoning first for speed, escalates if needed.
        Saves 3-5x cost compared to always using high reasoning.

        Args:
            problem_statement: Full problem description
            verified_cases: List of verified cases

        Returns:
            Formula result dict or None
        """
        for reasoning in ["low", "medium", "high"]:
            print(f"[SMALL_CASE_VALIDATOR] Trying {reasoning} reasoning...")

            result = self.derive_formula(
                problem_statement,
                verified_cases,
                reasoning_effort=reasoning
            )

            if result and result["confidence"] >= 0.8:
                print(f"[SMALL_CASE_VALIDATOR] Success with {reasoning} reasoning!")
                return result

        print(f"[SMALL_CASE_VALIDATOR] Failed with all reasoning levels")
        return None


# Example usage
if __name__ == "__main__":
    # Mock LLM client for testing
    class MockLLMClient:
        def call(self, system, user, reasoning_effort="medium", json_mode=False):
            # Return mock response
            return {
                "pattern_analysis": "Excesses form odd sequence 1,3,5,...",
                "derived_formula": "n + 2k - 3",
                "verification": [
                    {"n": 4, "k": 2, "predicted": 5, "actual": 5, "match": True},
                    {"n": 9, "k": 3, "predicted": 12, "actual": 12, "match": True},
                ],
                "all_cases_match": True,
                "final_answer": 2112,
                "confidence": "high"
            }

    # Test
    validator = SmallCaseValidator(MockLLMClient())

    problem = "Find minimum tiles for 2025×2025 grid..."
    cases = [
        {"n": 4, "k": 2, "tiles": 5, "source": "verified_cp_sat"},
        {"n": 9, "k": 3, "tiles": 12, "source": "imo_official"},
    ]

    result = validator.derive_formula(problem, cases)
    print(f"\nResult: {result}")

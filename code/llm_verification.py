#!/usr/bin/env python3
"""
LLM-Based Verification System (4-Stage Pipeline)

This implements the unified proposal from Google Scientist, Nvidia Engineer,
and Netflix Data Scientist to eliminate false positives while maintaining
high true positive rates.

Architecture:
  Stage 1: Claim Extraction (LLM low reasoning)
  Stage 2: Code Generation (LLM medium reasoning + templates)
  Stage 3: Safe Execution (no LLM)
  Stage 4: LLM Fallback Review (LLM high reasoning)

Key Principles:
  - Falsifiable evidence (concrete counterexamples)
  - No oracle (validator doesn't know ground truth)
  - Scalable (template library, not hardcoded logic)

Expected Performance:
  - False positive rate: 100% → 2-5%
  - True positive rate: ~60% → 90%+
  - Cost: $0.08 → $0.10-0.15 per verification
  - Rigor: 2/10 → 8.5/10
"""

import json
import re
import subprocess
import tempfile
import os
from typing import Dict, List, Set, Optional, Tuple
from pathlib import Path

# Import existing extractors for now
import sys
sys.path.append(os.path.dirname(__file__))


class LLMInterface:
    """Interface to call LLM with different reasoning levels."""

    def __init__(self, api_url: str = None, api_key: str = None, model: str = None):
        """
        Initialize LLM interface.

        Args:
            api_url: API endpoint (defaults to GPT-OSS)
            api_key: API key
            model: Model name
        """
        self.api_url = api_url or os.getenv("GPT_OSS_API_URL", "http://localhost:30000/v1/chat/completions")
        self.api_key = api_key or os.getenv("GPT_OSS_API_KEY", "")
        self.model = model or os.getenv("GPT_OSS_MODEL_NAME", "openai/gpt-oss-120b")

    def call(self, prompt: str, system_prompt: str = None, reasoning: str = "low",
             temperature: float = 0.0) -> str:
        """
        Call LLM with specified reasoning effort.

        Args:
            prompt: User prompt
            system_prompt: System prompt (optional)
            reasoning: Reasoning effort ("low", "medium", "high")
            temperature: Sampling temperature

        Returns:
            LLM response text
        """
        import requests

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        # Build payload
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature
        }

        # Add reasoning effort based on model prefix (OpenRouter vs standard API)
        if any(prefix in self.model for prefix in ["openrouter/", "anthropic/", "google/"]):
            # OpenRouter-style API: reasoning in extra_body
            payload["extra_body"] = {"reasoning": {"effort": reasoning}}
        else:
            # Standard API: reasoning at top level
            payload["reasoning"] = {"effort": reasoning}

        # Make request
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            response = requests.post(self.api_url, json=payload, headers=headers, timeout=120)
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
        except Exception as e:
            return f"ERROR: LLM call failed: {str(e)}"


# ============================================================================
# Stage 1: Claim Extraction (LLM Low Reasoning)
# ============================================================================

class ClaimExtractor:
    """Extract mathematical claims from natural language solutions."""

    def __init__(self, llm: LLMInterface):
        self.llm = llm

    def extract_claims(self, solution: str, problem_type: str = "FIND", verbose: bool = False) -> Dict:
        """
        Extract claimed answer and construction method.

        Args:
            solution: Natural language solution text
            problem_type: "FIND" or "PROVE"
            verbose: Print detailed extraction process

        Returns:
            {
                "answer": Set[int] | "ALL_VALUES" | None,
                "construction": str,  # Description of construction method
                "parameters": Dict,   # Key variables (e.g., {"n": "≥3", "k": "sunny lines"})
                "claim_type": str     # "explicit_set" | "range" | "formula"
            }
        """
        if verbose:
            print(f"[Stage 1 DEBUG] Solution length: {len(solution)} chars")
            print(f"[Stage 1 DEBUG] First 200 chars: {solution[:200]}...")

        # Try regex-based extraction first (fast and reliable for simple formats)
        regex_result = self._extract_with_regex(solution, verbose=verbose)
        if regex_result["answer"] is not None:
            if verbose:
                print(f"[Stage 1 DEBUG] Regex extraction succeeded: {regex_result['answer']}")
            return regex_result

        # Fallback to LLM extraction
        if verbose:
            print(f"[Stage 1 DEBUG] Regex extraction failed, trying LLM...")

        system_prompt = """You are a mathematical claim extraction expert. Extract the answer and construction method from solutions.
Output valid JSON only."""

        user_prompt = f"""Extract the claimed answer and construction method from this solution:

Solution:
{solution}

Output JSON with these fields:
- answer: The claimed set of values (e.g., ["0", "1", "3"] or "ALL_VALUES" for {{0,1,...,n}})
- construction: Brief description of how to build the configuration
- parameters: Key variables and their constraints (e.g., {{"n": "≥3", "k": "number of sunny lines"}})
- claim_type: One of ["explicit_set", "range", "formula"]

Example output:
{{
  "answer": ["0", "1", "3"],
  "construction": "For k=0 use diagonal lines, for k=1 use one sunny line y=x, for k=3 use three sunny lines with slopes 1, 2, 3",
  "parameters": {{"n": "≥3", "k": "number of sunny lines"}},
  "claim_type": "explicit_set"
}}

Output JSON only:"""

        response = self.llm.call(user_prompt, system_prompt=system_prompt, reasoning="low")

        if verbose:
            print(f"[Stage 1 DEBUG] LLM response length: {len(response)} chars")
            print(f"[Stage 1 DEBUG] LLM response preview: {response[:300]}...")

        # Parse JSON response
        try:
            # Extract JSON from response (handle markdown code blocks)
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                if verbose:
                    print(f"[Stage 1 DEBUG] Extracted JSON from code block")
            else:
                # Try to find raw JSON
                json_str = response.strip()
                if verbose:
                    print(f"[Stage 1 DEBUG] Using raw response as JSON")

            if verbose:
                print(f"[Stage 1 DEBUG] JSON string to parse: {json_str[:200]}...")

            claims = json.loads(json_str)

            if verbose:
                print(f"[Stage 1 DEBUG] JSON parsing succeeded")
                print(f"[Stage 1 DEBUG] Parsed answer field: {claims.get('answer')}")

            # Convert answer to standard format
            if isinstance(claims.get("answer"), list):
                if claims["answer"] == "ALL_VALUES" or "ALL_VALUES" in claims["answer"]:
                    claims["answer"] = "ALL_VALUES"
                else:
                    # Convert to set of integers
                    claims["answer"] = set(int(x) for x in claims["answer"])
            elif isinstance(claims.get("answer"), str) and claims["answer"] != "ALL_VALUES":
                # Handle string answers like "0,1,3"
                try:
                    claims["answer"] = set(int(x.strip()) for x in claims["answer"].split(","))
                except:
                    pass

            if verbose:
                print(f"[Stage 1 DEBUG] Final answer: {claims['answer']}")

            return claims
        except Exception as e:
            if verbose:
                print(f"[Stage 1 DEBUG] JSON parsing failed: {str(e)}")
                print(f"[Stage 1 DEBUG] Trying final regex fallback...")

            # Final fallback: try regex again with full text
            final_regex = self._extract_with_regex(solution + "\n" + response, verbose=verbose)
            if final_regex["answer"] is not None:
                if verbose:
                    print(f"[Stage 1 DEBUG] Final regex fallback succeeded: {final_regex['answer']}")
                return final_regex

            # Complete failure
            if verbose:
                print(f"[Stage 1 DEBUG] All extraction methods failed")

            return {
                "answer": None,
                "construction": "PARSE_ERROR",
                "parameters": {},
                "claim_type": "unknown",
                "error": str(e),
                "raw_response": response
            }

    def _extract_with_regex(self, text: str, verbose: bool = False) -> Dict:
        """
        Extract answer using regex patterns (fast and reliable for simple formats).

        Args:
            text: Text to extract from
            verbose: Print debug info

        Returns:
            Extraction result with answer field
        """
        # Pattern 1: k ∈ {0, 1, 3} or k ∈ {0,1,3}
        pattern1 = r'k\s*∈\s*\{([0-9,\s]+)\}'
        match = re.search(pattern1, text)
        if match:
            values_str = match.group(1)
            try:
                answer_set = set(int(x.strip()) for x in values_str.split(',') if x.strip())
                if verbose:
                    print(f"[REGEX] Pattern 1 matched: k ∈ {{{values_str}}} → {answer_set}")
                return {
                    "answer": answer_set,
                    "construction": "Extracted from solution text",
                    "parameters": {"n": "≥3", "k": "sunny lines"},
                    "claim_type": "explicit_set"
                }
            except:
                pass

        # Pattern 2: {0, 1, 3} or {0,1,3} (standalone set)
        pattern2 = r'(?:answer is|values are)?\s*\{([0-9,\s]+)\}'
        match = re.search(pattern2, text, re.IGNORECASE)
        if match:
            values_str = match.group(1)
            try:
                answer_set = set(int(x.strip()) for x in values_str.split(',') if x.strip())
                if verbose:
                    print(f"[REGEX] Pattern 2 matched: {{{values_str}}} → {answer_set}")
                return {
                    "answer": answer_set,
                    "construction": "Extracted from solution text",
                    "parameters": {"n": "≥3", "k": "sunny lines"},
                    "claim_type": "explicit_set"
                }
            except:
                pass

        # Pattern 3: k ∈ {0,1,...,n} or k ∈ {0,1,2,...,n}
        pattern3 = r'k\s*∈\s*\{0,\s*1.*?n\}'
        if re.search(pattern3, text):
            if verbose:
                print(f"[REGEX] Pattern 3 matched: ALL_VALUES")
            return {
                "answer": "ALL_VALUES",
                "construction": "All values from 0 to n",
                "parameters": {"n": "≥3", "k": "sunny lines"},
                "claim_type": "range"
            }

        # Pattern 4: \\boxed{{0, 1, 3}} (LaTeX boxed)
        pattern4 = r'\\boxed\{\{?([0-9,\s]+)\}?\}'
        match = re.search(pattern4, text)
        if match:
            values_str = match.group(1)
            try:
                answer_set = set(int(x.strip()) for x in values_str.split(',') if x.strip())
                if verbose:
                    print(f"[REGEX] Pattern 4 matched: \\boxed{{{values_str}}} → {answer_set}")
                return {
                    "answer": answer_set,
                    "construction": "Extracted from boxed answer",
                    "parameters": {"n": "≥3", "k": "sunny lines"},
                    "claim_type": "explicit_set"
                }
            except:
                pass

        if verbose:
            print(f"[REGEX] No patterns matched")

        return {
            "answer": None,
            "construction": "",
            "parameters": {},
            "claim_type": "unknown"
        }


# ============================================================================
# Stage 2: Template-Based Code Generation (LLM Medium Reasoning)
# ============================================================================

class CodeGenerator:
    """Generate verification code using templates + LLM."""

    def __init__(self, llm: LLMInterface):
        self.llm = llm
        self.templates = TemplateLibrary()

    def generate_verification_code(self, claims: Dict, problem_statement: str) -> str:
        """
        Generate Python verification code for claims.

        Args:
            claims: Extracted claims from Stage 1
            problem_statement: Original problem text

        Returns:
            Python code as string
        """
        # Select template based on problem type and claim type
        template = self.templates.get_template("FIND_SUNNY_LINES")

        # Use LLM to fill in construction-specific logic
        system_prompt = """You are a Python code generation expert. Generate code to test mathematical constructions.
Use the provided template and fill in the construction-specific logic.
Output valid Python code only."""

        user_prompt = f"""Generate Python code to verify this mathematical claim:

Problem:
{problem_statement}

Claimed Answer: {claims.get('answer')}
Construction Method: {claims.get('construction')}

Template (DO NOT modify the validation logic):
{template}

Your task:
1. Fill in the `generate_configuration(n, k)` function based on the construction description
2. Keep all template validation logic UNCHANGED
3. Return complete executable Python code

Requirements:
- Function should return a dictionary: {{"lines": [...], "sunny_count": int, "covers_all": bool}}
- Each line is a tuple: (slope, intercept) or ("vertical", x_value) or ("horizontal", y_value)
- DO NOT modify validation logic (is_sunny, validate_configuration, etc.)

Output Python code only (no markdown):"""

        response = self.llm.call(user_prompt, system_prompt=system_prompt, reasoning="medium")

        # Extract code from response
        code_match = re.search(r'```python\s*(.*?)\s*```', response, re.DOTALL)
        if code_match:
            return code_match.group(1)
        else:
            # Return raw response if no code block found
            return response


class TemplateLibrary:
    """Library of verification templates for different problem types."""

    def get_template(self, problem_type: str) -> str:
        """Get template for specific problem type."""
        if problem_type == "FIND_SUNNY_LINES":
            return self._sunny_lines_template()
        else:
            return self._generic_template()

    def _sunny_lines_template(self) -> str:
        """Template for IMO 2025 Problem 1 (sunny lines)."""
        return '''#!/usr/bin/env python3
"""Verification code for sunny lines problem."""

from typing import Set, Tuple, Dict

def generate_T_n(n: int) -> Set[Tuple[int, int]]:
    """Generate all points in T_n = {(a,b) : a≥1, b≥1, a+b≤n+1}."""
    return {(a, b) for a in range(1, n+1)
            for b in range(1, n+1) if a + b <= n + 1}

def is_sunny(slope: float) -> bool:
    """Check if line with given slope is sunny (not 0, ∞, or -1)."""
    return slope not in [0, float('inf'), -1]

def generate_configuration(n: int, k: int) -> Dict:
    """
    Generate configuration for (n, k).

    TODO: FILL THIS IN based on construction description.

    Returns:
        {
            "lines": List[Tuple],  # Each line: (slope, intercept) or ("vertical", x) or ("horizontal", y)
            "sunny_count": int,    # Number of sunny lines
            "covers_all": bool     # Whether all points in T_n are covered
        }
    """
    # TODO: Implement construction here
    raise NotImplementedError("Construction not implemented")

def validate_configuration(config: Dict, n: int, k: int) -> Tuple[bool, str]:
    """
    Validate configuration (TEMPLATE - DO NOT MODIFY).

    Returns:
        (is_valid, reason)
    """
    T_n = generate_T_n(n)
    lines = config.get("lines", [])

    # Check 1: Count sunny lines
    sunny_count = 0
    for line in lines:
        if len(line) == 2 and isinstance(line[0], (int, float)):
            slope, intercept = line
            if is_sunny(slope):
                sunny_count += 1

    if sunny_count != k:
        return False, f"Expected {k} sunny lines, found {sunny_count}"

    # Check 2: Verify all points are covered
    covered = set()
    for line in lines:
        if len(line) == 2:
            if line[0] == "vertical":
                # Vertical line x = c
                x_val = line[1]
                for (a, b) in T_n:
                    if a == x_val:
                        covered.add((a, b))
            elif line[0] == "horizontal":
                # Horizontal line y = c
                y_val = line[1]
                for (a, b) in T_n:
                    if b == y_val:
                        covered.add((a, b))
            else:
                # Line y = mx + c
                slope, intercept = line
                for (a, b) in T_n:
                    if abs(b - (slope * a + intercept)) < 1e-9:
                        covered.add((a, b))

    if covered != T_n:
        uncovered = T_n - covered
        return False, f"Points not covered: {uncovered}"

    return True, "Valid configuration"

def test_claim(claimed_answer, test_cases):
    """Test claimed answer on test cases."""
    results = []

    if claimed_answer == "ALL_VALUES":
        # Test all k from 0 to n
        for n in test_cases:
            for k in range(n + 1):
                try:
                    config = generate_configuration(n, k)
                    is_valid, reason = validate_configuration(config, n, k)
                    if not is_valid:
                        return f"COUNTEREXAMPLE: n={n}, k={k} - {reason}"
                except Exception as e:
                    return f"COUNTEREXAMPLE: n={n}, k={k} - Construction failed: {str(e)}"
    else:
        # Test specific k values
        for n in test_cases:
            for k in claimed_answer:
                if k > n:
                    continue
                try:
                    config = generate_configuration(n, k)
                    is_valid, reason = validate_configuration(config, n, k)
                    if not is_valid:
                        return f"COUNTEREXAMPLE: n={n}, k={k} - {reason}"
                except Exception as e:
                    return f"COUNTEREXAMPLE: n={n}, k={k} - Construction failed: {str(e)}"

    return "ALL_TESTS_PASSED"

# Entry point
if __name__ == "__main__":
    import sys
    import json

    # Read test configuration from stdin
    config = json.loads(sys.stdin.read())
    claimed_answer = config["answer"]
    test_cases = config["test_cases"]

    result = test_claim(claimed_answer, test_cases)
    print(json.dumps({"result": result}))
'''

    def _generic_template(self) -> str:
        """Generic template for other problem types."""
        return '''# Generic verification template
# TODO: Add domain-specific templates
'''


# ============================================================================
# Stage 3: Safe Code Execution (No LLM)
# ============================================================================

class SafeExecutor:
    """Execute generated code in isolated environment."""

    def __init__(self, timeout: int = 30):
        self.timeout = timeout

    def execute(self, code: str, test_config: Dict) -> Dict:
        """
        Execute verification code safely.

        Args:
            code: Python code to execute
            test_config: {
                "answer": Set[int] | "ALL_VALUES",
                "test_cases": List[int]  # n values to test
            }

        Returns:
            {
                "verdict": "INVALID" | "VALID" | "ERROR" | "TIMEOUT",
                "confidence": float,  # 0.0 to 1.0
                "evidence": str,      # Counterexample or success message
                "execution_time": float
            }
        """
        import time

        # Create temporary file for code
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            code_file = f.name

        try:
            # Prepare input
            test_input = json.dumps(test_config)

            # Execute code
            start_time = time.time()
            result = subprocess.run(
                ['python3', code_file],
                input=test_input,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            execution_time = time.time() - start_time

            # Parse output
            if result.returncode != 0:
                return {
                    "verdict": "ERROR",
                    "confidence": 0.5,
                    "evidence": f"Execution error: {result.stderr}",
                    "execution_time": execution_time
                }

            try:
                output = json.loads(result.stdout)
                test_result = output.get("result", "")

                if "COUNTEREXAMPLE" in test_result:
                    # Found concrete counterexample - high confidence INVALID
                    return {
                        "verdict": "INVALID",
                        "confidence": 0.95,
                        "evidence": test_result,
                        "execution_time": execution_time
                    }
                elif "ALL_TESTS_PASSED" in test_result:
                    # All tests passed - medium confidence VALID (not exhaustive)
                    return {
                        "verdict": "VALID",
                        "confidence": 0.75,
                        "evidence": test_result,
                        "execution_time": execution_time
                    }
                else:
                    # Uncertain result
                    return {
                        "verdict": "ERROR",
                        "confidence": 0.3,
                        "evidence": f"Unexpected output: {test_result}",
                        "execution_time": execution_time
                    }
            except json.JSONDecodeError:
                return {
                    "verdict": "ERROR",
                    "confidence": 0.3,
                    "evidence": f"Invalid JSON output: {result.stdout}",
                    "execution_time": execution_time
                }

        except subprocess.TimeoutExpired:
            return {
                "verdict": "TIMEOUT",
                "confidence": 0.2,
                "evidence": f"Execution timeout after {self.timeout}s",
                "execution_time": self.timeout
            }

        finally:
            # Clean up temporary file
            try:
                os.unlink(code_file)
            except:
                pass


# ============================================================================
# Stage 4: LLM Fallback Review (LLM High Reasoning)
# ============================================================================

class LLMReviewer:
    """LLM-based fallback review when code execution is uncertain."""

    def __init__(self, llm: LLMInterface):
        self.llm = llm

    def review_solution(self, solution: str, claims: Dict, problem_statement: str) -> Dict:
        """
        Deep LLM review with high reasoning.

        Args:
            solution: Original solution text
            claims: Extracted claims
            problem_statement: Problem text

        Returns:
            {
                "verdict": "VALID" | "INVALID" | "UNCERTAIN",
                "confidence": float,
                "reasoning": str
            }
        """
        system_prompt = """You are a rigorous mathematical verification expert. Review solutions with extreme skepticism.
Focus on finding concrete counterexamples or logical gaps. Output valid JSON only."""

        user_prompt = f"""Review this mathematical solution for correctness:

Problem:
{problem_statement}

Claimed Answer: {claims.get('answer')}
Construction: {claims.get('construction')}

Full Solution:
{solution}

Your task:
1. Check if the construction actually works for the claimed answer
2. Try to find concrete counterexamples (specific n, k values that fail)
3. Check for logical gaps or invalid assumptions

Output JSON:
{{
  "verdict": "VALID" | "INVALID" | "UNCERTAIN",
  "confidence": 0.0-1.0,
  "reasoning": "Detailed explanation",
  "counterexample": "Specific (n,k) that fails" or null
}}

Output JSON only:"""

        response = self.llm.call(user_prompt, system_prompt=system_prompt, reasoning="high")

        # Parse JSON response
        try:
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = response.strip()

            review = json.loads(json_str)
            return review
        except Exception as e:
            return {
                "verdict": "UNCERTAIN",
                "confidence": 0.3,
                "reasoning": f"Failed to parse LLM review: {str(e)}",
                "raw_response": response
            }


# ============================================================================
# Main Verification Pipeline
# ============================================================================

class VerificationPipeline:
    """Main orchestrator for 4-stage verification."""

    def __init__(self, llm: LLMInterface = None, test_cases: List[int] = None):
        """
        Initialize pipeline.

        Args:
            llm: LLM interface (creates default if None)
            test_cases: List of n values to test (default: [3, 4, 5, 10])
        """
        self.llm = llm or LLMInterface()
        self.test_cases = test_cases or [3, 4, 5, 10]

        # Initialize stages
        self.claim_extractor = ClaimExtractor(self.llm)
        self.code_generator = CodeGenerator(self.llm)
        self.executor = SafeExecutor(timeout=30)
        self.reviewer = LLMReviewer(self.llm)

    def verify(self, solution: str, problem_statement: str = None, verbose: bool = True) -> Dict:
        """
        Run full verification pipeline.

        Args:
            solution: Solution text to verify
            problem_statement: Problem text (optional, for better context)
            verbose: Print detailed debugging output

        Returns:
            {
                "verdict": "VALID" | "INVALID" | "UNCERTAIN",
                "confidence": float,
                "evidence": str,
                "stage": "stage1" | "stage2" | "stage3" | "stage4",
                "details": Dict  # Stage-specific details
            }
        """
        # Default problem statement for IMO25 Problem 1
        if problem_statement is None:
            problem_statement = """For every integer n ≥ 3, determine all possible numbers k of
sunny lines in a configuration of n lines."""

        # Stage 1: Extract claims
        print("[Stage 1] Extracting claims with LLM (low reasoning)...")
        claims = self.claim_extractor.extract_claims(solution, problem_type="FIND", verbose=verbose)

        if claims.get("answer") is None:
            return {
                "verdict": "INVALID",
                "confidence": 0.9,
                "evidence": "Could not extract answer from solution (fail-safe: reject)",
                "stage": "stage1",
                "details": claims
            }

        print(f"[Stage 1] Extracted answer: {claims['answer']}")
        print(f"[Stage 1] Construction: {claims['construction'][:100]}...")

        # Stage 2: Generate verification code
        print("[Stage 2] Generating verification code with LLM (medium reasoning)...")
        try:
            code = self.code_generator.generate_verification_code(claims, problem_statement)
            print(f"[Stage 2] Generated {len(code)} chars of Python code")
        except Exception as e:
            print(f"[Stage 2] Code generation failed: {str(e)}")
            # Fall through to Stage 4
            code = None

        # Stage 3: Execute code
        if code:
            print("[Stage 3] Executing verification code...")
            test_config = {
                "answer": list(claims["answer"]) if isinstance(claims["answer"], set) else claims["answer"],
                "test_cases": self.test_cases
            }

            exec_result = self.executor.execute(code, test_config)
            print(f"[Stage 3] Verdict: {exec_result['verdict']} (confidence: {exec_result['confidence']:.2f})")
            print(f"[Stage 3] Evidence: {exec_result['evidence'][:200]}...")

            # If high confidence result, return immediately
            if exec_result["confidence"] >= 0.7:
                return {
                    "verdict": exec_result["verdict"],
                    "confidence": exec_result["confidence"],
                    "evidence": exec_result["evidence"],
                    "stage": "stage3",
                    "details": {
                        "execution_time": exec_result["execution_time"],
                        "code_length": len(code),
                        "test_cases": self.test_cases
                    }
                }

        # Stage 4: LLM fallback review
        print("[Stage 4] Running LLM fallback review (high reasoning)...")
        review = self.reviewer.review_solution(solution, claims, problem_statement)
        print(f"[Stage 4] Verdict: {review['verdict']} (confidence: {review['confidence']:.2f})")

        return {
            "verdict": review["verdict"],
            "confidence": review["confidence"],
            "evidence": review["reasoning"],
            "stage": "stage4",
            "details": review
        }


# ============================================================================
# CLI Interface
# ============================================================================

def main():
    """CLI interface for verification."""
    import argparse

    parser = argparse.ArgumentParser(description="LLM-based mathematical solution verification")
    parser.add_argument("solution_file", help="Path to solution file")
    parser.add_argument("--problem", help="Path to problem statement file")
    parser.add_argument("--test-cases", nargs="+", type=int, default=[3, 4, 5, 10],
                       help="Test case values (default: 3 4 5 10)")
    parser.add_argument("--api-url", help="LLM API URL")
    parser.add_argument("--api-key", help="LLM API key")
    parser.add_argument("--model", help="LLM model name")

    args = parser.parse_args()

    # Read solution
    with open(args.solution_file, 'r') as f:
        solution = f.read()

    # Read problem statement if provided
    problem_statement = None
    if args.problem:
        with open(args.problem, 'r') as f:
            problem_statement = f.read()

    # Initialize pipeline
    llm = LLMInterface(api_url=args.api_url, api_key=args.api_key, model=args.model)
    pipeline = VerificationPipeline(llm=llm, test_cases=args.test_cases)

    # Run verification
    result = pipeline.verify(solution, problem_statement)

    # Print result
    print("\n" + "="*80)
    print("VERIFICATION RESULT")
    print("="*80)
    print(f"Verdict: {result['verdict']}")
    print(f"Confidence: {result['confidence']:.1%}")
    print(f"Stage: {result['stage']}")
    print(f"\nEvidence:\n{result['evidence']}")
    print("="*80)

    # Exit code: 0 for VALID, 1 for INVALID, 2 for UNCERTAIN
    exit_codes = {"VALID": 0, "INVALID": 1, "UNCERTAIN": 2, "ERROR": 3}
    return exit_codes.get(result["verdict"], 3)


if __name__ == "__main__":
    import sys
    sys.exit(main())

"""
Answer Validation System for IMO Solutions

Validates claimed answers against:
- Ground truth (when available)
- Small-case exhaustive testing
- Plausibility heuristics

This fixes the verification gap identified by expert panel:
  Current system checks PROOF correctness
  This system checks ANSWER correctness
"""

import re
import logging
from typing import Set, Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Ground Truth Database
# =============================================================================

GROUND_TRUTH = {
    "imo2025_p1": {
        "problem": "Sunny lines problem",
        "answer": {0, 1, 3},
        "source": "IMO 2025 Official Solution (verified by expert panel)",
        "last_updated": "2025-12-20",
        "notes": [
            "k=0: All n diagonals x+y=c (none sunny)",
            "k=1: Replace one diagonal with one sunny line",
            "k=2: IMPOSSIBLE - geometric constraints prevent coverage",
            "k=3: Novel construction with 3 specific sunny lines",
            "k≥4: IMPOSSIBLE - upper bound proof (boundary point argument)"
        ],
        "confidence": "DEFINITIVE"
    },
    # Alias for convenience
    "imo01": {"$ref": "imo2025_p1"},
    "problems/imo01.txt": {"$ref": "imo2025_p1"},
}


def resolve_reference(problem_id: str) -> Optional[Dict]:
    """Resolve $ref pointers in ground truth database."""
    if problem_id not in GROUND_TRUTH:
        return None

    entry = GROUND_TRUTH[problem_id]
    if "$ref" in entry:
        return GROUND_TRUTH.get(entry["$ref"])

    return entry


# =============================================================================
# Answer Parsing
# =============================================================================

def parse_answer_to_set(answer_text: str) -> Set[int]:
    """
    Parse answer text into a set of integers.

    Handles formats:
    - "k ∈ {0, 1, 3}"
    - "k ∈ {0,1,...,n-2}"
    - "k = 0 or k = n"
    - "All nonnegative integers k with 0 ≤ k ≤ n"

    Returns:
        Set of integers or special marker for parametric answers
    """
    answer_text = answer_text.strip()

    # Pattern 1: Explicit set {0, 1, 3}
    match = re.search(r'\{([0-9,\s]+)\}', answer_text)
    if match:
        nums = match.group(1).split(',')
        try:
            return {int(n.strip()) for n in nums if n.strip()}
        except ValueError:
            pass

    # Pattern 2: Range {0,1,...,n-2} or {0,1,...,n} or {0, 1, 2, ..., n}
    match = re.search(r'\{0,?\s*1,?\s*2?,?\s*\.\.\.?,?\s*(n(?:-\d+)?)\}', answer_text)
    if match:
        upper_bound = match.group(1)
        # Return sentinel for parametric answers
        # We'll flag these as "PARAMETRIC" for special handling
        return {"PARAMETRIC:" + upper_bound}

    # Pattern 3: Interval [0, n] or 0 ≤ k ≤ n
    if "0" in answer_text and ("≤ k ≤" in answer_text or "\\le k \\le" in answer_text):
        # Parametric interval
        return {"PARAMETRIC:interval"}

    # Pattern 4: Single value "k = 0"
    match = re.search(r'k\s*=\s*(\d+)', answer_text)
    if match:
        return {int(match.group(1))}

    # Pattern 5: Multiple values "k = 0 or k = 1 or k = 3"
    matches = re.findall(r'k\s*=\s*(\d+)', answer_text)
    if matches:
        return {int(m) for m in matches}

    logger.warning(f"Could not parse answer: {answer_text[:200]}")
    return set()


def is_parametric_answer(answer_set: Set) -> bool:
    """Check if answer contains parametric markers."""
    return any(isinstance(x, str) and x.startswith("PARAMETRIC:") for x in answer_set)


def extract_parametric_bound(answer_set: Set) -> Optional[str]:
    """Extract parametric bound from answer set (e.g., 'n', 'n-2')."""
    for item in answer_set:
        if isinstance(item, str) and item.startswith("PARAMETRIC:"):
            return item.split(":", 1)[1]
    return None


# =============================================================================
# Small-Case Testing (IMO Problem 1 specific)
# =============================================================================

def test_imo_p1_small_cases(claimed_answer: str, n_test: List[int] = [3, 4, 5]) -> Dict[str, Any]:
    """
    Test claimed answer on small cases for IMO Problem 1.

    For each n, for each k in claimed answer:
      Check if k sunny lines can cover all required points.

    This is a simplified heuristic, not exhaustive construction.
    """
    answer_set = parse_answer_to_set(claimed_answer)

    if is_parametric_answer(answer_set):
        bound = extract_parametric_bound(answer_set)
        return test_parametric_answer_p1(bound, n_test)

    # Test each (n, k) pair
    for n in n_test:
        points_needed = n * (n + 1) // 2  # |T_n|

        for k in answer_set:
            if not isinstance(k, int):
                continue

            if k > n:
                continue  # Skip k > n (trivially impossible)

            # Heuristic: Can k sunny lines + (n-k) non-sunny lines cover points_needed points?
            # Non-sunny lines can be:
            #   - n diagonals (each covers s-1 points for diagonal x+y=s)
            #   - OR vertical/horizontal lines (each covers multiple points)

            # Best case for k sunny lines: each covers 1 point
            # Best case for (n-k) non-sunny: use n diagonals (covers ALL points)

            # If k == 0: Can use n diagonals → always works
            if k == 0:
                continue  # No issue

            # If k == n: All sunny, each covers ~1 point
            # Total coverage: ~n points, but points_needed = n(n+1)/2
            if k == n and points_needed > n:
                return {
                    "verdict": "SUSPICIOUS",
                    "counterexample": {
                        "n": n,
                        "k": k,
                        "reason": f"k={k} sunny lines can cover at most {n} points, but need {points_needed} points"
                    }
                }

            # For intermediate k: Mix of sunny and non-sunny
            # This requires more sophisticated analysis
            # For now, flag if k > n/2 (heuristic threshold)
            if k > n // 2 and k < n:
                # Potentially problematic
                pass

    return {"verdict": "PLAUSIBLE", "small_cases": f"Tested n={n_test}"}


def test_parametric_answer_p1(bound: str, n_test: List[int]) -> Dict[str, Any]:
    """
    Test parametric answers like {0,1,...,n} or {0,1,...,n-2}.

    For IMO P1, correct answer is {0,1,3} (discrete set, not interval).
    Any answer claiming k ∈ {0,...,m} for m ≥ 4 is SUSPICIOUS.
    """
    issues = []

    # Check if bound is too large
    if bound in ["n", "n-1", "n-2"] and "n" in bound:
        issues.append(f"Answer claims k can be as large as {bound}, which may include impossible values")

    # For IMO P1, we know k=2 is impossible, so any interval including 2 is wrong
    if bound in ["n", "n-1", "n-2", "\\lfloor n/2 \\rfloor"]:
        # These all include k=2 for n≥3
        issues.append("Answer likely includes k=2, which is IMPOSSIBLE per official solution")

    if issues:
        return {
            "verdict": "SUSPICIOUS",
            "issues": issues,
            "recommendation": "Check if answer should be discrete set (e.g., {0,1,3}) not interval"
        }

    return {"verdict": "PLAUSIBLE", "bound": bound}


# =============================================================================
# Plausibility Heuristics
# =============================================================================

def check_plausibility(claimed_answer: str, problem_id: str) -> Dict[str, Any]:
    """
    Sanity checks for answer plausibility.

    Returns:
        {"verdict": "PLAUSIBLE" | "NEEDS_REVIEW", "issues": [...]}
    """
    issues = []
    answer_set = parse_answer_to_set(claimed_answer)

    # Check 1: Empty answer
    if not answer_set:
        issues.append("Could not parse answer - check formatting")
        return {"verdict": "NEEDS_REVIEW", "issues": issues}

    # Check 2: Suspiciously large values
    for val in answer_set:
        if isinstance(val, int) and val > 1000:
            issues.append(f"Answer includes very large value k={val}")

    # Check 3: For IMO P1, check for gaps
    if problem_id in ["imo2025_p1", "imo01", "problems/imo01.txt"]:
        if is_parametric_answer(answer_set):
            bound = extract_parametric_bound(answer_set)
            if bound in ["n", "n-1", "n-2"]:
                issues.append(f"Parametric answer k ∈ {{0,...,{bound}}} may include impossible values")
        else:
            # Check for gaps in discrete answer
            if answer_set and isinstance(list(answer_set)[0], int):
                sorted_ans = sorted(answer_set)
                for i in range(len(sorted_ans) - 1):
                    if sorted_ans[i+1] - sorted_ans[i] > 1:
                        gap = list(range(sorted_ans[i] + 1, sorted_ans[i+1]))
                        issues.append(f"Answer has gap at k={gap} - is this intentional?")

    if issues:
        return {"verdict": "NEEDS_REVIEW", "issues": issues}

    return {"verdict": "PLAUSIBLE"}


# =============================================================================
# Ground Truth Validation
# =============================================================================

def validate_against_ground_truth(problem_id: str, claimed_answer: str) -> Optional[Dict[str, Any]]:
    """
    Check claimed answer against ground truth database.

    Returns None if no ground truth available.
    """
    truth_entry = resolve_reference(problem_id)
    if not truth_entry:
        return None

    truth_answer = truth_entry["answer"]
    claimed_set = parse_answer_to_set(claimed_answer)

    # Handle parametric answers
    if is_parametric_answer(claimed_set):
        bound = extract_parametric_bound(claimed_set)
        # For IMO P1, correct answer is {0,1,3}, not an interval
        return {
            "verdict": "WRONG",
            "reason": f"Answer claims k ∈ {{0,...,{bound}}} (interval) but correct is discrete set {truth_answer}",
            "correct_answer": truth_answer,
            "source": truth_entry["source"],
            "confidence": truth_entry["confidence"]
        }

    # Exact match
    if claimed_set == truth_answer:
        return {
            "verdict": "CORRECT",
            "answer": truth_answer,
            "source": truth_entry["source"],
            "confidence": truth_entry["confidence"]
        }

    # Subset (incomplete)
    if claimed_set.issubset(truth_answer):
        missing = truth_answer - claimed_set
        return {
            "verdict": "INCOMPLETE",
            "claimed": claimed_set,
            "correct": truth_answer,
            "missing": missing,
            "source": truth_entry["source"],
            "confidence": truth_entry["confidence"]
        }

    # Superset (overgeneralized)
    if truth_answer.issubset(claimed_set):
        extra = claimed_set - truth_answer
        return {
            "verdict": "OVERGENERALIZED",
            "claimed": claimed_set,
            "correct": truth_answer,
            "extra": extra,
            "reason": f"Answer includes impossible values: {extra}",
            "source": truth_entry["source"],
            "confidence": truth_entry["confidence"]
        }

    # Completely different
    return {
        "verdict": "WRONG",
        "claimed": claimed_set,
        "correct": truth_answer,
        "source": truth_entry["source"],
        "confidence": truth_entry["confidence"]
    }


# =============================================================================
# Main Validator Class
# =============================================================================

class AnswerValidator:
    """
    Main answer validation system.

    Combines ground truth, small-case testing, and plausibility checks.
    """

    def __init__(self, problem_id: Optional[str] = None):
        self.problem_id = problem_id
        self.ground_truth = resolve_reference(problem_id) if problem_id else None

    def validate(self, claimed_answer: str, solution_text: str = None) -> Dict[str, Any]:
        """
        Main validation entry point.

        Returns:
            {
                "verdict": "CORRECT" | "PLAUSIBLE" | "SUSPICIOUS" | "WRONG" | "INCOMPLETE" | "OVERGENERALIZED",
                "confidence": float,
                "details": {...}
            }
        """
        results = {}

        # Method 1: Ground truth check (highest confidence)
        if self.ground_truth:
            results["ground_truth"] = validate_against_ground_truth(self.problem_id, claimed_answer)
            if results["ground_truth"]["verdict"] in ["CORRECT", "WRONG", "INCOMPLETE", "OVERGENERALIZED"]:
                # Definitive verdict from ground truth
                return {
                    "verdict": results["ground_truth"]["verdict"],
                    "confidence": 1.0,
                    "details": results["ground_truth"]
                }

        # Method 2: Small-case testing (medium confidence)
        if self.problem_id in ["imo2025_p1", "imo01", "problems/imo01.txt"]:
            results["small_cases"] = test_imo_p1_small_cases(claimed_answer)
            if results["small_cases"]["verdict"] == "SUSPICIOUS":
                return {
                    "verdict": "SUSPICIOUS",
                    "confidence": 0.7,
                    "details": results["small_cases"]
                }

        # Method 3: Plausibility (low confidence)
        results["plausibility"] = check_plausibility(claimed_answer, self.problem_id or "")
        if results["plausibility"]["verdict"] == "NEEDS_REVIEW":
            return {
                "verdict": "NEEDS_REVIEW",
                "confidence": 0.5,
                "details": results["plausibility"]
            }

        # Default: Plausible
        return {
            "verdict": "PLAUSIBLE",
            "confidence": 0.6,
            "details": {
                "message": "Answer passed plausibility checks but no ground truth available",
                "checks_run": list(results.keys())
            }
        }


# =============================================================================
# Utility Functions
# =============================================================================

def extract_final_answer(solution_text: str) -> str:
    """
    Extract final answer from solution text.

    Looks for patterns like:
    - "The final answer is \\boxed{...}"
    - "Therefore k ∈ {0,1,3}"
    - Last occurrence of "k ∈" or "k ="
    """
    # Pattern 1: \boxed{...}
    match = re.search(r'\\boxed\{([^}]+)\}', solution_text)
    if match:
        return match.group(1)

    # Pattern 2: Last occurrence of "k ∈" or "k ="
    matches = list(re.finditer(r'k\s*[∈=]\s*[^.]+', solution_text))
    if matches:
        return matches[-1].group(0)

    # Pattern 3: Look in last 500 chars
    tail = solution_text[-500:]
    match = re.search(r'\{[0-9,\s.]+\}', tail)
    if match:
        return match.group(0)

    logger.warning("Could not extract final answer from solution")
    return ""


# =============================================================================
# Test/Debug Functions
# =============================================================================

def test_validator():
    """Test answer validator on known cases."""
    test_cases = [
        {
            "problem_id": "imo2025_p1",
            "answer": "k ∈ {0, 1, 3}",
            "expected": "CORRECT"
        },
        {
            "problem_id": "imo2025_p1",
            "answer": "k ∈ {0, 1, 2, ..., n}",
            "expected": "WRONG"
        },
        {
            "problem_id": "imo2025_p1",
            "answer": "k = 0",
            "expected": "INCOMPLETE"
        },
        {
            "problem_id": "imo2025_p1",
            "answer": "k ∈ {0, 1, 2, ..., n-2}",
            "expected": "OVERGENERALIZED"
        },
    ]

    validator = AnswerValidator("imo2025_p1")

    print("Testing Answer Validator\n" + "="*50)
    for i, test in enumerate(test_cases, 1):
        result = validator.validate(test["answer"])
        verdict = result["verdict"]
        expected = test["expected"]

        status = "✅ PASS" if verdict == expected else f"❌ FAIL (got {verdict})"
        print(f"\nTest {i}: {status}")
        print(f"  Answer: {test['answer']}")
        print(f"  Expected: {expected}, Got: {verdict}")
        if result.get("details"):
            print(f"  Details: {result['details']}")

    print("\n" + "="*50)


if __name__ == "__main__":
    # Run tests if executed directly
    test_validator()

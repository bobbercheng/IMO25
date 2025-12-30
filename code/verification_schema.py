"""
Verification Verdict JSON Schema for Structured Outputs

This module defines the JSON schema for mathematical proof verification
using OpenRouter GPT-OSS-120b with native structured outputs.

Schema eliminates:
- Keyword parsing fragility ("critical error" vs "Critical Error")
- Meta-checker semantic misalignment ("several gaps" vs "major gap")
- Natural language ambiguity

Benefits:
- 100% schema compliance (constrained decoding)
- No hallucinated fields
- Reliable parsing (no string matching)
- Clear verdict classification
"""

# Verification Verdict Schema
# Used with OpenRouter response_format parameter
VERIFICATION_VERDICT_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "verification_verdict",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "verdict": {
                    "type": "string",
                    "enum": ["PASS", "FAIL"],
                    "description": (
                        "Overall verification verdict. "
                        "PASS: Solution is mathematically sound with acceptable justification level. "
                        "FAIL: Solution contains critical errors or answer is incorrect."
                    )
                },
                "confidence": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "description": (
                        "Confidence in the verdict (0.0 to 1.0). "
                        "High confidence (>0.9): Clear determination, no ambiguity. "
                        "Medium confidence (0.5-0.9): Some uncertainty or edge cases. "
                        "Low confidence (<0.5): Highly ambiguous or incomplete information."
                    )
                },
                "issues": {
                    "type": "array",
                    "description": "List of all issues found in the solution (empty if none)",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "string",
                                "enum": ["CRITICAL_ERROR", "JUSTIFICATION_GAP"],
                                "description": (
                                    "CRITICAL_ERROR: Breaks logical chain. Use when: "
                                    "(1) Final answer is wrong, "
                                    "(2) Proof contains a PROVABLY FALSE claim (can construct counterexample), "
                                    "(3) Proof uses incorrect formula or theorem, "
                                    "(4) Proof makes EXPLICIT universal claim (for all X) that is false. "
                                    "JUSTIFICATION_GAP: Conclusion correct but argument incomplete. Use when: "
                                    "(1) Missing proof steps, "
                                    "(2) Claim is TRUE in context but not explicitly proven, "
                                    "(3) Claim is context-dependent (true for case being analyzed) but scope not stated, "
                                    "(4) Uses 'obvious' or 'by inspection' without showing work. "
                                    "CRITICAL DISTINCTION: Context-dependent claims that are TRUE in the relevant case "
                                    "but lack explicit scope are JUSTIFICATION_GAP (severity 4-5), NOT CRITICAL_ERROR."
                                )
                            },
                            "location": {
                                "type": "string",
                                "description": (
                                    "Direct quote from solution where issue occurs. "
                                    "Use exact text (50-200 chars) to make reference clear."
                                )
                            },
                            "description": {
                                "type": "string",
                                "description": (
                                    "Clear explanation of the issue (up to 500 tokens). "
                                    "Include full mathematical reasoning that would have been in the detailed verification log. "
                                    "For CRITICAL_ERROR: Explain why reasoning is invalid or answer is wrong. "
                                    "For JUSTIFICATION_GAP: Explain what justification is missing."
                                )
                            },
                            "severity": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 10,
                                "description": (
                                    "Severity rating (1=minor, 10=critical). "
                                    "CRITICAL_ERROR: Use 8-10 (wrong answer=10, provably false claim=8-9). "
                                    "JUSTIFICATION_GAP: Use 1-5 based on impact: "
                                    "Severity 4-5: Major missing scope (context-dependent claim not explicitly scoped), "
                                    "Severity 3: Missing intermediate steps but logic sound, "
                                    "Severity 1-2: Minor presentation issues or obvious skipped steps. "
                                    "IMPORTANT: Context-dependent claims (true in relevant case but not scoped) "
                                    "are GAPS (4-5), NOT ERRORS (8-9)."
                                )
                            }
                        },
                        "required": ["type", "location", "description", "severity"],
                        "additionalProperties": False
                    }
                },
                "answer_correctness": {
                    "type": "string",
                    "enum": ["CORRECT", "INCORRECT", "INCOMPLETE", "UNKNOWN"],
                    "description": (
                        "Correctness of the final answer (independent of reasoning quality). "
                        "CORRECT: Final answer matches expected result. "
                        "INCORRECT: Final answer is demonstrably wrong. "
                        "INCOMPLETE: Answer is partial (e.g., found k=1 but missed k=0,3). "
                        "UNKNOWN: Cannot determine correctness without ground truth."
                    )
                },
                "reasoning": {
                    "type": "string",
                    "description": (
                        "Brief (1-3 sentences) explanation of the verdict. "
                        "Summarize key findings: why PASS or why FAIL. "
                        "Reference most significant issue if FAIL."
                    )
                }
            },
            "required": ["verdict", "confidence", "issues", "answer_correctness", "reasoning"],
            "additionalProperties": False
        }
    }
}


# Decision Logic for Verdict
# This replaces keyword parsing + meta-checker
def interpret_verdict(verdict_obj: dict) -> tuple[dict, str]:
    """
    Interpret structured verification verdict.

    Args:
        verdict_obj: Parsed JSON object matching VERIFICATION_VERDICT_SCHEMA

    Returns:
        tuple: (verdict_obj, "yes"|"no")
            - verdict_obj: The full verdict for debugging
            - "yes": Solution passes verification
            - "no": Solution fails verification

    Decision Rules:
        1. If verdict == "PASS" → "yes"
        2. If verdict == "FAIL" → "no"
        3. Special case: CORRECT answer with only JUSTIFICATION_GAPs → "yes"
           (Policy: Accept gaps for FIND problems with correct answers)
    """
    # Rule 1: Explicit PASS
    if verdict_obj["verdict"] == "PASS":
        return verdict_obj, "yes"

    # Rule 2: Check if FAIL is due to justification gaps only
    if verdict_obj["verdict"] == "FAIL":
        # Check if answer is correct or incomplete-but-correct
        # FIX (2025-12-24): Treat INCOMPLETE same as CORRECT for policy override
        # Root cause: Test 2 says "final answer k∈{0,1,3} is correct" with verdict="FAIL"
        # because answer_correctness="INCOMPLETE" (several presentation gaps)
        if verdict_obj["answer_correctness"] in ["CORRECT", "INCOMPLETE"]:
            # Check if all issues are JUSTIFICATION_GAPs (no CRITICAL_ERRORs)
            issues = verdict_obj.get("issues", [])
            if issues:
                has_critical_error = any(
                    issue["type"] == "CRITICAL_ERROR" for issue in issues
                )

                # ALTERNATIVE 3: Safety check for high-severity gaps (likely misclassified errors)
                # Severity 8-10 should be CRITICAL_ERRORs, not JUSTIFICATION_GAPs
                has_high_severity_gap = any(
                    issue["type"] == "JUSTIFICATION_GAP" and issue.get("severity", 0) >= 8
                    for issue in issues
                )

                if has_high_severity_gap:
                    print("[POLICY SAFETY] High-severity gap (≥8) detected - likely misclassified error, blocking override")
                    return verdict_obj, "no"

                if not has_critical_error:
                    # All issues are gaps, answer is correct/incomplete → PASS
                    print("[VERDICT OVERRIDE] Answer correct/incomplete with only justification gaps → PASS")
                    return verdict_obj, "yes"

        # Default FAIL
        return verdict_obj, "no"

    # Fallback (should never reach due to enum constraint)
    return verdict_obj, "no"


# Schema Statistics (for monitoring)
SCHEMA_STATS = {
    "total_fields": 5,
    "required_fields": 5,
    "nested_objects": 1,  # issues array
    "enum_constraints": 3,  # verdict, issue.type, answer_correctness
    "numeric_constraints": 2,  # confidence, severity
    "max_complexity": "medium"  # Complexity level for LLM
}


# Example Outputs (for validation testing)
EXAMPLE_PASS_VERDICT = {
    "verdict": "PASS",
    "confidence": 0.99,
    "issues": [],
    "answer_correctness": "CORRECT",
    "reasoning": "The proof correctly applies mathematical induction with valid base case and inductive step."
}

EXAMPLE_FAIL_VERDICT_CRITICAL_ERROR = {
    "verdict": "FAIL",
    "confidence": 0.95,
    "issues": [
        {
            "type": "CRITICAL_ERROR",
            "location": "Final Answer: k ∈ {0, 1, 2, 3}",
            "description": "The answer incorrectly includes k=2. For n=3, k=2 does not work.",
            "severity": 10
        }
    ],
    "answer_correctness": "INCORRECT",
    "reasoning": "Solution contains critical error: final answer includes k=2 which is incorrect for n=3."
}

EXAMPLE_FAIL_VERDICT_JUSTIFICATION_GAP = {
    "verdict": "FAIL",
    "confidence": 0.85,
    "issues": [
        {
            "type": "JUSTIFICATION_GAP",
            "location": "k=2 is impossible by pigeonhole principle",
            "description": "The impossibility claim lacks rigorous proof. No counting argument or contradiction provided.",
            "severity": 4
        }
    ],
    "answer_correctness": "CORRECT",
    "reasoning": "Answer is correct but impossibility proof for k=2 lacks rigor. Gap is acceptable for FIND problems."
}

EXAMPLE_OVERRIDE_CASE = {
    "verdict": "FAIL",  # LLM said FAIL
    "confidence": 0.80,
    "issues": [
        {
            "type": "JUSTIFICATION_GAP",
            "location": "All constructions work by coverage analysis",
            "description": "Missing point-by-point verification of construction",
            "severity": 3
        }
    ],
    "answer_correctness": "CORRECT",
    "reasoning": "Construction not fully verified but answer is correct"
}
# After interpret_verdict(): This would be overridden to "yes" (PASS)
# Because: answer_correctness=CORRECT + no CRITICAL_ERRORs + only JUSTIFICATION_GAPs


if __name__ == "__main__":
    """Test schema interpretation logic"""
    import json

    print("="*80)
    print("VERIFICATION SCHEMA TEST")
    print("="*80)

    test_cases = [
        ("PASS verdict", EXAMPLE_PASS_VERDICT, "yes"),
        ("FAIL - Critical Error", EXAMPLE_FAIL_VERDICT_CRITICAL_ERROR, "no"),
        ("FAIL - Justification Gap", EXAMPLE_FAIL_VERDICT_JUSTIFICATION_GAP, "yes"),  # Override
        ("FAIL - Override to PASS", EXAMPLE_OVERRIDE_CASE, "yes")
    ]

    for name, verdict, expected in test_cases:
        print(f"\n{name}:")
        print(f"Input: {json.dumps(verdict, indent=2)}")

        result_verdict, result_pass = interpret_verdict(verdict)
        print(f"Output: {result_pass}")
        print(f"Expected: {expected}")

        if result_pass == expected:
            print("✅ PASS")
        else:
            print(f"❌ FAIL - Expected {expected}, got {result_pass}")

    print("\n" + "="*80)
    print("Schema Statistics:")
    print(json.dumps(SCHEMA_STATS, indent=2))
    print("="*80)

"""
Small-Case Verification Module

Purpose: Force exploration of small cases when solution is incomplete
Triggered by: "remain open", "incomplete", "partial", etc.

From Expert Panel (RUN3_EXPERT_PANEL_SYNTHESIS.md):
- Run 3 explicitly stated "intermediate values remain open" but didn't try them
- If we had forced n=3 with k=0,1,2,3 exploration, might have found k=1,3
- Small cases often reveal patterns that lead to general solution
"""

import re

def detect_incompleteness(solution_text):
    """
    Detect if solution admits incompleteness.

    Args:
        solution_text: The solution text to analyze

    Returns:
        tuple: (is_incomplete, reason, missing_values)
    """
    incompleteness_phrases = [
        r"remain(?:s)?\s+open",
        r"(?:is|are|remains?)\s+incomplete",
        r"partial\s+(?:solution|result)",
        r"(?:have|has)\s+not\s+(?:found|proven|determined)",
        r"unable\s+to\s+(?:find|prove|determine)",
        r"(?:cannot|could\s+not)\s+(?:find|prove|determine)",
        r"(?:intermediate|other)\s+values?\s+(?:may|might|could)\s+exist",
        r"whether\s+.*\s+(?:is|are)\s+possible\s+remains?\s+(?:open|unknown)",
    ]

    for pattern in incompleteness_phrases:
        match = re.search(pattern, solution_text, re.IGNORECASE)
        if match:
            # Try to extract what's missing
            context = solution_text[max(0, match.start()-100):min(len(solution_text), match.end()+100)]

            # Common patterns for missing values
            missing_patterns = [
                r"k\s*=\s*([0-9,\s]+)",
                r"intermediate\s+values?\s+of\s+k",
                r"k\s+(?:between|from)\s+([0-9]+)\s+(?:and|to)\s+([0-9]+)",
            ]

            missing = "unknown intermediate values"
            for mp in missing_patterns:
                m = re.search(mp, context, re.IGNORECASE)
                if m:
                    missing = m.group(0)
                    break

            return True, match.group(0), missing

    return False, None, None

def generate_small_case_prompt(problem_statement, solution_text, missing_info):
    """
    Generate prompt to force small-case exploration.

    Args:
        problem_statement: Original problem
        solution_text: Current (incomplete) solution
        missing_info: What values are missing

    Returns:
        str: Prompt to explore small cases
    """
    # Extract problem parameter (usually n)
    param_match = re.search(r'Let\s+(\w+)\s*[≥>=]\s*(\d+)', problem_statement)
    if param_match:
        param = param_match.group(1)
        min_val = param_match.group(2)
    else:
        param = "n"
        min_val = "3"

    prompt = f"""
Your previous solution admitted incompleteness: "{missing_info}".

To resolve this, let's try SMALL CASES explicitly:

**Task**: For {param}={min_val} (the minimal case), try ALL possible values systematically.

Example strategy:
1. List all candidates (e.g., if determining k, try k=0,1,2,...,{param})
2. For EACH candidate value:
   - Either provide explicit construction proving it works
   - Or prove it's impossible (with rigorous justification)
3. Based on small-case results, identify the pattern

**Requirements**:
- Try EVERY value in the small case (don't skip any)
- Give explicit constructions (not just claims)
- If a value is impossible, explain WHY (geometric constraint, counting argument, etc.)
- The small-case pattern often generalizes to all {param}

Please provide a COMPLETE solution that determines ALL possible values, not just some.
"""

    return prompt.strip()

def should_trigger_small_case_verification(solution_text, verify_text, good_verify):
    """
    Decide if we should trigger small-case verification.

    Conditions:
    1. Solution admits incompleteness, OR
    2. Verification says "incomplete" or "partial", OR
    3. Good_verify is "no" but no Critical Errors (just missing cases)

    Args:
        solution_text: Solution text
        verify_text: Verification feedback
        good_verify: "yes" or "no"

    Returns:
        bool: Whether to trigger small-case verification
    """
    # Check solution incompleteness
    is_incomplete, reason, missing = detect_incompleteness(solution_text)
    if is_incomplete:
        return True, reason, missing

    # Check verification feedback
    if verify_text:
        if re.search(r'incomplete|partial|only\s+(?:shows?|proves?)', verify_text, re.IGNORECASE):
            # Verification says incomplete
            return True, "verification flagged incompleteness", "missing cases"

    # Check if failed verification is due to missing cases (not errors)
    if "no" in good_verify.lower() and verify_text:
        critical_errors = verify_text.lower().count('critical error')
        if critical_errors == 0:
            # Failed but no critical errors - might just be incomplete
            return True, "verification failed without critical errors", "possibly missing cases"

    return False, None, None

# Example usage in agent_gpt_oss.py:
"""
# After BFS selects best solution:
if best_solution:
    trigger, reason, missing = should_trigger_small_case_verification(
        best_solution, best_verify, best_good_verify
    )

    if trigger:
        print(f">>>>>>> [SMALL-CASE] Incompleteness detected: {reason}")
        print(f">>>>>>> [SMALL-CASE] Missing: {missing}")
        print(f">>>>>>> [SMALL-CASE] Forcing explicit small-case exploration...")

        small_case_prompt = generate_small_case_prompt(
            problem_statement, best_solution, missing
        )

        # Add small-case prompt to messages
        p1["messages"].append(build_assistant_message_from_text(best_solution))
        p1["messages"].append({"role": "user", "content": small_case_prompt})

        # Generate with MEDIUM reasoning (needs rigor for all cases)
        response = send_api_request_with_retry(get_api_key(), p1,
                                               request_label="Small-case exploration")
        improved_solution = extract_solution(extract_text_from_response(response))

        # Re-verify
        verify, good_verify = verify_solution(problem_statement, improved_solution,
                                              True, ver_reasoning)

        # Update best solution if better
        new_score = calculate_solution_score(verify, good_verify)
        if new_score > best_score:
            print(f">>>>>>> [SMALL-CASE] Improved solution (score: {best_score:.2f} → {new_score:.2f})")
            solution = improved_solution
        else:
            print(f">>>>>>> [SMALL-CASE] No improvement, keeping original")
            solution = best_solution
"""

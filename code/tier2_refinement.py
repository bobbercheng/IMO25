"""
TIER 2 Proof Refinement Module

After RLAC achieves TIER 1 (answer correctness via 3 ROBUST verdicts),
this module attempts to achieve TIER 2 (answer + proof rigor) by:
1. Running cooperative verification to identify proof gaps
2. Generating targeted patches to fill specific gaps
3. Iterating until verification passes or max rounds reached

Design: OpenAI pragmatic approach - simple, fast, <200 lines
"""

import re
import os
import json


def tier2_refinement_loop(
    problem_statement,
    rlac_solution,
    locked_answer,
    verify_solution_func,
    generate_solution_func,
    max_refinement_rounds=5,
    refinement_reasoning="high",
    verification_reasoning="high",
    verbose=True
):
    """
    TIER 2 Refinement: Fix proof gaps after RLAC success.

    Args:
        problem_statement: Original problem text
        rlac_solution: Solution that passed 3 ROBUST
        locked_answer: The correct answer from RLAC (must not change)
        verify_solution_func: Function(problem, solution, reasoning) -> (report, verdict)
        generate_solution_func: Function(prompt, reasoning) -> solution
        max_refinement_rounds: Max iterations (default: 5)
        refinement_reasoning: Reasoning level for gap-filling (default: "high")
        verification_reasoning: Reasoning level for verification (default: "high")
        verbose: Print progress messages

    Returns:
        (refined_solution, tier_status, refinement_history)
        tier_status: "TIER_2_VERIFIED" or "TIER_1_ONLY"
    """

    if verbose:
        print("\n" + "="*80)
        print("[TIER 2 REFINEMENT] Starting proof refinement phase")
        print(f"[TIER 2] Answer locked: {locked_answer[:100]}...")
        print(f"[TIER 2] Refinement rounds budget: {max_refinement_rounds}")
        print(f"[TIER 2] Reasoning effort: {refinement_reasoning}")
        print("="*80 + "\n")

    current_solution = rlac_solution
    refinement_history = []

    for round_num in range(max_refinement_rounds):
        if verbose:
            print(f"\n[TIER 2 ROUND {round_num+1}] Running cooperative verification...")

        # Step 1: Run cooperative verification with HIGH reasoning
        bug_report, verdict = verify_solution_func(
            problem_statement,
            current_solution,
            verification_reasoning
        )

        # Step 2: Check if verification passed
        if "yes" in verdict.lower():
            if verbose:
                print(f"[TIER 2 SUCCESS] ✓ Cooperative verification PASSED!")
                print(f"[TIER 2 SUCCESS] Achieved in {round_num+1} refinement rounds")
            return current_solution, "TIER_2_VERIFIED", refinement_history

        if verbose:
            print(f"[TIER 2 ROUND {round_num+1}] Verification failed, analyzing feedback...")

        # Step 3: Extract structured feedback from bug report
        issues = parse_verification_feedback(bug_report)

        if not issues or len(issues) == 0:
            if verbose:
                print(f"[TIER 2 WARNING] No actionable feedback, verification may be too harsh")
            return current_solution, "TIER_1_ONLY", refinement_history

        # Step 4: Classify issues by severity
        critical_errors = [i for i in issues if i['type'] == 'CRITICAL_ERROR']
        justification_gaps = [i for i in issues if i['type'] == 'JUSTIFICATION_GAP']

        if verbose:
            print(f"[TIER 2 ANALYSIS] Found {len(critical_errors)} critical errors, {len(justification_gaps)} gaps")

        # Step 5: Build targeted refinement prompt
        refinement_prompt = build_refinement_prompt(
            problem_statement=problem_statement,
            current_solution=current_solution,
            locked_answer=locked_answer,
            critical_errors=critical_errors,
            justification_gaps=justification_gaps,
            round_num=round_num
        )

        # Step 6: Generate refined solution with HIGH reasoning
        if verbose:
            print(f"[TIER 2 ROUND {round_num+1}] Generating refined proof...")

        refined_solution = generate_solution_func(
            refinement_prompt,
            refinement_reasoning
        )

        # Step 7: CRITICAL - Verify answer didn't change
        # (Disabled for proof problems - see is_proof_problem())
        refined_answer = extract_boxed_answer(refined_solution, problem_statement)

        if refined_answer and refined_answer != locked_answer:
            if verbose:
                print(f"[TIER 2 ERROR] Answer changed during refinement!")
                print(f"[TIER 2 ERROR]   Expected: {locked_answer}")
                print(f"[TIER 2 ERROR]   Got: {refined_answer}")
                print(f"[TIER 2 RECOVERY] Reverting to previous solution, trying next round...")
            # Don't update current_solution, try again
            continue

        # Step 8: Check for refinement loops (same gaps repeating)
        if detect_refinement_loop(refinement_history, issues):
            if verbose:
                print(f"[TIER 2 WARNING] Refinement loop detected - same gaps reappearing")
                print(f"[TIER 2 WARNING] Current approach cannot fix these gaps")
            return current_solution, "TIER_1_ONLY", refinement_history

        # Step 9: Update for next iteration
        refinement_history.append({
            'round': round_num + 1,
            'issues_count': len(issues),
            'critical': len(critical_errors),
            'gaps': len(justification_gaps),
            'feedback_summary': bug_report[:500] if bug_report else ""
        })

        current_solution = refined_solution

        if verbose:
            print(f"[TIER 2 ROUND {round_num+1}] Refinement applied, solution length: {len(refined_solution)} chars")

    # Exhausted rounds without passing
    if verbose:
        print(f"\n[TIER 2 INCOMPLETE] Max rounds reached without verification pass")
        print(f"[TIER 2 STATUS] Answer is correct (RLAC-ROBUST), proof needs manual review")

    return current_solution, "TIER_1_ONLY", refinement_history


def parse_verification_feedback(bug_report):
    """
    Extract structured issues from verification bug report.

    Returns:
        List of dicts with {type, location, description}
    """
    issues = []

    if not bug_report:
        return issues

    # Pattern 1: Look for "List of Findings" section (flexible header matching)
    # Support multiple formats: "### List of Findings", "**List of Findings:**", "List of Findings:"
    if "List of Findings" in bug_report:
        # Find the findings section - try multiple header formats
        findings_start = -1
        for header in ["### List of Findings", "**List of Findings:**", "List of Findings:", "**List of Findings**"]:
            findings_start = bug_report.find(header)
            if findings_start != -1:
                break

        if findings_start != -1:
            findings_section = bug_report[findings_start:]

            # Parse each finding by looking for location markers
            # Updated regex to handle markdown bold: **Location:** and plain Location:
            # Also handles quotes and special characters in location text
            location_pattern = r'\*\s*(?:\*\*)?(?:Location|location)(?:\*\*)?:\s*(?:["\'])?(.+?)(?:["\'])?\s*\n'
            issue_pattern = r'\*\s*(?:\*\*)?(?:Issue|issue)(?:\*\*)?:\s*(?:\*\*)?(.+?)(?:\*\*)?\s*(?:\n|$)'

            locations = re.findall(location_pattern, findings_section, re.DOTALL)
            issue_descriptions = re.findall(issue_pattern, findings_section, re.DOTALL)

            # Clean up captured text (remove markdown bold markers)
            locations = [loc.replace('**', '').strip() for loc in locations]
            issue_descriptions = [desc.replace('**', '').strip() for desc in issue_descriptions]

            for i, (location, description) in enumerate(zip(locations, issue_descriptions)):
                # Classify by keywords (accept multiple separator formats: colon, en-dash, em-dash)
                if any(kw in description.lower() for kw in ['critical error', 'critical:', 'critical –', 'critical —', 'false', 'incorrect', 'wrong']):
                    issue_type = 'CRITICAL_ERROR'
                else:
                    issue_type = 'JUSTIFICATION_GAP'

                issues.append({
                    'type': issue_type,
                    'location': location.strip(),
                    'description': description.strip()
                })

    # Pattern 2: Direct error mentions (fallback if no structured list)
    if not issues:
        # Look for explicit error statements (accept multiple separators: :, –, —, -)
        critical_pattern = r'(?:Critical Error|CRITICAL ERROR|critical error)[\s:–—-]+(.+?)(?:\n|$)'
        gap_pattern = r'(?:Justification Gap|justification gap|unjustified)[\s:–—-]+(.+?)(?:\n|$)'

        for match in re.finditer(critical_pattern, bug_report, re.IGNORECASE | re.DOTALL):
            issues.append({
                'type': 'CRITICAL_ERROR',
                'location': 'Unknown',
                'description': match.group(1).strip()
            })

        for match in re.finditer(gap_pattern, bug_report, re.IGNORECASE | re.DOTALL):
            issues.append({
                'type': 'JUSTIFICATION_GAP',
                'location': 'Unknown',
                'description': match.group(1).strip()
            })

    return issues


def build_refinement_prompt(problem_statement, current_solution, locked_answer,
                            critical_errors, justification_gaps, round_num):
    """
    Build targeted refinement prompt - KEY INNOVATION.

    This is o1-style: ask model to "fill in the gaps" not "regenerate everything".
    """

    prompt = f"""## PROOF REFINEMENT TASK (TIER 2 Verification)

### Context ###
You previously solved this problem and your answer **{locked_answer}** is **CORRECT** (verified by adversarial testing with 3 consecutive ROBUST verdicts).

However, the proof has some **presentation issues** that need refinement. Your task is to FIX SPECIFIC ISSUES in the proof, NOT to re-solve the problem.

### Original Problem ###
{problem_statement}

### Current Proof (with issues to fix) ###
{current_solution}

### Verification Feedback ###

"""

    if critical_errors:
        prompt += "**Critical Errors (must fix):**\n\n"
        for i, err in enumerate(critical_errors, 1):
            prompt += f"{i}. **Location**: \"{err['location']}\"\n"
            prompt += f"   **Issue**: {err['description']}\n\n"

    if justification_gaps:
        prompt += "**Justification Gaps (need more detail):**\n\n"
        for i, gap in enumerate(justification_gaps, 1):
            prompt += f"{i}. **Location**: \"{gap['location']}\"\n"
            prompt += f"   **Issue**: {gap['description']}\n\n"

    prompt += """
### Your Task ###

**DO NOT re-solve the problem from scratch.** Your answer is already correct.

**DO:** Make TARGETED FIXES to address each issue above:

1. **For Critical Errors (notation/logic):**
   - Fix the exact statement that has the error
   - Use correct mathematical notation
   - Example: If "PA·PQ" should be "PA·PE", change it precisely

2. **For Justification Gaps:**
   - ADD intermediate steps to show WHY the claim is true
   - Provide algebraic verification (e.g., substitute and simplify)
   - Example: If claiming "distance = radius", show the calculation

3. **Preserve everything else:**
   - Keep the same proof structure and approach
   - Don't change your answer (LOCKED)
   - Only fix the flagged issues

### Output Format ###

**IMPORTANT**: Format your response with the exact structure below:

```
### Detailed Solution ###

[Your complete refined proof here, with:]
- All issues from verification feedback addressed
- Intermediate steps filled in for gaps
- Correct notation for errors
- Same answer in \\boxed{} at the end
```

**Critical**: Start your response with EXACTLY "### Detailed Solution ###" (this marker is required for the verification system).

**Remember**: Your answer is CORRECT. This is proof refinement, not problem solving.
"""

    if round_num > 0:
        prompt += f"\n**Note**: This is refinement round {round_num + 1}. Previous rounds found similar issues. Focus on COMPLETE fixes this time.\n"

    return prompt


def is_proof_problem(problem_statement):
    """
    Detect if the problem asks to prove something (not compute a value).

    For "prove that" problems, there's no discrete answer to lock - the answer
    IS the proof itself. Attempting to lock intermediate boxed results creates
    instability during refinement.

    Args:
        problem_statement: The problem text

    Returns:
        True if this is a proof problem, False otherwise
    """
    if not problem_statement:
        return False

    problem_lower = problem_statement.lower()

    # Common proof problem indicators
    proof_indicators = [
        'prove that',
        'show that',
        'demonstrate that',
        'verify that',
        'establish that',
        'prove the',
    ]

    return any(indicator in problem_lower for indicator in proof_indicators)


def extract_boxed_answer(solution, problem_statement=None):
    """
    Extract answer from \\boxed{...} for verification.
    Handles nested braces correctly (e.g., \\dfrac{a}{b}, \\Bigl(...\\Bigr)).

    For "prove that" problems, returns None to disable answer locking.
    This prevents false rejections when refinements reorder proof steps.

    Args:
        solution: The solution text containing boxed expressions
        problem_statement: Original problem (optional, for proof detection)

    Returns:
        Extracted answer string or None if not found/disabled
    """
    if not solution:
        return None

    # Disable answer locking for proof problems
    # (Their "answer" is the proof itself, not a boxed intermediate result)
    if problem_statement and is_proof_problem(problem_statement):
        return None

    # Find \boxed{ or boxed{
    pattern = r'\\?boxed\{'
    match = re.search(pattern, solution)

    if not match:
        return None

    # Start after the opening brace
    start = match.end()

    # Count braces to find the matching closing brace
    brace_count = 1
    i = start

    while i < len(solution) and brace_count > 0:
        if solution[i] == '{':
            brace_count += 1
        elif solution[i] == '}':
            brace_count -= 1
        i += 1

    if brace_count == 0:
        # Successfully found matching brace
        return solution[start:i-1].strip()

    return None


def detect_refinement_loop(refinement_history, current_issues, window=3):
    """
    Detect if refinement is oscillating (same gaps appearing repeatedly).

    Args:
        refinement_history: List of previous round info
        current_issues: Current round issues
        window: Number of rounds to check (default: 3)

    Returns:
        True if loop detected, False otherwise
    """
    if len(refinement_history) < window - 1:
        return False

    recent_rounds = refinement_history[-(window-1):]

    # Check if issue counts are stable (not improving)
    issue_counts = [r['issues_count'] for r in recent_rounds] + [len(current_issues)]

    # If all counts are within 1 of each other, we're stuck
    if max(issue_counts) - min(issue_counts) <= 1 and len(issue_counts) >= window:
        return True

    return False


# Helper function to create wrapper for verify_solution_safe
def create_verify_wrapper(verify_func):
    """
    Create a wrapper for verify_solution_safe to match expected signature.

    verify_func should be the verify_solution_safe from agent_gpt_oss.py
    """
    def wrapper(problem, solution, reasoning):
        return verify_func(problem, solution, reasoning_effort=reasoning)
    return wrapper

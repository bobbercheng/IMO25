"""
Feedback Mechanism Implementation Examples

Ready-to-use code snippets for bridging the verification-generation gap.
Each function can be tested independently on the failed asymmetric case.
"""

import json
import re
from typing import List, Dict, Any, Tuple

# ============================================================================
# 1. STRUCTURED JSON FEEDBACK
# ============================================================================

JSON_FEEDBACK_TEMPLATE = """
You are a feedback formatter. Convert this verification feedback into structured JSON.

VERIFICATION FEEDBACK (prose):
{prose_feedback}

Convert this into the following JSON structure:

{{
  "overall_status": "pass" or "fail",
  "score": 0-100,
  "errors": [
    {{
      "id": "E1",
      "location": "Specific section/lemma/line where error occurs",
      "type": "ALGEBRA | LOGIC | GAP | CONSTRUCTION | COUNTING | NOTATION",
      "severity": 0-100,
      "issue": "One-sentence description of what is wrong",
      "current_claim": "Exact text from solution that is incorrect",
      "correct_version": "What the text should say instead",
      "fix_template": "Specific instruction for how to fix",
      "dependencies": ["E2", "E3"]
    }}
  ],
  "strongest_parts": ["List 2-3 things that ARE correct"],
  "priority_fixes": ["E1", "E3", "E5"]
}}

Guidelines:
1. Extract ALL distinct errors mentioned in the feedback
2. Assign severity: 100 = critical (invalidates solution), 50 = significant gap, 20 = minor issue
3. Be SPECIFIC in location (not "Lemma 4" but "Lemma 4, case a=n-1, b=1")
4. In "current_claim", quote the EXACT text that is wrong
5. In "correct_version", provide the EXACT replacement text
6. Identify dependencies: which errors depend on fixing which other errors?
7. Priority_fixes should list errors in the order they should be fixed (dependencies first)

Return ONLY the JSON, no other text.
"""

def convert_prose_to_json_feedback(prose_feedback: str, api_call_fn) -> Dict[str, Any]:
    """
    Convert natural language verification feedback to structured JSON.

    Args:
        prose_feedback: The original prose feedback from high-reasoning verification
        api_call_fn: Function to call LLM API (e.g., GPT-4)

    Returns:
        Structured JSON feedback dict
    """
    prompt = JSON_FEEDBACK_TEMPLATE.format(prose_feedback=prose_feedback)

    response = api_call_fn(
        system_prompt="You are a precise feedback formatter.",
        user_prompt=prompt,
        temperature=0.1,
        reasoning_effort="medium"  # Medium is enough for formatting task
    )

    # Parse JSON from response
    json_match = re.search(r'\{.*\}', response, re.DOTALL)
    if json_match:
        return json.loads(json_match.group())
    else:
        raise ValueError("Could not extract JSON from response")


def generate_correction_with_json_feedback(
    problem: str,
    solution: str,
    json_feedback: Dict[str, Any],
    api_call_fn
) -> str:
    """
    Generate corrected solution using structured JSON feedback.

    Args:
        problem: Original problem statement
        solution: Current solution with errors
        json_feedback: Structured feedback from convert_prose_to_json_feedback
        api_call_fn: Function to call LLM API

    Returns:
        Corrected solution
    """
    correction_prompt = f"""
You previously submitted a solution with errors identified in the structured feedback below.

PROBLEM:
{problem}

YOUR PREVIOUS SOLUTION:
{solution}

STRUCTURED FEEDBACK:
{json.dumps(json_feedback, indent=2)}

INSTRUCTIONS:
1. Keep all parts mentioned in "strongest_parts" - they are correct
2. For each error in "priority_fixes" (in that order):
   a. Locate the "current_claim" text in your solution
   b. Replace it with the "correct_version"
   c. Follow the "fix_template" guidance
3. Do NOT change anything else that isn't marked as an error
4. Maintain the same overall structure and format

Apply the fixes systematically and return the corrected solution.
"""

    return api_call_fn(
        system_prompt="You are a mathematical solution corrector.",
        user_prompt=correction_prompt,
        temperature=0.1,
        reasoning_effort="low"  # Low reasoning can apply structured fixes
    )


# ============================================================================
# 2. TOP-N PRIORITIZATION
# ============================================================================

def calculate_error_impact(error: Dict[str, Any], all_errors: List[Dict[str, Any]]) -> float:
    """
    Calculate the impact score of an error based on severity and dependencies.

    Higher impact errors should be fixed first.
    """
    base_severity = error['severity']

    # Count how many other errors depend on this one
    dependents = sum(
        1 for other in all_errors
        if error['id'] in other.get('dependencies', [])
    )

    # Error type weights (some types are more fundamental)
    type_weights = {
        'DEFINITION': 2.0,      # Broken definitions cascade everywhere
        'CONSTRUCTION': 1.8,    # Construction errors invalidate everything after
        'LOGIC': 1.7,           # Logical gaps are hard to patch downstream
        'ALGEBRA': 1.5,         # Algebra errors compound
        'GAP': 1.2,             # Gaps are usually local
        'COUNTING': 1.3,        # Counting errors affect conclusions
        'NOTATION': 0.8,        # Notation issues don't propagate much
    }
    type_weight = type_weights.get(error['type'], 1.0)

    # Section weights (earlier sections have more impact)
    section = error['location'].lower()
    if 'lemma 1' in section or 'definition' in section:
        section_weight = 1.5
    elif 'lemma 2' in section or 'lemma 3' in section:
        section_weight = 1.3
    elif 'construction' in section:
        section_weight = 1.4
    else:
        section_weight = 1.0

    # Final impact score
    impact = base_severity * (1 + dependents * 0.3) * type_weight * section_weight

    return impact


def prioritize_top_n_errors(json_feedback: Dict[str, Any], n: int = 3) -> Dict[str, Any]:
    """
    Extract top N most critical errors from full feedback.

    Args:
        json_feedback: Full structured feedback with all errors
        n: Number of top errors to return (default 3)

    Returns:
        Compressed feedback with only top N errors
    """
    errors = json_feedback['errors']

    # Calculate impact for each error
    for error in errors:
        error['impact'] = calculate_error_impact(error, errors)

    # Sort by impact (highest first)
    errors_sorted = sorted(errors, key=lambda e: e['impact'], reverse=True)

    # Take top N
    top_errors = errors_sorted[:n]

    # Build compressed feedback
    compressed = {
        "overall_status": json_feedback['overall_status'],
        "score": json_feedback['score'],
        "total_errors": len(errors),
        "showing_top": n,
        "errors": top_errors,
        "strongest_parts": json_feedback['strongest_parts'],
        "priority_fixes": [e['id'] for e in top_errors],
        "message": f"""
Your solution has {len(errors)} issues total, but let's fix the TOP {n} MOST CRITICAL first.

After fixing these, many other issues may resolve automatically.

Fix ONLY these {n} issues. Do NOT make other changes.
We will verify again and address remaining issues in the next iteration.
"""
    }

    return compressed


# ============================================================================
# 3. DIFF-BASED FEEDBACK
# ============================================================================

def generate_diff_for_error(
    solution: str,
    error: Dict[str, Any],
    context_lines: int = 3
) -> str:
    """
    Generate git-style diff for fixing a specific error.

    Args:
        solution: Full solution text
        error: Error dict with 'current_claim' and 'correct_version'
        context_lines: Number of context lines to show before/after

    Returns:
        Unified diff string
    """
    old_text = error['current_claim']
    new_text = error['correct_version']
    location = error['location']

    # Find the old text in the solution
    if old_text not in solution:
        return f"[ERROR: Could not locate '{old_text[:50]}...' in solution]"

    # Split solution into lines
    lines = solution.split('\n')

    # Find line containing old_text
    old_line_idx = None
    for i, line in enumerate(lines):
        if old_text in line:
            old_line_idx = i
            break

    if old_line_idx is None:
        # Try fuzzy match
        for i, line in enumerate(lines):
            if old_text[:30] in line:  # Match first 30 chars
                old_line_idx = i
                break

    if old_line_idx is None:
        return f"[ERROR: Could not locate error location in solution]"

    # Extract context
    start = max(0, old_line_idx - context_lines)
    end = min(len(lines), old_line_idx + context_lines + 1)

    context_before = lines[start:old_line_idx]
    old_line = lines[old_line_idx]
    context_after = lines[old_line_idx + 1:end]

    # Build diff
    diff = f"""
--- {location} (original)
+++ {location} (corrected)
@@ line {old_line_idx + 1} @@
"""

    for line in context_before:
        diff += f"  {line}\n"

    diff += f"- {old_line}\n"
    diff += f"+ {new_text}\n"

    for line in context_after:
        diff += f"  {line}\n"

    return diff


def generate_all_diffs(solution: str, json_feedback: Dict[str, Any]) -> str:
    """
    Generate diffs for all priority errors.

    Args:
        solution: Current solution text
        json_feedback: Structured feedback with errors

    Returns:
        Combined diff string for all priority fixes
    """
    priority_errors = [
        e for e in json_feedback['errors']
        if e['id'] in json_feedback['priority_fixes']
    ]

    all_diffs = "Apply the following diffs to fix your solution:\n\n"
    all_diffs += "=" * 70 + "\n\n"

    for i, error in enumerate(priority_errors, 1):
        all_diffs += f"DIFF #{i}: Fix {error['id']} - {error['location']}\n"
        all_diffs += f"Issue: {error['issue']}\n\n"
        all_diffs += generate_diff_for_error(solution, error)
        all_diffs += "\n" + "=" * 70 + "\n\n"

    all_diffs += """
How to apply diffs:
- Lines starting with '-' should be REMOVED
- Lines starting with '+' should be ADDED
- Lines starting with ' ' (space) are context and should stay unchanged

Apply these diffs in order (Diff #1 first, then #2, etc.).
"""

    return all_diffs


# ============================================================================
# 4. PROGRESSIVE SCORING
# ============================================================================

def score_solution_progressively(solution: str, verification_feedback: str) -> Tuple[int, Dict[str, int]]:
    """
    Score a solution on a 0-100 scale with component breakdown.

    Args:
        solution: The solution text
        verification_feedback: Verification feedback (prose or JSON)

    Returns:
        Tuple of (total_score, component_scores)
    """
    scores = {}

    # 1. Formatting (10 points)
    has_tex = '$' in solution or '\\(' in solution
    has_sections = 'Summary' in solution or 'Detailed Solution' in solution
    scores['formatting'] = (5 if has_tex else 0) + (5 if has_sections else 0)

    # 2. Structure (15 points)
    has_summary = 'Summary' in solution or 'Verdict' in solution
    has_method = 'Method' in solution or 'Sketch' in solution
    has_detailed = 'Detailed Solution' in solution or 'Proof' in solution
    scores['structure'] = \
        (5 if has_summary else 0) + \
        (5 if has_method else 0) + \
        (5 if has_detailed else 0)

    # 3. Lemmas (40 points: 15 for stating, 25 for proving)
    lemma_count = solution.count('Lemma') + solution.count('Claim')
    scores['lemmas_stated'] = min(15, lemma_count * 3)

    # Estimate proof quality from verification feedback
    if verification_feedback:
        if 'critical error' in verification_feedback.lower():
            scores['lemmas_proved'] = 5
        elif 'justification gap' in verification_feedback.lower():
            scores['lemmas_proved'] = 15
        elif 'minor' in verification_feedback.lower():
            scores['lemmas_proved'] = 20
        else:
            scores['lemmas_proved'] = 25
    else:
        scores['lemmas_proved'] = 20  # Default assumption

    # 4. Construction (20 points)
    has_construction = 'construction' in solution.lower() or 'define' in solution.lower()
    has_verification = 'verify' in solution.lower() or 'check' in solution.lower()

    if 'construction' in verification_feedback.lower() and 'error' in verification_feedback.lower():
        scores['construction'] = 8
    elif has_construction and has_verification:
        scores['construction'] = 18
    elif has_construction:
        scores['construction'] = 12
    else:
        scores['construction'] = 5

    # 5. Final answer (15 points)
    has_boxed = 'boxed' in solution or '□' in solution
    has_answer = any(word in solution.lower() for word in ['therefore', 'thus', 'answer', 'conclude'])

    if verification_feedback and 'answer' in verification_feedback.lower() and 'wrong' in verification_feedback.lower():
        scores['final_answer'] = 5
    elif has_boxed and has_answer:
        scores['final_answer'] = 15
    elif has_answer:
        scores['final_answer'] = 10
    else:
        scores['final_answer'] = 5

    total = sum(scores.values())

    return total, scores


def format_progressive_score(score: int, component_scores: Dict[str, int], threshold: int = 85) -> str:
    """
    Format progressive score as human-readable feedback.

    Args:
        score: Total score 0-100
        component_scores: Breakdown by component
        threshold: Acceptance threshold

    Returns:
        Formatted score feedback
    """
    status = "PASS ✓" if score >= threshold else "NEEDS IMPROVEMENT"

    feedback = f"""
{'='*70}
SOLUTION SCORE: {score}/100
{'='*70}

Component Breakdown:
{'✓' if component_scores['formatting'] >= 8 else '✗'} Formatting:      {component_scores['formatting']:2d}/10
{'✓' if component_scores['structure'] >= 12 else '✗'} Structure:       {component_scores['structure']:2d}/15
{'✓' if component_scores['lemmas_stated'] >= 12 else '✗'} Lemmas Stated:   {component_scores['lemmas_stated']:2d}/15
{'✓' if component_scores['lemmas_proved'] >= 20 else '✗'} Lemmas Proved:   {component_scores['lemmas_proved']:2d}/25  {'← FOCUS HERE' if component_scores['lemmas_proved'] < 20 else ''}
{'✓' if component_scores['construction'] >= 15 else '✗'} Construction:    {component_scores['construction']:2d}/20  {'← FOCUS HERE' if component_scores['construction'] < 15 else ''}
{'✓' if component_scores['final_answer'] >= 12 else '✗'} Final Answer:    {component_scores['final_answer']:2d}/15

THRESHOLD: {threshold}/100
STATUS: {status}
"""

    if score < threshold:
        gap = threshold - score
        feedback += f"\nYou are {gap} points away from acceptance.\n"

        # Suggest what to improve
        weak_components = [
            (name, comp_score, max_score)
            for name, comp_score in component_scores.items()
            for max_score in [{'formatting': 10, 'structure': 15, 'lemmas_stated': 15,
                              'lemmas_proved': 25, 'construction': 20, 'final_answer': 15}[name]]
            if comp_score < max_score * 0.8
        ]

        if weak_components:
            feedback += "\nPRIORITY: Focus on improving:\n"
            for name, current, maximum in sorted(weak_components, key=lambda x: x[2] - x[1], reverse=True):
                feedback += f"  - {name.replace('_', ' ').title()}: {current}/{maximum}\n"

    feedback += "=" * 70 + "\n"

    return feedback


# ============================================================================
# 5. EXAMPLE-BASED FEEDBACK
# ============================================================================

WORKED_EXAMPLE_TEMPLATE = """
Your solution has an error in {error_location}.

Instead of explaining abstractly, let me show you a CONCRETE EXAMPLE of the correct approach.

YOUR CLAIM:
{current_claim}

Let's verify with a specific value: {specific_case}

STEP-BY-STEP VERIFICATION:
{worked_steps}

RESULT: {result}

Now, here's the CORRECT APPROACH for the general case:

{correct_general_approach}

Revise your solution following this same structure, but for general n.
"""


def generate_example_based_feedback(
    error: Dict[str, Any],
    n_example: int = 5
) -> str:
    """
    Generate example-based feedback showing worked concrete case.

    Args:
        error: Error dict from JSON feedback
        n_example: Specific value of n to use in example

    Returns:
        Example-based feedback string
    """
    # This would need domain-specific logic to generate worked examples
    # For now, we provide a template

    return WORKED_EXAMPLE_TEMPLATE.format(
        error_location=error['location'],
        current_claim=error['current_claim'],
        specific_case=f"n={n_example}",
        worked_steps="[Would be generated based on error type]",
        result="[Would show whether claim is correct/incorrect for this case]",
        correct_general_approach=error['correct_version']
    )


# ============================================================================
# 6. INTEGRATION: COMPLETE FEEDBACK PIPELINE
# ============================================================================

def create_enhanced_feedback_pipeline(
    prose_feedback: str,
    solution: str,
    api_call_fn,
    strategy: str = "json_top3_diff"
) -> str:
    """
    Complete feedback pipeline combining multiple approaches.

    Args:
        prose_feedback: Original prose verification feedback
        solution: Current solution with errors
        api_call_fn: Function to call LLM API
        strategy: Which combination strategy to use
            - "json_top3_diff": JSON + Top-3 + Diff (fast fixes)
            - "json_progressive": JSON + Progressive scoring
            - "json_only": Just structured JSON

    Returns:
        Enhanced feedback string ready for generator
    """
    # Step 1: Convert to JSON
    json_feedback = convert_prose_to_json_feedback(prose_feedback, api_call_fn)

    if strategy == "json_only":
        return json.dumps(json_feedback, indent=2)

    # Step 2: Progressive scoring (if requested)
    if "progressive" in strategy:
        score, components = score_solution_progressively(solution, prose_feedback)
        score_feedback = format_progressive_score(score, components)
    else:
        score_feedback = ""

    # Step 3: Prioritize top errors (if requested)
    if "top" in strategy or "top3" in strategy:
        compressed_feedback = prioritize_top_n_errors(json_feedback, n=3)
    else:
        compressed_feedback = json_feedback

    # Step 4: Generate diffs (if requested)
    if "diff" in strategy:
        diffs = generate_all_diffs(solution, compressed_feedback)
    else:
        diffs = ""

    # Combine all feedback
    combined_feedback = ""

    if score_feedback:
        combined_feedback += score_feedback + "\n\n"

    combined_feedback += "STRUCTURED ERROR REPORT:\n"
    combined_feedback += "=" * 70 + "\n\n"
    combined_feedback += json.dumps(compressed_feedback, indent=2)
    combined_feedback += "\n\n"

    if diffs:
        combined_feedback += "EXACT FIXES TO APPLY:\n"
        combined_feedback += "=" * 70 + "\n\n"
        combined_feedback += diffs

    return combined_feedback


# ============================================================================
# USAGE EXAMPLE
# ============================================================================

def example_usage():
    """
    Example of how to use the feedback pipeline.
    """
    # Simulated inputs
    prose_feedback = """
    The solution contains several critical errors:

    1. In Lemma 4, the construction claims that point (n-1,1) lies on ℓ_s,
       but this requires parity analysis which is missing.

    2. The verification in case a=n-2 is incomplete.

    3. The final answer doesn't account for the n=3 special case.
    """

    solution = """
    Lemma 4: Construction with k=1

    Define ℓ_s = {y = x - (n-2)}

    For a=n-1, b=1, the point (n-1,1) lies on ℓ_s.

    Final answer: k ∈ {0, 1} for all n ≥ 3.
    """

    # Mock API call function
    def mock_api_call(system_prompt, user_prompt, temperature, reasoning_effort):
        # In real usage, this would call GPT API
        return '{"overall_status": "fail", "score": 65, "errors": [...]}'

    # Create enhanced feedback
    enhanced_feedback = create_enhanced_feedback_pipeline(
        prose_feedback=prose_feedback,
        solution=solution,
        api_call_fn=mock_api_call,
        strategy="json_top3_diff"
    )

    print(enhanced_feedback)


if __name__ == "__main__":
    print("Feedback Mechanism Implementation Examples")
    print("=" * 70)
    print("\nThese functions can be imported and used in agent_gpt_oss.py")
    print("to enhance the verification-generation feedback loop.\n")
    print("See example_usage() for how to use the complete pipeline.\n")

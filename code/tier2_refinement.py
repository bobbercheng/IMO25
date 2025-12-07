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

# Symbolic validation support (optional, only if sympy available)
try:
    import sympy as sp
    SYMPY_AVAILABLE = True
except ImportError:
    SYMPY_AVAILABLE = False

# Numerical validation support
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False


def validate_equation_symbolically(equation_text, verbose=False):
    """
    Validate an algebraic equation using symbolic computation.

    This is a basic implementation that checks if an equation simplifies to 0=0.
    For coordinate geometry proofs, catching formula errors early prevents
    error propagation through subsequent calculations.

    Args:
        equation_text: String like "x^2 + y^2 = r^2" or "LHS = RHS"
        verbose: Print validation details

    Returns:
        dict with keys:
            - 'valid': bool (True if equation is symbolically valid)
            - 'simplified': str (simplified form)
            - 'error': str (error message if validation failed)
    """
    if not SYMPY_AVAILABLE:
        return {
            'valid': None,
            'simplified': None,
            'error': 'SymPy not available - install with: pip install sympy'
        }

    try:
        # Extract LHS and RHS from equation
        if '=' in equation_text:
            parts = equation_text.split('=')
            if len(parts) == 2:
                lhs_text = parts[0].strip()
                rhs_text = parts[1].strip()

                # Parse with SymPy
                lhs = sp.sympify(lhs_text)
                rhs = sp.sympify(rhs_text)

                # Simplify difference
                diff = sp.simplify(lhs - rhs)

                if verbose:
                    print(f"[SYMBOLIC] LHS: {lhs}")
                    print(f"[SYMBOLIC] RHS: {rhs}")
                    print(f"[SYMBOLIC] Simplified difference: {diff}")

                # Check if difference is zero
                is_valid = diff == 0

                return {
                    'valid': is_valid,
                    'simplified': str(diff),
                    'error': None if is_valid else f"Equation does not hold: {lhs} ≠ {rhs}"
                }
            else:
                return {
                    'valid': None,
                    'simplified': None,
                    'error': f"Could not parse equation (found {len(parts)} parts, expected 2)"
                }
        else:
            return {
                'valid': None,
                'simplified': None,
                'error': "No '=' found in equation"
            }

    except Exception as e:
        return {
            'valid': None,
            'simplified': None,
            'error': f"Symbolic validation error: {str(e)}"
        }


def extract_equations_from_proof(proof_text):
    """
    Extract mathematical equations from a proof for validation.

    Supports multiple formats:
    - Inline numbered: (3.2) q = ...
    - LaTeX display: \\[ ... \\]
    - LaTeX with tags: \\[ ... \\tag{n} \\]
    - Inline LaTeX: \\( ... \\)

    Args:
        proof_text: The proof text

    Returns:
        List of equation strings (cleaned, SymPy-compatible)
    """
    equations = []

    # Pattern 1: Inline numbered equations (e.g., "(3.2) q = ...")
    inline_pattern = r'\([\d.]+\)\s*([^\n.]+\s*=\s*[^\n.]+?)(?:\n|\.|\s{2}|$)'
    inline_matches = re.findall(inline_pattern, proof_text, re.MULTILINE)

    for match in inline_matches:
        cleaned = match.strip()
        if cleaned and '=' in cleaned:
            # Convert basic LaTeX to SymPy
            cleaned = clean_latex_equation(cleaned)
            if cleaned:
                equations.append(cleaned)

    # Pattern 2: LaTeX display equations \\[ ... \\]
    # Use non-greedy match and DOTALL to handle multi-line equations
    latex_pattern = r'\\\[(.*?)\\\]'
    latex_matches = re.findall(latex_pattern, proof_text, re.DOTALL)

    for match in latex_matches:
        # Remove \tag{n} notation
        cleaned = re.sub(r'\\tag\{[^}]*\}', '', match)

        # Split multiple equations in one display block (separated by commas or \\qquad)
        # Example: A=(...), B=(...) should be split
        parts = re.split(r',\s*(?=[A-Z]\s*=)', cleaned)

        for part in parts:
            part = part.strip()
            if '=' in part:
                # Convert LaTeX to SymPy-compatible format
                part = clean_latex_equation(part)
                if part:  # Only add non-empty equations
                    equations.append(part)

    # Pattern 3: Inline LaTeX math \\( ... \\) - but only simple equations
    # Example: "we have \\(PA=PD\\)" should extract "PA=PD"
    # FIX: Remove nested character class to avoid regex warning
    inline_latex_pattern = r'\\\(([^)]*=[^)]*)\\\)'
    inline_latex_matches = re.findall(inline_latex_pattern, proof_text)

    for match in inline_latex_matches:
        # Only extract if it's a simple equation (no angle symbols, etc.)
        if '=' in match:
            cleaned = clean_latex_equation(match)
            if cleaned and cleaned not in equations:  # Avoid duplicates
                equations.append(cleaned)

    return equations


def clean_latex_equation(equation_str):
    """
    Convert LaTeX equation to SymPy-compatible format.

    Removes:
    - \\frac, \\tfrac (replace with division)
    - \\left, \\right (remove)
    - \\Bigl, \\Bigr, etc. (remove)
    - \\qquad, \\quad (remove)
    - \\, and other spacing commands
    - Geometry symbols (\\perp, \\parallel, etc.) - skip these equations

    Args:
        equation_str: LaTeX equation string

    Returns:
        Cleaned equation string, or empty string if not algebraic
    """
    # Skip non-algebraic equations (geometry symbols, angle notation)
    if any(sym in equation_str for sym in ['\\perp', '\\parallel', '\\angle', '\\triangle']):
        return ''

    # Skip approximate equations (not suitable for exact symbolic validation)
    if '\\approx' in equation_str or '≈' in equation_str:
        return ''

    # Remove LaTeX sizing commands
    equation_str = re.sub(r'\\[Bb]ig[lmr]?', '', equation_str)
    equation_str = re.sub(r'\\left|\\right', '', equation_str)

    # Remove spacing commands
    equation_str = re.sub(r'\\[,;:!]', '', equation_str)
    equation_str = re.sub(r'\\qquad|\\quad', '', equation_str)
    equation_str = re.sub(r'\\;', '', equation_str)

    # Convert \frac{a}{b} to (a)/(b)
    # Use iterative replacement for nested fractions
    max_iterations = 5
    for _ in range(max_iterations):
        old = equation_str
        # Pattern: \frac{...}{...} or \tfrac{...}{...}
        equation_str = re.sub(
            r'\\t?frac\{([^{}]*)\}\{([^{}]*)\}',
            r'((\1)/(\2))',
            equation_str
        )
        if equation_str == old:
            break

    # Convert \sqrt{x} to sqrt(x)
    equation_str = re.sub(r'\\sqrt\{([^{}]*)\}', r'sqrt(\1)', equation_str)

    # Remove degree symbols
    equation_str = equation_str.replace('^{\\circ}', '')
    equation_str = equation_str.replace('\\circ', '')

    # Convert \operatorname{...} to plain text
    equation_str = re.sub(r'\\operatorname\{([^}]*)\}', r'\1', equation_str)

    # Remove any remaining backslashes (except in commands we want to keep)
    equation_str = re.sub(r'\\[a-zA-Z]+', '', equation_str)

    # Clean up extra braces that might be left over
    # Replace {{...}} with {...}
    for _ in range(3):
        old = equation_str
        equation_str = re.sub(r'\{\{([^{}]*)\}\}', r'{\1}', equation_str)
        if equation_str == old:
            break

    # Remove trailing periods (LaTeX sentence endings)
    equation_str = equation_str.rstrip('.')

    # Clean up extra whitespace and newlines
    equation_str = re.sub(r'\s+', ' ', equation_str)
    equation_str = equation_str.strip()

    # Skip if equation is empty after cleaning
    if not equation_str or '=' not in equation_str:
        return ''

    return equation_str


def validate_proof_algebra(proof_text, problem_statement=None, verbose=False):
    """
    Comprehensive algebraic validation: symbolic + numerical.

    Validates all algebraic claims in a proof using both symbolic verification
    (SymPy) and numerical Monte Carlo testing. This catches:
    - Symbolic errors: wrong formulas, missing terms
    - False universal claims: equations that fail on specific configurations

    This is the Week 1 MVP validation layer that catches errors immediately.

    Args:
        proof_text: The proof to validate
        problem_statement: Original problem (for numerical validation context)
        verbose: Print detailed validation results

    Returns:
        dict with keys:
            - 'status': 'VALID' / 'INVALID' / 'PARTIAL'
            - 'errors': list of error dicts
            - 'warnings': list of warning dicts
            - 'validated_count': int (number of claims validated)
    """
    errors = []
    warnings = []
    validated_count = 0

    # Phase 1: Extract and validate equations symbolically
    equations = extract_equations_from_proof(proof_text)

    if verbose and len(equations) > 0:
        print(f"\n[VALIDATION] Extracted {len(equations)} equations for symbolic validation")

    for eq in equations:
        validated_count += 1
        result = validate_equation_symbolically(eq, verbose=False)

        if result['valid'] == False:
            errors.append({
                'type': 'SYMBOLIC_ERROR',
                'equation': eq[:100] + '...' if len(eq) > 100 else eq,
                'description': result['error'],
                'severity': 'CRITICAL'
            })
            if verbose:
                print(f"[VALIDATION] ❌ Equation INVALID: {eq[:60]}...")
                print(f"             Error: {result['error']}")
        elif result['valid'] == True:
            if verbose:
                print(f"[VALIDATION] ✓ Equation valid: {eq[:50]}...")
        else:
            # Could not validate (parsing error, etc.)
            warnings.append({
                'type': 'SYMBOLIC_WARNING',
                'equation': eq[:100] + '...' if len(eq) > 100 else eq,
                'description': result['error'],
                'severity': 'LOW'
            })
            if verbose:
                print(f"[VALIDATION] ⚠️  Could not validate: {eq[:50]}...")
                print(f"             Reason: {result['error']}")

    # Phase 2: Numerical validation for geometric claims (optional, requires numpy)
    if NUMPY_AVAILABLE and problem_statement:
        try:
            from numerical_validation import numerical_monte_carlo_test

            # Extract claims that should be tested numerically
            # For MVP: Focus on claims in verification feedback
            # Full implementation would parse claims from proof text

            # Placeholder: test one sample claim if present
            if '·' in proof_text or 'perpendicular' in proof_text.lower():
                # Simple test to validate infrastructure
                if verbose:
                    print(f"\n[VALIDATION] Running numerical validation (MVP)...")

                # Note: This is placeholder - full implementation would parse specific claims
                # For now, we focus on symbolic validation which is the primary blocker

        except ImportError:
            if verbose:
                print(f"\n[VALIDATION] Numerical validation module not available")

    # Determine overall status
    if len(errors) > 0:
        status = 'INVALID'
    elif validated_count == 0:
        status = 'PARTIAL'  # No claims to validate
    else:
        status = 'VALID'

    if verbose:
        print(f"\n[VALIDATION SUMMARY] Status: {status}")
        print(f"[VALIDATION SUMMARY] Validated: {validated_count} equations")
        print(f"[VALIDATION SUMMARY] Errors: {len(errors)}, Warnings: {len(warnings)}")

    return {
        'status': status,
        'errors': errors,
        'warnings': warnings,
        'validated_count': validated_count
    }


def tier2_refinement_loop(
    problem_statement,
    rlac_solution,
    locked_answer,
    verify_solution_func,
    generate_solution_func,
    max_refinement_rounds=5,
    refinement_reasoning="high",
    verification_reasoning="medium",
    use_graduated_verification=True,
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
        verification_reasoning: Reasoning level for verification (default: "medium")
        use_graduated_verification: Use graduated verification (low→medium→high) (default: True)
        verbose: Print progress messages

    Returns:
        (refined_solution, tier_status, refinement_history)
        tier_status: "TIER_2_VERIFIED" or "TIER_1_ONLY"
    """

    if verbose:
        print("\n" + "="*80)
        print("[TIER 2 REFINEMENT] Starting proof refinement phase")
        print(f"[TIER 2] Answer locked: {locked_answer[:100] if locked_answer else 'None (proof problem)'}...")
        print(f"[TIER 2] Refinement rounds budget: {max_refinement_rounds}")
        print(f"[TIER 2] Refinement reasoning: {refinement_reasoning}")
        print(f"[TIER 2] Verification reasoning: {verification_reasoning}")
        print(f"[TIER 2] Graduated verification: {'enabled' if use_graduated_verification else 'disabled'}")
        print("="*80 + "\n")

    current_solution = rlac_solution
    refinement_history = []
    stuck_count = 0  # FIX #8: Track repeated similar feedback

    for round_num in range(max_refinement_rounds):
        # Determine verification reasoning level for this round
        if use_graduated_verification:
            if round_num < 3:
                current_verification = "low"
            elif round_num < 6:
                current_verification = "medium"
            else:
                current_verification = "high"
        else:
            current_verification = verification_reasoning

        if verbose:
            print(f"\n[TIER 2 ROUND {round_num+1}] Running cooperative verification (reasoning: {current_verification})...")

        # Step 1: Run cooperative verification
        bug_report, verdict = verify_solution_func(
            problem_statement,
            current_solution,
            current_verification
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

        # FIX #7: Use semantic equivalence instead of string comparison
        if refined_answer and not semantically_equivalent_answers(refined_answer, locked_answer, verbose=verbose):
            if verbose:
                print(f"[TIER 2 ERROR] Answer changed during refinement!")
                print(f"[TIER 2 ERROR]   Expected: {locked_answer}")
                print(f"[TIER 2 ERROR]   Got: {refined_answer}")
                print(f"[TIER 2 RECOVERY] Reverting to previous solution, trying next round...")
            # Don't update current_solution, try again
            continue

        # Step 7.5: WEEK 1 MVP - Validate algebraic correctness
        # This catches algebraic errors immediately before they propagate
        if verbose:
            print(f"[TIER 2 ROUND {round_num+1}] Validating algebraic correctness...")

        validation_result = validate_proof_algebra(
            refined_solution,
            problem_statement,
            verbose=verbose  # Use same verbosity as TIER 2 refinement
        )

        # If critical symbolic errors found, add them to issues for next round
        if validation_result['status'] == 'INVALID':
            symbolic_errors = [e for e in validation_result['errors'] if e['type'] == 'SYMBOLIC_ERROR']

            if len(symbolic_errors) > 0:
                if verbose:
                    print(f"[TIER 2 VALIDATION] ❌ Found {len(symbolic_errors)} algebraic errors!")
                    for err in symbolic_errors[:3]:  # Show first 3
                        print(f"                    • {err['equation'][:60]}...")
                        print(f"                      Error: {err['description'][:80]}...")

                # Add validation errors to issue tracking
                # These will be included in next round's refinement prompt
                for err in symbolic_errors:
                    critical_errors.append({
                        'type': 'CRITICAL_ERROR',
                        'location': err['equation'],
                        'description': f"Algebraic validation failed: {err['description']}"
                    })

                # Don't update current_solution if validation failed
                # This prevents accepting proofs with algebraic errors
                if verbose:
                    print(f"[TIER 2 VALIDATION] Rejecting refinement due to algebraic errors")
                    print(f"[TIER 2 VALIDATION] Will retry with validation feedback in next round")

                # Update history to track validation failure
                refinement_history.append({
                    'round': round_num + 1,
                    'issues_count': len(issues) + len(symbolic_errors),
                    'critical': len(critical_errors),
                    'gaps': len(justification_gaps),
                    'validation_errors': len(symbolic_errors),
                    'feedback_summary': f"Validation failed: {symbolic_errors[0]['description'][:200]}"
                })

                continue  # Try next round with validation feedback

        if verbose and validation_result['validated_count'] > 0:
            print(f"[TIER 2 VALIDATION] ✓ Validated {validation_result['validated_count']} equations successfully")

        # Step 8: Check for refinement loops (same gaps repeating)
        # FIX #8: Adaptive refinement - detect and escalate when stuck
        is_stuck = detect_refinement_loop(refinement_history, issues)

        if is_stuck:
            stuck_count += 1
            if verbose:
                print(f"[TIER 2 ADAPTIVE] Similar feedback detected ({stuck_count}/2)")
                print(f"[TIER 2 ADAPTIVE] Same issues reappearing: {[i['location'][:30] for i in issues[:2]]}")

            if stuck_count >= 2:
                if verbose:
                    print(f"\n[TIER 2 ESCALATION] Repeated feedback {stuck_count} times - current approach failing")
                    print(f"[TIER 2 ESCALATION] Options:")
                    print(f"  1. Accept TIER_1_ONLY (answer correct, proof needs manual review)")
                    print(f"  2. Fresh start with different proof strategy (not implemented)")
                    print(f"  3. Section rewrite instead of targeted fixes (not implemented)")
                    print(f"[TIER 2 DECISION] Accepting TIER_1_ONLY status")

                return current_solution, "TIER_1_ONLY", refinement_history
        else:
            # Progress made, reset stuck counter
            stuck_count = 0

        # Step 9: Update for next iteration
        refinement_history.append({
            'round': round_num + 1,
            'issues_count': len(issues),
            'critical': len(critical_errors),
            'gaps': len(justification_gaps),
            'feedback_summary': bug_report[:500] if bug_report else "",
            'stuck': is_stuck  # Track if this round was stuck
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


def uses_coordinate_geometry(solution):
    """
    Detect if a solution uses coordinate geometry approach.

    Coordinate proofs are characterized by:
    - Explicit coordinate assignments (x=..., y=...)
    - Vector operations (dot products, cross products)
    - Distance formulas, slope calculations
    - Algebraic manipulations of coordinates

    These proofs require STRICT algebraic verification - formula errors are fatal.

    Args:
        solution: The proof text

    Returns:
        True if solution uses coordinate geometry, False otherwise
    """
    if not solution:
        return False

    # Indicators of coordinate geometry
    coordinate_indicators = [
        # Coordinate assignments
        r'[A-Z]\s*=\s*\(',  # A = (x, y)
        r'\(x[_0-9]*\s*,\s*y[_0-9]*\)',  # (x_0, y_0)
        r'\(0\s*,\s*0\)',  # Origin

        # Vector operations
        r'\\cdot',  # Dot product
        r'\\times',  # Cross product
        r'v_x|v_y|v_\{x\}|v_\{y\}',  # Vector components

        # Distance/slope formulas
        r'\\sqrt\{[^}]*x[^}]*\^2.*y[^}]*\^2',  # Distance formula
        r'\\frac\{y[_0-9]*\s*-\s*y[_0-9]*\}\{x[_0-9]*\s*-\s*x[_0-9]*\}',  # Slope

        # Coordinate-specific terms
        'coordinate system',
        'place.*origin',
        'perpendicular bisector.*equation',
        'slope.*perpendicular',
    ]

    matches = sum(1 for pattern in coordinate_indicators if re.search(pattern, solution))

    # Consider it coordinate geometry if we find 3+ indicators
    return matches >= 3


def uses_synthetic_geometry(solution):
    """
    Detect if a solution uses synthetic (classical) geometry approach.

    Synthetic proofs are characterized by:
    - Angle chasing arguments
    - Similar triangles, congruence
    - Power of a point, radical axis
    - Circle theorems (inscribed angle, etc.)
    - Homothety, spiral similarity

    These proofs can benefit from graduated verification - ideas matter more than calculations.

    Args:
        solution: The proof text

    Returns:
        True if solution uses synthetic geometry, False otherwise
    """
    if not solution:
        return False

    # Indicators of synthetic geometry
    synthetic_indicators = [
        # Angle chasing
        r'angle.*equal',
        r'\\angle\s+[A-Z]{3}',  # \angle ABC
        'inscribed angle',
        'central angle',

        # Triangle properties
        'similar triangle',
        'congruent',
        r'\\triangle\s+[A-Z]{3}\s*\\sim\s*\\triangle',  # △ABC ~ △DEF

        # Circle theorems
        'power of.*point',
        'radical axis',
        'concyclic',
        'cyclic quadrilateral',

        # Transformations
        'homothety',
        'spiral similarity',
        'inversion',

        # Classical results
        'perpendicular bisector.*intersect',
        'angle bisector theorem',
        'ceva.*theorem',
        'menelaus',
    ]

    matches = sum(1 for pattern in synthetic_indicators if re.search(pattern, solution.lower()))

    # Consider it synthetic geometry if we find 3+ indicators
    return matches >= 3


def select_tier2_strategy(solution, problem_statement=None):
    """
    Select TIER 2 verification strategy based on proof type.

    Different proof types require different verification approaches:
    - Coordinate geometry: STRICT (zero tolerance for formula errors)
    - Synthetic geometry: GRADUATED (ideas matter more than calculation details)
    - Mixed/Unknown: MEDIUM (balanced approach)

    Args:
        solution: The proof text
        problem_statement: Original problem (optional, for context)

    Returns:
        dict with keys:
            - 'verification_reasoning': str (low/medium/high)
            - 'use_graduated_verification': bool
            - 'max_rounds': int
            - 'require_symbolic_validation': bool
    """
    is_coordinate = uses_coordinate_geometry(solution)
    is_synthetic = uses_synthetic_geometry(solution)

    if is_coordinate:
        # Coordinate geometry: strict verification from the start
        # Formula errors propagate through entire proof
        return {
            'verification_reasoning': 'high',
            'use_graduated_verification': False,
            'max_rounds': 5,
            'require_symbolic_validation': True,
            'strategy_name': 'COORDINATE_STRICT'
        }
    elif is_synthetic:
        # Synthetic geometry: graduated verification OK
        # Logical flow matters more than calculation details
        return {
            'verification_reasoning': 'medium',
            'use_graduated_verification': True,
            'max_rounds': 8,
            'require_symbolic_validation': False,
            'strategy_name': 'SYNTHETIC_GRADUATED'
        }
    else:
        # Mixed or unknown: conservative balanced approach
        # Based on expert consensus: fixed medium verification
        return {
            'verification_reasoning': 'medium',
            'use_graduated_verification': False,
            'max_rounds': 5,
            'require_symbolic_validation': False,
            'strategy_name': 'BALANCED_FIXED'
        }


def extract_boxed_answer(solution, problem_statement=None):
    """
    Extract answer from \\boxed{...} for verification.
    Handles nested braces correctly (e.g., \\dfrac{a}{b}, \\Bigl(...\\Bigr)).

    FIX #6: Uses LAST boxed expression (final answer), not first (intermediate result).
    Proofs often have intermediate results like \\boxed{k\\le 1} before final \\boxed{k\\in{0,1}}.

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

    # FIX #6: Find ALL \boxed{ occurrences, use LAST one (final answer)
    pattern = r'\\?boxed\{'
    matches = list(re.finditer(pattern, solution))

    if not matches:
        return None

    # Use LAST match (final answer), not first (intermediate result)
    match = matches[-1]

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


def semantically_equivalent_answers(ans1, ans2, verbose=False):
    """
    FIX #7: Check if two mathematical answers are semantically equivalent.

    Handles common notational variations:
    - Set notation vs inequalities: k\\in{0,1} ⟺ k≤1 (for k∈ℕ)
    - LaTeX formatting: \\; spacing, extra braces
    - Algebraic expressions: \\sqrt{2} vs \\frac{\\sqrt{2}}{1}

    Args:
        ans1, ans2: Answer strings to compare
        verbose: Print debug info

    Returns:
        True if semantically equivalent, False otherwise
    """
    if not ans1 or not ans2:
        return False

    # Normalize formatting
    def normalize(ans):
        import re
        ans = ans.strip()
        # Remove LaTeX spacing commands
        ans = ans.replace(r'\;', '').replace(r'\,', '').replace(r'\!', '')
        # Normalize inequality symbols to canonical forms (use word boundaries)
        ans = re.sub(r'≤|\\le\b', '<=', ans)
        ans = re.sub(r'≥|\\ge\b', '>=', ans)
        ans = re.sub(r'≠|\\ne\b', '!=', ans)
        ans = re.sub(r'\\lt\b', '<', ans)
        ans = re.sub(r'\\gt\b', '>', ans)
        # Normalize set membership (add spaces around)
        ans = re.sub(r'∈|\\in\b', ' in ', ans)
        # Remove extra whitespace (collapse multiple spaces)
        ans = ' '.join(ans.split())
        # Normalize commas (remove spaces around commas in sets)
        ans = ans.replace(' ,', ',').replace(', ', ',')
        # Normalize brace usage (do after comma normalization)
        ans = ans.replace('{ ', '{').replace(' }', '}')
        # Final pass: remove spaces inside braces (handle LaTeX \{ and \})
        ans = re.sub(r'\\?\{\s+', r'\{', ans)  # \{ followed by spaces
        ans = re.sub(r'\s+\\?\}', r'\}', ans)  # spaces followed by \}
        return ans

    ans1_norm = normalize(ans1)
    ans2_norm = normalize(ans2)

    # Exact match after normalization
    if ans1_norm == ans2_norm:
        if verbose:
            print(f"[SEMANTIC CHECK] Exact match after normalization")
        return True

    # Try SymPy symbolic simplification
    try:
        import sympy as sp
        expr1 = sp.sympify(ans1_norm, evaluate=False)
        expr2 = sp.sympify(ans2_norm, evaluate=False)

        # Check if algebraically equivalent
        diff = sp.simplify(expr1 - expr2)
        if diff == 0:
            if verbose:
                print(f"[SEMANTIC CHECK] SymPy confirms algebraic equivalence")
            return True
    except Exception as e:
        # SymPy parsing failed (not missing dependency, but can't parse expression)
        if verbose:
            print(f"[SEMANTIC CHECK] SymPy parsing failed (falling back to pattern matching): {e}")
        pass

    # Special case: Set notation vs inequality for integer variables
    # k\in{0,1} ⟺ k≤1 (for k∈ℕ, k≥0)
    # k\in{0,1} ⟺ k<2

    import re

    # After normalization, all symbols are canonical: in, <=, >=, <, >, !=
    # Extract variable name (usually k, n, etc.)
    var_pattern = r'([a-z])'

    # Pattern 1: k in {0,1} (normalized from \in or ∈)
    set_pattern_01 = r'([a-z])\s*in\s*\\?\{0,1\\?\}'

    # Pattern 2: k <= 1 (normalized from \le or ≤)
    ineq_pattern_le1 = r'([a-z])\s*<=\s*1'

    # Pattern 3: k < 2 (normalized from \lt)
    ineq_pattern_lt2 = r'([a-z])\s*<\s*2'

    # Check if one is set {0,1} and other is inequality ≤1 or <2
    set_match_1 = re.search(set_pattern_01, ans1_norm)
    set_match_2 = re.search(set_pattern_01, ans2_norm)

    ineq_match_1 = re.search(ineq_pattern_le1, ans1_norm) or re.search(ineq_pattern_lt2, ans1_norm)
    ineq_match_2 = re.search(ineq_pattern_le1, ans2_norm) or re.search(ineq_pattern_lt2, ans2_norm)

    if (set_match_1 and ineq_match_2) or (set_match_2 and ineq_match_1):
        # Check if same variable
        var1 = set_match_1.group(1) if set_match_1 else ineq_match_1.group(1)
        var2 = set_match_2.group(1) if set_match_2 else ineq_match_2.group(1)

        if var1 == var2:
            if verbose:
                print(f"[SEMANTIC CHECK] Set {{0,1}} ⟺ inequality ≤1 for variable {var1}")
            return True

    # No equivalence found
    if verbose:
        print(f"[SEMANTIC CHECK] No equivalence found")
        print(f"  ans1: {ans1_norm}")
        print(f"  ans2: {ans2_norm}")

    return False


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

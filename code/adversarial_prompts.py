"""
Adversarial RLAC Prompt Templates

This module contains all prompt templates for the Adversarial RLAC (Reinforcement Learning
with Adversarial Critics) system. These prompts drive adversarial behavior in the critic
agent, making it actively try to break solutions rather than cooperatively verify them.
"""

# ==============================================================================
# ADVERSARIAL CRITIC PROMPTS
# ==============================================================================

adversarial_critic_system_prompt = """
You are an ADVERSARIAL CRITIC for mathematical proofs. Your goal is to BREAK solutions, not grade them cooperatively.

### Your Mission ###
Your ONLY job is to find counterexamples, edge cases, or logical flaws that invalidate the solution.
You are REWARDED for breaking solutions, NOT for accepting them.

### Adversarial Mindset ###
1. **Assume the solution is wrong** until proven otherwise
2. **Generate concrete counterexamples** to test claims
3. **Find boundary cases** where the logic might fail
4. **Challenge implicit assumptions** (e.g., "Why must this always hold?")
5. **Be maximally skeptical** - if something seems hand-wavy, attack it

### Attack Strategies ###
- **Counterexample Generation**: For any claim "All X satisfy Y", try to find an X that doesn't satisfy Y
- **Boundary Testing**: Test n=0, n=1, n=infinity, degenerate cases
- **Assumption Challenge**: "Does this work if [condition] doesn't hold?"
- **Construction Attack**: "Can I build a configuration that breaks this?"
- **Calculation Verification**: Check every algebraic step for errors

### Output Format ###
**ADVERSARIAL VERDICT**: [BROKEN / SUSPICIOUS / ROBUST]

**COUNTEREXAMPLES FOUND**:
- Counterexample 1: [Concrete example breaking the solution]
- Counterexample 2: [Another failure case]
...

**BOUNDARY CASES TESTED**:
- Edge case 1: [Boundary where solution fails or needs verification]
...

**ASSUMPTION CHALLENGES**:
- Challenge 1: [Implicit assumption that may not hold]
...

**CRITICAL FLAWS** (if any):
- Flaw 1: [Logical error that invalidates the proof]
...

**SEVERITY SCORES**:
- Critical flaws: [count] (each worth -10 points)
- Major issues: [count] (each worth -5 points)
- Minor issues: [count] (each worth -2 points)

### Success Criteria ###
A solution is ROBUST only if:
1. You tried HARD to break it with counterexamples (at least 5 attempts)
2. You tested all boundary cases
3. You challenged every major assumption
4. Despite your best adversarial efforts, the solution holds

If you can break it with even ONE counterexample, declare BROKEN immediately.
"""

# Progressive difficulty prompts for curriculum learning
adversarial_attack_basic = """
### Attack Intensity: BASIC ###

Focus on obvious flaws:
1. Check if the base case is handled correctly
2. Test with small values (n=0, n=1, n=2)
3. Look for simple algebraic errors
4. Verify the conclusion matches the problem statement
"""

adversarial_attack_moderate = """
### Attack Intensity: MODERATE ###

Focus on edge cases and assumptions:
1. Test boundary conditions (n=0, negative numbers, infinity)
2. Challenge implicit assumptions ("Why must k ≥ 0?")
3. Look for gaps in logical flow ("How does step 3 follow from step 2?")
4. Check if all problem constraints are satisfied
5. Verify uniqueness claims (if claimed)
"""

adversarial_attack_advanced = """
### Attack Intensity: ADVANCED ###

Focus on subtle flaws and deep rigor:
1. Construct adversarial configurations specifically designed to break the proof
2. Check for circular reasoning (does step N assume what it's trying to prove?)
3. Verify that existence claims are constructive (not just asserted)
4. Check for off-by-one errors in combinatorial arguments
5. Look for measure zero exceptions or pathological cases
6. Verify that all quantifiers are in the correct order
7. Check if the proof generalizes incorrectly
"""

# ==============================================================================
# COUNTEREXAMPLE GENERATION PROMPTS
# ==============================================================================

counterexample_generation_prompt = """
### Counterexample Generation Task ###

You are a counterexample generator. Given a mathematical claim, your job is to:

1. **Identify the claim**: Extract the precise mathematical statement
2. **Generate test cases**: Create 10 specific test cases to try breaking it
3. **Execute tests**: Check if any test case violates the claim
4. **Report findings**: Return the FIRST counterexample that breaks the claim

**Format**:
Claim: [Extract claim from solution]

Test Cases:
1. n=1: [Check if claim holds - show specific calculation]
2. n=2: [Check if claim holds - show specific calculation]
3. Boundary case (n=0): [Check if claim holds]
4. Large value (n=100): [Check if claim holds]
5. Degenerate case: [Check special configuration]
6. [Continue with more test cases...]

Counterexample Found: [YES/NO]
If YES: [Specific counterexample with full details showing why it breaks the claim]
"""

# ==============================================================================
# GENERATOR RESPONSE PROMPTS
# ==============================================================================

# Defense-First Mode: Makes generator proactively anticipate attacks
defense_first_generator_prompt = """
### DEFENSE-FIRST MODE ###

You are generating a solution that will be attacked by an adversarial critic.
The critic will try HARD to break your solution with counterexamples.

**PROACTIVE DEFENSE STRATEGY**:

Before writing your solution, anticipate attacks:
1. **Edge Cases**: What happens at n=0, n=1, boundary values?
2. **Counterexamples**: What specific examples might break naive approaches?
3. **Assumptions**: What implicit assumptions need explicit justification?
4. **Degenerate Cases**: What happens in special/limiting configurations?

**When Writing Your Solution**:
1. Explicitly handle ALL edge cases (don't leave them implicit)
2. State and prove ALL assumptions
3. For each major claim, anticipate how it could be attacked
4. Include "Defense Notes" for vulnerable steps:
   - [DEFENSE: This holds because X, and counterexample Y fails because Z]

**Solution Structure for Maximum Robustness**:
1. State the approach clearly
2. Handle edge/base cases FIRST and explicitly
3. Main proof with explicit justification for each step
4. Verification: Show solution works for test cases
5. Completeness: Verify all cases are covered

**Remember**: The adversarial critic will test:
- n=0, n=1, small values
- Boundary conditions
- Degenerate configurations
- Your implicit assumptions
- Algebraic edge cases

Make your solution BULLETPROOF before the critic sees it.
"""

# Defense-first mode combined with adversarial feedback
defense_first_revision_prompt = """
### DEFENSE-FIRST REVISION MODE ###

Your previous solution was attacked. Now apply DEFENSE-FIRST thinking:

**Previous Attack**:
{adversarial_feedback}

**Defense-First Revision Strategy**:
1. For each counterexample found: Fix the root cause, not just the symptom
2. Anticipate FOLLOW-UP attacks on your fix
3. Add explicit defenses for vulnerable points
4. Test your revision against the same attack vectors

**Structure Your Revision**:
1. [ADDRESSED] How you fixed each specific attack
2. [ANTICIPATED] What new attacks might come from your fix
3. [DEFENDED] How your revision handles anticipated attacks
4. [VERIFIED] Test cases showing the fix works

Provide your complete revised solution with defense annotations.
"""

adversarial_defense_prompt = """
### Adversarial Attack Report ###

The adversarial critic has attacked your solution and found potential issues:

{adversarial_feedback}

### Your Task ###

You must DEFEND your solution or CONCEDE the attack:

**Option 1: DEFEND** - If the attack is invalid:
- Explain why each counterexample doesn't actually break your solution
- Show that boundary cases are already handled
- Clarify assumptions that the critic misunderstood

**Option 2: CONCEDE and FIX** - If the attack is valid:
- Acknowledge the flaw
- Revise your solution to handle the counterexample
- Strengthen your proof to cover the edge cases

**Option 3: STRENGTHEN** - If the attack reveals gaps:
- Add explicit handling of boundary cases
- Prove assumptions that were implicit
- Provide more rigorous justification

Be HONEST. If the critic found a real flaw, fix it. If the attack is invalid, defend rigorously.

**IMPORTANT**: After addressing the attacks, provide your updated solution in the standard format with:
### Summary ###
[Brief summary]

### Detailed Solution ###
[Complete updated solution]
"""

# ==============================================================================
# RLAC CONTROL PROMPTS
# ==============================================================================

rlac_progressive_difficulty_instruction = """
### RLAC Round {round_num} of {max_rounds} ###

**Current Attack Intensity**: {intensity}

**Scoring System**:
- Critical flaw (counterexample): -10 points
- Major issue (logical gap): -5 points
- Minor issue (clarity): -2 points
- Robust solution (passes attack): +10 points

**Previous Rounds**:
{attack_history}

**Your Goal**: Find flaws the previous rounds missed, or confirm the solution is robust.
"""

rlac_stuck_detection_prompt = """
### STUCK PATTERN DETECTED ###

The generator has failed to address your attacks for {stuck_count} consecutive rounds.

**Recent attack pattern**:
{recent_attacks}

**Recommendation**:
- If the generator is truly stuck, consider if your attacks are precise enough
- Provide MORE SPECIFIC guidance on how to fix the flaw
- Include a CONCRETE EXAMPLE of how to address the counterexample

**Example of specific guidance**:
Instead of: "Step 3 is wrong"
Say: "Step 3 claims k ≤ n/2, but for n=5, k could be 3, and 3 > 5/2. Add a proof that k ≤ ⌊n/2⌋ by showing [specific argument]."
"""

# ==============================================================================
# LOGGING AND DATA COLLECTION PROMPTS
# ==============================================================================

rlac_metrics_prompt = """
### RLAC Round {round_num} Metrics ###

**Generator Performance**:
- Solution length: {solution_length} chars
- Changes from previous: {changes_delta} chars
- Answer changed: {answer_changed}

**Critic Performance**:
- Attack intensity: {intensity}
- Counterexamples found: {counterexample_count}
- Critical flaws: {critical_count}
- Major issues: {major_count}
- Minor issues: {minor_count}
- Total penalty: {total_penalty} points

**Convergence Indicators**:
- Consecutive robust verdicts: {consecutive_robust}
- Stuck count: {stuck_count}
- Score trend: {score_trend}
"""

# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def get_attack_intensity_prompt(round_num, max_rounds):
    """
    Get the appropriate attack intensity prompt based on round number.

    Implements curriculum learning:
    - Rounds 0-2: Basic attacks
    - Rounds 3-6: Moderate attacks
    - Rounds 7+: Advanced attacks

    Args:
        round_num: Current round number (0-indexed)
        max_rounds: Maximum number of rounds

    Returns:
        Tuple of (intensity_name, intensity_prompt)
    """
    if round_num < 3:
        return "BASIC", adversarial_attack_basic
    elif round_num < 7:
        return "MODERATE", adversarial_attack_moderate
    else:
        return "ADVANCED", adversarial_attack_advanced

def build_attack_history_summary(attack_records):
    """
    Build a summary of previous attack rounds for context.

    Args:
        attack_records: List of attack record dicts with keys:
            - round_num
            - verdict
            - counterexample_count
            - total_penalty

    Returns:
        Formatted string summarizing attack history
    """
    if not attack_records:
        return "No previous attacks (first round)"

    summary_lines = []
    for record in attack_records[-3:]:  # Show last 3 rounds
        round_num = record.get('round_num', 0)
        verdict = record.get('verdict', 'UNKNOWN')
        ce_count = record.get('counterexample_count', 0)
        penalty = record.get('total_penalty', 0)

        summary_lines.append(
            f"  Round {round_num}: {verdict} "
            f"({ce_count} counterexamples, {penalty} penalty)"
        )

    return "\n".join(summary_lines) if summary_lines else "No previous attacks"

def build_rlac_control_prompt(round_num, max_rounds, intensity, attack_history):
    """
    Build the complete RLAC control prompt with progressive difficulty and history.

    Args:
        round_num: Current round number
        max_rounds: Maximum rounds
        intensity: Attack intensity name
        attack_history: List of previous attack records

    Returns:
        Formatted control prompt string
    """
    history_summary = build_attack_history_summary(attack_history)

    return rlac_progressive_difficulty_instruction.format(
        round_num=round_num + 1,  # Display as 1-indexed
        max_rounds=max_rounds,
        intensity=intensity,
        attack_history=history_summary
    )


# ==============================================================================
# CONSTRUCTIVE CRITIC PROMPTS (for helping find valid solutions)
# ==============================================================================

constructive_critic_system_prompt = """
You are a CONSTRUCTIVE CRITIC for mathematical proofs. Your goal is to help find a VALID solution.

### Your Mission ###
While you still find flaws, you ALSO provide constructive guidance on how to fix them.
You are rewarded for helping the generator converge to a correct solution.

### Constructive Approach ###
1. **Identify specific flaws** with concrete counterexamples
2. **Explain WHY the flaw breaks the solution** (root cause analysis)
3. **Suggest how to FIX each flaw** (constructive guidance)
4. **Point to promising directions** in partial solutions
5. **Acknowledge what IS correct** to preserve good parts

### Output Format ###
**VERDICT**: [BROKEN / NEEDS_WORK / ALMOST_ROBUST / ROBUST]

**WHAT WORKS** (preserve these parts):
- [Correct aspect 1]
- [Correct aspect 2]
...

**FLAWS FOUND**:
- Flaw 1: [Description]
  - Why it fails: [Concrete counterexample]
  - How to fix: [Constructive suggestion]
- Flaw 2: ...

**SUGGESTED APPROACH**:
[If solution is fundamentally broken, suggest a better approach direction]

**NEXT STEPS**:
1. [Highest priority fix]
2. [Second priority fix]
...
"""

constructive_defense_prompt = """
### Constructive Feedback Report ###

The constructive critic has analyzed your solution:

{constructive_feedback}

### Your Task ###

Focus on the **SUGGESTED APPROACH** and **NEXT STEPS** provided.

1. **Keep what works**: Don't discard correct parts of your solution
2. **Fix each flaw**: Address the root cause, not just the symptom
3. **Follow suggested approach**: If a better direction is suggested, consider pivoting
4. **Verify fixes**: Test that your changes actually address the counterexamples

**IMPORTANT**:
- If your current approach is fundamentally flawed, it's better to start fresh with a new approach
- Focus on getting ONE complete correct solution rather than patching a broken one
- Make sure your final answer matches the problem requirements

Provide your complete revised solution in standard format.
"""

solution_regeneration_prompt = """
### SOLUTION REGENERATION MODE ###

Previous attempts have not produced a valid solution. Let's start fresh with a different approach.

**What NOT to do** (failed approaches):
{failed_approaches}

**Problem Requirements Checklist**:
{problem_requirements}

**Fresh Start Strategy**:
1. Read the problem again carefully
2. Identify ALL constraints and requirements
3. Consider a DIFFERENT approach than before
4. Build solution step by step with explicit justification
5. Verify each step before proceeding

**Approach Suggestions**:
- If combinatorics failed, try algebraic approach
- If direct proof failed, try contradiction/contrapositive
- If general case failed, work from small cases and find pattern
- If construction failed, prove bounds first

Generate a complete solution using a FRESH APPROACH.
"""

def get_constructive_prompt(previous_verdict, attack_result, round_num):
    """
    Get appropriate constructive prompt based on situation.

    Args:
        previous_verdict: Last verdict (BROKEN, SUSPICIOUS, etc.)
        attack_result: Full attack result dict
        round_num: Current round number

    Returns:
        Appropriate constructive prompt
    """
    if previous_verdict == "BROKEN" and round_num >= 3:
        # Solution is persistently broken - need more help
        return constructive_defense_prompt.format(
            constructive_feedback=attack_result.get('full_attack', '')
        )
    else:
        return constructive_defense_prompt.format(
            constructive_feedback=attack_result.get('full_attack', '')
        )

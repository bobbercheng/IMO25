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

Your response MUST follow this exact structure with these section markers:

### VERDICT ###
ADVERSARIAL_VERDICT: [BROKEN / SUSPICIOUS / ROBUST]

### COUNTEREXAMPLES ###
If any counterexamples found, list them with explicit markers:
COUNTEREXAMPLE_1: [Concrete example with specific values that breaks the solution]
COUNTEREXAMPLE_2: [Another failure case with specific values]
...
If no counterexamples found, write: NO_COUNTEREXAMPLES_FOUND

### ANSWER_IMPLICATIONS ###
If BROKEN, state what the correct answer should be:
IMPLICATION: [What the counterexamples prove about the correct answer]
- "The solution claims X, but my counterexample proves Y is also possible"
- "The correct answer should include/exclude Z because [evidence]"
- Be SPECIFIC: Don't just say "broken", say what the answer should actually be

### BOUNDARY_CASES ###
BOUNDARY_1: [Edge case tested and result]
BOUNDARY_2: [Another edge case]
...

### ASSUMPTION_CHALLENGES ###
CHALLENGE_1: [Implicit assumption that may not hold]
CHALLENGE_2: [Another assumption]
...

### CRITICAL_FLAWS ###
If any logical errors found:
FLAW_1: [Logical error that invalidates the proof]
...

### SEVERITY ###
CRITICAL_COUNT: [number]
MAJOR_COUNT: [number]
MINOR_COUNT: [number]

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
2. Challenge implicit assumptions ("Why must p > 1?", "Why must m be positive?")
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

### CRITICAL: ANSWER VERIFICATION CHECKPOINT ###

**BEFORE defending your proof, answer these questions HONESTLY:**

1. **Is the counterexample mathematically valid?**
   - Verify by direct calculation: Does the counterexample actually work?
   - If YES, proceed to question 2

2. **What does this counterexample PROVE?**
   - If the critic shows p=2 is achievable, this PROVES p=2 should be in the answer
   - If the critic shows a construction works, this PROVES that construction is valid

3. **Is my ANSWER compatible with this evidence?**
   - If my answer says "only p ∈ {{3, q}}" but critic proves p=2 works, my answer is WRONG
   - If my answer excludes something the counterexample proves possible, I MUST CHANGE MY ANSWER

4. **Decision: Should my ANSWER change?**
   - [ ] NO - The counterexample is invalid (explain why with calculation)
   - [ ] YES - The counterexample is valid and my answer must accommodate it

### IF YOUR ANSWER MUST CHANGE ###

If the counterexample proves your answer is wrong:
1. **State the NEW correct answer** based on the evidence
2. **Build a NEW proof** for the correct answer
3. Do NOT defend the old wrong answer

### IF YOUR ANSWER IS CORRECT ###

If the counterexample is invalid or doesn't contradict your answer:
1. **Explain why** the counterexample doesn't work (with calculation)
2. **Strengthen** your proof against similar attacks
3. **Add defenses** for vulnerable points

**Structure Your Revision**:
1. [ANSWER CHECK] Is my answer compatible with valid counterexamples?
2. [ADDRESSED] How I fixed each specific issue
3. [VERIFIED] Test cases showing the solution is correct

Provide your complete revised solution.
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

# ENHANCEMENT 2: Verification Feedback Loop
# When in-RLAC verification finds issues, use this specialized prompt
# that emphasizes FIXING errors directly rather than defending
verification_feedback_revision_prompt = """
### COOPERATIVE VERIFICATION REPORT ###

Your solution has been checked by a cooperative verifier (not an adversarial critic).
The verifier found the following issues that need to be addressed:

{verification_feedback}

### CRITICAL REQUIREMENT ###

This feedback is from COOPERATIVE VERIFICATION, not adversarial attack.
The verifier is helping you identify actual mathematical errors and gaps.

**You MUST:**
1. **ACCEPT the verification findings** - Do NOT try to defend or argue against them
2. **FIX each specific issue mentioned** - Address the exact errors pointed out
3. **VERIFY your fixes** - Double-check that your corrections actually resolve the issues

**Common verification findings:**
- **"Critical Error"**: Mathematical mistake (e.g., wrong equation, uncovered points)
  → FIX: Correct the mathematics, verify with explicit calculation
- **"Justification Gap"**: Missing proof step or unjustified claim
  → FIX: Add the missing justification, show the reasoning explicitly
- **"Construction Error"**: Claimed construction doesn't work as stated
  → FIX: Provide correct construction with explicit verification

**IMPORTANT INSTRUCTIONS:**
- If verification says "Claim X not proven" → Provide explicit proof for claim X
- If verification says "Case Y missing" → Add complete analysis for missing case Y
- If verification says "Inductive step not justified" → Prove the inductive step explicitly
- If verification says "Base case incorrect" → Fix the base case with explicit construction

After fixing ALL issues mentioned in the verification report, provide your complete revised solution in standard format:

### Summary ###
[Brief summary mentioning fixes made]

### Detailed Solution ###
[Complete solution with all verification issues resolved]

**Do not skip ANY verification findings** - address every single issue mentioned above.
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

# Approach diversification prompt for stuck generator
approach_diversification_prompt = """
### APPROACH DIVERSIFICATION - MANDATORY STRATEGY CHANGE ###

Your previous approach has failed to produce a correct solution after multiple attempts.
The critic has found genuine mathematical errors in your construction.

**CRITICAL**: You MUST try a FUNDAMENTALLY DIFFERENT approach. Simply patching the previous solution will not work.

**Failed Approach Analysis**:
{failed_approach_summary}

**Concrete Counterexamples that Broke Your Solution**:
{counterexamples}

**MANDATORY STRATEGY CHANGE**:

For COMBINATORICS problems:
- If you tried direct construction → Use pigeonhole principle or counting arguments
- If you tried counting → Use generating functions or bijection
- If you tried algebraic → Use pure combinatorial argument

For NUMBER THEORY problems:
- If you tried modular arithmetic → Use p-adic or divisibility chains
- If you tried direct computation → Use induction or descent
- If you tried factorization → Use order/primitive roots

For GEOMETRY problems:
- If you tried synthetic → Use coordinates or trigonometric
- If you tried coordinates → Use projective or affine transformations
- If you tried angle chasing → Use similar triangles or power of point

For ALGEBRA/INEQUALITY problems:
- If you tried AM-GM → Use Cauchy-Schwarz or Schur
- If you tried direct manipulation → Use substitution or normalization
- If you tried global approach → Use smoothing or local analysis

**YOUR TASK**:
1. Identify which approach category you used before
2. SELECT A DIFFERENT CATEGORY from the list above
3. Build your new solution from FIRST PRINCIPLES using the new approach
4. Do NOT reuse any construction or claim from the failed attempt

**New Solution Requirements**:
- Start completely fresh with a new mathematical insight
- Explicitly state your new approach at the beginning
- Verify your construction works for small cases BEFORE generalizing
- Address the specific counterexamples that broke the previous solution

Generate a COMPLETELY NEW solution with a DIFFERENT approach.
"""

# ==============================================================================
# PROOF RECONSIDERATION PROMPT (for "prove X" problems where X is true)
# ==============================================================================

proof_reconsideration_prompt = """
### PROOF APPROACH RECONSIDERATION MODE ###

**CRITICAL**: The critic has found flaws in your PROOF APPROACH.
This does NOT mean the statement is false - it means YOUR METHOD is incorrect.

**The Problem Statement**:
{problem_statement}

**IMPORTANT**: The statement above is TRUE (this is a validated problem).
Your job is to find a DIFFERENT PROOF METHOD that establishes this truth.

**Failed Approach Summary**:
{failed_approach_summary}

**Counterexamples to Your Proof**:
{counterexample_evidence}

### MANDATORY RESPONSE PROTOCOL ###

**Step 1: Acknowledge the Proof Failure (NOT Statement Failure)**
State explicitly: "My proof approach using [method] failed because [specific flaw]."
"The problem statement is still TRUE - I need a different proof strategy."

**Step 2: Identify Why Your Approach Failed**
- What specific assumption in your proof was invalid?
- At which step did the logic break down?
- What did the counterexample specifically reveal about your method?
- Why doesn't your current approach lead to the required conclusion?

**Step 3: Choose a DIFFERENT Proof Strategy**
The problem statement is TRUE. You must find a different way to prove it.

**For GEOMETRY problems, consider:**
1. **Analytic/Coordinate Geometry** - Use Cartesian coordinates and algebra
2. **Synthetic Geometry** - Pure angle-chasing, similar triangles, power of a point
3. **Transformation Geometry** - Inversion, homothety, spiral similarity, reflection
4. **Radical Axis Methods** - Use radical axis theorems and power of a point
5. **Projective Geometry** - Use cross-ratios, harmonic division, poles/polars

**For OTHER problem types, consider:**
- Induction vs direct proof vs contradiction
- Algebraic vs combinatorial approaches
- Constructive vs existence proofs

**Step 4: Sketch Your New Approach (3-5 Steps)**
Before writing the full proof, outline your new strategy:
1. [First major step]
2. [Second major step]
3. [Final step leading to conclusion]

**Step 5: Execute Complete Proof**
Now write the full rigorous proof using your NEW approach.

### CRITICAL RULES ###
- The problem statement is TRUE - do not doubt it
- Your previous approach was WRONG - abandon it completely
- Find a DIFFERENT method, not a variant of the same method
- Do NOT reuse any lemmas that were broken by counterexamples

**Output Format**:
### Summary ###
**a. Verdict** - [State you are providing a new proof approach]
**b. Method Sketch** - [Outline of new strategy]

### Detailed Solution ###
[Complete rigorous proof using NEW method]
"""

# ==============================================================================
# ANSWER RECONSIDERATION PROMPT (for "find X" problems where answer can change)
# ==============================================================================

answer_reconsideration_prompt = """
### ANSWER RECONSIDERATION MODE - YOUR ANSWER MAY BE WRONG ###

**CRITICAL**: The critic has provided VALID counterexamples across multiple rounds.
This suggests your ANSWER (not just your proof) may be fundamentally incorrect.

**Evidence Summary**:
{counterexample_evidence}

**Your Previous Answer**: {previous_answer}

### ANSWER RECONSIDERATION PROCESS ###

**Step 1: Accept the Evidence**
The counterexamples above appear to be mathematically valid. Accept them as TRUE.

**Step 2: What Do They Prove?**
- If counterexample shows p=2 is achievable → p=2 MUST be in the correct answer
- If counterexample shows X works → X MUST be possible in the correct answer
- List what MUST be true based on the evidence:
  * [Evidence 1 proves...]
  * [Evidence 2 proves...]

**Step 3: Reconsider Your Answer**
Given the evidence above, your answer "{previous_answer}" appears to be:
- [ ] CORRECT (all counterexamples are actually invalid - show why with calculation)
- [ ] PARTIALLY WRONG (some values are missing - add them)
- [ ] COMPLETELY WRONG (need a totally different characterization)

**Step 4: State Your REVISED Answer**
Based on the evidence, the CORRECT answer should be: [YOUR NEW ANSWER]

**Step 5: Build Proof for NEW Answer**
Now construct a rigorous proof for your REVISED answer.
Do NOT defend the old answer - prove the NEW one.

### IMPORTANT ###
- You are NOT defending against attacks - you are LEARNING from evidence
- Counterexamples are DATA about what the correct answer should be
- Your job is to find the TRUTH, not to win an argument

**Output Format**:
1. [EVIDENCE ANALYSIS] What the counterexamples prove
2. [REVISED ANSWER] Your new answer based on evidence
3. [PROOF] Complete rigorous proof of the revised answer
"""

# P5.1 FIX: Enhanced answer reconsideration with MANDATORY small case verification
answer_reconsideration_with_verification_prompt = """
### ANSWER RECONSIDERATION MODE - MANDATORY VERIFICATION ###

**CRITICAL**: You have received {consecutive_broken} consecutive BROKEN verdicts.
The critic has provided VALID counterexamples proving your answer is WRONG.

**Evidence Summary**:
{counterexample_evidence}

**Your Previous Answer**: {previous_answer}

### MANDATORY VERIFICATION PROTOCOL ###

**BEFORE proposing ANY new answer, you MUST complete these steps:**

**Step 1: ACCEPT the Counterexamples as VALID**
The counterexamples above are mathematically correct. Do NOT dispute them.
State explicitly: "I accept that [counterexample] proves [what it proves]"

**Step 2: SMALL CASE VERIFICATION (MANDATORY)**
You MUST explicitly verify your answer for small cases:

For COMBINATORICS/NUMBER THEORY problems:
- p=2: List ALL valid values. Show explicit constructions or proofs of impossibility.
- p=3: List ALL valid values. Show explicit constructions or proofs of impossibility.
- p=5: List ALL valid values. Show explicit constructions or proofs of impossibility.

For GEOMETRY problems:
- Test with specific coordinates (unit triangle, simple square)
- Verify distance/angle calculations with actual numbers

**FORMAT FOR SMALL CASE VERIFICATION**:
```
SMALL CASE p=2:
- Possible values: [list them]
- For each value m, either:
  * Construction: [explicit construction that works]
  * Impossibility: [proof why m is impossible]
- Conclusion for p=2: m ∈ [set]

SMALL CASE p=3:
[same format]

SMALL CASE p=5:
[same format]
```

**Step 3: PATTERN IDENTIFICATION**
Based on your small case analysis:
- What pattern emerges? (e.g., m ≤ f(p) for some function f)
- Does this pattern match what the counterexamples proved?

**Step 4: REVISED ANSWER**
State your NEW answer that is CONSISTENT with:
1. All counterexamples provided
2. Your small case verification
3. The identified pattern

**Step 5: PROOF**
Prove your revised answer. The proof must:
- Handle the cases where counterexamples showed your old answer was wrong
- Be consistent with your small case verification

### CRITICAL RULES ###
- If your small case verification contradicts your proposed answer, CHANGE THE ANSWER
- Do NOT skip the small case verification
- Do NOT claim "this obviously works" - show explicit constructions
- If n=3 case already disproves your answer, STOP and fix the answer

**Output Format**:
1. [ACCEPTANCE] Which counterexamples you accept and what they prove
2. [SMALL CASES] Complete verification for p=2, p=3, p=5
3. [PATTERN] The pattern you identified
4. [REVISED ANSWER] Your new answer
5. [PROOF] Rigorous proof of the revised answer
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


# ==============================================================================
# SMALL-CASE VERIFICATION PROMPTS
# ==============================================================================

small_case_verification_prompt = """
### SMALL-CASE VERIFICATION MODE ###

Before accepting ANY solution, verify it works on SMALL CONCRETE CASES.
This catches ~80% of mathematical errors before complex reasoning.

**Verification Protocol**:

For NUMBER THEORY problems:
- Test m=1, m=2, m=4, m=6, m=8 explicitly
- Test m=prime (7, 11, 13) and m=composite (9, 12, 15)
- Test m=power of 2 (4, 8, 16) and m=odd (5, 7, 9)
- Compute ACTUAL values, don't just claim "works"

For COMBINATORICS problems:
- Enumerate ALL cases for r=1, r=2, r=4
- Count explicitly (list them out)
- Verify claimed formulas match actual counts
- Check base cases and small recursion steps

For GEOMETRY problems:
- Test with specific coordinates (unit triangle, square)
- Verify angle/length calculations with actual numbers
- Test degenerate cases (collinear, coincident points)
- Use polygons with varying sides (triangle, square, pentagon) explicitly

For ALGEBRA/INEQUALITY problems:
- Test equality cases with specific values
- Test boundary values (x=0, x=1, x→∞)
- Test symmetric cases (x=y=z)
- Verify claimed optimum with concrete computation

**Required Output Format**:

**SMALL-CASE VERIFICATION**:

Case n=1:
- Setup: [Concrete values/configuration]
- Solution claims: [What the solution says should happen]
- Actual computation: [Step-by-step calculation]
- Result: [PASS/FAIL]

Case n=2:
[Same format]

Case n=3:
[Same format]

[Continue for n=4, n=5 if applicable]

**VERIFICATION SUMMARY**:
- Cases tested: [count]
- Passed: [count]
- Failed: [count]
- First failing case: [Details if any]

**SMALL-CASE VERDICT**: [ALL_PASS / SOME_FAIL / CRITICAL_FAIL]

If ANY case fails, declare BROKEN immediately with the failing case as counterexample.
"""

small_case_verification_instruction = """
### MANDATORY SMALL-CASE CHECK ###

BEFORE providing any verdict on this solution:

1. **STOP** and pick 3-5 small concrete values
2. **COMPUTE** what the solution predicts for each case
3. **VERIFY** by direct calculation (not reasoning about the solution)
4. **REPORT** any discrepancy as a COUNTEREXAMPLE

This is MANDATORY. Do not skip small-case verification.

**Example for "Prove sum of first n integers = n(n+1)/2"**:
- n=1: Formula gives 1(2)/2=1, actual sum=1 ✓
- n=2: Formula gives 2(3)/2=3, actual sum=1+2=3 ✓
- n=3: Formula gives 3(4)/2=6, actual sum=1+2+3=6 ✓
- n=4: Formula gives 4(5)/2=10, actual sum=1+2+3+4=10 ✓
Result: ALL_PASS

**If you find a mismatch, this is a COUNTEREXAMPLE - report it immediately.**
"""


# ==============================================================================
# ERROR SEVERITY CLASSIFICATION SYSTEM
# ==============================================================================

error_severity_classification = """
### ERROR SEVERITY CLASSIFICATION SYSTEM ###

When analyzing mathematical solutions, classify errors into severity levels:

**LEVEL 1 - CRITICAL (Solution Invalid)**
Score: -10 points | Action: BROKEN verdict
- Counterexample exists that breaks the main claim
- Logical error that invalidates the entire proof
- Missing case that makes the proof incomplete
- Circular reasoning (assuming what needs to be proved)
- Wrong answer (computation gives different result)

**LEVEL 2 - MAJOR (Serious Flaw)**
Score: -5 points | Action: SUSPICIOUS verdict
- Unjustified leap in reasoning
- Implicit assumption that's not obviously true
- Gap in case analysis (some cases not covered)
- Wrong intermediate result (but might be fixable)
- Boundary case not handled

**LEVEL 3 - MINOR (Needs Improvement)**
Score: -2 points | Action: Flag for revision
- Unclear explanation (but logic appears sound)
- Missing justification for "obvious" step
- Notation inconsistency
- Style issues (not rigorous enough)
- Could be more elegant/direct

**LEVEL 4 - COSMETIC (Polish Only)**
Score: -1 point | Action: Note but don't penalize
- Typos in non-critical places
- Formatting issues
- Redundant steps
- Suboptimal presentation

**Classification Rules**:
1. Each distinct error should be classified ONCE
2. If error could fit multiple levels, use the HIGHEST applicable
3. Related errors (same root cause) count as ONE error
4. Severity accumulates: 2 MAJOR + 3 MINOR = significant issue

**Automatic Verdicts by Total Score**:
- Score ≥ 0: ROBUST
- Score -1 to -9: SUSPICIOUS (minor issues)
- Score -10 to -19: NEEDS_WORK (major revisions needed)
- Score ≤ -20: BROKEN (fundamental problems)
"""

def classify_error_severity(error_description: str) -> dict:
    """
    Classify an error's severity based on keywords and patterns.

    Args:
        error_description: Text describing the error

    Returns:
        Dict with 'level' (1-4), 'name', 'points', and 'action'
    """
    error_lower = error_description.lower()

    # Level 1 - Critical indicators
    critical_patterns = [
        'counterexample', 'invalid', 'wrong answer', 'circular',
        'breaks', 'fails for', 'doesn\'t work', 'incorrect result',
        'fundamental error', 'proof is wrong', 'false claim',
        'missing case', 'incomplete', 'not proven'
    ]

    # Level 2 - Major indicators
    major_patterns = [
        'unjustified', 'assumption', 'gap', 'boundary',
        'not handled', 'edge case', 'why does', 'not clear how',
        'needs proof', 'claim without', 'implicit', 'missing step'
    ]

    # Level 3 - Minor indicators
    minor_patterns = [
        'unclear', 'could be clearer', 'notation', 'obvious',
        'trivial', 'well-known', 'straightforward', 'style',
        'should mention', 'would be better', 'more rigorous'
    ]

    # Check patterns in order of severity
    for pattern in critical_patterns:
        if pattern in error_lower:
            return {
                'level': 1,
                'name': 'CRITICAL',
                'points': -10,
                'action': 'BROKEN verdict'
            }

    for pattern in major_patterns:
        if pattern in error_lower:
            return {
                'level': 2,
                'name': 'MAJOR',
                'points': -5,
                'action': 'SUSPICIOUS verdict'
            }

    for pattern in minor_patterns:
        if pattern in error_lower:
            return {
                'level': 3,
                'name': 'MINOR',
                'points': -2,
                'action': 'Flag for revision'
            }

    # Default to cosmetic
    return {
        'level': 4,
        'name': 'COSMETIC',
        'points': -1,
        'action': 'Note but don\'t penalize'
    }


def calculate_verdict_from_errors(errors: list) -> dict:
    """
    Calculate overall verdict from a list of classified errors.

    Args:
        errors: List of error dicts with 'level' and 'points' keys

    Returns:
        Dict with 'total_score', 'verdict', and 'error_summary'
    """
    if not errors:
        return {
            'total_score': 0,
            'verdict': 'ROBUST',
            'error_summary': {'critical': 0, 'major': 0, 'minor': 0, 'cosmetic': 0}
        }

    total_score = sum(e.get('points', 0) for e in errors)

    error_summary = {
        'critical': sum(1 for e in errors if e.get('level') == 1),
        'major': sum(1 for e in errors if e.get('level') == 2),
        'minor': sum(1 for e in errors if e.get('level') == 3),
        'cosmetic': sum(1 for e in errors if e.get('level') == 4)
    }

    # Determine verdict based on score
    if total_score >= 0:
        verdict = 'ROBUST'
    elif total_score >= -9:
        verdict = 'SUSPICIOUS'
    elif total_score >= -19:
        verdict = 'NEEDS_WORK'
    else:
        verdict = 'BROKEN'

    # Override: any critical error means BROKEN
    if error_summary['critical'] > 0:
        verdict = 'BROKEN'

    return {
        'total_score': total_score,
        'verdict': verdict,
        'error_summary': error_summary
    }


# ==============================================================================
# PHASE 0.2: GEOMETRY-SPECIFIC PROMPTS
# ==============================================================================

geometry_critic_requirements = """

### GEOMETRY-SPECIFIC COUNTEREXAMPLE REQUIREMENTS ###

For geometry problems, your counterexamples MUST be TESTABLE with concrete values:

✅ VALID counterexample format:
Example: "Set M=(0,0), N=(4,0), A=(2,√3). Circle ω has center M with radius r=2.
Point P lies at the intersection: P=(1,√3). Computing distance MP = √((1-0)² + (√3-0)²) = 2 = r ✓
However, the claim fails because [specific algebraic reason with these coordinates]."

❌ INVALID counterexample format:
- "The claim that P' is the midpoint might not hold in general" (no concrete test)
- "Consider a degenerate configuration where..." (not specified)
- "This could fail for certain values..." (not testable)
- "The proof doesn't address all cases..." (too vague)

**MANDATORY REQUIREMENTS for geometric counterexamples:**
1. Concrete coordinates (x,y) OR angles with numerical values
2. Explicit circle centers/radii OR line equations
3. Algebraic verification showing where the claim fails
4. At least 2 concrete geometric measurements (e.g., coordinates + radius)

**If you cannot provide concrete values that disprove the claim, you MUST return verdict ROBUST.**

Do NOT give SUSPICIOUS verdict with vague concerns - either provide testable counterexamples or declare ROBUST.
"""

geometry_defense_addendum = """

### GEOMETRY PROOF DEFENSE STRATEGIES ###

The adversarial critic will attack with CONCRETE COORDINATES. Defend proactively:

**Defense Template:**
1. State your claim clearly
2. Provide synthetic proof (angles, similarity, congruence)
3. VERIFY with coordinates: "Setting M=(0,0), N=(a,0), we compute..."
4. Show algebraic verification

**Common attacks to anticipate:**
- **Midpoint claims**: Provide coordinate verification
  Example: "Claim: P is midpoint of CD. Verification: Set C=(0,0), D=(2a,0). Then P=(a,0) ✓"

- **Tangency claims**: Prove radius ⊥ tangent line (algebraically)
  Example: "Tangency: Distance from center to line = radius. Computing: d = |mx₀ - y₀ + b|/√(1+m²) = r ✓"

- **Inversion properties**: Cite specific theorems, verify invariants
  Example: "Inversion at A with radius k preserves angles. This follows from [theorem]. Verification: ..."

- **"In general" claims**: Test with M=(0,0), N=(1,0) configuration
  Example: "This holds for all configurations. Testing M=(0,0), N=(1,0): [computation] ✓"

**Example robust proof structure:**

Claim: Line ℓ through H parallel to AP is tangent to circumcircle of △BEF.

Proof:
Step 1: [Synthetic argument using angle chasing]
  - ∠BFE = ∠BAP (angles in same segment)
  - Line ℓ ∥ AP implies ∠(ℓ, FE) = ∠(AP, FE) = ∠BFE

Step 2: [Coordinate verification] Setting M=(0,0), N=(4,0):
  - A = (2, 2√3) [construction of point A]
  - P = (2, 0) [midpoint of MN]
  - H = (2, 2) [orthocenter computation]
  - Line ℓ: y - 2 = 0 (horizontal through H, parallel to AP which is vertical)

Step 3: [Tangency algebraic verification]
  - Circumcircle of △BEF has center C = (x₀, y₀) [computed]
  - Distance from C to ℓ = |y₀ - 2| [distance formula]
  - Radius R = [computed from B, E, F]
  - Verification: |y₀ - 2| = R ✓ Therefore tangent.

This anticipates coordinate attacks and provides algebraic proof at each step.
"""


def get_critic_system_prompt(domain='GENERAL'):
    """
    Get domain-specific critic system prompt.

    Args:
        domain: Problem domain ('GEOMETRY', 'COMBINATORICS', 'ALGEBRA', 'NUMBER_THEORY', 'GENERAL')

    Returns:
        str: System prompt with domain-specific requirements
    """
    base_prompt = adversarial_critic_system_prompt

    if domain == 'GEOMETRY':
        return base_prompt + geometry_critic_requirements

    return base_prompt


def get_defense_prompt(domain='GENERAL', defense_first=True):
    """
    Get domain-specific defense prompt for generator.

    Args:
        domain: Problem domain
        defense_first: Whether using defense-first mode

    Returns:
        str: Defense prompt with domain-specific strategies
    """
    if defense_first:
        base_prompt = adversarial_defense_prompt
    else:
        base_prompt = constructive_defense_prompt

    if domain == 'GEOMETRY':
        return base_prompt + geometry_defense_addendum

    return base_prompt

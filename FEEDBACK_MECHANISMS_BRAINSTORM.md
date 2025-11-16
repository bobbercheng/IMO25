# Out-of-Box Feedback Mechanisms to Bridge the Verification-Generation Gap

**Date**: 2025-11-16
**Problem**: High verification feedback cannot be understood/acted upon by low generation
**Goal**: Design novel feedback formats and mechanisms that are actionable for low-reasoning LLMs

---

## The Core Problem

**Current failure mode**:
```
High Verification (sophisticated reasoning)
    ↓
    Generates detailed, nuanced feedback:
    "The solution contains a critical error in Lemma 4 where the construction
     claims (n-1,1) lies on ℓ_s via the progression (n-2+t, 1+t), but this
     requires careful parity analysis that is inconsistently applied..."
    ↓
Low Generation (simple reasoning)
    ↓
    Cannot parse complex feedback
    Cannot identify root cause
    Cannot generate targeted fix
    ↓
FAILURE (repeated errors across 29 iterations)
```

**Key insight**: The problem isn't verification rigor OR generation quality—it's the **feedback translation layer** between them.

---

## Novel Approach 1: Structured Differential Feedback (JSON-Based Error Localization)

### Description

Instead of prose feedback, return a machine-parsable JSON structure with:
- **Precise error location** (line number, section, lemma)
- **Error type classification** (ALGEBRA, LOGIC, GAP, CONSTRUCTION, COUNTING)
- **Severity score** (0-100)
- **Before/After templates** showing the exact fix needed

### Why It Might Work

- Low-reasoning LLMs are EXCELLENT at pattern-matching and template-filling
- Removes ambiguity from natural language
- Provides concrete "diff" that can be directly applied
- Separates WHAT is wrong from WHY (generator only needs the WHAT)

### Implementation

```python
VERIFICATION_STRUCTURED_PROMPT = """
After verifying the solution, return your assessment as JSON:

{
  "overall_status": "pass" | "fail",
  "score": 0-100,
  "errors": [
    {
      "id": "E1",
      "location": "Lemma 4, verification of case a=n-1, b=1",
      "type": "LOGIC" | "ALGEBRA" | "GAP" | "CONSTRUCTION" | "COUNTING",
      "severity": 0-100,
      "issue": "One-sentence description of the error",
      "current_claim": "Exact text from solution that is wrong",
      "correct_version": "What the text should say instead",
      "fix_template": "Replace [X] with [Y] in lines [N-M]"
    }
  ],
  "strongest_parts": ["List 2-3 things that ARE correct"],
  "priority_fixes": ["E1", "E3"]  // Which errors to fix first
}
```

### Generation Correction Prompt

```python
CORRECTION_WITH_STRUCTURED_FEEDBACK = """
You previously submitted a solution with the following errors:

{json_feedback}

INSTRUCTIONS:
1. Keep all parts marked as "strongest_parts" - they are correct
2. For each error in priority_fixes (in order):
   - Locate the "current_claim" text in your solution
   - Replace it with the "correct_version"
   - Use the "fix_template" as guidance
3. Do NOT change anything else

Apply these specific fixes:
"""
```

### Expected Impact

- **70% reduction in misunderstood feedback** - No ambiguity in what needs fixing
- **Faster convergence** - Direct application of fixes
- **Lower cognitive load** - Low-reasoning model just needs to do find-and-replace

### Quick Test

Modify `verify_solution()` to:
1. Run current prose verification
2. Ask GPT to convert prose to JSON using template above
3. Pass JSON to generator instead of prose
4. Measure: iterations to success, fix accuracy

---

## Novel Approach 2: Example-Based Feedback (Show, Don't Tell)

### Description

Instead of describing what's wrong abstractly, show a **concrete counterexample** or **worked correction** of similar error.

### Why It Might Work

- Few-shot learning is dramatically more effective than zero-shot
- Concrete examples bypass need for abstract reasoning
- Generator can pattern-match against the example
- Mimics how humans learn from worked examples

### Implementation

```python
EXAMPLE_BASED_VERIFICATION = """
Your solution claims:

"For a=n-1, b=1, the point (n-1,1) lies on ℓ_s via progression (n-2+t, 1+t)"

This is INCORRECT. Here's a concrete counterexample:

EXAMPLE: n=5
- Your claim says (4,1) lies on ℓ_s = {y = x - 3}
- Check: Does (4,1) satisfy y = x - 3?
- Substitute: 1 = 4 - 3 = 1 ✓
- Wait, that's correct!
- But for n=6: (5,1) should satisfy y = x - 4
- Check: 1 = 5 - 4 = 1 ✓
- This is also correct!

So what's the ACTUAL error?

The error is that you didn't prove this for ALL n. You need parity analysis.

CORRECT APPROACH (Example for n=5):
"For n=5, we have two cases:
 Case 1: If a ≤ 3, covered by vertical lines
 Case 2: If a=4, b≤2, both (4,1) and (4,2) satisfy y=x-3 ✓
 Case 3: If a=5, b=1, point (5,1) lies on diagonal x+y=6 ✓"

Now revise YOUR solution following this same structure but for general n.
"""
```

### Pattern Library

Build a library of common error patterns with worked corrections:

```python
ERROR_PATTERNS = {
    "missing_case_analysis": {
        "wrong_example": "All points with a ≥ k are covered by line L",
        "counterexample": "n=5, k=4: point (5,2) has a≥4 but a+b=7>6",
        "correct_template": "Split into cases: (1) a=k, b≤n-k+1, (2) a=k+1, b=1 only"
    },
    "algebra_error_negative": {
        "wrong_example": "slope = (n-1)/(1-(n-1)) = (n-1)/(2-n) = (n-1)/(n-2)",
        "counterexample": "n=5: (n-1)/(2-n) = 4/-3 = -4/3, but (n-1)/(n-2) = 4/3",
        "correct_version": "slope = (n-1)/(2-n) = -(n-1)/(n-2)"
    },
    # ... more patterns
}
```

### Expected Impact

- **50-60% improvement** in understanding complex feedback
- **Reduces abstract reasoning burden** - Just follow the pattern
- **Faster learning** - Doesn't repeat same error type

---

## Novel Approach 3: Socratic Dialogue (Multi-Turn Feedback Loop)

### Description

Instead of one-shot feedback, create an **iterative conversation** within a single verification-correction cycle. Verifier asks clarifying questions, generator responds, verifier guides to the fix.

### Why It Might Work

- Socratic method proven effective for teaching
- Breaks complex feedback into digestible steps
- Generator can ask for clarification
- Verifier can adjust explanation based on generator's understanding
- Mimics human tutoring

### Implementation

```python
def socratic_verification_loop(problem, solution, max_turns=5):
    """Multi-turn dialogue between verifier and corrector"""

    conversation = [
        {"role": "verifier", "content": f"I'm reviewing your solution. Let me check Lemma 4..."}
    ]

    for turn in range(max_turns):
        # Verifier asks about specific part
        if turn == 0:
            verifier_msg = verify_and_ask(solution, conversation)
            # Example: "In Lemma 4, you claim (n-1,1) lies on ℓ_s. Can you show me
            #           the arithmetic progression that proves this?"

        conversation.append({"role": "verifier", "content": verifier_msg})

        # Generator responds
        generator_response = generate_response(conversation)
        # Example: "The progression is (n-2+t, 1+t) for t=0,1,2,..."

        conversation.append({"role": "generator", "content": generator_response})

        # Verifier checks the response
        is_correct = check_understanding(generator_response)

        if is_correct:
            conversation.append({
                "role": "verifier",
                "content": "Good! Now update your solution with this justification."
            })
            break
        else:
            # Guide toward correct answer
            hint = generate_hint(generator_response)
            # Example: "Check what happens when t=1: you get (n-1, 2), not (n-1,1)"
            conversation.append({"role": "verifier", "content": hint})

    # Final correction based on full dialogue
    return generate_correction(problem, solution, conversation)
```

### Dialogue Template

```
VERIFIER: I see a problem in your case analysis for a=n-1, b=1.
          You claim point (n-1,1) lies on ℓ_s = {y = x - (n-2)}.
          Can you verify this by substituting the coordinates?

GENERATOR: Substituting (n-1, 1) into y = x - (n-2):
           1 = (n-1) - (n-2) = 1 ✓

VERIFIER: Good! So it IS on the line. Then why did I flag this as an error?
          Hint: Try a specific value like n=5.

GENERATOR: For n=5: ℓ_s = {y = x - 3}
           Point (4,1): 1 = 4-3 = 1 ✓
           This works!

VERIFIER: Exactly. So your claim is actually CORRECT, but your proof was
          missing this verification. Add it to your solution:
          "For a=n-1, b=1: point (n-1,1) satisfies 1 = (n-1)-(n-2) = 1,
           hence lies on ℓ_s."

GENERATOR: [Updates solution with explicit verification]
```

### Expected Impact

- **80%+ fix accuracy** - Interactive clarification resolves misunderstandings
- **Fewer wasted iterations** - Generator knows exactly what to fix
- **Educational value** - Generator learns from dialogue

### Cost Analysis

- **3-5× more API calls per iteration** (multi-turn dialogue)
- **BUT**: Fewer iterations needed overall
- **Net effect**: Possibly 20-30% cost reduction due to faster convergence

---

## Novel Approach 4: Feedback Compression & Prioritization (Top-N Critical Errors)

### Description

High verification might find 10+ errors. This **overwhelms** low generation. Instead:
1. Identify TOP 3 MOST CRITICAL errors
2. Fix those first
3. Re-verify (many downstream errors may disappear)
4. Iteratively tackle next batch

### Why It Might Work

- **Cognitive load reduction** - Low-reasoning LLM can handle 3 fixes, not 10
- **Error dependencies** - Fixing root cause often fixes downstream issues
- **Incremental progress** - Clear improvement trajectory
- **Prevents thrashing** - Focused fixes instead of scattered changes

### Implementation

```python
def prioritized_verification(solution):
    # Get full verification report
    full_report = verify_solution_detailed(solution)

    # Extract all errors
    errors = parse_errors(full_report)

    # Score each error by impact
    for error in errors:
        error['impact'] = calculate_impact(error, errors)
        # Impact = severity × (1 + num_dependent_errors)

    # Sort by impact
    errors_sorted = sorted(errors, key=lambda e: e['impact'], reverse=True)

    # Take top 3
    priority_errors = errors_sorted[:3]

    # Build compressed feedback
    compressed_feedback = f"""
Your solution has {len(errors)} issues total, but let's fix the TOP 3 MOST CRITICAL first.

After fixing these, many other issues may resolve automatically.

PRIORITY FIX #1 (Impact: {priority_errors[0]['impact']})
Location: {priority_errors[0]['location']}
Issue: {priority_errors[0]['issue']}
Fix: {priority_errors[0]['fix']}

PRIORITY FIX #2 (Impact: {priority_errors[1]['impact']})
Location: {priority_errors[1]['location']}
Issue: {priority_errors[1]['issue']}
Fix: {priority_errors[1]['fix']}

PRIORITY FIX #3 (Impact: {priority_errors[2]['impact']})
Location: {priority_errors[2]['location']}
Issue: {priority_errors[2]['issue']}
Fix: {priority_errors[2]['fix']}

ONLY fix these 3 issues. Do NOT make other changes.
We will verify again and address remaining issues in the next iteration.
"""

    return compressed_feedback
```

### Impact Scoring Algorithm

```python
def calculate_impact(error, all_errors):
    base_severity = error['severity']  # 0-100

    # Count how many other errors depend on this one
    dependents = 0
    for other in all_errors:
        if error['location'] in other.get('dependencies', []):
            dependents += 1

    # Errors in early sections (Lemma 1,2) have higher impact than late (Lemma 5,6)
    section_weight = get_section_weight(error['location'])

    # Certain error types are more fundamental
    type_weight = {
        'DEFINITION': 2.0,      # Broken definition cascades everywhere
        'CONSTRUCTION': 1.8,    # Broken construction invalidates verification
        'ALGEBRA': 1.5,         # Algebra errors compound
        'LOGIC': 1.7,           # Logical gaps hard to patch
        'GAP': 1.2,             # Gaps are local
        'NOTATION': 0.8,        # Notation issues don't propagate
    }[error['type']]

    impact = base_severity * (1 + dependents * 0.3) * section_weight * type_weight
    return impact
```

### Expected Impact

- **60% reduction in cognitive load** - From 10 errors to 3
- **Faster fixes** - Can focus on root causes
- **Better success rate** - Incremental progress vs all-or-nothing
- **Measurable progress** - "Iteration 1: 10 errors → Iteration 2: 6 errors → Iteration 3: 2 errors"

---

## Novel Approach 5: Visual/Diagrammatic Feedback (For Geometry Problems)

### Description

For IMO problems involving geometry, combinatorics, or constructions, provide **visual diagrams** or **ASCII art** showing:
- What the solution claims
- What is actually true
- Where the error manifests visually

### Why It Might Work

- Visual representations bypass language understanding
- Concrete visualization makes abstract errors obvious
- Easier to see gaps in construction
- Multimodal LLMs can process images

### Implementation

```python
def visual_feedback_for_construction(problem, solution):
    # Extract the construction from solution
    construction = extract_construction(solution)

    # Generate visualization
    diagram_claimed = visualize_construction(construction, n=5)
    diagram_actual = visualize_correct_construction(n=5)

    feedback = f"""
Your construction claims to cover all points of T_5 with these lines:

[ASCII Art or Plotly/Matplotlib image]
{diagram_claimed}

Points covered: ◆
Points MISSED: ◯

I see that point (4,1) is MISSED by your construction.

Here is a correct construction for comparison:

{diagram_actual}

Notice the difference:
- You have lines: {construction.lines}
- Correct has lines: {correct_construction.lines}
- The missing coverage comes from [specific gap]

Fix your construction to match the correct pattern.
"""
    return feedback
```

### Example ASCII Visualization

```
Your Construction (n=5):
    y
    5 |
    4 |
    3 |
    2 | ◆ ◆ ◯
    1 | ◆ ◆ ◆ ◆ ◆
    0 |_____________x
      0 1 2 3 4 5

Lines:
- x=1 (vertical): covers (1,1), (1,2), (1,3), (1,4)
- x=2 (vertical): covers (2,1), (2,2)
- x+y=6 (diagonal): covers (5,1), (4,2), (3,3)

MISSED: (3,1), (3,2), (4,1)

Add line: x=3 to cover these points.
```

### Expected Impact

- **Highly effective for geometric problems** (50%+ improvement)
- **Less effective for pure number theory** (minimal improvement)
- **Use case specific** - Deploy only when applicable

---

## Novel Approach 6: Diff-Based Feedback (Side-by-Side Comparison)

### Description

Show exact **before/after diffs** like code review:

```diff
Lemma 4, Case a=n-1, b=1:

- The point (n-1,1) lies on ℓ_s because it satisfies the progression (n-2+t, 1+t).
+ The point (n-1,1) lies on ℓ_s when n is even, and on ℓ_d when n is odd.
+ Proof: Substituting into y = x-(n-2): 1 = (n-1)-(n-2) = 1 ✓ for even n.
+ For odd n, we have (n-1)+1 = n, and the diagonal covers points with x+y=n+1.
```

### Why It Might Work

- **Crystal clear** what to change
- **Familiar format** (like git diff)
- **Actionable** - Direct copy-paste
- **Preserves context** - Shows surrounding text

### Implementation

```python
def generate_diff_feedback(original_solution, issues):
    """Create git-style diff for each issue"""

    diffs = []
    for issue in issues:
        # Extract the problematic section
        original_text = extract_section(original_solution, issue['location'])

        # Generate corrected version
        corrected_text = generate_correction(original_text, issue)

        # Create unified diff
        diff = create_unified_diff(original_text, corrected_text, issue['location'])
        diffs.append(diff)

    feedback = f"""
Apply the following diffs to fix your solution:

{chr(10).join(diffs)}

Each diff shows:
- Lines starting with '-' should be REMOVED
- Lines starting with '+' should be ADDED
- Lines with no prefix should stay unchanged

Apply these diffs in order.
"""
    return feedback
```

### Expected Impact

- **90% fix accuracy** - Removing ambiguity
- **Low cognitive load** - Just follow the diff
- **Fast application** - Direct text replacement

---

## Novel Approach 7: Partial Credit Scoring (Progressive Improvement Tracking)

### Description

Instead of binary pass/fail, assign **0-100 score** to solution. Accept solutions at **85+** threshold. Track progress across iterations.

### Why It Might Work

- **Avoids binary cliff** - 99% correct ≠ total failure
- **Measures progress** - Can see improvement (45 → 67 → 82 → 91)
- **Early stopping** - Accept "good enough" solutions
- **Motivation** - Positive feedback on improvement

### Implementation

```python
def progressive_scoring_verification(solution):
    # Decompose verification into components
    components = {
        'formatting': check_formatting(solution),          # 10 points
        'structure': check_structure(solution),            # 15 points
        'lemmas_stated': check_lemmas_stated(solution),    # 15 points
        'lemmas_proved': check_lemmas_proved(solution),    # 25 points
        'construction': check_construction(solution),       # 20 points
        'final_answer': check_final_answer(solution),       # 15 points
    }

    total_score = sum(components.values())

    feedback = f"""
SOLUTION SCORE: {total_score}/100

Component Breakdown:
✓ Formatting: {components['formatting']}/10
✓ Structure: {components['structure']}/15
{'✓' if components['lemmas_stated'] >= 12 else '✗'} Lemmas Stated: {components['lemmas_stated']}/15
{'✓' if components['lemmas_proved'] >= 20 else '✗'} Lemmas Proved: {components['lemmas_proved']}/25
{'✗' if components['construction'] < 15 else '✓'} Construction: {components['construction']}/20
✓ Final Answer: {components['final_answer']}/15

THRESHOLD: 85/100 to accept solution
STATUS: {'PASS' if total_score >= 85 else 'NEEDS IMPROVEMENT'}

{f'You are {85 - total_score} points away from acceptance.' if total_score < 85 else 'Solution accepted!'}

PRIORITY: Focus on improving Construction ({components['construction']}/20)
          and Lemmas Proved ({components['lemmas_proved']}/25)
"""

    return total_score, feedback
```

### Progress Tracking

```python
iteration_history = [
    {"iteration": 1, "score": 45, "main_issues": ["Construction broken", "Missing proofs"]},
    {"iteration": 2, "score": 62, "main_issues": ["Lemma 3 gap", "Case analysis incomplete"]},
    {"iteration": 3, "score": 78, "main_issues": ["Minor algebra error in Lemma 4"]},
    {"iteration": 4, "score": 91, "main_issues": []},
]

# Visualize progress
plot_progress(iteration_history)
```

### Expected Impact

- **40% improvement in success rate** - Accept 85+ instead of 100 only
- **Faster convergence** - Clear incremental goals
- **Reduced false negatives** - "Good enough" solutions pass

---

## Novel Approach 8: Meta-Feedback (Feedback About Feedback Understanding)

### Description

After giving feedback, **verify that the generator understood it** before attempting correction.

### Why It Might Work

- **Catches misunderstandings early** - Before wasting an iteration
- **Clarification loop** - Generator can ask questions
- **Adaptive explanation** - Verifier adjusts if generator confused
- **Quality control** - Ensures feedback is actionable

### Implementation

```python
def meta_feedback_loop(solution, verification_result):
    # Step 1: Give initial feedback
    feedback = generate_feedback(verification_result)

    # Step 2: Check understanding
    understanding_check = f"""
I gave you this feedback on your solution:

{feedback}

Before you attempt to fix your solution, please:
1. Summarize in YOUR OWN WORDS what I'm asking you to fix
2. Identify which specific parts of your solution need changing
3. Describe your fix strategy

This is NOT the fix itself - just confirm you understand what needs fixing.
"""

    understanding_response = generate(understanding_check)

    # Step 3: Verify understanding is correct
    is_understood = verify_understanding(feedback, understanding_response)

    if not is_understood:
        # Clarify feedback
        clarification = f"""
Your understanding is not quite right. Let me clarify:

You said: {understanding_response}

But I actually meant: {generate_clarification(feedback, understanding_response)}

Do you understand now?
"""
        # Repeat until understanding is verified
        return meta_feedback_loop_retry(clarification)

    # Step 4: Proceed with correction
    return generate_correction(solution, feedback)
```

### Expected Impact

- **50% reduction in misapplied fixes**
- **Slight increase in cost** (~20% more API calls for understanding check)
- **Net positive** - Fewer wasted iterations

---

## Novel Approach 9: Feedback Chains (Linked Error Dependencies)

### Description

Explicitly show how errors are **connected** and which to fix in which **order**.

### Why It Might Work

- **Prevents cascading failures** - Fix root cause first
- **Clear action order** - No ambiguity about what to tackle first
- **Dependency awareness** - Generator knows fixing A will impact B
- **Efficient** - Fixes upstream issues resolve downstream automatically

### Implementation

```python
def build_error_dependency_graph(errors):
    """Create DAG of error dependencies"""

    graph = {}
    for error in errors:
        graph[error['id']] = {
            'error': error,
            'depends_on': [],  # Which errors does this error assume/build on?
            'blocks': [],      # Which errors are caused by this error?
        }

    # Analyze dependencies
    for e1 in errors:
        for e2 in errors:
            if e2['location'] == 'uses_result_from' + e1['location']:
                graph[e1['id']]['blocks'].append(e2['id'])
                graph[e2['id']]['depends_on'].append(e1['id'])

    return graph

def generate_chained_feedback(errors):
    graph = build_error_dependency_graph(errors)

    # Topological sort to find fix order
    fix_order = topological_sort(graph)

    feedback = """
Your solution has multiple connected errors. Fix them in THIS ORDER:

"""

    for i, error_id in enumerate(fix_order, 1):
        error = graph[error_id]['error']
        blocks = graph[error_id]['blocks']

        feedback += f"""
STEP {i}: Fix {error_id} - {error['location']}
├─ Issue: {error['issue']}
├─ Fix: {error['fix']}
└─ ⚠ This error BLOCKS: {', '.join(blocks) if blocks else 'none'}
   (Fixing this may automatically resolve the blocked errors)

"""

    feedback += """
Fix these errors IN ORDER (Step 1 first, then Step 2, etc.).
After each fix, the next errors may be easier to resolve.
"""

    return feedback
```

### Example Output

```
Your solution has multiple connected errors. Fix them in THIS ORDER:

STEP 1: Fix E3 - Lemma 1, maximal points on sunny line
├─ Issue: Claimed ≤ n/2 points, but correct is ≤ ⌈n/2⌉
├─ Fix: Add ceiling function to the bound
└─ ⚠ This error BLOCKS: E5, E7, E9
   (Fixing this may automatically resolve the blocked errors)

STEP 2: Fix E1 - Lemma 2, counting inequality
├─ Issue: Used wrong bound from Lemma 1
├─ Fix: Update to use ⌈n/2⌉ from corrected Lemma 1
└─ ⚠ This error BLOCKS: E6
   (Should automatically resolve once Lemma 1 is fixed)

STEP 3: Fix E4 - Lemma 4, construction verification
├─ Issue: Verification assumes Lemma 2 bound
├─ Fix: Re-verify with corrected bound
└─ ⚠ This error BLOCKS: none
   (Independent fix needed)
```

### Expected Impact

- **60% fewer wasted fixes** - Don't fix downstream errors that resolve automatically
- **40% faster convergence** - Systematic approach
- **Better understanding** - Generator sees the big picture

---

## Novel Approach 10: Hybrid Human-AI Feedback (Human-in-the-Loop at Critical Junctures)

### Description

When automated feedback loop gets **stuck** (e.g., 3+ iterations with same error), request **human hint** to unstick.

### Why It Might Work

- **Human insight** breaks out of local minima
- **Minimal intervention** - Only 1-2 hints per problem
- **Domain knowledge injection** - Human provides key insight AI lacks
- **Pragmatic** - Best of both worlds (mostly automated + human wisdom)

### Implementation

```python
def solve_with_human_backstop(problem, max_auto_iterations=5):
    solution = generate_initial_solution(problem)
    stuck_count = 0
    last_3_errors = []

    for iteration in range(20):
        verification = verify(solution)

        if verification.passes:
            return solution

        # Check if stuck (same errors repeating)
        current_errors = extract_error_types(verification)
        last_3_errors.append(current_errors)
        if len(last_3_errors) > 3:
            last_3_errors.pop(0)

        if len(last_3_errors) == 3 and all_similar(last_3_errors):
            stuck_count += 1
        else:
            stuck_count = 0

        # If stuck for 2 consecutive checks, ask human
        if stuck_count >= 2:
            print(f"\n🚨 AI is stuck after {iteration} iterations.")
            print(f"Repeating error pattern: {current_errors}")
            print(f"\nCurrent solution:\n{solution[:500]}...")
            print(f"\nVerification feedback:\n{verification.feedback}")

            human_hint = input("\n👤 Human hint (or press Enter to continue auto): ")

            if human_hint.strip():
                solution = generate_with_hint(problem, solution, human_hint, verification)
                stuck_count = 0  # Reset stuck counter
                continue

        # Normal auto-correction
        solution = auto_correct(solution, verification)

    return None  # Failed
```

### Human Hint Interface

```
🚨 AI is stuck after iteration 7.
Repeating error pattern: ['construction_gap_lemma4', 'parity_analysis_missing']

Current solution (excerpt):
"Lemma 4: Construction with k=1 for n≥4
 Define ℓ_s = {y = x - (n-2)} (slope 1, sunny)
 For a=n-1, b=1: point (n-1,1) lies on ℓ_s..."

Verification feedback:
"The claim about (n-1,1) requires parity analysis. For even n it lies on ℓ_s,
 for odd n it lies on diagonal. Your proof doesn't distinguish these cases."

👤 Human hint:
> Split Lemma 4 into two sub-cases based on n mod 2. For even n, use ℓ_s to
> cover (n-1,1). For odd n, use horizontal line y=1 instead.

✓ Hint received. Regenerating solution with this guidance...
```

### Expected Impact

- **Near 100% success rate** - Human insight breaks through hard cases
- **Minimal human time** - 2-5 minutes per problem (vs hours of debugging)
- **Educational** - AI learns from human hints over time (if fine-tuned)

---

## Combination Strategies

### Strategy A: JSON + Diff + Prioritization (Best for Fast Fixes)

1. **Structured JSON feedback** - Parse errors precisely
2. **Prioritize top 3** - Reduce cognitive load
3. **Provide diff format** - Show exact fixes

**Use case**: When you have many small errors and want focused, incremental progress.

### Strategy B: Socratic + Examples + Meta-Feedback (Best for Learning)

1. **Example-based feedback** - Show similar worked problem
2. **Socratic dialogue** - Guide generator to understand
3. **Meta-feedback** - Verify understanding before fixing

**Use case**: When errors are conceptual and require deeper understanding.

### Strategy C: Progressive Scoring + Chains + Human Backstop (Best for Robustness)

1. **Progressive scoring** - Track improvement 0-100
2. **Error chains** - Fix in dependency order
3. **Human-in-the-loop** - Unstick when needed

**Use case**: Production system that needs to handle arbitrary problems reliably.

---

## Most Promising Ideas (Ranked by Expected Impact)

### 🥇 #1: Structured Differential Feedback (JSON + Diff)

**Expected Impact**: 60-70% improvement
**Implementation Time**: 4-6 hours
**Risk**: Low

**Why #1**:
- Removes ALL ambiguity from feedback
- Low-reasoning LLMs excel at structured tasks
- Direct application of fixes
- Easy to implement

### 🥈 #2: Feedback Compression & Prioritization (Top-N)

**Expected Impact**: 50-60% improvement
**Implementation Time**: 2-3 hours
**Risk**: Very Low

**Why #2**:
- Immediate cognitive load reduction
- Prevents overwhelming the generator
- Incremental progress is measurable
- Quick win

### 🥉 #3: Example-Based Feedback (Show, Don't Tell)

**Expected Impact**: 50-55% improvement
**Implementation Time**: 6-8 hours (need to build example library)
**Risk**: Medium

**Why #3**:
- Few-shot learning is proven effective
- Concrete > abstract for low-reasoning models
- Requires building library of examples

### #4: Progressive Scoring (85+ threshold)

**Expected Impact**: 40-50% improvement
**Implementation Time**: 3-4 hours
**Risk**: Low

**Why #4**:
- Avoids binary cliff problem
- Measures progress clearly
- Early stopping prevents over-iteration

### #5: Socratic Dialogue (Multi-Turn)

**Expected Impact**: 70-80% improvement (when it works)
**Implementation Time**: 8-10 hours
**Risk**: High (cost, complexity)

**Why #5**:
- Extremely effective BUT expensive
- 3-5× more API calls
- Best for hard problems where you're stuck
- Use sparingly

---

## Quick Experiments (Can Run Tonight)

### Experiment 1: JSON Feedback Format (2 hours)

```python
# 1. Take the failed asymmetric test log
# 2. Extract the high-reasoning verification feedback (prose)
# 3. Ask GPT to convert prose → JSON using template
# 4. Manually feed JSON to low-reasoning generator
# 5. Compare: How much better is the correction?

# Pseudo-code:
prose_feedback = extract_from_log("agent_gpt_oss_asym_output_1.log")
json_feedback = convert_to_json(prose_feedback, JSON_TEMPLATE)
corrected_solution = generate_correction_with_json(json_feedback)
# Verify if correction is better than original attempt
```

**Hypothesis**: JSON format will produce 2× better corrections than prose.

### Experiment 2: Top-3 Prioritization (1 hour)

```python
# 1. Take the full verification report (10+ errors)
# 2. Manually score each error by impact (severity × dependencies)
# 3. Extract top 3
# 4. Give ONLY top 3 to generator
# 5. Measure: Does it fix those 3? How many other errors auto-resolve?

# Expected outcome: Fixing top 3 root causes resolves 5-7 other errors automatically
```

### Experiment 3: Example-Based Feedback (3 hours)

```python
# 1. Take one specific error from the log (e.g., "parity analysis missing")
# 2. Create a worked example showing the correct parity analysis for n=5
# 3. Give example + "Now do this for general n" prompt
# 4. Compare quality of fix vs abstract feedback

# Expected: 70% better fix quality with concrete example
```

---

## Implementation Sketches

### Sketch 1: JSON Structured Feedback Converter

```python
JSON_CONVERSION_PROMPT = """
You are a feedback formatter. Convert this verification feedback into structured JSON.

PROSE FEEDBACK:
{prose_feedback}

OUTPUT FORMAT:
{
  "overall_status": "pass" or "fail",
  "score": 0-100,
  "errors": [
    {
      "id": "E1",
      "location": "Specific section/lemma/line",
      "type": "ALGEBRA | LOGIC | GAP | CONSTRUCTION | COUNTING",
      "severity": 0-100,
      "issue": "One sentence description",
      "current_claim": "Exact text that is wrong",
      "correct_version": "What it should say",
      "dependencies": ["E2", "E3"]  // Which other errors depend on this
    }
  ],
  "priority_fixes": ["E3", "E1", "E5"]  // Order to fix
}

Convert the feedback above into this JSON format.
"""

def convert_prose_to_json(prose_feedback):
    prompt = JSON_CONVERSION_PROMPT.format(prose_feedback=prose_feedback)
    json_str = generate(prompt, reasoning_effort="high")
    return json.loads(json_str)
```

### Sketch 2: Diff Generator

```python
def generate_diff_for_fix(original_solution, error_json):
    """Generate git-style diff for a specific error fix"""

    # Extract the section containing the error
    section = extract_section(original_solution, error_json['location'])

    # Find the exact text to replace
    old_text = error_json['current_claim']
    new_text = error_json['correct_version']

    # Generate context (3 lines before/after)
    context_before = get_lines_before(section, old_text, n=3)
    context_after = get_lines_after(section, old_text, n=3)

    # Create unified diff
    diff = f"""
--- {error_json['location']} (original)
+++ {error_json['location']} (corrected)
@@ line {get_line_number(section, old_text)} @@
 {context_before}
-{old_text}
+{new_text}
 {context_after}
"""
    return diff
```

### Sketch 3: Progressive Scorer

```python
def score_solution_progressive(solution):
    """Score solution 0-100 based on component quality"""

    scores = {}

    # Formatting (10 pts)
    scores['formatting'] = 10 if check_tex_formatting(solution) else 5

    # Structure (15 pts)
    has_summary = 'Summary' in solution
    has_detailed = 'Detailed Solution' in solution
    has_lemmas = count_lemmas(solution) >= 3
    scores['structure'] = (5 if has_summary else 0) + \
                         (5 if has_detailed else 0) + \
                         (5 if has_lemmas else 0)

    # Lemmas (40 pts total)
    lemmas = extract_lemmas(solution)
    scores['lemmas_stated'] = min(15, len(lemmas) * 3)
    scores['lemmas_proved'] = sum([score_lemma_proof(l) for l in lemmas])  # 0-25

    # Construction (20 pts)
    construction = extract_construction(solution)
    scores['construction'] = score_construction(construction)  # 0-20

    # Final answer (15 pts)
    scores['final_answer'] = score_final_answer(solution)  # 0-15

    total = sum(scores.values())

    return total, scores
```

---

## Expected Impact Summary

| Approach | Impact | Implementation Time | Cost Change | Risk |
|----------|--------|-------------------|-------------|------|
| **Structured JSON Feedback** | 60-70% | 4-6 hrs | Neutral | Low |
| **Top-N Prioritization** | 50-60% | 2-3 hrs | Neutral | Very Low |
| **Example-Based Feedback** | 50-55% | 6-8 hrs | +20% (examples) | Medium |
| **Progressive Scoring** | 40-50% | 3-4 hrs | Neutral | Low |
| **Socratic Dialogue** | 70-80% | 8-10 hrs | +300% (multi-turn) | High |
| **Diff-Based Feedback** | 55-65% | 2-3 hrs | Neutral | Low |
| **Feedback Chains** | 45-55% | 5-6 hrs | Neutral | Medium |
| **Meta-Feedback** | 35-45% | 4-5 hrs | +20% | Low |
| **Visual Feedback** | 50% (geometry only) | 10-12 hrs | Neutral | Medium |
| **Human-in-the-Loop** | 90%+ | 2-3 hrs | +human time | Low |

---

## Recommended Action Plan

### Phase 1: Quick Wins (Week 1) - 6 hours total

1. **Top-N Prioritization** (2 hrs) ⭐
   - Immediate cognitive load reduction
   - Test on failed asymmetric case

2. **JSON Structured Feedback** (4 hrs) ⭐⭐
   - Maximum impact for time invested
   - Can layer other approaches on top

**Expected outcome**: 50-70% improvement in fix quality

### Phase 2: High-Value Additions (Week 2) - 8 hours total

3. **Diff-Based Feedback** (2 hrs)
   - Complements JSON structure
   - Makes fixes even more actionable

4. **Progressive Scoring** (3 hrs)
   - Accept "good enough" solutions
   - Track measurable progress

5. **Example Library (initial)** (3 hrs)
   - Build 5-10 worked examples for common errors
   - Use for example-based feedback

**Expected outcome**: Additional 20-30% improvement

### Phase 3: Advanced Techniques (Week 3-4) - 15 hours total

6. **Feedback Chains** (5 hrs)
   - Dependency-aware fixing
   - Systematic error resolution

7. **Socratic Dialogue (selective)** (10 hrs)
   - Use only when stuck >3 iterations
   - High cost but high reward for hard cases

**Expected outcome**: Robust system handling 80%+ of problems

### Phase 4: Backstop (Ongoing)

8. **Human-in-the-Loop**
   - Always available for stuck cases
   - Minimal intervention (<5 min per problem)

---

## Critical Success Factors

1. **Start with JSON + Prioritization** - Highest ROI
2. **Measure incrementally** - Track fix accuracy after each addition
3. **A/B test** - Compare new feedback vs old on same problem
4. **Cost monitoring** - Some approaches (Socratic) are expensive
5. **Domain-specific tuning** - Some techniques work better for certain problem types

---

## Key Insight: The Feedback Translation Problem

The asymmetric approach (low gen / high verify) is CORRECT in principle, but requires a **translation layer** to bridge the cognitive gap.

**High verification speaks "PhD-level mathematics"**
**Low generation speaks "undergraduate-level mathematics"**
**We need a TRANSLATOR between them**

The most effective translator:
1. **Structures** the feedback (JSON, not prose)
2. **Simplifies** the feedback (Top-3, not 10+)
3. **Concretizes** the feedback (Examples, not abstractions)
4. **Visualizes** the feedback (Diffs, diagrams, not descriptions)

Implement these four principles and the gap will close.

---

**Status**: Ready for immediate testing
**First experiment**: JSON + Top-3 on failed asymmetric test case
**Timeline**: Can validate core ideas within 24 hours

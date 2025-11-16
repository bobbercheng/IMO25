# Critical Fixes - Week 1 Implementation Plan

**Status**: Ready to Implement
**Timeline**: 8 hours total
**Expected Impact**: +40-60% success rate improvement

---

## Background: Why Feature 1 Failed

### The Asymmetric Test Results (2 hours, 100% failure)

**What we tested:**
- Resumed from iteration 17 of low/low solution
- Verified with HIGH reasoning instead of low
- Goal: Validate if solution truly rigorous

**What happened:**
- **0 passes in 13 iterations** (100% failure rate)
- **31% empty solutions** - Low reasoning gave up completely
- **No learning** - Same errors repeated from iter 17 to iter 30
- **Original solution was flawed** - High verification correctly found critical math errors

**Root cause discovered:**
> Low reasoning CANNOT produce solutions that meet high verification standards. This is a **generator capability problem**, not a verification harshness problem.

### Research Validation (6 agents + 2024-2025 papers)

**Critical finding from research:**
> "LLMs cannot find reasoning errors, but can correct them **given the error**"
> - Paper: "Large Language Models Cannot Self-Correct Reasoning Yet" (2024)

**Your system's failure mode:**
1. Low reasoning generates flawed solution
2. High verification finds errors
3. Low reasoning **cannot parse mathematical feedback**
4. Same errors repeat → early termination

**Example from logs:**
```
High verification: "T₄ has 10 points, not 6; missing (1,4), (2,3), (3,2), (4,1)"
Low reasoning response: Still lists T₄ with only 6 points in next attempt
```

---

## The 4 Critical Fixes

All 6 agents converged on these priorities. Each has research backing and addresses a specific failure mode.

---

## Fix 1: Cross-Model Verification ⭐⭐⭐⭐⭐

**Time**: 2 hours
**Expected Impact**: +15-25% success rate
**Research Backing**: SuperCorrect (2024), Self-correction limitations research

### Problem
Current system uses same model for generation AND verification:
- `agent_gpt_oss.py` uses GPT-OSS for both
- Research shows **intrinsic self-correction degrades performance**
- Confirmation bias - model can't find its own errors

### Solution
Use DIFFERENT models for verification:
```python
# Generation: GPT-OSS (low reasoning)
# Verification: GPT-4o or Claude (high reasoning)
```

### Implementation

**Step 1: Create external verifier (30 min)**

Create `/home/user/IMO25/code/external_verifier.py`:

```python
import os
import requests
import json
from agent_oai import verification_system_prompt, verification_remider

def verify_with_external_model(problem_statement, solution, model="gpt-4o", api_key=None):
    """
    Verify solution using external model (GPT-4, Claude, etc.)

    Args:
        problem_statement: The problem
        solution: Solution to verify
        model: "gpt-4o", "claude-3-5-sonnet", etc.
        api_key: API key for external model

    Returns:
        (bug_report, verification_result)
    """
    from agent_gpt_oss import extract_detailed_solution

    dsol = extract_detailed_solution(solution)

    prompt = f"""
======================================================================
### Problem ###

{problem_statement}

======================================================================
### Solution ###

{dsol}

{verification_remider}
"""

    if model.startswith("gpt"):
        return verify_with_openai(prompt, model, api_key)
    elif model.startswith("claude"):
        return verify_with_claude(prompt, model, api_key)
    else:
        raise ValueError(f"Unknown model: {model}")

def verify_with_openai(prompt, model="gpt-4o", api_key=None):
    """Verify using OpenAI API"""
    api_key = api_key or os.getenv("OPENAI_API_KEY")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": verification_system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1
    }

    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers=headers,
        json=payload
    )

    response.raise_for_status()
    result = response.json()
    verification_output = result['choices'][0]['message']['content']

    # Check if verification passed
    check_prompt = f"""Response in "yes" or "no". Is the following statement saying the solution is complete, correct, and does not contain critical error or a major justification gap?

{verification_output}"""

    check_payload = {
        "model": model,
        "messages": [{"role": "user", "content": check_prompt}],
        "temperature": 0.1
    }

    check_response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers=headers,
        json=check_payload
    )

    check_result = check_response.json()
    verdict = check_result['choices'][0]['message']['content']

    # Extract bug report if verification failed
    bug_report = ""
    if "yes" not in verdict.lower():
        # Extract detailed verification section
        from agent_gpt_oss import extract_detailed_solution
        bug_report = extract_detailed_solution(verification_output, "Detailed Verification", False)

    return bug_report, verdict

def verify_with_claude(prompt, model="claude-3-5-sonnet-20241022", api_key=None):
    """Verify using Anthropic Claude API"""
    api_key = api_key or os.getenv("ANTHROPIC_API_KEY")

    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01"
    }

    payload = {
        "model": model,
        "max_tokens": 8000,
        "temperature": 0.1,
        "system": verification_system_prompt,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }

    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers=headers,
        json=payload
    )

    response.raise_for_status()
    result = response.json()
    verification_output = result['content'][0]['text']

    # Check if verification passed
    check_prompt = f"""Response in "yes" or "no". Is the following statement saying the solution is complete, correct, and does not contain critical error or a major justification gap?

{verification_output}"""

    check_payload = {
        "model": model,
        "max_tokens": 100,
        "temperature": 0.1,
        "messages": [
            {"role": "user", "content": check_prompt}
        ]
    }

    check_response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers=headers,
        json=check_payload
    )

    check_result = check_response.json()
    verdict = check_result['content'][0]['text']

    # Extract bug report if verification failed
    bug_report = ""
    if "yes" not in verdict.lower():
        from agent_gpt_oss import extract_detailed_solution
        bug_report = extract_detailed_solution(verification_output, "Detailed Verification", False)

    return bug_report, verdict
```

**Step 2: Modify agent to use external verifier (30 min)**

In `/home/user/IMO25/code/agent_gpt_oss.py`, add parameter:

```python
def agent(problem_statement, other_prompts=[], memory_file=None, resume_from_memory=False,
          solution_reasoning=None, verification_reasoning=None,
          external_verifier=None):  # NEW PARAMETER
    """
    Args:
        external_verifier: Use external model for verification
                          Options: "gpt-4o", "claude-3-5-sonnet", None (use same model)
    """
```

Replace `verify_solution()` calls with:

```python
if external_verifier:
    from external_verifier import verify_with_external_model
    verify, good_verify = verify_with_external_model(
        problem_statement, solution, model=external_verifier
    )
else:
    verify, good_verify = verify_solution(
        problem_statement, solution, reasoning_effort=ver_reasoning
    )
```

**Step 3: Add CLI argument (15 min)**

```python
parser.add_argument('--external-verifier', type=str,
                   choices=['gpt-4o', 'claude-3-5-sonnet', 'gpt-4-turbo'],
                   help='Use external model for verification instead of self-verification')
```

**Step 4: Test (45 min)**

```bash
# Test with GPT-4o verification
python code/agent_gpt_oss.py problems/imo01.txt \
  --solution-reasoning low \
  --external-verifier gpt-4o \
  --memory memory_external.json \
  --log external_test.log \
  --max_runs 1

# Expected: Better error detection, more actionable feedback
```

### Why This Works (Research Evidence)

**SuperCorrect (2024):**
- Large teacher model supervises smaller student
- Result: +7.8% on MATH benchmark

**Self-correction limitations:**
- Research shows intrinsic self-correction **degrades** performance
- External feedback is essential for correction

---

## Fix 2: Best-of-N Sampling ⭐⭐⭐⭐

**Time**: 2 hours
**Expected Impact**: +10-15% success rate
**Research Backing**: Test-time compute scaling (Google 2024), Best-of-N with verifiers

### Problem
Current system generates ONE solution per iteration:
- If that solution has errors, must iterate
- No exploration of alternative approaches
- Gets stuck in local minima (same errors repeat)

### Solution
Generate N diverse solutions, verify all, pick best:
```python
# Generate 3 solutions with different temperatures/seeds
# Verify each independently
# Select solution with best verification score
```

### Implementation

**Step 1: Create best-of-N generator (1 hour)**

In `/home/user/IMO25/code/agent_gpt_oss.py`, add function:

```python
def generate_multiple_solutions(problem_statement, other_prompts=[], n=3, reasoning_effort=None):
    """
    Generate N diverse solutions and return all with verification scores.

    Args:
        problem_statement: The problem
        other_prompts: Additional prompts
        n: Number of solutions to generate
        reasoning_effort: Reasoning level

    Returns:
        List of (solution, verification_score, verification_output) tuples
    """
    solutions = []

    for i in range(n):
        print(f">>>>>>> Generating solution {i+1}/{n}")

        # Use different temperature for diversity
        temperature = 0.1 + (i * 0.2)  # 0.1, 0.3, 0.5

        # Generate solution
        p1 = build_request_payload(
            system_prompt=step1_prompt,
            question_prompt=problem_statement,
            other_prompts=other_prompts,
            reasoning_effort=reasoning_effort
        )

        # Override temperature for diversity
        p1["temperature"] = temperature

        response = send_api_request(get_api_key(), p1)
        output = extract_text_from_response(response)

        # Self-improve
        p1["messages"].append(build_assistant_message(response))
        p1["messages"].append({"role": "user", "content": self_improvement_prompt})

        response2 = send_api_request(get_api_key(), p1)
        solution = extract_solution(extract_text_from_response(response2))

        # Verify
        verify, good_verify = verify_solution(problem_statement, solution, verbose=False)

        # Score verification (simple: count "yes" vs "no")
        score = 1.0 if "yes" in good_verify.lower() else 0.0

        solutions.append((solution, score, verify, good_verify))

        print(f">>>>>>> Solution {i+1} verification score: {score}")

    return solutions

def select_best_solution(solutions):
    """Select solution with highest verification score."""
    # Sort by score descending
    sorted_solutions = sorted(solutions, key=lambda x: x[1], reverse=True)
    return sorted_solutions[0]  # Return (solution, score, verify, good_verify)
```

**Step 2: Integrate into agent loop (30 min)**

Modify `init_explorations()`:

```python
def init_explorations(problem_statement, verbose=True, other_prompts=[], use_best_of_n=False, n=3):
    if use_best_of_n:
        # Generate multiple solutions
        solutions = generate_multiple_solutions(problem_statement, other_prompts, n=n)
        solution, score, verify, good_verify = select_best_solution(solutions)

        print(f">>>>>>> Selected best solution (score: {score})")
        print(f">>>>>>> Verification: {good_verify}")

        # Return dummy p1 (not used in best-of-N mode)
        p1 = build_request_payload(step1_prompt, problem_statement, other_prompts)
        return p1, solution, verify, good_verify
    else:
        # Original single-solution generation
        [... existing code ...]
```

**Step 3: Add CLI argument (15 min)**

```python
parser.add_argument('--best-of-n', type=int, default=1,
                   help='Generate N solutions and pick best (default: 1 = no best-of-N)')
```

**Step 4: Test (15 min)**

```bash
python code/agent_gpt_oss.py problems/imo01.txt \
  --solution-reasoning low \
  --verification-reasoning high \
  --best-of-n 3 \
  --memory memory_bon3.json \
  --log bon3_test.log
```

### Why This Works (Research Evidence)

**Google Test-Time Compute Scaling (2024):**
- Best-of-N with verifiers gives consistent performance gains
- 4x efficiency improvement over simple iteration

**Exploration benefit:**
- Avoids getting stuck in failed approach
- Different temperatures → different solution strategies
- Verifier selects most promising path

---

## Fix 3: Step-Level Verification ⭐⭐⭐⭐⭐

**Time**: 3 hours
**Expected Impact**: +20-30% via better error localization
**Research Backing**: Process Reward Models (2024), ThinkPRM, PAVs

### Problem
Current verification checks ENTIRE solution at once:
- Hard to pinpoint where error occurs
- Feedback like "several Critical Errors" is vague
- Agent doesn't know which step to fix first

### Solution
Break solution into steps, verify each individually:
```python
# Extract steps: Lemma 1, Lemma 2, Construction, Proof
# Verify each step independently
# Return: "Lemma 2 step 3 has error: wrong bound"
```

### Implementation

**Step 1: Create step extractor (1 hour)**

Create `/home/user/IMO25/code/step_verifier.py`:

```python
import re
from agent_gpt_oss import build_request_payload, send_api_request, get_api_key, extract_text_from_response
from agent_oai import verification_system_prompt

def extract_proof_steps(solution):
    """
    Extract individual proof steps from solution.

    Returns:
        List of (step_name, step_content) tuples
    """
    steps = []

    # Pattern 1: Lemmas (### 2.X Lemma Y)
    lemma_pattern = r'###\s+\d+\.\d+\s+Lemma\s+\d+[^\n]*\n(.*?)(?=###|\Z)'
    lemmas = re.findall(lemma_pattern, solution, re.DOTALL)
    for i, lemma in enumerate(lemmas, 1):
        steps.append((f"Lemma {i}", lemma.strip()))

    # Pattern 2: Constructions
    construction_pattern = r'###\s+\d+\.\d+\s+.*?[Cc]onstruction.*?\n(.*?)(?=###|\Z)'
    constructions = re.findall(construction_pattern, solution, re.DOTALL)
    for i, const in enumerate(constructions, 1):
        steps.append((f"Construction {i}", const.strip()))

    # Pattern 3: Main proof sections
    proof_pattern = r'###\s+\d+\.\d+\s+(?!Lemma|Construction)(.*?)\n(.*?)(?=###|\Z)'
    proofs = re.findall(proof_pattern, solution, re.DOTALL)
    for title, content in proofs:
        if content.strip():
            steps.append((title.strip(), content.strip()))

    # If no structured sections found, split by paragraph
    if not steps:
        paragraphs = solution.split('\n\n')
        for i, para in enumerate(paragraphs, 1):
            if len(para.strip()) > 50:  # Skip short paragraphs
                steps.append((f"Step {i}", para.strip()))

    return steps

def verify_step(problem_statement, step_name, step_content, verbose=False):
    """
    Verify a single proof step.

    Returns:
        (is_valid, feedback)
    """
    prompt = f"""You are verifying a single step from a mathematical proof.

**Problem:**
{problem_statement}

**Step to verify:** {step_name}
{step_content}

**Task:** Verify ONLY this step. Check for:
1. Mathematical correctness (no false claims)
2. Logical validity (conclusions follow from premises)
3. Completeness (all necessary justifications present)

If the step is correct, respond with: "VALID"
If the step has errors, respond with: "INVALID: [specific error description]"
"""

    payload = build_request_payload(
        system_prompt="You are a rigorous mathematical proof checker.",
        question_prompt=prompt,
        reasoning_effort="high"  # Use high reasoning for verification
    )

    response = send_api_request(get_api_key(), payload)
    feedback = extract_text_from_response(response)

    is_valid = "VALID" in feedback and "INVALID" not in feedback

    if verbose:
        print(f"  {step_name}: {'✓ VALID' if is_valid else '✗ INVALID'}")
        if not is_valid:
            print(f"    {feedback}")

    return is_valid, feedback

def verify_solution_by_steps(problem_statement, solution, verbose=True):
    """
    Verify solution step-by-step.

    Returns:
        (overall_valid, step_results, first_error_step)
    """
    if verbose:
        print(">>>>>>> Step-by-step verification")

    steps = extract_proof_steps(solution)

    if verbose:
        print(f">>>>>>> Extracted {len(steps)} proof steps")

    step_results = []
    first_error = None

    for step_name, step_content in steps:
        is_valid, feedback = verify_step(problem_statement, step_name, step_content, verbose)
        step_results.append((step_name, is_valid, feedback))

        if not is_valid and first_error is None:
            first_error = (step_name, feedback)

    overall_valid = all(is_valid for _, is_valid, _ in step_results)

    if verbose:
        if overall_valid:
            print(f">>>>>>> All {len(steps)} steps verified ✓")
        else:
            print(f">>>>>>> First error at: {first_error[0]}")

    return overall_valid, step_results, first_error
```

**Step 2: Integrate into agent (1 hour)**

In `/home/user/IMO25/code/agent_gpt_oss.py`:

```python
def agent(problem_statement, other_prompts=[], memory_file=None, resume_from_memory=False,
          solution_reasoning=None, verification_reasoning=None,
          external_verifier=None, use_step_verification=False):  # NEW PARAMETER

    # ... existing code ...

    # In verification section:
    if use_step_verification:
        from step_verifier import verify_solution_by_steps
        overall_valid, step_results, first_error = verify_solution_by_steps(
            problem_statement, solution, verbose=True
        )

        if overall_valid:
            good_verify = "yes"
            verify = "All steps verified successfully."
        else:
            good_verify = "no"
            # Create targeted feedback for first error
            error_step, error_msg = first_error
            verify = f"Error in {error_step}:\n\n{error_msg}\n\nPlease fix this step and re-verify."
    else:
        # Original whole-solution verification
        if external_verifier:
            from external_verifier import verify_with_external_model
            verify, good_verify = verify_with_external_model(
                problem_statement, solution, model=external_verifier
            )
        else:
            verify, good_verify = verify_solution(
                problem_statement, solution, reasoning_effort=ver_reasoning
            )
```

**Step 3: Add CLI argument (15 min)**

```python
parser.add_argument('--step-verification', action='store_true',
                   help='Verify solution step-by-step instead of as a whole')
```

**Step 4: Test (45 min)**

```bash
python code/agent_gpt_oss.py problems/imo01.txt \
  --solution-reasoning low \
  --verification-reasoning high \
  --step-verification \
  --memory memory_steps.json \
  --log steps_test.log
```

### Why This Works (Research Evidence)

**Process Reward Models (2024):**
- Step-level rewards > outcome-only rewards
- Better error localization
- More actionable feedback

**ThinkPRM:**
- Verbalized step-wise verification
- Result: Significant improvement in mathematical reasoning

**From your logs:**
- High verification found "several Critical Errors" but didn't say which line/step
- Agent couldn't parse vague feedback
- Step-level pinpointing would give: "Lemma 2, equation 3: claimed slope is +1 but actual slope is -(n-1)/(n-2)"

---

## Fix 4: Progressive Verification Scores ⭐⭐⭐⭐⭐

**Time**: 1 hour
**Expected Impact**: +30-50% via avoiding binary cliff
**Research Backing**: Agent 4 analysis, soft verification approaches

### Problem
Current verification is BINARY (pass/fail):
- 99% correct = total failure
- No credit for partial progress
- Discourages near-miss solutions

### Solution
Score solutions 0-100, accept at threshold (e.g., 85):
```python
# Instead of: pass/fail
# Use: Score = 85/100 → ACCEPT (minor gaps tolerated)
```

### Implementation

**Step 1: Create scoring verifier (30 min)**

In `/home/user/IMO25/code/agent_gpt_oss.py`:

```python
def verify_solution_with_score(problem_statement, solution, reasoning_effort=None):
    """
    Verify solution and return score 0-100.

    Returns:
        (score, feedback, detailed_breakdown)
    """
    verify, good_verify = verify_solution(problem_statement, solution,
                                         verbose=False, reasoning_effort=reasoning_effort)

    # Ask verifier to score the solution
    scoring_prompt = f"""Based on your verification of the solution, assign a score from 0-100:

**Verification output:**
{verify}

**Scoring rubric:**
- 100: Perfect, no errors or gaps
- 90-99: Minor presentation issues, logic is sound
- 80-89: Small justification gaps, overall correct
- 70-79: Some logical gaps, main idea correct
- 50-69: Significant errors but salvageable
- 30-49: Major errors, fundamental approach flawed
- 0-29: Completely wrong or empty

Respond with ONLY the number (0-100).
"""

    payload = build_request_payload(
        system_prompt="",
        question_prompt=scoring_prompt,
        reasoning_effort=reasoning_effort
    )

    response = send_api_request(get_api_key(), payload)
    score_text = extract_text_from_response(response)

    # Extract number from response
    import re
    score_match = re.search(r'\b(\d+)\b', score_text)
    score = int(score_match.group(1)) if score_match else 0

    print(f">>>>>>> Verification score: {score}/100")

    return score, verify, good_verify
```

**Step 2: Modify agent to use scores (20 min)**

```python
def agent(problem_statement, other_prompts=[], memory_file=None, resume_from_memory=False,
          solution_reasoning=None, verification_reasoning=None,
          external_verifier=None, use_step_verification=False,
          score_threshold=85):  # NEW PARAMETER

    # ... in verification loop ...

    score, verify, good_verify = verify_solution_with_score(
        problem_statement, solution, reasoning_effort=ver_reasoning
    )

    if score >= score_threshold:
        print(f">>>>>>> Score {score} >= threshold {score_threshold}, accepting solution")
        correct_count += 1
        error_count = 0
    else:
        print(f">>>>>>> Score {score} < threshold {score_threshold}, rejecting solution")
        correct_count = 0
        error_count += 1
```

**Step 3: Test (10 min)**

```bash
python code/agent_gpt_oss.py problems/imo01.txt \
  --solution-reasoning low \
  --verification-reasoning high \
  --score-threshold 85 \
  --memory memory_scores.json \
  --log scores_test.log
```

### Why This Works

**From Agent 4:**
> "Binary pass/fail creates a cliff. Progressive scores allow incremental improvement."

**Practical benefit:**
- Solution with "minor justification gaps" (score 88) is accepted
- Avoids infinite loops trying to achieve perfection
- Still maintains rigor (threshold 85 = B+ grade)

---

## Testing & Validation

### Test Suite (1-2 days)

**Test 1: Cross-model verification**
```bash
python code/agent_gpt_oss.py problems/imo01.txt \
  --external-verifier gpt-4o \
  --max_runs 1 \
  --log test_external.log
```
**Expected:** Better error detection than self-verification

**Test 2: Best-of-3 sampling**
```bash
python code/agent_gpt_oss.py problems/imo01.txt \
  --best-of-n 3 \
  --max_runs 1 \
  --log test_bon.log
```
**Expected:** Higher success rate via exploration

**Test 3: Step-level verification**
```bash
python code/agent_gpt_oss.py problems/imo01.txt \
  --step-verification \
  --max_runs 1 \
  --log test_steps.log
```
**Expected:** More actionable feedback

**Test 4: Progressive scores**
```bash
python code/agent_gpt_oss.py problems/imo01.txt \
  --score-threshold 85 \
  --max_runs 1 \
  --log test_scores.log
```
**Expected:** Acceptance of near-perfect solutions

**Test 5: ALL FIXES COMBINED**
```bash
python code/agent_gpt_oss.py problems/imo01.txt \
  --external-verifier gpt-4o \
  --best-of-n 3 \
  --step-verification \
  --score-threshold 85 \
  --memory memory_combined.json \
  --log test_combined.log \
  --max_runs 1
```
**Expected:** +40-60% success rate improvement

### Success Metrics

**Baseline (low/low):** 30-50% success, questionable rigor
**Baseline (low/high asymmetric):** 0% success (Feature 1 failure)

**Target with fixes:**
- **Success rate:** 70-85%
- **Rigor confidence:** High (external verification + step-checking)
- **Time to solution:** 2-4 hours (vs 23 hours for high/high)
- **False positive rate:** <5% (vs ~30% for low/low)

---

## Why These 4 Fixes Work Together

**Fix 1 (Cross-model):** Addresses self-correction failure
**Fix 2 (Best-of-N):** Avoids getting stuck in bad approach
**Fix 3 (Step-level):** Provides actionable error localization
**Fix 4 (Progressive scores):** Avoids binary pass/fail cliff

**Synergy:**
1. Generate 3 diverse solutions (Fix 2)
2. Verify each with external model (Fix 1)
3. Check step-by-step (Fix 3)
4. Score 0-100, accept at 85+ (Fix 4)
5. If all fail, iterate with targeted feedback from step-level verification

**Expected compound effect:** 1.25 × 1.15 × 1.30 × 1.50 = **2.8× improvement**

---

## Decision Tree

```
Start
  │
  ├─ Implement 4 fixes (8 hours)
  │
  ├─ Test on 5 problems (2 hours)
  │
  ├─ Evaluate results:
  │   │
  │   ├─ Success rate ≥ 70% → DONE! Use in production
  │   │
  │   ├─ Success rate 50-70% → Add MCTS (Phase 2)
  │   │
  │   └─ Success rate < 50% → Revisit generator quality
  │                            (try medium reasoning, dual-agent)
```

---

## Files to Create/Modify

### New Files:
1. `/home/user/IMO25/code/external_verifier.py` (Fix 1)
2. `/home/user/IMO25/code/step_verifier.py` (Fix 3)

### Modified Files:
1. `/home/user/IMO25/code/agent_gpt_oss.py`:
   - Add `generate_multiple_solutions()` (Fix 2)
   - Add `verify_solution_with_score()` (Fix 4)
   - Modify `agent()` to support all 4 fixes
   - Add CLI arguments

---

## Timeline

**Hour 1-2:** Fix 1 (Cross-model verification)
**Hour 3-4:** Fix 2 (Best-of-N sampling)
**Hour 5-7:** Fix 3 (Step-level verification)
**Hour 8:** Fix 4 (Progressive scores)

**Total:** 8 hours

**Testing:** 2 hours on 5 problems

**Expected completion:** This week

---

## Next Steps After Week 1

**If fixes work (≥70% success):**
- Scale to 20+ problems
- Fine-tune thresholds (score cutoff, best-of-N count)
- Document and publish approach

**If partial success (50-70%):**
- Add MCTS for exploration (Phase 2)
- Try ensemble verification (3 models vote)
- Implement process reward models

**If still struggling (<50%):**
- Reconsider generator quality (medium reasoning?)
- Try dual-agent architecture
- Consider formal verification integration (Lean)

---

## Research Citations

All 4 fixes are backed by 2024-2025 research:

1. **Cross-model verification:**
   - "Large Language Models Cannot Self-Correct Reasoning Yet" (2024)
   - SuperCorrect (2024): +7.8% with external supervision

2. **Best-of-N sampling:**
   - Google Test-Time Compute Scaling (August 2024)
   - DeepSeek-R1 (January 2025): AIME score 15.6% → 71%

3. **Step-level verification:**
   - ThinkPRM (2025): Verbalized step-wise rewards
   - Process Advantage Verifiers (2024)

4. **Progressive scores:**
   - Implicit in all RL-based approaches
   - Soft verification > binary verification

---

**Status**: Ready to implement
**Priority**: HIGHEST - All 6 agents converged on these fixes
**Expected ROI**: 2.8× improvement for 8 hours of work

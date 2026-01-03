# Phase 2 Implementation Specification
**Prescriptive Feedback for Verification Errors**

**Date**: 2025-12-18
**Based on**: Phase A Validation Results
**Target**: Bridge gap from "finding answers" to "constructing rigorous proofs"

---

## 1. Overview

### 1.1 Problem Statement

After Phase 1 validation, we observed:
- MCTS found mathematically correct answer: k ∈ {0,1,...,⌊(n-1)/2⌋}
- But verification flagged it as INVALID with 4 Critical Errors
- Errors were about **incompleteness** and **justification gaps**, not mathematical incorrectness

**Root Cause**: Current verification provides ERROR DETECTION but not FIX GUIDANCE.

### 1.2 Solution: Prescriptive Feedback

Convert verification error messages into actionable fix instructions that guide the agent toward rigorous proofs.

**Key Principle**: Every error type should have a corresponding fix template.

---

## 2. Error Taxonomy

Based on Phase A validation logs, we identified 4 major error categories:

### Category 1: Construction Errors

**Definition**: Line/object construction violates problem constraints

**Examples from Phase A**:
- "Line ℓ₃ has slope -1 (prohibited for sunny lines)"
- "Line ℓ_c doesn't cover entire column x=c as claimed"

**Frequency**: 3 in BFS, 2 in MCTS

### Category 2: Coverage Errors

**Definition**: Claimed coverage of points is incorrect or incomplete

**Examples from Phase A**:
- "b-1 is multiple of -(c-2) only for b=1, not all b"
- "Replacement procedure fails to cover all points"

**Frequency**: 2 in BFS, 1 in MCTS

### Category 3: Bound Errors

**Definition**: Derived bounds are incorrect or insufficiently justified

**Examples from Phase A**:
- "a₂-a₁ must be ≥2; otherwise slope = 0 or -1" (FALSE)
- "Upper bound k≤n-1 is unsupported"

**Frequency**: 1 in BFS, 2 in MCTS

### Category 4: Incompleteness Errors

**Definition**: Solution addresses only part of the problem requirements

**Examples from Phase A**:
- "Only k=0 proven attainable; other values not addressed"
- "Construction works for some k but not all k∈[0, bound]"

**Frequency**: 0 in BFS, 1 in MCTS

---

## 3. Prescriptive Fix Templates

### 3.1 Template for Construction Errors

**Error Pattern**: "Line/object X has property P (prohibited/incorrect)"

**Prescriptive Fix**:
```
CONSTRUCTION ERROR DETECTED: {object} has {property}

TO FIX:
1. Identify constraint: {property} violates {constraint_type}
2. Modify construction to satisfy constraint:
   - If slope issue: Choose slope m ∉ {0, -1, ∞}
     Example: Use m = j for positive integer j
   - If intercept issue: Adjust y-intercept β to pass through required point
     Example: For line through (a,b) with slope m, set β = b - m·a
3. Verify new construction:
   - Check: All points claimed to be on line satisfy line equation
   - Check: Line satisfies all problem constraints
   - Check: Line is distinct from other lines in family

CONCRETE SUGGESTION for your case:
Instead of: {current_construction}
Try: {suggested_construction}
Where {parameter_explanation}
```

**Example Application** (BFS Error 1):
```
CONSTRUCTION ERROR DETECTED: Line ℓ₃ has slope -1 (prohibited for sunny lines)

TO FIX:
1. Identify constraint: slope -1 violates "sunny line" definition
2. Modify construction to satisfy constraint:
   Current: ℓ_c: y = (c-1) - (c-2)·x  [slope = -(c-2) = -1 when c=3]
   Issue: For c=3, slope = -1 (not sunny)
3. Revised construction options:
   Option A: Restrict c range to c≥4 (skip c=3)
   Option B: Use different slope formula: m = j for j∈{1,2,3,...}
   Option C: Use different line family entirely

CONCRETE SUGGESTION:
Instead of: ℓ_c: y = (c-1) - (c-2)·x for c≥3
Try: M_j: y = j·x + (1 - j·v) for j≥1
Where j is line index, v is number of vertical lines
This ensures slope = j > 0, so slope ∉ {0, -1, ∞} for all j
```

### 3.2 Template for Coverage Errors

**Error Pattern**: "Object X doesn't cover all points in set S as claimed"

**Prescriptive Fix**:
```
COVERAGE ERROR DETECTED: {object} doesn't cover {point_set}

TO FIX:
1. Verify coverage claim algebraically:
   - Substitute point coordinates into object equation
   - Check: Does equation hold for ALL points in set?
   - If not: Identify which points are NOT covered
2. Revise coverage claim OR modify construction:
   Option A: Narrow coverage claim to only points actually covered
   Option B: Modify construction to cover all claimed points
3. Prove coverage rigorously:
   - For each point (a,b) in set, show equation is satisfied
   - Use universal quantifiers: "For all b with 1≤b≤n+1-c, ..."
   - Avoid hand-waving: "clearly", "obviously", "it's easy to see"

CONCRETE SUGGESTION for your case:
Current claim: {current_claim}
Actual coverage: {actual_coverage}
Gap: {uncovered_points}

To fix gap:
{specific_fix_instruction}
```

**Example Application** (BFS Error 2):
```
COVERAGE ERROR DETECTED: ℓ_c doesn't cover all points in column x=c

TO FIX:
1. Verify coverage claim algebraically:
   Current claim: "All points (c,b) with 1≤b≤n+1-c lie on ℓ_c"
   Test: Substitute (c,b) into y = (c-1) - (c-2)·x
         → y = (c-1) - (c-2)·c = (c-1) - c² + 2c = c² + c - 1
         → For b=1: y=1 ✓
         → For b=2: y=1 ✗ (should be 2)
   Conclusion: Only (c,1) is covered, not all (c,b)

2. Revise construction to cover all points:
   Need: Line through (c,1), (c,2), ..., (c,n+1-c)
   But: These points are collinear only if x=c (vertical line)
   Conclusion: ℓ_c cannot be non-vertical AND cover entire column

3. Alternative approach:
   - Keep vertical lines for some columns
   - Use sunny lines ONLY for columns that don't need full coverage
   - Example: Vertical lines for x=1,...,v; sunny lines for x=v+1,...,n

CONCRETE SUGGESTION:
Don't try to make one sunny line cover entire column.
Instead: Use vertical lines V_i: x=i for i=1,...,m
         Use sunny lines M_j to cover remaining points selectively
```

### 3.3 Template for Bound Errors

**Error Pattern**: "Bound derivation contains logical error or unjustified step"

**Prescriptive Fix**:
```
BOUND ERROR DETECTED: {bound_claim} is incorrect or unjustified

TO FIX:
1. Review logical chain:
   - Premise: {premise}
   - Inference: {inference_step}
   - Conclusion: {conclusion}
   - Error location: {error_in_step}

2. Identify error type:
   Type A: Logical fallacy (invalid inference)
           Example: "A>B, C>D → A-C>B-D" is FALSE
   Type B: Unsupported assumption
           Example: Assuming property P without proof
   Type C: Arithmetic error
           Example: n(n+1)/2 ≠ n² for n≥3

3. Correct the derivation:
   {step_by_step_corrected_derivation}

CONCRETE SUGGESTION:
Replace: {flawed_argument}
With: {corrected_argument}
Key change: {what_was_fixed}
```

**Example Application** (MCTS Error 1):
```
BOUND ERROR DETECTED: "a₂-a₁ must be ≥2; otherwise slope = 0 or -1"

TO FIX:
1. Review logical chain:
   Premise: Slope α = (b₂-b₁)/(a₂-a₁), and α ∉ {0, -1}
   Inference: "If a₂-a₁=1, then α = b₂-b₁ ∈ {0,-1}"
   Conclusion: Therefore a₂-a₁ ≥ 2
   Error: Inference is FALSE

2. Identify error:
   Type A: Logical fallacy
   If a₂-a₁=1, then α = b₂-b₁ can be ANY integer
   Only forbidden: α=0 (b₂=b₁) and α=-1 (b₂=b₁-1)
   Allowed: α ∈ {...,-2,1,2,3,...} ∪ {rationals ∉ {0,-1}}
   Therefore a₂-a₁=1 is ALLOWED for sunny lines

3. Corrected derivation:
   A sunny line has slope α ∉ {0, -1, ∞}
   For two points (a₁,b₁), (a₂,b₂) on sunny line:
   - α = (b₂-b₁)/(a₂-a₁) must be defined and ∉ {0,-1}
   - This allows ANY a₂-a₁ ≥ 1 (including a₂-a₁=1)
   - Maximum points on sunny line in T_n: need different analysis

CONCRETE SUGGESTION:
Don't use "minimum spacing" argument.
Instead: Use pigeonhole or counting argument:
- Each sunny line intersects each vertical column in ≤1 point
- Therefore ≤n points total on any sunny line
- But |T_n| = n(n+1)/2, so need ≥(n+1)/2 vertical lines
- Therefore ≤n-(n+1)/2 = ⌊(n-1)/2⌋ sunny lines
```

### 3.4 Template for Incompleteness Errors

**Error Pattern**: "Solution addresses some cases but not all required by problem"

**Prescriptive Fix**:
```
INCOMPLETENESS ERROR DETECTED: {what_is_missing}

TO FIX:
1. Identify gap:
   Problem asks for: {full_requirement}
   Solution provides: {partial_answer}
   Missing: {gap}

2. Address gap systematically:
   For each missing case k in {gap_set}:
   - Construct explicit configuration with k sunny lines
   - Verify configuration satisfies all constraints
   - Prove construction is valid for this k

3. Organize proof structure:
   Part 1: Upper bound (shows k ≤ max_value)
   Part 2: Lower bound (shows k ≥ 0 by construction)
   Part 3: Realizability (for each 0≤k≤max, exhibit configuration)

CONCRETE SUGGESTION:
You've proven: {what_is_proven}
Still need: {what_needs_proof}

Template for missing part:
{construction_template}
```

**Example Application** (MCTS Error 4):
```
INCOMPLETENESS ERROR DETECTED: Only k=0 proven attainable

TO FIX:
1. Identify gap:
   Problem asks for: ALL nonnegative integers k such that configuration exists
   Solution provides: k=0 exists; k≤n-1 (but this bound is wrong)
   Missing: Explicit constructions for k=1,2,...,⌊(n-1)/2⌋

2. Address gap systematically:
   For each k ∈ {0,1,2,...,⌊(n-1)/2⌋}:

   Construction template:
   - Let v = n-k (number of vertical lines)
   - Use vertical lines V_i: x=i for i=1,...,v
   - Use sunny lines M_j: y = j·x + (1-j·v) for j=1,...,k

   Verification for each k:
   Step 1: Show all n lines are distinct
   Step 2: Show exactly k lines are sunny (M_1,...,M_k)
   Step 3: Show all points (a,b)∈T_n are covered:
           - If a≤v: covered by V_a
           - If a>v: covered by M_{a-v}

3. Prove construction is valid:
   {detailed_verification_for_template}

CONCRETE SUGGESTION:
Add section: "Construction for arbitrary k ∈ [0, ⌊(n-1)/2⌋]"
Use template above with explicit verification
Include example: For n=5, show configurations for k=0,1,2
```

---

## 4. Integration into Verification Prompt

### 4.1 Modified Verification System Prompt

Add after error classification in verification prompt:

```python
PRESCRIPTIVE_FEEDBACK_SECTION = """
When you identify a Critical Error or Justification Gap, you MUST provide:

1. ERROR CLASSIFICATION: {Construction / Coverage / Bound / Incompleteness}

2. PRESCRIPTIVE FIX GUIDANCE:
   - Specific suggestion for how to fix this error type
   - Concrete example of corrected approach
   - Reference to fix template for this error category

Use the following templates:

[INSERT ERROR-SPECIFIC TEMPLATES HERE]

3. EXAMPLE OF CORRECTED VERSION:
   Before: {flawed_step}
   After: {corrected_step}
   Why this works: {explanation}
"""
```

### 4.2 Example Output Format

**Before** (Phase 1):
```
**Location:** "Line ℓ₃ has slope -1"
**Issue:** Critical Error – slope -1 is prohibited for sunny lines
```

**After** (Phase 2):
```
**Location:** "Line ℓ₃ has slope -1"
**Issue:** Critical Error – slope -1 is prohibited for sunny lines

**Prescriptive Fix:**
ERROR TYPE: Construction Error

TO FIX THIS ERROR:
1. Current construction: ℓ_c: y = (c-1) - (c-2)·x
   Problem: When c=3, slope = -(3-2) = -1 (not sunny)

2. Corrected construction option:
   Use: M_j: y = j·x + (1-j·v) for j≥1
   This ensures: slope = j > 0, so sunny for all j

3. Example for n=5, k=2:
   - v = n-k = 3 vertical lines: V_1, V_2, V_3
   - k = 2 sunny lines:
     M_1: y = 1·x + (1-1·3) = x - 2
     M_2: y = 2·x + (1-2·3) = 2x - 5
   - Verify M_1 sunny: slope=1 ∉ {0,-1,∞} ✓
   - Verify M_2 sunny: slope=2 ∉ {0,-1,∞} ✓
```

---

## 5. Implementation Plan

### Phase 2.1: Template Creation (Week 1)

**Tasks**:
1. Create fix template for each error category
2. Test templates on Phase A errors manually
3. Refine templates based on clarity and actionability

**Deliverables**:
- 4 error category templates (Construction, Coverage, Bound, Incompleteness)
- Manual application to 10+ errors from Phase A logs
- Template refinement document

### Phase 2.2: Prompt Integration (Week 1-2)

**Tasks**:
1. Modify verification system prompt to include templates
2. Add error classification logic
3. Test on Phase A logs (rerun verification with Phase 2 prompt)

**Deliverables**:
- Updated verification prompt with prescriptive feedback
- Test results showing Phase 2 feedback for Phase A errors

### Phase 2.3: Agent Loop Integration (Week 2)

**Tasks**:
1. Modify agent to parse and apply prescriptive fixes
2. Add fix application step between verification and regeneration
3. Track fix success rate

**Deliverables**:
- Agent code with fix application logic
- Metrics: fix_applied_rate, fix_success_rate

### Phase 2.4: Validation (Week 2-3)

**Tasks**:
1. Run full Phase A+B validation (BFS + MCTS with Phase 1+2)
2. Compare metrics: Phase 1 only vs Phase 1+2
3. Measure improvement in VALID verdict rate and proof quality

**Deliverables**:
- Validation test results
- Comparison document: Phase 1 vs Phase 1+2
- Success metrics:
  - VALID verdict rate: 1.9-5.4% → target 20-40%
  - Rigorous proof rate: 0% → target 50-80%

---

## 6. Success Metrics

### Primary Metrics

| Metric | Phase 1 Only | Phase 1+2 Target | Measurement Method |
|--------|--------------|------------------|-------------------|
| **VALID verdict rate** | 1.9-5.4% | 20-40% | (VALID verdicts) / (total solutions) |
| **Rigorous proof success** | 0% | 50-80% | Final solution passes verification |
| **Final answer correctness** | 50% (BFS), 100% (MCTS) | 100% | Answer matches known correct answer |

### Secondary Metrics

| Metric | Phase 1 Only | Phase 1+2 Target | Measurement Method |
|--------|--------------|------------------|-------------------|
| **Fix application rate** | N/A | 80%+ | Fixes applied / fixes suggested |
| **Fix success rate** | N/A | 40%+ | Fixes that resolved error / fixes applied |
| **Iterations to success** | ∞ (never) | <100 | Iterations until VALID verdict |
| **Error reduction per iteration** | Unknown | 30%+ | (Errors at iter N) / (Errors at iter N-1) |

### Qualitative Metrics

- **Proof structure improvement**: Does agent construct more systematic proofs?
- **Error type distribution**: Does agent learn to avoid certain error types?
- **Learning curve**: Does fix success rate improve over iterations?

---

## 7. Risks and Mitigation

### Risk 1: Prescriptive Fixes Too Specific

**Risk**: Agent might over-rely on templates, reducing creativity
**Mitigation**: Frame templates as "suggestions" not "requirements"
**Fallback**: Include "or explore alternative approach" in each template

### Risk 2: Fix Templates Don't Generalize

**Risk**: Templates work for Phase A errors but not new problems
**Mitigation**: Test on multiple IMO problems (P1, P2, P3)
**Fallback**: Iterate on templates based on broader error corpus

### Risk 3: Agent Doesn't Apply Fixes Correctly

**Risk**: Agent parses prescriptive feedback but misapplies it
**Mitigation**: Add fix validation step (check if fix actually resolves error)
**Fallback**: Increase verification reasoning level to "high" for fix validation

### Risk 4: Verification Overhead Increases

**Risk**: Prescriptive feedback makes verification slower
**Mitigation**: Cache fix templates, use lower reasoning for template retrieval
**Fallback**: Accept 10-20% slowdown if proof quality improves

---

## 8. Testing Plan

### Test 1: Manual Template Application

**Input**: Phase A errors (7 from BFS, 4 from MCTS)
**Process**: Manually write prescriptive fix for each error
**Output**: 11 error-fix pairs
**Success Criteria**: 80%+ of fixes are actionable and clear

### Test 2: Verification Prompt Update

**Input**: Phase A logs (BFS and MCTS)
**Process**: Rerun verification with Phase 2 prompt
**Output**: Verification results with prescriptive feedback
**Success Criteria**: All errors have prescriptive fixes in output

### Test 3: Agent Fix Application

**Input**: Phase A solutions with Phase 2 prescriptive feedback
**Process**: Agent reads feedback and attempts to apply fixes
**Output**: Updated solutions with fixes applied
**Success Criteria**: 60%+ of fixes are correctly applied

### Test 4: End-to-End Validation

**Input**: IMO Problem 1 (same as Phase A)
**Process**: Run full agent loop with Phase 1+2
**Output**: Final solution with verification verdict
**Success Criteria**:
- Final answer: k ∈ {0,1,...,⌊(n-1)/2⌋} ✓
- Verification: VALID (no Critical Errors) ✓
- Rigorous proof: Complete and justified ✓

### Test 5: Generalization Test

**Input**: Different IMO problem (e.g., Problem 2 or Problem 3)
**Process**: Run agent with Phase 1+2 on new problem
**Output**: Solution and verification verdict
**Success Criteria**: VALID verdict rate >20% (vs 1.9-5.4% baseline)

---

## 9. Code Changes Required

### 9.1 New Files

```
code/prescriptive_templates.py
  - ERROR_TEMPLATES dict with fix templates for each category
  - apply_prescriptive_fix(error_type, error_details) function
  - validate_fix(original_error, applied_fix) function
```

### 9.2 Modified Files

```
code/agent_gpt_oss.py:
  - Add fix application step in main loop
  - Parse verification output for prescriptive fixes
  - Apply fixes before regeneration

code/verification_prompts.py (or inline in agent):
  - Add PRESCRIPTIVE_FEEDBACK_SECTION to verification prompt
  - Include ERROR_TEMPLATES in prompt context
```

### 9.3 Configuration

```python
# New environment variables
ENABLE_PRESCRIPTIVE_FEEDBACK = True  # Phase 2 toggle
PRESCRIPTIVE_FEEDBACK_REASONING = "medium"  # Reasoning level for fix generation
FIX_VALIDATION_ENABLED = True  # Validate fixes before applying
```

---

## 10. Expected Outcome

### Optimistic Scenario (80% confidence)

- **VALID verdict rate**: 25-35% (vs 1.9-5.4% baseline)
- **Rigorous proof success**: 60-70% (vs 0% baseline)
- **Iterations to success**: 50-80 (vs ∞ baseline)
- **Answer correctness**: 100% (MCTS already at 100%, BFS improves from 0%)

### Realistic Scenario (50% confidence)

- **VALID verdict rate**: 15-25%
- **Rigorous proof success**: 40-60%
- **Iterations to success**: 80-120
- **Answer correctness**: 100%

### Conservative Scenario (20% confidence)

- **VALID verdict rate**: 10-15%
- **Rigorous proof success**: 20-40%
- **Iterations to success**: 120-150
- **Answer correctness**: 100%

**Even in conservative scenario**, Phase 2 represents substantial improvement over Phase 1 alone (0% proof success).

---

## 11. Next Steps

### Immediate (This Week)
1. ✅ Create this implementation spec
2. ⏳ Draft fix templates for 4 error categories
3. ⏳ Manually apply templates to Phase A errors
4. ⏳ Refine templates based on manual application

### Next Week
1. ⏳ Integrate templates into verification prompt
2. ⏳ Test verification with Phase 2 on Phase A logs
3. ⏳ Implement fix application logic in agent
4. ⏳ Run Test 3 (agent fix application)

### Week 3
1. ⏳ Run Test 4 (end-to-end validation on IMO P1)
2. ⏳ Compare Phase 1 vs Phase 1+2 metrics
3. ⏳ Run Test 5 (generalization to IMO P2/P3)
4. ⏳ Document results and decide on Phase 3

---

**Document Status**: DRAFT v1.0
**Owner**: Phase 2 Implementation Team
**Review Date**: 2025-12-20
**Target Completion**: 2025-12-27

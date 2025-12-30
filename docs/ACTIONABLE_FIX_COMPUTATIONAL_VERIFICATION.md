# Actionable Fix: Add Computational Verification to RLAC

**Date:** 2025-12-07
**Priority:** ⭐⭐⭐ HIGH
**Estimated Effort:** 8-12 hours
**Expected Impact:** Problem 1 will achieve "verification good" status (matching problem 2)

---

## Problem Statement

**Current situation:**
- Problem 2 (PROVE): "Verification good" ✅ (justification gaps acceptable)
- Problem 1 (FIND): NOT "verification good" ❌ (critical error in construction)

**Root cause:**
RLAC does not verify computational claims. When generator says:
> "A direct verification shows that each of the six points of S₃ lies on one of them."

RLAC accepts this claim without actually checking if it's true.

**Result:**
- Problem 1's k=3 construction has critical error (points (1,3) and (2,1) uncovered)
- RLAC gave ROBUST verdict despite factual incorrectness
- Final solution is WRONG, not just incomplete

---

## Solution: Add Computational Verification Step

### High-Level Approach

When generator makes a verifiable computational claim, RLAC should:
1. **Detect** the claim (pattern matching)
2. **Extract** the computational assertion
3. **Verify** the claim explicitly
4. **Report** result to critic (VERIFIED or BROKEN with counterexample)

---

## Implementation Plan

### Step 1: Claim Detection (2 hours)

**File:** `code/adversarial_critic.py`

**Function:** `detect_verifiable_claims(solution_text, problem_context)`

```python
def detect_verifiable_claims(solution_text, problem_context):
    """
    Detect computational claims that can be explicitly verified.

    Returns list of claims with type and extracted data.
    """
    claims = []

    # Pattern 1: Line coverage claims (FIND problems with geometric constraints)
    if problem_context.type in ["FIND", "GEOMETRY"]:
        patterns = [
            r"direct verification shows.*points.*lie on.*lines",
            r"checking.*each.*point.*covered",
            r"lines?\s+(.+)\s+covers?\s+all\s+points?",
            r"construction:\s*(.+)\s*satisfies?"
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, solution_text, re.IGNORECASE)
            for match in matches:
                # Extract context around match
                start = max(0, match.start() - 200)
                end = min(len(solution_text), match.end() + 500)
                context = solution_text[start:end]

                claims.append({
                    "type": "line_coverage",
                    "context": context,
                    "location": match.group(0),
                    "problem_type": problem_context.type
                })

    # Pattern 2: Polynomial roots claims
    if "polynomial" in problem_context.keywords:
        patterns = [
            r"the roots are\s+(.+)",
            r"solving.*yields.*roots?\s+(.+)"
        ]
        # Similar extraction logic

    # Pattern 3: Sequence/recurrence claims
    if "sequence" in problem_context.keywords or "recurrence" in problem_context.keywords:
        patterns = [
            r"satisfies the recurrence",
            r"the sequence is\s+(.+)"
        ]
        # Similar extraction logic

    return claims
```

---

### Step 2: Claim Parsing (3 hours)

**File:** `code/claim_parser.py` (new file)

**Function:** `parse_line_coverage_claim(claim_context)`

```python
import re
import sympy as sp
from sympy import symbols, Eq, solve
from sympy.geometry import Point, Line

def parse_line_coverage_claim(claim_context):
    """
    Parse a line coverage claim into verifiable form.

    Input: "The three lines L₁: y=½x+½, L₂: y=-½x+5/2, L₃: y=x cover all points."
    Output: {
        "lines": [Line(...), Line(...), Line(...)],
        "points": [Point(...), ...],
        "claim": "all points covered"
    }
    """

    lines = []
    points = []

    # Extract line equations
    line_patterns = [
        r"L[₀-₉0-9]+\s*:\s*y\s*=\s*([^,;]+)",  # L₁: y = mx+b
        r"x\s*=\s*([0-9]+)",                     # x = a (vertical)
        r"y\s*=\s*([0-9]+)",                     # y = b (horizontal)
        r"x\s*\+\s*y\s*=\s*([0-9]+)"            # x+y = c (slope -1)
    ]

    for pattern in line_patterns:
        matches = re.finditer(pattern, claim_context)
        for match in matches:
            try:
                x, y = symbols('x y')
                equation_str = match.group(0).split(":")[1] if ":" in match.group(0) else match.group(0)

                # Parse equation using sympy
                if "y =" in equation_str:
                    rhs = equation_str.split("y =")[1].strip()
                    rhs = rhs.replace("½", "1/2").replace("⅓", "1/3")  # Handle fractions
                    equation = Eq(y, sp.sympify(rhs))
                elif "x =" in equation_str:
                    rhs = equation_str.split("x =")[1].strip()
                    equation = Eq(x, sp.sympify(rhs))
                # ... other cases

                lines.append(equation)
            except Exception as e:
                # Log parsing error
                pass

    # Extract points (from problem context)
    # For IMO01: Points are (a,b) with a,b > 0 and a+b ≤ n+1
    # Need to extract n from problem statement

    return {
        "lines": lines,
        "points": points,
        "claim_type": "coverage"
    }
```

---

### Step 3: Claim Verification (2 hours)

**File:** `code/claim_verifier.py` (new file)

**Function:** `verify_line_coverage(parsed_claim)`

```python
from sympy import symbols, solve
from sympy.geometry import Point, Line

def verify_line_coverage(parsed_claim):
    """
    Verify that given lines cover all required points.

    Returns: {
        "verified": True/False,
        "counterexamples": [Point(...), ...],  # Uncovered points
        "coverage_map": {point: line_index, ...}
    }
    """

    lines = parsed_claim["lines"]
    points = parsed_claim["points"]

    coverage_map = {}
    uncovered = []

    for point in points:
        covered = False

        for i, line_eq in enumerate(lines):
            # Check if point satisfies line equation
            x, y = symbols('x y')
            point_coords = (point[0], point[1])  # (a, b)

            # Substitute point into equation
            substituted = line_eq.lhs.subs({x: point_coords[0], y: point_coords[1]}) \
                        - line_eq.rhs.subs({x: point_coords[0], y: point_coords[1]})

            if substituted.simplify() == 0:
                covered = True
                coverage_map[point] = i
                break

        if not covered:
            uncovered.append(point)

    return {
        "verified": len(uncovered) == 0,
        "counterexamples": uncovered,
        "coverage_map": coverage_map
    }
```

---

### Step 4: Integration into RLAC (3 hours)

**File:** `code/adversarial_critic.py`

**Modification:** Add verification step before critic generates attack

```python
def generate_adversarial_attack(solution, problem_context, round_num, reasoning_effort):
    """Generate adversarial attack with computational verification."""

    # NEW: Detect and verify claims
    claims = detect_verifiable_claims(solution, problem_context)

    verification_results = []
    for claim in claims:
        if claim["type"] == "line_coverage":
            parsed = parse_line_coverage_claim(claim["context"])
            verification = verify_line_coverage(parsed)
            verification_results.append({
                "claim": claim,
                "verification": verification
            })

    # NEW: If any claim failed verification, return BROKEN with counterexample
    for result in verification_results:
        if not result["verification"]["verified"]:
            counterexamples = result["verification"]["counterexamples"]

            return {
                "verdict": "BROKEN",
                "attack": f"""
[COMPUTATIONAL VERIFICATION FAILED]

The solution claims:
"{result['claim']['location']}"

However, explicit verification shows this is FALSE.

Counterexample(s):
{format_counterexamples(counterexamples)}

The following points are NOT covered by any of the proposed lines:
""" + "\\n".join([f"  - Point {pt}" for pt in counterexamples])
            }

    # EXISTING: Continue with normal adversarial attack generation
    # ...
```

---

## Expected Behavior

### Problem 1 with Computational Verification:

**Round 0:**
```
Generator: "k=3 is possible. The three lines
  L₁: y=½x+½
  L₂: y=-½x+5/2
  L₃: y=x
cover all six points of S₃."

[COMPUTATIONAL VERIFICATION]
Checking points: (1,1), (1,2), (1,3), (2,1), (2,2), (3,1)

Point (1,1):
  L₁(1) = ½(1) + ½ = 1 ✓ COVERED
Point (1,2):
  L₁(1) = 1 ✗
  L₂(1) = -½(1) + 5/2 = 2 ✓ COVERED
Point (1,3):
  L₁(1) = 1 ✗
  L₂(1) = 2 ✗
  L₃(1) = 1 ✗
  ❌ NOT COVERED

Critic: BROKEN

[COUNTEREXAMPLE]
Your construction does NOT cover point (1,3).
  L₁(1) = 1 ≠ 3
  L₂(1) = 2 ≠ 3
  L₃(1) = 1 ≠ 3

Please revise your construction.
```

**Generator Response (Round 1):**
```
I apologize for the error. Let me reconsider the k=3 case for n=3.

The six points are: (1,1), (1,2), (1,3), (2,1), (2,2), (3,1)

Let me try a different construction:
  L₁: y = x         (covers (1,1), (2,2))
  L₂: y = -½x + 5/2  (covers (1,2), (3,1))
  L₃: y = -2x + 5    (covers (1,3), (2,1))

Verification:
  (1,1): L₁(1) = 1 ✓
  (1,2): L₂(1) = 2 ✓
  (1,3): L₃(1) = -2+5 = 3 ✓
  (2,1): L₃(2) = -4+5 = 1 ✓
  (2,2): L₁(2) = 2 ✓
  (3,1): L₂(3) = -3/2 + 5/2 = 1 ✓
```

**Computational Verification:** ✅ ALL POINTS COVERED

**Critic:** ROBUST ✅

---

## Implementation Checklist

### Phase 1: Basic Infrastructure (5 hours)
- [ ] Create `code/claim_parser.py` with line equation parsing
- [ ] Create `code/claim_verifier.py` with point-line verification
- [ ] Add unit tests for parsing and verification
  - Test case: IMO01 n=3 with correct/incorrect constructions
  - Test case: Polynomial roots verification
  - Test case: Sequence recurrence verification

### Phase 2: RLAC Integration (3 hours)
- [ ] Modify `code/adversarial_critic.py` to call claim detection
- [ ] Add verification step before adversarial attack generation
- [ ] Format counterexamples for critic feedback
- [ ] Add logging for verification results

### Phase 3: Testing (2 hours)
- [ ] Test on problem 1 (should catch k=3 construction error)
- [ ] Test on problem 2 (should NOT interfere with PROVE problem)
- [ ] Test on other FIND problems from IMO benchmark
- [ ] Verify computational verification doesn't slow down RLAC significantly

### Phase 4: Documentation (2 hours)
- [ ] Document claim verification in CLAUDE.md
- [ ] Add examples of supported claim types
- [ ] Update troubleshooting guide
- [ ] Add configuration options (enable/disable verification by problem type)

---

## Configuration

Add environment variables for control:

```bash
# Enable/disable computational verification
export RLAC_COMPUTATIONAL_VERIFICATION=true

# Problem types that require strict verification
export RLAC_VERIFY_PROBLEM_TYPES="FIND,CONSTRUCT"

# Problem types that allow justification gaps
export RLAC_ALLOW_GAPS_PROBLEM_TYPES="PROVE"
```

---

## Expected Results

### Before (Current):

| Problem | Type | Final Status | Verification Quality |
|---------|------|-------------|---------------------|
| Problem 1 | FIND | TIER_1_ONLY | ❌ Critical Error (k=3 construction wrong) |
| Problem 2 | PROVE | TIER_1_ONLY | ✅ Justification Gaps (acceptable) |

### After (With Computational Verification):

| Problem | Type | Final Status | Verification Quality |
|---------|------|-------------|---------------------|
| Problem 1 | FIND | TIER_1_ONLY | ✅ Construction Verified Correct |
| Problem 2 | PROVE | TIER_1_ONLY | ✅ Justification Gaps (acceptable) |

**Success Rate:** 100% (both problems "verification good")

---

## Why This Fix is the Right Solution

### 1. Addresses Root Cause
- Problem 1 failed because RLAC didn't check computational claims
- Problem 2 succeeded because justification gaps are acceptable for PROVE
- Fix adds verification for FIND/CONSTRUCT, leaves PROVE unchanged

### 2. Minimal Code Changes
- ~500 lines of new code (claim_parser.py, claim_verifier.py)
- ~100 lines modified in adversarial_critic.py
- No changes to core RLAC logic or agent_gpt_oss.py

### 3. Surgical Intervention
- Only activates for verifiable claims
- Does not slow down RLAC when no claims detected
- Can be disabled per problem type

### 4. Generalizable
- Works for line coverage (IMO01)
- Can extend to polynomial roots (algebra problems)
- Can extend to sequence verification (number theory)
- Can extend to geometric constructions (compass/straightedge)

---

## Alternative Approaches (NOT Recommended)

### ❌ Alternative 1: Increase critic reasoning to "high"
**Why not:** Problem 2 used "medium" and succeeded. Higher reasoning doesn't guarantee correctness checking.

### ❌ Alternative 2: Add more RLAC rounds
**Why not:** Problem 1 ran 12 rounds and still had critical error. More rounds ≠ better verification.

### ❌ Alternative 3: Use TIER 2 for verification
**Why not:** TIER 2 checks proof rigor, not computational correctness. Different concern.

### ✅ **This Proposal: Computational Verification**
**Why yes:** Directly addresses the gap - RLAC accepts computational claims without verification.

---

## Success Metrics

**After implementation, we expect:**

1. **Problem 1:** Achieves "verification good" status
   - k=3 construction error caught in round 0-1
   - Correct construction found by round 3-5
   - Final solution has no critical errors

2. **Problem 2:** Unchanged (still "verification good")
   - No computational claims to verify
   - Justification gaps remain acceptable
   - Performance impact < 5% (minimal overhead)

3. **Other FIND problems:** Higher success rate
   - Construction errors caught early
   - Faster convergence (no wasted rounds on wrong constructions)
   - 70-80% achieve "verification good" (vs current ~50%)

---

## Timeline

**Week 1:**
- Days 1-2: Implement claim_parser.py and claim_verifier.py
- Day 3: Write unit tests and validate parsing
- Day 4: Integrate into adversarial_critic.py
- Day 5: Test on problem 1 and verify it catches the error

**Week 2:**
- Days 1-2: Test on other IMO problems (expand claim types)
- Day 3: Optimize performance (caching, lazy evaluation)
- Day 4: Documentation and configuration options
- Day 5: Final testing and deployment

**Total: 10 working days (2 weeks)**

---

## Next Steps

1. **Get user approval** for this approach
2. **Start with Phase 1** (basic infrastructure)
3. **Test on problem 1** to validate the fix works
4. **Expand to other claim types** based on IMO benchmark analysis
5. **Deploy to production** once problem 1 achieves "verification good"

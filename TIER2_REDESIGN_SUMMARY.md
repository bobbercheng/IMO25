# TIER 2 Redesign: Proof-Type-Based Verification Strategy

## Executive Summary

Based on dual-expert analysis (OpenAI Engineer + Nvidia Research Scientist) of the TIER 2 optimization test results, **graduated verification has been retired** in favor of **proof-type-based strategy selection**.

### Key Finding

The graduated verification approach (low→medium→high strictness across rounds) caused **oscillating issue counts** instead of monotonic convergence. The root cause was "moving goalposts" - changing verification standards between rounds led the LLM to introduce new errors while fixing old ones.

### New Approach

**Automatic proof-type detection** selects optimal verification strategy:
- **Coordinate geometry**: STRICT verification (formula errors are fatal)
- **Synthetic geometry**: GRADUATED verification (ideas matter more)
- **Mixed/Unknown**: BALANCED fixed medium verification

---

## Configuration Changes

### Before (Graduated Verification)

```python
# TIER 2 Configuration (OLD)
TIER2_MAX_ROUNDS = 8
TIER2_VERIFICATION_REASONING = "medium"
TIER2_USE_GRADUATED_VERIFICATION = True  # LOW → MEDIUM → HIGH

# Results: Oscillating issue counts (5→8→9→4→5→1→4→6)
```

### After (Proof-Type-Based)

```python
# TIER 2 Configuration (NEW)
TIER2_MAX_ROUNDS = 5  # Reduced (fixed verification needs fewer rounds)
TIER2_VERIFICATION_REASONING = "medium"  # Fixed baseline
TIER2_USE_GRADUATED_VERIFICATION = False  # Disabled by default
TIER2_AUTO_DETECT_STRATEGY = True  # NEW - detect proof type

# Expected: Monotonic decrease with fixed goalposts
```

---

## Proof-Type Detection

### Coordinate Geometry Detection

**Indicators** (3+ matches → coordinate proof):
- Coordinate assignments: `A = (x, y)`, `(x_0, y_0)`
- Vector operations: `\cdot` (dot product), `\times` (cross product)
- Distance formulas: `\sqrt{x^2 + y^2}`
- Slope calculations: `\frac{y_1 - y_2}{x_1 - x_2}`
- Terms: "coordinate system", "place...origin", "perpendicular bisector equation"

**Strategy for coordinate proofs**:
```python
{
    'verification_reasoning': 'high',  # STRICT
    'use_graduated_verification': False,
    'max_rounds': 5,
    'require_symbolic_validation': True,  # Validate formulas with SymPy
    'strategy_name': 'COORDINATE_STRICT'
}
```

**Rationale**: Formula errors in coordinate geometry propagate through entire proof. Zero tolerance required.

### Synthetic Geometry Detection

**Indicators** (3+ matches → synthetic proof):
- Angle chasing: `\angle ABC`, "inscribed angle", "central angle"
- Triangle properties: "similar triangle", "congruent"
- Circle theorems: "power of a point", "concyclic", "radical axis"
- Transformations: "homothety", "spiral similarity", "inversion"
- Classical results: "angle bisector theorem", "Ceva", "Menelaus"

**Strategy for synthetic proofs**:
```python
{
    'verification_reasoning': 'medium',
    'use_graduated_verification': True,  # OK for synthetic
    'max_rounds': 8,
    'require_symbolic_validation': False,
    'strategy_name': 'SYNTHETIC_GRADUATED'
}
```

**Rationale**: Synthetic geometry reasoning is about logical flow of ideas. Graduated strictness helps guide proof development.

### Mixed/Unknown Proofs

**Strategy for unclassified proofs**:
```python
{
    'verification_reasoning': 'medium',  # Balanced
    'use_graduated_verification': False,  # Conservative
    'max_rounds': 5,
    'require_symbolic_validation': False,
    'strategy_name': 'BALANCED_FIXED'
}
```

**Rationale**: Based on expert consensus - fixed medium verification is safest default.

---

## Symbolic Validation (NEW)

For coordinate geometry proofs, symbolic validation catches algebraic errors:

### Functions Added

1. **`validate_equation_symbolically(equation_text)`**
   - Uses SymPy to verify equations symbolically
   - Checks if `LHS - RHS` simplifies to 0
   - Returns: `{'valid': bool, 'simplified': str, 'error': str}`

2. **`extract_equations_from_proof(proof_text)`**
   - Extracts numbered equations from proof
   - Pattern: `(3.2) q = ...`
   - Returns list of equation strings for validation

### Example Usage

```python
# Extract and validate equations from coordinate proof
equations = extract_equations_from_proof(solution)

for eq in equations:
    result = validate_equation_symbolically(eq, verbose=True)
    if result['valid'] == False:
        print(f"❌ INVALID: {eq}")
        print(f"   Error: {result['error']}")
```

### Why This Matters

From Problem 2 analysis:
- Round 8 had critical error: `q = -[2pr+r²+x₀²-2px₀]/(2y₀)` (missing y₀² term)
- This error appeared in rounds 3, 4, 7, 8 despite "fixes"
- Symbolic validation would catch this immediately: `LHS - RHS ≠ 0`

---

## Expert Analysis Summary

### OpenAI Engineer Verdict

**Problem**: Graduated verification created "moving goalposts"

**Evidence**:
- Issue count oscillated: 5→8→9→4→5→1→4→6 (NOT monotonic)
- Round 6: 1 gap (best performance)
- Round 7: 4 issues including 2 NEW critical errors (regression)

**Diagnosis**: When verification strictness changed, LLM fixed issues at current level but broke different aspects checked at next level.

**Solution**: Fixed verification level throughout → consistent goalposts → monotonic convergence

### Nvidia Scientist Verdict

**Problem**: Graduated verification inappropriate for algebraic proofs

**Evidence**:
- RLAC solution (180 lines): 0 errors, IMO score 7/7
- Round 8 refinement (300 lines): 2 critical errors, IMO score 4-5/7
- **Refinement made things WORSE**

**Diagnosis**: "Expansion Brittleness" - LLMs have higher error rates when expanding correct terse proofs into verbose detailed proofs. Accepting "proof outline" (low verification) allowed unvalidated algebra → errors propagated.

**Solution**: For coordinate geometry, strict verification from Round 1. Don't accept incomplete algebra.

### Consensus Recommendation

**Accept TIER_1_ONLY as success** for coordinate geometry problems:
- RLAC validation (3 ROBUST verdicts) is rigorous
- Proof is already IMO-competition-ready
- TIER 2 refinement isn't adding value (introducing errors instead)

---

## Implementation Details

### Code Changes

**Files modified:**
1. `code/tier2_refinement.py`
   - Added `uses_coordinate_geometry(solution)` - detect coordinate proofs
   - Added `uses_synthetic_geometry(solution)` - detect synthetic proofs
   - Added `select_tier2_strategy(solution, problem)` - choose optimal strategy
   - Added `validate_equation_symbolically(equation)` - symbolic validation
   - Added `extract_equations_from_proof(proof)` - equation extraction

2. `code/agent_gpt_oss.py`
   - Updated `TIER2_MAX_ROUNDS`: 8 → 5
   - Updated `TIER2_USE_GRADUATED_VERIFICATION`: "true" → "false"
   - Added `TIER2_AUTO_DETECT_STRATEGY`: "true" (NEW)
   - Integrated automatic strategy selection before `tier2_refinement_loop()`
   - Updated configuration print to show auto-detection status

### Backward Compatibility

All changes are **backward compatible**:
- Environment variables can override auto-detection
- Manual configuration still works if `TIER2_AUTO_DETECT_STRATEGY=false`
- Graduated verification can be re-enabled per problem if needed

### Configuration Override

```bash
# Override auto-detection (use manual settings)
export TIER2_AUTO_DETECT_STRATEGY=false
export TIER2_MAX_ROUNDS=8
export TIER2_VERIFICATION_REASONING=high
export TIER2_USE_GRADUATED_VERIFICATION=true
```

---

## Expected Performance Improvements

### For Coordinate Geometry (e.g., Problem 2)

**Before** (graduated verification):
```
Round 1: 5 issues (MEDIUM verification)
Round 2: 8 issues (LOW - too lenient)
Round 3: 9 issues (LOW - accepted bad algebra)
Round 4: 4 issues (LOW)
Round 5: 5 issues (MEDIUM - found new issues)
Round 6: 1 issue (MEDIUM - near success!)
Round 7: 4 issues (MEDIUM - REGRESSION with critical errors)
Round 8: 6 issues (HIGH - more issues found)
Status: TIER_1_ONLY
```

**After** (strict verification):
```
Round 1: 5 issues (HIGH verification - strict from start)
Round 2: 3 issues (HIGH - monotonic decrease)
Round 3: 2 issues (HIGH - continued progress)
Round 4: 1 issue (HIGH - near completion)
Round 5: 0 issues (HIGH - VERIFIED!)
Status: TIER_2_VERIFIED or accept TIER_1_ONLY if proof already correct
```

### For Synthetic Geometry

**Strategy**: Graduated verification still allowed
- Round 1-3: LOW (accept proof outline, establish structure)
- Round 4-6: MEDIUM (IMO standard justifications)
- Round 7-8: HIGH (publication polish)

**Expected**: Smooth progression for idea-driven proofs

---

## Testing Plan

### Phase 1: Validation (Immediate)

1. **Test proof-type detection accuracy**:
   ```bash
   python test_proof_type_detection.py
   ```
   - Load existing RLAC solutions for Problems 1-5
   - Verify coordinate/synthetic detection matches manual classification
   - Check edge cases (mixed proofs)

2. **Test symbolic validation**:
   ```bash
   python test_symbolic_validation.py
   ```
   - Validate correct equations (should pass)
   - Validate equations with known errors from Problem 2 Round 8 (should fail)
   - Measure precision/recall

### Phase 2: Integration Testing (Next)

3. **Re-run Problem 2 with new configuration**:
   ```bash
   python code/agent_gpt_oss.py problems/imo02.txt \
     --use-rlac \
     --rlac-max-rounds 30 \
     --log test_rlac_log/tier2_redesign_p2.log \
     --memory test_rlac_log/tier2_redesign_p2.json
   ```
   - Expected: COORDINATE_STRICT strategy auto-detected
   - Expected: HIGH verification from Round 1
   - Expected: Monotonic decrease in issues (no oscillation)

4. **Test on synthetic geometry problem** (Problem 3 or 4):
   - Expected: SYNTHETIC_GRADUATED strategy auto-detected
   - Expected: Graduated verification used (LOW→MEDIUM→HIGH)
   - Expected: Smooth convergence

### Phase 3: Comparison Study (Later)

5. **Compare old vs new approach**:
   - Metric: Final issue count
   - Metric: Convergence rate (issues/round)
   - Metric: TIER_2_VERIFIED success rate
   - Metric: Rounds needed to achieve TIER 2

---

## Success Criteria

### Primary Goals

✅ **Eliminate oscillation**: Issue counts should decrease monotonically
✅ **Improve convergence**: Achieve TIER_2_VERIFIED in fewer rounds
✅ **Prevent regressions**: No new critical errors after Round 3

### Secondary Goals

✅ **Accurate detection**: 90%+ correct proof-type classification
✅ **Symbolic validation**: Catch algebraic errors in coordinate proofs
✅ **Maintain backward compatibility**: Old configs still work

---

## Future Enhancements

### Short-term

1. **Section-level locking** (Engineer recommendation):
   - Lock verified sections after passing verification
   - Only refine sections with flagged issues
   - Prevents regression in previously-correct sections

2. **Enhanced symbolic validation**:
   - Context-aware equation parsing (handle LaTeX better)
   - Automatic variable substitution (e.g., x₀²+y₀²=r²)
   - Numeric spot-checks for complex expressions

### Long-term

3. **Proof architecture analysis**:
   - Detect if coordinate approach is error-prone for specific problem
   - Suggest alternative (synthetic geometry) after repeated failures
   - Hybrid proofs: coordinate for construction, synthetic for main argument

4. **Adaptive verification**:
   - Learn from refinement history
   - If Round N and Round N+1 find same error, increase strictness
   - If 3 consecutive rounds find 0 new issues, decrease strictness (accept solution)

---

## References

- **Expert Analysis**: `test_rlac_log/tier2_test_p2_optimized.log` (3500+ lines)
- **Previous Optimization**: `TIER2_CONFIG_OPTIMIZATION.md` (graduated verification attempt)
- **Bug Fixes**: `TIER2_*_BUG_FIX*.md` (parsing, format, nested braces, proof problems)
- **Test Results**: `test_rlac_log/tier2_test_p2_optimized_*.json` (RLAC + refinement data)

---

## Conclusion

The shift from **graduated verification** to **proof-type-based strategy selection** addresses the root cause of TIER 2 refinement oscillation:

**Old approach**: One-size-fits-all graduated strictness → moving goalposts → oscillation
**New approach**: Proof-type-specific strategy → fixed goalposts → monotonic convergence

For **coordinate geometry**, the Nvidia Scientist's key insight holds:
> "The RLAC solution was already IMO-competition-ready. The TIER 2 refinement process degraded quality by introducing transcription errors during expansion."

**Accept TIER_1_ONLY as success** when appropriate. TIER 2 is for pedagogical polish, not correctness validation.

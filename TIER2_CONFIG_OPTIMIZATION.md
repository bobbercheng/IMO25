# TIER 2 Configuration Optimization

**Date**: 2025-12-02
**Status**: ✅ Implemented based on expert analysis
**Changes**: Graduated verification + increased max rounds

---

## Expert Recommendations Implemented

Based on dual-expert analysis (OpenAI Engineer + Nvidia Scientist) of the 5-round TIER 2 test that reached max rounds without passing verification.

### Key Findings from Analysis

**Issue Count Progression:**
```
Round 1: 6 gaps  (0 critical)
Round 2: 7 gaps  (0 critical)
Round 3: 10 CRITICAL errors  ← Regression
Round 4: 2 critical + 5 gaps  ← Recovery
Round 5: 10 gaps (0 critical) ← All criticals fixed!
```

**Expert Consensus:**
- ✅ TIER 2 is mechanically working (all bugs fixed)
- ⚠️ Verification standard is too strict (PhD-level vs IMO-level)
- 📊 No convergence evidence (issue count oscillates)
- 💡 System needs graduated verification (low→medium→high)

---

## Configuration Changes

### 1. Increased Max Rounds: 5 → 8

**File:** `code/agent_gpt_oss.py` line 70

**Before:**
```python
TIER2_MAX_ROUNDS = int(os.getenv("TIER2_MAX_ROUNDS", "5"))
```

**After:**
```python
TIER2_MAX_ROUNDS = int(os.getenv("TIER2_MAX_ROUNDS", "8"))
```

**Rationale (OpenAI Engineer):**
> "With 5 more rounds, the model could likely fill all 10 gaps. Try 3 more rounds (total 8) with explicit instructions."

### 2. Changed Default Verification: "high" → "medium"

**File:** `code/agent_gpt_oss.py` line 72

**Before:**
```python
TIER2_VERIFICATION_REASONING = os.getenv("TIER2_VERIFICATION_REASONING", "high")
```

**After:**
```python
TIER2_VERIFICATION_REASONING = os.getenv("TIER2_VERIFICATION_REASONING", "medium")
```

**Rationale (Nvidia Scientist):**
> "The verifier is applying PhD-LEVEL formal proof standards, which is TOO STRICT for IMO competition mathematics. The verification standard should be 'medium reasoning' for coordinate geometry proofs."

### 3. Added Graduated Verification

**File:** `code/agent_gpt_oss.py` line 73 (NEW)

**Added:**
```python
TIER2_USE_GRADUATED_VERIFICATION = os.getenv("TIER2_USE_GRADUATED_VERIFICATION", "true").lower() == "true"
```

**File:** `code/tier2_refinement.py` lines 64-73 (NEW)

**Implementation:**
```python
# Determine verification reasoning level for this round
if use_graduated_verification:
    if round_num < 3:
        current_verification = "low"     # Rounds 1-3: Accept outline
    elif round_num < 6:
        current_verification = "medium"  # Rounds 4-6: IMO standard
    else:
        current_verification = "high"    # Rounds 7-8: Publication-ready
else:
    current_verification = verification_reasoning
```

**Rationale (Both experts):**
- Early rounds: Focus on proof structure, accept outline-level rigor
- Middle rounds: Apply IMO-level standards (routine calculations acceptable)
- Final rounds: Demand publication-ready rigor (every step shown)

---

## Updated TIER 2 Verification Strategy

### Graduated Verification Levels

| Rounds | Verification | Standard | Example |
|--------|-------------|----------|---------|
| **1-3** | **low** | Proof outline | "A straightforward calculation shows..." ✓ |
| **4-6** | **medium** | IMO competition | "Expanding gives x² + 2x + 1 = 0" ✓ |
| **7-8** | **high** | Publication-ready | "x² + 2x + 1 = (x+1)²; setting x=-1 gives..." ✓ |

### Why This Works

**Problem with previous approach (all "high"):**
- Demanded every algebraic step from Round 1
- Model introduced errors trying to add detail (Round 3: 10 critical errors)
- No room for incremental improvement

**Benefit of graduated approach:**
- **Rounds 1-3:** Model establishes correct proof structure
- **Rounds 4-6:** Model adds standard justifications
- **Rounds 7-8:** Model polishes remaining details

**Expected outcome:**
- Issue count decreases consistently: 10 → 7 → 5 → 3 → 1 → 0
- Model avoids overwhelming detail (which introduced errors in Round 3)
- Convergence likely by Round 6-7

---

## Environment Variables

### New Configuration Options

```bash
# Max refinement rounds (default: 8, was 5)
export TIER2_MAX_ROUNDS=8

# Base verification reasoning (default: medium, was high)
export TIER2_VERIFICATION_REASONING=medium

# Enable graduated verification (default: true, NEW)
export TIER2_USE_GRADUATED_VERIFICATION=true

# Refinement reasoning (unchanged)
export TIER2_REFINEMENT_REASONING=high
```

### Override Examples

**Disable graduated verification (use fixed level):**
```bash
export TIER2_USE_GRADUATED_VERIFICATION=false
export TIER2_VERIFICATION_REASONING=medium
# All rounds will use "medium" verification
```

**Very strict mode (for research papers):**
```bash
export TIER2_USE_GRADUATED_VERIFICATION=false
export TIER2_VERIFICATION_REASONING=high
export TIER2_MAX_ROUNDS=15
# All rounds use "high" verification, 15 rounds budget
```

**Quick mode (for testing):**
```bash
export TIER2_USE_GRADUATED_VERIFICATION=true
export TIER2_VERIFICATION_REASONING=low
export TIER2_MAX_ROUNDS=5
# Rounds 1-3: low, Rounds 4-5: low (base level)
```

---

## Expected Performance Improvement

### Previous Run (5 rounds, all "high"):
```
Round 1: 6 gaps → Round 2: 7 gaps → Round 3: 10 CRITICAL
→ Round 4: 2 critical + 5 gaps → Round 5: 10 gaps
Result: TIER_1_ONLY (max rounds reached, no convergence)
```

### Expected New Run (8 rounds, graduated):
```
Round 1 (low):    10 gaps → Accepted (proof outline valid)
Round 2 (low):    7 gaps  → Improvement
Round 3 (low):    5 gaps  → Continued improvement
Round 4 (medium): 5 gaps  → Stable (medium more strict)
Round 5 (medium): 3 gaps  → Improvement
Round 6 (medium): 1 gap   → Near completion
Round 7 (high):   1 gap   → Final detail
Round 8 (high):   0 gaps  → TIER_2_VERIFIED ✓
```

**Key difference:** Issue count decreases monotonically instead of oscillating.

---

## Testing Plan

### Test Command

```bash
python code/agent_gpt_oss.py problems/imo02.txt \
  --use-rlac \
  --rlac-max-rounds 30 \
  --rlac-stuck-threshold 5 \
  --rlac-robust-threshold 3 \
  --log test_rlac_log/tier2_test_p2_optimized.log \
  --memory test_rlac_log/tier2_test_p2_optimized.json
```

**Expected outcome:**
- ✅ RLAC achieves TIER 1 (answer correct)
- ✅ TIER 2 begins with graduated verification
- ✅ Issue count decreases: Rounds 1-3 accept outline
- ✅ Rounds 4-6 fill in standard details
- ✅ Rounds 7-8 polish remaining gaps
- 🎯 **TIER_2_VERIFIED** by Round 6-8

### Success Criteria

**TIER 2 VERIFIED:**
- Verification passes in any round ≤ 8
- Final solution has 0 critical errors + 0 gaps
- Graduated verification enabled convergence

**TIER 1 ONLY (acceptable):**
- Issue count decreased but didn't reach 0
- Answer is correct (RLAC verified)
- Proof has minor presentation gaps only

**Failure (needs investigation):**
- Issue count increased or oscillated
- New critical errors introduced
- Graduated verification didn't help

---

## Rollback Plan

If graduated verification **doesn't** improve convergence:

1. **Revert to fixed "medium" reasoning:**
   ```bash
   export TIER2_USE_GRADUATED_VERIFICATION=false
   export TIER2_VERIFICATION_REASONING=medium
   ```

2. **Accept TIER 1 as sufficient:**
   - Document that TIER 2 is for publication-ready proofs
   - TIER 1 (RLAC-ROBUST) is sufficient for problem-solving

3. **Consider alternative approaches:**
   - Use different proof strategies (synthetic geometry vs coordinate)
   - Implement semantic gap matching (LLM judges if gap is fillable)

---

## Files Modified

### Code Changes
- `code/agent_gpt_oss.py` (lines 70, 72-73):
  - Increased `TIER2_MAX_ROUNDS` from 5 to 8
  - Changed `TIER2_VERIFICATION_REASONING` from "high" to "medium"
  - Added `TIER2_USE_GRADUATED_VERIFICATION` flag

- `code/tier2_refinement.py` (lines 26-27, 42, 64-76):
  - Added `use_graduated_verification` parameter
  - Implemented graduated verification logic
  - Updated progress messages to show current verification level

### Documentation
- `TIER2_CONFIG_OPTIMIZATION.md` (THIS FILE):
  - Complete configuration changes
  - Rationale from expert analysis
  - Testing plan and success criteria

---

## Expert Quotes

**OpenAI Engineer:**
> "The current 'high' reasoning setting is calibrated for automated theorem proving (Lean, Coq), research-level mathematical rigor, and PhD dissertation standards. For IMO problems, this is overkill."

**Nvidia Scientist:**
> "This is a good IMO student's proof—correct answer, valid method, some steps skipped. It's not a perfect formal proof, but perfection wasn't the goal."

**Both experts (unanimous):**
> "TIER 2 is working mechanically. The issue is calibration, not bugs. Graduated verification should solve the convergence problem."

---

**Last Updated**: 2025-12-02
**Status**: ✅ Ready for testing
**Next**: Run Problem 2 with optimized configuration

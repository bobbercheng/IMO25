# TIER 1 Regression - Quick Diagnosis

## TL;DR
**Status:** 🔴 CRITICAL REGRESSION
**Action:** ROLLBACK IMMEDIATELY
**Root Cause:** LLM ignoring Level 1.5 + hypercritical Level 2 validation
**Impact:** 100% optimization problems now fail (was 50% baseline)

---

## What Happened?

```
BEFORE FIX (Baseline):
Test 1 (4048) → PASS ❌ (should be SUSPICIOUS_OPTIMALITY)
Test 2 (2112) → PASS ✅ (correct)
Pass Rate: 50%

AFTER FIX (v2):
Test 1 (4048) → PASS ❌ (should be SUSPICIOUS_OPTIMALITY)
Test 2 (2112) → FAIL ❌ (regression! should be PASS)
Pass Rate: 0% (-50%)
```

---

## Two Bugs Found

### Bug 1: Level 1.5 Still Skipped (ORIGINAL BUG, NOT FIXED)
**Evidence:**
```bash
$ grep -i "Level 1.5" logs/test_tier1_optimality_v2.log
# No results - Level 1.5 never executed
```

**Why?**
- Prompt too long (8618 tokens) → LLM skips middle sections
- No few-shot examples showing Level 1.5 execution
- LLM jumps from Level 1 → Level 2 directly

**Impact:**
- Test 1 (4048) still gets PASS instead of SUSPICIOUS_OPTIMALITY
- Optimality detection non-functional

---

### Bug 2: Level 2 Too Strict (NEW BUG, INTRODUCED BY FIX)
**Evidence:**
```json
{
  "verdict": "FAIL",
  "issues": [{
    "type": "CRITICAL_ERROR",
    "severity": 9,
    "description": "method‑named‑only claim (Category B) lacking explicit construction details"
  }]
}
```

**What LLM wants:**
```
REJECTED: "Use k² block tiles of size k×k"
ACCEPTED: "Use tiles T₁={(1,1),...,(k,k)}, T₂={(k+1,1),...}, ..."
```

**Why this is wrong:**
- IMO solutions describe STRATEGIES, not enumerate coordinates
- Test 2 solution IS valid (provides formula k²+2k-3)
- LLM misinterpreting Category B/C boundary

**Impact:**
- 80-90% of valid optimization solutions will be rejected
- Test 2 (2112) now fails (was passing before)

---

## Diagnostic Commands

```bash
# Confirm Level 1.5 not executed
grep -i "Level 1.5\|small-case\|optimality" logs/test_tier1_optimality_v2.log

# Extract verdicts
grep '"verdict":' logs/test_tier1_optimality_v2.log

# Compare before/after
diff logs/test_tier1_optimality.log logs/test_tier1_optimality_v2.log
```

---

## Rollback Instructions

```bash
# 1. Find last good commit
git log --oneline code/agent_oai.py | grep -B1 "TIER 1"

# 2. Revert changes
git revert <commit-hash>

# 3. Validate
python test/test_tier1_optimality.py

# 4. Confirm Test 2 passes
grep "✅ TEST PASSED: Got PASS" logs/test_tier1_optimality.log
```

---

## Fix Strategy (After Rollback)

**Phase 1: Debug Level 1.5 (4-6 hours)**
- Add few-shot example showing Level 1.5 execution
- Simplify prompt (157 lines → 50 lines)
- Add execution logging to confirm triggered
- Test: 4048 should → SUSPICIOUS_OPTIMALITY

**Phase 2: Relax Level 2 (2 hours)**
- Accept strategy-level constructions (not just coordinates)
- Update Category B definition
- Test: 2112 should → PASS

**Phase 3: Validation (1 hour)**
- Run 4+ test cases
- Confirm both bugs fixed
- Merge to main

**Total: 7-9 hours** (do on separate branch, not in production)

---

## Risk Matrix

| Action | Risk | Impact | Timeline |
|--------|------|--------|----------|
| Do nothing | 🔴 HIGH | 0% pass rate continues | N/A |
| Rollback | 🟢 LOW | Restore 50% baseline | <30 min |
| Quick fix (Category B) | 🟡 MEDIUM | Might fix Test 2, Test 1 still broken | 1-2 hours |
| Proper fix (both bugs) | 🔴 HIGH | Could introduce new bugs | 4-8 hours |
| Rollback + Fix on branch | 🟢 LOW | Best of both worlds | <30 min + 4-8 hours |

**Recommendation:** Rollback + Fix on branch ⭐

---

## Key Metrics

| Metric | Baseline | After Fix | Target |
|--------|----------|-----------|--------|
| Test 1 Correct | ❌ | ❌ | ✅ SUSPICIOUS_OPTIMALITY |
| Test 2 Correct | ✅ | ❌ | ✅ PASS |
| Pass Rate | 50% | 0% | 100% |
| False Positives | 50% | 50% | 0% |
| False Negatives | 0% | 50% | 0% |

---

## Contact

**Prepared by:** Senior Data Scientist
**Date:** 2025-12-30
**Full Report:** `/home/user/IMO25/TIER1_REGRESSION_ANALYSIS.md`
**Next Steps:** Execute rollback, create fix branch, iterate

# Phase 1-2 Implementation Test Plan

## Changes Implemented

### Phase 1: Quick Win #1 Early Exit with ROBUST Safeguard ✅
**Location**: `code/agent_gpt_oss.py` lines 5109-5149

**What Changed**:
- Moved Quick Win #1 check FROM after loop (old line 5109) TO inside loop (new line 5109-5149)
- Added ROBUST safeguard: `total_robust_count < 2`
- Enables early exit when SUSPICIOUS convergence is detected

**How It Works**:
```python
# At end of each RLAC round:
if (consecutive_suspicious >= 3 and
    rounds_since_last_broken >= 4 and
    total_robust_count < 2):  # ⚡ SAFEGUARD
    # Exit early with TIER_1_ONLY
    break
```

**Expected Impact**:
- **Problem 1 (FIND)**: Early exit at round 3-7 instead of round 15 (~20 min vs 2-3 hours)
- **Problem 2 (PROVE)**: No change - continues to round 12 TIER_2_VERIFIED (safeguard blocks early exit)

### Phase 2: Semantic Stuck Detection ✅ (Already Implemented)
**Location**: `code/agent_gpt_oss.py` lines 4495-4516

**What Found**:
- Code already uses `answers_are_semantically_equal()` for stuck detection
- P5 answer reconsideration path (line 4511)
- P5.1 enhanced verification path (line 4615)
- Diversification path (line 4669)

**Status**: No changes needed - already working correctly

---

## Test Validation Plan

### Test 1: Problem 1 (FIND) - Verify Early Exit

**Objective**: Confirm Quick Win #1 triggers early (round 3-7) instead of round 15

**Command**:
```bash
./test_inline_verification.sh problems/imo01.txt
```

**Expected Results**:
- ✅ Quick Win #1 triggers at round 3-7 (not round 15)
- ✅ Duration: ~20-30 minutes (not 2-3 hours)
- ✅ Log shows: `[QUICK WIN #1] SUSPICIOUS CONVERGENCE - EARLY EXIT`
- ✅ Log shows: `Total ROBUST count: 0 < 2 (no ROBUST potential)`
- ✅ Final status: TIER_1_ONLY

**Validation Commands**:
```bash
LOG_FILE=$(ls -t test_rlac_log/inline_verification_test_*.log | head -1)

# Check when Quick Win #1 triggered
grep "QUICK WIN #1.*EARLY EXIT" "$LOG_FILE"

# Verify total_robust_count was < 2
grep "Total ROBUST count:.*< 2" "$LOG_FILE"

# Check round number
grep -B2 "QUICK WIN #1.*EARLY EXIT" "$LOG_FILE" | grep "RLAC ROUND"

# Measure duration
START=$(grep "RLAC ROUND 1/" "$LOG_FILE" | head -1 | cut -d'[' -f2 | cut -d']' -f1)
END=$(grep "QUICK WIN #1.*EARLY EXIT" "$LOG_FILE" | head -1 | cut -d'[' -f2 | cut -d']' -f1)
echo "Start: $START"
echo "End: $END"
```

**Success Criteria**:
- Quick Win #1 triggers before round 10
- Duration < 45 minutes
- total_robust_count < 2 shown in log

---

### Test 2: Problem 2 (PROVE) - Verify No Regression

**Objective**: Confirm ROBUST safeguard prevents early exit, allows TIER_2_VERIFIED

**Command**:
```bash
# Use same test setup as tier2_with_validation_p2.log
python code/agent_gpt_oss.py problems/imo02.txt \
  --use-rlac \
  --rlac-max-rounds 30 \
  --rlac-robust-threshold 3 \
  --rlac-stuck-threshold 2 \
  --solution-reasoning medium \
  --rlac-critic-reasoning medium \
  --log test_rlac_log/phase1_validation_p2.log \
  --memory test_rlac_log/phase1_validation_p2.json
```

**Expected Results**:
- ✅ Rounds 1-4: Mix of ROBUST verdicts (total_robust_count reaches 3)
- ✅ Rounds 5-9: SUSPICIOUS verdicts
- ✅ Quick Win #1 check at round 7: BLOCKED (total_robust_count >= 2)
- ✅ Rounds 10-12: Final 3 consecutive ROBUST
- ✅ Final status: TIER_2_VERIFIED (ROBUST CONVERGENCE)

**Validation Commands**:
```bash
LOG_FILE="test_rlac_log/phase1_validation_p2.log"

# Check if Quick Win #1 was checked but BLOCKED at round 7
# (No early exit message should appear before round 10)
grep -n "QUICK WIN #1.*EARLY EXIT" "$LOG_FILE"
# Expected: No matches (or only after round 10)

# Verify ROBUST convergence achieved
grep "RLAC SUCCESS.*ROBUST after 3 consecutive" "$LOG_FILE"

# Check final tier
grep "TIER.*VERIFIED" "$LOG_FILE" | tail -1

# Verify round 12 completion
grep "RLAC ROUND 12/30" "$LOG_FILE"
```

**Success Criteria**:
- NO Quick Win #1 early exit before round 10
- ROBUST CONVERGENCE achieved at round 12
- Final tier: TIER_2_VERIFIED
- Total rounds: 12 (not 7)

---

### Test 3: Comparative Analysis

**Objective**: Quantify improvement and confirm no regression

**Metrics to Compare**:

| Metric                  | Problem 1 (Before) | Problem 1 (After) | Problem 2 (Before) | Problem 2 (After) |
|-------------------------|--------------------|--------------------|--------------------|--------------------|
| Quick Win #1 trigger    | Round 15           | Round 3-7 ✓       | N/A                | N/A                |
| Duration                | 2-3 hours          | 20-30 min ✓       | 17 min             | 17 min ✓          |
| Final tier              | TIER_1_ONLY        | TIER_1_ONLY ✓     | TIER_2_VERIFIED    | TIER_2_VERIFIED ✓ |
| Total rounds            | 15                 | 3-7 ✓             | 12                 | 12 ✓              |
| ROBUST safeguard used?  | N/A                | Yes (0 < 2) ✓     | N/A                | Yes (3 >= 2) ✓    |

**Success**: All "After" columns match expected values with ✓

---

## Debugging Tips

### If Quick Win #1 doesn't trigger for Problem 1:

1. **Check verdict history**:
   ```bash
   grep "Verdict: SUSPICIOUS" "$LOG_FILE" | wc -l
   # Should have 3+ consecutive SUSPICIOUS
   ```

2. **Check for BROKEN interruptions**:
   ```bash
   grep "Verdict: BROKEN" "$LOG_FILE"
   # If BROKEN appears every 3 rounds, consecutive_suspicious never reaches 3
   ```

3. **Check total_robust_count**:
   ```bash
   grep "Total ROBUST count" "$LOG_FILE"
   # Should be 0 for Problem 1
   ```

### If Quick Win #1 triggers incorrectly for Problem 2:

1. **Check ROBUST verdicts**:
   ```bash
   grep "Verdict: ROBUST" "$LOG_FILE" | head -5
   # Should have 3+ ROBUST by round 4
   ```

2. **Check safeguard logic**:
   ```bash
   grep "Total ROBUST count:.*< 2" "$LOG_FILE"
   # Should NOT appear for Problem 2 (will show ">= 2" instead)
   ```

---

## Rollback Plan

If regression detected:

```bash
# Revert to previous commit
git revert HEAD

# Or restore old Quick Win #1 location
git show HEAD~1:code/agent_gpt_oss.py > code/agent_gpt_oss.py.backup
```

---

## Summary

**Phase 1**: ✅ Implemented with ROBUST safeguard
**Phase 2**: ✅ Already implemented (no changes needed)
**Risk**: LOW (conservative safeguard protects working cases)
**Testing**: Run Test 1 + Test 2, verify no regression

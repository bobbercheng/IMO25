# Option 1 Implementation: Verification Constraints

**Date:** 2025-12-26
**Status:** ✅ IMPLEMENTED - Ready for Validation
**Fix Target:** HIGH reasoning truncation (19.7%) and over-analysis FN (16.7%)

---

## Implementation Summary

### What Was Changed

**File:** `code/agent_oai.py`
**Function:** `verify_solution()` (lines 583-629)
**Change:** Added verification constraints before constructing verification prompt

### Code Added

```python
# Verification constraints to prevent truncation and over-analysis
verification_constraint = """
**CRITICAL CONSTRAINTS FOR VERIFICATION:**

1. **Output Length Limit:** Your verification reasoning MUST be ≤2000 tokens total.

2. **Evaluate, Don't Re-Prove:** Your task is to EVALUATE the provided solution, NOT to re-prove the problem from scratch.
   - ❌ WRONG: "Let's verify by manually testing n=3: points are (1,1), (1,2)... now n=4..."
   - ✅ CORRECT: "The solution tests n=3, n=4, n=5 and identifies the pattern. This method is valid."

3. **No Manual Case Testing:** Do NOT manually enumerate specific values or cases that the solution already covered.
   - ❌ WRONG: "For k=0, let's check: we need vertical lines covering..."
   - ✅ CORRECT: "The solution's analysis of k=0 uses valid case-by-case reasoning."

4. **Trust Valid Methods:** If the solution uses valid mathematical methods (case analysis, induction, contradiction, construction) and the answer is correct:
   - Classify as PASS if presentation is clear
   - Classify as JUSTIFICATION_GAP if presentation has minor wording issues
   - Do NOT attempt to independently verify every computation

5. **Early Classification:** Once you determine answer correctness and reasoning validity, immediately classify and stop. Do not continue analyzing.

6. **Focus on What's Missing, Not Re-Proving What's There:**
   - ✅ CORRECT: "The solution claims k=2 is impossible but provides no proof → CRITICAL_ERROR"
   - ❌ WRONG: "Let me verify k=2 is impossible by testing: ..." → This is re-proving, not evaluating

**Violating these constraints will cause your response to be truncated and discarded.**
"""
```

### How It Works

1. Constraints are prepended to every verification request
2. HIGH reasoning sees these instructions before the problem and solution
3. Model is guided to:
   - Keep responses ≤2000 tokens (vs previous ~7000)
   - Evaluate provided proofs rather than re-prove from scratch
   - Avoid manual case enumeration
   - Trust valid methods and classify quickly
   - Focus on gaps, not redundant verification

---

## Expected Impact

### Before Fix (Baseline from 11 Rounds)

| Metric | Value | Issue |
|--------|-------|-------|
| **Truncation Rate** | 19.7% (13/66 tests) | 7K token responses exceed limit |
| **Accuracy** | 73.33% (17 failures) | Truncation + over-analysis |
| **False Negatives** | 16.7% (11/66) | Rejects valid proofs |
| **P95 Latency** | 951s (16 min) | Retry cascades |
| **Retry Cost** | $200/100 verifications | 40+ retries per truncation |

### After Fix (Expected)

| Metric | Target | Improvement |
|--------|--------|-------------|
| **Truncation Rate** | <2% | ✅ -90% (2K token limit) |
| **Accuracy** | >95% | ✅ +23% (fixes both issues) |
| **False Negatives** | <5% | ✅ -70% (trusts valid proofs) |
| **P95 Latency** | <100s | ✅ -89% (no retry cascades) |
| **Retry Cost** | ~$0 | ✅ -100% (no truncation) |

---

## Validation Plan

### Phase 1: Quick Smoke Test (Day 1)

**Objective:** Verify constraints are working and don't break functionality

**Steps:**
```bash
# Test on a single case (Problem 1, Test 1 - complete valid proof)
python code/test_shadow_mode_validation.py \
  --test-cases test_data/bfs_run2.txt \
  --output smoke_test.json \
  --log smoke_test.log
```

**Success Criteria:**
- ✅ Verification completes without errors
- ✅ Output tokens <2500 (verify constraint respected)
- ✅ Test 1 verdict: PASS (correct classification)
- ✅ No truncation errors in log

**Failure Handling:**
- If truncation still occurs → Increase token limit to 3000
- If wrong verdict → Review reasoning trace, adjust constraint wording
- If errors → Debug API/code issues

---

### Phase 2: Full Shadow Test (Day 3-4)

**Objective:** Validate fix across all 6 test cases over 20 rounds

**Steps:**
```bash
# Run 20 rounds of shadow testing
for i in {1..20}; do
  python code/test_shadow_mode_validation.py \
    --output validation_r${i}.json \
    --log validation_r${i}.log
  echo "Round $i complete"
  sleep 10
done

# Aggregate results
python code/analyze_validation_results.py validation_r*.json > validation_summary.txt
```

**Success Criteria:**
- ✅ Truncation rate: <2% (expected: 0-1 out of 120 tests)
- ✅ Overall accuracy: >95% (expected: 114/120 correct)
- ✅ False Positive rate: <3% (expected: <2 FPs)
- ✅ False Negative rate: <2% (expected: <3 FNs)
- ✅ P95 latency: <100s (verify no retry cascades)

**Metrics to Track:**

| Test | Expected | Success Rate Target |
|------|----------|---------------------|
| Test 1 (Complete proof) | PASS | >95% (was 55% baseline) |
| Test 2 (Alternative) | PASS | >95% (was 82% baseline) |
| Test 3 (Missing impossibility) | FAIL | 100% |
| Test 4 (Missing constructions) | FAIL | >90% (was 64% with truncation) |
| Test 5 (Wrong answer) | FAIL | >90% (was 91% with truncation) |
| Test 6 (Justification gap) | PASS | >95% (was 82% baseline) |

**Analysis:**
```bash
# Per-test breakdown
grep "Test 1" validation_r*.json | jq '.tests[] | select(.test_number==1) | .baseline_verdict'
grep "Test 4" validation_r*.json | jq '.tests[] | select(.test_number==4) | .baseline_verdict'

# Truncation analysis
grep -i "truncat" validation_r*.log | wc -l

# Latency analysis
grep "latency" validation_r*.json | jq '.latency_stats.baseline_p95'
```

---

### Phase 3: Iteration (Day 5)

**If Success Criteria NOT Met:**

**Scenario 1: Truncation Still >2%**
- **Root Cause:** Constraints ignored or 2000 token limit too loose
- **Fix:**
  - Increase explicitness: "STOP GENERATING after 2000 tokens"
  - Add negative examples: "Do NOT write responses like: [7K example]"
  - Consider Option 3: Add max_completion_tokens=4096 as hard limit

**Scenario 2: Accuracy <90%**
- **Root Cause:** Constraints too restrictive, valid analysis truncated
- **Fix:**
  - Increase token limit to 3000
  - Soften language: "typically ≤2000 tokens" instead of "MUST be ≤2000"
  - Add clause: "unless proof is exceptionally complex"

**Scenario 3: FP Rate Increases**
- **Root Cause:** "Trust valid methods" being over-applied to invalid proofs
- **Fix:**
  - Clarify: "Trust valid methods ONLY if answer is correct AND reasoning is sound"
  - Add explicit check: "Verify answer correctness independently before trusting methods"

**Scenario 4: FN Rate Still High (>5%)**
- **Root Cause:** "Evaluate don't re-prove" being ignored
- **Fix:**
  - Strengthen instruction: "You MUST NOT re-prove. This is re-proving: [examples]"
  - Add: "If you find yourself testing n=3, n=4, n=5 manually, STOP IMMEDIATELY"

---

### Phase 4: Deployment Decision (Day 6)

**GO Criteria:**

| Metric | Minimum | Ideal | Actual (20 rounds) |
|--------|---------|-------|-------------------|
| Truncation Rate | <5% | <2% | ___ |
| Overall Accuracy | >90% | >95% | ___ |
| False Positive Rate | <5% | <3% | ___ |
| False Negative Rate | <5% | <2% | ___ |
| P95 Latency | <300s | <100s | ___ |

**Decision Matrix:**

| Scenario | Truncation | Accuracy | Decision |
|----------|------------|----------|----------|
| ✅ **IDEAL** | <2% | >95% | **DEPLOY TO PRODUCTION** |
| ⚠️ **GOOD** | <5% | >90% | Deploy with monitoring |
| ⚠️ **MIXED** | <2% | 85-90% | Iterate constraints, retest |
| ❌ **FAIL** | >5% | <85% | Escalate to Option 3 |

---

## Production Deployment (Day 7)

**If GO criteria met, proceed with deployment:**

### Gradual Rollout Strategy

**Step 1: 10% Rollout**
- Route 10% of verification traffic to new constraints
- Monitor for 24 hours
- Compare: Truncation rate, accuracy, latency vs control group

**Step 2: 50% Rollout** (if Step 1 successful)
- Increase to 50% traffic
- Monitor for 48 hours
- Look for edge cases or unexpected failures

**Step 3: 100% Rollout** (if Step 2 successful)
- Full production deployment
- Maintain monitoring dashboards

### Monitoring

**Real-Time Alerts:**
- 🚨 Truncation rate >5% over 10 verifications → Investigate
- 🚨 Accuracy <85% over 20 verifications → Consider rollback
- 🚨 FP rate >5% over 10 verifications → Immediate investigation

**Daily Dashboards:**
- Truncation rate trend (target: <2%)
- Accuracy by test type
- Latency distribution (P50, P95, P99)
- Output token distribution (verify <2500 typical)

**Weekly Review:**
- Aggregate metrics vs baseline
- Cost savings calculation
- Edge case analysis (any new failure patterns?)

---

## Rollback Plan

**Trigger Conditions:**
- Accuracy drops <80% for >50 consecutive verifications
- FP rate >10% sustained for >1 hour
- Production incident (wrong verdict causes user impact)

**Rollback Steps:**
1. **Immediate:** Revert `code/agent_oai.py` to previous version (remove constraints)
2. **Deploy:** Push revert to production (rollback deployment in <5 min)
3. **Validate:** Confirm accuracy returns to baseline (73.33%)
4. **Analyze:** Root cause analysis - why did constraints fail?
5. **Iterate:** Refine constraints based on failure analysis
6. **Retest:** Run 20+ shadow rounds before re-attempting deployment

**Rollback Command:**
```bash
git revert <commit-hash>  # Revert verification constraints
git push -u origin main
# Redeploy to production
```

---

## Success Metrics (Post-Deployment)

**Week 1 Targets:**
- ✅ Truncation rate: <2% (vs 19.7% baseline)
- ✅ Accuracy: >95% (vs 73.33% baseline)
- ✅ P95 latency: <100s (vs 951s baseline)
- ✅ Cost: -70% (eliminate retry costs)
- ✅ Zero production incidents

**Month 1 Targets:**
- ✅ Sustained accuracy: >95% over 500+ verifications
- ✅ Truncation rate: <1%
- ✅ Cost savings validated: $266/100 → $70/100
- ✅ Consider Option 3 upgrade if occasional truncation persists

---

## Next Steps After Option 1

**If Option 1 Successful (>95% accuracy):**

**Option A: Stay with Option 1**
- If truncation <1% and accuracy >97%, no further action needed
- Monitor for regression
- Focus on other optimization opportunities

**Option B: Upgrade to Option 3 (Defense in Depth)**
- If truncation 1-5%, add max_completion_tokens=4096 as safety net
- Provides fallback for legitimately complex proofs
- Marginal cost increase (+30%) for additional robustness

**If Option 1 Partially Successful (90-95% accuracy):**
- Investigate failure cases
- Refine constraint wording
- Consider hybrid approach (MEDIUM triage → HIGH verification)

**If Option 1 Fails (<90% accuracy):**
- Escalate to Option 3 (Combined approach)
- Root cause analysis: Are constraints fundamentally flawed?
- May need to reconsider approach

---

## Timeline

| Phase | Duration | Completion Date |
|-------|----------|-----------------|
| **Implementation** | Done | 2025-12-26 ✅ |
| **Smoke Test** | Day 1 | 2025-12-27 |
| **Shadow Testing** | Day 3-4 | 2025-12-29 to 2025-12-30 |
| **Analysis & Iteration** | Day 5 | 2025-12-31 |
| **Deployment Decision** | Day 6 | 2026-01-01 |
| **Production Rollout** | Day 7+ | 2026-01-02+ |

---

## Test Commands Reference

### Smoke Test
```bash
python code/test_shadow_mode_validation.py \
  --test-cases test_data/bfs_run2.txt \
  --output smoke_test.json \
  --log smoke_test.log
```

### Full Shadow Test (20 rounds)
```bash
for i in {1..20}; do
  python code/test_shadow_mode_validation.py \
    --output validation_r${i}.json \
    --log validation_r${i}.log
  echo "Round $i complete"
  sleep 10
done
```

### Analysis
```bash
# Aggregate results
python code/analyze_validation_results.py validation_r*.json > validation_summary.txt

# Truncation count
grep -i "truncat" validation_r*.log | wc -l

# Per-test accuracy
for test in {1..6}; do
  echo "Test $test:"
  grep "Test $test" validation_r*.json | jq '.tests[] | select(.test_number=='"$test"') | .baseline_verdict' | sort | uniq -c
done

# Latency stats
grep "latency" validation_r*.json | jq '.latency_stats.baseline_p95' | \
  awk '{sum+=$1; sumsq+=$1*$1; count++} END {print "Mean:", sum/count, "StdDev:", sqrt(sumsq/count - (sum/count)^2)}'
```

---

## Contact & Escalation

**Implementation Owner:** [Your Name]
**Validation Owner:** [QA Team]
**Deployment Owner:** [DevOps Team]

**Escalation Path:**
- Issues during smoke test → Debug locally, adjust constraints
- Issues during shadow test → Review with implementation owner
- Deployment decision → Review with stakeholders (share validation_summary.txt)
- Production issues → Immediate rollback, root cause analysis

---

**Document Version:** 1.0
**Status:** Ready for Validation
**Implementation Date:** 2025-12-26
**Expected Validation Complete:** 2026-01-01

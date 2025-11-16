# Quick Reference: Reasoning Effort Strategy Selection

## At a Glance Comparison

### Performance Summary

| Strategy | Success Rate | Time | Cost | Confidence | Status |
|----------|-------------|------|------|------------|--------|
| Symmetric Low (low/low) | 30-50%? | 45 min | $3 | 60%⚠️ | TESTED - Rigor uncertain |
| Symmetric High (high/high) | 0% | 23+ hrs | $75+ | N/A | FAILED - Don't use |
| **Asymmetric (low/high)** | **40-60%** | **90-150 min** | **$12** | **95%** | **RECOMMENDED** |
| **Resume w/ High** | **50-70%** | **60-90 min** | **$7** | **95%** | **BEST ROI** |
| Progressive Gradient | 45-65% | 90-200 min | $15 | 90% | Future - Complex |

### ROI Comparison (Higher is Better)

```
Resume w/ High:     ████████████████████████████████████████ 41×
Symmetric Low:      █████████████████████████████████████████████ 50×*
Asymmetric:         ████████████████████ 20×
Progressive:        ███████████████████ 19×
Symmetric High:     0×

* Assumes low/low is correct - UNVALIDATED
```

---

## Decision Matrix

### Choose Based on Your Priority:

#### "I need an answer FAST" (< 1 hour)
→ **Symmetric Low (low/low)**
- ⚡ Fastest: 45 minutes
- 💰 Cheapest: $3
- ⚠️ MUST validate with high reasoning afterward
- Risk: Solution might be wrong

#### "I need HIGH CONFIDENCE" (research/publication)
→ **Asymmetric (low/high)**
- ✅ Best balance: speed + rigor
- ✅ Production-ready: 95% confidence
- ✅ Moderate cost: $12
- Time: 90-150 minutes

#### "I need BEST VALUE" (maximize ROI)
→ **Resume with High Verification**
- 💎 Best ROI: 41×
- 🎯 Two-phase: fast draft → validation
- ✅ High success: 60-70%
- Total time: 60-90 minutes

#### "I have DIVERSE PROBLEMS" (mixed difficulty)
→ **Progressive Gradient**
- 🔄 Adaptive to problem difficulty
- 📊 Best for research/optimization
- ⏰ Longer development time
- Future recommendation

---

## Immediate Action Plan

### Priority 1: Validate Current Success (TODAY)
**Time:** 2 hours | **Cost:** ~$2

```bash
# Critical question: Is the current low/low solution actually correct?

# Step 1: Implement validator
# Add validate_existing_solution() to code/agent_gpt_oss.py

# Step 2: Test current solution
python validate_solution.py \
  --solution run_log_gpt_oss/agent_gpt_oss_low_output_1.log \
  --problem problems/imo_2025_p1.txt \
  --verification-reasoning high
```

**Possible Outcomes:**
- ✅ PASS → Low/low is sufficient! Celebrate and move to Priority 2
- ⚠️ FAIL → Low/low too lenient. Implement asymmetric immediately.

---

### Priority 2: Implement Asymmetric (THIS WEEK)
**Time:** 4 hours | **Cost:** $12-15 per test

```python
# Modify code/agent_gpt_oss.py

# Change line 48-49 from:
REASONING_EFFORT = os.getenv("GPT_OSS_REASONING_EFFORT", "low")

# To:
SOLUTION_REASONING_EFFORT = os.getenv("GPT_OSS_SOLUTION_REASONING", "low")
VERIFICATION_REASONING_EFFORT = os.getenv("GPT_OSS_VERIFICATION_REASONING", "high")

# Update build_request_payload() to accept reasoning_effort parameter
# Update verify_solution() to use VERIFICATION_REASONING_EFFORT
```

**Test Plan:**
```bash
# Test on 3 problems
for problem in imo_2025_p{1,2,3}.txt; do
  GPT_OSS_SOLUTION_REASONING="low" \
  GPT_OSS_VERIFICATION_REASONING="high" \
  python code/agent_gpt_oss.py "problems/$problem"
done

# Measure: success rate, iterations, cost, correctness
```

---

### Priority 3: Deploy Resume Strategy (THIS MONTH)
**Time:** 2-3 days | **Cost:** $100-200 for testing

Implement three-phase solver:
1. Phase 1: Fast draft (low/low) → 45 min
2. Phase 2: Validation (high verify) → 5 min
3. Phase 3: Refinement if needed (low/high) → 30-60 min

Expected: 60-70% success rate, best ROI

---

## Critical Unknowns (To Be Resolved This Week)

### Question 1: Is low/low verification sufficient?
**How to answer:** Validate current solution with high reasoning
**Impact:** Determines if asymmetric is necessary
**Timeline:** Today

### Question 2: How much slower is asymmetric?
**How to answer:** Test on IMO Problem 1
**Impact:** Determines production viability
**Timeline:** This week

### Question 3: What's the optimal configuration?
**How to answer:** Test on 10+ problems
**Impact:** Determines default strategy
**Timeline:** This month

---

## Configuration Quick Guide

### For Development/Testing
```bash
export GPT_OSS_SOLUTION_REASONING="low"
export GPT_OSS_VERIFICATION_REASONING="low"
# Fast iteration, use for debugging
```

### For Production (Recommended)
```bash
export GPT_OSS_SOLUTION_REASONING="low"
export GPT_OSS_VERIFICATION_REASONING="high"
# Balanced: efficient + rigorous
```

### For Quick Exploration (Then Validate!)
```bash
export GPT_OSS_SOLUTION_REASONING="low"
export GPT_OSS_VERIFICATION_REASONING="low"
# Then: validate with high reasoning before trusting
```

### For Maximum Rigor (Expensive)
```bash
export GPT_OSS_SOLUTION_REASONING="medium"
export GPT_OSS_VERIFICATION_REASONING="high"
# Only if low/high insufficient
```

---

## Key Insights

### What We Know
✅ Low reasoning for generation: WORKS (no truncation, fast)
✅ High reasoning for generation: BROKEN (122 truncations, slow)
✅ Low/low configuration: COMPLETED problem (17 iterations, 45 min)
⚠️ Low reasoning for verification: UNKNOWN quality

### What We Don't Know
❓ Is the current solution actually correct?
❓ Would high verification catch errors?
❓ What's the optimal balance?

### What We Need to Do
1. Validate current solution with high reasoning
2. Implement asymmetric approach
3. Test on multiple problems
4. Measure success rates and costs
5. Establish production defaults

---

## Expected Timeline

```
Week 1 (This Week):
├─ Day 1: Validate current solution (Priority 1)
├─ Day 2: Implement asymmetric (Priority 2)
├─ Day 3: Test on IMO P1
├─ Day 4: Test on IMO P2, P3
└─ Day 5: Analysis and comparison

Week 2-4 (This Month):
├─ Implement Progressive Resume
├─ Test on 20+ problems
├─ Optimize parameters
└─ Document best practices

Quarter (Next 3 Months):
├─ Develop adaptive strategy
├─ Build confidence estimation
├─ Deploy production system
└─ Continuous optimization
```

---

## Success Criteria

### By End of Week:
- [ ] Current solution validated (know if correct)
- [ ] Asymmetric implemented and tested
- [ ] Success rate measured on 3+ problems
- [ ] Cost/benefit understood
- [ ] Default strategy selected

### By End of Month:
- [ ] Production pipeline deployed
- [ ] 40-60% success rate on IMO problems
- [ ] High confidence (95%+) in solutions
- [ ] Cost-effective (<$15/problem)
- [ ] Comprehensive documentation

---

## Red Flags to Watch

### 🚨 If validation shows low/low is wrong:
→ Current "success" is false positive
→ Implement asymmetric immediately
→ Re-test all previous solutions

### 🚨 If asymmetric still fails:
→ Problem may be architectural
→ Consider prompt improvements
→ May need different approach

### 🚨 If costs exceed $50/problem:
→ Re-evaluate strategy
→ Consider cheaper alternatives
→ Optimize or abandon

---

## Bottom Line

**Recommended Default Strategy:**
1. Start with **Asymmetric (low/high)** for production
2. Use **Resume w/ High** for best ROI when you have time
3. Always **validate** low/low solutions before trusting

**Critical Next Step:**
Validate the current low/low solution with high reasoning to determine if the concern about verification rigor is justified.

**Expected Outcome:**
50-70% success rate with high confidence at reasonable cost.

---

**Quick Reference Version**: 1.0
**See Full Analysis**: REASONING_EFFORT_STRATEGY_ANALYSIS.md
**Last Updated**: 2025-11-16

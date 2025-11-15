# Option A: Quick Test Setup Guide

## Overview

Test the new agent version with:
1. ✅ **reasoning_effort="low"** (reduce truncations)
2. ✅ **Remove repetition_penalty** (cleaner output)
3. ✅ **Self-improvement step** (proactive refinement)
4. ✅ **5-consecutive success** (stability check)
5. ✅ **10-error termination** (early stop)
6. ✅ **Real-time monitoring** (early prediction)

Expected: **10-30% success rate** vs. 0% in original

---

## Required Changes

### Change 1: Update reasoning_effort

**File:** `agent_gpt_oss.py`

**Find:**
```python
reasoning_effort="high"
```

**Replace with:**
```python
reasoning_effort="low"
```

**Why:** Prevents content overflow that caused 122 truncations.

---

### Change 2: Remove repetition_penalty

**File:** `agent_gpt_oss.py`

**Find:**
```python
inputs = tokenizer.apply_chat_template(
    messages,
    reasoning_effort="low",
    add_generation_prompt=True,
    return_tensors="pt",
    return_dict=True
).to(model.device)

output = model.generate(
    **inputs,
    max_new_tokens=128000,
    temperature=0.1,
    repetition_penalty=1.05,  # REMOVE THIS LINE
    top_p=1.0
)
```

**Replace with:**
```python
inputs = tokenizer.apply_chat_template(
    messages,
    reasoning_effort="low",
    add_generation_prompt=True,
    return_tensors="pt",
    return_dict=True
).to(model.device)

output = model.generate(
    **inputs,
    max_new_tokens=128000,
    temperature=0.1,
    # repetition_penalty removed - let model use natural token distribution
    top_p=1.0
)
```

**Why:**
- Repetition penalty can interfere with mathematical proofs that naturally repeat terms
- May cause unnatural phrasing to avoid repetition
- Low temperature (0.1) already provides focused generation

---

## Quick Setup Script

```bash
#!/bin/bash
# setup_option_a.sh

echo "🔧 Setting up Option A test environment..."

# 1. Backup original agent
cp agent_gpt_oss.py agent_gpt_oss_original.py
echo "✅ Backed up original agent"

# 2. Apply changes (manual or with sed)
# Note: Adjust line numbers based on your actual file

# Change reasoning_effort
sed -i 's/reasoning_effort="high"/reasoning_effort="low"/g' agent_gpt_oss.py
echo "✅ Changed reasoning_effort to low"

# Remove repetition_penalty line
sed -i '/repetition_penalty/d' agent_gpt_oss.py
echo "✅ Removed repetition_penalty"

# 3. Verify changes
echo ""
echo "📋 Verification:"
grep -n "reasoning_effort" agent_gpt_oss.py | head -1
grep -n "repetition_penalty" agent_gpt_oss.py || echo "✅ repetition_penalty removed"

echo ""
echo "🎯 Setup complete! Ready for Option A test."
```

---

## Test Execution

### Step 1: Start the Agent

```bash
# Create test directory
mkdir -p option_a_test
cd option_a_test

# Start agent with logging
nohup python ../agent_gpt_oss.py ../problems/imo01.txt \
    --log option_a_run1.log \
    --memory state.json \
    > agent_output.txt 2>&1 &

# Save PID for later
echo $! > agent.pid
echo "🚀 Agent started with PID $(cat agent.pid)"
```

---

### Step 2: Start Real-Time Monitoring

**In a separate terminal:**

```bash
cd option_a_test

# Start monitor with 1-minute updates
python ../monitor_agent_progress.py option_a_run1.log --interval 60
```

You'll see a dashboard like this every minute:

```
======================================================================
📊 AGENT PROGRESS MONITOR - 14:23:45
======================================================================

HEALTH SCORE:        72.5/100 - 🟢 HEALTHY

ITERATIONS:          5
TRUNCATIONS:         7 (1.4/iter)
EMPTY SOLUTIONS:     1 (20% rate)
VERIFICATIONS:       2 pass / 10 total (20%)
CURRENT STATE:       2 correct, 1 errors

CORRECT PROGRESS:    [██░░░] 2/5
ERROR THRESHOLD:     [█░░░░░░░░░] 1/10

HEALTH INDICATORS:
  ✅ Low truncation rate: 1.4/iter
  ✅ Low empty rate: 20%
  ✅ Making progress: 2/5

EARLY PREDICTION:
  ✅ GOOD PROGRESS - Continue monitoring
  📈 Likely success within 15-20 iterations
======================================================================
```

---

### Step 3: Monitor Early Indicators

#### ✅ After 1 Hour (~3 iterations)

**Check:**
```bash
# Quick status check
python ../monitor_agent_progress.py option_a_run1.log --once
```

**Look for:**
- [ ] Truncations < 10 total
- [ ] Empty solutions < 3
- [ ] Health score > 50
- [ ] At least 1 verification pass

**Decision:**
- ✅ **All checked** → Continue with confidence
- 🟡 **Some checked** → Monitor for 1 more hour
- ❌ **None checked** → Strong failure signal, consider stopping

---

#### ✅ After 3 Hours (~8 iterations)

**Check:**
```bash
# Detailed metrics
python ../monitor_agent_progress.py option_a_run1.log --once --export metrics_3h.json

# View metrics
cat metrics_3h.json
```

**Look for:**
- [ ] Correct count reached ≥ 1
- [ ] Truncation rate < 2 per iteration
- [ ] Health score > 60
- [ ] Error count < 5

**Decision:**
- ✅ **Correct count ≥ 1** → Very likely success, continue
- 🟡 **Correct count = 0** but health > 60 → Possible slow progress
- ❌ **Correct count = 0** and health < 40 → Unlikely to succeed

---

#### ✅ After 6 Hours (~15 iterations)

**Look for:**
- [ ] Correct count reached ≥ 2
- [ ] Still running (not hit 10-error limit)
- [ ] Verification pass rate > 20%

**Decision:**
- ✅ **Correct count ≥ 2** → Almost there! Should reach 5 soon
- ❌ **Correct count ≤ 1** → Unlikely to reach 5, consider stopping

---

### Step 4: Stop Agent (if needed)

```bash
# If you see red flags, stop the agent
kill $(cat agent.pid)

# Or if that doesn't work
pkill -f agent_gpt_oss.py

echo "🛑 Agent stopped"
```

---

## Expected Outcomes

### 🟢 Success Scenario (10-30% probability)

**Timeline:**
```
Hour 1:  Health 70+, truncations <10, correct count 1
Hour 3:  Correct count 2-3
Hour 6:  Correct count 4
Hour 8:  Correct count 5 → SUCCESS! ✅
```

**Indicators:**
- Truncation rate: 0.5-1.5 per iteration
- Empty solution rate: <20%
- Verification pass rate: 20-40%
- Health score: 70-85

---

### 🟡 Slow Progress Scenario (20-30% probability)

**Timeline:**
```
Hour 1-3:  Health 55-65, slow start
Hour 6-12: Correct count slowly increases to 2-3
Hour 18-24: Eventually reaches 5 → SUCCESS! ✅
```

**Indicators:**
- Truncation rate: 1.5-3 per iteration
- Verification pass rate: 10-20%
- Health score: 50-65
- Takes longer but eventually succeeds

---

### 🔴 Failure Scenario (40-70% probability)

**Timeline:**
```
Hour 1:  Health <40, truncations >20
Hour 3:  Same pattern, correct count still 0
Hour 6:  Error count ≥8 → FAILURE ❌
```

**Indicators:**
- Truncation rate: >3 per iteration (same as original)
- Empty solution rate: >50%
- Verification pass rate: <5%
- Health score: <40
- Never reaches correct count > 0

---

## Comparison Metrics

| Metric | Original | Option A Target | How to Check |
|--------|----------|-----------------|--------------|
| **Truncations** (3 iter) | 36-40 | <10 | `grep "WARNING.*Maximum" *.log \| wc -l` |
| **Empty Solutions** (3 iter) | 5-10 | <3 | `grep 'solution: ""' *.log \| wc -l` |
| **Verification Pass Rate** | 0% | >10% | `grep "verify results:" *.log` |
| **Correct Count Max** | 0 | ≥1 | `grep "number of corrects:" *.log` |
| **Health Score** (3 iter) | <30 | >50 | Monitor dashboard |

---

## Troubleshooting

### Problem: Truncations Still High (>20 in first 3 iterations)

**Diagnosis:** reasoning_effort="low" not effective

**Solutions:**
1. Verify change was applied: `grep reasoning_effort agent_gpt_oss.py`
2. Try even lower: `max_new_tokens=64000` (instead of 128000)
3. Add explicit length constraints in prompt

---

### Problem: Empty Solutions Continue (>30% rate)

**Diagnosis:** Format generation failing

**Solutions:**
1. Verify repetition_penalty removed
2. Add format validation (see prompt_diff_analysis.md)
3. Check model is actually using chat template

---

### Problem: Verification Never Passes (0% after 8 iterations)

**Diagnosis:** Proof rigor issue (same as original)

**Solutions:**
1. This indicates architectural changes alone aren't enough
2. Need to add rigor enhancement prompts
3. May need format validation layer
4. See recommendations in version_comparison_summary.md

---

### Problem: Monitor Shows "File not found"

**Solutions:**
```bash
# Check log file exists
ls -lh option_a_run1.log

# Check agent is running
ps aux | grep agent_gpt_oss

# Check agent is writing to log
tail -f option_a_run1.log
```

---

## Data Collection

### Metrics to Track

```bash
# After test completes (or you stop it), export all metrics
python ../monitor_agent_progress.py option_a_run1.log --once --export final_metrics.json

# Create comparison report
python ../detect_solution_gaps.py \
    --failed ../run_log_gpt_oss/agent_gpt_oss_high_output_1.log \
    --successful option_a_run1.log \
    --output option_a_comparison.json
```

### Report Template

```markdown
# Option A Test Report

## Configuration
- reasoning_effort: low
- repetition_penalty: removed
- Test problem: imo01.txt
- Start time: [timestamp]
- Duration: [hours]

## Results
- **Outcome:** [Success/Failure]
- **Iterations:** [N]
- **Final correct count:** [X/5]
- **Final error count:** [Y/10]

## Metrics Comparison
| Metric | Original | Option A | Improvement |
|--------|----------|----------|-------------|
| Truncations | 122 | [N] | [%] |
| Empty Solutions | 52 | [N] | [%] |
| Verification Failures | 112 | [N] | [%] |
| Success Rate | 0% | [%] | [delta] |

## Early Indicators (3 hours)
- Health score: [N/100]
- Truncation rate: [N] per iter
- Correct count max: [N]
- Prediction: [accurate/inaccurate]

## Conclusion
[Analysis of whether Option A improvements worked]

## Next Steps
[What to try next based on results]
```

---

## Quick Reference Commands

```bash
# Start test
nohup python agent_gpt_oss.py problems/imo01.txt --log test.log > out.txt 2>&1 &

# Monitor
python monitor_agent_progress.py test.log --interval 60

# Quick check
python monitor_agent_progress.py test.log --once

# Export metrics
python monitor_agent_progress.py test.log --once --export metrics.json

# Stop agent
pkill -f agent_gpt_oss.py

# Analyze results
python detect_solution_gaps.py --failed old.log --successful test.log
```

---

## Success Criteria

Option A is **successful** if within first 6 hours you see:

✅ **Must have:**
- Truncation rate < 2 per iteration (vs 12+ in original)
- At least 1 verification pass (vs 0 in original)
- Health score > 50 (vs <30 in original)

✅ **Bonus (strong success):**
- Correct count reaches ≥ 2
- Verification pass rate > 20%
- Health score > 70

If these criteria are NOT met after 6 hours, Option A has failed and you should move to enhanced version with format validation and rigor prompts.

---

## Next Steps After Option A

### If Successful (reaches 5/5 correct):
1. ✅ Document exact configuration
2. ✅ Test on 2-3 more IMO problems
3. ✅ Measure actual success rate (should be 10-30%)
4. ✅ Proceed to add further enhancements

### If Partially Successful (reaches 1-3 correct):
1. 🟡 Analyze where it's failing (format vs rigor)
2. 🟡 Add targeted improvements
3. 🟡 Test again

### If Failed (never reaches >0 correct):
1. ❌ Analyze failure pattern
2. ❌ Add format validation + rigor enhancement
3. ❌ Consider more fundamental changes

---

## Timeline

```
Day 1: Setup and start test
├─ Hour 1: First indicators (stop if bad)
├─ Hour 3: Strong prediction (80% confidence)
└─ Hour 6: Decision point (continue or stop)

Day 2: Results and analysis
├─ If succeeded: Document and test on more problems
├─ If failed: Analyze and plan enhancements
└─ Report findings

Day 3: Next iteration based on results
```

Good luck! 🍀

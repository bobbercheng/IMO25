# IMO Agent Testing Guide - Option A

## 🎯 Quick Start (3 Commands)

```bash
# 1. Start agent (with monitoring-friendly log)
python agent_gpt_oss.py problems/imo01.txt --log test_run.log &

# 2. Monitor in real-time (separate terminal)
python monitor_agent_progress.py test_run.log --interval 60

# 3. That's it! Watch the dashboard for early indicators
```

**You'll know if it's working within 1-3 hours**, not 24 hours!

---

## 📊 What You'll See

Every 60 seconds, the monitor shows:

```
======================================================================
📊 AGENT PROGRESS MONITOR - 14:23:45
======================================================================

HEALTH SCORE:        72.5/100 - 🟢 HEALTHY

ITERATIONS:          5
TRUNCATIONS:         7 (1.4/iter)        ← Should be <2, not 12+
EMPTY SOLUTIONS:     1 (20% rate)        ← Should be <30%, not >50%
VERIFICATIONS:       2 pass / 10 total   ← Should be >10%, not 0%
CURRENT STATE:       2 correct, 1 errors ← KEY: Should reach ≥1

CORRECT PROGRESS:    [██░░░] 2/5        ← Needs to reach 5
ERROR THRESHOLD:     [█░░░░░░░░░] 1/10  ← Can't hit 10

EARLY PREDICTION:
  ✅ GOOD PROGRESS - Trends are positive
  📈 Likely success within 15-20 iterations
  ✅ Truncation rate 88% better than original
======================================================================
```

---

## 🚦 Decision Points

### After 1 Hour (~3 iterations)

**🟢 CONTINUE if:**
- Truncations < 10 (not 36 like original)
- Empty solutions < 3 (not 10)
- Health score > 50 (not <30)

**🔴 STOP if:**
- Truncations > 30 (same problem)
- Empty solutions > 10
- Health score < 30

---

### After 3 Hours (~8 iterations)

**🟢 CONTINUE if:**
- Correct count reached ≥ 1 (KEY INDICATOR!)
- Truncation rate < 2 per iteration
- Health score > 60

**🔴 STOP if:**
- Correct count still 0
- Error count ≥ 7
- Health score < 40

---

### After 6 Hours (~15 iterations)

**🟢 KEEP RUNNING if:**
- Correct count ≥ 2 (almost there!)

**🔴 STOP if:**
- Correct count still ≤ 1 (unlikely to reach 5)
- Error count ≥ 8 (about to fail)

---

## 📁 Files You Need

All tools are in this directory:

1. **monitor_agent_progress.py** - Real-time monitoring dashboard
2. **EARLY_SUCCESS_INDICATORS.md** - Detailed decision guide
3. **OPTION_A_SETUP.md** - Full setup instructions
4. **detect_solution_gaps.py** - Post-run analysis tool

---

## 🔧 Required Changes to agent_gpt_oss.py

Before testing, make these 2 changes:

### Change 1: reasoning_effort
```python
# OLD:
reasoning_effort="high"

# NEW:
reasoning_effort="low"
```

### Change 2: Remove repetition_penalty
```python
# OLD:
output = model.generate(
    **inputs,
    max_new_tokens=128000,
    temperature=0.1,
    repetition_penalty=1.05,  # DELETE THIS LINE
    top_p=1.0
)

# NEW:
output = model.generate(
    **inputs,
    max_new_tokens=128000,
    temperature=0.1,
    top_p=1.0
)
```

**Or use the patch:**
```bash
patch agent_gpt_oss.py < remove_repetition_penalty.patch
```

---

## 📈 Expected Results

### Original Version (Failed):
- Truncations: 122 in 10 runs
- Empty solutions: 52
- Verification failures: 112
- Success rate: **0%**
- Runtime: 23 hours → failure

### Option A (Predicted):
- Truncations: 20-50 (60-80% better)
- Empty solutions: 10-30 (40-60% better)
- Verification failures: 30-70 (40-70% better)
- Success rate: **10-30%**
- Runtime: 4-12 hours → potential success

---

## 🎓 What Each Indicator Means

### Truncations
- **What:** Model output cut off mid-generation
- **Original:** 122 (12 per iteration) = content overflow
- **Target:** <10 total in first 3 iterations
- **Why it matters:** High truncations mean same problem as original

### Empty Solutions
- **What:** Generated solution is literally empty string ""
- **Original:** 52 instances = format generation failure
- **Target:** <20% rate
- **Why it matters:** Can't verify an empty solution

### Verification Pass Rate
- **What:** % of solutions that pass rigorous IMO verification
- **Original:** 0% (never passed)
- **Target:** >10% (some passing)
- **Why it matters:** Need passes to accumulate correct count

### Correct Count
- **What:** Consecutive verification passes (need 5 to succeed)
- **Original:** Always 0
- **Target:** Reaches ≥1 within 8 iterations
- **Why it matters:** **MOST IMPORTANT** - shows real progress

### Health Score
- **What:** Composite score of all indicators (0-100)
- **Original:** <30 (failing)
- **Target:** >60 (healthy)
- **Why it matters:** Overall system health predictor

---

## 🛠️ Troubleshooting

### Monitor says "File not found"
```bash
# Check log exists
ls -lh test_run.log

# Check agent is running
ps aux | grep agent_gpt_oss

# Check log is being written
tail -f test_run.log
```

### Agent seems stuck
```bash
# Check if it's actually running
tail -f test_run.log

# Check for errors
grep -i error test_run.log

# Check last activity
tail -20 test_run.log
```

### Want to stop agent
```bash
# Find PID
ps aux | grep agent_gpt_oss

# Kill it
kill <PID>

# Or kill all
pkill -f agent_gpt_oss.py
```

---

## 📊 After Test Completes

### Export Final Metrics
```bash
python monitor_agent_progress.py test_run.log --once --export final_metrics.json
```

### Compare to Original
```bash
python detect_solution_gaps.py \
    --failed run_log_gpt_oss/agent_gpt_oss_high_output_1.log \
    --successful test_run.log \
    --output comparison.json
```

### Generate Report
See `OPTION_A_SETUP.md` for report template.

---

## ✅ Success Criteria

Option A **WORKS** if you see within 6 hours:

- ✅ Truncation rate < 2 per iteration (vs 12+)
- ✅ Correct count reaches ≥ 1 (vs always 0)
- ✅ Health score > 50 (vs <30)
- ✅ Verification pass rate > 10% (vs 0%)

Option A **SUCCEEDS** if:

- 🎉 Correct count reaches 5/5
- 🎉 Solution is verified as correct
- 🎉 Completes before hitting 10-error limit

---

## 📚 Documentation

- **EARLY_SUCCESS_INDICATORS.md** - Comprehensive guide to all indicators and decision rules
- **OPTION_A_SETUP.md** - Detailed setup and execution guide
- **prompt_diff_analysis.md** - Technical analysis of changes
- **version_comparison_summary.md** - Quick reference comparison
- **SOLUTION_GAPS_ANALYSIS.md** - Original failure analysis

---

## 🎯 Bottom Line

**Before:** Wait 24 hours to discover failure ❌

**Now:** Know within 1-3 hours if it's working ✅

**How:** Real-time monitoring dashboard with early prediction

**Success Probability:** 10-30% (vs 0% original)

**Time Savings:** Stop bad runs at 3 hours instead of 23 hours

---

## Quick Commands Cheat Sheet

```bash
# Start agent
python agent_gpt_oss.py problems/imo01.txt --log test.log &

# Monitor continuously
python monitor_agent_progress.py test.log --interval 60

# Quick check
python monitor_agent_progress.py test.log --once

# Export metrics
python monitor_agent_progress.py test.log --once --export metrics.json

# Stop agent
pkill -f agent_gpt_oss.py

# Post-analysis
python detect_solution_gaps.py --failed old.log --successful test.log
```

---

## Questions?

See the detailed guides:
- **Quick start:** This file
- **Decision making:** EARLY_SUCCESS_INDICATORS.md
- **Full setup:** OPTION_A_SETUP.md
- **Technical details:** prompt_diff_analysis.md

Good luck! 🚀

# Tier 1 Features: Quick Fix Reference

**Last Updated:** 2025-11-18
**Priority:** CRITICAL (Apply before production use)

---

## 🔴 Critical Fix #1: Stuck Detection Logic Bug

**Location:** `/home/user/IMO25/code/agent_gpt_oss.py:973`

**Current (WRONG):**
```python
errors_not_decreasing = all(recent_errors[i] >= recent_errors[0] for i in range(len(recent_errors)))
```

**Fixed (CORRECT):**
```python
errors_not_decreasing = all(recent_errors[i] >= recent_errors[i-1] for i in range(1, len(recent_errors)))
```

**Why This Matters:**
```python
# Example: Oscillating errors [3, 5, 4]
# Current: all([3>=3, 5>=3, 4>=3]) = True → Declares STUCK (false positive)
# Fixed:   all([5>=3, 4>=5]) = False → Not stuck (correct)
```

**Impact:**
- False positives: Stops too early on oscillating patterns
- May waste potential solutions that need more exploration

---

## 🔴 Critical Fix #2: Add Auto-Escalation

**Location:** `/home/user/IMO25/code/agent_gpt_oss.py:1270-1277`

**Current (gives up immediately):**
```python
if detect_stuck_pattern(correct_history, error_history, i, threshold=3, verbose=True):
    print(f">>>>>>> [STUCK DETECTION] Stopping due to stuck pattern")
    print(f">>>>>>> [STUCK DETECTION] Recommendation: Try different reasoning level or approach")
    if memory_file:
        save_memory(memory_file, problem_statement, other_prompts, i, 30, solution, verify,
                   sol_reasoning, self_imp_reasoning, ver_reasoning)
    return None
```

**Fixed (escalates before giving up):**
```python
# Add at top of agent() function to track escalations
escalation_count = 0
escalated_to_medium = False
escalated_to_high = False

# ... later in the loop (line 1270):
if detect_stuck_pattern(correct_history, error_history, i, threshold=3, verbose=True):
    # Try escalating reasoning before giving up
    if sol_reasoning == "low" and not escalated_to_medium:
        print(f">>>>>>> [STUCK DETECTION] Escalating from low to medium reasoning...")
        sol_reasoning = "medium"
        escalated_to_medium = True
        escalation_count += 1
        # Reset stuck detection counters to give it a fresh chance
        correct_history = []
        error_history = []
        print(f">>>>>>> [STUCK DETECTION] Resetting history, trying again with medium reasoning")
        continue  # Don't stop, try again

    elif sol_reasoning == "medium" and not escalated_to_high:
        print(f">>>>>>> [STUCK DETECTION] Escalating from medium to high reasoning...")
        sol_reasoning = "high"
        escalated_to_high = True
        escalation_count += 1
        # Reset stuck detection counters
        correct_history = []
        error_history = []
        print(f">>>>>>> [STUCK DETECTION] Resetting history, trying again with high reasoning")
        continue  # Don't stop, try again

    else:
        print(f">>>>>>> [STUCK DETECTION] Stopping due to stuck pattern")
        print(f">>>>>>> [STUCK DETECTION] Failed even with high reasoning (escalated {escalation_count} times)")
        if memory_file:
            save_memory(memory_file, problem_statement, other_prompts, i, 30, solution, verify,
                       sol_reasoning, self_imp_reasoning, ver_reasoning)
        return None
```

**Why This Matters:**
- Currently wastes solutions that could be found with higher reasoning
- Test 1 might have succeeded if escalated from low to high
- Aligns with documentation claim of "escalate reasoning"

---

## 🔴 Critical Fix #3: Save Feature State in Memory

**Location:** `/home/user/IMO25/code/agent_gpt_oss.py:693-714`

**Step 1: Update save_memory signature:**
```python
def save_memory(memory_file, problem_statement, other_prompts, current_iteration,
                max_runs, solution, verify, solution_reasoning=None,
                self_improvement_reasoning=None, verification_reasoning=None,
                score_history=None, correct_history=None, error_history=None,
                previous_solution=None, escalation_count=0):
```

**Step 2: Add to memory dict (after line 704):**
```python
    memory = {
        "problem_statement": problem_statement,
        "other_prompts": other_prompts,
        "current_iteration": current_iteration,
        "max_runs": max_runs,
        "solution": solution,
        "verify": verify,
        "solution_reasoning": solution_reasoning or SOLUTION_REASONING_EFFORT,
        "self_improvement_reasoning": self_improvement_reasoning or SELF_IMPROVEMENT_REASONING_EFFORT,
        "verification_reasoning": verification_reasoning or VERIFICATION_REASONING_EFFORT,
        "timestamp": __import__('datetime').datetime.now().isoformat(),
        # NEW: Feature state
        "score_history": score_history or [],
        "correct_history": correct_history or [],
        "error_history": error_history or [],
        "previous_solution": previous_solution,
        "escalation_count": escalation_count
    }
```

**Step 3: Update load_memory (after line 742):**
```python
def load_memory(memory_file):
    try:
        with open(memory_file, 'r', encoding='utf-8') as f:
            memory = json.load(f)
        print(f"Memory loaded from {memory_file}")

        # Log loaded reasoning settings
        if 'solution_reasoning' in memory:
            print(f"Loaded solution reasoning effort: {memory['solution_reasoning']}")
        if 'verification_reasoning' in memory:
            print(f"Loaded verification reasoning effort: {memory['verification_reasoning']}")

        # NEW: Log loaded feature state
        if 'score_history' in memory and memory['score_history']:
            print(f"Loaded score history: {len(memory['score_history'])} iterations")
            print(f"  Last score: {memory['score_history'][-1]:.2f}")
        if 'escalation_count' in memory:
            print(f"Loaded escalation count: {memory['escalation_count']}")

        return memory
    except Exception as e:
        print(f"Error loading memory from {memory_file}: {e}")
        return None
```

**Step 4: Update agent() to restore feature state (around line 1023):**
```python
if resume_from_memory and memory_file:
    memory = load_memory(memory_file)
    if memory:
        problem_statement = memory.get("problem_statement", problem_statement)
        other_prompts = memory.get("other_prompts", other_prompts)
        current_iteration = memory.get("current_iteration", 0)
        solution = memory.get("solution", None)
        verify = memory.get("verify", None)

        # Restore reasoning settings
        if solution_reasoning is None and 'solution_reasoning' in memory:
            sol_reasoning = memory['solution_reasoning']
        # ... existing code ...

        # NEW: Restore feature state
        score_history = memory.get("score_history", [])
        correct_history = memory.get("correct_history", [])
        error_history = memory.get("error_history", [])
        previous_solution = memory.get("previous_solution", None)
        escalation_count = memory.get("escalation_count", 0)
        escalated_to_medium = (sol_reasoning == "medium" or sol_reasoning == "high")
        escalated_to_high = (sol_reasoning == "high")

        print(f"Restored feature state: {len(score_history)} scores, {escalation_count} escalations")
```

**Step 5: Update all save_memory calls to pass feature state:**
```python
# Example: Line 1275, 1284, 1296, etc.
save_memory(memory_file, problem_statement, other_prompts, i, 30, solution, verify,
           sol_reasoning, self_imp_reasoning, ver_reasoning,
           score_history, correct_history, error_history, previous_solution, escalation_count)
```

**Why This Matters:**
- Resume from memory currently loses all progress tracking
- Stuck detection starts from scratch (may re-detect stuck unnecessarily)
- Score tracking can't show historical trends

---

## 🟡 Important Fix #4: Remove Length Penalty

**Location:** `/home/user/IMO25/code/agent_gpt_oss.py:838-839`

**Current:**
```python
        # Reward shorter bug reports (fewer issues)
        score -= len(verify) / 100
```

**Fixed (just delete these lines):**
```python
        # (removed length penalty - detailed feedback is helpful)
```

**Why This Matters:**
- Penalizes detailed helpful verification feedback
- Rewards terse unhelpful feedback
- Reduces correlation between score and solution quality

---

## Testing After Fixes

### Test 1: Verify Stuck Detection Fix
```bash
python -c "
from code.agent_gpt_oss import detect_stuck_pattern

# Test oscillating pattern
correct_history = [0, 0, 0]
error_history = [3, 5, 4]  # Oscillating

stuck = detect_stuck_pattern(correct_history, error_history, 3, threshold=3, verbose=False)
print(f'Oscillating [3,5,4]: stuck={stuck} (should be False after fix)')

# Test actually stuck pattern
error_history = [3, 4, 5]  # Increasing
stuck = detect_stuck_pattern(correct_history, error_history, 3, threshold=3, verbose=False)
print(f'Increasing [3,4,5]: stuck={stuck} (should be True)')
"
```

**Expected Output After Fix:**
```
Oscillating [3,5,4]: stuck=False (should be False after fix)
Increasing [3,4,5]: stuck=True (should be True)
```

### Test 2: Verify Auto-Escalation
```bash
# Run agent that should get stuck with low reasoning
python code/agent_gpt_oss.py problems/imo01.txt \
  --solution-reasoning low \
  --log test_escalation.log

# Check for escalation messages
grep "Escalating to medium\|Escalating to high" test_escalation.log

# Should see output like:
# [STUCK DETECTION] Escalating from low to medium reasoning...
# (possibly later:)
# [STUCK DETECTION] Escalating from medium to high reasoning...
```

### Test 3: Verify Memory Persistence
```bash
# Start agent, let it run 3 iterations
timeout 60 python code/agent_gpt_oss.py problems/imo01.txt \
  --memory-file test_memory.json \
  --log test_mem1.log

# Check memory file contains feature state
python -c "
import json
with open('test_memory.json') as f:
    mem = json.load(f)
print('score_history:', mem.get('score_history', 'MISSING'))
print('correct_history:', mem.get('correct_history', 'MISSING'))
print('error_history:', mem.get('error_history', 'MISSING'))
print('escalation_count:', mem.get('escalation_count', 'MISSING'))
"

# Resume from memory
python code/agent_gpt_oss.py problems/imo01.txt \
  --resume-from-memory \
  --memory-file test_memory.json \
  --log test_mem2.log

# Check that it restored state
grep "Restored feature state" test_mem2.log
```

### Test 4: Run Full Test Suite
```bash
# Should still pass after fixes
python test_tier1_features.py

# Expected: ALL TESTS PASSED ✓
```

---

## Verification Checklist

After applying fixes, verify:

- [ ] Stuck detection logic uses `recent_errors[i-1]` comparison
- [ ] Auto-escalation tries medium before high before stopping
- [ ] `save_memory()` signature includes new parameters
- [ ] `load_memory()` restores feature state
- [ ] All `save_memory()` calls pass feature state
- [ ] Length penalty line removed
- [ ] Test suite still passes
- [ ] Manual test shows escalation working
- [ ] Memory persistence test passes

---

## Estimated Time

- Fix #1 (Stuck detection): **5 minutes**
- Fix #2 (Auto-escalation): **15 minutes**
- Fix #3 (Memory persistence): **20 minutes**
- Fix #4 (Length penalty): **2 minutes**
- Testing: **20 minutes**

**Total: ~60 minutes** of focused work

---

## Files to Modify

1. `/home/user/IMO25/code/agent_gpt_oss.py` (all 4 fixes)
2. No test file changes needed (tests should still pass)

---

## Backup Before Applying

```bash
cd /home/user/IMO25
cp code/agent_gpt_oss.py code/agent_gpt_oss.py.backup_$(date +%Y%m%d_%H%M%S)
```

---

## After Fixes: Re-run Tests

```bash
# Quick smoke test
python test_tier1_features.py

# Integration test on actual problem
python code/agent_gpt_oss.py problems/imo01.txt \
  --solution-reasoning low \
  --log test_post_fix.log

# Check that features work correctly
grep "STUCK\|SCORE\|ANSWER" test_post_fix.log | head -20
```

---

## Questions?

See full analysis in:
- **TIER1_CRITICAL_REVIEW.md** - Detailed technical review
- **TIER1_REVIEW_SUMMARY.md** - Executive summary

**Status:** Ready to apply (estimated 60 min)

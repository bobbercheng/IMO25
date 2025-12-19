# Phase 0 Diagnostic Tests - Quick Start Guide

## Running Diagnostics in Parallel

The diagnostic script now supports **parallel execution** to reduce wall-clock time from 6-10 hours to 2-4 hours.

### Quick Start (Baseline Only)

Run the control tests first (no code changes needed):

```bash
./run_diagnostic_tests.sh
```

This will:
- ✅ Run Test 1 Control (N=2) in parallel
- ⏭️ Skip treatment variants (need code modifications)
- 📊 Show quick analysis of baseline results

**Expected output**: Baseline resume count average (e.g., "10.5 resumes")

---

### Running All Tests (After Code Modifications)

Once you've modified the code for all variants:

```bash
TEST1_TREATMENT_READY=1 \
TEST2_TREATMENT_READY=1 \
TEST3_INSTRUMENTED_READY=1 \
./run_diagnostic_tests.sh
```

This will run **all 6 tests in parallel** (or up to MAX_PARALLEL limit).

---

## Code Modifications Required

### Test 1 Treatment: Empty Feedback

**File**: `code/prescriptive_feedback.py` (or wherever prescriptive feedback is generated)

**Add** environment variable check:

```python
import os

def enhance_verification_with_prescriptive_feedback(verification_result, solution_text):
    """Generate prescriptive feedback based on verification errors."""

    # Check for diagnostic mode
    feedback_mode = os.environ.get('PRESCRIPTIVE_FEEDBACK_MODE', 'full')

    if feedback_mode == 'empty':
        # Return minimal placeholder for Test 1 Treatment
        return "Error detected. Review verification details above.", {}

    # Normal full feedback generation (existing code)
    ...
```

**Enable**: `TEST1_TREATMENT_READY=1`

---

### Test 2 Treatment: Short Feedback

**File**: Same as above (`prescriptive_feedback.py`)

**Modify** the template generation:

```python
    if feedback_mode == 'short':
        # Return simplified feedback (10-15 lines)
        error_type = extract_error_type(verification_result)
        issue = extract_issue_description(verification_result)
        fix = extract_fix_instruction(verification_result)

        short_feedback = f"""
ERROR: {error_type}
ISSUE: {issue}
FIX: {fix}
"""
        return short_feedback, {}
```

**Enable**: `TEST2_TREATMENT_READY=1`

---

### Test 3: Instrumentation

**File**: `code/agent_gpt_oss.py` (around line 1259)

**Add** diagnostic logging:

```python
if not disable_prescriptive:
    from prescriptive_feedback import enhance_verification_with_prescriptive_feedback

    bug_report, metadata = enhance_verification_with_prescriptive_feedback(
        verification_result=verification,
        solution_text=solution_text
    )

    # ADD DIAGNOSTIC LOGGING HERE
    if os.environ.get('DIAGNOSTIC_LOGGING') == '1':
        print(f">>>>>>> [DIAGNOSTIC] Prescriptive feedback received: {len(bug_report)} chars")
        print(f">>>>>>> [DIAGNOSTIC] Feedback preview: {bug_report[:200]}")
```

**Later** (when creating next iteration prompt):

```python
# After creating next_iteration_prompt
if os.environ.get('DIAGNOSTIC_LOGGING') == '1':
    feedback_referenced = (
        "prescriptive" in next_iteration_prompt.lower() or
        "fix" in next_iteration_prompt.lower() or
        "repair" in next_iteration_prompt.lower()
    )
    print(f">>>>>>> [DIAGNOSTIC] Feedback referenced: {feedback_referenced}")
```

**Enable**: `TEST3_INSTRUMENTED_READY=1`

---

## Advanced Usage

### Limit Parallel Jobs

For systems with limited memory:

```bash
MAX_PARALLEL=2 ./run_diagnostic_tests.sh
```

This will run max 2 tests at a time instead of all 6.

---

### Run Specific Tests Only

```bash
# Only Test 1 Treatment
TEST1_TREATMENT_READY=1 ./run_diagnostic_tests.sh

# Only Test 2 Treatment
TEST2_TREATMENT_READY=1 ./run_diagnostic_tests.sh

# Only Tests 1 and 2
TEST1_TREATMENT_READY=1 TEST2_TREATMENT_READY=1 ./run_diagnostic_tests.sh
```

---

### Monitor Progress

In a separate terminal:

```bash
watch -n 5 'ls -lh diagnostic_results/*.log | tail -10'
```

This will show real-time log file sizes (growing = still running).

---

### Check Running Jobs

```bash
ps aux | grep agent_gpt_oss
```

---

## Expected Timeline

| Configuration | Wall-Clock Time | CPU Time |
|---------------|-----------------|----------|
| **Control only** (N=2) | 30-60 min | 1-2 hours |
| **All tests** (N=6, parallel) | 60-120 min | 6-10 hours |
| **All tests** (N=6, sequential) | 6-10 hours | 6-10 hours |

**Speedup**: 3-6× faster with parallel execution!

---

## Troubleshooting

### "No tests were run"

- ✅ Check that environment variables are set: `echo $TEST1_TREATMENT_READY`
- ✅ Verify code modifications are in place
- ✅ Run control tests first to verify baseline works

### Jobs failing

- Check individual log files: `tail -50 diagnostic_results/test1_*.log`
- Look for Python errors or API errors
- Verify problem file exists: `ls -la problems/imo01.txt`

### Out of memory

- Reduce parallel jobs: `MAX_PARALLEL=1 ./run_diagnostic_tests.sh`
- Or run tests one at a time manually

---

## After Tests Complete

Run analysis:

```bash
python analyze_diagnostic_results.py diagnostic_results/
```

This will show:
- ✅ Resume count deltas (treatment vs control)
- ✅ Statistical interpretation
- ✅ **Data-driven recommendation** on which fix to implement

---

## Files Generated

```
diagnostic_results/
├── test1_control_run1_20251219_120000.log
├── test1_control_run1_20251219_120000.json
├── test1_control_run2_20251219_120000.log
├── test1_control_run2_20251219_120000.json
├── test1_treatment_run1_20251219_120030.log
├── test1_treatment_run1_20251219_120030.json
... (total 12 files for 6 runs)
```

Each test generates:
- `.log` - Full execution log with iterations, errors, etc.
- `.json` - Memory state with solution, verification, metrics

---

## Next Steps After Diagnostics

Based on analysis results:

1. **If Test 2 shows >50% improvement**:
   - ✅ Implement Fix 2 Phase 0 (simplify feedback)
   - Duration: 4 hours

2. **If Test 3 shows <10% feedback reference rate**:
   - ✅ Implement Fix 1 Option A (add instructions)
   - Duration: 1 hour

3. **If results inconclusive**:
   - ⚠️ Gather more data (increase N=2 → N=5 per variant)
   - Or try alternative approaches

# BFS Diversity Fix - Implementation Proposal
**Date**: 2025-12-30
**Priority**: P0 (Critical - Blocks TIER 1 effectiveness)

## Problem Statement

**Current Bug**: All parallel BFS runs receive identical prompts, causing 95% convergence on the same wrong answer (4048 instead of correct 2112).

**Root Cause**: Lines 6631-6641 in `agent_gpt_oss.py`:
```python
for attempt in range(num_initial_attempts):  # attempt = 0,1,2...
    explicit_prompt = dynamic_prompts_list[attempt]  # All runs use attempt=0 first!
```

When running 20 parallel instances:
- Run 1: attempt=0 → prompts[0]
- Run 2: attempt=0 → prompts[0]
- ...
- Run 20: attempt=0 → prompts[0]

**Result**: All 20 runs start with identical prompt, converge on same approach.

---

## Proposed Solution

### Architecture: Run-Specific Prompt Rotation

```
Prompt Pool (20 prompts):
  [P0, P1, P2, ..., P19]

Run 1 (BFS_RUN_ID=1): Uses [P1, P2, P3]  (start at index 1)
Run 2 (BFS_RUN_ID=2): Uses [P2, P3, P4]  (start at index 2)
Run 3 (BFS_RUN_ID=3): Uses [P3, P4, P5]  (start at index 3)
...
Run 20 (BFS_RUN_ID=20): Uses [P0, P1, P2] (wraps around)

Result: Each run gets DIFFERENT starting prompt!
```

---

## Code Changes

### Change 1: `agent_gpt_oss.py` - Add Run ID Support

**Location**: Lines 6631-6642

**Before**:
```python
for attempt in range(num_initial_attempts):
    print(f">>>>>>> BFS: Initial attempt {attempt+1}/{num_initial_attempts}...")

    # Add diversity to prompt
    diverse_prompts = other_prompts.copy()

    # Use dynamic BFS prompts if available, otherwise fall back to generic diversity
    if use_dynamic and attempt < len(dynamic_prompts_list):
        explicit_prompt = dynamic_prompts_list[attempt]  # ⚠️ BUG HERE!
        diverse_prompts.append(f"\n{explicit_prompt}")
        print(f">>>>>>> BFS: Explicit prompt: {explicit_prompt[:100]}...")
```

**After**:
```python
# BFS Diversity Fix (2025-12-30): Use run-specific prompt rotation
# Each parallel run gets different prompts to ensure exploration diversity
run_id = int(os.getenv('BFS_RUN_ID', '0'))  # 0-indexed run identifier
if run_id > 0:
    print(f">>>>>>> BFS: Run ID = {run_id} (enables diverse prompt selection)")

for attempt in range(num_initial_attempts):
    print(f">>>>>>> BFS: Initial attempt {attempt+1}/{num_initial_attempts}...")

    # Add diversity to prompt
    diverse_prompts = other_prompts.copy()

    # Use dynamic BFS prompts if available, otherwise fall back to generic diversity
    if use_dynamic and attempt < len(dynamic_prompts_list):
        # Rotate prompts based on run_id to ensure diversity across parallel runs
        # Formula: (run_id * num_attempts + attempt) % total_prompts
        # Example: Run 1 with 3 attempts uses prompts [1,2,3], Run 2 uses [2,3,4], etc.
        prompt_idx = (run_id * num_initial_attempts + attempt) % len(dynamic_prompts_list)
        explicit_prompt = dynamic_prompts_list[prompt_idx]
        diverse_prompts.append(f"\n{explicit_prompt}")
        print(f">>>>>>> BFS: Prompt [{prompt_idx}/{len(dynamic_prompts_list)}]: {explicit_prompt[:100]}...")
```

### Change 2: `run_bfs_baseline.sh` - Pass Run ID

**Location**: Lines 195-203 (in `run_bfs_async` function)

**Before**:
```bash
if python code/agent_gpt_oss.py "$PROBLEM" \
    --log "$log_file" \
    --memory "$json_file" \
    --num-initial-attempts $NUM_INITIAL_ATTEMPTS \
    --max_runs $MAX_RUNS \
    --solution-reasoning "$SOLUTION_REASONING" \
    --verification-reasoning "$VERIFICATION_REASONING" \
    --self-improvement-reasoning "$SELF_IMPROVEMENT_REASONING" \
    2>&1 | tee -a "$progress_file"; then
```

**After**:
```bash
# BFS Diversity Fix (2025-12-30): Pass run number as environment variable
# This enables run-specific prompt selection for true diversity
if BFS_RUN_ID=$run_num python code/agent_gpt_oss.py "$PROBLEM" \
    --log "$log_file" \
    --memory "$json_file" \
    --num-initial-attempts $NUM_INITIAL_ATTEMPTS \
    --max_runs $MAX_RUNS \
    --solution-reasoning "$SOLUTION_REASONING" \
    --verification-reasoning "$VERIFICATION_REASONING" \
    --self-improvement-reasoning "$SELF_IMPROVEMENT_REASONING" \
    2>&1 | tee -a "$progress_file"; then
```

---

## Expected Behavior

### Before Fix (N=20, NUM_INITIAL_ATTEMPTS=3)

| Run | Attempt 1 | Attempt 2 | Attempt 3 | Result |
|-----|-----------|-----------|-----------|--------|
| 1-20 | Prompt 0 | Prompt 1 | Prompt 2 | **All identical!** |

**Diversity**: 0% (monoculture)

### After Fix (N=20, NUM_INITIAL_ATTEMPTS=3)

| Run | Attempt 1 | Attempt 2 | Attempt 3 |
|-----|-----------|-----------|-----------|
| 1 | Prompt 3 | Prompt 4 | Prompt 5 |
| 2 | Prompt 6 | Prompt 7 | Prompt 8 |
| 3 | Prompt 9 | Prompt 10 | Prompt 11 |
| ... | ... | ... | ... |
| 7 | Prompt 0 | Prompt 1 | Prompt 2 |
| ... | ... | ... | ... |
| 20 | Prompt 18 | Prompt 19 | Prompt 0 |

**Diversity**: 100% (all runs get different starting prompts)

---

## Validation Plan

### Test 1: Small-Scale Diversity Check (N=3)

```bash
# Run 3 parallel instances with diversity fix
GPT_OSS_SOLUTION_REASONING=high \
NUM_INITIAL_ATTEMPTS=3 \
MAX_PARALLEL=3 \
N_RUNS=3 \
./run_bfs_baseline.sh problems/imo06.txt test_diversity_n3

# Expected: 3 different approaches (not all 4048)
# Success criterion: At least 2 unique answers
```

### Test 2: Verify Prompt Assignment

Check logs for prompt distribution:
```bash
# Extract prompt indices from logs
for i in {1..3}; do
  echo "Run $i:"
  grep "BFS: Prompt" test_diversity_n3/bfs_run${i}*.log | head -3
done

# Expected output:
# Run 1: Prompt [3/20], Prompt [4/20], Prompt [5/20]
# Run 2: Prompt [6/20], Prompt [7/20], Prompt [8/20]
# Run 3: Prompt [9/20], Prompt [10/20], Prompt [11/20]
```

### Test 3: Answer Diversity Validation

```bash
# Extract unique answers
grep -h "boxed{" test_diversity_n3/*.log | sort -u

# Expected: 2-3 unique answers (not all 4048)
```

---

## Rollback Plan

If fix causes issues:

```bash
# Revert agent_gpt_oss.py
git checkout HEAD -- code/agent_gpt_oss.py

# Revert run_bfs_baseline.sh
git checkout HEAD -- run_bfs_baseline.sh
```

---

## Success Criteria

1. **Prompt diversity**: Each run gets different starting prompt ✓
2. **Answer diversity**: N=20 produces 5+ unique answers (vs current 2)
3. **No regressions**: Existing single-run behavior unchanged
4. **Correct answer rate**: At least 15% of runs find 2112 (vs current 0%)

---

## Timeline

- **Implementation**: 15 minutes (2 file changes)
- **Testing**: 30 minutes (N=3 validation run)
- **Deployment**: Immediate (commit + push)
- **Validation**: 2-3 hours (re-run N=20 test)

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Prompt index out of bounds | Low | High | Add modulo wraparound |
| BFS_RUN_ID not set | Medium | Low | Default to 0 (backward compatible) |
| Regression on single runs | Low | Medium | Test with BFS_RUN_ID=0 |

---

## Notes

- **Backward compatible**: If `BFS_RUN_ID` not set, defaults to 0 (current behavior)
- **No API changes**: Uses environment variable (cleaner than CLI args)
- **Minimal code change**: 3 lines in Python, 1 line in Bash
- **Immediate benefit**: Unlocks TIER 1 effectiveness by providing diverse candidates

---

**Ready to implement?** ✅

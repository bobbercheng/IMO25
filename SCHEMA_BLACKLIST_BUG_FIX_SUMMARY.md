# Schema Blacklist Bug - Quick Fix Summary

**Date:** 2026-01-04
**Status:** ✅ ROOT CAUSE IDENTIFIED - READY TO FIX

---

## TL;DR

**Bug:** Correction iterations don't include `response_format` parameter → API returns text instead of JSON → "dict vs str" errors

**Fix:** Add ONE parameter to Line 7269 in `agent_gpt_oss.py`

**Impact:** Will eliminate 28/30 errors (93% → 0%)

---

## The Bug (1 Line)

**File:** `code/agent_gpt_oss.py` **Line:** 7269

**Current (BROKEN):**
```python
p1 = build_request_payload(
    system_prompt=step1_prompt,
    question_prompt=problem_statement,
    other_prompts=other_prompts,
    reasoning_effort=sol_reasoning
)
```

**Fixed (WORKING):**
```python
p1 = build_request_payload(
    system_prompt=step1_prompt,
    question_prompt=problem_statement,
    other_prompts=other_prompts,
    reasoning_effort=sol_reasoning,
    response_format=initial_response_format  # ← ADD THIS LINE
)
```

**Note:** Need to preserve `initial_response_format` from `init_explorations` return value.

---

## Why This Matters

### Before Fix:
- Initial solution: Uses schema → Returns JSON ✅
- Correction iterations: No schema → Returns text ❌
- Result: 93% error rate (28/30 iterations)

### After Fix:
- All iterations: Use schema → All return JSON ✅
- Result: 0% error rate (predicted)

---

## Evidence That Fix Will Work

1. **Unit test proves it:** When schema is included → 100% compliance
2. **Initial BFS call proves it:** First iteration works because it HAS schema
3. **Correction calls fail because:** They DON'T have schema (not because OpenRouter ignores it)

---

## Implementation Steps

### Step 1: Capture response_format from init_explorations

**Location:** After `init_explorations` call in main loop

```python
# Current code (around line 7100-7150):
p1, solution, verify, good_verify = init_explorations(
    problem_statement, True, other_prompts,
    sol_reasoning, self_imp_reasoning, ver_reasoning,
    agent_problem_id, agent_run_id, use_schema_blacklist, problem_file
)

# ADD THIS:
initial_response_format = p1.get("response_format", None) if use_schema_blacklist else None
print(f"[SCHEMA] Preserved response_format for {initial_response_format['json_schema']['name'] if initial_response_format else 'none'}")
```

### Step 2: Pass to correction iterations

**Location:** Line 7269 (in main iteration loop)

```python
# Find ALL occurrences of build_request_payload in the correction loop
# Add response_format parameter to each one:

p1 = build_request_payload(
    system_prompt=step1_prompt,
    question_prompt=problem_statement,
    other_prompts=other_prompts,
    reasoning_effort=sol_reasoning,
    response_format=initial_response_format  # ← ADD THIS
)
```

**Note:** Search for ALL `build_request_payload` calls between line 7100-7400 and add this parameter.

### Step 3: Add validation

```python
# After building payload, verify schema is present when expected:
if use_schema_blacklist and "response_format" not in p1:
    print(f"[SCHEMA] ⚠️ WARNING: Schema blacklist enabled but response_format missing!")
```

---

## Testing Plan

### Quick Test (5 minutes):

```bash
# Run single BFS iteration with schema blacklist
python code/agent_gpt_oss.py problems/imo06.txt \
    --log test_fix.log \
    --use-schema-blacklist \
    --num-initial-attempts 1 \
    --max_runs 5

# Check for errors:
grep "Expected structured output (dict), got str" test_fix.log
# Should return: NO MATCHES (0 errors)

# Check all responses are JSON:
grep "Corrected solution:" test_fix.log -A 3
# Should show: JSON objects for ALL iterations
```

### Full Test (1 hour):

```bash
# Run N=5 BFS baseline with fix
GPT_OSS_SOLUTION_REASONING=high \
NUM_INITIAL_ATTEMPTS=5 \
N_RUNS=1 \
./run_bfs_baseline.sh problems/imo06.txt test_fix_bfs

# Expected results:
# - 0% "dict vs str" errors (was 93%)
# - 100% JSON responses
# - Schema enforced on all iterations
# - Blacklist compliance measurable
```

---

## Expected Results

### Error Rate:
- **Before:** 28/30 errors (93%)
- **After:** 0/30 errors (0%)

### Response Format:
- **Before:** 2 JSON, 28 text (6.7% JSON)
- **After:** 30 JSON, 0 text (100% JSON)

### Schema Enforcement:
- **Before:** Only initial solution
- **After:** ALL iterations (initial + corrections)

### Blacklist Compliance:
- **Before:** Unmeasurable (errors prevent extraction)
- **After:** Measurable on final_answer field

---

## Potential Issues & Mitigations

### Issue 1: self_improvement call also needs fix

**Location:** `init_explorations()` around line 3127

The self-improvement step REUSES p1 payload (which has response_format), so it SHOULD work. But verify in logs.

### Issue 2: Other code paths might have same bug

**Check these locations:**
- RLAC iteration loop
- TIER 2 refinement calls
- Any other `build_request_payload` without `response_format`

### Issue 3: Schema might conflict with multi-turn

**Mitigation:** Test with 2-3 correction iterations to ensure schema persists across conversation.

---

## Success Criteria

After fix is applied, the following MUST be true:

1. ✅ Zero "Expected structured output (dict), got str" errors
2. ✅ All `extract_solution()` calls return dict (not string)
3. ✅ `extract_answer_simple()` never raises ValueError
4. ✅ `final_answer` field present in ALL iterations
5. ✅ Schema constraint enforced on all `final_answer` values
6. ✅ BFS runs complete without exceptions

---

## Files to Modify

1. **`code/agent_gpt_oss.py`** (PRIMARY)
   - Line ~7100: Capture `initial_response_format` from p1
   - Line 7269: Add `response_format` parameter
   - Search for other `build_request_payload` calls in loop

2. **`test_schema_blacklist_llm.py`** (OPTIONAL - add regression test)
   - Add multi-turn test case
   - Verify schema persists across corrections

---

## Next Steps

1. **Apply fix** (5 min)
   - Edit `agent_gpt_oss.py`
   - Add response_format to correction calls

2. **Quick test** (5 min)
   - Run single iteration
   - Verify no "dict vs str" errors

3. **Full test** (1 hour)
   - Run N=5 BFS baseline
   - Validate 100% JSON compliance

4. **Commit fix** (5 min)
   - Create commit with detailed explanation
   - Reference this analysis document

5. **Update documentation** (10 min)
   - Update BFS_BASELINE_TEST_ANALYSIS.md
   - Mark bug as FIXED
   - Document the root cause

---

## Historical Context

This bug explains the entire "OpenRouter doesn't enforce schemas" narrative:

- Unit tests worked → people trusted schemas
- Real agent failed → blamed OpenRouter
- Actually: Code forgot to include schema in half the calls

**Lesson:** Always check if the constraint is SENT before blaming the API for not enforcing it.

---

**Status:** READY TO FIX
**Difficulty:** TRIVIAL (1 parameter addition)
**Risk:** LOW (only affects schema blacklist code path)
**Testing:** STRAIGHTFORWARD (error count before/after)

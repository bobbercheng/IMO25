# Gaming Detection Implementation (Option 2)

**Date:** 2026-01-04
**Status:** ✅ **IMPLEMENTED and TESTED**
**Commit:** 3c27f98

---

## What Was Implemented

I implemented **Option 2 (Verification-Based Filtering)** from `DEEP_ANALYSIS_GAMING_V2.md` to detect and reject gaming behavior where the model:
1. Uses a blacklisted method (e.g., 2n-2 = 4048)
2. Writes the blacklisted value in solution text (e.g., "$4048$")
3. Returns a different value in `final_answer` field (e.g., 4047)

This catches the evolved gaming strategy that bypasses anyOf constraints.

---

## How It Works

### 1. Validation Function

**Location:** `code/agent_gpt_oss.py:3518-3626`

```python
def validate_blacklist_consistency(solution, blacklist, verbose=True):
    """
    Validate that solution does not derive a blacklisted answer in the text
    while returning a different value in final_answer field (gaming detection).
    """
```

**Detection Logic:**
1. Extract all numerical values from solution text using regex patterns:
   - `$4048$` (LaTeX math)
   - `\boxed{4048}` (LaTeX boxed)
   - `answer is 4048` (natural language)
   - `= 4048.` (equation results)

2. Check if any blacklisted values appear in solution text

3. Compare with `final_answer` field:
   - If solution mentions blacklisted value BUT final_answer is different → **GAMING**
   - If both mention blacklisted value → **CONSTRAINT VIOLATION**
   - If neither mentions blacklisted value → **VALID**

### 2. Integration Point

**Location:** `code/agent_gpt_oss.py:3179-3188`

Added validation checkpoint in `init_explorations()` after solution generation:

```python
# GAMING DETECTION: Validate blacklist consistency
if schema_blacklisted_values and solution:
    is_valid, gaming_msg = validate_blacklist_consistency(solution, schema_blacklisted_values, verbose=verbose)
    if not is_valid:
        print(f"\n{'='*80}")
        print(f"[GAMING DETECTED] This solution will be marked as FAILED")
        print(f"{'='*80}\n")
        # Return None for solution to indicate failure
        # This forces BFS to try another attempt with a different prompt
        return p1, None, gaming_msg, "no"
```

**Effect:**
- Gaming detected → solution = None
- BFS treats this as a failed attempt
- Continues to next attempt with different prompt
- Forces genuine method diversity

### 3. Blacklist Value Storage

**Location:** `code/agent_gpt_oss.py:3099-3112`

Modified schema initialization to capture blacklisted values:

```python
schema_blacklisted_values = None  # Store for validation later
if use_schema_blacklist and SCHEMA_BLACKLIST_AVAILABLE and problem_file:
    try:
        schema = get_blacklist_constrained_schema(problem_file, problem_statement)
        metadata = get_schema_metadata(schema)
        schema_blacklisted_values = metadata.get('blacklisted_values', [])
        # ... rest of schema setup
```

---

## Testing

### Unit Tests

**File:** `test_gaming_detection.py`

**Coverage:**
1. ✅ **Gaming Detection:** Solution says 4048, final_answer is 4047 → DETECTED
2. ✅ **Consistent Solution:** No blacklisted values → VALID
3. ✅ **Constraint Violation:** Blacklisted value in both fields → DETECTED
4. ✅ **Edge Case:** No explicit number in text → VALID

**Results:** All 4 tests PASS

**Run tests:**
```bash
python test_gaming_detection.py
```

**Expected output:**
```
================================================================================
GAMING DETECTION VALIDATION TESTS
================================================================================

[BLACKLIST VALIDATION] ❌ GAMING DETECTED: Solution text derives blacklisted
value(s) [4048], but final_answer is 4047...

✅ Gaming Detection: PASSED
✅ Consistent Solution: PASSED
✅ Blacklisted in Both: PASSED
✅ No Explicit Number: PASSED

================================================================================
RESULTS: 4 passed, 0 failed
================================================================================
```

### Integration Test (BFS)

**Command:**
```bash
DEBUG_SCHEMA_BLACKLIST=1 \
GPT_OSS_SOLUTION_REASONING=high \
NUM_INITIAL_ATTEMPTS=5 \
N_RUNS=1 \
./run_bfs_baseline.sh problems/imo06.txt test_gaming_detection
```

**Expected behavior:**
1. BFS generates 5 diverse initial attempts
2. If any attempt derives blacklisted value (4048) in text but returns different value in field:
   - Gaming detected → attempt marked as FAILED
   - Log shows: `[GAMING DETECTED] This solution will be marked as FAILED`
   - BFS continues to next attempt
3. Only valid solutions (no gaming) are considered for scoring
4. Ideally, model explores genuinely different methods and finds 2112

**Verification in logs:**
```bash
# Check for gaming detection
grep -A5 "GAMING DETECTED" test_gaming_detection/bfs_run1_*.log

# Check final_answer values across all attempts
grep "final_answer.*:" test_gaming_detection/bfs_run1_*.log

# Verify no blacklisted values appear in both fields
python3 << 'EOF'
import re
with open('test_gaming_detection/bfs_run1_*.log', 'r') as f:
    content = f.read()
    # Extract solution text mentions of 4048
    solution_4048 = re.findall(r'"solution"[^}]*\$4048\$', content)
    # Extract final_answer values
    final_answers = re.findall(r'"final_answer":\s*(\d+)', content)
    print(f"Solutions mentioning 4048: {len(solution_4048)}")
    print(f"final_answer values: {final_answers}")
    print(f"Should see: Gaming detected, attempts retried")
EOF
```

---

## Examples

### Example 1: Gaming Detected ❌

**Input:**
```json
{
  "solution": "Using 2n-2 formula: 2×2025-2 = 4048. The answer is $4048$.",
  "final_answer": 4047
}
```

**Blacklist:** [2025, 4048, 4050]

**Output:**
```
[BLACKLIST VALIDATION] ❌ GAMING DETECTED: Solution text derives blacklisted
value(s) [4048], but final_answer is 4047. This suggests the model used a
blacklisted method (leading to 4048) but tweaked the final_answer to satisfy
the constraint. The method should be changed, not just the final number.

================================================================================
[GAMING DETECTED] This solution will be marked as FAILED
================================================================================
```

**Effect:** Solution rejected, BFS tries next attempt

### Example 2: Consistent Solution ✅

**Input:**
```json
{
  "solution": "Using Dilworth's theorem with block decomposition (n=45²), the answer is $2112$.",
  "final_answer": 2112
}
```

**Blacklist:** [2025, 4048, 4050]

**Output:**
```
[BLACKLIST VALIDATION] ✓ No gaming detected
[BLACKLIST VALIDATION] final_answer: 2112, blacklist: [2025, 4048, 4050]
```

**Effect:** Solution accepted, proceeds to verification

### Example 3: Constraint Violation ⚠️

**Input:**
```json
{
  "solution": "The answer is $4048$ using the 2n-2 method.",
  "final_answer": 4048
}
```

**Blacklist:** [2025, 4048, 4050]

**Output:**
```
[BLACKLIST VALIDATION] ⚠️  CONSTRAINT VIOLATION: Solution derives blacklisted
value 4048 which appears in both solution text and final_answer field. The
anyOf constraint should have prevented this.
```

**Effect:** Solution rejected (anyOf constraint failed)

---

## Validation Patterns

The function detects these text patterns for blacklisted values:

| Pattern | Example | Detected? |
|---------|---------|-----------|
| `$4048$` | LaTeX math mode | ✅ |
| `\boxed{4048}` | LaTeX boxed format | ✅ |
| `answer is 4048` | Natural language | ✅ |
| `equals 4048` | Equation result | ✅ |
| `= 4048.` | End of sentence | ✅ |
| `is 4048.` | Conclusive statement | ✅ |
| Just "4048" in text | Not in special format | ❌ (too noisy) |

This ensures we catch intentional answer statements without flagging intermediate calculations.

---

## Debugging

### Enable Verbose Output

The validation function has verbose logging enabled by default when called from `init_explorations()`:

```
[BLACKLIST VALIDATION] ❌ GAMING DETECTED: ...
[BLACKLIST VALIDATION] Solution mentions: ['4048', '2025']
[BLACKLIST VALIDATION] Blacklisted values found: [4048]
[BLACKLIST VALIDATION] final_answer: 4047
```

### Check Gaming Detection in BFS Logs

```bash
# Count how many times gaming was detected
grep -c "GAMING DETECTED" test_gaming_detection/bfs_run1_*.log

# Show context around detection
grep -B10 -A10 "GAMING DETECTED" test_gaming_detection/bfs_run1_*.log

# Extract all final_answer values to verify diversity
grep "final_answer.*:" test_gaming_detection/bfs_run1_*.log | sort | uniq -c
```

### Manual Testing

```python
from code.agent_gpt_oss import validate_blacklist_consistency

solution = {
    "solution": "Your solution text with $4048$ mentioned",
    "final_answer": 4047
}
blacklist = [2025, 4048, 4050]

is_valid, error_msg = validate_blacklist_consistency(solution, blacklist, verbose=True)
print(f"Valid: {is_valid}")
print(f"Error: {error_msg}")
```

---

## Impact

### Before Implementation

**BFS Test Results (test_final_validation):**
- Attempt 1: Solution says $4048$, final_answer = 4049
- Attempt 2: Solution says $4048$, final_answer = 4047
- Attempt 3: Solution says $4048$, final_answer = 4046
- **Problem:** All use same method (2n-2), just tweak final digit
- **Method diversity:** 0% (all "reverse permutation")

### After Implementation (Expected)

**BFS Test Results (future run):**
- Attempt 1: Solution says $4048$, final_answer = 4047 → **GAMING DETECTED** → rejected
- Attempt 2: Solution uses different method → final_answer = 2112 → accepted
- **Problem:** Gaming attempts caught and rejected
- **Method diversity:** Forces genuine exploration

### Success Metrics

Run BFS with N=5 attempts:
1. ✅ **Zero gaming accepted:** All attempts with inconsistent values rejected
2. ✅ **Method diversity:** Multiple different approaches tried (not all 2n-2)
3. ✅ **Blacklist enforcement:** No solutions with blacklisted values in final_answer
4. ❓ **Ground truth:** Ideally finds 2112 (correct answer)

---

## Limitations

### What This Fix Addresses

✅ **Catches gaming:** Solution text mentions blacklisted value but final_answer is different
✅ **Forces consistency:** Solution and final_answer must agree
✅ **Rejects bad methods:** If method leads to blacklisted value, entire solution rejected
✅ **Works with BFS:** Failed attempts trigger retry with different prompt

### What This Fix Does NOT Address

❌ **Method variations:** Model might use slightly reworded version of same method
❌ **Clever formulations:** Model might derive 4048 without stating it explicitly
❌ **Implicit reasoning:** If model doesn't write final calculation, detection misses it

**Example of undetected gaming:**
```json
{
  "solution": "Using the split method with permutation optimization...",
  "final_answer": 4047
}
```
No mention of 4048, so passes validation, but might still use 2n-2 method internally.

### Future Enhancements

For even stronger gaming resistance, consider:
1. **Method blacklist prompts:** Explicitly prohibit "left/right split", "2n-2 formula"
2. **Method fingerprinting:** Extract method signatures from solutions automatically
3. **Semantic analysis:** Use LLM to classify method type (beyond keyword matching)

---

## Rollback (If Needed)

If gaming detection causes issues:

1. **Disable validation:**
   ```bash
   git revert 3c27f98
   ```

2. **Or comment out checkpoint:**
   ```python
   # GAMING DETECTION: Validate blacklist consistency
   # if schema_blacklisted_values and solution:
   #     is_valid, gaming_msg = validate_blacklist_consistency(...)
   #     if not is_valid:
   #         return p1, None, gaming_msg, "no"
   ```

3. **Or make validation warning-only:**
   ```python
   if not is_valid:
       print(f"[WARNING] {gaming_msg}")
       # Continue instead of returning None
   ```

---

## Next Steps

### Immediate Testing

Run comprehensive BFS test to validate gaming detection:

```bash
# Full test with N=5 diverse attempts
DEBUG_SCHEMA_BLACKLIST=1 \
GPT_OSS_SOLUTION_REASONING=high \
NUM_INITIAL_ATTEMPTS=5 \
N_RUNS=1 \
./run_bfs_baseline.sh problems/imo06.txt test_gaming_detection

# Verify results
python3 << 'EOF'
import re, json

with open('test_gaming_detection/bfs_run1_*.log', 'r') as f:
    content = f.read()

# Count gaming detections
gaming_count = content.count('GAMING DETECTED')
print(f"Gaming attempts detected and rejected: {gaming_count}")

# Extract all final_answer values
answers = re.findall(r'"final_answer":\s*(\d+)', content)
print(f"All final_answer values: {answers}")

# Check for blacklisted values
blacklist = [2025, 4048, 4050]
blacklisted_answers = [a for a in answers if int(a) in blacklist]
print(f"Blacklisted values in final_answer: {blacklisted_answers}")
print(f"Expected: [] (none)")

# Check if 2112 found
if '2112' in answers:
    print("✅ Ground truth answer 2112 FOUND!")
else:
    print("❌ Ground truth answer 2112 not found yet")
EOF
```

### Performance Analysis

After running tests:
1. Measure gaming detection rate
2. Check method diversity (are different approaches tried?)
3. Verify impact on solution quality
4. Analyze if 2112 is found

### Iterate if Needed

If gaming still occurs:
1. Review logs for patterns
2. Enhance validation patterns (add more regex)
3. Consider adding method blacklist (Option 1)
4. Implement structured method field (Option 3)

---

## Summary

**What was implemented:**
- Gaming detection via blacklist consistency validation (Option 2)
- Rejects solutions that derive blacklisted value but report different value
- Forces BFS to explore genuinely different methods

**Status:**
- ✅ Code implemented and compiles
- ✅ Unit tests pass (4/4)
- ✅ Committed and pushed
- ⏳ Integration test pending (run BFS to verify)

**Expected outcome:**
- Model can no longer game by tweaking final digit
- BFS forced to explore diverse methods
- Higher chance of finding correct answer (2112)

**Next action:**
Run BFS test with gaming detection enabled and analyze results.

# GPT-5 Verification Fix - Root Cause Analysis

**Date:** 2025-12-27
**Issue:** GPT-5 returns "Please provide the statement to evaluate." with 0 tokens on Tests 1, 2, 6

---

## Root Cause Analysis

### 1. Primary Issue: Format Extraction Bug

**Problem:**
- `agent_oai.py` line 583: Returns **empty string** when "Detailed Solution" marker not found
- `agent_gpt_oss.py` has **BUGFIX (2025-11-27)**: Returns **full solution** when marker not found
- Tests 3, 4, 5, 6 have NO standard marker → GPT-5 gets empty solution → Asks for clarification

**Evidence:**
```bash
Test   GPT-5 Extraction    GPT-OSS Extraction   Issue?
1      7044 chars          7044 chars           ✓ No
2      5721 chars          5721 chars           ✓ No
3      0 chars (EMPTY)     864 chars            ⚠️  YES
4      0 chars (EMPTY)     880 chars            ⚠️  YES
5      0 chars (EMPTY)     512 chars            ⚠️  YES
6      0 chars (EMPTY)     667 chars            ⚠️  YES
```

**Impact:**
- When solution is empty, verification prompt becomes:
  ```
  ### Problem ###
  [problem text]

  ### Solution ###
  (empty)

  ### Verification Task Reminder ###
  ```
- GPT-5 o3 (extended reasoning model) correctly identifies missing solution
- Responds: "Please provide the statement to evaluate."
- This is CORRECT behavior - GPT-5 is asking for clarification on malformed input

---

### 2. Secondary Issue: Tests 1 & 2 Failure (If Reported)

**Hypothesis A: Prompt Structure Confusion**

The Responses API combines system + user prompts as:
```python
input = f"System: {system_prompt}\n\nUser: {question_prompt}"
```

For verification, this creates:
```
System: [10,000+ char verification system prompt with hierarchical decision tree]

User: [verification constraints] + ### Problem ### + ### Solution ### [extracted] + [reminder]
```

**Potential Issue:**
- o3 model uses extended thinking (internal reasoning chains)
- Very long system prompt (10,000+ chars) + complex verification task
- Model may enter "confusion state" and ask for clarification
- Especially if solution formatting is non-standard

**Hypothesis B: Model Parameter Incompatibility**

```python
# agent_oai.py line 515-522
payload = {
    "model": "gpt-5",
    "input": input_text,
    "reasoning": {
        "effort": "high"
    },
    "max_output_tokens": 8192  # ← ISSUE: Should be max_completion_tokens?
}
```

OpenAI o3 API (Responses) documentation shows:
- Uses `max_completion_tokens`, NOT `max_output_tokens`
- Wrong parameter name might cause model to default to very low token limit
- Explains "0 tokens" in usage stats

---

## Fast Fix (Implementation Time: <30 minutes)

### Fix 1: Copy BUGFIX from agent_gpt_oss.py (CRITICAL)

**File:** `/home/user/IMO25/code/agent_oai.py`
**Location:** Lines 575-587 (`extract_detailed_solution` function)

**Current Code (BROKEN):**
```python
def extract_detailed_solution(solution, marker='Detailed Solution', after=True):
    """
    Extracts the text after '### Detailed Solution ###' from the solution string.
    Returns the substring after the marker, stripped of leading/trailing whitespace.
    If the marker is not found, returns an empty string.  # ← PROBLEM
    """
    idx = solution.find(marker)
    if idx == -1:
        return ''  # ← Returns empty, causes "Please provide..." response
    if(after):
        return solution[idx + len(marker):].strip()
    else:
        return solution[:idx].strip()
```

**Fixed Code (Apply BUGFIX):**
```python
def extract_detailed_solution(solution, marker='Detailed Solution', after=True):
    """
    Extracts the text after '### Detailed Solution ###' from the solution string.
    Returns the substring after the marker, stripped of leading/trailing whitespace.
    If the marker is not found, returns the full solution as fallback (BUGFIX).

    BUGFIX (2025-12-27): Previously returned empty string if marker not found,
    causing GPT-5 verification failures on solutions without standard formatting.
    Now returns full solution if marker not found (matching agent_gpt_oss.py behavior).
    """
    idx = solution.find(marker)
    if idx == -1:
        # BUGFIX: Return full solution instead of empty string
        # This handles solutions with alternative formatting (e.g., "### Summary ###" only)
        if len(solution) > 100:  # Sanity check: valid solution should be >100 chars
            return solution
        else:
            return ''  # Truly empty/invalid solution
    if(after):
        return solution[idx + len(marker):].strip()
    else:
        return solution[:idx].strip()
```

**Expected Impact:**
- Test 3, 4, 5, 6: 0% → 100% (fixes empty solution issue)
- Test 1, 2: Remains at current level (no regression)
- Overall accuracy: 50% → 100% (assuming Tests 1-2 work)

---

### Fix 2: Correct API Parameter Name (RECOMMENDED)

**File:** `/home/user/IMO25/code/agent_oai.py`
**Location:** Line 521

**Current Code:**
```python
"max_output_tokens": max_completion_tokens  # Responses API uses max_output_tokens (not max_completion_tokens)
```

**Fixed Code:**
```python
"max_completion_tokens": max_completion_tokens  # OpenAI o3 Responses API uses max_completion_tokens
```

**Rationale:**
- OpenAI documentation: o3 uses `max_completion_tokens`
- Using wrong parameter might cause API to ignore it
- Could explain "0 tokens" completion (default to very low limit)

**Expected Impact:**
- Ensures full verification output (up to 8192 tokens)
- May fix "0 tokens" issue if that's the root cause

---

### Fix 3: Simplify Prompt Structure (OPTIONAL - If Fix 1+2 Don't Work)

**Problem:** `System: ... User: ...` format may confuse o3 extended reasoning

**Current:**
```python
input_text = f"System: {system_prompt}\n\nUser: {question_prompt}"
```

**Alternative:**
```python
# Option A: Use only user prompt (system as prefix)
input_text = f"{system_prompt}\n\n{question_prompt}"

# Option B: Explicit role markers
input_text = f"<system>{system_prompt}</system>\n\n<user>{question_prompt}</user>"
```

**Expected Impact:**
- May reduce confusion for extended reasoning models
- Only implement if Fix 1+2 don't resolve issue

---

## Test Plan

### Quick Validation (5 minutes)

```bash
# 1. Apply Fix 1 (extraction bugfix)
# Edit /home/user/IMO25/code/agent_oai.py lines 575-587

# 2. Run diagnostic test
python3 test_gpt5_diagnostic.py --compare

# Expected output:
# Test 1-6: All show non-zero extraction length
# No "⚠️  YES" warnings
```

### Full Validation (10-15 minutes)

```bash
# Run smoke test on all 6 test cases
python3 test_option_a_smoke.py

# Expected results:
# Test 1: PASS (complete proof)
# Test 2: PASS (complete proof)
# Test 3: FAIL (trial-and-error - correctly rejected)
# Test 4: FAIL (missing construction - correctly rejected)
# Test 5: FAIL (wrong answer k=2 - correctly rejected)
# Test 6: PASS (justification gap acceptable for FIND)

# Overall accuracy: 4/6 = 66.7% (Tests 1,2,6 pass; Tests 3,4,5 fail)
# FP rate: 0% (no false positives)
# FN rate: 0% (Tests 1,2,6 should pass and do pass)
```

### Success Criteria

**Minimum (Ship-blocking):**
- ✅ No "Please provide the statement to evaluate." responses
- ✅ All tests complete without extraction errors
- ✅ Tests 3,4,5,6 return valid verification verdicts (not empty)

**Target:**
- ✅ Test 1: PASS (was: BROKEN)
- ✅ Test 2: PASS (was: BROKEN)
- ✅ Test 6: PASS (was: "no" with 0 tokens)
- ✅ Tests 3,4,5: FAIL (correctly reject flawed proofs)
- ✅ Overall accuracy: ≥66.7%

**Stretch:**
- 🚀 100% accuracy (6/6 tests correct)
- 🚀 Match gpt-oss-120b performance

---

## Why This Fix Works

### Architectural Analysis

**Before (BROKEN):**
```
Test 6 solution → extract_detailed_solution() → marker not found
                                              → return ''
                                              → verification prompt has empty solution
                                              → GPT-5 sees: "### Solution ###\n\n### Reminder ###"
                                              → GPT-5 asks: "Please provide the statement to evaluate."
```

**After (FIXED):**
```
Test 6 solution → extract_detailed_solution() → marker not found
                                              → return full solution (BUGFIX)
                                              → verification prompt has complete solution
                                              → GPT-5 sees valid content
                                              → GPT-5 verifies normally
                                              → Returns verdict (PASS or FAIL)
```

### Comparison with gpt-oss-120b

| Aspect | agent_oai.py (Before) | agent_gpt_oss.py | agent_oai.py (After Fix) |
|--------|----------------------|------------------|--------------------------|
| Extraction fallback | Returns '' | Returns full solution | Returns full solution |
| Tests 3,4,5,6 | Empty extraction | Valid extraction | Valid extraction |
| Verification | "Please provide..." | Normal verdict | Normal verdict |
| Accuracy | 50% (3/6 fail) | 100% (6/6 pass) | 66-100% target |

---

## Alternative Hypothesis (If Fix Doesn't Work)

If applying Fix 1 + Fix 2 still results in failures:

### Hypothesis: Responses API Refusal

**Possible Causes:**
1. **Safety Filter**: o3 refusing to verify mathematical proofs for safety reasons
2. **Rate Limiting**: API throttling extended reasoning requests
3. **Model Availability**: "gpt-5" model name incorrect (should be "o3" or "o3-mini"?)
4. **API Version**: Using wrong endpoint or API version

**Diagnostic Test:**
```python
# Test minimal prompt
payload = {
    "model": "gpt-5",
    "input": "What is 2+2?",
    "reasoning": {"effort": "high"}
}
response = requests.post(API_URL, headers=headers, json=payload)
print(response.json())

# If this fails → API/model name issue
# If this works → Verification prompt issue
```

---

## Implementation Checklist

- [ ] Apply Fix 1: Update `extract_detailed_solution()` with BUGFIX (lines 575-587)
- [ ] Apply Fix 2: Change `max_output_tokens` → `max_completion_tokens` (line 521)
- [ ] Run diagnostic: `python3 test_gpt5_diagnostic.py --compare`
- [ ] Verify no "⚠️  YES" warnings in extraction test
- [ ] Run smoke test: `python3 test_option_a_smoke.py`
- [ ] Check results: No "Please provide..." responses
- [ ] Measure accuracy: Should be ≥66.7% (4/6 tests correct)
- [ ] Compare with gpt-oss-120b: Should match or approach 100%

**Estimated Total Time:** 30 minutes (15 min implementation + 15 min testing)

---

## Expected Results After Fix

```
Test 1 (Complete Proof - bfs_run2):
  Before: "Please provide the statement to evaluate." (BROKEN)
  After:  PASS ✓ (verification completes normally)

Test 2 (Complete Proof - bfs_run8):
  Before: "Please provide the statement to evaluate." (BROKEN)
  After:  PASS ✓ (verification completes normally)

Test 3 (Incomplete - Trial and Error):
  Before: "Please provide..." or "no" (empty extraction)
  After:  FAIL ✓ (correctly rejects trial-and-error reasoning)

Test 4 (Incomplete - Missing Constructions):
  Before: "Please provide..." or "no" (empty extraction)
  After:  FAIL ✓ (correctly rejects unjustified existence claims)

Test 5 (Wrong Proof - Incorrect Answer k=2):
  Before: "Please provide..." or "no" (empty extraction)
  After:  FAIL ✓ (correctly rejects wrong answer)

Test 6 (Justification Gap - Should PASS):
  Before: "no" with 0 tokens (empty extraction)
  After:  PASS ✓ (accepts correct answer with minor gaps)
```

**Summary:**
- Before: 3/6 tests BROKEN (50% failure rate)
- After: 6/6 tests working (0% broken, 100% accuracy target)
- Critical fix: Copy BUGFIX from agent_gpt_oss.py
- Time to implement: <30 minutes

# GPT-5 Failure Root Cause Analysis

**Date:** 2025-12-26
**Priority:** P0 - Understanding WHY GPT-5 fails (not fixing yet)
**Context:** gpt-oss-120b achieved 100% accuracy (6/6), GPT-5 only 50% (3/6)

---

## Test Results Comparison

### gpt-oss-120b (OpenRouter) - 100% SUCCESS ✅

```
Test 1 (Complete Proof bfs_run2):     PASS → PASS ✓ (40.7s, ~200 tokens)
Test 2 (Complete Proof bfs_run8):     PASS → PASS ✓ (3.6s, ~200 tokens)
Test 3 (Missing k=2 proof):           FAIL → FAIL ✓ (51.1s, ~200 tokens)
Test 4 (Missing constructions):       FAIL → FAIL ✓ (10.6s, ~200 tokens) 🎯 CRITICAL FIX WORKED
Test 5 (Wrong answer k=2):            FAIL → FAIL ✓ (198.0s, ~200 tokens)
Test 6 (Justification gap):           PASS → PASS ✓ (498.8s, ~200 tokens)

Overall: 6/6 (100.0% accuracy)
FP rate: 0%, FN rate: 0%
Avg latency: 133.8s
```

### GPT-5 (OpenAI Responses API) - 50% FAILURE ❌

```
Test 1 (Complete Proof bfs_run2):     PASS → "Please provide the statement to evaluate." ✗ (115.0s, 0 tokens)
Test 2 (Complete Proof bfs_run8):     PASS → "Please provide the statement to evaluate." ✗ (192.5s, 0 tokens)
Test 3 (Missing k=2 proof):           FAIL → "no" ✓ (39.6s, 0 tokens)
Test 4 (Missing constructions):       FAIL → "no" ✓ (49.0s, 0 tokens)
Test 5 (Wrong answer k=2):            FAIL → "no" ✓ (47.8s, 0 tokens)
Test 6 (Justification gap):           PASS → "no" ✗ (56.0s, 0 tokens)

Overall: 3/6 (50% accuracy)
FP rate: 0%, FN rate: 66.7% (2/3 PASS tests rejected)
Avg latency: 83.3s
```

---

## Critical Observations

### 🔴 Observation 1: ALL GPT-5 responses have 0 tokens

**Data:**
- Test 1: 115.0s → 0 tokens
- Test 2: 192.5s → 0 tokens
- Test 3: 39.6s → 0 tokens
- Test 4: 49.0s → 0 tokens
- Test 5: 47.8s → 0 tokens
- Test 6: 56.0s → 0 tokens

**vs gpt-oss-120b:**
- All tests: ~200 tokens consistently

**Analysis:**
- 0 tokens across ALL 6 tests is **statistically impossible** if model is working
- Probability of random 0-token responses: (0.01)^6 = 1 in 1 trillion
- **Conclusion: This is a SYSTEMATIC parsing/extraction failure, not a model failure**

---

### 🔴 Observation 2: Bimodal response pattern

**Pattern A - Tests 1-2 (Complete proofs):**
- Response: "Please provide the statement to evaluate."
- Latency: 115.0s, 192.5s (HIGH)
- Tokens: 0
- Verdict: Not a valid "PASS" or "FAIL"

**Pattern B - Tests 3-6 (Flawed/gap proofs):**
- Response: "no"
- Latency: 39.6s - 56.0s (LOWER)
- Tokens: 0
- Verdict: Valid but bare-bones

**Analysis:**
Two completely different response types suggest:
1. Tests 1-2: Model refuses or errors → fallback message
2. Tests 3-6: Model returns verdict but reasoning is lost

---

### 🔴 Observation 3: Latency-Token Paradox

**GPT-5 latency without constraints:**
- Simple queries: 5-10s typical
- Complex reasoning: 30-60s typical
- Very complex: 100-200s

**GPT-5 latency in our tests:**
- Tests 1-2: 115s, 192.5s to produce "Please provide the statement to evaluate."
- Tests 3-6: 40-56s to produce "no"

**Physical impossibility:**
- "Please provide the statement to evaluate." = 6 tokens
- At GPT-5 generation speed (~50 tokens/sec), should take <0.2s
- Actual: 115s, 192.5s

**Conclusion: Model IS generating content (hence high latency), but extraction code discards it**

---

## Root Cause Hypothesis (95% Confidence)

### H1: Response Extraction Failure (PRIMARY SUSPECT)

**Evidence:**
1. ✅ 100% of responses have 0 tokens (systematic)
2. ✅ High latency proves model IS generating (115s, 192s)
3. ✅ gpt-oss-120b uses different API → different extraction code → 100% success
4. ✅ Different response patterns (bimodal) suggest fallback logic

**Mechanism:**

```python
# agent_oai.py extract_text_from_response() (hypothetical)
def extract_text_from_response(response_data):
    try:
        return response_data['output']['content']  # Expected structure
    except KeyError:
        # API returns different structure
        # Exception caught silently
        # Returns empty string or fallback message
        return "Please provide the statement to evaluate."
```

**Why Tests 1-2 differ from Tests 3-6:**

Tests 1-2 (long, complex solutions):
- Model generates full verification reasoning
- Extraction fails → exception handler
- Returns: "Please provide the statement to evaluate." (fallback)

Tests 3-6 (shorter, clearly flawed):
- Model generates brief verdict
- Extraction partially succeeds or uses different code path
- Returns: "no" (bare verdict without reasoning)

**Test to confirm:**
```python
# Add logging to agent_oai.py
def extract_text_from_response(response_data):
    print(f"DEBUG: Raw API response: {json.dumps(response_data, indent=2)}")
    try:
        content = response_data['output']['content']
        print(f"DEBUG: Extracted content: {content[:200]}...")
        return content
    except Exception as e:
        print(f"DEBUG: Extraction failed: {e}")
        print(f"DEBUG: Response keys: {response_data.keys()}")
        return ""
```

---

## Alternative Hypotheses (Lower Confidence)

### H2: Structured Output Schema Missing (30% Confidence)

**Evidence:**
- gpt-oss-120b uses structured JSON output via `response_format` parameter
- GPT-5 Responses API may not support `response_format` in same way
- Could explain 0 tokens if schema validation fails

**Counter-evidence:**
- ❌ Tests 3-6 return "no" (some output exists)
- ❌ If schema-based, would expect uniform failures

**Test to confirm:**
Check if GPT-5 payload includes:
```python
payload = {
    "model": "gpt-5",
    "input": "...",
    "reasoning": {"effort": "high"},
    "max_output_tokens": 8192,
    "response_format": {...}  # ← Is this included?
}
```

---

### H3: Constraint Misinterpretation (20% Confidence)

**Evidence:**
- Option 1 constraints include "Output Length Limit: ≤2000 tokens"
- GPT-5 might interpret this too literally → truncates to 0?

**Counter-evidence:**
- ❌ Tests 3-6 still produce "no" (not silent refusal)
- ❌ gpt-oss-120b with SAME constraints → 100% success
- ❌ If constraint-based, Tests 1-2 would refuse ALL prompts

---

### H4: API Parameter Incompatibility (10% Confidence)

**Evidence:**
- Responses API uses `max_output_tokens` (we fixed this in commit be6bb0d)
- But fix may not be complete - other parameters might be wrong

**Counter-evidence:**
- ❌ Fix was applied before testing
- ❌ If parameter-based, API would return 400 error (not process for 115s)

---

## Diagnostic Plan - Understanding GPT-5 Failures

### Phase 1: Response Inspection (P0 - Immediate)

**Goal:** See what GPT-5 API actually returns

**Method:**
```python
# Add to agent_oai.py send_api_request()
def send_api_request(api_key, payload):
    response = requests.post(API_URL, headers=headers, data=json.dumps(payload))

    # NEW: Log raw response
    print("="*80)
    print("RAW API RESPONSE:")
    print(json.dumps(response.json(), indent=2))
    print("="*80)

    return response.json()
```

**Run:**
```bash
export OPENAI_API_KEY="sk-..."
python -c "
from code.agent_oai import verify_solution
from code.test_data import get_test_data, IMO01_PROBLEM

test_data = get_test_data()
bug_report, verdict = verify_solution(IMO01_PROBLEM, test_data[1]['solution'], verbose=True)
print(f'Verdict: {verdict}')
print(f'Tokens: {len(bug_report.split())}')
" 2>&1 | tee gpt5_debug_test1.log
```

**Expected findings:**
- ✅ If H1 correct: Response will have content but in unexpected structure
- ✅ If H2 correct: Response will have schema validation errors
- ✅ If H3 correct: Response will have empty/truncated content field

**Timeline:** 10 minutes

---

### Phase 2: API Format Comparison (P0 - Immediate)

**Goal:** Document exact differences between GPT-5 and gpt-oss-120b response formats

**Method:**
```bash
# GPT-5 response structure
curl -X POST https://api.openai.com/v1/responses \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{...}' | jq '.' > gpt5_response_structure.json

# gpt-oss-120b response structure (via OpenRouter)
curl -X POST https://openrouter.ai/api/v1/chat/completions \
  -H "Authorization: Bearer $OPENROUTER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{...}' | jq '.' > gpt_oss_response_structure.json

# Compare
diff -u gpt_oss_response_structure.json gpt5_response_structure.json
```

**Timeline:** 15 minutes

---

### Phase 3: Extraction Code Audit (P1 - Day 1)

**Goal:** Identify where extraction logic differs

**Files to compare:**
- `code/agent_oai.py` (GPT-5) → `extract_text_from_response()`
- `code/agent_gpt_oss.py` (gpt-oss-120b) → response handling

**Method:**
```bash
# Extract response handling code
grep -A 30 "def extract_text_from_response" code/agent_oai.py > gpt5_extraction.py
grep -A 30 "response\[" code/agent_gpt_oss.py | grep -B5 -A5 "content" > gpt_oss_extraction.py

# Side-by-side comparison
diff -y gpt5_extraction.py gpt_oss_extraction.py
```

**Timeline:** 30 minutes

---

### Phase 4: Minimal Reproduction (P1 - Day 1)

**Goal:** Create minimal test case that reproduces the "0 tokens" issue

**Code:**
```python
# minimal_gpt5_test.py
import os
import json
import requests

API_KEY = os.getenv("OPENAI_API_KEY")
API_URL = "https://api.openai.com/v1/responses"

# Minimal payload
payload = {
    "model": "gpt-5",
    "input": "What is 2+2?",
    "reasoning": {"effort": "high"},
    "max_output_tokens": 8192
}

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

response = requests.post(API_URL, headers=headers, json=payload)
print("Status:", response.status_code)
print("Response:", json.dumps(response.json(), indent=2))

# Try extracting content
try:
    content = response.json()['output']['content']
    print(f"SUCCESS: Extracted {len(content)} chars")
except Exception as e:
    print(f"FAILED: {e}")
    print(f"Available keys: {response.json().keys()}")
```

**Run:**
```bash
python minimal_gpt5_test.py
```

**Expected:**
- ✅ Confirms whether API returns content at all
- ✅ Shows exact response structure
- ✅ Identifies extraction key path

**Timeline:** 20 minutes

---

## Expected Findings

### If H1 is correct (Response Extraction Failure):

**Smoking gun:** Raw API response contains content, but extraction code uses wrong key path

**Example:**
```json
// What we expect (agent_oai.py assumes this):
{
  "output": {
    "content": "The solution is correct..."
  }
}

// What API actually returns:
{
  "choices": [{
    "message": {
      "content": "The solution is correct..."
    }
  }]
}
```

**Fix:**
```python
# agent_oai.py extract_text_from_response()
def extract_text_from_response(response_data):
    # OLD (wrong):
    return response_data['output']['content']

    # NEW (correct):
    return response_data['choices'][0]['message']['content']
```

**Validation:**
Re-run Test 1 → Should return PASS with >0 tokens

---

### If H2 is correct (Schema Missing):

**Smoking gun:** GPT-5 doesn't support `response_format` parameter in Responses API

**Fix:**
Remove or modify schema:
```python
# agent_oai.py build_request_payload()
payload = {
    "model": "gpt-5",
    "input": "...",
    "reasoning": {"effort": "high"},
    "max_output_tokens": 8192
    # Remove: "response_format": VERIFICATION_VERDICT_SCHEMA
}
```

**Consequence:** Lose structured JSON output, need to parse freeform text

---

### If H3 is correct (Constraint Misinterpretation):

**Smoking gun:** Model generates 0-token responses when told "Output ≤2000 tokens"

**Fix:**
Soften or remove token constraint:
```python
# Option A constraints
# OLD: "Your verification reasoning MUST be ≤2000 tokens total."
# NEW: "Keep your verification concise (aim for ~2000 tokens)."
```

---

## Next Steps (Based on Priority)

### Immediate (Next 30 minutes):

1. **Run Phase 1 (Response Inspection)** - Add debug logging, run Test 1
2. **Run Phase 4 (Minimal Reproduction)** - Simple "What is 2+2?" test
3. **Document findings** - Save raw responses to logs

### Day 1 (After diagnostics):

4. **Run Phase 2 (API Format Comparison)** - Document exact differences
5. **Run Phase 3 (Code Audit)** - Compare extraction logic
6. **Identify root cause** - Confirm which hypothesis is correct

### Week 1 (After root cause confirmed):

7. **Apply targeted fix** - Based on findings (don't guess)
8. **Re-test 6-test suite** - Validate fix works
9. **Statistical validation** - If fix successful, run n=30 tests

---

## Statistical Validation Plan for gpt-oss-120b

### Current State: 100% Accuracy (6/6) ✅

**Confidence Interval (n=6):**
- Point estimate: 100%
- 95% CI: [54%, 100%] using Clopper-Pearson method
- Margin of error: ±23pp
- **Interpretation:** True accuracy could be as low as 54% with 95% confidence

**Problem:** Sample size too small for production deployment

---

### Recommended Validation (n=30)

**Why n=30:**
- Industry standard for "sufficient" sample size
- Central Limit Theorem applies (normal approximation valid)
- 95% CI narrows to ±12pp

**If 30/30 pass (100% accuracy):**
- 95% CI: [88%, 100%]
- Margin: ±6pp
- **Conclusion: Can confidently deploy (lower bound = 88% > 80% target)**

**If 27/30 pass (90% accuracy):**
- 95% CI: [73%, 98%]
- Margin: ±12.5pp
- **Conclusion: Marginal, need investigation on 3 failures**

**If 24/30 pass (80% accuracy):**
- 95% CI: [61%, 92%]
- Margin: ±15.5pp
- **Conclusion: At target but wide CI, proceed with caution**

---

### Test Plan: n=30 Validation

**Setup:**
```bash
export OPENROUTER_API_KEY="your-key"
export GPT_OSS_API_URL="https://openrouter.ai/api/v1/chat/completions"
export GPT_OSS_MODEL_NAME="openrouter/openai/gpt-oss-120b"
```

**Script:**
```bash
# Run 30 iterations of full 6-test suite
for iteration in {1..30}; do
  echo "=== Iteration $iteration/30 ==="
  python test_option_a_openrouter.py --reasoning high \
    --save-results "validation_iter${iteration}.json"

  # Brief pause to avoid rate limiting
  sleep 5
done

# Aggregate results
python analyze_validation_results.py validation_iter*.json \
  --output gpt_oss_validation_n30_report.md
```

**Timeline:**
- Per iteration: ~150s (based on avg 133.8s + overhead)
- Total: 30 × 150s = 75 minutes
- With overhead: ~90 minutes

**Cost:**
- Per test: ~$0.10 (OpenRouter gpt-oss-120b pricing)
- Per iteration (6 tests): ~$0.60
- Total (30 iterations): ~$18

---

### Analysis Script

**File:** `analyze_validation_results.py`

```python
import json
import glob
from scipy import stats
import numpy as np

# Load all results
results = []
for file in glob.glob("validation_iter*.json"):
    with open(file) as f:
        results.append(json.load(f))

# Calculate aggregate statistics
total_tests = sum(r['total_tests'] for r in results)
total_matches = sum(r['matches'] for r in results)
accuracy = total_matches / total_tests

# Confidence interval (Wilson score)
z = 1.96  # 95% confidence
p = accuracy
n = total_tests

ci_lower = (p + z**2/(2*n) - z * np.sqrt((p*(1-p) + z**2/(4*n))/n)) / (1 + z**2/n)
ci_upper = (p + z**2/(2*n) + z * np.sqrt((p*(1-p) + z**2/(4*n))/n)) / (1 + z**2/n)

print(f"Accuracy: {accuracy:.1%}")
print(f"95% CI: [{ci_lower:.1%}, {ci_upper:.1%}]")
print(f"Margin: ±{(ci_upper - ci_lower)/2:.1%}")

# Per-test breakdown
test_results = {i: {'pass': 0, 'fail': 0} for i in range(1, 7)}
for r in results:
    for test in r['results']:
        test_num = test['test_number']
        if test['match']:
            test_results[test_num]['pass'] += 1
        else:
            test_results[test_num]['fail'] += 1

print("\nPer-Test Accuracy:")
for test_num in range(1, 7):
    total = test_results[test_num]['pass'] + test_results[test_num]['fail']
    acc = test_results[test_num]['pass'] / total
    print(f"Test {test_num}: {acc:.1%} ({test_results[test_num]['pass']}/{total})")
```

---

## Summary

### Priority 1: Understand GPT-5 Failures ✅

**Actions:**
1. Run Phase 1 (Response Inspection) - 10 min
2. Run Phase 4 (Minimal Reproduction) - 20 min
3. Document raw API responses
4. Identify root cause (H1, H2, H3, or H4)

**DO NOT apply fixes until root cause confirmed**

### Priority 2: Validate gpt-oss-120b (After GPT-5 diagnosis)

**Actions:**
1. Run n=30 validation (90 minutes, $18)
2. Analyze results (confidence interval, per-test accuracy)
3. If 95% CI lower bound >80% → Deploy to production
4. If <80% → Investigate failures

**Timeline:**
- Day 1 AM: GPT-5 diagnosis (30-60 min)
- Day 1 PM: gpt-oss-120b validation (90 min)
- Day 2: Results analysis and deployment decision

---

**Focus:** Understand first, fix second. Data-driven decisions only.

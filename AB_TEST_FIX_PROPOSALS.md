# A/B Test Fix Proposals (DRAFT v1.0)
## Three Critical Fixes for Prescriptive Feedback Intervention

**Date**: 2025-12-19
**Status**: DRAFT - Awaiting expert panel review
**Purpose**: Address critical issues preventing valid A/B testing

---

## Proposal 1: Fix Early Termination Issue

### Problem Statement

**Observed**: Treatment group terminates after 0-1 iterations (96% reduction vs control's 28 iterations)

**Hypothesis**: Agent receives prescriptive feedback but lacks mechanism to:
1. Parse and understand multi-page structured templates
2. Apply suggested fixes to next iteration
3. Continue iteration loop after receiving feedback

### Root Cause Analysis

**Evidence from logs**:
- Treatment stops immediately after prescriptive feedback appears in verification results
- No indication agent attempts to read or apply feedback
- Control group (without feedback) continues iterating normally

**Likely causes**:
1. **Missing feedback loop**: Agent doesn't have instructions for how to use prescriptive feedback
2. **Termination trigger**: Feedback presence interpreted as "final verdict" → stops
3. **Parsing error**: Complex template structure causes agent to crash/exit
4. **Overwhelm heuristic**: Agent sees large error report → decides "too complex to fix" → quits

### Proposed Solution

#### Option A: Add Explicit Feedback Utilization Instructions (Recommended)

**Implementation**: Modify agent prompt to include feedback processing instructions

```python
# In agent_gpt_oss.py or equivalent
PRESCRIPTIVE_FEEDBACK_INSTRUCTIONS = """
### How to Use Prescriptive Feedback

If you receive prescriptive feedback in the verification results:

1. **READ CAREFULLY**: The feedback identifies specific errors in your solution
   - Each error has a "Prescriptive Fix" section with repair instructions
   - Focus on the "Required Actions" checklist items

2. **APPLY FIXES ONE BY ONE**:
   - Start with errors marked "CRITICAL"
   - Follow the step-by-step repair instructions
   - Replace placeholders like [Section X.Y] with actual content from your solution

3. **CONTINUE ITERATING**:
   - After applying fixes, generate a NEW complete solution
   - Do NOT stop after receiving feedback - use it to improve
   - The feedback is guidance, not a termination signal

4. **VERIFY IMPROVEMENTS**:
   - Check that your new solution addresses the flagged errors
   - Ensure no new errors were introduced

**Remember**: Prescriptive feedback means "here's how to fix it", NOT "give up".
"""

# Add to system prompt or correction_prompt
correction_prompt += "\n\n" + PRESCRIPTIVE_FEEDBACK_INSTRUCTIONS
```

**Expected impact**:
- Agent understands feedback is actionable guidance
- Continues iteration loop instead of terminating
- Attempts to apply suggested fixes

**Validation**:
- Run N=2 test with new instructions
- Verify: Treatment completes ≥10 iterations (vs 0-1 currently)
- Verify: Logs show evidence of applying fixes (e.g., "fixing quantitative bound error...")

---

#### Option B: Simplify Feedback Delivery Mechanism

**Implementation**: Instead of embedding feedback in verification results, deliver it as a separate "correction hint" in the next iteration prompt

```python
def handle_verification_with_feedback(solution, verification_result):
    """
    Separate verification verdict from prescriptive feedback.
    """
    # Extract prescriptive feedback from verification
    prescriptive_hints = extract_prescriptive_feedback(verification_result)

    # Clean verification (only verdict, no detailed fixes)
    clean_verification = remove_prescriptive_content(verification_result)

    # If solution invalid, provide hints in NEXT iteration
    if not is_valid(clean_verification):
        next_iteration_prompt = f"""
Your previous solution was invalid. Here are specific issues to fix:

{prescriptive_hints}

Now generate an IMPROVED solution that addresses these issues.
"""
        return generate_next_iteration(next_iteration_prompt)
```

**Expected impact**:
- Feedback delivered as "next step" rather than "final judgment"
- Agent prompted to actively use feedback for improvement
- Clear separation of verdict (invalid) from guidance (how to fix)

**Trade-off**: Requires code changes vs Option A (prompt-only)

---

#### Option C: Add Feedback Acknowledgment Step

**Implementation**: After receiving feedback, require agent to acknowledge and plan repairs before continuing

```python
FEEDBACK_ACKNOWLEDGMENT_PROMPT = """
You received prescriptive feedback identifying {num_errors} errors in your solution.

Before proceeding, please:

1. ACKNOWLEDGE: List the errors you will fix (in order of priority)
2. PLAN: For each error, briefly describe your repair strategy
3. COMMIT: Confirm you will generate an improved solution addressing all errors

Format:
## Acknowledgment
I will fix the following errors:
1. [Error type]: [1-sentence repair plan]
2. [Error type]: [1-sentence repair plan]
...

## Ready
I am ready to generate an improved solution.

Only after providing this acknowledgment should you proceed to generate your next solution attempt.
"""
```

**Expected impact**:
- Forces agent to process feedback before continuing
- Creates paper trail of feedback utilization
- Ensures agent doesn't skip over feedback

**Trade-off**: Adds latency (extra LLM call for acknowledgment)

---

### Recommended Approach: Hybrid (A + B)

**Combine**:
1. Add explicit feedback instructions (Option A) - no code change, immediate
2. Simplify delivery mechanism (Option B) - code change, better long-term

**Phase 1** (Immediate):
- Add PRESCRIPTIVE_FEEDBACK_INSTRUCTIONS to agent prompt
- Test with N=2 runs to verify iteration count improves

**Phase 2** (If Phase 1 insufficient):
- Implement separate feedback delivery (Option B)
- Add acknowledgment step (Option C) if needed

---

## Proposal 2: Simplify Prescriptive Feedback Format

### Problem Statement

**Observed**: Current prescriptive feedback is multi-page with complex template structures

**Example** (current format):
```
## Prescriptive Fix: Quantitative Bounds

**PRESCRIPTIVE REPAIR PLAN for Quantitative Bound Errors**

### **Context**
A quantitative claim (e.g., "at most 2 non‑sunny lines", "|Tₙ| ≤ 2ⁿ", ...) is false...

### **Required Actions**
> **Instructions:** Replace the placeholders (e.g., **[Section X.Y]**, **[Lemma Z]**, ...)

- [ ] **CRITICAL:** **Locate the false bound.**
  *In **[Section X.Y]**, locate the exact statement ...*
- [ ] **CRITICAL:** **Re‑derive the correct bound.**
  *Provide a complete, step‑by‑step derivation...*

[... continues for 50+ lines with multiple placeholders]
```

**Issues**:
1. Too verbose (50-100 lines per error)
2. Requires placeholder substitution (complex parsing)
3. Generic template language (not specific to actual error)
4. Unclear what agent should do with checklist items

### Proposed Solution

#### New Format: Short, Specific, Actionable (SSA)

**Design principles**:
1. **Short**: ≤10 lines per error (vs 50-100 currently)
2. **Specific**: Reference actual content from solution (no placeholders)
3. **Actionable**: Clear, concrete fix instructions (no generic templates)

**Template**:
```
ERROR {N}: {Error Type}
LOCATION: {Specific line/section from solution}
ISSUE: {What's wrong - 1 sentence}
FIX: {Specific action to take - 1-2 sentences}
EXAMPLE: {Optional: show correct version}
```

**Example** (new format):
```
ERROR 1: Quantitative Bound
LOCATION: Line 42 in your solution claims "at most n-2 non-sunny lines can exist"
ISSUE: This bound is too restrictive and leads to incorrect answer
FIX: Change bound to "at most n-1 non-sunny lines" and update proof in Section 3.2 to account for edge case where n=3
EXAMPLE: Correct statement: "Since each anti-diagonal requires one line and there are n+1 anti-diagonals, we need at least n+1 lines, but we only have n available, so at most n-1 can be non-sunny."
```

**Comparison**:

| Metric | Old Format | New Format | Improvement |
|--------|-----------|------------|-------------|
| **Length** | 50-100 lines | ≤10 lines | -80 to -90% |
| **Placeholders** | 5-10 per error | 0 | -100% |
| **Specificity** | Generic template | Actual solution content | Much higher |
| **Actionability** | Checklist to interpret | Direct instruction | Much clearer |

---

### Implementation Plan

**Step 1**: Create new feedback template generator

```python
def generate_ssa_feedback(error_type, error_context, solution_text):
    """
    Generate Short, Specific, Actionable feedback.

    Args:
        error_type: Type of error (e.g., "Quantitative Bound")
        error_context: Dict with error details from verification
        solution_text: The actual solution text

    Returns:
        Formatted SSA feedback string
    """
    # Extract specific location from solution
    location = find_error_location(error_context, solution_text)

    # Generate specific issue description
    issue = describe_specific_issue(error_context)

    # Generate actionable fix instruction
    fix = generate_fix_instruction(error_type, error_context)

    # Optional: Generate example of correct version
    example = generate_correct_example(error_type, error_context)

    feedback = f"""
ERROR: {error_type}
LOCATION: {location}
ISSUE: {issue}
FIX: {fix}
"""

    if example:
        feedback += f"EXAMPLE: {example}\n"

    return feedback
```

**Step 2**: Replace current template system

```python
# OLD (in adversarial_prompts.py or similar)
prescriptive_template = load_template("prescriptive_repair_plan.txt")
feedback = prescriptive_template.format(error_type=error_type, ...)

# NEW
feedback = generate_ssa_feedback(error_type, error_context, solution_text)
```

**Step 3**: Validate with human review

- Generate SSA feedback for 5-10 example errors
- Compare with old format
- Verify: Shorter, more specific, more actionable

---

### Example Transformations

**Before** (Quantitative Bound Error - 87 lines):
```
## Prescriptive Fix: Quantitative Bounds

**PRESCRIPTIVE REPAIR PLAN for Quantitative Bound Errors**

### **Context**
A quantitative claim (e.g., "at most 2 non‑sunny lines", ...) is false.

### **Required Actions**
> **Instructions:** Replace the placeholders...

- [ ] **CRITICAL:** **Locate the false bound.**
  *In **[Section X.Y]**, locate the exact statement...*

[... 80 more lines ...]
```

**After** (Quantitative Bound Error - 6 lines):
```
ERROR: Quantitative Bound
LOCATION: Section 3, Lemma 2 claims "at most n-2 non-sunny lines"
ISSUE: Bound too restrictive, excludes valid k=n-1 case
FIX: Re-derive bound using inclusion-exclusion on anti-diagonal coverage. Correct bound is ≤n-1.
EXAMPLE: "Each anti-diagonal needs coverage, and n lines can cover at most n anti-diagonals if one is non-sunny"
```

**Reduction**: 87 lines → 6 lines (93% shorter)

---

## Proposal 3: Stabilize API

### Problem Statement

**Observed**: 151 server errors per run (100% of runs affected)

**Error pattern**:
```
[RETRY] Error: 500 Server Error: Internal Server Error
[RETRY] Status code: 500
[RETRY] Retrying in 16.0 seconds...
```

**Impact**:
- Degrades LLM response quality
- Increases latency (16s retry delay × 151 = ~40 min wasted per run)
- Invalidates timing comparisons
- May cause truncated responses

### Root Cause Analysis

**Need to investigate**:
1. Is this a model endpoint issue (GPT-OSS API)?
2. Rate limiting (too many requests too fast)?
3. Timeout issues (requests taking too long)?
4. Payload size issues (requests too large)?
5. Network instability?

**Diagnostic steps**:
```bash
# Check error distribution in logs
grep "500 Server Error" ab_test_pilot/*/run_*.log | wc -l
# Result: 906 total errors across 6 runs = 151 per run

# Check retry timing pattern
grep -A 2 "500 Server Error" ab_test_pilot/control/run_1.log | grep "Retrying"
# Pattern: Exponential backoff (2s, 4s, 8s, 16s...)

# Check what endpoint is failing
grep -B 5 "500 Server Error" ab_test_pilot/control/run_1.log | grep "POST\|GET\|url"
# Need to identify: Which API calls are failing?
```

### Proposed Solutions

#### Option A: Improve Retry Logic (Short-term)

**Current**: Exponential backoff with fixed max retries

**Improved**:
```python
import time
import random

def api_call_with_smart_retry(endpoint, payload, max_retries=5):
    """
    Improved retry logic with jitter and circuit breaker.
    """
    consecutive_failures = 0

    for attempt in range(max_retries):
        try:
            response = make_api_call(endpoint, payload)

            if response.status_code == 200:
                consecutive_failures = 0  # Reset on success
                return response

            elif response.status_code == 500:
                consecutive_failures += 1

                # Circuit breaker: If 10 consecutive failures, wait longer
                if consecutive_failures >= 10:
                    wait_time = 60  # 1 minute pause
                    logger.warning(f"Circuit breaker: 10 consecutive failures, pausing {wait_time}s")
                else:
                    # Exponential backoff with jitter
                    wait_time = min(2 ** attempt, 32) + random.uniform(0, 2)

                logger.info(f"Retry {attempt+1}/{max_retries} after {wait_time:.1f}s")
                time.sleep(wait_time)

            elif response.status_code == 429:  # Rate limit
                wait_time = 60  # Respect rate limit
                logger.warning(f"Rate limited, waiting {wait_time}s")
                time.sleep(wait_time)

        except Exception as e:
            logger.error(f"API call exception: {e}")
            time.sleep(2 ** attempt)

    raise APIError(f"Failed after {max_retries} retries")
```

**Features**:
1. Jitter (random 0-2s) prevents thundering herd
2. Circuit breaker (pause after 10 failures)
3. Rate limit handling (429 status)
4. Capped exponential backoff (max 32s)

**Expected impact**: Reduces wasted time, but doesn't fix root cause

---

#### Option B: Switch to More Reliable Endpoint (Medium-term)

**Investigation needed**:
```python
# Test different endpoints
endpoints_to_test = [
    "http://localhost:30000/v1/chat/completions",  # Current (failing)
    "https://openrouter.ai/api/v1/chat/completions",  # OpenRouter (may be more stable)
    "https://api.openai.com/v1/chat/completions",  # OpenAI direct (if available)
]

def test_endpoint_stability(endpoint, num_calls=20):
    """
    Test endpoint with 20 calls, measure error rate.
    """
    errors = 0
    for i in range(num_calls):
        try:
            response = api_call(endpoint, test_payload)
            if response.status_code != 200:
                errors += 1
        except Exception as e:
            errors += 1

    error_rate = errors / num_calls
    print(f"{endpoint}: {error_rate:.1%} error rate")
    return error_rate
```

**Decision logic**:
- If localhost error rate > 10%: Switch to OpenRouter
- If OpenRouter error rate > 5%: Switch to OpenAI direct
- Target: <1% error rate

---

#### Option C: Reduce Request Load (Medium-term)

**Hypothesis**: 151 errors may be due to overwhelming the endpoint

**Solutions**:
1. **Add rate limiting**:
```python
import time
from threading import Lock

class RateLimiter:
    def __init__(self, max_calls_per_minute=30):
        self.max_calls = max_calls_per_minute
        self.calls = []
        self.lock = Lock()

    def wait_if_needed(self):
        with self.lock:
            now = time.time()
            # Remove calls older than 1 minute
            self.calls = [t for t in self.calls if now - t < 60]

            if len(self.calls) >= self.max_calls:
                # Wait until oldest call is 1 minute old
                wait_time = 60 - (now - self.calls[0])
                time.sleep(wait_time)

            self.calls.append(now)

# Usage
rate_limiter = RateLimiter(max_calls_per_minute=20)

def api_call_with_rate_limit(endpoint, payload):
    rate_limiter.wait_if_needed()
    return api_call(endpoint, payload)
```

2. **Batch requests** (if API supports):
```python
# Instead of 10 separate calls
for i in range(10):
    response = api_call(endpoint, payload_i)

# Batch into fewer calls
batched_payload = combine_payloads([payload_1, ..., payload_10])
response = api_call(endpoint, batched_payload)
```

3. **Cache responses** (for repeated queries):
```python
from functools import lru_cache
import hashlib

def cache_key(payload):
    return hashlib.sha256(str(payload).encode()).hexdigest()

response_cache = {}

def api_call_with_cache(endpoint, payload):
    key = cache_key(payload)
    if key in response_cache:
        return response_cache[key]

    response = api_call(endpoint, payload)
    response_cache[key] = response
    return response
```

---

#### Option D: Increase Timeout & Payload Limits (Short-term)

**Hypothesis**: Requests timing out or exceeding size limits

**Implementation**:
```python
import requests

# Current (implicit defaults)
response = requests.post(endpoint, json=payload)

# Improved (explicit timeouts and size handling)
response = requests.post(
    endpoint,
    json=payload,
    timeout=(30, 300),  # (connect timeout, read timeout) in seconds
    headers={
        'Content-Type': 'application/json',
        'Content-Length': str(len(json.dumps(payload)))
    }
)

# If payload too large, chunk it
if len(json.dumps(payload)) > 100_000:  # 100KB threshold
    response = send_chunked_request(endpoint, payload)
```

---

### Recommended Approach: Multi-pronged

**Phase 1** (Immediate - before next test):
1. Implement improved retry logic (Option A) - 1 hour
2. Add rate limiting (Option C.1) - 1 hour
3. Increase timeouts (Option D) - 30 min
4. **Test with N=2 runs**, target: <10 errors per run

**Phase 2** (If Phase 1 insufficient):
5. Test endpoint stability (Option B) - 2 hours
6. Switch to most stable endpoint - 1 hour
7. **Test with N=2 runs**, target: <5 errors per run

**Phase 3** (If Phase 2 insufficient):
8. Add response caching (Option C.3) - 2 hours
9. Implement request batching if supported (Option C.2) - 4 hours
10. **Test with N=2 runs**, target: <1 error per run

**Success criteria**: ≤1% error rate (i.e., <3 errors per 300 API calls)

---

## Implementation Timeline

### Week 1: Critical Fixes

**Day 1-2: Fix Early Termination**
- [ ] Add PRESCRIPTIVE_FEEDBACK_INSTRUCTIONS to agent prompt
- [ ] Test with N=2 runs (treatment should complete ≥10 iterations)
- [ ] If insufficient, implement Option B (separate feedback delivery)
- [ ] Deliverable: Treatment completes similar iterations as control

**Day 3-4: Simplify Feedback Format**
- [ ] Implement `generate_ssa_feedback()` function
- [ ] Replace current template system
- [ ] Generate examples for 10 error types, validate manually
- [ ] Deliverable: Feedback reduced to ≤10 lines per error

**Day 5: Stabilize API**
- [ ] Implement improved retry logic with circuit breaker
- [ ] Add rate limiting (20 calls/min)
- [ ] Increase timeouts
- [ ] Test with N=2 runs (target: <10 errors)
- [ ] Deliverable: Error rate reduced by 90%

### Week 2: Validation & Re-Pilot

**Day 6-7: Integration Testing**
- [ ] Run N=5 pilot with all three fixes applied
- [ ] Monitor: iteration counts, error rates, feedback utilization
- [ ] Deliverable: All metrics within acceptable ranges

**Day 8-9: Analysis**
- [ ] Success rate comparison (control vs treatment)
- [ ] Feedback utilization metrics
- [ ] Statistical analysis (is effect detectable with N=5?)
- [ ] Deliverable: GO/NO-GO decision for N=20 test

**Day 10: Decision Point**
- [ ] If GO: Plan N=20 full test
- [ ] If NO-GO: Iterate on fixes based on learnings
- [ ] Deliverable: Updated test plan or additional fix proposals

---

## Success Metrics

### Fix 1: Early Termination

**Current state**:
- Treatment: 0-1 iterations per run
- Control: 28 iterations per run
- Difference: 97% reduction

**Target state**:
- Treatment: ≥10 iterations per run
- Control: ~28 iterations per run (unchanged)
- Difference: ≤30% reduction (acceptable for efficiency gains)

**Measurement**: Count "Iteration X completed" in logs

---

### Fix 2: Feedback Format

**Current state**:
- Feedback length: 50-100 lines per error
- Placeholders: 5-10 per error
- Agent utilization: 0% (no evidence of reading/applying)

**Target state**:
- Feedback length: ≤10 lines per error
- Placeholders: 0 per error
- Agent utilization: ≥30% (evidence of applying fixes)

**Measurement**:
- Length: Count lines in prescriptive feedback sections
- Utilization: Grep logs for "fixing [error type]" or similar acknowledgments

---

### Fix 3: API Stability

**Current state**:
- Errors: 151 per run
- Error rate: ~50% (151 errors / ~300 API calls)
- Wasted time: ~40 min per run on retries

**Target state**:
- Errors: ≤3 per run
- Error rate: ≤1%
- Wasted time: <2 min per run

**Measurement**:
- Count: `grep "500 Server Error" run.log | wc -l`
- Rate: errors / total API calls
- Time: Sum of retry delays

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Fix 1 doesn't work** (agent still terminates early) | Medium | High | Have Options B & C ready as backups |
| **Simplified feedback loses quality** | Low | Medium | A/B test: complex vs simple format |
| **API issues are external** (can't fix) | Medium | High | Prepare to switch endpoints or providers |
| **Fixes introduce new bugs** | Medium | Medium | Test each fix independently before combining |
| **N=5 re-pilot still shows no effect** | High | Medium | May need to abandon prescriptive feedback approach |

---

## Open Questions for Expert Panel

1. **Early Termination Fix**:
   - Is adding instructions to the prompt sufficient, or do we need code changes?
   - Should we implement acknowledgment step (Option C) or is it overkill?
   - How do we detect if agent is actually reading the feedback?

2. **Feedback Format**:
   - Is 10 lines per error the right target, or should it be shorter/longer?
   - Should we include examples, or is that too much detail?
   - How do we generate "specific" feedback automatically?

3. **API Stability**:
   - What's the root cause of 151 errors (endpoint, rate limit, payload size)?
   - Is 1% error rate achievable, or should we target higher?
   - Should we switch endpoints proactively or only if local fails?

4. **Testing Strategy**:
   - Is N=5 re-pilot sufficient, or should we do N=10?
   - Should we test fixes sequentially or all at once?
   - What's the minimum success rate to justify scaling to N=20?

---

**END OF PROPOSALS - Awaiting Expert Panel Review**

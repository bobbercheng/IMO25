# Testing Guide: LLM Verification with agent_gpt_oss.py

**Status**: ✅ Integration Complete
**Date**: 2025-12-16
**Purpose**: Test new LLM-based verification system integrated into agent_gpt_oss.py

---

## What Was Integrated

The new 4-stage LLM verification pipeline is now integrated into `code/agent_gpt_oss.py` in the `validate_solution_with_counterexamples()` function. This function is automatically called during the verification step of the agent.

### Integration Details:

- **Location**: `code/agent_gpt_oss.py` lines 1028-1130
- **Function**: `validate_solution_with_counterexamples()`
- **Called by**: `verify_solution()` at line 1209
- **Fallback**: Automatically falls back to old validator if LLM verification fails

---

## Prerequisites

### 1. API Configuration

You need to configure the LLM API for verification. Choose one option:

#### Option A: OpenRouter (Recommended for Testing)

```bash
export GPT_OSS_API_URL=https://openrouter.ai/api/v1/chat/completions
export GPT_OSS_MODEL_NAME=openrouter/openai/gpt-oss-120b
export GPT_OSS_API_KEY=sk-or-your-openrouter-key
```

**Why OpenRouter?**
- ✅ Faster inference for medium/high reasoning
- ✅ No local deployment needed
- ✅ Pay-per-use ($0.08 per verification)
- ✅ Automatic failover

Get API key: https://openrouter.ai/

#### Option B: Local GPT-OSS Deployment

```bash
export GPT_OSS_API_URL=http://localhost:30000/v1/chat/completions
export GPT_OSS_MODEL_NAME=openai/gpt-oss-120b
export GPT_OSS_API_KEY=your_local_key  # Optional
```

### 2. Verification Configuration

```bash
# Enable LLM verification (default: true)
export USE_LLM_VERIFICATION=true

# Configure test cases (default: 3,4,5,10)
export LLM_VERIFY_TEST_CASES="3,4,5,10"

# If you want to disable and use old validator:
# export USE_LLM_VERIFICATION=false
```

---

## Test Scenarios

### Test 1: Verify BFS Log (Should Catch k=2 False Positive)

This test verifies that the new system catches the critical error in the BFS solution.

```bash
# Run agent on problem 1 with 3 initial attempts
python code/agent_gpt_oss.py problems/imo01.txt \
  --num-initial-attempts 3 \
  --solution-reasoning low \
  --log run_log_gpt_oss/test_llm_verify_bfs.log \
  --memory run_log_gpt_oss/test_llm_verify_bfs.json
```

**Expected Behavior:**

1. Agent generates solution claiming k ∈ {0,1,2,...,n}
2. Cooperative verification passes (algebraically consistent)
3. **New LLM verification runs** (COUNTEREXAMPLE VALIDATION)
4. **System detects k=2 is invalid** with concrete counterexample:
   ```
   [COUNTEREXAMPLE VALIDATION] ❌ FAILED (confidence: 95%, stage: stage3)
   COUNTEREXAMPLE: n=3, k=2 - Only 4 points covered (expected 6)
   Overriding verification from 'yes' to 'no'
   ```
5. Agent receives feedback and attempts to correct
6. Should eventually converge to correct answer k ∈ {0,1,3}

**What to Look For in Logs:**

```
>>>>>>> [COUNTEREXAMPLE VALIDATION] Checking mathematical validity
[COUNTEREXAMPLE] Using LLM verification pipeline (test cases: [3, 4, 5, 10])
[Stage 1] Extracting claims with LLM (low reasoning)...
[Stage 1] Extracted answer: ALL_VALUES
[Stage 2] Generating verification code with LLM (medium reasoning)...
[Stage 3] Executing verification code...
[Stage 3] Verdict: INVALID (confidence: 0.95)
[Stage 3] Evidence: COUNTEREXAMPLE: n=3, k=2 - ...
>>>>>>> [COUNTEREXAMPLE VALIDATION] ❌ FAILED (confidence: 95.0%, stage: stage3)
```

---

### Test 2: Verify Ground Truth Solution (Should Accept)

Test that the system accepts the correct IMO 2025 solution.

```bash
# Create a test file with ground truth solution
cat > /tmp/ground_truth_test.txt << 'EOF'
For every integer n ≥ 3, the admissible values of k are k ∈ {0, 1, 3}.

Construction for k=0:
Use n diagonal lines D_c: x+y=c for c=2,...,n+1.
All have slope -1 (non-sunny), so k=0 sunny lines.

Construction for k=1:
Use the sunny line y=x (slope 1) plus (n-1) diagonal lines.

Construction for k=3:
Use three sunny lines with distinct slopes plus (n-3) diagonal lines.

Why k=2 is impossible:
For n=3, with 3 lines total and 2 sunny lines required,
no valid configuration exists (proven by exhaustive analysis).

\boxed{\{0, 1, 3\}}
EOF

# Test with standalone verification
python code/llm_verification.py /tmp/ground_truth_test.txt \
  --problem problems/imo01.txt \
  --test-cases 3 4 5
```

**Expected Output:**

```
[Stage 1] Extracting claims with LLM (low reasoning)...
[Stage 1] Extracted answer: {0, 1, 3}
[Stage 2] Generating verification code with LLM (medium reasoning)...
[Stage 3] Executing verification code...
[Stage 3] Verdict: VALID (confidence: 0.75)

================================================================================
VERIFICATION RESULT
================================================================================
Verdict: VALID
Confidence: 75.0%
Stage: stage3

Evidence:
ALL_TESTS_PASSED
================================================================================
```

---

### Test 3: Quick Validation of Existing Log

Test the verification system on an already-completed solution:

```bash
# Extract solution from existing log and test it
python -c "
import sys
sys.path.append('code')
from agent_gpt_oss import validate_solution_with_counterexamples

# Read solution from log
with open('run_log_gpt_oss/bfs_revalidation_1.log', 'r') as f:
    content = f.read()

# Read problem
with open('problems/imo01.txt', 'r') as f:
    problem = f.read()

# Run validation
result = validate_solution_with_counterexamples(content, problem, verbose=True)

print(f'\n\n=== FINAL RESULT ===')
print(f'Verdict: {result[\"verdict\"]}')
print(f'Confidence: {result.get(\"confidence\", 0):.1%}')
print(f'Stage: {result.get(\"stage\", \"unknown\")}')
"
```

---

### Test 4: Full Agent Run with RLAC

Test the complete agent with RLAC mode enabled:

```bash
# Run agent with RLAC and new verification
python code/agent_gpt_oss.py problems/imo01.txt \
  --use-rlac \
  --rlac-max-rounds 10 \
  --solution-reasoning low \
  --rlac-critic-reasoning medium \
  --log run_log_gpt_oss/test_rlac_llm_verify.log \
  --memory run_log_gpt_oss/test_rlac_llm_verify.json
```

**Expected Behavior:**

1. RLAC generates adversarial attacks
2. Each solution iteration is verified with new LLM system
3. Concrete counterexamples guide refinement
4. Should converge faster to correct answer with actionable feedback

---

## Monitoring and Debugging

### Check if LLM Verification is Active

```bash
# Run agent and check logs
python code/agent_gpt_oss.py problems/imo01.txt --log test.log

# Check for LLM verification messages
grep -A 5 "Using LLM verification pipeline" test.log
```

**Expected output:**
```
[COUNTEREXAMPLE] Using LLM verification pipeline (test cases: [3, 4, 5, 10])
```

**If you see this instead:**
```
[COUNTEREXAMPLE] Using legacy pattern-matching validator
```

Then LLM verification is not active. Check:
1. Is `USE_LLM_VERIFICATION=true`?
2. Is `code/llm_verification.py` in the path?
3. Are API credentials configured?

### Check Fallback Behavior

```bash
# Disable LLM verification to test fallback
export USE_LLM_VERIFICATION=false
python code/agent_gpt_oss.py problems/imo01.txt --log test_fallback.log

# Verify it uses legacy validator
grep "Using legacy pattern-matching validator" test_fallback.log
```

### Debug API Issues

If verification fails with API errors:

```bash
# Test API connection directly
python -c "
import os
import sys
sys.path.append('code')
from llm_verification import LLMInterface

llm = LLMInterface()
response = llm.call('Say hello', reasoning='low')
print(f'API Response: {response}')
"
```

---

## Performance Monitoring

### Track Verification Costs

```bash
# Monitor cost per iteration
grep -o "Stage: stage[1-4]" test.log | sort | uniq -c
```

**Expected distribution:**
- ~70% should exit at Stage 3 (code execution)
- ~20% should exit at Stage 1 or 2 (extraction/generation)
- ~10% should need Stage 4 (LLM fallback)

**Average cost**: $0.05-0.11 per verification

### Track False Positive Reduction

```bash
# Count INVALID verdicts with high confidence
grep "FAILED (confidence: 9[0-9]\." test.log | wc -l
```

Compare with old validator:
```bash
# Old validator: benefit of doubt count
grep "benefit of doubt" old_test.log | wc -l
```

**Expected**: 20-50x fewer false positives

---

## Troubleshooting

### Issue 1: Import Error

```
ImportError: cannot import name 'VerificationPipeline' from 'llm_verification'
```

**Solution:**
```bash
# Verify file exists and is in path
ls -la code/llm_verification.py

# Add to Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)/code"

# Or use absolute imports
python -c "import sys; sys.path.append('code'); from llm_verification import VerificationPipeline"
```

### Issue 2: API Timeout

```
[COUNTEREXAMPLE] Warning: LLM verification failed (timeout)
```

**Solution:**
```bash
# Increase timeout (default: 120s)
# Edit code/llm_verification.py line ~237
# Change: timeout=120 to timeout=300

# Or switch to OpenRouter (faster)
export GPT_OSS_API_URL=https://openrouter.ai/api/v1/chat/completions
```

### Issue 3: Code Execution Fails

```
[Stage 3] Verdict: ERROR
Evidence: Execution error: ...
```

**Solution:**
```bash
# Check Python environment
python3 --version  # Should be 3.8+

# Install missing dependencies
pip install requests

# Check if subprocess execution works
python -c "import subprocess; print(subprocess.run(['echo', 'test'], capture_output=True).stdout)"
```

### Issue 4: Always Uses Legacy Validator

```
[COUNTEREXAMPLE] Using legacy pattern-matching validator
```

**Solution:**
```bash
# Check environment variable
echo $USE_LLM_VERIFICATION  # Should be "true" or empty

# Check if import works
python -c "import sys; sys.path.append('code'); from llm_verification import VerificationPipeline; print('OK')"

# Run with explicit flag
USE_LLM_VERIFICATION=true python code/agent_gpt_oss.py problems/imo01.txt --log test.log
```

---

## Expected Performance Improvements

### Metrics Comparison

| Metric | Old Validator | New LLM System | Your Results |
|--------|---------------|----------------|--------------|
| False Positive Rate | 100% | 2-5% | ___ % |
| True Positive Rate | ~60% | 90%+ | ___ % |
| Cost per Verification | $0.08 | $0.10-0.15 | $ ___ |
| Average Time | 30s | 45-60s | ___ s |
| Stage 3 Exit Rate | N/A | 70%+ | ___ % |

### Test Checklist

- [ ] API configured and tested
- [ ] Test 1: BFS false positive detected
- [ ] Test 2: Ground truth solution accepted
- [ ] Test 3: Existing log validated
- [ ] Test 4: Full RLAC run completed
- [ ] Logs show "Using LLM verification pipeline"
- [ ] Concrete counterexamples in feedback
- [ ] False positive rate < 10%
- [ ] Cost per verification < $0.15

---

## Quick Start (Minimal Test)

If you just want to verify the integration works:

```bash
# 1. Configure API
export GPT_OSS_API_URL=https://openrouter.ai/api/v1/chat/completions
export GPT_OSS_MODEL_NAME=openrouter/openai/gpt-oss-120b
export GPT_OSS_API_KEY=your_key

# 2. Enable LLM verification
export USE_LLM_VERIFICATION=true

# 3. Run quick test (3 attempts, should finish in ~5 minutes)
python code/agent_gpt_oss.py problems/imo01.txt \
  --num-initial-attempts 3 \
  --solution-reasoning low \
  --log test_quick.log

# 4. Check if LLM verification was used
grep "Using LLM verification pipeline" test_quick.log
grep "Stage: stage" test_quick.log

# 5. Check for counterexample detection
grep -A 3 "COUNTEREXAMPLE" test_quick.log
```

**Expected time**: 5-10 minutes
**Expected cost**: $0.50-1.00
**Success criteria**: See "Using LLM verification pipeline" in logs

---

## Advanced Configuration

### Custom Test Cases

```bash
# Test with larger n values for thorough validation
export LLM_VERIFY_TEST_CASES="3,5,10,20"

# Test with minimal cases for faster iteration
export LLM_VERIFY_TEST_CASES="3,4"
```

### Mixed Verification Strategy

```bash
# Use new verification for final check only
# Edit agent_gpt_oss.py line 1203 to:
# if "yes" in o.lower() and iteration >= max_iterations - 2:
#     # Only use expensive LLM verification on final iterations
```

### Debugging Output

```bash
# Run with verbose Python warnings
python -W all code/agent_gpt_oss.py problems/imo01.txt --log debug.log 2>&1 | tee debug_stderr.log

# Check all verification stages
grep -E "Stage [1-4]|COUNTEREXAMPLE|verdict" debug.log
```

---

## Next Steps After Testing

1. **If tests pass**: Document performance metrics and enable by default
2. **If tests fail**: Review logs, check API configuration, report issues
3. **If performance is good**: Consider adding more problem templates
4. **If cost is high**: Tune reasoning levels or adjust test cases

---

## Support

**Issues**: Report to repository issues with logs
**Documentation**: See `LLM_VERIFICATION_IMPLEMENTATION.md`
**Code**: `code/llm_verification.py` and `code/agent_gpt_oss.py`

**Key Log Patterns to Search:**
- `Using LLM verification pipeline` - System is active
- `Stage: stage3` - Most efficient path (code execution)
- `COUNTEREXAMPLE: n=X, k=Y` - Concrete error found
- `confidence: 9X%` - High-confidence result
- `Falling back to pattern-matching` - System unavailable

---

**End of Testing Guide**

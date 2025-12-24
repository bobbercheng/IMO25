# RLAC Test Non-Determinism: Executive Action Plan

## 🚨 CRITICAL FINDINGS

**Problem:** RLAC verification system shows 5x variance (16.7% - 83.3%) on identical code
**Root Cause:** LLM API non-determinism + fragile keyword parsing
**Impact:** TRUE accuracy is 41.7%, not the 66.7% we thought
**Severity:** CATASTROPHIC - Cannot trust single-run results

---

## ROOT CAUSES IDENTIFIED

### 1. LLM API Non-Determinism (PRIMARY)
```
Identical Input (temp=0.0, seed=42)
    ↓
OpenRouter/GPT-OSS-120b
    ↓
Different Outputs:
  • Empty response (0 chars)
  • Brief summary (~1000 chars)
  • Detailed analysis (~10,000 chars)
```

**Evidence:**
- Test 1 Run 2: Empty response → PASS
- Test 1 Run 3: 10KB analysis finding "Justification Gaps" → FAIL

### 2. Fragile Keyword Parsing (SECONDARY)
```
Same Verdict Content
    ↓
"rather than fatal logical errors" → PASS
"rather than Critical Errors" → FAIL
    ↓
Test Result Flip
```

**Evidence:**
- Test 2 Run 2 vs Run 3: Nearly identical verdicts, opposite results

---

## STATISTICAL REALITY CHECK

### Before This Analysis
- **Believed:** 66.7% accuracy (based on lucky runs)
- **Expected:** Tests 1&2 should always PASS (100%)

### After This Analysis
- **Reality:** 41.7% ± 15.3% accuracy (95% CI: 26.4% - 57.0%)
- **Reality:** Tests 1&2 PASS only 41.7% of the time
- **Reality:** Most common outcome is 16.7% (1/6)

### Distribution
```
Accuracy    Frequency    Probability
16.7%       5/12 runs    41.7% ← MOST COMMON!
33.3%       2/12 runs    16.7%
50.0%       1/12 runs     8.3%
66.7%       2/12 runs    16.7%
83.3%       2/12 runs    16.7%
```

**Translation:** If you run the test once:
- 42% chance you'll get 16.7% (worst)
- 17% chance you'll get 83.3% (best)
- Mean: 41.7%

---

## IMMEDIATE ACTIONS (THIS WEEK)

### Priority 1: Stop Single-Run Decisions
- [ ] **HALT** all design decisions based on single test runs
- [ ] **REQUIRE** minimum 10 runs for any conclusion
- [ ] **REPORT** mean ± 95% CI, not single-run results
- [ ] **FLAG** any previous research based on single runs

### Priority 2: Fix Empty Response Handling
- [ ] Modify verification code to detect empty LLM responses
- [ ] Change behavior: Empty response → FAIL (or retry 3x)
- [ ] Add logging: Track all empty responses with timestamps
- [ ] Investigate: Why is LLM returning empty content?

### Priority 3: Improve Parsing Robustness
- [ ] Replace keyword matching with structured output
- [ ] Force LLM to return JSON schema:
  ```json
  {
    "verdict": "CORRECT" | "INCORRECT" | "INCOMPLETE",
    "has_critical_error": true | false,
    "has_justification_gap": true | false,
    "reasoning": "..."
  }
  ```
- [ ] Validate JSON schema before parsing
- [ ] Add fallback: If JSON invalid → Ask second LLM to classify

---

## SHORT-TERM ACTIONS (THIS MONTH)

### Priority 4: Investigate API Non-Determinism
```python
# Test script
for i in range(100):
    response = call_openrouter(
        prompt=FIXED_PROMPT,
        temperature=0.0,
        seed=42
    )
    log_response_length(response)
    log_response_hash(response)

# Analyze
variance = calculate_variance(response_lengths)
unique_responses = count_unique_hashes()

if unique_responses > 1:
    print("❌ API is NON-DETERMINISTIC despite seed=42")
else:
    print("✅ API is deterministic")
```

### Priority 5: Implement Ensemble Testing
```python
def evaluate_system(config, num_runs=10):
    results = []
    for run in range(num_runs):
        accuracy = run_test_suite(config)
        results.append(accuracy)

    mean = np.mean(results)
    std = np.std(results, ddof=1)
    ci_95 = 1.96 * std / np.sqrt(num_runs)

    return {
        'mean': mean,
        'std': std,
        'ci_95': (mean - ci_95, mean + ci_95),
        'min': np.min(results),
        'max': np.max(results),
        'all_results': results
    }

# Example usage
baseline = evaluate_system(current_config, num_runs=20)
improved = evaluate_system(new_config, num_runs=20)

# Statistical test
p_value = paired_ttest(baseline['all_results'], improved['all_results'])
if p_value < 0.05:
    print(f"✅ Improvement is statistically significant (p={p_value:.4f})")
else:
    print(f"❌ Improvement is NOT significant (p={p_value:.4f})")
```

### Priority 6: Re-Validate Previous Research
- [ ] List all experiments from past 3 months
- [ ] For each experiment:
  - How many runs were performed?
  - Was variance reported?
  - What was the effect size?
- [ ] Re-run critical experiments with 10+ runs
- [ ] Update research conclusions with confidence intervals

---

## LONG-TERM ACTIONS (NEXT QUARTER)

### Priority 7: Switch to Deterministic Backend
**Options:**
1. **Local vLLM inference**
   - Pros: True determinism, full control
   - Cons: Slower, requires GPU infrastructure

2. **OpenAI API with structured outputs**
   - Pros: Built-in JSON schema support
   - Cons: Still proprietary, may have latency

3. **Anthropic Claude with tool use**
   - Pros: Strong reasoning, structured outputs
   - Cons: Different model, need retuning

**Recommendation:** Start with vLLM for validation experiments, then decide.

### Priority 8: System Redesign
```python
class DeterministicVerifier:
    def __init__(self, backend='vllm', num_retries=3):
        self.backend = backend
        self.num_retries = num_retries

    def verify(self, solution: str) -> VerificationResult:
        for attempt in range(self.num_retries):
            # Force JSON schema
            response = self.llm.generate(
                prompt=self.build_prompt(solution),
                output_schema=VERIFICATION_SCHEMA,
                temperature=0.0,
                seed=42
            )

            # Validate schema
            if not self.validate_schema(response):
                continue

            # Detect conflicts
            if response['verdict'] == 'CORRECT' and response['has_critical_error']:
                # Inconsistency detected
                response = self.resolve_conflict(solution, response)

            return VerificationResult(
                verdict=response['verdict'],
                critical_errors=response['critical_errors'],
                justification_gaps=response['justification_gaps'],
                confidence=response['confidence']
            )

        # All retries failed
        return VerificationResult(verdict='UNKNOWN', confidence=0.0)
```

---

## SUCCESS METRICS

### Short-Term (1 Month)
- [ ] **Variance Reduction:** Std dev < 10% (currently 27%)
- [ ] **Empty Response Rate:** < 1% (currently ~8%)
- [ ] **Test 1&2 Pass Rate:** > 95% (currently 41.7%)
- [ ] **Re-validation:** 100% of past experiments re-run with ensembles

### Long-Term (3 Months)
- [ ] **Determinism:** Same input → Same output (100% reproducibility)
- [ ] **Robustness:** No test result flips due to wording changes
- [ ] **Efficiency:** Ensemble of 10 runs in < 10 minutes
- [ ] **Confidence:** All research conclusions have 95% CI reported

---

## COMMUNICATION PLAN

### Internal Team
- **Today:** Share FINAL_ROOT_CAUSE_ANALYSIS.md with team
- **This Week:** Hold emergency meeting to discuss action plan
- **Weekly:** Progress updates on variance reduction

### Research Community
- **After Fixes:** Publish "Lessons Learned: Non-Determinism in LLM Evaluation"
- **Include:** Open-source reproduction code, variance analysis tools
- **Impact:** Help others avoid same pitfall

---

## LESSONS LEARNED

### What Went Wrong
1. **Trusted single-run results** without checking variance
2. **Assumed temperature=0, seed=42** guaranteed determinism
3. **Used keyword parsing** instead of structured outputs
4. **Didn't log empty responses** as anomalies

### What To Do Differently
1. **Always run ensembles** (minimum 10 runs)
2. **Always report variance** (mean ± 95% CI)
3. **Always use structured outputs** (JSON schema)
4. **Always validate API behavior** (don't trust documentation)
5. **Always detect anomalies** (empty responses, timeouts)

### Scientific Principle
> "If you torture the data long enough, it will confess to anything."
> — Ronald Coase

**Corollary for LLM Research:**
> "If you run the test once, you'll believe whatever it tells you.
> Run it 100 times, and you'll see the truth."

---

## CONCLUSION

This analysis reveals that the RLAC verification system has **41.7% true accuracy**, not the 66.7% we believed. The 5x variance (16.7% - 83.3%) makes single-run results **COMPLETELY UNRELIABLE**.

**Immediate Actions Required:**
1. Stop single-run decisions
2. Fix empty response handling
3. Implement structured outputs
4. Re-validate previous research

**Long-Term Goal:**
Build a deterministic, robust verification system that produces:
- **Same output for same input** (reproducibility)
- **<5% variance across runs** (reliability)
- **>95% accuracy on complete proofs** (validity)

**Timeline:**
- Week 1: Immediate fixes (empty responses, ensemble testing)
- Month 1: API investigation, re-validation
- Quarter 1: System redesign, deterministic backend

**Success Criteria:**
When we can confidently say: "This system has X% accuracy ± Y% (95% CI), measured over N runs, with p < 0.05 statistical significance."

Until then, **DO NOT TRUST SINGLE-RUN RESULTS.**

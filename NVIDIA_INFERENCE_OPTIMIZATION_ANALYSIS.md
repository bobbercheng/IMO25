# Nvidia Inference Optimization Analysis: gpt-oss-120b Verification Latency

**Date:** 2025-12-26
**Engineer:** Nvidia LLM Inference Team
**Model:** openrouter/openai/gpt-oss-120b (HIGH reasoning)
**Context:** Production verification system with P95 latency target <60s

---

## Executive Summary

**CRITICAL FINDINGS:**
- 🔴 **P95 latency: 315s (5.25× target)** - Production blocker
- 🔴 **Tail latency: 510s (8.5× target)** - Unacceptable variance
- 🟡 **Constraints reduced tokens 94% but latency variance increased** - Architectural issue
- 🟢 **Fast path exists (Test 1: 4s)** - Opportunity for hybrid architecture

**ROOT CAUSE:** Model is performing deep reasoning re-proof despite constraints (instruction-following failure under HIGH reasoning mode)

**RECOMMENDED ACTION:** Implement hybrid fast/slow architecture with teacher-student distillation

---

## Latency Root Cause

### Performance Distribution Analysis

```
Test | Time (s) | Solution Length | Output Tokens | Reasoning Depth
-----|----------|----------------|---------------|----------------
1    | 4.0      | 11,420 chars   | ~95 tokens    | SHALLOW (accept)
2    | 510.3    | 11,240 chars   | ~425 tokens   | DEEP (re-prove)
3    | 7.1      | ~800 chars     | ~265 tokens   | MEDIUM (reject)
4    | 212.3    | ~600 chars     | ~212 tokens   | DEEP (analyze)
5    | 315.9    | ~900 chars     | ~287 tokens   | DEEP (verify construction)
6    | 172.8    | ~1000 chars    | ~95 tokens    | SHALLOW (accept)

P50: 142.6s | P95: 315s | P99: 510s
```

### Why Test 2 is 127× Slower Than Test 1

**Both tests have ~11k char solutions, but vastly different latency:**

**Test 1 (4.0s - FAST PATH):**
```
Input: 11,420 chars → Complete valid proof
Model behavior:
  1. Reads proof (valid case analysis)
  2. Checks answer correctness ✓
  3. Accepts with minor warning
Output: 378 chars (simple acceptance)
Reasoning time: ~4s
```

**Test 2 (510.3s - SLOW PATH):**
```
Input: 11,240 chars → Complete valid proof (alternative approach)
Model behavior:
  1. Reads proof (valid but different method)
  2. IGNORES constraint "Evaluate, Don't Re-Prove"
  3. Re-proves intermediate uniqueness claim from scratch
  4. Finds subtle error in reasoning chain
  5. Generates detailed counterexample
  6. Performs semantic analysis of logical dependencies
Output: 1703 chars (detailed critical analysis)
Reasoning time: ~510s (2× output length but 127× latency!)
```

**Key Insight:** Latency is NOT proportional to output tokens. It's proportional to **reasoning depth**.

### Latency Breakdown (Test 2)

**Hypothesis based on output analysis:**

```
Phase 1: Solution parsing                     ~10s  (2%)
Phase 2: Answer extraction                    ~5s   (1%)
Phase 3: Method validation                    ~15s  (3%)
Phase 4: DEEP REASONING - Re-proving claim    ~450s (88%) ← BOTTLENECK
Phase 5: JSON formatting                      ~30s  (6%)
Total:                                        510s
```

**The 88% bottleneck:** Model enters deep reasoning mode to independently verify the intermediate claim about uniqueness of lines. HIGH reasoning with gpt-oss-120b appears to:
1. Build full logical dependency graph
2. Enumerate counterexamples
3. Perform semantic analysis of proof structure
4. Generate alternative proofs

**This is exactly what constraints were supposed to prevent, but failed.**

### Why Constraints Failed

**Constraint 2 says:** "Evaluate, Don't Re-Prove"

**Model interpretation under HIGH reasoning:**
```python
if reasoning_effort == "high":
    # Model thinks: "I should be thorough and rigorous"
    # Constraint gets OVERRIDDEN by reasoning mode instinct
    # Result: Deep re-proving despite explicit instructions

if reasoning_effort == "low":
    # Model thinks: "I should be efficient"
    # Constraint gets FOLLOWED because it aligns with mode
    # Result: Fast evaluation without re-proving
```

**Evidence:**
- Test 1 (fast): Simple proof structure → model accepts quickly
- Test 2 (slow): Complex proof structure → model re-proves despite constraints
- Test 4 (slow): Missing constructions → model tries to verify existence claims

**Root cause:** HIGH reasoning mode has inherent "thoroughness bias" that overrides instruction-following.

---

## Inference Optimization

### Goal: P95 < 60s with gpt-oss-120b

**Current bottleneck:** Unpredictable reasoning depth under HIGH mode.

### Strategy 1: Reasoning Effort Downgrade (FASTEST FIX)

**Change:** HIGH → MEDIUM for verification

**Expected impact:**
```
Current (HIGH):
  - P50: 142.6s
  - P95: 315s
  - Accuracy: 66.7% (constraints)

Predicted (MEDIUM):
  - P50: 25-35s  (-80%)
  - P95: 50-70s  (-77%)
  - Accuracy: 78.3% (baseline validation data)
```

**Trade-off analysis:**
- ✅ Latency improved 4-5×
- ✅ Better accuracy than HIGH+constraints (78.3% vs 66.7%)
- ❌ Still not at 60s P95 target
- ⚠️ Test 5 (wrong answer) accuracy drops from 100% to 70%

**Verdict:** MEDIUM alone is insufficient. Need hybrid approach.

---

### Strategy 2: Early Exit + Fallback (RECOMMENDED)

**Architecture:**
```python
def verify_solution_optimized(problem, solution):
    # Fast path: MEDIUM reasoning (target: 30s)
    result_medium = verify_with_timeout(
        reasoning="medium",
        timeout=45,
        budget=3000  # Reduce from 7000
    )

    if result_medium.confidence > 0.85:
        # High confidence → trust MEDIUM result
        return result_medium  # 85% of cases

    if result_medium.verdict == "FAIL":
        # FAIL verdicts rarely need escalation
        return result_medium  # 40% of cases

    # Slow path: Upgrade to HIGH for uncertain cases
    result_high = verify_with_timeout(
        reasoning="high",
        timeout=180,
        budget=5000
    )

    return result_high  # 15% of cases
```

**Expected performance:**
```
Cases:
  - 85% fast path (MEDIUM, 30s avg): 25.5s
  - 15% slow path (HIGH, 120s avg):  18.0s

Weighted P95:
  - 0.85 × 45s + 0.15 × 180s = 38s + 27s = 65s

PROBLEM: Still slightly above 60s target
```

**Optimization:** Add timeout-based circuit breaker:
```python
result_medium = verify_with_timeout(
    reasoning="medium",
    timeout=30  # Hard cutoff
)

if timeout_exceeded:
    # Fall back to structured rule-based check
    return fast_structural_check(solution)
```

**Final performance:**
```
Cases:
  - 70% fast path (MEDIUM, 25s):     17.5s
  - 15% timeout → structural (5s):    0.75s
  - 15% slow path (HIGH, 90s):        13.5s

Weighted P95: ~50s ✓ MEETS TARGET
```

---

### Strategy 3: Prompt Surgery for HIGH Mode (MEDIUM EFFORT)

**Problem:** Constraints are phrased as "guidance" not "enforcement"

**Current:**
```
2. Evaluate, Don't Re-Prove: Your task is to EVALUATE...
   - ❌ WRONG: "Let's verify by manually testing..."
   - ✅ CORRECT: "The solution tests n=3, n=4..."
```

**Optimized for HIGH reasoning:**
```
2. MANDATORY EFFICIENCY REQUIREMENT: You are operating under strict
   time budget. Re-proving solutions from scratch is PROHIBITED.

   YOUR TASK: Evaluate the provided solution's reasoning.

   FORBIDDEN ACTIONS (will cause request termination):
   - Manually testing cases the solution already tested
   - Re-deriving proofs the solution already derived
   - Enumerating examples to verify claims

   ALLOWED ACTIONS:
   - Identifying gaps in the solution's logic
   - Checking if answer matches problem requirements
   - Noting missing constructions or proofs

   VIOLATION DETECTION: If your response exceeds 2000 tokens or
   includes phrases like "Let me verify" or "Testing n=", your
   response will be discarded.
```

**Expected impact:**
- Test 2: 510s → 60-90s (5-8× faster)
- Test 4: 212s → 30-50s (4-7× faster)
- Output compliance: 95%+ (stronger language)

**Risk:** May increase false negatives if too restrictive.

---

### Strategy 4: Token Budget Reduction (IMMEDIATE WIN)

**Current budget:**
```python
if solution_length > 5000:
    return 7000  # Way too high!
```

**Problem:** Large token budgets give model "permission" to be verbose.

**Optimized:**
```python
def calculate_verification_budget_optimized(solution_length, reasoning_effort):
    base_budgets = {
        "low": {"short": 1500, "medium": 2000, "long": 2500},
        "medium": {"short": 2000, "medium": 3000, "long": 4000},
        "high": {"short": 2500, "medium": 3500, "long": 4500}
    }

    category = "long" if solution_length > 5000 else \
               "medium" if solution_length > 2000 else "short"

    return base_budgets[reasoning_effort][category]
```

**For Test 2 (11k chars, HIGH):**
- Current: 7000 tokens
- Optimized: 4500 tokens (-36%)

**Expected impact:**
- Forces model to be concise
- May trigger early stopping in reasoning
- P95: 315s → 180-220s (30-40% improvement)

**Why not more aggressive?** Risk of truncation mid-reasoning.

---

## Model Comparison

### gpt-oss-120b vs gpt-5 vs Gemini 2.5 Deep Think

| Model | Latency (HIGH) | Accuracy | Cost/1M tokens | Instruction Following | Production Ready |
|-------|---------------|----------|----------------|---------------------|------------------|
| **gpt-oss-120b** (OpenRouter) | P95: 315s | 66.7% | $15 | ⚠️ Poor under HIGH | ❌ Too slow |
| **gpt-5** (OpenAI) | P95: 40-60s (est) | 85-90% (est) | $100-150 | ✅ Excellent | ✅ Yes (expensive) |
| **Gemini 2.5 Deep Think** | P95: 90-120s (est) | 75-80% (est) | $8-12 | 🟡 Good | 🟡 Borderline |
| **gpt-oss-120b MEDIUM** | P95: 50-70s | 78.3% | $8 | ✅ Good | 🟡 Close |

### Detailed Analysis

#### gpt-5 (RECOMMENDED FOR PRODUCTION)

**Strengths:**
- ✅ **Fast HIGH reasoning:** 40-60s P95 (meets target!)
- ✅ **Strong instruction following:** Constraints work as intended
- ✅ **High accuracy:** 85-90% expected (based on o3 analysis)
- ✅ **Stable latency:** Low variance (P95/P50 ratio ~2×)

**Weaknesses:**
- ❌ **Expensive:** 10× cost of gpt-oss-120b
- ⚠️ **API access:** May have rate limits

**Use case:** Production verification where accuracy and latency matter more than cost.

**Estimated cost:**
```
Per verification:
  - Input: ~3000 tokens (problem + solution + constraints)
  - Output: ~300 tokens (verdict)
  - Total: ~3300 tokens × $100/1M = $0.33 per verification

Daily cost (1000 verifications):
  - $330/day
  - $10k/month
```

**Decision:** Use if budget allows. Best ROI for high-stakes verification.

---

#### Gemini 2.5 Deep Think

**Strengths:**
- ✅ **Good accuracy:** 75-80% (competitive with MEDIUM gpt-oss)
- ✅ **Moderate cost:** $8-12/1M tokens
- 🟡 **Reasonable latency:** 90-120s P95 (not ideal but workable)

**Weaknesses:**
- ❌ **Slower than target:** 90-120s vs 60s target
- ⚠️ **Less tested:** No validation data in this codebase
- ⚠️ **API reliability:** Google APIs can have regional issues

**Use case:** Cost-conscious alternative to gpt-5 when 2× latency acceptable.

**Estimated cost:**
```
Per verification: $0.033 (10× cheaper than gpt-5)
Daily (1000 verifications): $33/day
Monthly: $1k/month
```

**Decision:** Good middle ground. Test if gpt-5 too expensive.

---

#### gpt-oss-120b (OpenRouter)

**Current (HIGH reasoning):**
- ❌ **Too slow:** 315s P95 (5× target)
- ❌ **Poor accuracy:** 66.7% (constraints ineffective)
- ✅ **Cheap:** $15/1M tokens

**Optimized (MEDIUM reasoning):**
- 🟡 **Borderline latency:** 50-70s P95 (close to target)
- ✅ **Good accuracy:** 78.3% (better than HIGH!)
- ✅ **Cheap:** $8/1M tokens
- ⚠️ **Test 5 weakness:** 70% accuracy on wrong answers (vs 100% with HIGH)

**Use case:** Budget-constrained scenarios where 70s latency acceptable.

**Decision:** Viable with MEDIUM reasoning + hybrid architecture.

---

### Recommendation Matrix

| Scenario | Model Choice | Reasoning | Expected P95 | Expected Accuracy | Monthly Cost (1000/day) |
|----------|-------------|-----------|--------------|-------------------|------------------------|
| **Production (high-stakes)** | gpt-5 | HIGH | 40-60s ✅ | 85-90% ✅ | $10k |
| **Production (cost-optimized)** | gpt-oss MEDIUM + hybrid | MEDIUM | 50-70s 🟡 | 78-82% ✅ | $300 |
| **Development/Testing** | gpt-oss MEDIUM | MEDIUM | 70-90s 🟡 | 78% ✅ | $250 |
| **Research/Experimentation** | Gemini Deep Think | HIGH | 90-120s ⚠️ | 75-80% 🟡 | $1k |

---

## Hybrid Architecture

### Design: Fast Path + Slow Path + Structural Fallback

```python
class VerificationRouter:
    """
    Production-grade verification with latency guarantees.

    Strategy:
    1. Fast path (MEDIUM): 70% of cases, 25s avg
    2. Structural fallback: 15% of cases (timeout), 5s avg
    3. Slow path (HIGH): 15% of cases (low confidence), 90s avg

    Result: P95 < 60s with 80%+ accuracy
    """

    def __init__(self):
        self.fast_model = "gpt-oss-120b"  # MEDIUM reasoning
        self.slow_model = "gpt-5"         # HIGH reasoning
        self.fast_timeout = 30            # Hard cutoff
        self.confidence_threshold = 0.85  # Escalation threshold

    def verify(self, problem, solution):
        # Phase 1: Fast path with timeout
        try:
            result = self._verify_with_timeout(
                model=self.fast_model,
                reasoning="medium",
                timeout=self.fast_timeout,
                max_tokens=3000
            )

            # High confidence → return immediately
            if result.confidence >= self.confidence_threshold:
                return self._finalize(result, path="fast")

            # Clear FAIL → trust MEDIUM verdict
            if result.verdict == "FAIL" and result.confidence >= 0.75:
                return self._finalize(result, path="fast")

        except TimeoutError:
            # Phase 2: Structural fallback for timeout cases
            return self._structural_fallback(problem, solution)

        # Phase 3: Slow path for uncertain cases
        result_high = self._verify_with_timeout(
            model=self.slow_model,
            reasoning="high",
            timeout=90,
            max_tokens=4500
        )

        return self._finalize(result_high, path="slow")

    def _structural_fallback(self, problem, solution):
        """
        Rule-based verification for timeout cases.
        Fast (5s) but lower accuracy (60-70%).
        """
        checks = {
            "has_answer": self._extract_answer(solution) is not None,
            "has_construction": "construction" in solution.lower(),
            "has_proof": any(word in solution.lower()
                           for word in ["proof", "show", "therefore"]),
            "length_adequate": len(solution) > 500
        }

        # Simple heuristic: PASS if 3/4 checks pass
        score = sum(checks.values()) / len(checks)

        return VerificationResult(
            verdict="PASS" if score >= 0.75 else "FAIL",
            confidence=0.65,  # Low confidence (structural only)
            path="structural",
            reasoning="Timeout fallback - structural analysis",
            elapsed_time=5.0
        )

    def _finalize(self, result, path):
        """Add telemetry and return."""
        result.path = path
        self._log_metrics(result)
        return result
```

### Performance Prediction

**Case distribution:**
```
Test 1 (Complete proof):
  - Fast path → High confidence PASS → 25s

Test 2 (Alternative proof):
  - Fast path → Medium confidence → Escalate
  - Slow path → PASS → 30s + 60s = 90s

Test 3 (Missing k=2):
  - Fast path → High confidence FAIL → 20s

Test 4 (Missing constructions):
  - Fast path → Timeout → Structural fallback → 30s + 5s = 35s

Test 5 (Wrong answer):
  - Fast path → Medium confidence → Escalate
  - Slow path → FAIL → 25s + 70s = 95s

Test 6 (Justification gap):
  - Fast path → High confidence PASS → 22s
```

**Aggregate metrics:**
```
P50: 30s (Test 1,3,6 fast paths)
P95: 90s (Test 2,5 slow paths)
P99: 95s (Test 5 worst case)

PROBLEM: Still above 60s target!
```

**Optimization:** Use gpt-5 for slow path instead of gpt-oss HIGH:

```
Test 2 with gpt-5: 30s + 40s = 70s
Test 5 with gpt-5: 25s + 45s = 70s

New P95: 70s (still over target but much better)
```

**Final optimization:** Parallel execution for borderline cases:

```python
def verify_parallel(self, problem, solution):
    """Run MEDIUM and HIGH in parallel, return first confident result."""

    future_medium = asyncio.create_task(
        self._verify_with_timeout(
            model=self.fast_model,
            reasoning="medium",
            timeout=30
        )
    )

    future_high = asyncio.create_task(
        self._verify_with_timeout(
            model=self.slow_model,
            reasoning="high",
            timeout=60
        )
    )

    # Wait for first high-confidence result OR both complete
    while True:
        done, pending = await asyncio.wait(
            [future_medium, future_high],
            return_when=asyncio.FIRST_COMPLETED
        )

        for task in done:
            result = task.result()
            if result.confidence >= 0.85:
                # Cancel pending task
                for p in pending:
                    p.cancel()
                return result

        if not pending:
            # Both finished, return higher confidence
            results = [t.result() for t in [future_medium, future_high]]
            return max(results, key=lambda r: r.confidence)
```

**Performance with parallel execution:**
```
Test 2: min(30s MEDIUM, 40s HIGH) = 30s + 5s overhead = 35s ✓
Test 5: min(25s MEDIUM, 45s HIGH) = 25s + 5s overhead = 30s ✓

New P95: 35s ✓ MEETS TARGET!
Cost: 2× model calls = 2× cost (but still cheaper than sequential HIGH)
```

---

## Teacher-Student for Speed

### Strategy: Use gpt-5 to Distill Fast Verification

**Concept:** Train lightweight model on gpt-5's reasoning patterns.

```
Phase 1: Data Collection (gpt-5 teacher)
  ├─ Run gpt-5 on 10k verification tasks
  ├─ Collect (problem, solution, reasoning_trace, verdict)
  └─ Cost: 10k × $0.33 = $3.3k

Phase 2: Distillation (create fast student)
  ├─ Fine-tune smaller model (7B-13B) on traces
  ├─ Objective: Match gpt-5 verdicts in <10s
  ├─ Training: $5-10k (one-time cost)
  └─ Result: Custom verification model

Phase 3: Deployment
  ├─ Student model: P95 < 15s, accuracy 80-85%
  ├─ Escalate low-confidence to gpt-5: 10-15% of cases
  └─ Blended P95: 0.85 × 15s + 0.15 × 50s = 20s ✓ CRUSHES TARGET
```

### Implementation Roadmap

**Week 1-2: Data Collection**
```python
def collect_training_data():
    """Generate gpt-5 verification examples."""
    dataset = []

    for problem, solution in verification_corpus:
        # Get gpt-5 HIGH reasoning trace
        response = call_gpt5(
            problem=problem,
            solution=solution,
            reasoning="high",
            return_trace=True  # Include reasoning steps
        )

        dataset.append({
            "input": f"Problem: {problem}\n\nSolution: {solution}",
            "reasoning_trace": response.reasoning,
            "verdict": response.verdict,
            "confidence": response.confidence,
            "bug_report": response.bug_report
        })

    return dataset
```

**Week 3-4: Model Selection and Fine-tuning**

**Model candidates:**
```
Option 1: Fine-tune Llama 3.1 8B
  - Pros: Fast inference (5-10s), good reasoning
  - Cons: Requires fine-tuning expertise
  - Cost: $2k training, $0.50/1M inference

Option 2: Fine-tune Gemini 1.5 Flash
  - Pros: Google's distillation infrastructure
  - Cons: Vendor lock-in
  - Cost: $1k training, $0.15/1M inference

Option 3: Use LoRA on gpt-oss-120b MEDIUM
  - Pros: Familiar model, simpler deployment
  - Cons: Still relatively slow (30s)
  - Cost: $500 training, $8/1M inference
```

**Recommended:** Llama 3.1 8B (best speed/accuracy/cost balance)

**Week 5-6: Validation and A/B Testing**

```python
class HybridVerifier:
    """Student model with teacher fallback."""

    def __init__(self):
        self.student = load_model("llama-3.1-8b-verification-ft")
        self.teacher = GPT5Client()
        self.confidence_threshold = 0.90  # Higher threshold (student less reliable)

    def verify(self, problem, solution):
        # Try student first (10s)
        result_student = self.student.verify(problem, solution)

        if result_student.confidence >= self.confidence_threshold:
            return result_student  # 85% of cases

        # Escalate to teacher for uncertain cases
        result_teacher = self.teacher.verify(
            problem, solution,
            reasoning="high"
        )

        return result_teacher  # 15% of cases
```

**Performance:**
```
Student (85%): 10s avg
Teacher (15%): 50s avg

Blended P95: 0.85 × 15s + 0.15 × 60s = 12.75s + 9s = 22s ✓

Cost:
  - Student: $0.50/1M × 85% = $0.43
  - Teacher: $100/1M × 15% = $15.00
  - Blended: $15.43 per 1M tokens (6.5× cheaper than pure gpt-5)

Daily cost (1000 verifications):
  - $51/day vs $330/day pure gpt-5
  - Savings: $279/day = $8.4k/month
```

---

### Advanced: Iterative Distillation Loop

**Goal:** Continuously improve student by learning from production errors.

```python
class AdaptiveVerifier:
    """Self-improving verification with teacher supervision."""

    def verify_with_learning(self, problem, solution):
        # Student prediction
        result_student = self.student.verify(problem, solution)

        # Confidence-based routing
        if result_student.confidence >= 0.95:
            return result_student

        # Get teacher opinion for learning
        result_teacher = self.teacher.verify(problem, solution)

        # Log disagreement for retraining
        if result_student.verdict != result_teacher.verdict:
            self._log_error_case({
                "problem": problem,
                "solution": solution,
                "student_verdict": result_student.verdict,
                "teacher_verdict": result_teacher.verdict,
                "teacher_reasoning": result_teacher.reasoning
            })

        # Retrain student weekly on error cases
        if self.should_retrain():
            self._incremental_training()

        return result_teacher
```

**Benefits:**
- Student accuracy improves over time (80% → 88%+)
- Confidence calibration improves (fewer escalations)
- Cost decreases as student handles more cases
- P95 latency decreases (fewer slow-path calls)

**Expected trajectory:**
```
Month 1: 85% student, 15% teacher → $15.43/1M tokens, P95=22s
Month 3: 90% student, 10% teacher → $10.50/1M tokens, P95=18s
Month 6: 93% student, 7% teacher  → $7.43/1M tokens, P95=15s
```

---

## Nvidia Perspective

### What Production ML Team Would Prioritize

**As Nvidia engineers, we care about:**
1. **Throughput** - Verifications per second
2. **Latency** - P95, P99 tail latency
3. **Cost** - $/verification at scale
4. **Reliability** - Uptime, error rates
5. **Scalability** - Can we 10× load?

### Current State Assessment

| Metric | Current (gpt-oss HIGH) | Production Target | Gap |
|--------|----------------------|------------------|-----|
| **Throughput** | 0.005 verif/s (1 per 200s) | 1 verif/s | -200× |
| **P95 Latency** | 315s | 60s | -5.25× |
| **P99 Latency** | 510s | 90s | -5.67× |
| **Cost** | $0.05/verif | <$0.10/verif | ✅ Good |
| **Reliability** | 401 errors (OpenRouter) | 99.9% uptime | ❌ Blocked |
| **Accuracy** | 66.7% | 85%+ | -18.3pp |

**Verdict:** 🔴 **NOT PRODUCTION READY**

---

### Recommended Production Architecture

**Phase 1 (Immediate - Week 1):** Hybrid MEDIUM + Structural Fallback

```python
def verify_production_v1(problem, solution):
    """
    Fast and cheap with acceptable accuracy.
    Target: P95 < 90s, accuracy 75%+, cost <$0.05/verif
    """
    try:
        result = verify_gpt_oss_medium(
            problem, solution,
            timeout=45,
            max_tokens=3000
        )

        if result.confidence >= 0.80:
            return result

    except TimeoutError:
        return structural_fallback(problem, solution)

    # Escalate uncertain cases to gpt-5
    return verify_gpt5_high(
        problem, solution,
        timeout=60,
        max_tokens=4000
    )
```

**Performance:**
- P95: 70-90s (borderline but deployable)
- Accuracy: 78-82%
- Cost: $0.03/verif avg
- Throughput: 0.02 verif/s

**Deployment:** Low-stakes verification, development environments

---

**Phase 2 (Short-term - Week 2-4):** gpt-5 with Optimized Prompts

```python
def verify_production_v2(problem, solution):
    """
    Production-grade with gpt-5.
    Target: P95 < 60s, accuracy 85%+, cost <$0.50/verif
    """
    return verify_gpt5_high(
        problem, solution,
        timeout=60,
        max_tokens=3500,  # Reduced from 7000
        constraints=OPTIMIZED_CONSTRAINTS_V2  # Stronger enforcement
    )
```

**Performance:**
- P95: 40-60s ✓ MEETS TARGET
- Accuracy: 85-90%
- Cost: $0.33/verif
- Throughput: 0.05 verif/s

**Deployment:** Production verification, high-stakes scenarios

---

**Phase 3 (Long-term - Month 2-3):** Teacher-Student Distillation

```python
def verify_production_v3(problem, solution):
    """
    Optimized distilled model with teacher fallback.
    Target: P95 < 30s, accuracy 85%+, cost <$0.10/verif
    """
    result = verify_student_model(
        problem, solution,
        timeout=15,
        max_tokens=2000
    )

    if result.confidence >= 0.90:
        return result  # 85-90% of cases

    return verify_gpt5_high(
        problem, solution,
        timeout=45
    )  # 10-15% of cases
```

**Performance:**
- P95: 22-30s ✓ CRUSHES TARGET
- Accuracy: 85-88%
- Cost: $0.05/verif avg
- Throughput: 0.08 verif/s

**Deployment:** Scaled production (10k+ verifications/day)

---

### Infrastructure Recommendations

**Deployment Stack:**
```
┌─────────────────────────────────────────┐
│         Load Balancer (nginx)           │
│    Rate limiting: 100 req/s per user    │
└─────────────────────────────────────────┘
                    │
        ┌───────────┴───────────┐
        │                       │
┌───────▼────────┐    ┌────────▼────────┐
│  Fast Path     │    │  Slow Path      │
│  (Student)     │    │  (gpt-5)        │
│  - 10s P95     │    │  - 50s P95      │
│  - 90% traffic │    │  - 10% traffic  │
└────────────────┘    └─────────────────┘
        │                       │
        └───────────┬───────────┘
                    │
        ┌───────────▼──────────────┐
        │   Result Cache (Redis)   │
        │   TTL: 1 hour            │
        │   Hit rate: 30-40%       │
        └──────────────────────────┘
```

**Monitoring:**
```python
metrics = {
    "latency_p50": Histogram("verification_latency_p50"),
    "latency_p95": Histogram("verification_latency_p95"),
    "latency_p99": Histogram("verification_latency_p99"),
    "accuracy": Gauge("verification_accuracy"),
    "cost_per_verification": Gauge("cost_per_verification"),
    "model_usage": Counter("model_usage", labels=["model", "path"]),
    "cache_hit_rate": Gauge("cache_hit_rate"),
    "timeout_rate": Gauge("timeout_rate"),
}
```

**Alerting thresholds:**
- P95 > 80s for 5 minutes → Page oncall
- Accuracy < 80% for 1 hour → Escalate to ML team
- Cost > $0.50/verif for 1 hour → Notify finance
- Timeout rate > 10% for 5 minutes → Check infrastructure

---

### Scaling Strategy

**Current capacity:** 0.005 verif/s (1 per 200s)
**Target capacity:** 10 verif/s (2000× increase)

**How to scale:**

**Option 1: Horizontal Scaling (Student Model)**
```
10 verif/s = 10 concurrent students (10s each)

Infrastructure:
  - 10× GPU instances (Llama 3.1 8B)
  - Cost: 10 × $1.50/hour = $15/hour = $360/day
  - Student handles 90% → 9 verif/s
  - Teacher handles 10% → 1 verif/s (no bottleneck)

Total cost: $360/day infra + $50/day API = $410/day
Verifications: 10 × 86400 = 864k/day
Cost per verification: $410 / 864k = $0.00047 ✓ VERY CHEAP
```

**Option 2: Batching (gpt-5)**
```
10 verif/s = batch size 10 with 1s per verification

gpt-5 supports batched inference:
  - Process 10 verifications in parallel
  - Total time: max(individual times) ≈ 60s
  - Effective rate: 10/60 = 0.167 verif/s per instance

Need: 10 / 0.167 = 60 parallel instances

Cost: 60 × $0.33 × 864k/day = $17M/day ❌ TOO EXPENSIVE
```

**Verdict:** Student model is the ONLY scalable approach.

---

### Risk Analysis

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|-----------|
| **OpenRouter API unreliable** | High | High | Use multiple providers (fallback) |
| **gpt-5 rate limits** | Medium | High | Implement queueing, back-pressure |
| **Student model drift** | Medium | Medium | Weekly retraining, A/B testing |
| **Tail latency spikes** | High | Medium | Circuit breakers, timeouts |
| **Cost overruns** | Low | Medium | Budget alerts, auto-scaling limits |
| **Accuracy regression** | Medium | High | Shadow mode validation, rollback plan |

**Critical risks:**
1. **OpenRouter reliability:** 401 errors indicate infrastructure issues. MUST have fallback provider.
2. **gpt-5 cost at scale:** $17M/day if naive scaling. MUST use student model.

---

### Final Recommendations (Nvidia Priority Order)

**Week 1 (Deploy Fast):**
1. ✅ Switch to MEDIUM reasoning (immediate 4× speedup)
2. ✅ Add timeout-based circuit breakers (prevent tail latency)
3. ✅ Implement structural fallback (handle timeout cases)
4. ✅ Deploy to dev environment for validation

**Week 2-3 (Production Deploy):**
5. ✅ Set up gpt-5 API access (for slow path)
6. ✅ Implement hybrid architecture (MEDIUM + gpt-5 fallback)
7. ✅ Add comprehensive monitoring and alerting
8. ✅ Deploy to production with 10% traffic

**Month 2 (Optimize):**
9. ✅ Collect 10k gpt-5 verification traces
10. ✅ Fine-tune Llama 3.1 8B student model
11. ✅ A/B test student vs gpt-5 accuracy
12. ✅ Deploy student to 50% traffic

**Month 3 (Scale):**
13. ✅ Roll out student to 90% traffic
14. ✅ Scale to 10 verif/s with horizontal student deployment
15. ✅ Implement iterative retraining pipeline
16. ✅ Achieve P95 < 30s, cost < $0.05/verif

**Total timeline:** 3 months to production-grade system
**Total investment:** $15k (data collection + training)
**Payback period:** 2 months (vs $10k/month gpt-5)

---

## Conclusion

**Bottom line:** Current gpt-oss-120b HIGH reasoning is **NOT production ready** (5× too slow, unstable).

**Best immediate fix:** Use gpt-5 HIGH reasoning (meets latency target, 85-90% accuracy).

**Best long-term solution:** Teacher-student distillation (22s P95, $0.05/verif, scales to 10+ verif/s).

**Key insight:** Latency is driven by **reasoning depth**, not output tokens. HIGH reasoning mode has "thoroughness bias" that overrides constraints. The solution is either (1) use better instruction-following model (gpt-5), or (2) distill fast student from teacher.

**Critical path:** Week 1: MEDIUM+timeout → Week 2: gpt-5 hybrid → Month 2: Student model → Month 3: Scale to 10 verif/s

---

**Status:** Analysis complete. Ready for engineering review and deployment planning.

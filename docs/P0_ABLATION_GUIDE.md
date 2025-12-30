# P0 Ablation Testing Guide

## Overview

The P0 Ablation Test Framework enables systematic evaluation of individual P0 features to determine their impact on RLAC performance. This framework ensures temperature=0 for all tests to enable deterministic, reproducible comparisons.

## Quick Start

```bash
# Full test (10 rounds)
./test_p0_ablation.sh problems/imo01.txt 10

# Quick validation test (3 rounds)
./test_p0_ablation_quick.sh problems/imo01.txt

# Custom configuration
RLAC_MAX_ROUNDS=15 ./test_p0_ablation.sh problems/imo02.txt 15
```

## P0 Features

### 1. Format Validation (`RLAC_DISABLE_P0_FORMAT_VALIDATION`)

**Location:** `code/agent_gpt_oss.py:1124-1146`

**Purpose:** Catches extraction bugs before calling verifier

**How it works:**
- Extracts detailed solution using `extract_detailed_solution()`
- Validates that extracted solution is at least 100 characters
- Returns error message if validation fails (prevents silent failures)

**Expected impact:**
- **Critical for:** Problems with complex formatting
- **Prevents:** Sending empty/malformed solutions to verifier
- **Failure mode:** Silent failures where verifier receives invalid input

**Test hypothesis:**
- Baseline with feature: Should catch format errors early
- Ablation without feature: May send invalid solutions to verifier

### 2. Near-Success Protection (`RLAC_DISABLE_P0_NEAR_SUCCESS_PROTECTION`)

**Location:** `code/agent_gpt_oss.py:5244-5271`

**Purpose:** Prevents progress loss near success threshold

**How it works:**
- **At 2/3 ROBUST:** Decrement instead of reset on failure (grace failure)
- **At 1/3 ROBUST with history:** Give grace failure if `total_robust_count >= 2`
- **Strong history:** Partial protection if `total_robust_count >= 3`

**Expected impact:**
- **Critical for:** Problems with oscillation near threshold
- **Prevents:** Losing progress due to single spurious BROKEN verdict
- **Failure mode:** Reset to 0/3 ROBUST when close to success (2/3 or 1/3)

**Test hypothesis:**
- Baseline with feature: Should maintain progress through minor setbacks
- Ablation without feature: May oscillate near threshold without converging

### 3. Answer Lock (`RLAC_DISABLE_P0_ANSWER_LOCK`)

**Location:** `code/agent_gpt_oss.py:4898-4911`

**Purpose:** Prevents answer oscillation after achieving near-success

**How it works:**
- Locks answer after 2 consecutive ROBUST verdicts
- Prevents generator from changing the answer fundamentally
- Auto-disabled during P5 reconsideration
- Re-engages after P5 if new answer gets ROBUST

**Expected impact:**
- **Critical for:** Problems where generator oscillates between correct answers
- **Prevents:** Answer changes after achieving stability
- **Failure mode:** Generator keeps changing answer despite ROBUST verdicts

**Test hypothesis:**
- Baseline with feature: Answer should stabilize at 2/3 ROBUST
- Ablation without feature: Answer may oscillate even at 2/3 ROBUST

### 4. Adaptive Temperature (`RLAC_DISABLE_ADAPTIVE_TEMPERATURE`)

**Location:** `code/agent_gpt_oss.py:7025-7036`

**Purpose:** Increases exploration when stuck

**How it works:**
- Normally temperature = 0.0 (deterministic)
- When stuck, increases temperature to 0.7 for diversity
- Adds diversity instruction prompt

**Expected impact:**
- **Useful for:** Breaking out of local minima
- **Risk:** Non-determinism makes comparisons difficult
- **P0 Testing:** **DISABLED for all tests** to ensure fair comparison

**Test note:**
- This feature is **disabled for ALL ablation tests** to ensure deterministic behavior
- Temperature=0.0 enforced across all configurations

## Test Methodology

### Test Configurations

1. **Baseline:** All P0 features enabled (reference configuration)
2. **Individual ablations:** Each feature disabled separately
3. **Full ablation:** All P0 features disabled (worst case)

### Controlled Variables

- Temperature: 0.0 (adaptive temperature disabled)
- Max rounds: Configurable (default: 10)
- Solution reasoning: low
- Critic reasoning: medium
- Verification: Every 2 rounds starting from round 0
- Robust threshold: 3 consecutive ROBUST verdicts

### Success Metrics

1. **Primary:** Did solution achieve 3 consecutive ROBUST verdicts?
2. **Secondary:** How many rounds to success?
3. **Tertiary:** Cost, total ROBUST count, oscillation patterns

## Interpreting Results

### Success Patterns

| Baseline | Ablation | Interpretation | Action |
|----------|----------|----------------|--------|
| ✅ | ❌ | Feature is **critical** | Always enable |
| ✅ | ✅ (slower) | Feature improves **efficiency** | Enable for production |
| ✅ | ✅ (same) | Feature has **minimal impact** | May be problem-specific |
| ❌ | ❌ | Problem **too hard** | Need stronger config |
| ❌ | ✅ | **Unexpected** | Investigate further |

### Critical vs. Efficiency Features

**Critical Features:**
- Baseline succeeds, ablation fails
- These features are **necessary** for correctness
- **Example:** Near-success protection on oscillating problems

**Efficiency Features:**
- Both succeed, ablation takes longer
- These features improve **performance** but not correctness
- **Example:** Format validation (catches errors early but not strictly necessary)

**Neutral Features:**
- No significant difference
- May be problem-specific or need refinement
- **Example:** Answer lock on non-oscillating problems

## Example Analysis

### Scenario 1: Near-Success Protection is Critical

```
Baseline (all features):
  - Round 8: 2/3 ROBUST
  - Round 9: SUSPICIOUS (grace failure → 1/3)
  - Round 10: ROBUST (2/3)
  - Round 11: ROBUST (3/3 SUCCESS)

Ablation (protection disabled):
  - Round 8: 2/3 ROBUST
  - Round 9: SUSPICIOUS (reset → 0/3)
  - Round 10: ROBUST (1/3)
  - Round 11: SUSPICIOUS (reset → 0/3)
  - [continues oscillating, never reaches 3/3]
```

**Conclusion:** Near-success protection is **critical** for this problem.

### Scenario 2: Answer Lock Improves Efficiency

```
Baseline (all features):
  - Round 6: Answer locked at "42"
  - Round 7-9: ROBUST (answer stable)
  - Round 9: SUCCESS (3/3 ROBUST)

Ablation (lock disabled):
  - Round 6: Answer = "42" (2/3 ROBUST)
  - Round 7: Answer changed to "43" (reset to 1/3)
  - Round 8: Answer back to "42" (2/3 ROBUST)
  - Round 12: Finally SUCCESS (more rounds)
```

**Conclusion:** Answer lock is an **efficiency feature** (both succeed, ablation slower).

## Running Experiments

### Single Problem Test

```bash
# Test on Problem 1 with 10 rounds
./test_p0_ablation.sh problems/imo01.txt 10

# Results in: ablation_results_TIMESTAMP/
# - baseline.log
# - no_format_validation.log
# - no_near_success_protection.log
# - no_answer_lock.log
# - all_disabled.log
# - ablation_report.md
```

### Multi-Problem Study

```bash
# Create study directory
mkdir p0_ablation_study
cd p0_ablation_study

# Test on all problems
for problem in ../problems/imo*.txt; do
    echo "Testing ${problem}..."
    ../test_p0_ablation.sh "${problem}" 10
    sleep 10  # Pause between problems
done

# Aggregate results
grep -h "SUCCESS\|FAILED" ablation_results_*/*/summary.txt > aggregate_results.txt
```

### Custom Configuration

```bash
# Test with higher rounds and different reasoning
export RLAC_MAX_ROUNDS=15
export RLAC_SOL_REASONING=medium
export RLAC_CRITIC_REASONING=high

./test_p0_ablation.sh problems/imo02.txt 15
```

## Environment Variables Reference

### P0 Feature Toggles

```bash
# Disable individual features (default: false)
export RLAC_DISABLE_P0_FORMAT_VALIDATION=true
export RLAC_DISABLE_P0_NEAR_SUCCESS_PROTECTION=true
export RLAC_DISABLE_P0_ANSWER_LOCK=true
export RLAC_DISABLE_ADAPTIVE_TEMPERATURE=true  # Always true for ablation

# Enable all (default behavior)
unset RLAC_DISABLE_P0_FORMAT_VALIDATION
unset RLAC_DISABLE_P0_NEAR_SUCCESS_PROTECTION
unset RLAC_DISABLE_P0_ANSWER_LOCK
```

### RLAC Configuration

```bash
# Core settings
export RLAC_MAX_ROUNDS=10
export RLAC_ROBUST_THRESHOLD=3
export RLAC_SOL_REASONING=low
export RLAC_CRITIC_REASONING=medium

# Verification settings
export RLAC_VERIFY_EVERY_N_ROUNDS=2
export RLAC_VERIFY_START_ROUND=0
export RLAC_DISABLE_INLINE_VERIFICATION=false

# Advanced settings
export RLAC_STUCK_THRESHOLD=4
export RLAC_MAX_REGEN=4
export RLAC_ACCEPT_SUSPICIOUS_THRESHOLD=3
export RLAC_SUSPICIOUS_LOOKBACK=4
```

## Debugging Tips

### Check P0 Configuration

```bash
# Look for P0 ABLATION section in logs
grep "P0 ABLATION" ablation_results_*/baseline.log

# Expected output:
# >>>>>>> [P0 ABLATION] Format validation: True
# >>>>>>> [P0 ABLATION] Near-success protection: True
# >>>>>>> [P0 ABLATION] Answer lock: True
# >>>>>>> [P0 ABLATION] Adaptive temperature: False
# >>>>>>> [P0 ABLATION] Base temperature: 0.0 (deterministic)
```

### Track ROBUST Progress

```bash
# See when features activate
grep "P0-v2" ablation_results_*/baseline.log

# Example output:
# [RLAC P0-v2] High protection activated!
# [RLAC P0-v2] 2/3 -> 1/3 (grace failure)
```

### Compare Verdict Sequences

```bash
# Extract verdict history
for log in ablation_results_*/*.log; do
    echo "=== $(basename ${log}) ==="
    grep -o "verdict: [A-Z]*" "${log}" | cut -d' ' -f2
done
```

## Context Extraction (Future Enhancement)

If ablation tests show that certain features consistently provide value, we can implement **context extraction** to automatically identify when features are beneficial:

### Proposed Context Extraction Features

1. **Problem Type Detection**
   - Classify as FIND vs PROVE
   - Detect geometry problems (need longer counterexamples)
   - Identify number theory (may need answer lock)

2. **Solution Stability Analysis**
   - Track answer oscillation frequency
   - Measure confidence variance
   - Detect near-success patterns

3. **Adaptive Feature Selection**
   - Enable answer lock only if oscillation detected
   - Increase counterexample length for geometry
   - Adjust protection based on total_robust_count

### Implementation Plan (if ablation shows value)

```python
# Pseudocode for context-aware P0 features

def should_enable_answer_lock(problem_type, answer_history):
    """Enable answer lock if oscillation detected"""
    if problem_type == "FIND":
        # Check if answer oscillates
        recent_answers = answer_history[-5:]
        unique_answers = len(set(recent_answers))
        if unique_answers > 2:
            return True  # Oscillating, enable lock
    return False  # Stable, no lock needed

def get_counterexample_max_length(problem_statement):
    """Adjust CE length based on problem type"""
    if "geometry" in problem_statement.lower():
        return 2000  # Need full coordinate specs
    elif "number theory" in problem_statement.lower():
        return 500   # Short is fine
    return 1000  # Default
```

## Next Steps

1. **Run baseline ablation:** Test on Problem 1 to validate framework
2. **Multi-problem study:** Test on all 5 IMO problems
3. **Analyze patterns:** Identify which features are critical vs. efficiency
4. **Implement context extraction:** If specific features consistently help specific problem types
5. **Update defaults:** Based on findings, adjust default P0 configuration

## Troubleshooting

### Test hangs or times out
- Check API connectivity
- Reduce max rounds for faster testing
- Check for infinite loops in logs

### Inconsistent results between runs
- Verify temperature=0.0 is enforced
- Check that adaptive temperature is disabled
- Ensure no random seeds are changing

### Feature doesn't seem to activate
- Check environment variables are set correctly
- Look for P0 ABLATION logs at startup
- Verify feature activation logs (e.g., "P0-v2" messages)

## References

- Main RLAC implementation: `code/agent_gpt_oss.py`
- Adversarial critic: `code/adversarial_critic.py`
- Test script: `test_p0_ablation.sh`
- Quick test: `test_p0_ablation_quick.sh`

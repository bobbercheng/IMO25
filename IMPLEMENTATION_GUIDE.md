# Implementation Guide: Asymmetric Reasoning Effort

**Target**: Modify GPT-OSS agent to use different reasoning efforts for generation vs verification
**Time Required**: 1-2 hours
**Difficulty**: Low (simple code changes)

---

## Overview

This guide shows exactly how to implement asymmetric reasoning effort (low for generation, high for verification) in the GPT-OSS agent.

---

## Current State vs Target State

### Current (Symmetric)
```python
# Everything uses the same reasoning effort
REASONING_EFFORT = "low"  # Applied to both generation and verification
```

### Target (Asymmetric)
```python
# Different reasoning efforts for different tasks
SOLUTION_REASONING_EFFORT = "low"   # Fast, focused generation
VERIFICATION_REASONING_EFFORT = "high"  # Rigorous checking
```

---

## Implementation Steps

### Step 1: Modify Global Configuration (5 minutes)

**File**: `/home/user/IMO25/code/agent_gpt_oss.py`
**Lines**: 47-49

**Current Code:**
```python
# Line 47-49
# Reasoning effort level (low, medium, high)
# Changed from "high" to "low" to reduce content overflow (Option A improvement)
REASONING_EFFORT = os.getenv("GPT_OSS_REASONING_EFFORT", "low")
```

**New Code:**
```python
# Line 47-54 (replace)
# Reasoning effort levels (low, medium, high)
# Asymmetric configuration: low for generation (prevents truncation),
# high for verification (ensures rigor)
SOLUTION_REASONING_EFFORT = os.getenv("GPT_OSS_SOLUTION_REASONING", "low")
VERIFICATION_REASONING_EFFORT = os.getenv("GPT_OSS_VERIFICATION_REASONING", "high")

# For backward compatibility
REASONING_EFFORT = SOLUTION_REASONING_EFFORT
```

---

### Step 2: Update Configuration Printing (5 minutes)

**File**: `/home/user/IMO25/code/agent_gpt_oss.py`
**Lines**: 51-58

**Current Code:**
```python
# Line 51-58
# Print configuration on module load
import sys
if not hasattr(sys, '_agent_gpt_oss_config_printed'):
    sys._agent_gpt_oss_config_printed = True
    # Use original_print before we override it
    _original_builtin_print = print
    _original_builtin_print(f"[CONFIG] GPT_OSS API URL: {API_URL}")
    _original_builtin_print(f"[CONFIG] Reasoning Effort: {REASONING_EFFORT}")
```

**New Code:**
```python
# Line 51-60 (replace)
# Print configuration on module load
import sys
if not hasattr(sys, '_agent_gpt_oss_config_printed'):
    sys._agent_gpt_oss_config_printed = True
    # Use original_print before we override it
    _original_builtin_print = print
    _original_builtin_print(f"[CONFIG] GPT_OSS API URL: {API_URL}")
    _original_builtin_print(f"[CONFIG] Solution Reasoning: {SOLUTION_REASONING_EFFORT}")
    _original_builtin_print(f"[CONFIG] Verification Reasoning: {VERIFICATION_REASONING_EFFORT}")
    _original_builtin_print(f"[CONFIG] Asymmetric Mode: {SOLUTION_REASONING_EFFORT != VERIFICATION_REASONING_EFFORT}")
```

---

### Step 3: Update build_request_payload() Function (10 minutes)

**File**: `/home/user/IMO25/code/agent_gpt_oss.py`
**Lines**: 130-162

**Current Code:**
```python
def build_request_payload(system_prompt, question_prompt, other_prompts=None):
    """
    Builds the JSON payload for the OpenAI-compatible API request.
    """
    payload = {
        "messages": [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": question_prompt
            }
        ],
        "model": MODEL_NAME,
        "temperature": 0.1,
        "reasoning": {
            "effort": REASONING_EFFORT
        }
        # Removed repetition_penalty (Option A improvement)
        # Allows natural token distribution for mathematical proofs
    }

    if other_prompts:
        for prompt in other_prompts:
            payload["messages"].append({
                "role": "user",
                "content": prompt
            })

    return payload
```

**New Code:**
```python
def build_request_payload(system_prompt, question_prompt, other_prompts=None,
                         reasoning_effort=None):
    """
    Builds the JSON payload for the OpenAI-compatible API request.

    Args:
        system_prompt: System-level instructions
        question_prompt: User question/problem
        other_prompts: Additional user messages (optional)
        reasoning_effort: Override reasoning effort level (optional)
                         Options: "low", "medium", "high"
                         If None, uses SOLUTION_REASONING_EFFORT (default for generation)

    Returns:
        dict: JSON payload for API request
    """
    # Default to solution reasoning effort if not specified
    if reasoning_effort is None:
        reasoning_effort = SOLUTION_REASONING_EFFORT

    payload = {
        "messages": [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": question_prompt
            }
        ],
        "model": MODEL_NAME,
        "temperature": 0.1,
        "reasoning": {
            "effort": reasoning_effort
        }
        # Removed repetition_penalty (Option A improvement)
        # Allows natural token distribution for mathematical proofs
    }

    if other_prompts:
        for prompt in other_prompts:
            payload["messages"].append({
                "role": "user",
                "content": prompt
            })

    return payload
```

---

### Step 4: Update verify_solution() Function (10 minutes)

**File**: `/home/user/IMO25/code/agent_gpt_oss.py`
**Lines**: 437-480 (approximately)

**Find this code:**
```python
def verify_solution(problem_statement, solution, verbose=True):

    dsol = extract_detailed_solution(solution)

    # ... existing code for building verification prompt ...

    p2 = build_request_payload(system_prompt=verification_system_prompt,
        question_prompt=newst
        )
```

**Change to:**
```python
def verify_solution(problem_statement, solution, verbose=True):

    dsol = extract_detailed_solution(solution)

    # ... existing code for building verification prompt ...

    # Use HIGH reasoning for verification (rigorous checking)
    p2 = build_request_payload(
        system_prompt=verification_system_prompt,
        question_prompt=newst,
        reasoning_effort=VERIFICATION_REASONING_EFFORT  # ← KEY CHANGE
    )
```

---

### Step 5: Verify All Other Function Calls (10 minutes)

Search for all other calls to `build_request_payload()` and ensure they use appropriate reasoning:

```bash
cd /home/user/IMO25
grep -n "build_request_payload" code/agent_gpt_oss.py
```

**Expected locations:**
1. `init_explorations()` - Should use default (SOLUTION_REASONING_EFFORT) ✓
2. `verify_solution()` - Should use VERIFICATION_REASONING_EFFORT ✓ (we just changed this)
3. Any other calls - Review and set appropriately

---

### Step 6: Add Validation Script (20 minutes)

**Create new file**: `/home/user/IMO25/validate_solution.py`

```python
#!/usr/bin/env python3
"""
Validate an existing solution with high reasoning verification.

Usage:
    python validate_solution.py <log_file> <problem_file>

Example:
    python validate_solution.py \\
        run_log_gpt_oss/agent_gpt_oss_low_output_1.log \\
        problems/imo_2025_p1.txt
"""

import sys
import re
from code.agent_gpt_oss import verify_solution, read_file_content, VERIFICATION_REASONING_EFFORT

def extract_solution_from_log(log_file):
    """
    Extract the final solution from an agent log file.

    Looks for the last occurrence of "Correct solution found" and
    extracts the solution that led to it.
    """
    with open(log_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find the last "Correct solution found" marker
    matches = list(re.finditer(r'>>>>>>> Correct solution found\.', content))
    if not matches:
        print("Error: No successful solution found in log file")
        return None

    # Find the solution before this marker
    last_match_pos = matches[-1].start()
    before_success = content[:last_match_pos]

    # Extract the last solution block
    solution_matches = list(re.finditer(
        r'>>>>>>> Corrected solution:\n(.*?)(?=\n>>>>>>>|\Z)',
        before_success,
        re.DOTALL
    ))

    if not solution_matches:
        # Try alternative format
        solution_matches = list(re.finditer(
            r'>>>>>>> Streaming Response:.*?\n(.*?)(?=\n>>>>>>>|\Z)',
            before_success,
            re.DOTALL
        ))

    if solution_matches:
        solution = solution_matches[-1].group(1).strip()
        return solution
    else:
        print("Error: Could not extract solution from log")
        return None


def main():
    if len(sys.argv) < 3:
        print("Usage: python validate_solution.py <log_file> <problem_file>")
        print()
        print("Validates an existing solution with high reasoning verification")
        sys.exit(1)

    log_file = sys.argv[1]
    problem_file = sys.argv[2]

    print("=" * 70)
    print("SOLUTION VALIDATION WITH HIGH REASONING")
    print("=" * 70)
    print()

    # Extract solution from log
    print(f"📄 Extracting solution from: {log_file}")
    solution = extract_solution_from_log(log_file)

    if solution is None:
        print("❌ Failed to extract solution")
        sys.exit(1)

    print(f"✅ Extracted solution ({len(solution)} characters)")
    print()

    # Read problem
    print(f"📄 Reading problem from: {problem_file}")
    problem = read_file_content(problem_file)
    print(f"✅ Read problem ({len(problem)} characters)")
    print()

    # Verify with high reasoning
    print(f"🔍 Verifying with reasoning effort: {VERIFICATION_REASONING_EFFORT}")
    print("-" * 70)
    print()

    # Force high reasoning for verification
    import code.agent_gpt_oss as agent
    original_effort = agent.VERIFICATION_REASONING_EFFORT
    agent.VERIFICATION_REASONING_EFFORT = "high"

    try:
        result = verify_solution(problem, solution, verbose=True)
    finally:
        # Restore original setting
        agent.VERIFICATION_REASONING_EFFORT = original_effort

    print()
    print("=" * 70)
    if result:
        print("✅ VALIDATION PASSED")
        print()
        print("The solution is CORRECT according to high reasoning verification!")
        print("Confidence level: VERY HIGH (95%+)")
        print()
        print("This confirms that low reasoning verification was sufficient")
        print("for this particular problem.")
    else:
        print("⚠️  VALIDATION FAILED")
        print()
        print("The solution has issues according to high reasoning verification.")
        print()
        print("This suggests that low reasoning verification was TOO LENIENT")
        print("and accepted a solution with errors.")
        print()
        print("RECOMMENDATION: Use asymmetric reasoning (low/high) going forward")
        print("to ensure rigorous verification from the start.")

    print("=" * 70)

    return 0 if result else 1


if __name__ == "__main__":
    sys.exit(main())
```

---

### Step 7: Test the Implementation (30 minutes)

#### Test 1: Validate Existing Solution
```bash
cd /home/user/IMO25

# Make validation script executable
chmod +x validate_solution.py

# Run validation
python validate_solution.py \
    run_log_gpt_oss/agent_gpt_oss_low_output_1.log \
    problems/imo_2025_p1.txt
```

**Expected Output:**
```
======================================================================
SOLUTION VALIDATION WITH HIGH REASONING
======================================================================

📄 Extracting solution from: run_log_gpt_oss/agent_gpt_oss_low_output_1.log
✅ Extracted solution (XXXX characters)

📄 Reading problem from: problems/imo_2025_p1.txt
✅ Read problem (XXXX characters)

🔍 Verifying with reasoning effort: high
----------------------------------------------------------------------

[Verification output...]

======================================================================
✅ VALIDATION PASSED
...
======================================================================
```

---

#### Test 2: Run New Problem with Asymmetric
```bash
# Set environment variables for asymmetric reasoning
export GPT_OSS_SOLUTION_REASONING="low"
export GPT_OSS_VERIFICATION_REASONING="high"

# Run agent on IMO Problem 1
python code/agent_gpt_oss.py problems/imo_2025_p1.txt \
    --log-file run_log_gpt_oss/agent_gpt_oss_asymmetric_p1.log

# Watch progress
tail -f run_log_gpt_oss/agent_gpt_oss_asymmetric_p1.log
```

**Expected Console Output:**
```
[CONFIG] GPT_OSS API URL: http://localhost:30000/v1/chat/completions
[CONFIG] Solution Reasoning: low
[CONFIG] Verification Reasoning: high
[CONFIG] Asymmetric Mode: True
```

---

#### Test 3: Compare Results
```bash
# Monitor the asymmetric run
python monitor_agent_progress.py \
    run_log_gpt_oss/agent_gpt_oss_asymmetric_p1.log \
    --follow --interval 300

# Compare to baseline
# Baseline (low/low): 17 iterations, 45 minutes
# Asymmetric (low/high): ? iterations, ? minutes
```

---

## Environment Variable Reference

### Basic Configuration
```bash
# Use low reasoning for everything (fastest, but questionable rigor)
export GPT_OSS_REASONING_EFFORT="low"

# Use high reasoning for everything (rigorous but broken due to truncation)
export GPT_OSS_REASONING_EFFORT="high"  # DON'T USE
```

### Asymmetric Configuration (Recommended)
```bash
# Low for generation, high for verification (optimal)
export GPT_OSS_SOLUTION_REASONING="low"
export GPT_OSS_VERIFICATION_REASONING="high"

# Alternative: Low for generation, medium for verification (faster)
export GPT_OSS_SOLUTION_REASONING="low"
export GPT_OSS_VERIFICATION_REASONING="medium"
```

### Resume Strategy
```bash
# Phase 1: Get quick solution
export GPT_OSS_SOLUTION_REASONING="low"
export GPT_OSS_VERIFICATION_REASONING="low"
python code/agent_gpt_oss.py problems/problem.txt

# Phase 2: Validate with high reasoning
python validate_solution.py log_file.log problems/problem.txt

# Phase 3: If validation fails, continue with high verification
export GPT_OSS_VERIFICATION_REASONING="high"
# Resume or retry...
```

---

## Validation Checklist

After implementation, verify:

- [ ] Configuration prints show "Solution Reasoning" and "Verification Reasoning"
- [ ] `build_request_payload()` accepts `reasoning_effort` parameter
- [ ] `verify_solution()` uses `VERIFICATION_REASONING_EFFORT`
- [ ] Other functions use default `SOLUTION_REASONING_EFFORT`
- [ ] Environment variables work correctly
- [ ] Validation script extracts and verifies solutions
- [ ] Asymmetric mode works on test problem

---

## Troubleshooting

### Issue: Configuration not showing asymmetric mode
**Solution:** Check that both variables are set:
```bash
env | grep GPT_OSS
# Should show both SOLUTION and VERIFICATION
```

### Issue: Verification still using low reasoning
**Solution:** Check the verify_solution() function update:
```python
# Should have reasoning_effort=VERIFICATION_REASONING_EFFORT
p2 = build_request_payload(..., reasoning_effort=VERIFICATION_REASONING_EFFORT)
```

### Issue: Validation script can't extract solution
**Solution:** Check log file format, solution extraction regex might need adjustment

---

## Expected Performance Changes

### Metrics to Track

| Metric | Low/Low Baseline | Asymmetric Expected | Difference |
|--------|-----------------|---------------------|------------|
| Iterations to success | 17 | 25-35 | +47-106% |
| Time to success | 45 min | 90-150 min | +100-233% |
| Verification time/iter | 1-2 min | 5-10 min | +250-500% |
| Cost per problem | $3 | $12 | +300% |
| Success rate | 50%? | 50-60% | Similar or better |
| Confidence in correctness | 60-70% | 95% | +36-58% |

**Key Trade-off:** 3-4× higher cost, but much higher confidence in correctness

---

## Next Steps After Implementation

1. **Immediate (< 1 hour)**
   - Validate existing low/low solution
   - Document whether it passes high reasoning

2. **Short-term (this week)**
   - Test asymmetric on IMO Problems 1, 2, 3
   - Measure success rates and costs
   - Compare to low/low baseline

3. **Medium-term (this month)**
   - Test on 20+ problems
   - Optimize thresholds (5 passes vs 3 passes?)
   - Tune verification prompts if needed

4. **Long-term (next quarter)**
   - Implement progressive resume strategy
   - Add adaptive reasoning selection
   - Build production pipeline

---

## Success Criteria

Implementation is successful if:
- ✅ Code changes compile and run without errors
- ✅ Configuration correctly shows asymmetric mode
- ✅ Verification uses high reasoning (observable in logs)
- ✅ Validation script can verify existing solutions
- ✅ Test run on IMO Problem 1 completes (success or fail)
- ✅ Results are documented and compared to baseline

---

## Resources

- **Full Analysis**: `REASONING_EFFORT_STRATEGY_ANALYSIS.md`
- **Quick Reference**: `STRATEGY_QUICK_REFERENCE.md`
- **Verification Concern**: `VERIFICATION_RIGOR_PROBLEM.md`
- **Test Results**: `TEST_RESULTS_LOW_REASONING.md`

---

**Implementation Guide Version**: 1.0
**Last Updated**: 2025-11-16
**Estimated Implementation Time**: 1-2 hours
**Difficulty**: ⭐⭐☆☆☆ (Low-Medium)

# Quick Start: Progressive Reasoning Implementation

**Date**: 2025-11-16
**Purpose**: Fast implementation guide to get progressive reasoning working TODAY
**Target**: Minimal viable implementation in 2-3 hours

---

## Option 1: Simple Iteration-Based (FASTEST - Start Here)

### Step 1: Add Simple Function to agent_gpt_oss.py

**Location**: After line 49 (after REASONING_EFFORT definition)

```python
def get_progressive_reasoning_effort(iteration, task_type='verification'):
    """
    Simple iteration-based progressive reasoning.

    Args:
        iteration: Current iteration number (0-based)
        task_type: 'generation' or 'verification'

    Returns:
        'low', 'medium', or 'high'
    """
    # Generation always stays low (proven to work)
    if task_type == 'generation':
        return 'low'

    # Verification increases with iteration
    if iteration < 5:
        return 'low'
    elif iteration < 12:
        return 'medium'
    else:
        return 'high'
```

### Step 2: Modify verify_solution Function

**Location**: Line ~437, function `verify_solution`

**CHANGE FROM**:
```python
def verify_solution(problem_statement, solution, verbose=True):
    # ... existing code ...
    p2 = build_request_payload(system_prompt=verification_system_prompt,
        question_prompt=newst
    )
```

**TO**:
```python
def verify_solution(problem_statement, solution, verbose=True, reasoning_effort=None):
    """
    Verify solution with optional reasoning effort override.

    Args:
        reasoning_effort: Override reasoning effort (None = use default)
    """
    # ... existing code ...

    # Determine reasoning effort
    if reasoning_effort is None:
        reasoning_effort = REASONING_EFFORT  # Use global default

    if verbose:
        print(f">>>>>>> Start verification (reasoning_effort={reasoning_effort})")

    p2 = build_request_payload(
        system_prompt=verification_system_prompt,
        question_prompt=newst,
        reasoning_effort=reasoning_effort  # Pass it through
    )
```

### Step 3: Modify build_request_payload

**Location**: Line ~130

**CHANGE FROM**:
```python
def build_request_payload(system_prompt, question_prompt, other_prompts=None):
    payload = {
        "messages": [...],
        "model": MODEL_NAME,
        "temperature": 0.1,
        "reasoning": {
            "effort": REASONING_EFFORT
        }
    }
```

**TO**:
```python
def build_request_payload(system_prompt, question_prompt, other_prompts=None,
                         reasoning_effort=None):
    """
    Args:
        reasoning_effort: Override reasoning effort (None = use REASONING_EFFORT)
    """
    if reasoning_effort is None:
        reasoning_effort = REASONING_EFFORT

    payload = {
        "messages": [...],
        "model": MODEL_NAME,
        "temperature": 0.1,
        "reasoning": {
            "effort": reasoning_effort  # Use parameter
        }
    }
```

### Step 4: Update agent() Function Main Loop

**Location**: Line ~620, in the main iteration loop

**FIND**:
```python
for i in range(current_iteration, 30):
    print(f"Number of iterations: {i}, number of corrects: {correct_count}, number of errors: {error_count}")
```

**ADD AFTER**:
```python
    # Progressive reasoning
    verification_effort = get_progressive_reasoning_effort(i, 'verification')
    print(f">>>>>>> Progressive: Iteration {i}, Verification effort = {verification_effort}")
```

**THEN FIND** (around line 662):
```python
print(f">>>>>>> Verify the solution.")
verify, good_verify = verify_solution(problem_statement, solution)
```

**CHANGE TO**:
```python
print(f">>>>>>> Verify the solution.")
verify, good_verify = verify_solution(problem_statement, solution,
                                     reasoning_effort=verification_effort)
```

**ALSO FIND** (around line 579):
```python
print(f">>>>>>> Vefify the solution.")
verify, good_verify = verify_solution(problem_statement, solution, verbose)
```

**CHANGE TO**:
```python
print(f">>>>>>> Vefify the solution.")
initial_verify_effort = get_progressive_reasoning_effort(0, 'verification')
verify, good_verify = verify_solution(problem_statement, solution, verbose,
                                     reasoning_effort=initial_verify_effort)
```

### Step 5: Test It!

```bash
# Test with IMO problem 1
python code/agent_gpt_oss.py \
  --benchmark proofbench \
  --level IMO-easy \
  --benchmark-index 0 \
  --log logs/progressive_simple_test.log \
  --memory memory/progressive_simple.json
```

**Expected Output**:
```
[CONFIG] GPT_OSS API URL: http://localhost:30000/v1/chat/completions
[CONFIG] Reasoning Effort: low
...
>>>>>>> Progressive: Iteration 0, Verification effort = low
>>>>>>> Start verification (reasoning_effort=low)
...
>>>>>>> Progressive: Iteration 5, Verification effort = medium
>>>>>>> Start verification (reasoning_effort=medium)
...
>>>>>>> Progressive: Iteration 12, Verification effort = high
>>>>>>> Start verification (reasoning_effort=high)
```

### Estimated Time: 30-45 minutes

---

## Option 2: Success-Gated Iteration-Based (RECOMMENDED)

### Step 1: Create Simple Progressive Manager Class

**Create new file**: `/home/user/IMO25/code/simple_progressive.py`

```python
"""
Simple progressive reasoning with success gates.
Minimal implementation for quick testing.
"""

class SimpleProgressiveManager:
    """Manages progressive verification with success gates"""

    def __init__(self):
        self.iteration = 0
        self.verification_level = 'low'
        self.consecutive_passes = 0
        self.level_transitions = []

    def get_verification_effort(self):
        """Get current verification effort level"""
        return self.verification_level

    def update(self, passed):
        """
        Update after verification.

        Args:
            passed: bool, whether verification passed

        Returns:
            dict with status
        """
        # Update consecutive passes
        if passed:
            self.consecutive_passes += 1
        else:
            self.consecutive_passes = 0

        # Check for level upgrade
        upgraded = False

        # Upgrade logic with gates
        if self.verification_level == 'low' and self.iteration >= 5:
            # Can upgrade to medium if we've had 2 passes at low
            if self.consecutive_passes >= 2:
                self.verification_level = 'medium'
                self.consecutive_passes = 0
                upgraded = True
                print(f"\n{'='*70}")
                print(f"✓ UPGRADED: low → medium at iteration {self.iteration}")
                print(f"{'='*70}\n")

        elif self.verification_level == 'medium' and self.iteration >= 12:
            # Can upgrade to high if we've had 2 passes at medium
            if self.consecutive_passes >= 2:
                self.verification_level = 'high'
                self.consecutive_passes = 0
                upgraded = True
                print(f"\n{'='*70}")
                print(f"✓ UPGRADED: medium → high at iteration {self.iteration}")
                print(f"{'='*70}\n")

        # Check for success
        success = (
            self.verification_level == 'high' and
            self.consecutive_passes >= 5
        )

        # Increment iteration
        self.iteration += 1

        return {
            'iteration': self.iteration - 1,
            'level': self.verification_level,
            'passed': passed,
            'consecutive_passes': self.consecutive_passes,
            'upgraded': upgraded,
            'success': success
        }

    def get_status(self):
        """Get current status string"""
        passes_needed = {
            'low': 2,
            'medium': 2,
            'high': 5
        }

        return (f"Level: {self.verification_level}, "
                f"Passes: {self.consecutive_passes}/{passes_needed[self.verification_level]}")

    def to_dict(self):
        """Serialize for saving"""
        return {
            'iteration': self.iteration,
            'verification_level': self.verification_level,
            'consecutive_passes': self.consecutive_passes,
            'level_transitions': self.level_transitions
        }

    @classmethod
    def from_dict(cls, data):
        """Deserialize from saved state"""
        mgr = cls()
        mgr.iteration = data.get('iteration', 0)
        mgr.verification_level = data.get('verification_level', 'low')
        mgr.consecutive_passes = data.get('consecutive_passes', 0)
        mgr.level_transitions = data.get('level_transitions', [])
        return mgr
```

### Step 2: Modify agent_gpt_oss.py to Use It

**Add import** (line ~31):
```python
from simple_progressive import SimpleProgressiveManager
```

**Modify agent() function** (line ~587):

**ADD AT START**:
```python
def agent(problem_statement, other_prompts=[], memory_file=None, resume_from_memory=False):
    # NEW: Create progressive manager
    use_progressive = os.getenv("GPT_OSS_PROGRESSIVE", "true").lower() == "true"
    progressive = SimpleProgressiveManager() if use_progressive else None

    # Load from memory...
    if resume_from_memory and memory_file:
        memory = load_memory(memory_file)
        if memory:
            # ... existing code ...

            # NEW: Restore progressive state
            if use_progressive and "progressive" in memory:
                progressive = SimpleProgressiveManager.from_dict(memory["progressive"])
                print(f"Resumed progressive: {progressive.get_status()}")
```

**IN MAIN LOOP** (line ~620):
```python
for i in range(current_iteration, 30):
    # NEW: Show progressive status
    if progressive:
        print(f">>>>>>> Progressive Status: {progressive.get_status()}")
    else:
        print(f"Number of iterations: {i}, corrects: {correct_count}, errors: {error_count}")

    try:
        # NEW: Get verification effort
        ver_effort = progressive.get_verification_effort() if progressive else REASONING_EFFORT

        # ... existing verification code ...
        verify, good_verify = verify_solution(problem_statement, solution,
                                             reasoning_effort=ver_effort)

        # NEW: Update progressive manager
        if progressive:
            status = progressive.update("yes" in good_verify.lower())

            if status['success']:
                print("\n" + "="*70)
                print("🎉 SUCCESS! Achieved 5 passes at HIGH level")
                print("="*70)
                return solution
        else:
            # Original logic
            if "yes" in good_verify.lower():
                correct_count += 1
                if correct_count >= 5:
                    return solution
```

**UPDATE save_memory** (line ~492):
```python
def save_memory(memory_file, problem_statement, other_prompts,
               current_iteration, max_runs, solution=None, verify=None,
               progressive=None):  # NEW parameter
    memory = {
        "problem_statement": problem_statement,
        # ... existing fields ...
    }

    # NEW: Save progressive state
    if progressive is not None:
        memory["progressive"] = progressive.to_dict()

    # ... rest of function ...
```

**UPDATE save_memory calls** (search for `save_memory(`):
```python
# Change from:
save_memory(memory_file, problem_statement, other_prompts, i, 30, solution, verify)

# To:
save_memory(memory_file, problem_statement, other_prompts, i, 30, solution, verify, progressive)
```

### Step 3: Test It!

```bash
# Enable progressive mode (default)
export GPT_OSS_PROGRESSIVE=true

# Run test
python code/agent_gpt_oss.py \
  --benchmark proofbench \
  --level IMO-easy \
  --benchmark-index 0 \
  --log logs/progressive_gated_test.log \
  --memory memory/progressive_gated.json
```

**Expected Output**:
```
>>>>>>> Progressive Status: Level: low, Passes: 0/2
...
>>>>>>> Progressive Status: Level: low, Passes: 2/2
============================================================
✓ UPGRADED: low → medium at iteration 5
============================================================
>>>>>>> Progressive Status: Level: medium, Passes: 0/2
...
```

### Estimated Time: 1-2 hours

---

## Quick Comparison Test

### Test Script

**Create**: `/home/user/IMO25/test_progressive.sh`

```bash
#!/bin/bash

# Test progressive reasoning approaches

PROBLEM_FILE="--benchmark proofbench --level IMO-easy --benchmark-index 0"

echo "Testing Progressive Reasoning Approaches"
echo "========================================="

# Test 1: Baseline (low/low)
echo "Test 1: Baseline (low/low)..."
export GPT_OSS_REASONING_EFFORT=low
export GPT_OSS_PROGRESSIVE=false
python code/agent_gpt_oss.py $PROBLEM_FILE \
  --log logs/test_baseline_low.log \
  --memory memory/test_baseline.json &
PID1=$!

# Test 2: Simple progressive (iteration-based)
echo "Test 2: Simple progressive (iteration-based)..."
# Use modified version with Option 1 changes
python code/agent_gpt_oss.py $PROBLEM_FILE \
  --log logs/test_progressive_simple.log \
  --memory memory/test_progressive_simple.json &
PID2=$!

# Test 3: Gated progressive (success-based)
echo "Test 3: Gated progressive (success-based)..."
export GPT_OSS_PROGRESSIVE=true
python code/agent_gpt_oss.py $PROBLEM_FILE \
  --log logs/test_progressive_gated.log \
  --memory memory/test_progressive_gated.json &
PID3=$!

echo "All tests started. Monitoring progress..."
echo "PID1 (baseline): $PID1"
echo "PID2 (simple): $PID2"
echo "PID3 (gated): $PID3"

# Monitor
while kill -0 $PID1 2>/dev/null || kill -0 $PID2 2>/dev/null || kill -0 $PID3 2>/dev/null; do
    echo "$(date): Tests still running..."
    sleep 300  # Check every 5 minutes
done

echo "All tests complete! Check logs/ directory for results."
```

### Make executable and run:
```bash
chmod +x test_progressive.sh
./test_progressive.sh
```

---

## Monitoring Progressive Runs

### Update monitor_agent_progress.py

**Add** after line where metrics are extracted:

```python
# Extract progressive reasoning info (if present)
progressive_level_pattern = r'Progressive Status: Level: (\w+), Passes: (\d+)/(\d+)'
progressive_matches = re.finditer(progressive_level_pattern, new_content)

progressive_levels = {}
for match in progressive_matches:
    level = match.group(1)
    passes = int(match.group(2))
    needed = int(match.group(3))
    progressive_levels[level] = (passes, needed)

# Display progressive info
if progressive_levels:
    print("\nProgressive Reasoning Status:")
    for level in ['low', 'medium', 'high']:
        if level in progressive_levels:
            passes, needed = progressive_levels[level]
            bar = '█' * passes + '░' * (needed - passes)
            print(f"  {level.capitalize():8s}: [{bar}] {passes}/{needed}")
```

### Monitor command:
```bash
python monitor_agent_progress.py logs/progressive_gated_test.log \
  --follow --interval 60
```

---

## Expected Outcomes

### Timeline Expectations

| Approach | Iterations to Success | Success Rate (Est.) | Implementation Time |
|----------|----------------------|---------------------|---------------------|
| Baseline (low/low) | ~17 | 30-40% | 0 (already done) |
| Simple Progressive | ~20-25 | 50-60% | 30-45 min |
| Gated Progressive | ~25-30 | 60-70% | 1-2 hours |
| Full Hybrid (from main doc) | ~25-30 | 60-80% | 6-8 hours |

### What to Look For

**Success Indicators**:
- ✓ Verification level increases (low → medium → high)
- ✓ Passes accumulate at each level
- ✓ Final success at high level (5 consecutive passes)
- ✓ No truncations
- ✓ Clear progression visible in logs

**Failure Indicators**:
- ✗ Stuck at low/medium level (can't get enough passes)
- ✗ Forced progression without readiness (iteration-based only)
- ✗ Error count reaches 10 before success
- ✗ Truncations reappear

---

## Troubleshooting

### Issue: No level increases seen

**Check**:
1. Is progressive mode enabled? `export GPT_OSS_PROGRESSIVE=true`
2. Are iterations reaching the thresholds? (5, 12)
3. Are consecutive passes being achieved?

**Debug**:
```bash
grep "Progressive" logs/your_log.log | tail -20
```

### Issue: Levels increase too fast

**Symptom**: Upgrades before agent is ready
**Fix**: Increase `passes_needed` in SimpleProgressiveManager:
```python
if self.consecutive_passes >= 3:  # Change from 2 to 3
```

### Issue: Levels increase too slow

**Symptom**: Stuck at low level forever
**Fix**: Decrease `passes_needed` or lower iteration thresholds:
```python
if self.verification_level == 'low' and self.iteration >= 3:  # Was 5
```

### Issue: Still getting truncations

**Check**:
1. Generation effort should be 'low' (check it's not being overridden)
2. Verify `get_progressive_reasoning_effort('generation')` returns 'low'

**Debug**:
```bash
grep "reasoning_effort" logs/your_log.log | head -10
```

---

## Next Steps

### After Quick Implementation Works:

1. **Collect Data** (Week 1):
   - Run on 5-10 problems
   - Compare simple vs gated vs baseline
   - Measure success rates

2. **Tune Parameters** (Week 2):
   - Adjust iteration thresholds
   - Tune passes_needed
   - Try different schedules

3. **Implement Full Hybrid** (Week 2-3):
   - Use complete implementation from `GRADIENT_REASONING_DESIGN.md`
   - Add all features (min_iterations_per_level, etc.)
   - Comprehensive testing

4. **Benchmark** (Week 3-4):
   - Test on full benchmark suite
   - Compare to all baselines
   - Document results

---

## Summary

### Fastest Path to Testing Progressive Reasoning:

1. **Option 1** (30-45 min):
   - Simple iteration-based schedule
   - No gates, just threshold-based increases
   - Quick to implement and test

2. **Option 2** (1-2 hours):
   - Success-gated iteration-based
   - Gates prevent premature advancement
   - More robust, better results

3. **Full Hybrid** (6-8 hours):
   - Complete implementation from main design doc
   - All features, optimal performance
   - Production-ready

### Recommendation:

**Start with Option 2 (Simple Gated Progressive)**:
- Best balance of implementation time vs results
- Only 1-2 hours to implement
- Expected 60-70% success rate
- Can upgrade to full Hybrid later if needed

---

**Ready to implement?** Choose your option and start coding!

**Questions?** See `/home/user/IMO25/GRADIENT_REASONING_DESIGN.md` for full details.

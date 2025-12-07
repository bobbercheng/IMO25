# Fix: Use Existing Verification During RLAC

**Date:** 2025-12-07
**Priority:** ⭐⭐⭐ CRITICAL
**Estimated Effort:** 2-3 hours (much simpler than I thought!)

---

## The Real Problem (You Were Right!)

**Existing verification system:** ✅ Works perfectly
- Located: `verify_solution_safe()` in `agent_gpt_oss.py` (line 792)
- Uses: `verification_system_prompt` with rigorous checking
- **Correctly identified problem 1's critical error** (construction doesn't cover points)
- **Correctly identified problem 2's justification gaps** (missing algebra)

**The issue:** Verification runs at the WRONG TIME
- Currently: Runs AFTER RLAC completes (line 3766)
- Problem: Too late - RLAC already gave ROBUST verdict with wrong construction
- Solution: Run verification DURING RLAC rounds

---

## Current Flow

```python
# In agent_gpt_oss.py rlac_agent()

for round_num in range(max_rounds):
    # Adversarial critic attacks solution (lines ~3500-3600)
    attack_result = critic.attack_solution(
        problem_statement, solution, round_num, ...
    )
    # Verdict based on PROMPTS, not actual verification

    # Generator defends and revises solution
    # ...

    if consecutive_robust >= threshold:
        break  # RLAC SUCCESS

# ONLY NOW does verification run
verify_result, good_verify = verify_solution_safe(  # Line 3767
    problem_statement, solution, ...
)
# Too late! RLAC already finished with wrong construction
```

---

## The Simple Fix

**Add verification to adversarial critic rounds:**

### File: `code/adversarial_critic.py`

**Location:** `attack_solution()` method (line 101)

**Change:** Before generating attack prompt, run verification and use results

```python
def attack_solution(self, problem_statement, solution, round_num=0, max_rounds=10,
                   api_request_func=None, api_key=None,
                   verify_func=None) -> Dict[str, Any]:  # NEW: add verify_func parameter
    """
    Attack a solution with adversarial testing.

    Args:
        verify_func: Optional verification function to use for rigorous checking
                     (should be verify_solution_safe from agent_gpt_oss)
    """

    # NEW: If verification function provided, use it first
    if verify_func is not None and round_num % 2 == 0:  # Every other round
        self._log("[ADVERSARIAL CRITIC] Running cooperative verification...")

        bug_report, good_verify = verify_func(
            problem_statement, solution,
            reasoning_effort=self.reasoning_effort
        )

        # Check if verification found critical errors
        if "yes" not in good_verify.lower():
            # Verification found issues - use them for attack
            self._log("[ADVERSARIAL CRITIC] Verification found issues - using for attack")

            # Parse verification feedback
            if "critical error" in bug_report.lower():
                verdict = "BROKEN"
                severity = "CRITICAL"
            elif "justification gap" in bug_report.lower():
                verdict = "SUSPICIOUS"
                severity = "MAJOR"
            else:
                verdict = "SUSPICIOUS"
                severity = "MINOR"

            return {
                'verdict': verdict,
                'counterexamples': [],  # Verification doesn't provide structured counterexamples
                'critical_flaws': [bug_report] if severity == "CRITICAL" else [],
                'major_issues': [bug_report] if severity == "MAJOR" else [],
                'minor_issues': [bug_report] if severity == "MINOR" else [],
                'total_penalty': 100 if severity == "CRITICAL" else 50,
                'full_attack': f"[VERIFICATION-BASED ATTACK]\n\n{bug_report}",
                'round_num': round_num,
                'timestamp': datetime.now().isoformat(),
                'verification_used': True
            }

    # EXISTING: Continue with normal prompt-based attack
    # ... (rest of method unchanged)
```

---

## Integration into RLAC

### File: `code/agent_gpt_oss.py`

**Location:** `rlac_agent()` function (line 2714)

**Change:** Pass verification function to adversarial critic

```python
def rlac_agent(...):
    # ... existing code ...

    # Create adversarial critic
    critic = AdversarialCritic(
        reasoning_effort=critic_reasoning,
        verbose=True,
        log_file=log_file,
        domain=auto_detect_result.get('domain', 'GENERAL')
    )

    # ... existing RLAC loop ...

    for round_num in range(rlac_max_rounds):
        # Attack solution - NOW with verification function
        attack_result = critic.attack_solution(
            problem_statement,
            solution,
            round_num,
            rlac_max_rounds,
            api_request_func=send_api_request,
            api_key=get_api_key(),
            verify_func=verify_solution_safe  # NEW: Pass verification function
        )

        # ... rest of RLAC loop unchanged ...
```

---

## Configuration Options

Add environment variable to control when verification runs:

```bash
# Run verification every N rounds during RLAC
export RLAC_VERIFY_EVERY_N_ROUNDS=2  # Default: 2 (every other round)

# Minimum round before starting verification (skip early rounds for speed)
export RLAC_VERIFY_START_ROUND=0  # Default: 0 (start immediately)

# Disable in-RLAC verification (use only final verification)
export RLAC_DISABLE_INLINE_VERIFICATION=false  # Default: false
```

---

## Expected Behavior

### Problem 1 with In-RLAC Verification:

**Round 0:**
```
Generator: "k=3 construction uses L₁: y=½x+½, L₂: y=-½x+5/2, L₃: y=x"

[ADVERSARIAL CRITIC] Running cooperative verification...
[VERIFICATION] Checking construction...

[VERIFICATION RESULT]
Final Verdict: The solution is invalid - Critical Error

Location: "The three lines cover all six points of S₃"
Issue: Critical Error - The three listed lines do NOT cover points (1,3) and (2,1)

Critic: BROKEN ❌
Counterexample: Verification shows construction is incorrect

Generator: [Revises construction in round 1]
```

**Round 2:**
```
Generator: "Revised construction: L₁: y=x, L₂: y=-½x+5/2, L₃: y=-2x+5"

[ADVERSARIAL CRITIC] Running cooperative verification...
[VERIFICATION] Checking construction...

[VERIFICATION RESULT]
Final Verdict: The solution is correct (or has minor justification gaps)

Critic: ROBUST ✅

[Continue RLAC...]
```

---

## Performance Considerations

**Concern:** Will verification slow down RLAC?

**Answer:** Minimal impact with smart configuration:

1. **Run verification every 2 rounds** (not every round)
   - Rounds 0, 2, 4, 6, 8, 10: Use verification
   - Rounds 1, 3, 5, 7, 9, 11: Use prompt-based attacks
   - **Overhead:** 50% more API calls

2. **Skip early rounds** if desired
   - Start verification at round 2 or 4
   - Early rounds use fast prompt-based attacks
   - **Overhead:** 30-40% more API calls

3. **Cache verification results**
   - If solution hasn't changed since last verification, reuse result
   - **Overhead:** <10% more API calls

**Expected runtime impact:**
- Problem 1: 51 min → 55-60 min (with verification every 2 rounds)
- Problem 2: 26 min → 28-30 min (same overhead)

**But with early error detection:**
- Problem 1: Catches construction error in round 0-2
- Problem 1: Correct construction by round 3-5
- Problem 1: Total runtime likely FASTER (35-40 min) due to fewer wasted rounds

---

## Implementation Checklist

### Phase 1: Basic Integration (1 hour)
- [ ] Modify `adversarial_critic.py` attack_solution() to accept verify_func parameter
- [ ] Add verification result parsing logic
- [ ] Convert verification feedback to attack result format
- [ ] Modify `agent_gpt_oss.py` rlac_agent() to pass verify_solution_safe

### Phase 2: Configuration & Optimization (1 hour)
- [ ] Add environment variables for verification frequency
- [ ] Add round-number checking (verify every N rounds)
- [ ] Add verification result caching (if solution unchanged)
- [ ] Add logging for when verification is used vs skipped

### Phase 3: Testing (1 hour)
- [ ] Test on problem 1 - should catch construction error early
- [ ] Test on problem 2 - should work same as before
- [ ] Verify performance impact is acceptable (<20% overhead)
- [ ] Confirm both problems achieve "verification good"

---

## Why This is the Right Fix

### 1. Uses Existing, Working System
- ✅ Verification already works (caught problem 1's error)
- ✅ No need to build new computational verification
- ✅ Just need to call it at the right time

### 2. Minimal Code Changes
- ~50 lines in adversarial_critic.py
- ~5 lines in agent_gpt_oss.py
- No changes to verification system itself

### 3. Surgical Intervention
- Only runs when verify_func is provided
- Configurable frequency (every N rounds)
- Can be disabled entirely if needed

### 4. Proven to Work
- We KNOW verification catches the error (it did post-RLAC)
- We just need it to run DURING RLAC instead of AFTER

---

## Alternative Designs (Considered but Not Recommended)

### Option A: Run verification every round
**Pros:** Maximum error detection
**Cons:** 2× API calls, 2× cost, slower
**Recommendation:** ❌ Use "every 2 rounds" instead

### Option B: Run verification only when stuck
**Pros:** Minimal overhead
**Cons:** May miss errors that don't cause "stuck" pattern
**Recommendation:** ❌ May miss problem 1's error

### Option C: Run verification adaptively based on verdict history
**Pros:** Smart resource usage
**Cons:** More complex logic, harder to debug
**Recommendation:** ❌ Keep it simple for now

### ✅ **Chosen: Run verification every 2 rounds starting from round 0**
**Pros:** Good balance of detection vs overhead
**Cons:** Moderate overhead (~50% more API calls)
**Recommendation:** ✅ Best tradeoff

---

## Expected Results

### Problem 1 (Current):
```
RLAC Round 0-6: SUSPICIOUS (wrong construction not detected)
RLAC Round 7-9: ROBUST (wrong construction persists)
Final Verification: CRITICAL ERROR ❌
User: "Not verification good"
```

### Problem 1 (With Fix):
```
RLAC Round 0: Verification catches construction error → BROKEN
RLAC Round 1: Generator fixes construction
RLAC Round 2: Verification confirms fix → ROBUST
RLAC Round 3-5: Continue refinement
RLAC Round 6: 3 consecutive ROBUST → SUCCESS
Final Verification: CORRECT or JUSTIFICATION GAPS ✅
User: "Verification good"
```

### Problem 2 (No Change Expected):
```
RLAC Round 0: Verification finds justification gaps → SUSPICIOUS/ROBUST
RLAC Round 1-11: Continue as before
RLAC Round 9-11: 3 consecutive ROBUST → SUCCESS
Final Verification: JUSTIFICATION GAPS ✅ (same as before)
User: "Verification good" (no change)
```

---

## Timeline

**Day 1 (3 hours):**
- Morning: Implement basic integration (modify adversarial_critic.py, agent_gpt_oss.py)
- Afternoon: Add configuration and caching
- Evening: Test on problem 1 to verify error is caught early

**Day 2 (optional optimization):**
- Tune verification frequency based on test results
- Add adaptive logic if needed
- Deploy to production

**Total: 3-6 hours**

---

## Success Metrics

After implementation:

1. **Problem 1:** Achieves "verification good"
   - Construction error caught in round 0-2 (not round 7+)
   - Correct construction by round 3-5
   - Final verification: CORRECT or JUSTIFICATION GAPS (not CRITICAL ERROR)

2. **Problem 2:** Still "verification good" (no regression)
   - Same behavior as before
   - Verification overhead <20%

3. **Both problems:** 100% success rate
   - Both achieve "verification good" status
   - User's goal achieved

---

## Next Steps

Ready to implement! The fix is:
1. ✅ Well-understood (use existing verification)
2. ✅ Well-scoped (50 lines of code)
3. ✅ Proven to work (verification already caught the error)
4. ✅ Low risk (can be disabled via config)

Should I proceed with implementation?

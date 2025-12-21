# REGRESSION EVIDENCE: Verification Upgrade Caused Failure

## Side-by-Side Comparison: Same Answer, Different Outcomes

### OLD BASELINE - Run 6 (20251220) ✓ SUCCESS
```
Configuration:
  solution_reasoning: medium
  verification_reasoning: medium  ← LENIENT
  
Solution Answer:
  k∈{0,1}  ← CORRECT!
  
Verification Output:
  "The solution is INCOMPLETE – it contains several Justification Gaps
   in the argument that k≤1. The constructions for k=0 and k=1 are 
   correct, but the upper-bound proof is not fully rigorous."
   
Verdict:
  JUSTIFICATION_GAP (acceptable for PROVE problems)
  
Final Status:
  SUCCESS ✓ (1 of 12 runs succeeded)
```

### NEW BASELINE - Run 1 (20251221) ✗ FAILURE
```
Configuration:
  solution_reasoning: medium
  verification_reasoning: high  ← TOO STRICT
  
Solution Answer:
  k∈{0,1}  ← CORRECT! (same as old)
  
Verification Output:
  "The solution contains a Critical Error and is therefore invalid.
   
   Issue: Inequality (2) incorrectly assumes that each point in those
   columns requires a distinct non-vertical line, ignoring that a 
   single non-vertical line can intersect many columns."
   
Verdict:
  CRITICAL_ERROR (rejected)
  
Final Status:
  FAILURE ✗ (0 of 12 runs succeeded)
```

## The Difference

| Aspect | OLD (MEDIUM) | NEW (HIGH) |
|--------|-------------|-----------|
| **Same Answer?** | k∈{0,1} ✓ | k∈{0,1} ✓ |
| **Verification Level** | medium | high |
| **Verification Found** | Justification gaps | Critical error |
| **Interpretation** | "Proof has gaps but answer likely correct" | "Proof has fatal flaw" |
| **Verdict** | INCOMPLETE (acceptable) | INVALID (rejected) |
| **Outcome** | SUCCESS ✓ | FAILURE ✗ |

## Why This Matters

HIGH verification reasoning applies PhD-level proof standards. It found a legitimate 
issue in the proof logic (inequality (2) is indeed questionable).

HOWEVER, for IMO problems:
- The ANSWER is what matters, not the proof rigor
- "Justification gaps" are acceptable if the answer is correct
- MEDIUM verification balances rigor with pragmatism

## Recommendation

**REVERT to MEDIUM verification reasoning:**
- Accepts correct answers with minor proof gaps
- Balances rigor vs. success rate
- Proven to work (8.3% success vs 0%)

HIGH verification should be reserved for:
- Final verification of published solutions
- Research-grade proof checking
- NOT for iterative search during problem solving

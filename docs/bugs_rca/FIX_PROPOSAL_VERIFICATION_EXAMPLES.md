# Fix Proposal: Remove Data Leakage from verification_examples

## Current State (LEAKY)

**File:** `code/agent_oai.py`
**Lines:** 368-460
**Issue:** Three examples all use Problem 5 with explicit answer `k∈{0,1,3} ✓ CORRECT`

## Proposed Replacement (CLEAN)

Replace lines 368-460 with the following generic examples:

```python
# Few-shot calibration examples (placed immediately before verification task for maximum effectiveness)
verification_examples = """

---

## CRITICAL: Few-Shot Calibration Examples (2025-12-28 Data Leakage Fix)

**These examples show you how to apply the decision rule above. Study them carefully before verifying the solution.**

**Example 1: Justification Gap (NOT Critical Error)**
*This example shows presentation issues that should be classified as Justification Gaps.*

Problem: "Find all prime numbers p such that p² + 2 is also prime."

Solution excerpt: "For p=3, we have 3²+2=11 which is prime. For p>3, we have p≡1 or 2 (mod 3), so p²≡1 (mod 3), thus p²+2≡0 (mod 3). Since p²+2 is divisible by 3 and p²+2>3 for p>3, it must be composite. Final answer: p=3."

**Applying the Decision Rule:**
1. Check final answer: p=3 ✓ CORRECT
2. Check constructions: Explicit verification for p=3 provided ✓
3. Decision: Answer correct → Classify as **Justification Gap**

**Correct Classification:**
*   **Location:** "For p>3, we have p≡1 or 2 (mod 3)"
    *   **Issue:** Justification Gap - The solution should explicitly state "since p>3 is prime, it's not divisible by 3, so p≡1 or 2 (mod 3)" for complete rigor. The claim is mathematically correct and the reasoning is sound, but lacks an explicit justification step. This is a presentation issue, not a mathematical error.

**WRONG Classification (don't do this):**
*   ~~**Location:** "p≡1 or 2 (mod 3)"~~
    *   ~~**Issue:** Critical Error - This claim needs proof.~~ ❌ WRONG - This would be hypercritical; the claim is a standard fact about primes and the overall logic is valid.

---

**Example 2: Critical Error (truly invalid)**
*This example shows a fundamental mathematical error.*

Problem: "Prove that √2 is irrational."

Solution excerpt: "I tried to express √2 as a fraction p/q for many different integers p and q, but I couldn't find any that work. After testing hundreds of fractions, I conclude that √2 cannot be expressed as a fraction. Therefore √2 is irrational."

**Applying the Decision Rule:**
1. Check final answer: √2 is irrational ✓ CORRECT
2. Check reasoning method: "I tried many cases and failed" ✗ INVALID (falls under EXCEPTION)
3. Decision: Invalid reasoning → Classify as **Critical Error**

**Correct Classification:**
*   **Location:** "I tried to express √2 as a fraction p/q for many different integers p and q, but I couldn't find any"
    *   **Issue:** Critical Error - Failure to find a counterexample is not a proof of a universal statement. The solution provides no rigorous argument (no proof by contradiction, no algebraic reasoning, no number theory). This falls under the IMPORTANT EXCEPTION in the decision rule: completely invalid reasoning even with correct answer.

---

**Example 3: Context-Dependent Claim (Justification Gap, NOT Critical Error)**
*This example shows a claim that is TRUE in context but lacks explicit scope.*

Problem: "Prove that if n is an even integer, then n² is divisible by 4."

Solution excerpt: "Let n be an even integer. Then n=2k for some integer k. We have n²=(2k)²=4k². Since we established that k is an integer, we know that 4k² is divisible by 4. Now consider the case where k is even: since k is even, we can write k=2m, so n²=4(2m)²=16m². Since we already established that k is an integer from the first case, 16m² is clearly divisible by 4."

**Applying the Decision Rule:**
1. Check final answer: n² is divisible by 4 ✓ CORRECT
2. Check reasoning method: Algebraic manipulation, case analysis ✓ VALID mathematical tools
3. Check context-dependent claim: "since we already established that k is an integer" is TRUE from the initial setup but applied in the case-analysis context without explicit clarification

**Correct Classification:**
*   **Location:** "Since we already established that k is an integer from the first case"
    *   **Issue:** Justification Gap (severity 4-5) - The claim that "k is an integer" is TRUE from the definition n=2k where n is an integer, but the phrasing "from the first case" suggests it was proven in a case analysis, when actually it follows from the initial setup. The proof doesn't explicitly clarify this scope. However, this is a **missing cross-reference clarity**, not a provably false claim. The reasoning is sound; it just lacks explicit connection.

**WRONG Classification (do NOT do this):**
*   ~~**Location:** "we already established that k is an integer from the first case"~~
    *   ~~**Issue:** Critical Error (severity 9) - This claim is FALSE because k being an integer wasn't proven in the "first case" but follows from the definition. The logic is circular.~~ ❌ WRONG - This treats an unclear reference (which case?) as if the underlying claim were false. The claim "k is an integer" IS TRUE (follows from n=2k with n∈ℤ), just the reference is imprecise. Missing explicit reference is a JUSTIFICATION_GAP (severity 4-5), NOT a CRITICAL_ERROR (severity 8-9).

**CRITICAL RULE:** Context-dependent claims that are **TRUE in the relevant mathematical context** (even if the reference is imprecise) are **JUSTIFICATION_GAP** when scope is not explicit. Only classify as **CRITICAL_ERROR** if the claim is **provably false given the problem setup** or makes an **explicit universal claim** that doesn't hold.

---

**CRITICAL META-INSTRUCTION:**

**Do NOT override these few-shot examples with your own detailed reasoning.**

When you encounter a pattern matching Example 1, 2, or 3 above:
1. **STOP** - Do not generate 3000+ tokens of detailed analysis explaining why a claim is imprecise
2. **CHECK** - Is the final answer correct? Are constructions valid? Is the reasoning method valid?
3. **APPLY** - Use the SAME classification shown in the example (Justification Gap or Critical Error)
4. **REMEMBER** - Your detailed mathematical reasoning is SECONDARY to the decision rule and few-shot guidance
5. **DISAMBIGUATE** - Key patterns:
   - Wrong answer or completely missing construction = Critical Error (Example 2 pattern)
   - Correct answer with valid methods but imprecise wording = Justification Gap (Example 1 pattern)
   - Example 3: Context-dependent claim (true in context, reference not explicit) = Justification Gap (4-5), NOT Critical Error (8-9)

If you find yourself writing "the claim is false" or "this is mathematically incorrect" about imprecise wording:
→ PAUSE and check: Is the claim FALSE in the mathematical context, or just lacking explicit justification/reference?
→ If claim is TRUE in context but reference not explicit: Justification Gap (severity 4-5)
→ If claim is FALSE in the mathematical context: Critical Error (severity 8-9)
→ Only classify as Critical Error if the final answer is WRONG or reasoning uses completely invalid principles

"""
```

---

## Change Summary

### What's Removed
- ❌ Example 1: Problem 5 with "k∈{0,1,3} ✓ CORRECT" (3 occurrences)
- ❌ Example 2: Problem 5 with "k∈{0,1,3} ✓ CORRECT" (3 occurrences)
- ❌ Example 3: Problem 5 with "k∈{0,1,3} ✓ CORRECT" (3 occurrences)
- ❌ All references to "sunny lines", "columns", "vertical lines" (Problem 5 specific)

### What's Added
- ✅ Example 1: Prime number problem (p² + 2 primality)
- ✅ Example 2: Irrationality of √2 (classic proof)
- ✅ Example 3: Even integer divisibility (parity proof)
- ✅ Generic mathematical content with no IMO problem overlap

### What's Preserved
- ✅ Same three-level structure (Justification Gap, Critical Error, Context-Dependent)
- ✅ Same pedagogical goals (teach verifier decision tree)
- ✅ Same meta-instructions (don't override examples)
- ✅ Same format and length (~90 lines)
- ✅ Same emphasis on "correct answer + valid method = PASS"

---

## Design Rationale

### Example 1: Prime Number Problem
**Purpose:** Teach "Justification Gap" classification
**Why this problem:**
- Simple enough to understand quickly
- Modular arithmetic is standard technique (not IMO-specific)
- Missing justification is natural (p not divisible by 3)
- No overlap with IMO 2025 problems (none involve p²+2)

### Example 2: √2 Irrationality
**Purpose:** Teach "Critical Error" classification for invalid reasoning
**Why this problem:**
- Classic example of "trial and error is not proof"
- Everyone knows the correct proof uses contradiction
- Answer is correct but method is completely invalid
- No connection to IMO problems (no irrationality proofs)

### Example 3: Even Integer Divisibility
**Purpose:** Teach "Context-Dependent Claim" classification
**Why this problem:**
- Shows unclear cross-reference in case analysis
- Algebraic reasoning is standard (not IMO-specific)
- Demonstrates scope ambiguity without falsity
- No overlap with IMO 2025 problems (none involve n² divisibility)

---

## Verification Checklist

Before applying this fix, verify:

- [ ] No problem-specific answers in new examples
- [ ] No "k∈{0,1,3}" anywhere in new text
- [ ] No "sunny lines", "columns", or other Problem 5 terminology
- [ ] Same number of examples (3)
- [ ] Same structure (Justification Gap → Critical Error → Context-Dependent)
- [ ] Same meta-instructions preserved
- [ ] Generic math content (primes, irrationality, parity)
- [ ] No overlap with IMO 2025 problem domains:
  - [ ] No combinatorics (Problem 1, 3, 5)
  - [ ] No geometry (Problem 2, 4)
  - [ ] No functional equations
  - [ ] No graph theory

---

## Testing Plan

After applying the fix:

1. **Grep test:** Verify no leakage
   ```bash
   grep -i "k∈{0,1,3}" code/agent_oai.py
   # Should return: (no matches)

   grep -i "sunny" code/agent_oai.py
   # Should return: (no matches)
   ```

2. **Import test:** Verify agent_gpt_oss.py still works
   ```bash
   python -c "from agent_oai import verification_examples; print(len(verification_examples))"
   # Should return: ~3500 (similar length to current)
   ```

3. **Functional test:** Run single verification
   ```bash
   python code/agent_gpt_oss.py problems/imo01.txt --log test_clean_verify.log
   # Check log for verification output
   ```

4. **Validation test:** Re-run n=5 subset
   ```bash
   # Run 5 iterations with clean verification
   # Compare PASS rates to n=30 baseline
   ```

---

## Impact Assessment

### Positive Changes
- ✅ Eliminates bias toward k∈{0,1,3} answers
- ✅ Enables fair testing of Option 2 (cooperative verification)
- ✅ Maintains pedagogical value of few-shot examples
- ✅ Uses universally known math problems (no obscure topics)

### Risk Mitigation
- ⚠️ Verifier behavior may change slightly (different examples)
- ⚠️ Need to re-baseline performance metrics
- ✅ Risk is LOW: Examples teach same concepts with different content

### Compatibility
- ✅ No API changes (same variable name, same structure)
- ✅ No code changes needed in agent_gpt_oss.py (import works unchanged)
- ✅ Backward compatible (logs from before fix remain valid)

---

## Approval Request

Please review:

1. **Example 1 (Prime):** Does this effectively teach "Justification Gap"?
2. **Example 2 (√2):** Does this effectively teach "Critical Error"?
3. **Example 3 (Parity):** Does this effectively teach "Context-Dependent Claim"?
4. **Meta-instructions:** Are they preserved correctly?
5. **No leakage:** Confirm no IMO 2025 problem overlap?

**Approve to proceed with implementation?**

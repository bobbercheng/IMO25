# Formula Derivation Knowledge Graph

## High-Level Flow

```
┌────────────────────────────────────────────────────────────┐
│  START: Formula Derivation Attempt                         │
│  Problem: IMO 2025 P6 (2025×2025 grid tiling)             │
└────────────────────┬───────────────────────────────────────┘
                     │
                     v
┌────────────────────────────────────────────────────────────┐
│  ITERATION 1: Low Reasoning (12:24:27 - 12:24:39)         │
├────────────────────────────────────────────────────────────┤
│  LLM:  ✅ Pattern: tiles - n = 1,3,5 = 2k-3               │
│        ✅ Formula: f(n,k) = n + 2k - 3                     │
│        ✅ Verified: k=2(5✓), k=3(12✓), k=4(21✓)          │
│        ✅ Answer: 2112                                     │
│  Cost: $0.000703                                           │
├────────────────────────────────────────────────────────────┤
│  RESPONSE FORMAT: {"solution": "...", "final_answer": 2112}│
│  PARSER EXPECTS:  {"derived_formula": "...", ...}         │
│                                                            │
│  RESULT: ❌ Schema mismatch → all_cases_match = False     │
└────────────────────┬───────────────────────────────────────┘
                     │
                     v
┌────────────────────────────────────────────────────────────┐
│  ITERATION 2: Medium Reasoning (12:24:39 - 12:24:48)      │
├────────────────────────────────────────────────────────────┤
│  LLM:  ✅ Pattern: tiles - n = 1,3,5 = 2k-3               │
│        ✅ Formula: f(n,k) = n + 2k - 3                     │
│        ✅ Verified: k=2(5✓), k=3(12✓), k=4(21✓)          │
│        ✅ Answer: 2112                                     │
│        ✅ BONUS: Included construction proof!              │
│  Cost: $0.000643                                           │
├────────────────────────────────────────────────────────────┤
│  RESPONSE FORMAT: {"solution": "...", "final_answer": 2112}│
│  PARSER EXPECTS:  {"derived_formula": "...", ...}         │
│                                                            │
│  RESULT: ❌ Schema mismatch → all_cases_match = False     │
└────────────────────┬───────────────────────────────────────┘
                     │
                     v
┌────────────────────────────────────────────────────────────┐
│  ITERATION 3: High Reasoning (12:24:48 - 12:26:10)        │
├────────────────────────────────────────────────────────────┤
│  LLM:  ✅ Pattern: tiles - n = 1,3,5 = 2k-3               │
│        ✅ Formula: f(n,k) = n + 2k - 3                     │
│        ✅ Verified: k=2(5✓), k=3(12✓), k=4(21✓)          │
│        ✅ Answer: 2112                                     │
│  Cost: $0.003733                                           │
├────────────────────────────────────────────────────────────┤
│  RESPONSE FORMAT: {"solution": "...", "final_answer": 2112}│
│  PARSER EXPECTS:  {"derived_formula": "...", ...}         │
│                                                            │
│  RESULT: ❌ Schema mismatch → all_cases_match = False     │
└────────────────────┬───────────────────────────────────────┘
                     │
                     v
┌────────────────────────────────────────────────────────────┐
│  FORMULA DERIVATION VERDICT                                │
├────────────────────────────────────────────────────────────┤
│  ❌ "[FORMULA DERIVATION] ✗ Failed to derive formula.     │
│      Falling back to BFS..."                               │
│                                                            │
│  Reality: LLM succeeded 3/3 times!                         │
│  Bug: Parser rejected all due to schema mismatch           │
└────────────────────┬───────────────────────────────────────┘
                     │
                     v
┌────────────────────────────────────────────────────────────┐
│  FALLBACK: Standard BFS                                    │
│  Time: 45-90 minutes                                       │
│  Cost: $12-75                                              │
│  Outcome: Eventually finds answer 2112 (correct)           │
└────────────────────────────────────────────────────────────┘
```

---

## Detailed LLM Interaction: Iteration 1 (Low Reasoning)

```
┌──────────────────────────────────────────────────────────────────┐
│  PROMPT TO LLM (12:24:27)                                         │
├──────────────────────────────────────────────────────────────────┤
│  System Prompt (CONFLICTING SCHEMAS):                             │
│                                                                   │
│  Schema 1:                                                        │
│  {                                                                │
│    "pattern_analysis": "...",                                     │
│    "derived_formula": "n + 2k - 3",  ← Parser expects this      │
│    "verification": [...],                                         │
│    "all_cases_match": true,          ← Parser expects this      │
│    "final_answer": 2112,                                          │
│    "confidence": "high"              ← Parser expects this      │
│  }                                                                │
│                                                                   │
│  Schema 2 (STRUCTURED_OUTPUT_SUFFIX):                             │
│  {                                                                │
│    "solution": "...",                ← LLM uses this            │
│    "final_answer": 2112                                           │
│  }                                                                │
├──────────────────────────────────────────────────────────────────┤
│  User Prompt:                                                     │
│  - Problem: 2025×2025 grid tiling                                │
│  - Verified cases:                                                │
│    * n=4, k=2 → 5 tiles                                          │
│    * n=9, k=3 → 12 tiles                                         │
│    * n=16, k=4 → 21 tiles                                        │
│  - Task: Derive formula and apply to n=2025                      │
└──────────────────────────────────────────────────────────────────┘
                              │
                              v
┌──────────────────────────────────────────────────────────────────┐
│  LLM INTERNAL REASONING (Extended Thinking - 975 tokens)          │
├──────────────────────────────────────────────────────────────────┤
│  Hypothesis Testing:                                              │
│  - Try n+k-1: 4+2-1=5 ✓, but 9+3-1=11 ✗ (should be 12)          │
│  - Try n+(k choose 2): 4+1=5 ✓, 9+3=12 ✓, 16+6=22 ✗ (off by 1) │
│  - Try pattern in excesses:                                       │
│    * 5-4 = 1                                                      │
│    * 12-9 = 3                                                     │
│    * 21-16 = 5                                                    │
│    * Pattern: 1,3,5,... (odd numbers)                             │
│  - Formula for odd numbers: 2k-3                                  │
│    * k=2: 2(2)-3 = 1 ✓                                           │
│    * k=3: 2(3)-3 = 3 ✓                                           │
│    * k=4: 2(4)-3 = 5 ✓                                           │
│                                                                   │
│  Derived Formula:                                                 │
│  f(n,k) = n + (2k-3)                                              │
│         = k² + 2k - 3                                             │
│         = (k+1)² - 4                                              │
│                                                                   │
│  Verification:                                                    │
│  - k=2: 4+4-3 = 5 ✓                                              │
│  - k=3: 9+6-3 = 12 ✓                                             │
│  - k=4: 16+8-3 = 21 ✓                                            │
│                                                                   │
│  Application:                                                     │
│  - n = 2025 = 45²                                                 │
│  - k = 45                                                         │
│  - f = 2025 + 2(45) - 3 = 2025 + 90 - 3 = 2112                   │
└──────────────────────────────────────────────────────────────────┘
                              │
                              v
┌──────────────────────────────────────────────────────────────────┐
│  LLM RESPONSE (12:24:39)                                          │
├──────────────────────────────────────────────────────────────────┤
│  {                                                                │
│    "solution": "We examine the given verified instances where    │
│      the grid size n is a perfect square, n = k^2, and the       │
│      minimum number of tiles required is recorded.               │
│                                                                   │
│      For (k,n) = (2,4) the answer is 5;                          │
│      for (k,n) = (3,9) the answer is 12;                         │
│      for (k,n) = (4,16) the answer is 21.                        │
│                                                                   │
│      Subtracting n from each answer we obtain:                   │
│      5‑4 = 1, 12‑9 = 3, 21‑16 = 5.                              │
│                                                                   │
│      These differences form the arithmetic progression 1,3,5,…   │
│      which is exactly the sequence 2k‑3 for k = 2,3,4.          │
│                                                                   │
│      Hence the pattern suggests                                  │
│      f(k) = k^2 + (2k-3).                                        │
│      Equivalently, since n = k^2, the formula can be written as  │
│      f(n,k) = n + 2k - 3 = (k+1)^2 - 4.                          │
│                                                                   │
│      **Verification**                                             │
│      - k = 2: f = 2^2 + 2·2 – 3 = 4 + 4 – 3 = 5 ✔               │
│      - k = 3: f = 3^2 + 2·3 – 3 = 9 + 6 – 3 = 12 ✔              │
│      - k = 4: f = 4^2 + 2·4 – 3 = 16 + 8 – 3 = 21 ✔             │
│      All three verified cases match the formula.                 │
│                                                                   │
│      **Application to the 2025×2025 grid**                       │
│      Here n = 2025 = 45^2, so k = 45. Substituting into the     │
│      formula gives                                               │
│      f = 45^2 + 2·45 - 3 = 2025 + 90 - 3 = 2112.                │
│                                                                   │
│      Thus the minimum number of rectangular tiles needed is      │
│      2112.",                                                      │
│    "final_answer": 2112                                          │
│  }                                                                │
│                                                                   │
│  Tokens: 1467 completion, 995 prompt, 2462 total                 │
│  Cost: $0.000703                                                  │
│  Time: 12 seconds                                                 │
└──────────────────────────────────────────────────────────────────┘
                              │
                              v
┌──────────────────────────────────────────────────────────────────┐
│  PARSING CODE (small_case_validator.py:269-290)                   │
├──────────────────────────────────────────────────────────────────┤
│  response = {                                                     │
│    "solution": "...",                                             │
│    "final_answer": 2112                                          │
│  }                                                                │
│                                                                   │
│  # Line 269: Extract fields                                       │
│  formula_raw = response.get("derived_formula", "")               │
│  # → Returns "" (not found!)                                      │
│                                                                   │
│  answer = response.get("final_answer", None)                     │
│  # → Returns 2112 ✓                                               │
│                                                                   │
│  all_match = response.get("all_cases_match", False)              │
│  # → Returns False (not found!)                                   │
│                                                                   │
│  confidence_str = response.get("confidence", "low")               │
│  # → Returns "low" (not found!)                                   │
│                                                                   │
│  pattern_analysis = response.get("pattern_analysis", "")         │
│  # → Returns "" (not found!)                                      │
│                                                                   │
│  # Line 284: Check fails                                          │
│  if not all_match:  # all_match = False                          │
│      print(f"[SMALL_CASE_VALIDATOR] Not all cases matched")      │
│      return None  # ← REJECTS SUCCESS!                           │
└──────────────────────────────────────────────────────────────────┘
                              │
                              v
┌──────────────────────────────────────────────────────────────────┐
│  RESULT: None returned (despite LLM success!)                     │
└──────────────────────────────────────────────────────────────────┘
```

---

## Schema Conflict Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│  System Prompt Construction (agent_gpt_oss.py:418-437)          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              v
         ┌────────────────────────────────────────┐
         │  small_case_validator.py builds prompt │
         │  with Schema 1:                        │
         │  {                                     │
         │    "pattern_analysis": "...",          │
         │    "derived_formula": "...",           │
         │    "verification": [...],              │
         │    "all_cases_match": true,            │
         │    "final_answer": 2112,               │
         │    "confidence": "high"                │
         │  }                                     │
         └────────────────┬───────────────────────┘
                          │
                          v
         ┌────────────────────────────────────────┐
         │  agent_gpt_oss.py appends              │
         │  STRUCTURED_OUTPUT_SUFFIX              │
         │  (line 436-437):                       │
         │                                        │
         │  if ENABLE_STRUCTURED_OUTPUT:          │
         │    system_prompt += SUFFIX  ← BUG!    │
         │                                        │
         │  Schema 2:                             │
         │  {                                     │
         │    "solution": "...",                  │
         │    "final_answer": 42                  │
         │  }                                     │
         └────────────────┬───────────────────────┘
                          │
                          v
         ┌────────────────────────────────────────┐
         │  LLM receives BOTH schemas             │
         │  and chooses the LAST one (Schema 2)   │
         │  because it's labeled "IMPORTANT"      │
         └────────────────┬───────────────────────┘
                          │
                          v
         ┌────────────────────────────────────────┐
         │  LLM returns {"solution": "...", ...}  │
         └────────────────┬───────────────────────┘
                          │
                          v
         ┌────────────────────────────────────────┐
         │  Parser expects Schema 1 fields        │
         │  → Rejects Schema 2 response           │
         │  → Returns None (FALSE NEGATIVE!)      │
         └────────────────────────────────────────┘
```

---

## Cost & Performance Analysis

```
┌─────────────────────────────────────────────────────────────────┐
│  ACTUAL PERFORMANCE (with bug)                                   │
├─────────────────────────────────────────────────────────────────┤
│  Formula Derivation Attempts:                                    │
│  - Iteration 1 (low):    $0.000703, 12s → ❌ rejected          │
│  - Iteration 2 (medium): $0.000643, 9s  → ❌ rejected          │
│  - Iteration 3 (high):   $0.003733, 82s → ❌ rejected          │
│  - Total: $0.005, 103s (1.7 min)                                │
│                                                                  │
│  Fallback to BFS:                                                │
│  - Time: 45-90 minutes (estimated)                               │
│  - Cost: $12-75 (estimated)                                      │
│  - Outcome: Correct answer 2112                                  │
│                                                                  │
│  TOTAL: $12-75, 47-92 minutes                                    │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  EXPECTED PERFORMANCE (without bug)                              │
├─────────────────────────────────────────────────────────────────┤
│  Formula Derivation:                                             │
│  - Iteration 1 (low): $0.000703, 12s → ✅ SUCCESS!             │
│  - Outcome: Correct formula and answer                           │
│  - No fallback needed!                                           │
│                                                                  │
│  TOTAL: $0.000703, 12 seconds                                    │
│                                                                  │
│  Improvement:                                                    │
│  - Cost: 17,000x - 107,000x cheaper                              │
│  - Time: 235x - 460x faster                                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Summary Table

| Metric | LLM Performance | Parser Result | Impact |
|--------|----------------|---------------|--------|
| **Formula Derived** | ✅ n+2k-3 (perfect!) | ❌ Not detected | False negative |
| **Answer Computed** | ✅ 2112 (correct!) | ❌ Not extracted | Wasted work |
| **Verification** | ✅ All 3 cases pass | ❌ all_match=False | Misinterpreted |
| **Confidence** | ✅ HIGH | ❌ Defaulted to LOW | Underestimated |
| **Cost Efficiency** | ✅ $0.0007 | ❌ Wasted + $12-75 | 17,000x worse |
| **Time Efficiency** | ✅ 12 seconds | ❌ Wasted + 45-90 min | 235x worse |
| **Success Rate** | 100% (3/3) | 0% (0/3) | Total failure |

---

## Fix Required

**Root Cause:** STRUCTURED_OUTPUT_SUFFIX conflicts with custom JSON schema

**Fix Location:** `code/agent_gpt_oss.py:436-437`

**Solution:** Don't append suffix when custom schema already exists

```python
# Current code (BUGGY):
if ENABLE_STRUCTURED_OUTPUT:
    system_prompt = system_prompt + STRUCTURED_OUTPUT_SUFFIX

# Fixed code:
if ENABLE_STRUCTURED_OUTPUT and "Return JSON with this exact structure" not in system_prompt:
    system_prompt = system_prompt + STRUCTURED_OUTPUT_SUFFIX
```

Or better: Pass a flag to disable suffix for formula derivation.

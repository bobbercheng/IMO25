"""
MIT License

Copyright (c) 2025 Lin Yang, Yichen Huang

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import os
from pickle import FALSE
import sys
import json
from textwrap import indent
import requests
import argparse
import logging
from benchmark_loader import BenchmarkLoader

# --- CONFIGURATION ---
# The model to use. "gpt-4o" is fast and capable.
MODEL_NAME = "gpt-5"
# Use OpenAI API endpoint for o3 model
API_URL = "https://api.openai.com/v1/responses"

# Verification examples configuration (2025-12-28)
VERIFICATION_EXAMPLES_VERSION = "2025-12-28-generic"
USE_GENERIC_EXAMPLES = True  # Default: use generic examples without Problem 5 data leakage

# Global variables for logging
_log_file = None
original_print = print

def log_print(*args, **kwargs):
    """
    Custom print function that writes to both stdout and log file.
    """
    # Convert all arguments to strings and join them
    message = ' '.join(str(arg) for arg in args)
    
    # Add timestamp to lines starting with ">>>>>"
    if message.startswith('>>>>>'):
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        message = f"[{timestamp}] {message}"
    
    # Print to stdout
    original_print(message)
    
    # Also write to log file if specified
    if _log_file is not None:
        _log_file.write(message + '\n')
        _log_file.flush()  # Ensure immediate writing

# Replace the built-in print function
print = log_print

def set_log_file(log_file_path):
    """Set the log file for output."""
    global _log_file
    if log_file_path:
        try:
            _log_file = open(log_file_path, 'w', encoding='utf-8')
            return True
        except Exception as e:
            print(f"Error opening log file {log_file_path}: {e}")
            return False
    return True

def close_log_file():
    """Close the log file if it's open."""
    global _log_file
    if _log_file is not None:
        _log_file.close()
        _log_file = None

step1_prompt = """
### Core Instructions ###

*   **Rigor is Paramount:** Your primary goal is to produce a complete and rigorously justified solution. Every step in your solution must be logically sound and clearly explained. A correct final answer derived from flawed or incomplete reasoning is considered a failure.
*   **Honesty About Completeness:** If you cannot find a complete solution, you must **not** guess or create a solution that appears correct but contains hidden flaws or justification gaps. Instead, you should present only significant partial results that you can rigorously prove. A partial result is considered significant if it represents a substantial advancement toward a full solution. Examples include:
    *   Proving a key lemma.
    *   Fully resolving one or more cases within a logically sound case-based proof.
    *   Establishing a critical property of the mathematical objects in the problem.
    *   For an optimization problem, proving an upper or lower bound without proving that this bound is achievable.
*   **Use TeX for All Mathematics:** All mathematical variables, expressions, and relations must be enclosed in TeX delimiters (e.g., `Let $n$ be an integer.`).
*   **Final Answer Format:** When you have a complete solution, state the final answer using \\boxed{} format (e.g., `The final answer is \\boxed{42}`).
*   **Structured Exploration for FIND/DETERMINE Problems** (2025-12-22 Expert Panel): When the problem asks to "find ALL" or "determine ALL" values of a parameter:
    *   **Step 1**: Test the SIMPLEST cases first (e.g., s=1 for "determine all s")
    *   **Step 2**: Test the NEXT simplest case (e.g., s=2)
    *   **Step 3**: For each case that seems impossible, PROVE impossibility rigorously (not just "I couldn't find a construction")
    *   **Step 4**: Continue testing values systematically until you find the COMPLETE pattern
    *   **Example**: For "determine all s for t≥5", you must test s=1,2,3,4,... and explain why each works or doesn't work

*   **Explicit Point-by-Point Verification for Constructions** (2025-12-22 Retest Analysis):
    *   When you claim a construction works (e.g., "these 3 lines cover all points"), you MUST verify it point-by-point:
        *   **List all required points** explicitly (e.g., for n=3: (1,1), (1,2), (1,3), (2,1), (2,2), (3,1))
        *   **For each point**, show which line(s) contain it by substitution (e.g., "Point (2,1) on line y=-2x+5: check 1 = -2(2)+5 = 1 ✓")
        *   **If ANY point is uncovered**, the construction FAILS - acknowledge this immediately
    *   **Do NOT claim** "the construction works" without explicit point-by-point verification

*   **Impossibility Proof Requirements** (2025-12-22 Retest Analysis):
    *   If you claim a specific value is impossible, you must use one of these rigorous proof strategies:
        *   **Counting Argument**: "We need to satisfy N constraints, but the available resources can satisfy at most M < N constraints"
        *   **Pigeonhole Principle**: "We have N constraints but only M degrees of freedom (N > M)"
        *   **Proof by Contradiction**: "Assume X works. Then [derive contradiction]. Therefore X is impossible."
    *   **Do NOT simply state** "X doesn't work" or "I couldn't find a construction" - this is NOT a proof of impossibility

*   **Construction Sanity Checks** (2025-12-22 Retest Analysis):
    *   Before claiming a construction works, verify systematically:
        *   **What needs to be satisfied?** List all required properties/constraints explicitly
        *   **What resources are available?** Count available objects/degrees of freedom
        *   **Does the proposed construction work?** Verify each constraint is satisfied
        *   **Is the claim feasible?** If resources cannot satisfy constraints, the construction is impossible
    *   **General principle**: Verify constructions explicitly rather than relying on intuition

### Output Format ###

Your response MUST be structured into the following sections, in this exact order. Use the EXACT section markers shown below.

### Summary ###

Provide a concise overview of your findings. This section must contain two parts:

*   **a. Verdict:** State clearly whether you have found a complete solution or a partial solution.
    *   **For a complete solution:** State the final answer in \\boxed{} format, e.g., "I have successfully solved the problem. The final answer is \\boxed{42}."
    *   **For a partial solution:** State the main rigorous conclusion(s) you were able to prove, e.g., "I have not found a complete solution, but I have rigorously proven that..."
*   **b. Method Sketch:** Present a high-level, conceptual outline of your solution. This sketch should allow an expert to understand the logical flow of your argument without reading the full detail. It should include:
    *   A narrative of your overall strategy.
    *   The full and precise mathematical statements of any key lemmas or major intermediate results.
    *   If applicable, describe any key constructions or case splits that form the backbone of your argument.

### Detailed Solution ###

Present the full, step-by-step mathematical proof. Each step must be logically justified and clearly explained. The level of detail should be sufficient for an expert to verify the correctness of your reasoning without needing to fill in any gaps. This section must contain ONLY the complete, rigorous proof, free of any internal commentary, alternative approaches, or failed attempts.

### Self-Correction Instruction ###

Before finalizing your output, carefully review your "Summary" and "Detailed Solution" sections to ensure they are clean, rigorous, and strictly adhere to all instructions provided above. Verify that every statement contributes directly to the final, coherent mathematical argument.

"""

self_improvement_prompt = """
You have an opportunity to improve your solution. Please review your solution carefully. Correct errors and fill justification gaps if any. Your second round of output should strictly follow the instructions in the system prompt.
"""

check_verification_prompt = """
Can you carefully review each item in your list of findings? Are they valid or overly strict? An expert grader must be able to distinguish between a genuine flaw and a concise argument that is nonetheless sound, and to correct their own assessment when necessary.

If you feel that modifications to any item or its justification is necessary. Please produce a new list. In your final output, please directly start with **Summary** (no need to justify the new list).
"""

correction_prompt = """
Below is the bug report. If you agree with certain item in it, can you improve your solution so that it is complete and rigorous? Note that the evaluator who generates the bug report can misunderstand your solution and thus make mistakes. If you do not agree with certain item in the bug report, please add some detailed explanations to avoid such misunderstanding. Your new solution should strictly follow the instructions in the system prompt.
"""

verification_system_prompt = """
You are an expert mathematician and a meticulous grader for an International Mathematical Olympiad (IMO) level exam. Your primary task is to verify whether the provided mathematical solution demonstrates valid mathematical reasoning that leads to the correct answer.

**HIERARCHICAL DECISION TREE** (2025-12-25 Rewrite):

Follow this THREE-LEVEL decision process in strict sequential order:

**LEVEL 1: Check Answer Correctness**
*   First, identify the final answer in the solution (e.g., "p∈{2,3,7}", "maximum value is 42", "proof complete").
*   Verify if the answer is mathematically valid.
*   **Decision:**
    *   If answer is **WRONG** → verdict = **FAIL** (Critical Error) → STOP (do not proceed to Level 2)
    *   If answer is **CORRECT** → proceed to Level 2

**LEVEL 2: Check Reasoning Validity**
*   Examine the mathematical principles and methods used in the solution.
*   Ask: Does the solution use **valid mathematical principles**?
    *   **Valid:** Counting arguments, pigeonhole principle, proof by contradiction, algebraic manipulation, geometric constructions, induction, etc.
    *   **Invalid:** "I tried many cases and failed" (without mathematical proof), circular reasoning, nonsense claims ("even numbers have bad karma"), etc.
*   **Decision:**
    *   If reasoning uses **INVALID principles** → verdict = **FAIL** (Critical Error) → STOP (do not proceed to Level 3)
    *   If reasoning uses **VALID principles** → proceed to Level 3

**LEVEL 3: Check Presentation Quality**
*   Examine the completeness and rigor of the presentation.
*   Classify any issues found:
    *   **Justification Gap:** Missing details, imprecise wording, incomplete verification (but logic is sound)
    *   **Critical Error:** Demonstrably wrong intermediate steps that invalidate the logic chain
*   **Decision:**
    *   If only **Justification Gaps** found → verdict = **PASS** (gaps are acceptable)
    *   If **Critical Errors** found → verdict = **FAIL**
    *   If **no issues** found → verdict = **PASS**

**CRITICAL GRADING PRINCIPLE:**
*   Level 1 and Level 2 are **gate checks**: failing either means immediate FAIL verdict.
*   Level 3 is **quality assessment**: only presentation issues are examined here.
*   **A solution with correct answer (Level 1 ✓) and valid reasoning (Level 2 ✓) MUST PASS**, even if presentation has gaps (Level 3).
*   **Justification gaps are NEVER grounds for FAIL** if Levels 1 and 2 passed.

### Detailed Implementation Instructions ###

**1. How to Apply the Hierarchical Decision Tree**

Follow the three levels sequentially. Do NOT skip levels or apply them out of order.

**LEVEL 1 IMPLEMENTATION: Answer Correctness**
*   Extract the final answer from the solution (look for conclusive statements like "Therefore p∈{2,3,7}", "The maximum value is 42", "This completes the proof").
*   For FIND problems: Check if the answer is a complete set (e.g., "p∈{2,5,11}") vs partial (e.g., "p=2 works").
*   For PROVE problems: Check if the claimed theorem/inequality is actually proven.
*   For DETERMINE problems: Check if all requested values are identified.
*   **Gate Decision:** WRONG answer → immediate FAIL, CORRECT answer → proceed to Level 2.

**LEVEL 2 IMPLEMENTATION: Reasoning Validity**

**SCOPE:** Check mathematical METHODS used (not individual claims).

**BEFORE YOU START - Pre-Flight Check:**
Ask yourself: "Am I about to evaluate whether a specific CLAIM is true/false?"
→ If YES: STOP. That's Level 3, not Level 2.
→ If NO: Proceed with method identification below.

**Step 1: Identify Methods Used**
List the mathematical methods/tools employed in the proof:
- [ ] Case analysis ("If k≤2, then... If k≥4, then...")
- [ ] Counting arguments ("We have N objects with property P, so...")
- [ ] Pigeonhole principle
- [ ] Proof by contradiction
- [ ] Explicit construction with verification
- [ ] Algebraic manipulation
- [ ] Geometric reasoning
- [ ] Induction
- [ ] Other recognized mathematical method: _______

**Step 2: Classify Methods**
- **VALID methods:** Any recognized mathematical tool from Step 1
- **INVALID methods:**
  - Trial-and-error without proof ("I tried 100 cases and failed" with NO mathematical reasoning)
  - Circular logic ("A is true because B, B is true because A")
  - Unjustified intuition/baseless claims (no reasoning provided)
  - Nonsense reasoning ("even numbers have bad karma")

**Step 3: Make Gate Decision**
- If ALL methods are VALID → **PASS Level 2** (proceed to Level 3)
- If ANY method is INVALID → **FAIL Level 2** (stop, do not proceed)

**CRITICAL SCOPE LIMIT:**
You are checking the TOOLS/METHODS used in the proof.
You are NOT checking:
- Whether specific claims are precisely worded (Level 3)
- Whether intermediate steps are completely rigorous (Level 3)
- Whether cross-references are perfectly clear (Level 3)

**Example: Correct Level 2 Analysis**

*Proof excerpt:* "For n≤5, direct computation shows the property holds. For n≥6, we use a counting argument: each element can contribute at most C resources, and we need at least D total. Since nC < D for n≥6, the property cannot hold. Therefore the answer is n∈{1,2,3,4,5}."

✓ **CORRECT Level 2 Analysis:**
- **Methods identified:** Case analysis (n≤5 vs n≥6), counting arguments (resource bounds)
- **Classification:** All methods are VALID (recognized mathematical tools)
- **Decision:** PASS Level 2 → proceed to Level 3

❌ **WRONG Level 2 Analysis (do NOT do this):**
- "The claim 'each element can contribute at most C resources' is FALSE for n≥6, because elements could contribute more resources with different configurations."
- **Why wrong:** This analyzes CLAIM accuracy (whether the specific bound is correct), not METHOD validity (whether counting arguments are a valid tool). This type of analysis belongs in Level 3.

**REMINDER - Hierarchical Decision Principle:**
- Level 1 (answer correctness) and Level 2 (method validity) are **GATE CHECKS**
- If answer is CORRECT (✓) and methods are VALID (✓) → proof MUST PASS, even if presentation has gaps
- Imprecise wording, missing intermediate steps, unclear cross-references → Level 3 (Presentation), NEVER grounds for FAIL

**CRITICAL CONSTRAINT:** Your Level 2 analysis MUST be ≤200 words (800 tokens). If you exceed this, you are over-analyzing CLAIMS instead of identifying METHODS.

Use this format:
- Methods identified: [list]
- Classification: [VALID/INVALID]
- Decision: [PASS Level 2 / FAIL Level 2]

**LEVEL 3 IMPLEMENTATION: Presentation Quality**
*   Now that answer is correct (Level 1 ✓) and reasoning is valid (Level 2 ✓), examine presentation details.
*   Classify issues into two categories:

    **Justification Gap (acceptable):**
    *   Imprecise wording that doesn't affect logic (e.g., "must be vertical" when "can be taken as vertical" is more precise)
    *   Missing intermediate algebraic steps that would be straightforward to fill in
    *   Incomplete verification of constructions when construction logic is sound
    *   Typos in intermediate steps that don't propagate to final answer

    **Critical Error (unacceptable):**
    *   Demonstrably wrong intermediate calculations that invalidate logic chain
    *   Circular reasoning or logical fallacies
    *   Construction that produces wrong output when tested

*   **Construction Completeness Rule for FIND Problems (Three-Level Classification):**

    For problems asking to find/determine all values, constructions must be provided.
    Classify construction completeness using THREE levels:

    **LEVEL 1 - CRITICAL_ERROR (Zero Detail - No Construction Strategy):**
    The solution claims a construction exists but provides NO strategy, NO approach, NO details.
    Reader cannot understand HOW to construct or WHAT the construction approach is.

    Examples of CRITICAL_ERROR (zero detail):
    - ❌ "Construction exists" → No details whatsoever
    - ❌ "Construction can be found" → No strategy mentioned
    - ❌ "Construction exists using specific values" → Which values? No specification
    - ❌ "For case A, construction exists" → No mention of approach or method
    - ❌ "Construction can be found using standard techniques" → No details about which techniques
    - ❌ "Construction is straightforward" → No construction shown at all
    - ❌ "Construction works by combinatorial argument" → No actual construction described

    **LEVEL 2 - JUSTIFICATION_GAP (Partial Detail - Strategy Clear, Formula Missing):**
    The solution describes a construction STRATEGY or APPROACH with enough detail to understand
    the construction concept, but does not provide explicit formulas/equations. The construction logic
    is sound and the reader can conceptually verify the approach works.

    Examples of JUSTIFICATION_GAP (partial detail):
    - ⚠️ "Use sequence a_i = first i primes" → Strategy clear (which sequence), formula missing
    - ⚠️ "Partition into three disjoint sets covering all elements" → Approach described, specific partition missing
    - ⚠️ "For n=5, use configuration with elements at positions 1,2,4" → Positions given, full construction missing
    - ⚠️ "Assign each element to its corresponding group" → Strategy clear, specific assignment missing
    - ⚠️ "Construction: function passing through points (a,f(a)) and (b,f(b))" → Points given, equation missing
    - ⚠️ "Divide into k regions using standard partitioning" → Approach clear, specific partition missing

    **LEVEL 3 - ACCEPTABLE (Full Explicit - Complete Formulas Provided):**
    The solution provides explicit formulas, equations, or complete specifications that can
    be directly verified by computation.

    Examples of ACCEPTABLE (full explicit):
    - ✅ "Use sequence a_i = 2^i for i=1,2,...,n" → Complete specification
    - ✅ "For n=5, use f(x) = x² - 3x + 2" → Explicit formula
    - ✅ "Partition: S1={1,3,5}, S2={2,4}, S3={6,7,8}" → All sets specified
    - ✅ "Define g(n) = ⌊n/2⌋ + 1" → Complete formula

    **Three-Level Decision Rule:**
    - If construction has ZERO strategy detail (Level 1) → Classify as CRITICAL_ERROR → FAIL
    - If construction describes PARTIAL strategy (Level 2) → Classify as JUSTIFICATION_GAP → PASS (per policy: accept gaps when answer correct + method valid)
    - If construction provides FULL formulas (Level 3) → Classify as ACCEPTABLE → PASS

    **Key Principle:**
    The difference between Level 1 and Level 2 is whether the reader can UNDERSTAND THE APPROACH.
    - Level 1 (zero detail): "Construction exists" - reader has no idea how to proceed
    - Level 2 (partial detail): "use first i primes" - reader understands the approach, can conceptually verify
    - Level 3 (full explicit): "a_i = p_i where p_i is the i-th prime" - reader can directly verify by computation

*   **Quality Decision:** Only Justification Gaps → PASS, Any Critical Errors in logic chain → FAIL.

**2. Output Format**
Your response should provide a concise summary:

*   **Level 1 Result:** State whether the final answer is CORRECT or WRONG (quote the answer)
*   **Level 2 Result:** State whether reasoning uses VALID or INVALID mathematical principles
*   **Level 3 Result:** List any presentation issues found (Justification Gaps or Critical Errors in logic chain)
*   **Final Verdict:** "PASS" or "FAIL" based on the hierarchical decision tree
*   **Reasoning:** Brief explanation of the verdict

All detailed mathematical analysis should be provided in the structured JSON output (not in a separate prose log).

"""

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
Problem: "Prove that if m is an even integer, then m² is divisible by 4."
Solution excerpt: "Let m=2j. Then m²=4j². Now for j even: m²=16r² since j is an integer from the first case."
**Applying the Decision Rule:** 1. Answer: m² divisible by 4 ✓ CORRECT | 2. Method: Algebraic manipulation ✓ VALID | 3. Claim: "j is integer from first case" - TRUE from setup, but reference unclear
**Correct Classification:** "j is integer from first case" → Justification Gap (4-5) - Claim IS TRUE (follows from m=2j), but "first case" reference imprecise. Missing cross-reference clarity, NOT provably false claim.
**WRONG:** ~~Critical Error - claim FALSE~~ ❌ WRONG - "j is integer" IS TRUE (from m=2j with m∈ℤ), just reference imprecise. Missing explicit reference = JUSTIFICATION_GAP (4-5), NOT CRITICAL_ERROR (8-9).
**CRITICAL RULE:** Context-dependent claims that are TRUE in context (even if reference imprecise) are JUSTIFICATION_GAP. Only CRITICAL_ERROR if claim provably FALSE or makes explicit universal claim that doesn't hold.

---

**Example 4: Count+Target Specification (Justification Gap, NOT Critical Error)**
*This example shows how to classify construction claims with count and target.*

Problem: "Find all prime numbers p such that 2^p + p^2 is also prime."

Solution excerpt (p=3 construction): "**p=3:** Computing 2³ + 3² = 8 + 9 = 17, which is prime."

**Applying the Decision Rule:**
1. Check final answer: p∈{2,3} ✓ CORRECT
2. Check construction claim: "Computing 2³ + 3² = 8 + 9 = 17, which is prime" → Has EXPLICIT COMPUTATION with concrete values
3. Classify specification level: Explicit computation is a CONCRETE DETAIL → Category C (VALID METHOD)
4. Level 2 decision: Category C → PASS Level 2, proceed to Level 3
5. Level 3 decision: Explicit verification shown → PASS Level 3

**Correct Classification:**
*   **Location:** "Computing 2³ + 3² = 8 + 9 = 17, which is prime."
    *   **Type:** JUSTIFICATION_GAP (NOT CRITICAL_ERROR)
    *   **Severity:** 4-5 (presentation issue, not method invalidity)
    *   **Issue:** Justification Gap - The solution provides explicit computation (2³ + 3² = 17), which is a valid construction STRATEGY per Category C. However, primality verification for 17 is implicit (not shown). This is a presentation gap at Level 3, NOT a method invalidity at Level 2. The final answer is correct and the approach is sound.

**WRONG Classification (don't do this):**
*   ~~**Location:** "p=3 works"~~
    *   ~~**Type:** CRITICAL_ERROR~~
    *   ~~**Issue:** Critical Error - No concrete specification provided, invalid method at Level 2.~~ ❌ WRONG - Explicit computation IS a concrete detail (Category C). The phrase "2³ + 3² = 8 + 9 = 17" provides concrete mathematical verification with specific numerical values. This is sufficient to be Category C per the boundary rule: "explicit computation → Category C". Missing primality proof for 17 is a Level 3 presentation gap, NOT a Level 2 method invalidity.

**CRITICAL BOUNDARY RULE APPLICATION:**
- "p=3 works" → Category A (zero details) → CRITICAL_ERROR at Level 2
- "p=3 by direct computation" → Category B (method name only) → CRITICAL_ERROR at Level 2
- "2³ + 3² = 8 + 9 = 17 (prime)" → Category C (computation shown) → PASS Level 2, JUSTIFICATION_GAP at Level 3
- "p=3: 2³ + 3² = 17, and 17 is prime (checked divisibility by 2,3,5)" → Category C (full verification) → PASS Level 2, PASS Level 3

**The Level 2 question:** "Does solution provide ANY concrete mathematical detail?" → YES (explicit computation with values) → Category C
**The Level 3 question:** "Are the provided details COMPLETE?" → MOSTLY (computation shown, primality implicit) → MINOR JUSTIFICATION_GAP

---

**CRITICAL META-INSTRUCTION:**

**Do NOT override these few-shot examples with your own detailed reasoning.**

When you encounter a pattern matching Example 1, 2, 3, or 4 above:
1. **STOP** - Do not generate 3000+ tokens of detailed analysis explaining why a claim is imprecise
2. **CHECK** - Is the final answer correct? Are constructions valid? Is the reasoning method valid?
3. **APPLY** - Use the SAME classification shown in the example (Justification Gap or Critical Error)
4. **REMEMBER** - Your detailed mathematical reasoning is SECONDARY to the decision rule and few-shot guidance
5. **DISAMBIGUATE** - Key patterns:
   - Wrong answer or completely missing construction = Critical Error (Example 2 pattern)
   - Correct answer with valid methods but imprecise wording = Justification Gap (Example 1 pattern)
   - Example 3: Context-dependent claim (true in context, reference not explicit) = Justification Gap (4-5), NOT Critical Error (8-9)
   - Example 4: Count+target specification without equations = Justification Gap (4-5), NOT Critical Error (8-9)

If you find yourself writing "the claim is false" or "this is mathematically incorrect" about imprecise wording:
→ PAUSE and check: Is the claim FALSE in the mathematical context, or just lacking explicit justification/reference?
→ If claim is TRUE in context but reference not explicit: Justification Gap (severity 4-5)
→ If claim is FALSE in the mathematical context: Critical Error (severity 8-9)
→ Only classify as Critical Error if the final answer is WRONG or reasoning uses completely invalid principles

"""

verification_remider = """
### Verification Task Reminder ###

Your task is to act as an IMO grader. Now, generate the **summary** and the **step-by-step verification log** for the solution above. In your log, justify each correct step and explain in detail any errors or justification gaps you find, as specified in the instructions above.
"""

def get_api_key():
    """
    Retrieves the OpenAI API key from environment variables.
    Exits if the key is not found.
    """

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set.")
        print("Please set the variable, e.g., 'export OPENAI_API_KEY=\"your_api_key\"'")
        sys.exit(1)
    return api_key

def read_file_content(filepath):
    """
    Reads and returns the content of a file.
    Exits if the file cannot be read.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"Error: File not found at '{filepath}'")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading file '{filepath}': {e}")
        sys.exit(1)

def build_request_payload(system_prompt, question_prompt, other_prompts=None, max_completion_tokens=8192):
    """
    Builds the JSON payload for the OpenAI o3 API request.

    Args:
        max_completion_tokens: Maximum output tokens (default 8192 to prevent truncation)
                               Note: Parameter name kept for backward compatibility,
                               but maps to max_output_tokens for Responses API
    """
    # Combine all prompts into a single input
    input_text = question_prompt

    if system_prompt:
        input_text = f"System: {system_prompt}\n\nUser: {question_prompt}"

    if other_prompts:
        for prompt in other_prompts:
            input_text += f"\n\nAdditional instruction: {prompt}"

    payload = {
        "model": MODEL_NAME,
        "input": input_text,
        "reasoning": {
            "effort": "high"
        },
        "max_completion_tokens": max_completion_tokens  # BUGFIX (2025-12-27): OpenAI o3 Responses API uses max_completion_tokens
    }

    return payload

def send_api_request(api_key, payload):
    """
    Sends the request to the OpenAI API and returns the response.
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    #print("Sending request to OpenAI API...")
    try:
        response = requests.post(API_URL, headers=headers, data=json.dumps(payload), timeout=7200)
        response.raise_for_status()  # Raises an HTTPError for bad responses (4xx or 5xx)
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error during API request: {e}")
        if response.status_code == 400:
            print(f"Possible reason for 400: Model '{MODEL_NAME}' might not be available or URL is incorrect for your setup.")
            print(f"Raw API Response (if available): {response.text}")
        raise e

def extract_text_from_response(response_data):
    """
    Extracts the generated text from the OpenAI o3 API response JSON.
    Handles potential errors if the response format is unexpected.
    """
    try:
        # The output is an array, we need to find the message with text content
        print(">>>>>> Response:")
        print(json.dumps(response_data, indent=2))

        output_array = response_data['output']
        for item in output_array:
            if item['type'] == 'message' and 'content' in item:
                content_array = item['content']
                for content_item in content_array:
                    if content_item['type'] == 'output_text':
                        return content_item['text']
        
        # Fallback: if no text found, return empty string
        return ""
    except (KeyError, IndexError, TypeError) as e:
        print("Error: Could not extract text from the API response.")
        print(f"Reason: {e}")
        print("Full API Response:")
        print(json.dumps(response_data, indent=2))
        #sys.exit(1)
        raise e 

def extract_detailed_solution(solution, marker='Detailed Solution', after=True):
    """
    Extracts the text after '### Detailed Solution ###' from the solution string.
    Returns the substring after the marker, stripped of leading/trailing whitespace.
    If the marker is not found, returns the full solution as fallback (BUGFIX).

    BUGFIX (2025-12-27): Previously returned empty string if marker not found,
    causing GPT-5 verification failures on solutions without standard formatting.
    Now returns full solution if marker not found (matching agent_gpt_oss.py behavior).
    This fixes "Please provide the statement to evaluate." errors on Tests 3,4,5,6.
    """
    idx = solution.find(marker)
    if idx == -1:
        # BUGFIX: Return full solution instead of empty string
        # This handles solutions with alternative formatting (e.g., "### Summary ###" only)
        if len(solution) > 100:  # Sanity check: valid solution should be >100 chars
            return solution
        else:
            return ''  # Truly empty/invalid solution
    if(after):
        return solution[idx + len(marker):].strip()
    else:
        return solution[:idx].strip()

def verify_solution(problem_statement, solution, verbose=True):

    dsol = extract_detailed_solution(solution)

    # Verification constraints to prevent truncation and over-analysis (Option A)
    verification_constraint = """
**CRITICAL CONSTRAINTS FOR VERIFICATION:**

1. **Output Length Limit:** Your verification reasoning MUST be ≤2000 tokens total.

2. **Evaluate, Don't Re-Prove:** Your task is to EVALUATE the provided solution, NOT to re-prove the problem from scratch.
   - ❌ WRONG: "Let's verify by manually testing n=3: points are (1,1), (1,2)... now n=4..."
   - ✅ CORRECT: "The solution tests n=3, n=4, n=5 and identifies the pattern. This method is valid."

3. **No Manual Case Testing:** Do NOT manually enumerate specific values or cases that the solution already covered.
   - ❌ WRONG: "For p=2, let's check: we need to verify divisibility conditions..."
   - ✅ CORRECT: "The solution's analysis of p=2 uses valid case-by-case reasoning."

4. **Trust Valid Methods:** If the solution uses valid mathematical methods (case analysis, induction, contradiction, construction) and the answer is correct:
   - Classify as PASS if presentation is clear
   - Classify as JUSTIFICATION_GAP if presentation has minor wording issues
   - Do NOT attempt to independently verify every computation

5. **Early Classification:** Once you determine answer correctness and reasoning validity, immediately classify and stop. Do not continue analyzing.

6. **Focus on What's Missing, Not Re-Proving What's There:**
   - ✅ CORRECT: "The solution claims m=4 is impossible but provides no proof → CRITICAL_ERROR"
   - ❌ WRONG: "Let me verify m=4 is impossible by testing: ..." → This is re-proving, not evaluating

7. **Construction Verification (for FIND/DETERMINE problems):**
   - If the problem asks to "find" or "determine" values, and the solution claims "X is achievable/possible":
     - ✅ PASS: Solution provides EXPLICIT construction with specific values/formulas/equations
       Example: "For p=5, use sequence a_i = 2^i for i=1,...,5 giving {2,4,8,16,32}"
     - ❌ FAIL: Solution only states existence without showing concrete construction
       Example: "p=5 is possible by case analysis" or "p=5 exists" (no explicit construction shown)
   - This applies to geometric constructions, combinatorial configurations, or any existence claims
   - Abstract existence proofs WITHOUT explicit examples should be classified as CRITICAL_ERROR for FIND problems

**Violating these constraints will cause your response to be truncated and discarded.**
"""

    newst = f"""
{verification_constraint}

======================================================================
### Problem ###

{problem_statement}

======================================================================
### Solution ###

{dsol}

{verification_remider}
"""
    if(verbose):
        print(">>>>>>> Start verification.")
    p2 = build_request_payload(system_prompt=verification_system_prompt, 
        question_prompt=newst
        )
    
    if(verbose):
        print(">>>>>>> Verification prompt:")
        print(json.dumps(p2, indent=4))

    res = send_api_request(get_api_key(), p2)
    out = extract_text_from_response(res) 

    if(verbose):
        print(">>>>>>> Verification results:")
        print(json.dumps(out, indent=4))

    check_correctness = """Response in "yes" or "no". Is the following statement saying the solution is correct, or does not contain critical error or a major justification gap?""" \
            + "\n\n" + out 
    prompt = build_request_payload(system_prompt="", question_prompt=check_correctness)
    r = send_api_request(get_api_key(), prompt)
    o = extract_text_from_response(r) 

    if(verbose):
        print(">>>>>>> Is verification good?")
        print(json.dumps(o, indent=4))
        
    bug_report = ""

    if("yes" not in o.lower()):
        bug_report = extract_detailed_solution(out, "Detailed Verification", False)

        """p2["contents"].append(
            {"role": "model",
            "parts": [{"text": bug_report}]
            }
        )
        p2["contents"].append(
            {"role": "user",
            "parts": [{"text": check_verification_prompt}]
            }
        )

        if(verbose):
            print(">>>>>>> Review bug report prompt:")
            print(json.dumps(p2["contents"][-2:], indent=4))

        res = send_api_request(get_api_key(), p2)
        out = extract_text_from_response(res) 
    """

    if(verbose):
        print(">>>>>>>Bug report:")
        print(json.dumps(bug_report, indent=4))
    
    return bug_report, o

def check_if_solution_claimed_complete(solution):
    check_complete_prompt = f"""
Is the following text claiming that the solution is complete?
==========================================================

{solution}

==========================================================

Response in exactly "yes" or "no". No other words.
    """

    p1 = build_request_payload(system_prompt="",    question_prompt=check_complete_prompt)
    r = send_api_request(get_api_key(), p1)
    o = extract_text_from_response(r)

    print(o)
    return "yes" in o.lower()


def init_explorations(problem_statement, verbose=True, other_prompts=[]):
    p1  = build_request_payload(
            system_prompt=step1_prompt,
            question_prompt=problem_statement,
            #other_prompts=["* Please explore all methods for solving the problem, including casework, induction, contradiction, and analytic geometry, if applicable."]
            #other_prompts = ["You may use analytic geometry to solve the problem."]
            other_prompts = other_prompts
        )

    print(f">>>>>> Initial prompt.")
    print(json.dumps(p1, indent=4))

    response1 = send_api_request(get_api_key(), p1)
    output1 = extract_text_from_response(response1)

    print(f">>>>>>> First solution: ") 
    print(json.dumps(output1, indent=4))

    print(f">>>>>>> Self improvement start:")
    # For o3, we need to build a new payload with the conversation context
    improvement_input = f"{p1['input']}\n\nAssistant: {output1}\n\nUser: {self_improvement_prompt}"
    p1 = {
        "model": MODEL_NAME,
        "input": improvement_input
    }

    response2 = send_api_request(get_api_key(), p1)
    solution = extract_text_from_response(response2)
    print(f">>>>>>> Corrected solution: ")
    print(json.dumps(solution, indent=4))
    
    #print(f">>>>>>> Check if solution is complete:"  )
    #is_complete = check_if_solution_claimed_complete(output1)
    #if not is_complete:
    #    print(f">>>>>>> Solution is not complete. Failed.")
    #    return None, None, None, None
    
    print(f">>>>>>> Vefify the solution.")
    verify, good_verify = verify_solution(problem_statement, solution, verbose)

    print(f">>>>>>> Initial verification: ")
    print(json.dumps(verify, indent=4))
    print(f">>>>>>> verify results: {good_verify}")
    
    return p1, solution, verify, good_verify

def agent(problem_statement, other_prompts=[]):
    p1, solution, verify, good_verify = init_explorations(problem_statement, True, other_prompts)

    if(solution is None):
        print(">>>>>>> Failed in finding a complete solution.")
        return None

    error_count = 0
    correct_count = 1
    success = False
    for i in range(30):
        print(f"Number of iterations: {i}, number of corrects: {correct_count}, number of errors: {error_count}")

        try:
            if("yes" not in good_verify.lower()):
                # clear
                correct_count = 0
                error_count += 1

                #self improvement
                print(">>>>>>> Verification does not pass, correcting ...")
                # establish a new prompt that contains the solution and the verification

                p1 = build_request_payload(
                    system_prompt=step1_prompt,
                    question_prompt=problem_statement,
                    #other_prompts=["You may use analytic geometry to solve the problem."]
                    other_prompts=other_prompts
                )

                # For o3, build a new payload with the conversation context
                correction_input = f"{p1['input']}\n\nAssistant: {solution}\n\nUser: {correction_prompt}\n\n{verify}"
                p1 = {
                    "model": MODEL_NAME,
                    "input": correction_input
                }

                print(">>>>>>> New prompt:")
                print(json.dumps(p1, indent=4))
                response2 = send_api_request(get_api_key(), p1)
                solution = extract_text_from_response(response2)

                print(">>>>>>> Corrected solution:")
                print(json.dumps(solution, indent=4))


                #print(f">>>>>>> Check if solution is complete:"  )
                #is_complete = check_if_solution_claimed_complete(solution)
                #if not is_complete:
                #    print(f">>>>>>> Solution is not complete. Failed.")
                #    return None

            print(f">>>>>>> Verify the solution.")
            verify, good_verify = verify_solution(problem_statement, solution)

            if("yes" in good_verify.lower()):
                print(">>>>>>> Solution is good, verifying again ...")
                correct_count += 1
                error_count = 0
     

            if(correct_count >= 5):
                print(">>>>>>> Correct solution found.")
                print(json.dumps(solution, indent=4))
                return solution

            elif(error_count >= 10):
                print(">>>>>>> Failed in finding a correct solution.")
                return None
        except Exception as e:
            print("Unexpected error:", e, "retry...")
    if(not success):
        print(">>>>>>> Failed in finding a correct solution.")
        return None
        
if __name__ == "__main__":
    # Set up argument parsing
    parser = argparse.ArgumentParser(description='IMO Problem Solver Agent')
    parser.add_argument('problem_file', nargs='?', default=None,
                       help='Path to the problem statement file (optional if using --benchmark)')
    parser.add_argument('--log', '-l', type=str, help='Path to log file (optional)')
    parser.add_argument('--other_prompts', '-o', type=str, help='Other prompts (optional)')
    parser.add_argument("--max_runs", '-m', type=int, default=10, help='Maximum number of runs (default: 10)')
    parser.add_argument('--benchmark', '-b', type=str, choices=['gradingbench', 'proofbench'],
                       help='Load problem from benchmark (gradingbench or proofbench)')
    parser.add_argument('--level', type=str,
                       help='Filter benchmark by level (Basic, Advanced). Case-insensitive.')
    parser.add_argument('--benchmark-index', '-i', type=int, default=0,
                       help='Index of problem to load from filtered benchmark (default: 0)')

    args = parser.parse_args()

    max_runs = args.max_runs

    other_prompts = []
    if args.other_prompts:
        other_prompts = args.other_prompts.split(',')

    print(">>>>>>> Other prompts:")
    print(other_prompts)

    # Set up logging if log file is specified
    if args.log:
        if not set_log_file(args.log):
            sys.exit(1)
        print(f"Logging to file: {args.log}")

    # Load problem statement from benchmark or file
    if args.benchmark:
        # Load from benchmark
        print(f">>>>>>> Loading problem from benchmark: {args.benchmark}")
        if args.level:
            print(f">>>>>>> Filtering by level: {args.level}")
        print(f">>>>>>> Benchmark index: {args.benchmark_index}")

        try:
            loader = BenchmarkLoader()

            # Load the appropriate benchmark
            if args.benchmark == 'gradingbench':
                entries = loader.load_gradingbench(level=args.level)
            else:  # proofbench
                entries = loader.load_proofbench(level=args.level)

            if not entries:
                print(f">>>>>>> Error: No entries found in {args.benchmark} with the specified filters")
                sys.exit(1)

            if args.benchmark_index >= len(entries):
                print(f">>>>>>> Error: Benchmark index {args.benchmark_index} is out of range (0-{len(entries)-1})")
                sys.exit(1)

            # Get the problem from the specified index
            entry = entries[args.benchmark_index]
            problem_statement = entry.get('Problem', '')
            problem_id = entry.get('Problem ID', 'Unknown')

            print(f">>>>>>> Loaded problem: {problem_id}")
            print(f">>>>>>> Total entries in filtered benchmark: {len(entries)}")
            print(f">>>>>>> Problem preview: {problem_statement[:200]}...")

        except Exception as e:
            print(f">>>>>>> Error loading from benchmark: {e}")
            sys.exit(1)
    elif args.problem_file:
        # Load from file
        problem_statement = read_file_content(args.problem_file)
    else:
        print(">>>>>>> Error: Either problem_file or --benchmark must be specified")
        parser.print_help()
        sys.exit(1)

    for i in range(max_runs):
        print(f"\n\n>>>>>>>>>>>>>>>>>>>>>>>>>> Run {i} of {max_runs} ...")
        try:
            sol = agent(problem_statement, other_prompts)
            if(sol is not None):
                print(f">>>>>>> Found a correct solution in run {i}.")
                print(json.dumps(sol, indent=4))
                break
        except Exception as e:
            print(f">>>>>>> Error in run {i}: {e}")
            continue
    
    # Close log file if it was opened
    close_log_file()

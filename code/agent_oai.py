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
    *   **Step 1**: Test the SIMPLEST cases first (e.g., k=0 for "determine all k")
    *   **Step 2**: Test the NEXT simplest case (e.g., k=1)
    *   **Step 3**: For each case that seems impossible, PROVE impossibility rigorously (not just "I couldn't find a construction")
    *   **Step 4**: Continue testing values systematically until you find the COMPLETE pattern
    *   **Example**: For "determine all k for n≥3", you must test k=0,1,2,3,... and explain why each works or doesn't work

*   **Explicit Point-by-Point Verification for Constructions** (2025-12-22 Retest Analysis):
    *   When you claim a construction works (e.g., "these 3 lines cover all points"), you MUST verify it point-by-point:
        *   **List all required points** explicitly (e.g., for n=3: (1,1), (1,2), (1,3), (2,1), (2,2), (3,1))
        *   **For each point**, show which line(s) contain it by substitution (e.g., "Point (2,1) on line y=-2x+5: check 1 = -2(2)+5 = 1 ✓")
        *   **If ANY point is uncovered**, the construction FAILS - acknowledge this immediately
    *   **Do NOT claim** "the construction works" without explicit point-by-point verification

*   **Impossibility Proof Requirements** (2025-12-22 Retest Analysis):
    *   If you claim k=X is impossible, you must use one of these rigorous proof strategies:
        *   **Counting Argument**: "We need to cover N points, but n lines with k sunny can cover at most M < N points"
        *   **Pigeonhole Principle**: "We have N constraints but only M degrees of freedom (N > M)"
        *   **Proof by Contradiction**: "Assume k=X works. Then [derive contradiction]. Therefore k=X is impossible."
    *   **Do NOT simply state** "k=X doesn't work" or "I couldn't find a construction" - this is NOT a proof of impossibility

*   **Construction Sanity Checks** (2025-12-22 Retest Analysis):
    *   Before claiming "k=X is achievable", ask yourself:
        *   **How many points** need covering? (For n=3: |T_3| = 6 points)
        *   **How many lines** are available? (Exactly n lines total)
        *   **Typical coverage**: Each sunny line covers ~1-2 points, each non-sunny diagonal covers ~(k-1) points
        *   **Is k=X feasible?** If k sunny lines + (n-k) diagonals can't cover enough points, k=X is likely impossible
    *   **Example for n=3, k=3**: Need 6 points, have 3 sunny lines covering ~3 points total → Need special construction!

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
*   First, identify the final answer in the solution (e.g., "k∈{0,1,3}", "maximum value is 42", "proof complete").
*   Compare to the ground truth or verify if the answer is mathematically valid.
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
*   Extract the final answer from the solution (look for conclusive statements like "Therefore k∈{0,1,3}", "The maximum value is 42", "This completes the proof").
*   For FIND problems: Check if the answer is a complete set (e.g., "k∈{0,1,3}") vs partial (e.g., "k=1 works").
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
- [ ] Counting arguments ("Column x has h points, so...")
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

*Proof excerpt:* "If k≤2, then column x=n-2 forces a vertical line for column n-2. Now consider k≥4: having k≥4 would force at least four columns to rely on sunny lines. Because the three rightmost columns already force the use of a vertical line for column n-2, we would run out of vertical lines. Hence k≥4 is impossible."

✓ **CORRECT Level 2 Analysis:**
- **Methods identified:** Case analysis (k≤2 vs k≥4), counting arguments (column point counts, line counting)
- **Classification:** All methods are VALID (recognized mathematical tools)
- **Decision:** PASS Level 2 → proceed to Level 3

❌ **WRONG Level 2 Analysis (do NOT do this):**
- "The claim 'the three rightmost columns already force the use of a vertical line for column n-2' is FALSE for k≥4, because with four sunny lines the column n-2 can be covered entirely by sunny lines."
- **Why wrong:** This analyzes CLAIM accuracy (whether the statement is true in the k≥4 context), not METHOD validity (whether counting arguments are a valid tool). This type of analysis belongs in Level 3.

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
    *   **IMPORTANT - Missing constructions for FIND problems:** If the problem asks to "determine all k"
        (or similar FIND-type questions) and the solution claims "construction exists" or "construction can be found"
        without providing explicit equations or descriptions, this is a CRITICAL_ERROR (not a justification gap).

*   **Construction Completeness Rule for FIND Problems:**
    For problems asking to find/determine all values, if the solution claims a value works, it MUST provide
    at least one explicit construction:

    **Examples of CRITICAL_ERROR (missing construction):**
    - ❌ "Construction exists using vertical lines" → CRITICAL_ERROR (no equations provided)
    - ❌ "For k=1, construction exists" → CRITICAL_ERROR (no equation for the sunny line)
    - ❌ "For k=3, construction can be found using three sunny lines" → CRITICAL_ERROR (no equations)
    - ❌ "Construction is straightforward" → CRITICAL_ERROR (no construction shown)

    **Examples of ACCEPTABLE (construction provided):**
    - ✅ "Use vertical lines x=1, x=2, ..., x=n" → Acceptable (explicit equations)
    - ✅ "For k=1, use L: y-1 = 1/(1-n)·(x-n)" → Acceptable (equation provided)
    - ✅ "For k=3, use L1: y=2x, L2: y=-x+5, L3: y=x-1" → Acceptable (equations provided)

    **Key distinction:** "Construction provided but not verified" = JUSTIFICATION_GAP (acceptable).
    "Construction not provided at all" = CRITICAL_ERROR (unacceptable).

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

## CRITICAL: Few-Shot Calibration Examples (2025-12-24 Phase 2)

**These examples show you how to apply the decision rule above. Study them carefully before verifying the solution.**

**Example 1: Justification Gap (NOT Critical Error)**
*This example shows presentation issues that should be classified as Justification Gaps.*

Problem: "Determine all k such that n lines with exactly k sunny lines cover all required points."

Solution excerpt: "Column x=n-2 has 3 points, so one of the non-sunny lines **must be vertical**. Therefore k=2 is impossible. Final answer: k∈{0,1,3}."

**Applying the Decision Rule:**
1. Check final answer: k∈{0,1,3} ✓ CORRECT
2. Check constructions: Valid constructions provided for k=0,1,3 ✓
3. Decision: Answer correct → Classify as **Justification Gap**

**Correct Classification:**
*   **Location:** "one of the non-sunny lines must be vertical"
    *   **Issue:** Justification Gap - The wording is imprecise; the solution should say "can be taken to be vertical without loss of generality" since non-sunny lines could also be horizontal or slope -1. However, the underlying logic (that columns with many points require special handling) is sound, and the final answer k∈{0,1,3} is correct. This is a presentation issue, not a mathematical error.

**WRONG Classification (don't do this):**
*   ~~**Location:** "must be vertical"~~
    *   ~~**Issue:** Critical Error - This claim is false because non-sunny lines could be horizontal.~~ ❌ WRONG - This would be hypercritical; the solution's logic is valid despite imprecise wording.

---

**Example 2: Critical Error (truly invalid)**
*This example shows a fundamental mathematical error.*

Problem: "Determine all k..."

Solution excerpt: "For k=2, I tried many constructions and couldn't find one. Therefore k=2 doesn't work. Final answer: k∈{0,1,3}."

**Applying the Decision Rule:**
1. Check final answer: k∈{0,1,3} ✓ CORRECT
2. Check impossibility reasoning: "I tried and failed" ✗ INVALID (falls under EXCEPTION)
3. Decision: Invalid reasoning → Classify as **Critical Error**

**Correct Classification:**
*   **Location:** "I tried many constructions and couldn't find one"
    *   **Issue:** Critical Error - Failure to find a construction is not a proof of impossibility. The solution provides no rigorous argument (no counting argument, no pigeonhole principle, no proof by contradiction). This falls under the IMPORTANT EXCEPTION in the decision rule: completely invalid reasoning even with correct answer.

---

**Example 3: Context-Dependent Claim (Justification Gap, NOT Critical Error)**
*This example shows a claim that is TRUE in context but lacks explicit scope.*

Problem: "Determine all k such that n lines with exactly k sunny lines cover all required points."

Solution excerpt: "If k≤2 then column x=n-2 (which contains three points) cannot be covered solely by sunny lines; consequently one of the non-sunny lines must be vertical and must be the line x=n-2. Now consider k≥4: Since a sunny line can meet each column in at most one point, having k≥4 would force at least four columns to rely on sunny lines. Because the three rightmost columns already force the use of a vertical line for column n-2, we would run out of vertical lines. Final answer: k∈{0,1,3}."

**Applying the Decision Rule:**
1. Check final answer: k∈{0,1,3} ✓ CORRECT
2. Check reasoning method: Case analysis (k≤2 vs k≥4), counting arguments ✓ VALID mathematical tools
3. Check context-dependent claim: "columns force vertical line" is TRUE for k≤2 case but stated without explicit scope in k≥4 analysis

**Correct Classification:**
*   **Location:** "Because the three rightmost columns already force the use of a vertical line for column n-2"
    *   **Issue:** Justification Gap (severity 4-5) - The claim that "columns force vertical line for n-2" is TRUE in the k≤2 case (which was analyzed earlier) but is context-dependent - it would be FALSE for k≥4 if analyzed in isolation. The proof doesn't explicitly state "as established for k≤2" or similar scope qualifier. However, this is a **missing quantifier scope**, not a provably false claim. The reasoning in context is sound; it just lacks explicit cross-reference.

**WRONG Classification (do NOT do this):**
*   ~~**Location:** "columns force the use of a vertical line for column n-2"~~
    *   ~~**Issue:** Critical Error (severity 9) - This claim is FALSE for k≥4 because with four sunny lines, column n-2 (3 points) can be covered entirely by sunny lines. The argument for k≥4 impossibility is invalid.~~ ❌ WRONG - This treats a context-dependent claim (true for k≤2, the case being referenced) as if it were a universal claim. The proof is analyzing k≥4 by referencing earlier k≤2 results. Missing explicit scope is a JUSTIFICATION_GAP (severity 4-5), NOT a CRITICAL_ERROR (severity 8-9).

**CRITICAL RULE:** Context-dependent claims that are **TRUE in the relevant case** (even if false in other cases) are **JUSTIFICATION_GAP** when scope is not explicit. Only classify as **CRITICAL_ERROR** if the claim is **provably false in the case being analyzed** or makes an **explicit universal claim** (e.g., "for all k").

---

**CRITICAL META-INSTRUCTION:**

**Do NOT override these few-shot examples with your own detailed reasoning.**

When you encounter a pattern matching Example 1, 2, or 3 above:
1. **STOP** - Do not generate 3000+ tokens of detailed analysis explaining why a claim is imprecise
2. **CHECK** - Is the final answer correct? Are constructions valid? Is the reasoning method valid?
3. **APPLY** - Use the SAME classification shown in the example (Justification Gap or Critical Error)
4. **REMEMBER** - Your detailed mathematical reasoning is SECONDARY to the decision rule and few-shot guidance
5. **DISAMBIGUATE** - Key patterns:
   - Wrong answer or missing construction = Critical Error (Example 2 pattern)
   - Correct answer with valid methods but imprecise wording = Justification Gap (Example 1 pattern)
   - Example 3: Context-dependent claim (true in relevant case, scope not stated) = Justification Gap (4-5), NOT Critical Error (8-9)

If you find yourself writing "the claim is false" or "this is mathematically incorrect" about imprecise wording:
→ PAUSE and check: Is the claim FALSE in the case being analyzed, or just lacking explicit scope?
→ If claim is TRUE in context but scope not stated: Justification Gap (severity 4-5)
→ If claim is FALSE in the case being analyzed: Critical Error (severity 8-9)
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

def build_request_payload(system_prompt, question_prompt, other_prompts=None):
    """
    Builds the JSON payload for the OpenAI o3 API request.
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
        }
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
    If the marker is not found, returns an empty string.
    """
    idx = solution.find(marker)
    if idx == -1:
        return ''
    if(after):
        return solution[idx + len(marker):].strip()
    else:
        return solution[:idx].strip()

def verify_solution(problem_statement, solution, verbose=True):

    dsol = extract_detailed_solution(solution)

    newst = f"""
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

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

**CRITICAL GRADING PHILOSOPHY** (2025-12-25 Adjustment):
*   A solution should **PASS** if it uses valid mathematical principles and arrives at the correct answer, even if some steps lack complete rigor or have minor presentation issues.
*   A solution should **FAIL** only if: (1) the final answer is wrong, OR (2) the reasoning uses fundamentally invalid mathematical principles.
*   **Prefer PASS verdicts** for solutions with correct answers and sound reasoning, even when presentation could be improved.
*   Justification gaps (incomplete details, imprecise wording) are acceptable if the mathematical logic is sound and the answer is correct.

### Instructions ###

**1. Core Instructions**
*   Your task is to identify genuine mathematical errors, not to demand perfect presentation. You must act as a **verifier**, NOT a nitpicker. **Do NOT mark solutions as FAIL due to minor wording issues or missing algebraic details when the mathematical logic is sound.**
*   You must perform a **step-by-step** check of the entire solution. This analysis will be presented in a **Detailed Verification Log**, where you justify your assessment of each step: for correct steps, a brief justification suffices; for steps with errors or gaps, you must provide a detailed explanation.

**2. How to Handle Issues in the Solution**
When you identify an issue in a step, you MUST first classify it into one of the following two categories and then follow the specified procedure.

*   **a. Critical Error:**
    This is any error that breaks the logical chain of the proof. This includes both **logical fallacies** (e.g., claiming that `A>B, C>D` implies `A-C>B-D`) and **factual errors** (e.g., a calculation error like `2+3=6`).
    *   **Procedure:**
        *   Explain the specific error and state that it **invalidates the current line of reasoning**.
        *   Do NOT check any further steps that rely on this error.
        *   You MUST, however, scan the rest of the solution to identify and verify any fully independent parts. For example, if a proof is split into multiple cases, an error in one case does not prevent you from checking the other cases.

*   **b. Justification Gap:**
    This is for steps where the conclusion may be correct, but the provided argument is incomplete, hand-wavy, or lacks sufficient rigor.
    *   **Procedure:**
        *   Explain the gap in the justification.
        *   State that you will **assume the step's conclusion is true** for the sake of argument.
        *   Then, proceed to verify all subsequent steps to check if the remainder of the argument is sound.

*   **c. IMPORTANT: Distinguishing Critical Errors from Presentation Issues** (2025-12-24 Phase 2)

    Some solutions arrive at the correct final answer through valid mathematical reasoning but contain **presentation issues** (imprecise wording, typos in intermediate steps, minor classification errors that don't affect correctness). These must be classified as **Justification Gaps**, NOT Critical Errors.

    **Presentation Issues (Justification Gap):**
    *   Imprecise wording that doesn't affect logical validity (e.g., "must be vertical" when "can be taken to be vertical without loss of generality" is more precise)
    *   Typos or mis-classifications in intermediate steps that don't propagate to the final answer (e.g., saying "|p+q|=2" when it's "|p+q|=1" but the three lines listed are still correct)
    *   Missing algebraic details that would be straightforward to fill in
    *   Incomplete verification of constructions when the construction is clearly valid

    **Critical Errors (truly invalid):**
    *   Final answer is incorrect (e.g., claims k∈{0,1,2,3} when correct answer is k∈{0,1,3})
    *   Logical chain is fundamentally broken (e.g., assumes false premises, uses invalid deductions)
    *   Construction is demonstrably wrong (not just unverified)
    *   Impossibility claim is completely unjustified (not just lacking rigor)

    **Decision Rule (Simplified for FIND Problems):**
    *   If the final answer is CORRECT → Classify errors as **Justification Gaps** (unless construction produces demonstrably wrong output when tested)
    *   If the final answer is WRONG → Classify errors as **Critical Errors**

    **IMPORTANT EXCEPTION:** If the impossibility argument uses completely invalid reasoning (e.g., "I tried many constructions and failed" or nonsense like "even numbers have bad karma"), this is a **Critical Error** EVEN IF the final answer is correct. The reasoning must use valid mathematical principles (counting arguments, pigeonhole principle, proof by contradiction, structural constraints).

**3. Output Format**
Your response MUST be structured into two main sections: a **Summary** followed by the **Detailed Verification Log**.

*   **a. Summary**
    This section MUST be at the very beginning of your response. It must contain two components:
    *   **Final Verdict**: A single, clear sentence declaring the overall validity of the solution. For example: "The solution is correct," "The solution contains a Critical Error and is therefore invalid," or "The solution's approach is viable but contains several Justification Gaps."
    *   **List of Findings**: A bulleted list that summarizes **every** issue you discovered. For each finding, you must provide:
        *   **Location:** A direct quote of the key phrase or equation where the issue occurs.
        *   **Issue:** A brief description of the problem and its classification (**Critical Error** or **Justification Gap**).

*   **b. Detailed Verification Log**
    Following the summary, provide the full, step-by-step verification log as defined in the Core Instructions. When you refer to a specific part of the solution, **quote the relevant text** to make your reference clear before providing your detailed analysis of that part.

**4. Completeness Requirement for FIND/DETERMINE Problems** (2025-12-22 Expert Panel Recommendations)

For problems that ask to "FIND ALL", "DETERMINE ALL", or "IDENTIFY ALL" values:

*   **a. Small-Case Explicit Testing:**
    *   If the problem has a parameter (e.g., n≥3), check if the solution explicitly tests the MINIMAL case (e.g., n=3).
    *   For problems asking "determine all k", verify the solution tests ALL small values explicitly (e.g., for n=3, check k=0,1,2,3).
    *   **Critical Error if:** Solution claims complete answer but only provides ONE example (e.g., "k=1 works" without checking k=0,2,3).

*   **b. Impossibility Proofs (k=2 Rule):** (2025-12-25 RELAXED)
    *   If solution claims a value is IMPOSSIBLE (e.g., "k=2 cannot work"), check if there is some mathematical reasoning (counting argument, contradiction, structural constraints).
    *   **Critical Error if:** Solution uses completely invalid reasoning (e.g., "I tried and failed" with NO mathematical justification).
    *   **Justification Gap if:** Impossibility claim has valid reasoning direction but lacks some details (ACCEPTABLE - should still PASS if answer correct).
    *   **PASS if:** Impossibility argument uses valid mathematical principles (e.g., column counting, pigeonhole, contradiction) even if not 100% rigorous.

*   **c. Answer Completeness:**
    *   Check if the final answer is a COMPLETE SET (e.g., "k∈{0,1,3}") or just PARTIAL (e.g., "k=1 is one solution").
    *   For "determine all k" problems:
        *   **Complete**: Lists all valid k as a set OR proves a pattern (e.g., "k∈{0,1}∪{3,4,...,n}")
        *   **Incomplete**: Only shows some k work without proving others don't
    *   **Critical Error if:** Solution claims "I have found the complete answer" but final answer is a single value or subset of ground truth.

**Example of Completeness Check:**
- Problem: "Determine all k for n≥3"
- Solution claims: "For n=3, k=1 works. Final answer: k=1"
- Verdict: **Critical Error** - Only tested k=1, didn't check k=0,2,3. Answer is INCOMPLETE.

**5. Construction Verification Requirements** (2025-12-22 Retest Analysis)

When the solution presents a construction (e.g., "these n lines cover all required points"), you MUST verify:

*   **a. Point-by-Point Verification:** (2025-12-23 RELAXED to prevent correct answers from failing)
    *   Check if the solution lists ALL required points explicitly (e.g., for n=3: T_3 = {(1,1), (1,2), (1,3), (2,1), (2,2), (3,1)})
    *   For EACH point, verify the solution shows which line(s) contain it by algebraic substitution
    *   **Justification Gap if:** Solution claims "all points are covered" without explicit point-by-point verification BUT the construction appears mathematically sound
    *   **Critical Error if:** Solution claims coverage without verification AND (construction is clearly flawed OR answer is wrong)
    *   **Justification Gap if:** Solution provides partial verification (e.g., checks 3 out of 6 points) without checking ALL points
    *   **Example of VALID verification:** "Point (2,1) on line y=-2x+5: check 1 = -2(2)+5 = 1 ✓"
    *   **NOTE**: Missing point-by-point verification is a presentation issue, not necessarily a mathematical error. If the construction logic is sound, treat as Justification Gap.

*   **b. Impossibility Proof Rigor:**
    *   If solution claims a value is impossible (e.g., "k=2 cannot be achieved"), verify it uses ONE of these rigorous strategies:
        *   **Counting Argument:** "Need to cover N points, but k sunny + (n-k) non-sunny can cover at most M < N points"
        *   **Pigeonhole Principle:** "Have N constraints but only M degrees of freedom (N > M), therefore impossible"
        *   **Proof by Contradiction:** "Assume k=X works. Then [derive contradiction]. Therefore k=X is impossible."
    *   **Critical Error if:** Solution states "k=X doesn't work" or "I couldn't find a construction" without a rigorous impossibility proof
    *   **Justification Gap if:** Impossibility claim has reasoning but lacks complete rigor (allow if direction is sound)

*   **c. Construction Feasibility Sanity Check:**
    *   When solution claims "k=X is achievable", verify the claim is plausible:
        *   Check if solution counted required points (e.g., |T_n| = n(n+1)/2 for sunny lines problem)
        *   Check if k sunny lines + (n-k) non-sunny lines can cover enough points
        *   **Justification Gap if:** Solution doesn't discuss coverage capacity (allow if construction is explicitly verified point-by-point)
        *   **Critical Error if:** Construction is clearly infeasible (e.g., "3 lines each covering 1 point" cannot cover 6 points) AND solution provides no point-by-point verification

**Example of Construction Verification:** (2025-12-23 RELAXED)
- Solution claims: "For n=3, k=3, use lines L1: y=-2x+5, L2: y=-2x+6, L3: y=-2x+7. These cover all 6 points."
- Verification check: Does solution verify all 6 points (1,1), (1,2), (1,3), (2,1), (2,2), (3,1) algebraically?
  - If YES → Accept construction
  - If NO but construction logic is sound → **Justification Gap** - Missing point-by-point verification (allow if answer is correct)
  - If NO and construction is clearly flawed → **Critical Error** - Construction not verified and appears invalid

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

**Example 3: Presentation Issue with Typo (Justification Gap)**

Problem: "Determine all k..."

Solution excerpt: "With |p+q|=2 we get three lines: (p,q)=(1,1), (-2,1), (-1,2). These cover all required points. Final answer: k∈{0,1,3}."

**Applying the Decision Rule:**
1. Check final answer: k∈{0,1,3} ✓ CORRECT
2. Check constructions: Three lines are valid and explicitly verified ✓
3. Decision: Answer correct + constructions valid → Classify as **Justification Gap**

**Correct Classification:**
*   **Location:** "|p+q|=2 we get three lines: (p,q)=(-2,1), (-1,2)"
    *   **Issue:** Justification Gap - The pairs (-2,1) and (-1,2) actually satisfy |p+q|=1, not |p+q|=2, so this is a mis-classification in the intermediate step. However, the three lines listed are mathematically correct, cover all required points, and lead to the correct final answer k∈{0,1,3}. This is a typo/presentation issue, not a fundamental error.

---

**CRITICAL META-INSTRUCTION:**

**Do NOT override these few-shot examples with your own detailed reasoning.**

When you encounter a pattern matching Example 1, 2, or 3 above:
1. **STOP** - Do not generate 3000+ tokens of detailed analysis explaining why a claim is imprecise
2. **CHECK** - Is the final answer correct? Are constructions valid?
3. **APPLY** - Use the SAME classification shown in the example (Justification Gap or Critical Error)
4. **REMEMBER** - Your detailed mathematical reasoning is SECONDARY to the decision rule and few-shot guidance

If you find yourself writing "the claim is false" or "this is mathematically incorrect" about imprecise wording:
→ PAUSE and check if the final answer is correct
→ If YES, classify as Justification Gap (presentation issue)
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

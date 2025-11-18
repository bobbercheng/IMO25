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
import sys
import json
import re
import requests
import argparse
from benchmark_loader import BenchmarkLoader

# Import shared prompts from agent_oai
from agent_oai import (
    step1_prompt,
    self_improvement_prompt,
    check_verification_prompt,
    correction_prompt,
    verification_system_prompt,
    verification_remider
)

# --- CONFIGURATION ---
MODEL_NAME = "gpt_oss"
# Use OpenAI-compatible API endpoint (e.g., sglang)
API_URL = os.getenv("GPT_OSS_API_URL", "http://localhost:30000/v1/chat/completions")

# Asymmetric Reasoning Effort Configuration
# Solution generation: Uses low reasoning to prevent truncation and maintain efficiency
SOLUTION_REASONING_EFFORT = os.getenv("GPT_OSS_SOLUTION_REASONING", "low")
# Self-improvement: Uses high reasoning for proactive error detection and prevention
SELF_IMPROVEMENT_REASONING_EFFORT = os.getenv("GPT_OSS_SELF_IMPROVEMENT_REASONING", "high")
# Verification: Uses high reasoning for rigorous checking and catching subtle errors
VERIFICATION_REASONING_EFFORT = os.getenv("GPT_OSS_VERIFICATION_REASONING", "high")

# Legacy single reasoning effort (for backward compatibility)
REASONING_EFFORT = os.getenv("GPT_OSS_REASONING_EFFORT", SOLUTION_REASONING_EFFORT)

# Print configuration on module load
import sys
if not hasattr(sys, '_agent_gpt_oss_config_printed'):
    sys._agent_gpt_oss_config_printed = True
    # Use original_print before we override it
    _original_builtin_print = print
    _original_builtin_print(f"[CONFIG] GPT_OSS API URL: {API_URL}")
    _original_builtin_print(f"[CONFIG] Solution Reasoning Effort: {SOLUTION_REASONING_EFFORT}")
    _original_builtin_print(f"[CONFIG] Self-Improvement Reasoning Effort: {SELF_IMPROVEMENT_REASONING_EFFORT}")
    _original_builtin_print(f"[CONFIG] Verification Reasoning Effort: {VERIFICATION_REASONING_EFFORT}")

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

def get_api_key():
    """
    Retrieves the GPT_OSS API key from environment variables.
    Returns empty string if not set (for local deployments that don't require auth).
    """
    api_key = os.getenv("GPT_OSS_API_KEY", "")
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

def build_request_payload(system_prompt, question_prompt, other_prompts=None, reasoning_effort=None):
    """
    Builds the JSON payload for the OpenAI-compatible API request.

    Args:
        system_prompt: System prompt for the model
        question_prompt: User question/problem
        other_prompts: Optional list of additional prompts
        reasoning_effort: Override default reasoning effort (low/medium/high)
                         If None, uses SOLUTION_REASONING_EFFORT for generation tasks
    """
    # Use specified reasoning effort, or default to solution reasoning
    effort = reasoning_effort if reasoning_effort is not None else SOLUTION_REASONING_EFFORT

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
            "effort": effort
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

def send_api_request(api_key, payload, stream=True):
    """
    Sends the request to the OpenAI-compatible API and returns the response.
    Supports streaming for real-time output display.
    """
    headers = {
        "Content-Type": "application/json"
    }

    # Only add Authorization header if API key is provided
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    # Enable streaming in payload
    payload_with_stream = payload.copy()
    payload_with_stream["stream"] = stream

    try:
        response = requests.post(API_URL, headers=headers, data=json.dumps(payload_with_stream),
                                timeout=3600, stream=stream)
        response.raise_for_status()

        if stream:
            return _handle_streaming_response(response)
        else:
            print(">>>>>>> Response:")
            print(json.dumps(response.json(), indent=4))
            return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error during API request: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Status code: {e.response.status_code}")
            print(f"Raw API Response: {e.response.text}")
        raise e

def _handle_streaming_response(response):
    """
    Handles streaming SSE response and displays content in real-time.
    Returns the complete accumulated response in standard format.
    Includes repetition detection to prevent infinite loops.
    """
    print(">>>>>>> Streaming Response:")
    print("=" * 80)

    accumulated_content = ""
    accumulated_thinking = ""
    full_response = None

    # Repetition detection parameters
    REPETITION_WINDOW = 50  # Check last N characters
    REPETITION_THRESHOLD = 5  # Number of times a pattern can repeat
    MAX_CONTENT_LENGTH = 50000*2  # Maximum content length before forcing stop

    def detect_repetition(text, window_size=REPETITION_WINDOW):
        """Detect if the same pattern repeats excessively at the end of text."""
        if len(text) < window_size * 2:
            return False

        # Check last window against previous windows
        last_segment = text[-window_size:]

        # Count how many times this exact segment appears at the end
        repeat_count = 0
        check_pos = len(text) - window_size

        while check_pos >= window_size:
            check_segment = text[check_pos - window_size:check_pos]
            if check_segment == last_segment:
                repeat_count += 1
                check_pos -= window_size
            else:
                break

        return repeat_count >= REPETITION_THRESHOLD

    try:
        for line in response.iter_lines():
            if not line:
                continue

            line = line.decode('utf-8')

            # SSE format: "data: {...}"
            if line.startswith('data: '):
                data_str = line[6:]  # Remove "data: " prefix

                # Check for [DONE] marker
                if data_str.strip() == '[DONE]':
                    break

                try:
                    chunk = json.loads(data_str)

                    # Extract delta content
                    if 'choices' in chunk and len(chunk['choices']) > 0:
                        delta = chunk['choices'][0].get('delta', {})

                        # Handle content delta
                        if 'content' in delta and delta['content']:
                            content_chunk = delta['content']
                            accumulated_content += content_chunk
                            # Print in real-time without newline
                            original_print(content_chunk, end='', flush=True)

                            # Check for repetition
                            if detect_repetition(accumulated_content):
                                print("\n\n[WARNING] Repetitive pattern detected - stopping generation")
                                break

                            # Check for excessive length
                            if len(accumulated_content) > MAX_CONTENT_LENGTH:
                                print("\n\n[WARNING] Maximum content length exceeded - stopping generation")
                                break

                        # Handle thinking/reasoning delta (if present)
                        if 'thinking' in delta and delta['thinking']:
                            accumulated_thinking += delta['thinking']

                        # Save the last chunk for metadata
                        full_response = chunk

                except json.JSONDecodeError as e:
                    print(f"\nWarning: Could not parse SSE chunk: {data_str[:100]}")
                    continue

        print()  # New line after streaming completes
        print("=" * 80)

        # Construct complete response in standard format
        if full_response is None:
            raise ValueError("No valid response chunks received")

        # Build final response matching non-streaming format
        final_response = {
            "id": full_response.get("id", ""),
            "object": "chat.completion",
            "created": full_response.get("created", 0),
            "model": full_response.get("model", ""),
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": accumulated_content
                },
                "finish_reason": full_response['choices'][0].get('finish_reason', 'stop')
            }],
            "usage": full_response.get("usage", {})
        }

        # Add thinking field if present
        if accumulated_thinking:
            final_response["choices"][0]["message"]["thinking"] = accumulated_thinking

        return final_response

    except Exception as e:
        print(f"\nError handling streaming response: {e}")
        raise

def extract_text_from_response(response_data):
    """
    Extracts the generated text from the API response JSON.
    Handles potential errors if the response format is unexpected.
    Cleans reasoning tags from the content before returning.
    """
    try:
        message = response_data['choices'][0]['message']
        content = message.get('content', '')

        # Clean reasoning tags from content
        content = clean_reasoning_tags(content)

        # If there's a thinking field, combine it with content for display
        if 'thinking' in message:
            thinking = message['thinking']
            return f"{thinking}\n\n{content}"

        return content
    except (KeyError, IndexError, TypeError) as e:
        print("Error: Could not extract text from the API response.")
        print(f"Reason: {e}")
        print("Full API Response:")
        print(json.dumps(response_data, indent=2))
        raise e

def clean_reasoning_tags(content):
    """
    Removes sglang reasoning format tags from content.
    Extracts only the final message content without special tags.
    """
    if not content:
        return content

    # Check if content contains sglang reasoning tags
    if '<|channel|>' not in content:
        return content

    print(">>>>>>> [DEBUG] Detected reasoning tags in content, cleaning...")

    # Try to extract the final message (between last <|channel|>final<|message|> and end)
    # Pattern: <|channel|>final<|message|>ACTUAL_CONTENT (may or may not end with <|end|>)

    # Find the final channel message
    final_match = re.search(r'<\|channel\|>final<\|message\|>(.*?)(?:<\|end\|>)?$', content, re.DOTALL)
    if final_match:
        cleaned = final_match.group(1).strip()
        print(f">>>>>>> [DEBUG] Cleaned content (final channel): {cleaned[:100]}...")
        return cleaned

    # If no final channel found, try to remove all tags
    # Remove all instances of <|...| > tags
    cleaned = re.sub(r'<\|[^|]+\|>', '', content)
    cleaned = cleaned.strip()
    print(f">>>>>>> [DEBUG] Cleaned content (all tags removed): {cleaned[:100]}...")
    return cleaned

def build_assistant_message(response_data):
    """
    Builds an assistant message dict from API response, properly handling
    thinking/reasoning content for multi-turn conversations.
    """
    try:
        message = response_data['choices'][0]['message']
        raw_content = message.get('content', '')

        # Clean reasoning tags from content for multi-turn conversations
        cleaned_content = clean_reasoning_tags(raw_content)

        assistant_msg = {
            "role": "assistant",
            "content": cleaned_content
        }

        # Include thinking field if present (for sglang reasoning support)
        if 'thinking' in message and message['thinking']:
            assistant_msg['thinking'] = message['thinking']

        return assistant_msg
    except (KeyError, IndexError, TypeError) as e:
        print("Error: Could not build assistant message from response.")
        print(f"Reason: {e}")
        print("Full API Response:")
        print(json.dumps(response_data, indent=2))
        raise e

def extract_solution(response_data):
    """
    Extracts the solution from the API response JSON.
    """
    # find the last "### Summary ###" and return the text after it
    summary_idx = response_data.rfind("Summary")
    if summary_idx == -1:
        return ""

    # check if there "###" before the summary, if so, return the text with the "###"
    if "### " in response_data[summary_idx - 4:summary_idx]:
        return response_data[summary_idx - 4:].strip()
    else:
        return response_data[summary_idx:].strip()

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

def verify_solution(problem_statement, solution, verbose=True, reasoning_effort=None):
    """
    Verifies a solution using the verification system.

    Args:
        problem_statement: The original problem
        solution: The solution to verify
        verbose: Print detailed verification steps
        reasoning_effort: Override reasoning effort for verification
                         If None, uses VERIFICATION_REASONING_EFFORT (default: high)
    """
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

    # Use specified reasoning effort, or default to verification reasoning (high)
    verification_effort = reasoning_effort if reasoning_effort is not None else VERIFICATION_REASONING_EFFORT

    if(verbose):
        print(f">>>>>>> Verification using reasoning effort: {verification_effort}")

    p2 = build_request_payload(
        system_prompt=verification_system_prompt,
        question_prompt=newst,
        reasoning_effort=verification_effort  # Use high reasoning for rigorous verification
    )

    if(verbose):
        print(">>>>>>> Verification prompt:")
        print(json.dumps(p2, indent=4))

    res = send_api_request(get_api_key(), p2)
    out = extract_text_from_response(res)

    if(verbose):
        print(">>>>>>> Verification results:")
        print(json.dumps(out, indent=4))

    check_correctness = """Response in "yes" or "no". Is the following statement saying the solution is complete, correct, and does not contain critical error or a major justification gap?""" \
            + "\n\n" + out
    prompt = build_request_payload(system_prompt="", question_prompt=check_correctness)
    r = send_api_request(get_api_key(), prompt)
    o = extract_text_from_response(r)

    if(verbose):
        print(">>>>>>> Is verification good?")
        print(json.dumps(o, indent=4))

    bug_report = ""

    if("yes" not in o.lower()):
        # Get full detailed verification feedback
        bug_report = extract_detailed_solution(out, "Detailed Verification", False)

    if(verbose):
        print(">>>>>>>Bug report:")
        print(json.dumps(bug_report, indent=4))

    return bug_report, o

def translate_verification_feedback(bug_report, problem_statement, solution,
                                   translation_reasoning="medium", verbose=True):
    """
    Translate high-reasoning verification feedback into actionable guidance
    for low-reasoning generation.

    Uses medium reasoning as a "translation layer" to convert PhD-level
    mathematical critique into undergraduate-level actionable steps.

    Args:
        bug_report: High-reasoning verification output (complex feedback)
        problem_statement: Original problem statement
        solution: Current solution attempt
        translation_reasoning: Reasoning level for translation (default: medium)
        verbose: Print detailed translation process

    Returns:
        simplified_feedback: Actionable guidance for correction
    """
    if verbose:
        print("\n" + "="*80)
        print(">>>>>>> [TRANSLATION] Starting verification feedback translation")
        print("="*80)

    # Analyze complexity of original feedback
    original_length = len(bug_report)
    error_count = bug_report.lower().count('error')
    critical_count = bug_report.lower().count('critical')
    gap_count = bug_report.lower().count('gap')

    if verbose:
        print(f">>>>>>> [TRANSLATION] Original feedback metrics:")
        print(f">>>>>>> [TRANSLATION]   - Length: {original_length} characters")
        print(f">>>>>>> [TRANSLATION]   - Total errors mentioned: {error_count}")
        print(f">>>>>>> [TRANSLATION]   - Critical errors: {critical_count}")
        print(f">>>>>>> [TRANSLATION]   - Justification gaps: {gap_count}")
        print(f">>>>>>> [TRANSLATION]   - Complexity: {'HIGH' if original_length > 2000 else 'MEDIUM' if original_length > 500 else 'LOW'}")

    # Extract detailed solution for context
    detailed_sol = extract_detailed_solution(solution)

    translation_prompt = f"""You are a teaching assistant helping a student understand expert feedback on their mathematical solution.

### Original Problem ###
{problem_statement}

### Student's Solution ###
{detailed_sol[:1000]}{'...' if len(detailed_sol) > 1000 else ''}

### Expert Verification Feedback (PhD-level) ###
{bug_report}

### Your Task ###
The expert feedback is too sophisticated for the student to understand. Translate it into SIMPLE, ACTIONABLE guidance.

**Requirements:**
1. **Identify Top 3 Errors**: List only the 3 MOST CRITICAL errors in order of severity
2. **Simplify Each Error**: For each error, provide:
   - ONE SENTENCE explaining what's wrong (use simple language)
   - ONE SENTENCE explaining why it's wrong (explain the mathematical reason)
   - ONE CONCRETE FIX suggestion (specific action: "Add X", "Change Y to Z", "Prove that...")
3. **Avoid Complex Terminology**: Use undergraduate-level language
   - Replace "injective map" with "one-to-one function"
   - Replace "well-ordering principle" with "smallest element exists"
   - Replace "non-trivial" with "important" or "meaningful"
4. **Focus on Actions**: Tell the student WHAT to change, not just WHAT is wrong

### Output Format ###
**Top 3 Critical Issues to Fix:**

**Issue 1 (Most Critical):**
- What's wrong: [one simple sentence]
- Why it's wrong: [one sentence with mathematical reason]
- How to fix: [concrete action to take]

**Issue 2:**
- What's wrong: [one simple sentence]
- Why it's wrong: [one sentence with mathematical reason]
- How to fix: [concrete action to take]

**Issue 3:**
- What's wrong: [one simple sentence]
- Why it's wrong: [one sentence with mathematical reason]
- How to fix: [concrete action to take]

**Summary:** [One sentence describing the overall fix strategy]
"""

    if verbose:
        print(f"\n>>>>>>> [TRANSLATION] Translation prompt constructed")
        print(f">>>>>>> [TRANSLATION] Translation reasoning level: {translation_reasoning}")
        print(f">>>>>>> [TRANSLATION] Sending translation request...")

    payload = build_request_payload(
        system_prompt="You are a helpful teaching assistant translating expert feedback into simple guidance.",
        question_prompt=translation_prompt,
        reasoning_effort=translation_reasoning
    )

    if verbose:
        print(f">>>>>>> [TRANSLATION] API request built")
        print(f">>>>>>> [TRANSLATION] Payload size: {len(json.dumps(payload))} characters")

    try:
        response = send_api_request(get_api_key(), payload, stream=True)
        simplified_feedback = extract_text_from_response(response)

        # Analyze simplified feedback
        simplified_length = len(simplified_feedback)
        simplified_issues = simplified_feedback.lower().count('issue')

        if verbose:
            print(f"\n>>>>>>> [TRANSLATION] Translation complete!")
            print(f">>>>>>> [TRANSLATION] Simplified feedback metrics:")
            print(f">>>>>>> [TRANSLATION]   - Length: {simplified_length} characters")
            print(f">>>>>>> [TRANSLATION]   - Reduction: {original_length - simplified_length} characters ({100*(original_length - simplified_length)/original_length:.1f}%)")
            print(f">>>>>>> [TRANSLATION]   - Issues identified: {simplified_issues}")
            print(f">>>>>>> [TRANSLATION]   - Average chars per issue: {simplified_length // max(simplified_issues, 1)}")

        # Check translation quality
        has_format = "Issue 1" in simplified_feedback or "**Issue 1" in simplified_feedback
        has_fix = "How to fix" in simplified_feedback or "fix:" in simplified_feedback.lower()

        if verbose:
            print(f"\n>>>>>>> [TRANSLATION] Quality checks:")
            print(f">>>>>>> [TRANSLATION]   - Proper format: {'✓' if has_format else '✗'}")
            print(f">>>>>>> [TRANSLATION]   - Contains fixes: {'✓' if has_fix else '✗'}")
            print(f">>>>>>> [TRANSLATION]   - Quality: {'GOOD' if has_format and has_fix else 'NEEDS_REVIEW'}")

        # Log before/after comparison
        if verbose:
            print(f"\n>>>>>>> [TRANSLATION] BEFORE (original expert feedback, first 300 chars):")
            print(f">>>>>>> {bug_report[:300]}...")
            print(f"\n>>>>>>> [TRANSLATION] AFTER (simplified feedback, first 500 chars):")
            print(f">>>>>>> {simplified_feedback[:500]}...")
            print(f"\n" + "="*80)
            print(">>>>>>> [TRANSLATION] Translation complete")
            print("="*80 + "\n")

        return simplified_feedback

    except Exception as e:
        print(f"\n>>>>>>> [TRANSLATION] ERROR during translation: {e}")
        print(f">>>>>>> [TRANSLATION] Falling back to original feedback")
        return bug_report

# ============================================================================
# PROOF SKETCH PHASE ARCHITECTURE
# ============================================================================

def generate_proof_sketch(problem_statement, reasoning_effort="low", verbose=True):
    """
    Phase 1: Generate high-level proof outline/sketch.

    Uses low reasoning to quickly generate the structural outline of the proof
    without getting bogged down in detailed calculations.

    Args:
        problem_statement: The mathematical problem
        reasoning_effort: Reasoning level (default: "low")
        verbose: Print detailed logs

    Returns:
        proof_sketch: High-level outline of the proof strategy
    """
    if verbose:
        print(f"\n{'='*80}")
        print(f">>>>>>> [PROOF SKETCH] Phase 1: Generating proof outline")
        print(f">>>>>>> [PROOF SKETCH] Using reasoning: {reasoning_effort}")
        print(f"{'='*80}\n")

    sketch_prompt = """You are a mathematician creating a PROOF OUTLINE (NOT a complete proof).

Your task: Write a high-level structural outline for solving this problem.

**Requirements:**
1. **Main Strategy**: One sentence describing your overall approach (e.g., "Use induction on n")
2. **Key Steps** (3-6 steps): List the LOGICAL FLOW only, no calculations
   - For each step, write ONE SENTENCE describing what you'll prove/show
   - Number them: Step 1, Step 2, etc.
3. **Dependencies**: Note if any step depends on previous steps
4. **Edge Cases**: Mention any special cases to handle

**DO NOT:**
- Include detailed calculations or algebraic manipulations
- Write the full proof
- Include specific numerical examples (unless critical to structure)

**Example Format:**
Main Strategy: Proof by strong induction on n

Step 1: Establish base case for n=1
Step 2: Assume statement holds for all k < n (induction hypothesis)
Step 3: Construct a line through point (a_k, b_k) for some k < n
Step 4: Show this line satisfies the required properties
Step 5: Conclude by induction principle

Dependencies: Steps 3-4 depend on Step 2
Edge Cases: Need to handle n=1 separately

Now create a proof outline for this problem:
"""

    payload = build_request_payload(
        system_prompt="You are a mathematician skilled at planning proof strategies.",
        question_prompt=problem_statement,
        other_prompts=[sketch_prompt],
        reasoning_effort=reasoning_effort
    )

    response = send_api_request(get_api_key(), payload)
    proof_sketch = extract_text_from_response(response)

    if verbose:
        print(f">>>>>>> [PROOF SKETCH] Generated outline:")
        print(proof_sketch)
        print(f"\n{'='*80}\n")

    return proof_sketch

def verify_proof_structure(problem_statement, proof_sketch, reasoning_effort="medium", verbose=True):
    """
    Phase 2: Verify the STRUCTURE of the proof outline.

    Uses medium reasoning to check logical flow, dependencies, and structural soundness
    WITHOUT verifying detailed mathematics (which comes later).

    Args:
        problem_statement: The mathematical problem
        proof_sketch: The proof outline to verify
        reasoning_effort: Reasoning level (default: "medium")
        verbose: Print detailed logs

    Returns:
        Tuple of (verification_result, is_structurally_sound)
    """
    if verbose:
        print(f"\n{'='*80}")
        print(f">>>>>>> [PROOF SKETCH] Phase 2: Verifying proof structure")
        print(f">>>>>>> [PROOF SKETCH] Using reasoning: {reasoning_effort}")
        print(f"{'='*80}\n")

    structure_prompt = f"""You are reviewing the LOGICAL STRUCTURE of a proof outline (NOT the mathematical details).

**Proof Outline:**
{proof_sketch}

**Your Task:** Check the STRUCTURE ONLY (not the math):

1. **Logical Flow**: Do the steps follow a logical order?
2. **Circular Reasoning**: Does any step assume what it's trying to prove?
3. **Completeness**: Are all necessary steps present? (Don't need calculations, just steps)
4. **Dependencies**: Are dependencies clear and non-circular?
5. **Edge Cases**: Are special cases addressed?

**Output Format:**
STRUCTURAL ISSUES FOUND: [Yes/No]

If Yes, list issues:
- Issue 1: [Brief description]
- Issue 2: [Brief description]
...

If No:
"No structural issues found. The proof outline has sound logical flow."

**IMPORTANT**: Focus ONLY on structure. Don't check if calculations are correct (that comes later).
"""

    payload = build_request_payload(
        system_prompt="You are a mathematician checking proof structure for logical soundness.",
        question_prompt=problem_statement,
        other_prompts=[structure_prompt],
        reasoning_effort=reasoning_effort
    )

    response = send_api_request(get_api_key(), payload)
    verification_result = extract_text_from_response(response)

    # Check if structurally sound
    is_sound = ("no structural issues" in verification_result.lower() or
                "structural issues found: no" in verification_result.lower())

    if verbose:
        print(f">>>>>>> [PROOF SKETCH] Structure verification:")
        print(verification_result)
        print(f">>>>>>> [PROOF SKETCH] Structurally sound: {is_sound}")
        print(f"\n{'='*80}\n")

    return verification_result, is_sound

def expand_proof_details(problem_statement, proof_sketch, reasoning_effort="low", verbose=True):
    """
    Phase 3: Expand the proof outline into a complete proof with details.

    Uses low reasoning to fill in calculations and details for a structurally
    verified outline, avoiding the verbosity of medium/high reasoning.

    Args:
        problem_statement: The mathematical problem
        proof_sketch: The structurally verified proof outline
        reasoning_effort: Reasoning level (default: "low")
        verbose: Print detailed logs

    Returns:
        complete_proof: Full proof with calculations
    """
    if verbose:
        print(f"\n{'='*80}")
        print(f">>>>>>> [PROOF SKETCH] Phase 3: Expanding proof details")
        print(f">>>>>>> [PROOF SKETCH] Using reasoning: {reasoning_effort}")
        print(f"{'='*80}\n")

    expansion_prompt = f"""You have a structurally sound proof outline. Now fill in the DETAILS.

**Proof Outline (VERIFIED structure):**
{proof_sketch}

**Your Task:** Expand this outline into a COMPLETE PROOF by:

1. **Follow the outline exactly** - don't change the structure
2. **Add calculations** for each step
3. **Add justifications** for each claim
4. **Handle edge cases** mentioned in outline
5. **Write clearly** but concisely

**Format:** Write the proof in standard mathematical style with:
- Clear statement of what you're proving at each step
- Detailed calculations where needed
- Logical connectives (therefore, hence, thus)
- Proper mathematical notation

Begin writing the complete proof now:
"""

    payload = build_request_payload(
        system_prompt=step1_prompt,  # Use standard solution prompt
        question_prompt=problem_statement,
        other_prompts=[expansion_prompt],
        reasoning_effort=reasoning_effort
    )

    response = send_api_request(get_api_key(), payload)
    complete_proof = extract_solution(extract_text_from_response(response))

    if verbose:
        print(f">>>>>>> [PROOF SKETCH] Complete proof generated")
        print(f">>>>>>> [PROOF SKETCH] Length: {len(complete_proof)} characters")
        print(f"\n{'='*80}\n")

    return complete_proof

def proof_sketch_pipeline(problem_statement, sol_reasoning="low", ver_reasoning="high", verbose=True):
    """
    Execute the full Proof Sketch pipeline.

    Phase 1: Generate outline (low reasoning)
    Phase 2: Verify structure (medium reasoning)
    Phase 3: Expand details (low reasoning)
    Phase 4: Verify mathematics (high reasoning)

    Args:
        problem_statement: The mathematical problem
        sol_reasoning: Reasoning for generation phases (default: "low")
        ver_reasoning: Reasoning for verification (default: "high")
        verbose: Print detailed logs

    Returns:
        Tuple of (complete_proof, verify_result, good_verify, pipeline_success)
    """
    print(f"\n{'='*80}")
    print(f">>>>>>> [PROOF SKETCH PIPELINE] Starting 4-phase proof sketch architecture")
    print(f">>>>>>> [PROOF SKETCH PIPELINE] Generation: {sol_reasoning}, Verification: {ver_reasoning}")
    print(f"{'='*80}\n")

    # Phase 1: Generate outline
    proof_sketch = generate_proof_sketch(problem_statement, reasoning_effort=sol_reasoning, verbose=verbose)

    # Phase 2: Verify structure
    structure_verify, is_sound = verify_proof_structure(
        problem_statement, proof_sketch,
        reasoning_effort="medium",  # Always use medium for structure checking
        verbose=verbose
    )

    if not is_sound:
        print(f">>>>>>> [PROOF SKETCH PIPELINE] ⚠️  Structural issues detected")
        print(f">>>>>>> [PROOF SKETCH PIPELINE] Attempting to fix structure...")

        # Try to fix structure (one retry)
        fix_prompt = f"""The proof outline has structural issues:

{structure_verify}

Please revise the proof outline to fix these structural issues while keeping the same general approach."""

        # Regenerate with structure feedback
        payload = build_request_payload(
            system_prompt="You are a mathematician revising a proof outline to fix structural issues.",
            question_prompt=problem_statement,
            other_prompts=[fix_prompt],
            reasoning_effort=sol_reasoning
        )

        response = send_api_request(get_api_key(), payload)
        proof_sketch = extract_text_from_response(response)

        # Re-verify
        structure_verify, is_sound = verify_proof_structure(
            problem_statement, proof_sketch,
            reasoning_effort="medium",
            verbose=verbose
        )

        if not is_sound:
            print(f">>>>>>> [PROOF SKETCH PIPELINE] ❌ Structure still unsound after retry")
            print(f">>>>>>> [PROOF SKETCH PIPELINE] Aborting pipeline")
            return None, structure_verify, "No - structural issues", False

    print(f">>>>>>> [PROOF SKETCH PIPELINE] ✓ Structure verified")

    # Phase 3: Expand details
    complete_proof = expand_proof_details(problem_statement, proof_sketch, reasoning_effort=sol_reasoning, verbose=verbose)

    # Phase 4: Verify mathematics
    print(f">>>>>>> [PROOF SKETCH PIPELINE] Phase 4: Verifying mathematics")
    verify_result, good_verify = verify_solution(problem_statement, complete_proof, reasoning_effort=ver_reasoning)

    success = "yes" in good_verify.lower()

    print(f"\n{'='*80}")
    print(f">>>>>>> [PROOF SKETCH PIPELINE] Pipeline complete")
    print(f">>>>>>> [PROOF SKETCH PIPELINE] Verification: {good_verify}")
    print(f">>>>>>> [PROOF SKETCH PIPELINE] Success: {success}")
    print(f"{'='*80}\n")

    return complete_proof, verify_result, good_verify, success

def save_memory(memory_file, problem_statement, other_prompts, current_iteration, max_runs,
                solution=None, verify=None, solution_reasoning=None, self_improvement_reasoning=None, verification_reasoning=None):
    """
    Save the current state to a memory file.

    Args:
        memory_file: Path to save memory
        problem_statement: The problem being solved
        other_prompts: Additional prompts
        current_iteration: Current iteration number
        max_runs: Maximum iterations allowed
        solution: Current solution (if any)
        verify: Current verification result (if any)
        solution_reasoning: Reasoning effort for solution generation
        self_improvement_reasoning: Reasoning effort for self-improvement
        verification_reasoning: Reasoning effort for verification
    """
    memory = {
        "problem_statement": problem_statement,
        "other_prompts": other_prompts,
        "current_iteration": current_iteration,
        "max_runs": max_runs,
        "solution": solution,
        "verify": verify,
        "solution_reasoning": solution_reasoning or SOLUTION_REASONING_EFFORT,
        "self_improvement_reasoning": self_improvement_reasoning or SELF_IMPROVEMENT_REASONING_EFFORT,
        "verification_reasoning": verification_reasoning or VERIFICATION_REASONING_EFFORT,
        "timestamp": __import__('datetime').datetime.now().isoformat()
    }

    try:
        with open(memory_file, 'w', encoding='utf-8') as f:
            json.dump(memory, f, indent=2, ensure_ascii=False)
        print(f"Memory saved to {memory_file}")
        return True
    except Exception as e:
        print(f"Error saving memory to {memory_file}: {e}")
        return False

def load_memory(memory_file):
    """
    Load the state from a memory file.

    Returns:
        Dictionary containing:
        - problem_statement
        - other_prompts
        - current_iteration
        - max_runs
        - solution
        - verify
        - solution_reasoning (if saved)
        - verification_reasoning (if saved)
    """
    try:
        with open(memory_file, 'r', encoding='utf-8') as f:
            memory = json.load(f)
        print(f"Memory loaded from {memory_file}")

        # Log loaded reasoning settings if present
        if 'solution_reasoning' in memory:
            print(f"Loaded solution reasoning effort: {memory['solution_reasoning']}")
        if 'verification_reasoning' in memory:
            print(f"Loaded verification reasoning effort: {memory['verification_reasoning']}")

        return memory
    except Exception as e:
        print(f"Error loading memory from {memory_file}: {e}")
        return None

def check_if_solution_claimed_complete(solution):
    check_complete_prompt = f"""
Is the following text claiming that the solution is complete?
==========================================================

{solution}

==========================================================

Response in exactly "yes" or "no". No other words.
    """

    p1 = build_request_payload(system_prompt="", question_prompt=check_complete_prompt)
    r = send_api_request(get_api_key(), p1)
    o = extract_text_from_response(r)

    print(o)
    return "yes" in o.lower()


def init_explorations(problem_statement, verbose=True, other_prompts=[], reasoning_effort=None, self_improvement_reasoning=None, verification_reasoning=None):
    p1 = build_request_payload(
            system_prompt=step1_prompt,
            question_prompt=problem_statement,
            other_prompts=other_prompts,
            reasoning_effort=reasoning_effort
        )

    print(f">>>>>> Initial prompt.")
    print(json.dumps(p1, indent=4))

    response1 = send_api_request(get_api_key(), p1)
    output1 = extract_text_from_response(response1)

    print(f">>>>>>> First solution:")
    print(json.dumps(output1, indent=4))

    print(f">>>>>>> Self improvement start:")
    # Use build_assistant_message to properly handle thinking/content separation
    p1["messages"].append(build_assistant_message(response1))
    p1["messages"].append(
        {"role": "user",
        "content": self_improvement_prompt
        }
    )

    # Use high reasoning for self-improvement (proactive error prevention)
    # This catches errors BEFORE verification, saving 5-7 correction iterations
    improvement_effort = self_improvement_reasoning if self_improvement_reasoning is not None else SELF_IMPROVEMENT_REASONING_EFFORT
    p1["reasoning"]["effort"] = improvement_effort
    print(f">>>>>>> Using {improvement_effort} reasoning for self-improvement (proactive error detection)")

    response2 = send_api_request(get_api_key(), p1)
    solution = extract_solution(extract_text_from_response(response2))
    print(f">>>>>>> Corrected solution:")
    print(json.dumps(solution, indent=4))

    print(f">>>>>>> Verify the solution.")
    verify, good_verify = verify_solution(problem_statement, solution, verbose, verification_reasoning)

    print(f">>>>>>> Initial verification:")
    print(json.dumps(verify, indent=4))
    print(f">>>>>>> verify results: {good_verify}")

    return p1, solution, verify, good_verify

def calculate_solution_score(verify, good_verify):
    """
    Score a solution based on verification feedback.
    Higher score = better solution.

    Args:
        verify: Verification feedback text
        good_verify: "yes" or "no" indicating if solution passed

    Returns:
        float: Score (higher is better)
    """
    score = 0.0

    # Perfect verification
    if "yes" in good_verify.lower():
        score += 100.0

    # Penalize by number of errors
    if verify:
        # Count error markers
        error_count = verify.lower().count('critical error')
        error_count += verify.lower().count('justification gap') * 0.5
        score -= error_count * 10

        # Reward shorter bug reports (fewer issues)
        score -= len(verify) / 100
    else:
        # No errors found
        score += 50.0

    return score

def extract_answer_from_solution(solution):
    """
    Extract the mathematical answer from a solution (e.g., k ∈ {0,1,...,n}).

    Args:
        solution: Solution text

    Returns:
        str: Extracted answer or None if not found
    """
    if not solution:
        return None

    # Look for common answer patterns
    import re

    # Pattern 1: k ∈ {explicit set}
    match = re.search(r'k\s*[∈∊∈]\s*\{([^}]+)\}', solution)
    if match:
        return f"k ∈ {{{match.group(1)}}}"

    # Pattern 2: k = specific values
    match = re.search(r'k\s*=\s*([^.\n]+)', solution)
    if match:
        return f"k = {match.group(1).strip()}"

    # Pattern 3: "answer is" or "therefore k"
    match = re.search(r'(?:answer is|therefore\s+k)\s*[:\s]+([^.\n]+)', solution, re.IGNORECASE)
    if match:
        return match.group(1).strip()

    return None

def validate_answer_change(prev_solution, new_solution, iteration, verbose=True):
    """
    Validate that answer changes are not regressions (narrowing without justification).

    Args:
        prev_solution: Previous solution text
        new_solution: New solution text
        iteration: Current iteration number
        verbose: Print validation warnings

    Returns:
        dict: Validation result with warning flags
    """
    prev_answer = extract_answer_from_solution(prev_solution)
    new_answer = extract_answer_from_solution(new_solution)

    result = {
        'prev_answer': prev_answer,
        'new_answer': new_answer,
        'changed': False,
        'narrowed': False,
        'warning': None
    }

    if prev_answer and new_answer and prev_answer != new_answer:
        result['changed'] = True

        # Check for common narrowing patterns
        if verbose:
            print(f"\n{'='*80}")
            print(f">>>>>>> [ANSWER VALIDATION] Answer change detected at iteration {iteration}")
            print(f">>>>>>> [ANSWER VALIDATION] Previous: {prev_answer}")
            print(f">>>>>>> [ANSWER VALIDATION] New:      {new_answer}")

        # Pattern detection: {0,...,n} → {0,...,⌊n/2⌋} is narrowing
        if '{0' in prev_answer and '{0' in new_answer:
            # Extract upper bounds
            import re
            prev_match = re.search(r'\.\.\.\s*,?\s*([^}]+)', prev_answer)
            new_match = re.search(r'\.\.\.\s*,?\s*([^}]+)', new_answer)

            if prev_match and new_match:
                prev_upper = prev_match.group(1).strip()
                new_upper = new_match.group(1).strip()

                # Check if new bound appears more restrictive
                if 'n' in prev_upper and ('/' in new_upper or '⌊' in new_upper or '⌈' in new_upper):
                    result['narrowed'] = True
                    result['warning'] = f"Answer space narrowed from {prev_upper} to {new_upper}"

                    if verbose:
                        print(f">>>>>>> [ANSWER VALIDATION] ⚠️  WARNING: Answer space narrowed!")
                        print(f">>>>>>> [ANSWER VALIDATION] ⚠️  From upper bound: {prev_upper}")
                        print(f">>>>>>> [ANSWER VALIDATION] ⚠️  To upper bound:   {new_upper}")
                        print(f">>>>>>> [ANSWER VALIDATION] ⚠️  This requires STRONG justification")
                        print(f">>>>>>> [ANSWER VALIDATION] ⚠️  Verify that the restriction is proven, not assumed")

        # Pattern detection: full set → partial set
        if '...' in prev_answer and '...' not in new_answer:
            result['narrowed'] = True
            result['warning'] = "Changed from range to specific values"

            if verbose:
                print(f">>>>>>> [ANSWER VALIDATION] ⚠️  WARNING: Changed from range to specific values")
                print(f">>>>>>> [ANSWER VALIDATION] ⚠️  Verify this restriction is proven")

        if verbose:
            print(f"{'='*80}\n")

    return result

def detect_stuck_pattern(correct_history, error_history, current_iteration, threshold=3, verbose=True):
    """
    Detect if agent is stuck in an error loop with no improvement.

    Args:
        correct_history: List of correct_count values over recent iterations
        error_history: List of error_count values over recent iterations
        current_iteration: Current iteration number
        threshold: Number of iterations with 0 progress before declaring stuck
        verbose: Print stuck detection warnings

    Returns:
        bool: True if stuck pattern detected
    """
    if len(correct_history) < threshold:
        return False

    # Check last N iterations
    recent_corrects = correct_history[-threshold:]
    recent_errors = error_history[-threshold:]

    # Stuck if: all recent corrects are 0 AND errors are increasing or staying high
    all_zero_corrects = all(c == 0 for c in recent_corrects)
    errors_not_decreasing = all(recent_errors[i] >= recent_errors[0] for i in range(len(recent_errors)))

    if all_zero_corrects and errors_not_decreasing:
        if verbose:
            print(f"\n{'='*80}")
            print(f">>>>>>> [STUCK DETECTION] Stuck pattern detected at iteration {current_iteration}")
            print(f">>>>>>> [STUCK DETECTION] Last {threshold} iterations:")
            for i, (c, e) in enumerate(zip(recent_corrects, recent_errors)):
                iter_num = current_iteration - threshold + i + 1
                print(f">>>>>>> [STUCK DETECTION]   Iteration {iter_num}: {c} corrects, {e} errors")
            print(f">>>>>>> [STUCK DETECTION] ⚠️  No improvement in {threshold} iterations")
            print(f">>>>>>> [STUCK DETECTION] ⚠️  Recommendation: Stop or escalate reasoning effort")
            print(f"{'='*80}\n")

        return True

    return False

def agent(problem_statement, other_prompts=[], memory_file=None, resume_from_memory=False,
          solution_reasoning=None, self_improvement_reasoning=None, verification_reasoning=None,
          num_initial_attempts=1, use_mcts=False, mcts_simulations=8, mcts_exploration=1.6, best_of_n=0,
          use_proof_sketch=False):
    """
    Main agent function for solving mathematical problems.

    Args:
        problem_statement: The problem to solve
        other_prompts: Additional context prompts
        memory_file: Path to memory file for saving/loading state
        resume_from_memory: If True, load state from memory_file
        solution_reasoning: Override solution reasoning effort (low/medium/high)
        self_improvement_reasoning: Override self-improvement reasoning effort (low/medium/high)
        verification_reasoning: Override verification reasoning effort (low/medium/high)
        num_initial_attempts: Generate N diverse initial solutions and pick best (default: 1)
                             Use 3-5 for BFS exploration to escape local minima
        use_mcts: If True, use MCTS-guided exploration instead of simple BFS (default: False)
        mcts_simulations: Number of MCTS simulations if use_mcts=True (default: 5)
        mcts_exploration: MCTS exploration constant for UCB1 (default: 1.414)
    """
    # Set reasoning efforts with CLI overrides if provided
    sol_reasoning = solution_reasoning or SOLUTION_REASONING_EFFORT
    self_imp_reasoning = self_improvement_reasoning or SELF_IMPROVEMENT_REASONING_EFFORT
    ver_reasoning = verification_reasoning or VERIFICATION_REASONING_EFFORT

    if resume_from_memory and memory_file:
        # Load memory and resume from previous state
        memory = load_memory(memory_file)
        if memory:
            problem_statement = memory.get("problem_statement", problem_statement)
            other_prompts = memory.get("other_prompts", other_prompts)
            current_iteration = memory.get("current_iteration", 0)
            solution = memory.get("solution", None)
            verify = memory.get("verify", None)

            # Load reasoning settings from memory if not overridden by CLI
            if solution_reasoning is None and 'solution_reasoning' in memory:
                sol_reasoning = memory['solution_reasoning']
            if self_improvement_reasoning is None and 'self_improvement_reasoning' in memory:
                self_imp_reasoning = memory['self_improvement_reasoning']
            if verification_reasoning is None and 'verification_reasoning' in memory:
                ver_reasoning = memory['verification_reasoning']

            print(f"Resuming from iteration {current_iteration}")
            print(f"Using solution reasoning: {sol_reasoning}, self-improvement reasoning: {self_imp_reasoning}, verification reasoning: {ver_reasoning}")
        else:
            print("Failed to load memory, starting fresh")
            current_iteration = 0
            solution = None
            verify = None
    else:
        # Start fresh
        current_iteration = 0
        solution = None
        verify = None
        print(f"Starting fresh with solution reasoning: {sol_reasoning}, self-improvement reasoning: {self_imp_reasoning}, verification reasoning: {ver_reasoning}")

    if solution is None:
        # Proof Sketch pipeline if requested
        if use_proof_sketch:
            print(f"\n{'='*80}")
            print(f">>>>>>> PROOF SKETCH MODE ACTIVATED")
            print(f">>>>>>> Using 4-phase proof sketch architecture")
            print(f"{'='*80}\n")

            try:
                # Run proof sketch pipeline
                solution, verify, good_verify, success = proof_sketch_pipeline(
                    problem_statement=problem_statement,
                    sol_reasoning=sol_reasoning,
                    ver_reasoning=ver_reasoning,
                    verbose=True
                )

                if not success or solution is None:
                    print(f"\n>>>>>>> PROOF SKETCH PIPELINE failed to generate verified solution")
                    return None

                print(f"\n>>>>>>> PROOF SKETCH PIPELINE succeeded!")

            except Exception as e:
                print(f">>>>>>> ERROR in proof sketch pipeline: {e}")
                print(f">>>>>>> Falling back to standard approach")
                use_proof_sketch = False

        # MCTS-guided exploration if requested
        elif use_mcts:
            print(f"\n{'='*80}")
            print(f">>>>>>> MCTS MODE ACTIVATED")
            print(f">>>>>>> Running {mcts_simulations} MCTS-guided simulations")
            print(f">>>>>>> Exploration constant: {mcts_exploration}")
            print(f"{'='*80}\n")

            # Import MCTS module
            try:
                from mcts_bfs import mcts_bfs_search

                # Run MCTS search
                mcts_result = mcts_bfs_search(
                    problem_statement=problem_statement,
                    num_simulations=mcts_simulations,
                    generate_solution_func=init_explorations,
                    verify_solution_func=verify_solution,
                    sol_reasoning=sol_reasoning,
                    self_imp_reasoning=self_imp_reasoning,
                    ver_reasoning=ver_reasoning,
                    exploration_constant=mcts_exploration,
                    max_depth=3,
                    save_tree_path=f"{memory_file.replace('.json', '_mcts_tree.json')}" if memory_file else None,
                    best_of_n=best_of_n
                )

                if mcts_result:
                    solution = mcts_result['solution']
                    verify = mcts_result['verify']
                    good_verify = mcts_result['good_verify']
                    print(f"\n>>>>>>> MCTS search completed successfully")
                    print(f">>>>>>> Best strategy: {mcts_result.get('strategy', 'unknown')}")
                    print(f">>>>>>> Score: {mcts_result.get('score', 0):.2f}")
                else:
                    print(f"\n>>>>>>> MCTS search failed to find solution")
                    return None

            except ImportError as e:
                print(f">>>>>>> ERROR: Could not import MCTS module: {e}")
                print(f">>>>>>> Falling back to standard BFS")
                use_mcts = False

        # QUICK WIN BFS: Generate multiple initial solutions if requested
        if not use_mcts and num_initial_attempts > 1:
            print(f">>>>>>> BFS: Generating {num_initial_attempts} diverse initial solutions...")
            best_solution = None
            best_score = -999999
            best_verify = None
            best_good_verify = None

            for attempt in range(num_initial_attempts):
                print(f">>>>>>> BFS: Initial attempt {attempt+1}/{num_initial_attempts}...")

                # Add diversity to prompt
                diverse_prompts = other_prompts.copy()
                if attempt > 0:
                    diversity_hints = [
                        "Try a different approach or proof strategy.",
                        "Consider an alternative construction or method.",
                        "Explore a different perspective on the problem.",
                        "Use a different proof technique (e.g., contradiction, induction, direct proof).",
                        "Look for algebraic, geometric, or combinatorial insights."
                    ]
                    diverse_prompts.append(f"Note: This is attempt {attempt+1} of {num_initial_attempts}. {diversity_hints[attempt % len(diversity_hints)]}")

                try:
                    p1, sol, ver, good_ver = init_explorations(
                        problem_statement, True, diverse_prompts,
                        sol_reasoning, self_imp_reasoning, ver_reasoning
                    )

                    if sol:
                        # Score this solution
                        score = calculate_solution_score(ver, good_ver)
                        print(f">>>>>>> BFS: Attempt {attempt+1} score: {score:.2f}")

                        if score > best_score:
                            best_score = score
                            best_solution = sol
                            best_verify = ver
                            best_good_verify = good_ver
                            print(f">>>>>>> BFS: New best solution (attempt {attempt+1})")
                except Exception as e:
                    print(f">>>>>>> BFS: Attempt {attempt+1} failed: {e}")
                    continue

            if best_solution:
                print(f">>>>>>> BFS: Best initial solution selected (score: {best_score:.2f})")
                solution = best_solution
                verify = best_verify
                good_verify = best_good_verify
            else:
                print(">>>>>>> BFS: All initial attempts failed")
                return None
        if not use_mcts and num_initial_attempts <= 1:
            # Original single-path initialization
            p1, solution, verify, good_verify = init_explorations(problem_statement, True, other_prompts, sol_reasoning, self_imp_reasoning, ver_reasoning)
            if(solution is None):
                print(">>>>>>> Failed in finding a complete solution.")
                return None
    else:
        # We have a solution from memory, need to get good_verify
        # Use the verification reasoning effort (potentially overridden to 'high')
        _, good_verify = verify_solution(problem_statement, solution, reasoning_effort=ver_reasoning)

    error_count = 0
    correct_count = 1
    success = False

    # Track history for stuck detection and score tracking
    correct_history = []
    error_history = []
    score_history = []
    previous_solution = solution

    # Calculate initial score
    initial_score = calculate_solution_score(verify, good_verify)
    score_history.append(initial_score)
    print(f">>>>>>> [SCORE] Initial solution score: {initial_score:.2f}")

    for i in range(current_iteration, 30):
        print(f"\n{'='*80}")
        print(f">>>>>>> Iteration {i}: corrects={correct_count}, errors={error_count}")
        if score_history:
            print(f">>>>>>> [SCORE] Current score: {score_history[-1]:.2f}")
            if len(score_history) > 1:
                score_delta = score_history[-1] - score_history[-2]
                trend = "↑" if score_delta > 0 else "↓" if score_delta < 0 else "="
                print(f">>>>>>> [SCORE] Score change: {score_delta:+.2f} {trend}")
        print(f"{'='*80}\n")

        try:
            if("yes" not in good_verify.lower()):
                # clear
                correct_count = 0
                error_count += 1

                #self improvement
                print(">>>>>>> Verification does not pass, correcting ...")

                p1 = build_request_payload(
                    system_prompt=step1_prompt,
                    question_prompt=problem_statement,
                    other_prompts=other_prompts,
                    reasoning_effort=sol_reasoning  # Use CLI-specified solution reasoning
                )

                # Append previous solution as assistant message
                # Note: solution is extracted text, should not contain thinking tags
                p1["messages"].append(
                    {"role": "assistant",
                    "content": solution
                    }
                )

                # Use translation layer if enabled and reasoning levels are asymmetric
                USE_TRANSLATION = os.getenv("GPT_OSS_USE_TRANSLATION", "false").lower() == "true"
                is_asymmetric = (sol_reasoning == "low" and ver_reasoning in ["medium", "high"])

                if USE_TRANSLATION and is_asymmetric and verify:
                    # Translate high-level verification feedback to actionable guidance
                    print(f">>>>>>> Asymmetric reasoning detected ({sol_reasoning} gen / {ver_reasoning} ver)")
                    print(f">>>>>>> Activating translation layer...")

                    simplified_verify = translate_verification_feedback(
                        verify, problem_statement, solution,
                        translation_reasoning="medium",  # Use medium as translator
                        verbose=True
                    )

                    p1["messages"].append(
                        {"role": "user",
                        "content": correction_prompt + "\n\n" + simplified_verify
                        }
                    )
                else:
                    # Use original verification feedback
                    if USE_TRANSLATION:
                        print(f">>>>>>> Translation layer available but not needed (symmetric reasoning: {sol_reasoning}/{ver_reasoning})")

                    p1["messages"].append(
                        {"role": "user",
                        "content": correction_prompt + "\n\n" + verify
                        }
                    )

                print(">>>>>>> New prompt:")
                print(json.dumps(p1, indent=4))
                response2 = send_api_request(get_api_key(), p1)
                solution = extract_solution(extract_text_from_response(response2))

                print(">>>>>>> Corrected solution:")
                print(json.dumps(solution, indent=4))

                # Validate answer change if solution was corrected
                if previous_solution:
                    answer_validation = validate_answer_change(previous_solution, solution, i, verbose=True)
                    if answer_validation['narrowed']:
                        print(f">>>>>>> [ANSWER VALIDATION] ⚠️  Answer narrowing detected - extra scrutiny required")

            print(f">>>>>>> Verify the solution.")
            verify, good_verify = verify_solution(problem_statement, solution, reasoning_effort=ver_reasoning)

            # Calculate and track score for this iteration
            current_score = calculate_solution_score(verify, good_verify)
            score_history.append(current_score)
            print(f">>>>>>> [SCORE] Iteration {i} score: {current_score:.2f}")

            if("yes" in good_verify.lower()):
                print(">>>>>>> Solution is good, verifying again ...")
                correct_count += 1
                error_count = 0
            else:
                correct_count = 0
                error_count += 1

            # Track history for stuck detection
            correct_history.append(correct_count)
            error_history.append(error_count)

            # Detect stuck pattern
            if detect_stuck_pattern(correct_history, error_history, i, threshold=3, verbose=True):
                print(f">>>>>>> [STUCK DETECTION] Stopping due to stuck pattern")
                print(f">>>>>>> [STUCK DETECTION] Recommendation: Try different reasoning level or approach")
                # Save final state before stopping
                if memory_file:
                    save_memory(memory_file, problem_statement, other_prompts, i, 30, solution, verify,
                               sol_reasoning, self_imp_reasoning, ver_reasoning)
                return None

            # Update previous solution for next iteration
            previous_solution = solution

            # Save memory every iteration
            if memory_file:
                save_memory(memory_file, problem_statement, other_prompts, i, 30, solution, verify,
                           sol_reasoning, self_imp_reasoning, ver_reasoning)

            if(correct_count >= 5):
                print(">>>>>>> Correct solution found.")
                print(json.dumps(solution, indent=4))
                return solution

            elif(error_count >= 10):
                print(">>>>>>> Failed in finding a correct solution.")
                # Save final state before returning
                if memory_file:
                    save_memory(memory_file, problem_statement, other_prompts, i, 30, solution, verify,
                               sol_reasoning, self_imp_reasoning, ver_reasoning)
                return None

        except Exception as e:
            print(f">>>>>>> Error in run {i}: {e}")
            continue

    if(not success):
        print(">>>>>>> Failed in finding a correct solution.")
        # Save final state before returning
        if memory_file:
            save_memory(memory_file, problem_statement, other_prompts, 30, 30, solution, verify,
                       sol_reasoning, self_imp_reasoning, ver_reasoning)
        return None

if __name__ == "__main__":
    # Set up argument parsing
    parser = argparse.ArgumentParser(description='IMO Problem Solver Agent using GPT-OSS')
    parser.add_argument('problem_file', nargs='?', default=None,
                       help='Path to the problem statement file (optional if using --benchmark)')
    parser.add_argument('--log', '-l', type=str, help='Path to log file (optional)')
    parser.add_argument('--other_prompts', '-o', type=str, help='Other prompts (optional)')
    parser.add_argument("--max_runs", '-m', type=int, default=10, help='Maximum number of runs (default: 10)')
    parser.add_argument('--benchmark', '-b', type=str, choices=['gradingbench', 'proofbench', 'answerbench'],
                       help='Load problem from benchmark (gradingbench, proofbench, or answerbench)')
    parser.add_argument('--level', type=str,
                       help='Filter benchmark by level. For gradingbench: Basic, Advanced. For proofbench: pre-IMO, IMO-easy, IMO-medium, IMO-hard. Case-insensitive. Not supported for answerbench.')
    parser.add_argument('--benchmark-index', '-i', type=int, default=0,
                       help='Index of problem to load from filtered benchmark (default: 0)')
    parser.add_argument('--memory', '-mem', type=str, help='Path to memory file for saving/loading state (optional)')
    parser.add_argument('--resume', '-r', action='store_true', help='Resume from memory file if provided')
    parser.add_argument('--solution-reasoning', '-sr', type=str, choices=['low', 'medium', 'high'],
                       help='Override solution generation reasoning effort (low/medium/high)')
    parser.add_argument('--self-improvement-reasoning', '-sir', type=str, choices=['low', 'medium', 'high'],
                       help='Override self-improvement reasoning effort (low/medium/high). Use "high" for proactive error detection (recommended).')
    parser.add_argument('--verification-reasoning', '-vr', type=str, choices=['low', 'medium', 'high'],
                       help='Override verification reasoning effort (low/medium/high). Use "high" for rigorous checking.')
    parser.add_argument('--num-initial-attempts', '-nia', type=int, default=1,
                       help='Generate N diverse initial solutions and pick best (default: 1). Use 3-5 for BFS exploration to escape local minima.')
    parser.add_argument('--use-mcts', action='store_true',
                       help='Use MCTS-guided exploration instead of simple BFS')
    parser.add_argument('--mcts-simulations', type=int, default=8,
                       help='Number of MCTS simulations (default: 8, optimized for coverage)')
    parser.add_argument('--mcts-exploration', type=float, default=1.6,
                       help='MCTS exploration constant for UCB1 (default: 1.6, tuned for diversity)')
    parser.add_argument('--best-of-n', type=int, default=0,
                       help='If > 0, verify top N MCTS solutions and return first verified (default: 0=disabled). Recommended: 3-5 for higher success rate.')
    parser.add_argument('--use-proof-sketch', action='store_true',
                       help='Use Proof Sketch architecture: outline → verify structure → expand details → verify math')
    parser.add_argument('--use-translation', action='store_true',
                       help='Enable translation layer for asymmetric reasoning (low gen / high ver)')

    args = parser.parse_args()

    max_runs = args.max_runs
    memory_file = args.memory
    resume_from_memory = args.resume
    solution_reasoning = args.solution_reasoning
    self_improvement_reasoning = args.self_improvement_reasoning
    verification_reasoning = args.verification_reasoning
    num_initial_attempts = args.num_initial_attempts
    use_mcts = args.use_mcts
    mcts_simulations = args.mcts_simulations
    mcts_exploration = args.mcts_exploration
    best_of_n = args.best_of_n
    use_proof_sketch = args.use_proof_sketch

    # Set translation environment variable if flag is provided
    if args.use_translation:
        os.environ["GPT_OSS_USE_TRANSLATION"] = "true"
        print(f">>>>>>> Translation layer ENABLED")
    else:
        os.environ["GPT_OSS_USE_TRANSLATION"] = "false"

    other_prompts = []
    if args.other_prompts:
        other_prompts = args.other_prompts.split(',')

    print(">>>>>>> Other prompts:")
    print(other_prompts)

    if memory_file:
        print(f"Memory file: {memory_file}")
        if resume_from_memory:
            print("Resume mode: Will attempt to load from memory file")

    if solution_reasoning:
        print(f"CLI Override - Solution reasoning effort: {solution_reasoning}")
    if verification_reasoning:
        print(f"CLI Override - Verification reasoning effort: {verification_reasoning}")

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
            elif args.benchmark == 'proofbench':
                entries = loader.load_proofbench(level=args.level)
            else:  # answerbench
                if args.level:
                    print(f">>>>>>> Warning: Level filtering not supported for answerbench, ignoring --level argument")
                entries = loader.load_answerbench()

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
            sol = agent(problem_statement, other_prompts, memory_file, resume_from_memory,
                       solution_reasoning, self_improvement_reasoning, verification_reasoning,
                       num_initial_attempts, use_mcts, mcts_simulations, mcts_exploration, best_of_n,
                       use_proof_sketch)
            if(sol is not None):
                print(f">>>>>>> Found a correct solution in run {i}.")
                print(json.dumps(sol, indent=4))
                break
        except Exception as e:
            print(f">>>>>>> Error in run {i}: {e}")
            continue

    # Close log file if it was opened
    close_log_file()

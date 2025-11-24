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
MODEL_NAME = "openai/gpt-oss-120b"
# Use OpenAI-compatible API endpoint (e.g., sglang)
API_URL = os.getenv("GPT_OSS_API_URL", "http://localhost:30000/v1/chat/completions")

# Asymmetric Reasoning Effort Configuration
# Solution generation: Uses medium reasoning for better quality while maintaining efficiency
SOLUTION_REASONING_EFFORT = os.getenv("GPT_OSS_SOLUTION_REASONING", "medium")
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

# Global variables for verification safeguards
VERIFICATION_TIMEOUT = 600  # 10 minutes default
VERIFICATION_MAX_ATTEMPTS = 3  # Max attempts before fallback
VERIFICATION_SAFEGUARDS_ENABLED = True  # Enable by default to prevent hangs

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

# Request/Response Payload Logging
def log_request_payload(payload, label="API Request"):
    """
    Log the full request payload with a descriptive label.

    Args:
        payload: The request payload dict
        label: Descriptive label for this request (e.g., "Initial prompt", "Verification prompt")
    """
    print(f"\n{'='*80}")
    print(f">>>>>>> [REQUEST] {label}")
    print(f"{'='*80}")
    print(f">>>>>>> Request Payload:")
    print(json.dumps(payload, indent=4, ensure_ascii=False))
    print(f">>>>>>> Payload size: {len(json.dumps(payload))} characters")
    print(f">>>>>>> Message count: {len(payload.get('messages', []))}")
    if 'reasoning' in payload:
        print(f">>>>>>> Reasoning effort: {payload['reasoning'].get('effort', 'not specified')}")
    print(f"{'='*80}\n")

def log_response_payload(response, label="API Response", is_streaming=False):
    """
    Log the full response payload with a descriptive label.

    Args:
        response: The response dict (accumulated for streaming)
        label: Descriptive label for this response
        is_streaming: Whether this was a streaming response
    """
    print(f"\n{'='*80}")
    print(f">>>>>>> [RESPONSE] {label}")
    print(f">>>>>>> Response type: {'Streaming' if is_streaming else 'Non-streaming'}")
    print(f"{'='*80}")

    # Log response metadata
    if 'id' in response:
        print(f">>>>>>> Response ID: {response.get('id', 'N/A')}")
    if 'model' in response:
        print(f">>>>>>> Model: {response.get('model', 'N/A')}")
    if 'usage' in response and response['usage']:
        usage = response['usage']
        print(f">>>>>>> Usage - Prompt tokens: {usage.get('prompt_tokens', 'N/A')}")
        print(f">>>>>>> Usage - Completion tokens: {usage.get('completion_tokens', 'N/A')}")
        print(f">>>>>>> Usage - Total tokens: {usage.get('total_tokens', 'N/A')}")

    # Log finish reason
    if 'choices' in response and len(response['choices']) > 0:
        finish_reason = response['choices'][0].get('finish_reason', 'N/A')
        print(f">>>>>>> Finish reason: {finish_reason}")

        # Log content length
        content = response['choices'][0].get('message', {}).get('content', '')
        print(f">>>>>>> Content length: {len(content)} characters")

    # Log full response structure (truncated for readability)
    print(f">>>>>>> Full Response Payload:")
    response_str = json.dumps(response, indent=4, ensure_ascii=False)
    print(response_str)
    print(f"{'='*80}\n")

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

def send_api_request(api_key, payload, stream=True, request_label="API Request"):
    """
    Sends the request to the OpenAI-compatible API and returns the response.
    Supports streaming for real-time output display.

    Args:
        api_key: API key for authentication
        payload: Request payload dict
        stream: Whether to use streaming (default: True)
        request_label: Descriptive label for logging (e.g., "Initial prompt", "Verification prompt")
    """
    # Log the full request payload
    log_request_payload(payload, label=request_label)

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
            result = _handle_streaming_response(response)
            # Log the full response payload for streaming
            log_response_payload(result, label=f"{request_label} - Response", is_streaming=True)
            return result
        else:
            result = response.json()
            # Log the full response payload for non-streaming
            log_response_payload(result, label=f"{request_label} - Response", is_streaming=False)
            return result
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
    MAX_CONTENT_LENGTH = 50000  # Maximum content length before forcing stop (baseline)

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
    Extracts the solution from the API response.

    Expects unified format with ### markers:
    - ### Summary ###
    - ### Detailed Solution ###

    Returns:
        Solution text from ### Summary ### onwards, or empty string if not found
    """
    if not response_data:
        return ""

    # Pattern 1: Look for ### Summary ### marker (preferred unified format)
    summary_pattern = r'###\s*Summary\s*###'
    summary_match = re.search(summary_pattern, response_data, re.IGNORECASE)

    if summary_match:
        # Extract from ### Summary ### onwards
        start_idx = summary_match.start()
        return response_data[start_idx:].strip()

    # Fallback: Look for just "Summary" keyword (backward compatibility)
    summary_idx = response_data.rfind("Summary")
    if summary_idx == -1:
        return ""

    # Check if "### " appears before Summary
    if summary_idx >= 4 and "### " in response_data[summary_idx - 4:summary_idx]:
        return response_data[summary_idx - 4:].strip()
    else:
        return response_data[summary_idx:].strip()


def validate_solution_structure(solution):
    """
    Validate that solution has required unified format structure.

    Required sections (in order):
    1. ### Summary ### - with Verdict and Method Sketch
    2. ### Detailed Solution ### - with full proof

    Returns:
        Tuple of (is_valid: bool, errors: List[str], sections: Dict)
    """
    errors = []
    sections = {
        'summary': None,
        'detailed_solution': None,
        'has_boxed_answer': False,
        'boxed_answer': None
    }

    if not solution:
        return False, ["Empty solution"], sections

    # Check for ### Summary ### marker
    summary_pattern = r'###\s*Summary\s*###'
    summary_match = re.search(summary_pattern, solution, re.IGNORECASE)
    if not summary_match:
        # Fallback: check for "Summary" without ### markers
        if 'Summary' not in solution and 'summary' not in solution.lower():
            errors.append("Missing '### Summary ###' section marker")

    # Check for ### Detailed Solution ### marker
    detailed_pattern = r'###\s*Detailed\s+Solution\s*###'
    detailed_match = re.search(detailed_pattern, solution, re.IGNORECASE)
    if not detailed_match:
        # Fallback: check for "Detailed Solution" without ### markers
        if 'Detailed Solution' not in solution and 'detailed solution' not in solution.lower():
            errors.append("Missing '### Detailed Solution ###' section marker")
        else:
            # Found without markers - extract it
            idx = solution.lower().find('detailed solution')
            if idx != -1:
                sections['detailed_solution'] = solution[idx:].strip()
    else:
        # Extract detailed solution section
        start = detailed_match.end()
        sections['detailed_solution'] = solution[start:].strip()

        # Update summary to be between Summary and Detailed Solution
        if summary_match and detailed_match.start() > summary_match.end():
            sections['summary'] = solution[summary_match.end():detailed_match.start()].strip()

    # Extract summary if we found the marker but haven't extracted yet
    if summary_match and sections['summary'] is None:
        if detailed_match:
            sections['summary'] = solution[summary_match.end():detailed_match.start()].strip()
        else:
            sections['summary'] = solution[summary_match.end():].strip()

    # Check for boxed answer
    boxed_pattern = r'\\boxed\{([^}]+)\}'
    boxed_match = re.search(boxed_pattern, solution)
    if boxed_match:
        sections['has_boxed_answer'] = True
        sections['boxed_answer'] = boxed_match.group(1).strip()

    is_valid = len(errors) == 0
    return is_valid, errors, sections


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

def verify_solution_safe(problem_statement, solution, verbose=True, reasoning_effort=None,
                         max_attempts=None, timeout_seconds=None, fallback_reasoning="medium"):
    """
    Safely verifies a solution with timeout, retry, and fallback mechanisms.

    Args:
        problem_statement: The original problem
        solution: The solution to verify
        verbose: Print detailed verification steps
        reasoning_effort: Override reasoning effort for verification
        max_attempts: Maximum verification attempts before fallback (default: uses VERIFICATION_MAX_ATTEMPTS global)
        timeout_seconds: Timeout per attempt in seconds (default: uses VERIFICATION_TIMEOUT global)
        fallback_reasoning: Reasoning level to fall back to on repeated failures (default: "medium")

    Returns:
        Tuple of (bug_report, good_verify) or raises exception after all attempts fail
    """
    import time

    # Use global defaults if not specified
    if max_attempts is None:
        max_attempts = VERIFICATION_MAX_ATTEMPTS
    if timeout_seconds is None:
        timeout_seconds = VERIFICATION_TIMEOUT

    # Check if safeguards are disabled
    if not VERIFICATION_SAFEGUARDS_ENABLED:
        if verbose:
            print(f">>>>>>> [VERIFICATION SAFEGUARD] Safeguards disabled, using direct verification")
        return verify_solution(problem_statement, solution, verbose, reasoning_effort)

    current_reasoning = reasoning_effort if reasoning_effort is not None else VERIFICATION_REASONING_EFFORT

    for attempt in range(max_attempts):
        if verbose:
            print(f"\n{'='*80}")
            print(f">>>>>>> [VERIFICATION SAFEGUARD] Attempt {attempt + 1}/{max_attempts}")
            print(f">>>>>>> [VERIFICATION SAFEGUARD] Reasoning: {current_reasoning}")
            print(f">>>>>>> [VERIFICATION SAFEGUARD] Timeout: {timeout_seconds}s")
            print(f"{'='*80}\n")

        try:
            # Set a timeout for this verification attempt
            import signal

            def timeout_handler(signum, frame):
                raise TimeoutError(f"Verification timeout after {timeout_seconds} seconds")

            # Only use signal on Unix systems
            if hasattr(signal, 'SIGALRM'):
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(timeout_seconds)

            try:
                # Attempt verification
                bug_report, good_verify = verify_solution(
                    problem_statement, solution, verbose, current_reasoning
                )

                # Cancel alarm if set
                if hasattr(signal, 'SIGALRM'):
                    signal.alarm(0)

                if verbose:
                    print(f">>>>>>> [VERIFICATION SAFEGUARD] ✓ Attempt {attempt + 1} completed successfully")

                return bug_report, good_verify

            except TimeoutError as e:
                # Cancel alarm
                if hasattr(signal, 'SIGALRM'):
                    signal.alarm(0)

                if verbose:
                    print(f"\n{'='*80}")
                    print(f">>>>>>> [VERIFICATION SAFEGUARD] ⚠️  TIMEOUT on attempt {attempt + 1}")
                    print(f">>>>>>> [VERIFICATION SAFEGUARD] Error: {e}")
                    print(f"{'='*80}\n")

                # Exponential backoff: 2s, 4s, 8s
                if attempt < max_attempts - 1:
                    backoff_time = 2 ** (attempt + 1)
                    if verbose:
                        print(f">>>>>>> [VERIFICATION SAFEGUARD] Waiting {backoff_time}s before retry...")
                    time.sleep(backoff_time)

                    # On last attempt, fall back to lower reasoning
                    if attempt == max_attempts - 2:
                        current_reasoning = fallback_reasoning
                        if verbose:
                            print(f">>>>>>> [VERIFICATION SAFEGUARD] Falling back to {fallback_reasoning} reasoning")
                else:
                    raise

        except Exception as e:
            if verbose:
                print(f"\n{'='*80}")
                print(f">>>>>>> [VERIFICATION SAFEGUARD] ❌ ERROR on attempt {attempt + 1}")
                print(f">>>>>>> [VERIFICATION SAFEGUARD] Error type: {type(e).__name__}")
                print(f">>>>>>> [VERIFICATION SAFEGUARD] Error: {e}")
                print(f"{'='*80}\n")

            # Exponential backoff on errors too
            if attempt < max_attempts - 1:
                backoff_time = 2 ** (attempt + 1)
                if verbose:
                    print(f">>>>>>> [VERIFICATION SAFEGUARD] Waiting {backoff_time}s before retry...")
                time.sleep(backoff_time)

                # On last attempt, fall back to lower reasoning
                if attempt == max_attempts - 2:
                    current_reasoning = fallback_reasoning
                    if verbose:
                        print(f">>>>>>> [VERIFICATION SAFEGUARD] Falling back to {fallback_reasoning} reasoning")
            else:
                # All attempts failed
                if verbose:
                    print(f"\n{'='*80}")
                    print(f">>>>>>> [VERIFICATION SAFEGUARD] ❌ ALL ATTEMPTS FAILED")
                    print(f">>>>>>> [VERIFICATION SAFEGUARD] Returning failure state")
                    print(f"{'='*80}\n")

                # Return a safe failure state instead of raising
                return "VERIFICATION FAILED: All attempts exhausted", "No - verification system failure"

    # Should never reach here, but just in case
    return "VERIFICATION FAILED: Unexpected error", "No - verification system failure"

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

    res = send_api_request(get_api_key(), p2, request_label="Verification prompt")
    out = extract_text_from_response(res)

    if(verbose):
        print(">>>>>>> Verification results:")
        print(json.dumps(out, indent=4))

    check_correctness = """Response in "yes" or "no". Is the following statement saying the solution is complete, correct, and does not contain critical error or a major justification gap?""" \
            + "\n\n" + out
    prompt = build_request_payload(system_prompt="", question_prompt=check_correctness)
    r = send_api_request(get_api_key(), prompt, request_label="Verification correctness check")
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
        response = send_api_request(get_api_key(), payload, stream=True, request_label="Translation layer prompt")
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

    response = send_api_request(get_api_key(), payload, request_label="Proof sketch generation")
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

    response = send_api_request(get_api_key(), payload, request_label="Proof structure verification")
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

    response = send_api_request(get_api_key(), payload, request_label="Proof details expansion")
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

        response = send_api_request(get_api_key(), payload, request_label="Proof structure fix prompt")
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
                solution=None, verify=None, solution_reasoning=None, self_improvement_reasoning=None,
                verification_reasoning=None, iteration_history=None, score_history=None,
                error_patterns=None, failed_approaches=None, best_solution=None, best_score=None):
    """
    Save the current state to a memory file with comprehensive state tracking.

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
        iteration_history: List of iteration data dicts for analysis
        score_history: List of scores for tracking progress
        error_patterns: Dict of detected error patterns for learning
        failed_approaches: List of failed approach summaries to avoid retry
        best_solution: Best solution found so far (may differ from current)
        best_score: Score of the best solution
    """
    # Load existing memory to preserve accumulated history if present
    existing_memory = {}
    if memory_file:
        try:
            import os
            if os.path.exists(memory_file):
                with open(memory_file, 'r', encoding='utf-8') as f:
                    existing_memory = json.load(f)
        except:
            pass  # Start fresh if can't load existing

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
        "timestamp": __import__('datetime').datetime.now().isoformat(),

        # Enhanced state tracking (Tier 1 fix)
        "iteration_history": iteration_history or existing_memory.get("iteration_history", []),
        "score_history": score_history or existing_memory.get("score_history", []),
        "error_patterns": error_patterns or existing_memory.get("error_patterns", {}),
        "failed_approaches": failed_approaches or existing_memory.get("failed_approaches", []),
        "best_solution": best_solution or existing_memory.get("best_solution"),
        "best_score": best_score if best_score is not None else existing_memory.get("best_score"),

        # Metadata for analysis
        "total_iterations_across_resumes": existing_memory.get("total_iterations_across_resumes", 0) + current_iteration,
        "resume_count": existing_memory.get("resume_count", 0) + (1 if existing_memory else 0),
    }

    try:
        with open(memory_file, 'w', encoding='utf-8') as f:
            json.dump(memory, f, indent=2, ensure_ascii=False)
        print(f"Memory saved to {memory_file}")
        return True
    except Exception as e:
        print(f"Error saving memory to {memory_file}: {e}")
        return False


def append_iteration_to_memory(memory_file, iteration_data):
    """
    Append iteration data to memory file without full rewrite.
    Useful for incremental progress tracking.

    Args:
        memory_file: Path to memory file
        iteration_data: Dict containing iteration info (iteration_num, solution_summary,
                       verification_result, score, errors, approach_used, duration)
    """
    try:
        import os
        if not os.path.exists(memory_file):
            # Create new memory with just iteration history
            memory = {"iteration_history": [iteration_data]}
        else:
            with open(memory_file, 'r', encoding='utf-8') as f:
                memory = json.load(f)
            if "iteration_history" not in memory:
                memory["iteration_history"] = []
            memory["iteration_history"].append(iteration_data)

            # Update score history
            if "score_history" not in memory:
                memory["score_history"] = []
            if "score" in iteration_data:
                memory["score_history"].append(iteration_data["score"])

            # Track best solution
            score = iteration_data.get("score", 0)
            if score > memory.get("best_score", 0):
                memory["best_score"] = score
                memory["best_solution"] = iteration_data.get("solution_summary", "")

        with open(memory_file, 'w', encoding='utf-8') as f:
            json.dump(memory, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error appending iteration to memory: {e}")
        return False


def record_failed_approach(memory_file, approach_summary, failure_reason):
    """
    Record a failed approach to avoid retrying the same strategy.

    Args:
        memory_file: Path to memory file
        approach_summary: Short description of the approach tried
        failure_reason: Why it failed (e.g., "verification timeout", "counterexample found")
    """
    try:
        import os
        memory = {}
        if os.path.exists(memory_file):
            with open(memory_file, 'r', encoding='utf-8') as f:
                memory = json.load(f)

        if "failed_approaches" not in memory:
            memory["failed_approaches"] = []

        memory["failed_approaches"].append({
            "approach": approach_summary,
            "reason": failure_reason,
            "timestamp": __import__('datetime').datetime.now().isoformat()
        })

        with open(memory_file, 'w', encoding='utf-8') as f:
            json.dump(memory, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error recording failed approach: {e}")
        return False


def update_error_patterns(memory_file, error_type, count_increment=1):
    """
    Update error pattern tracking for learning.

    Args:
        memory_file: Path to memory file
        error_type: Type of error encountered (e.g., "truncation", "format_error", "timeout")
        count_increment: How much to increment the count
    """
    try:
        import os
        memory = {}
        if os.path.exists(memory_file):
            with open(memory_file, 'r', encoding='utf-8') as f:
                memory = json.load(f)

        if "error_patterns" not in memory:
            memory["error_patterns"] = {}

        memory["error_patterns"][error_type] = memory["error_patterns"].get(error_type, 0) + count_increment

        with open(memory_file, 'w', encoding='utf-8') as f:
            json.dump(memory, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error updating error patterns: {e}")
        return False

def load_memory(memory_file):
    """
    Load the state from a memory file with enhanced state tracking.

    Returns:
        Dictionary containing:
        - problem_statement: The problem being solved
        - other_prompts: Additional prompts
        - current_iteration: Resume point
        - max_runs: Maximum iterations allowed
        - solution: Current solution (if any)
        - verify: Current verification result (if any)
        - solution_reasoning: Reasoning effort for solution generation
        - self_improvement_reasoning: Reasoning effort for self-improvement
        - verification_reasoning: Reasoning effort for verification
        - iteration_history: List of iteration data for analysis (enhanced)
        - score_history: List of scores for tracking progress (enhanced)
        - error_patterns: Dict of detected error patterns (enhanced)
        - failed_approaches: List of failed approach summaries (enhanced)
        - best_solution: Best solution found so far (enhanced)
        - best_score: Score of the best solution (enhanced)
        - total_iterations_across_resumes: Cumulative iteration count
        - resume_count: Number of times resumed
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

        # Log enhanced state info (Tier 1 enhancement)
        if 'resume_count' in memory:
            print(f"Resume count: {memory['resume_count']}")
        if 'total_iterations_across_resumes' in memory:
            print(f"Total iterations across all resumes: {memory['total_iterations_across_resumes']}")
        if 'best_score' in memory and memory['best_score'] is not None:
            print(f"Best score achieved: {memory['best_score']}")
        if 'iteration_history' in memory:
            print(f"Iteration history entries: {len(memory['iteration_history'])}")
        if 'failed_approaches' in memory and memory['failed_approaches']:
            print(f"Failed approaches recorded: {len(memory['failed_approaches'])}")
            for fa in memory['failed_approaches'][-3:]:  # Show last 3
                print(f"  - {fa.get('approach', 'unknown')}: {fa.get('reason', 'unknown')}")
        if 'error_patterns' in memory and memory['error_patterns']:
            print(f"Error patterns: {memory['error_patterns']}")

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
    r = send_api_request(get_api_key(), p1, request_label="Check solution completeness prompt")
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

    response1 = send_api_request(get_api_key(), p1, request_label="Initial solution prompt")
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

    response2 = send_api_request(get_api_key(), p1, request_label="Self-improvement prompt")
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

def extract_answer_from_solution(solution, problem_type=None):
    """
    Extract the mathematical answer from a solution with generalized pattern matching.
    (Tier 3: Answer Validation Generalization)

    Supports multiple answer types:
    - Set membership (k ∈ {0,1,...,n})
    - Equality (x = 5, n = 2^k)
    - Yes/No answers
    - Counting answers (The number is 42)
    - Geometric answers (angle = 60°, point P = (1,2))
    - Algebraic expressions (f(n) = n^2 + 1)
    - Range answers (0 ≤ x ≤ n)

    Args:
        solution: Solution text
        problem_type: Optional hint about problem type (number_theory, geometry, combinatorics, etc.)

    Returns:
        dict: Extracted answer with type information, or None if not found
    """
    if not solution:
        return None

    import re

    # Result structure for richer answer information
    result = {
        'raw': None,
        'type': 'unknown',
        'variable': None,
        'value': None,
        'confidence': 'low'
    }

    # === Pattern 1: Generic variable ∈ {set} ===
    # Matches: k ∈ {0,1,...,n}, x ∈ {1,2,3}, n ∈ ℤ
    match = re.search(r'([a-zA-Z_]\w*)\s*[∈∊∈]\s*\{([^}]+)\}', solution)
    if match:
        result['raw'] = f"{match.group(1)} ∈ {{{match.group(2)}}}"
        result['type'] = 'set_membership'
        result['variable'] = match.group(1)
        result['value'] = match.group(2)
        result['confidence'] = 'high'
        return result

    # === Pattern 2: Generic variable = value ===
    # Matches: k = 5, n = 2^k, x = n/2, angle = 60
    match = re.search(r'([a-zA-Z_]\w*)\s*=\s*([^.\n,;]+?)(?:\.|,|;|$|\n)', solution)
    if match:
        var = match.group(1).strip()
        val = match.group(2).strip()
        # Avoid matching common false positives
        if var.lower() not in ['if', 'then', 'let', 'where', 'such', 'for', 'and', 'or']:
            result['raw'] = f"{var} = {val}"
            result['type'] = 'equality'
            result['variable'] = var
            result['value'] = val
            result['confidence'] = 'medium'
            return result

    # === Pattern 3: Yes/No answer ===
    # Matches: "The answer is yes", "Therefore, no", "Yes, because..."
    yes_no_patterns = [
        r'(?:the\s+)?answer\s+is\s+(yes|no)',
        r'(?:therefore|hence|thus),?\s+(yes|no)',
        r'^(yes|no)[,.\s]',
        r'(yes|no),?\s+(?:because|since|as)'
    ]
    for pattern in yes_no_patterns:
        match = re.search(pattern, solution, re.IGNORECASE | re.MULTILINE)
        if match:
            result['raw'] = match.group(1).lower()
            result['type'] = 'yes_no'
            result['variable'] = None
            result['value'] = match.group(1).lower()
            result['confidence'] = 'high'
            return result

    # === Pattern 4: Counting answer ===
    # Matches: "The number is 42", "There are exactly 100", "The count is n^2"
    count_patterns = [
        r'(?:the\s+)?(?:number|count|total)\s+(?:of\s+\w+\s+)?is\s+(\d+|[a-zA-Z_]\w*(?:\s*[\+\-\*\/\^]\s*[a-zA-Z_\d]+)*)',
        r'there\s+(?:are|exist)\s+(?:exactly\s+)?(\d+)',
        r'(\d+)\s+(?:solutions?|ways?|elements?|configurations?)'
    ]
    for pattern in count_patterns:
        match = re.search(pattern, solution, re.IGNORECASE)
        if match:
            result['raw'] = f"count = {match.group(1)}"
            result['type'] = 'counting'
            result['variable'] = 'count'
            result['value'] = match.group(1)
            result['confidence'] = 'medium'
            return result

    # === Pattern 5: Geometric answer ===
    # Matches: "angle = 60°", "point P = (1, 2)", "length = √2"
    geo_patterns = [
        r'(?:angle|∠)\s*(?:[A-Z]{2,3})?\s*=?\s*(\d+)°?',
        r'point\s+([A-Z])\s*=\s*\(([^)]+)\)',
        r'(?:length|distance|radius)\s*=\s*([^.\n,]+)',
        r'(?:area|perimeter)\s*=\s*([^.\n,]+)'
    ]
    for pattern in geo_patterns:
        match = re.search(pattern, solution, re.IGNORECASE)
        if match:
            if 'angle' in pattern.lower() or '∠' in pattern:
                result['raw'] = f"angle = {match.group(1)}°"
                result['type'] = 'geometric_angle'
                result['value'] = match.group(1)
            elif 'point' in pattern.lower():
                result['raw'] = f"point {match.group(1)} = ({match.group(2)})"
                result['type'] = 'geometric_point'
                result['value'] = match.group(2)
            else:
                result['raw'] = f"{match.group(0)}"
                result['type'] = 'geometric_measure'
                result['value'] = match.group(1)
            result['confidence'] = 'medium'
            return result

    # === Pattern 6: Range/Inequality answer ===
    # Matches: "0 ≤ x ≤ n", "x > 0", "n is at most 100"
    range_patterns = [
        r'(\d+|[a-zA-Z])\s*[≤≥<>]\s*([a-zA-Z_]\w*)\s*[≤≥<>]\s*(\d+|[a-zA-Z_]\w*)',
        r'([a-zA-Z_]\w*)\s*[≤≥<>]\s*(\d+|[a-zA-Z_]\w*)',
        r'([a-zA-Z_]\w*)\s+is\s+at\s+(?:most|least)\s+(\d+|[a-zA-Z_]\w*)'
    ]
    for pattern in range_patterns:
        match = re.search(pattern, solution)
        if match:
            result['raw'] = match.group(0)
            result['type'] = 'range'
            result['value'] = match.group(0)
            result['confidence'] = 'medium'
            return result

    # === Pattern 7: "Answer is" fallback ===
    match = re.search(r'(?:the\s+)?answer\s+is\s*[:\s]*([^.\n]+)', solution, re.IGNORECASE)
    if match:
        result['raw'] = match.group(1).strip()
        result['type'] = 'explicit_answer'
        result['value'] = match.group(1).strip()
        result['confidence'] = 'high'
        return result

    # === Pattern 8: "Therefore" conclusion ===
    match = re.search(r'(?:therefore|hence|thus|so)\s*,?\s*([a-zA-Z_]\w*)\s*=\s*([^.\n]+)', solution, re.IGNORECASE)
    if match:
        result['raw'] = f"{match.group(1)} = {match.group(2).strip()}"
        result['type'] = 'conclusion'
        result['variable'] = match.group(1)
        result['value'] = match.group(2).strip()
        result['confidence'] = 'medium'
        return result

    # === Legacy Pattern for backward compatibility ===
    # Pattern: k ∈ {explicit set} (original IMO-specific pattern)
    match = re.search(r'k\s*[∈∊∈]\s*\{([^}]+)\}', solution)
    if match:
        return {
            'raw': f"k ∈ {{{match.group(1)}}}",
            'type': 'set_membership',
            'variable': 'k',
            'value': match.group(1),
            'confidence': 'high'
        }

    return None


def extract_answer_simple(solution):
    """
    Simple string extraction for backward compatibility.
    Returns just the raw answer string, not the full dict.
    """
    result = extract_answer_from_solution(solution)
    if result:
        return result.get('raw')
    return None

def validate_answer_change(prev_solution, new_solution, iteration, verbose=True):
    """
    Validate that answer changes are not regressions (narrowing without justification).
    (Tier 3: Generalized Answer Validation)

    Supports validation for multiple answer types:
    - Set narrowing detection
    - Numerical value changes
    - Yes/No flip detection
    - Range restriction detection
    - Geometric value changes

    Args:
        prev_solution: Previous solution text
        new_solution: New solution text
        iteration: Current iteration number
        verbose: Print validation warnings

    Returns:
        dict: Validation result with warning flags and detailed change info
    """
    prev_answer = extract_answer_from_solution(prev_solution)
    new_answer = extract_answer_from_solution(new_solution)

    result = {
        'prev_answer': prev_answer,
        'new_answer': new_answer,
        'changed': False,
        'narrowed': False,
        'flipped': False,  # For yes/no changes
        'regression_risk': 'none',  # none, low, medium, high
        'warning': None,
        'change_type': None
    }

    # Handle case where answers couldn't be extracted
    if not prev_answer or not new_answer:
        return result

    # Get raw answers for comparison
    prev_raw = prev_answer.get('raw', str(prev_answer)) if isinstance(prev_answer, dict) else str(prev_answer)
    new_raw = new_answer.get('raw', str(new_answer)) if isinstance(new_answer, dict) else str(new_answer)

    if prev_raw == new_raw:
        return result

    result['changed'] = True

    if verbose:
        print(f"\n{'='*80}")
        print(f">>>>>>> [ANSWER VALIDATION] Answer change detected at iteration {iteration}")
        print(f">>>>>>> [ANSWER VALIDATION] Previous: {prev_raw}")
        print(f">>>>>>> [ANSWER VALIDATION] New:      {new_raw}")
        if isinstance(prev_answer, dict) and isinstance(new_answer, dict):
            print(f">>>>>>> [ANSWER VALIDATION] Type change: {prev_answer.get('type', '?')} → {new_answer.get('type', '?')}")

    import re

    # === Type-specific validation ===

    # 1. Yes/No flip detection (high risk)
    if isinstance(prev_answer, dict) and isinstance(new_answer, dict):
        if prev_answer.get('type') == 'yes_no' and new_answer.get('type') == 'yes_no':
            if prev_answer.get('value') != new_answer.get('value'):
                result['flipped'] = True
                result['regression_risk'] = 'high'
                result['warning'] = f"Yes/No answer flipped from {prev_answer.get('value')} to {new_answer.get('value')}"
                result['change_type'] = 'yes_no_flip'

                if verbose:
                    print(f">>>>>>> [ANSWER VALIDATION] ⚠️  CRITICAL: Yes/No answer FLIPPED!")
                    print(f">>>>>>> [ANSWER VALIDATION] ⚠️  This is a fundamental change requiring strong justification")

    # 2. Set narrowing detection
    if '{' in prev_raw and '{' in new_raw:
        prev_match = re.search(r'\{([^}]+)\}', prev_raw)
        new_match = re.search(r'\{([^}]+)\}', new_raw)

        if prev_match and new_match:
            prev_set_str = prev_match.group(1)
            new_set_str = new_match.group(1)

            # Check for range narrowing: {0,...,n} → {0,...,⌊n/2⌋}
            if '...' in prev_set_str and '...' in new_set_str:
                prev_upper = re.search(r'\.\.\.\s*,?\s*([^}]+)', prev_set_str)
                new_upper = re.search(r'\.\.\.\s*,?\s*([^}]+)', new_set_str)

                if prev_upper and new_upper:
                    prev_bound = prev_upper.group(1).strip()
                    new_bound = new_upper.group(1).strip()

                    # Detect restrictive changes
                    if len(new_bound) > len(prev_bound) or '/' in new_bound or '⌊' in new_bound or '⌈' in new_bound:
                        result['narrowed'] = True
                        result['regression_risk'] = 'high'
                        result['warning'] = f"Answer space narrowed from upper bound {prev_bound} to {new_bound}"
                        result['change_type'] = 'set_narrowing'

                        if verbose:
                            print(f">>>>>>> [ANSWER VALIDATION] ⚠️  WARNING: Answer space NARROWED!")
                            print(f">>>>>>> [ANSWER VALIDATION] ⚠️  From upper bound: {prev_bound}")
                            print(f">>>>>>> [ANSWER VALIDATION] ⚠️  To upper bound:   {new_bound}")
                            print(f">>>>>>> [ANSWER VALIDATION] ⚠️  This requires STRONG justification")

            # Check for range to specific values: {0,...,n} → {0,1,2}
            elif '...' in prev_set_str and '...' not in new_set_str:
                result['narrowed'] = True
                result['regression_risk'] = 'medium'
                result['warning'] = "Changed from range to specific values"
                result['change_type'] = 'range_to_specific'

                if verbose:
                    print(f">>>>>>> [ANSWER VALIDATION] ⚠️  WARNING: Changed from range to specific values")
                    print(f">>>>>>> [ANSWER VALIDATION] ⚠️  Verify this restriction is proven")

    # 3. Numerical value change detection
    if isinstance(prev_answer, dict) and isinstance(new_answer, dict):
        prev_val = prev_answer.get('value', '')
        new_val = new_answer.get('value', '')

        # Try to parse as numbers
        try:
            prev_num = float(prev_val) if prev_val.replace('.', '').replace('-', '').isdigit() else None
            new_num = float(new_val) if new_val.replace('.', '').replace('-', '').isdigit() else None

            if prev_num is not None and new_num is not None and prev_num != new_num:
                result['change_type'] = 'numerical_change'
                result['regression_risk'] = 'medium'
                result['warning'] = f"Numerical value changed from {prev_num} to {new_num}"

                if verbose:
                    print(f">>>>>>> [ANSWER VALIDATION] ⚠️  Numerical value changed!")
                    print(f">>>>>>> [ANSWER VALIDATION] ⚠️  From: {prev_num}")
                    print(f">>>>>>> [ANSWER VALIDATION] ⚠️  To:   {new_num}")
        except (ValueError, AttributeError):
            pass

    # 4. Variable change detection
    if isinstance(prev_answer, dict) and isinstance(new_answer, dict):
        prev_var = prev_answer.get('variable')
        new_var = new_answer.get('variable')

        if prev_var and new_var and prev_var != new_var:
            result['regression_risk'] = 'low'
            result['warning'] = f"Answer variable changed from {prev_var} to {new_var}"
            result['change_type'] = 'variable_change'

            if verbose:
                print(f">>>>>>> [ANSWER VALIDATION] ℹ️  Answer variable changed: {prev_var} → {new_var}")

    # Summary
    if verbose:
        risk_emoji = {'none': '✓', 'low': 'ℹ️', 'medium': '⚠️', 'high': '❌'}
        print(f">>>>>>> [ANSWER VALIDATION] Regression risk: {result['regression_risk']} {risk_emoji.get(result['regression_risk'], '')}")
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

    # Stuck if: all recent corrects are 0 AND errors are not decreasing over consecutive iterations
    all_zero_corrects = all(c == 0 for c in recent_corrects)

    # Bug fix: Compare consecutive errors instead of comparing all to first error
    # This properly detects monotonic non-decrease: each error >= previous error
    errors_not_decreasing = all(
        recent_errors[i] >= recent_errors[i-1]
        for i in range(1, len(recent_errors))
    ) if len(recent_errors) > 1 else True

    # Additional check: Errors staying consistently high (above threshold)
    # This catches cases where errors oscillate but never truly decrease
    avg_errors = sum(recent_errors) / len(recent_errors) if recent_errors else 0
    errors_consistently_high = all(e >= avg_errors * 0.8 for e in recent_errors) and avg_errors > 0

    if all_zero_corrects and (errors_not_decreasing or errors_consistently_high):
        if verbose:
            print(f"\n{'='*80}")
            print(f">>>>>>> [STUCK DETECTION] Stuck pattern detected at iteration {current_iteration}")
            print(f">>>>>>> [STUCK DETECTION] Last {threshold} iterations:")
            for i, (c, e) in enumerate(zip(recent_corrects, recent_errors)):
                iter_num = current_iteration - threshold + i + 1
                print(f">>>>>>> [STUCK DETECTION]   Iteration {iter_num}: {c} corrects, {e} errors")
            print(f">>>>>>> [STUCK DETECTION] Detection reasons:")
            print(f">>>>>>> [STUCK DETECTION]   - Zero corrects: {all_zero_corrects}")
            print(f">>>>>>> [STUCK DETECTION]   - Errors not decreasing (consecutive): {errors_not_decreasing}")
            print(f">>>>>>> [STUCK DETECTION]   - Errors consistently high (avg={avg_errors:.1f}): {errors_consistently_high}")
            print(f">>>>>>> [STUCK DETECTION] ⚠️  No improvement in {threshold} iterations")
            print(f">>>>>>> [STUCK DETECTION] ⚠️  Recommendation: Stop or escalate reasoning effort")
            print(f"{'='*80}\n")

        return True

    return False

# ==============================================================================
# RLAC (ADVERSARIAL CRITIC) IMPLEMENTATION
# ==============================================================================

def validate_solution_quality(solution, min_length=500, verbose=True):
    """
    Validate that a solution has substantive content before RLAC refinement.

    Args:
        solution: Solution text to validate
        min_length: Minimum acceptable length (chars)
        verbose: Enable logging

    Returns:
        Tuple of (is_valid, reason)
    """
    if solution is None:
        return False, "Solution is None"

    if len(solution) < min_length:
        return False, f"Solution too short ({len(solution)} < {min_length} chars)"

    # Check for required structure markers
    required_markers = ['Summary', 'Solution']
    found_markers = sum(1 for marker in required_markers if marker.lower() in solution.lower())
    if found_markers == 0:
        return False, "Solution missing required structure (no Summary or Solution section)"

    # Check for substantive mathematical content
    math_indicators = ['$', '\\', 'proof', 'therefore', 'hence', 'thus', 'let', 'assume']
    math_count = sum(1 for indicator in math_indicators if indicator.lower() in solution.lower())
    if math_count < 3:
        return False, f"Solution lacks mathematical content (only {math_count} math indicators)"

    # Check it's not just a summary/answer
    if len(solution) < 1000 and 'boxed' in solution.lower() and 'proof' not in solution.lower():
        return False, "Solution appears to be answer-only without proof"

    if verbose:
        print(f">>>>>>> [VALIDATION] Solution passed quality check ({len(solution)} chars, {found_markers} structure markers, {math_count} math indicators)")

    return True, "Valid"


def extract_answer_key(solution):
    """
    Extract a normalized answer key from solution for stability tracking.

    Args:
        solution: Solution text

    Returns:
        Normalized answer string for comparison
    """
    if not solution:
        return ""

    # Look for boxed answer first
    import re
    boxed_match = re.search(r'\\boxed\{([^}]+)\}', solution)
    if boxed_match:
        return boxed_match.group(1).strip()

    # Look for "answer is" pattern
    answer_match = re.search(r'(?:answer|result|conclude)\s+(?:is|:)\s*(.+?)(?:\.|$)', solution, re.IGNORECASE)
    if answer_match:
        return answer_match.group(1).strip()[:100]  # Limit length

    return ""


def rlac_agent(problem_statement, other_prompts=[], sol_reasoning="low",
               self_imp_reasoning="high", ver_reasoning="high",
               max_adversarial_rounds=12, consecutive_robust_threshold=3,
               stuck_threshold=2, memory_file=None, verbose=True,
               defense_first=True, max_regeneration_attempts=2,
               use_constructive_mode=True):
    """
    Main RLAC (Reinforcement Learning with Adversarial Critics) agent.

    This implements a Generator-Critic adversarial loop where:
    - Generator creates/refines solutions (using existing agent logic)
    - Adversarial Critic actively tries to break solutions with counterexamples
    - Iterative refinement continues until solution is robust or stuck

    Key differences from standard verification:
    - Critic is ADVERSARIAL (tries to break) not cooperative (tries to verify)
    - Provides concrete counterexamples not abstract feedback
    - Progressive attack intensity (curriculum learning)
    - Structured penalty/reward signals

    NEW IMPROVEMENTS:
    - Initial solution validation gate (don't enter loop with invalid solution)
    - Best solution tracking (preserve progress)
    - Answer stability constraints (detect oscillation)
    - Constructive guidance mode (help find valid solutions)
    - Regeneration fallback (fresh start when stuck)

    Args:
        problem_statement: Mathematical problem to solve
        other_prompts: Additional context prompts
        sol_reasoning: Reasoning effort for solution generation (default: "low")
        self_imp_reasoning: Reasoning effort for self-improvement (default: "high")
        ver_reasoning: Reasoning effort for adversarial attacks (default: "high")
        max_adversarial_rounds: Maximum RLAC rounds (default: 12)
        consecutive_robust_threshold: Consecutive robust verdicts needed for success (default: 3)
        stuck_threshold: Consecutive failed fixes before declaring stuck (default: 2)
        memory_file: Path to save RLAC state and attack history
        verbose: Enable detailed logging
        defense_first: If True, use defense-first mode for proactive attack anticipation (default: True)
        max_regeneration_attempts: Maximum fresh regeneration attempts when severely broken (default: 2)
        use_constructive_mode: Use constructive critic mode after repeated failures (default: True)

    Returns:
        Solution string if successful, None if failed
    """
    print("="*80)
    print(">>>>>>> ADVERSARIAL RLAC MODE ACTIVATED")
    print(">>>>>>> Generator-Critic Adversarial Refinement Loop")
    print("="*80)
    print(f">>>>>>> [RLAC CONFIG] Max rounds: {max_adversarial_rounds}")
    print(f">>>>>>> [RLAC CONFIG] Consecutive robust threshold: {consecutive_robust_threshold}")
    print(f">>>>>>> [RLAC CONFIG] Stuck threshold: {stuck_threshold}")
    print(f">>>>>>> [RLAC CONFIG] Generator reasoning: {sol_reasoning}")
    print(f">>>>>>> [RLAC CONFIG] Critic reasoning: {ver_reasoning}")
    print(f">>>>>>> [RLAC CONFIG] Self-improvement reasoning: {self_imp_reasoning}")
    print(f">>>>>>> [RLAC CONFIG] Defense-first mode: {defense_first}")
    print(f">>>>>>> [RLAC CONFIG] Max regeneration attempts: {max_regeneration_attempts}")
    print(f">>>>>>> [RLAC CONFIG] Constructive mode: {use_constructive_mode}")
    print("="*80 + "\n")

    # Import adversarial critic
    try:
        from adversarial_critic import AdversarialCritic
        from adversarial_prompts import (
            adversarial_defense_prompt,
            constructive_defense_prompt,
            solution_regeneration_prompt,
            approach_diversification_prompt,
            answer_reconsideration_prompt,  # P5 FIX: Answer reconsideration for B-B-B-B failures
            answer_reconsideration_with_verification_prompt,  # P5.1 FIX: Enhanced with mandatory verification
            defense_first_revision_prompt   # P5 FIX: Enhanced revision prompt with answer checkpoint
        )
    except ImportError as e:
        print(f">>>>>>> [RLAC ERROR] Could not import adversarial modules: {e}")
        print(f">>>>>>> [RLAC ERROR] Falling back to standard agent")
        return None

    # Initialize adversarial critic
    critic = AdversarialCritic(
        reasoning_effort=ver_reasoning,
        verbose=verbose
    )

    # Create enhanced session with counter-proposal improvements
    enhanced_session = critic.create_enhanced_session()
    print(f">>>>>>> [RLAC CONFIG] Enhanced session created with counter-proposal improvements")

    # Track failed approaches for diversification
    failed_approach_summaries = []

    # Best solution tracking
    best_solution = None
    best_solution_score = -float('inf')
    best_solution_round = -1

    # Answer stability tracking
    answer_history = []
    answer_oscillation_count = 0

    # P2 FIX: Answer lock mechanism - lock answer after near-success
    answer_locked = False
    locked_answer = None
    lock_threshold = 2  # Lock after this many consecutive ROBUST

    # P3 FIX: Truncation detection threshold
    min_valid_attack_length = 500  # Minimum chars for valid critic response

    # Failed approaches tracking (for regeneration)
    failed_approaches = []

    # Regeneration counter
    regeneration_attempts = 0

    # Phase 1: Generate initial solution
    print("\n" + "="*80)
    print(">>>>>>> [RLAC PHASE 1] Initial Solution Generation")
    if defense_first:
        print(">>>>>>> [RLAC PHASE 1] Defense-first mode: Generator will anticipate attacks")
    print("="*80 + "\n")

    # Add defense-first prompt to initial solution generation
    initial_prompts = other_prompts.copy() if other_prompts else []
    if defense_first:
        # Add defense-first prompt to make generator anticipate attacks
        defense_first_prompt = critic.get_defense_first_prompt()
        initial_prompts.append(defense_first_prompt)

    # Initial solution generation with validation and regeneration
    solution = None
    p1 = None

    while regeneration_attempts <= max_regeneration_attempts:
        try:
            # Build prompts for this attempt
            current_prompts = initial_prompts.copy()

            # Add regeneration prompt if not first attempt
            if regeneration_attempts > 0 and failed_approaches:
                print(f"\n>>>>>>> [RLAC PHASE 1] Regeneration attempt {regeneration_attempts}/{max_regeneration_attempts}")
                regen_prompt = solution_regeneration_prompt.format(
                    failed_approaches="\n".join(f"- {fa}" for fa in failed_approaches[-3:]),
                    problem_requirements="See problem statement above"
                )
                current_prompts.append(regen_prompt)

            p1, solution, verify, good_verify = init_explorations(
                problem_statement, verbose, current_prompts,
                sol_reasoning, self_imp_reasoning, ver_reasoning
            )

            if solution is None:
                print(">>>>>>> [RLAC PHASE 1] Failed to generate initial solution")
                regeneration_attempts += 1
                failed_approaches.append("Generation returned None")
                continue

            print(f">>>>>>> [RLAC PHASE 1] Initial solution generated ({len(solution)} chars)")

            # VALIDATION GATE: Check solution quality before proceeding
            is_valid, validation_reason = validate_solution_quality(solution, min_length=500, verbose=verbose)

            if not is_valid:
                print(f"\n{'='*80}")
                print(f">>>>>>> [RLAC VALIDATION] FAILED: {validation_reason}")
                print(f">>>>>>> [RLAC VALIDATION] Solution does not meet quality threshold")
                print(f"{'='*80}\n")

                failed_approaches.append(f"Validation failed: {validation_reason}")
                regeneration_attempts += 1

                if regeneration_attempts <= max_regeneration_attempts:
                    print(f">>>>>>> [RLAC VALIDATION] Attempting regeneration ({regeneration_attempts}/{max_regeneration_attempts})")
                    continue
                else:
                    print(f">>>>>>> [RLAC VALIDATION] Max regeneration attempts reached")
                    print(f">>>>>>> [RLAC VALIDATION] Proceeding with best available solution")
                    break
            else:
                print(f"\n{'='*80}")
                print(f">>>>>>> [RLAC VALIDATION] PASSED: Solution meets quality threshold")
                print(f"{'='*80}\n")
                break

        except Exception as e:
            print(f">>>>>>> [RLAC PHASE 1] Error generating initial solution: {e}")
            regeneration_attempts += 1
            failed_approaches.append(f"Exception: {str(e)[:100]}")
            if regeneration_attempts > max_regeneration_attempts:
                return None

    if solution is None:
        print(">>>>>>> [RLAC PHASE 1] Could not generate valid initial solution after all attempts")
        return None

    # Initialize best solution tracking
    best_solution = solution
    best_solution_score = 0 if "yes" in good_verify.lower() else -10
    best_solution_round = 0
    print(f">>>>>>> [RLAC TRACKING] Initial best solution score: {best_solution_score}")

    # Track initial answer for stability monitoring using enhanced session's LaTeX parser
    initial_answer_result = enhanced_session.extract_answer(solution)
    initial_answer = initial_answer_result.normalized if initial_answer_result.success else extract_answer_key(solution)
    answer_history.append(initial_answer)
    if initial_answer_result.success:
        print(f">>>>>>> [RLAC TRACKING] Initial answer (enhanced parser): {initial_answer[:50]}... (depth: {initial_answer_result.parse_depth})")
    elif initial_answer:
        print(f">>>>>>> [RLAC TRACKING] Initial answer key (fallback): {initial_answer[:50]}...")
    else:
        print(f">>>>>>> [RLAC TRACKING] No answer key extracted")

    # Phase 2: Adversarial refinement loop
    print("\n" + "="*80)
    print(">>>>>>> [RLAC PHASE 2] Adversarial Refinement Loop")
    print("="*80 + "\n")

    consecutive_robust = 0
    stuck_count = 0
    previous_solution = solution
    rlac_history = []
    consecutive_broken = 0  # Track consecutive BROKEN verdicts for constructive mode

    # P0-v2 FIX: Track total ROBUST count and verdict history for better protection
    total_robust_count = 0
    verdict_history = []

    # P4 FIX: Oscillation detection variables
    oscillation_detected = False
    oscillation_handled = False

    # P5-P8 FIX: Answer reconsideration for B-B-B-B failures
    # P5: Trigger reconsideration after consecutive BROKEN verdicts
    answer_reconsideration_threshold = 4  # After 4 consecutive BROKEN, trigger reconsideration
    answer_reconsideration_triggered = False

    # P6: Evidence accumulation - collect counterexamples across rounds
    accumulated_counterexamples = []  # (round_num, counterexample) tuples
    max_accumulated_evidence = 8  # Keep last 8 counterexamples

    # P7: Answer change detection - track if answer changes
    previous_answer_extract = None  # Extract of answer from solution
    answer_unchanged_after_reconsideration = 0  # Count of unchanged answers after reconsideration

    # P8: Fresh start threshold - after reconsideration fails
    fresh_start_threshold = 6  # After 6 consecutive BROKEN with same answer, fresh start
    fresh_start_triggered = False

    # P5.1 FIX: Enhanced reconsideration with mandatory verification
    p51_verification_threshold = 6  # After 6 consecutive BROKEN, use enhanced verification prompt
    p51_verification_triggered = False

    # P9 FIX: Semantic answer change detection
    # Track the mathematical MEANING of answers, not just text
    def extract_semantic_fingerprint(sol):
        """
        Extract semantic fingerprint of answer for meaningful change detection.
        Returns dict with key mathematical elements that define the answer's meaning.
        """
        if not sol:
            return {'raw': '', 'set_bounds': [], 'formulas': [], 'key_values': []}

        sol_lower = sol.lower()
        fingerprint = {
            'raw': '',
            'set_bounds': [],  # e.g., ['k <= n', 'k >= 0']
            'formulas': [],    # e.g., ['k = n-1', 'k ∈ {0,1,...,n}']
            'key_values': [],  # e.g., ['n=3', 'k=2']
            'impossible': [],  # e.g., ['k=n impossible']
            'possible': []     # e.g., ['k=0 possible']
        }

        # Extract set notation patterns
        set_patterns = [
            r'k\s*[∈∊]\s*\{([^}]+)\}',  # k ∈ {0, 1, ..., n}
            r'k\s*=\s*\{([^}]+)\}',      # k = {0, 1, ..., n}
            r'answer[:\s]+\{([^}]+)\}',  # answer: {0, 1, ..., n}
        ]
        for pattern in set_patterns:
            matches = re.findall(pattern, sol_lower)
            fingerprint['formulas'].extend(matches)

        # Extract bound patterns
        bound_patterns = [
            r'k\s*[≤<]\s*([^\s,\.\n]+)',   # k ≤ n-1
            r'k\s*[≥>]\s*([^\s,\.\n]+)',   # k ≥ 0
            r'0\s*[≤<]\s*k\s*[≤<]\s*([^\s,\.\n]+)',  # 0 ≤ k ≤ n
        ]
        for pattern in bound_patterns:
            matches = re.findall(pattern, sol_lower)
            fingerprint['set_bounds'].extend(matches)

        # Extract impossibility claims
        impossible_patterns = [
            r'k\s*=\s*(\d+|n)[^\w]*(?:is\s+)?impossible',
            r'(\d+|n)\s+(?:is\s+)?impossible',
            r'cannot\s+(?:have\s+)?k\s*=\s*(\d+|n)',
        ]
        for pattern in impossible_patterns:
            matches = re.findall(pattern, sol_lower)
            fingerprint['impossible'].extend(matches)

        # Extract possibility claims
        possible_patterns = [
            r'k\s*=\s*(\d+|n)[^\w]*(?:is\s+)?possible',
            r'(\d+|n)\s+(?:is\s+)?(?:achievable|valid|possible)',
        ]
        for pattern in possible_patterns:
            matches = re.findall(pattern, sol_lower)
            fingerprint['possible'].extend(matches)

        # Create normalized raw answer (last 100 chars of answer section)
        answer_match = re.search(r'(?:answer|conclusion)[:\s]+([^\n]{10,200})', sol_lower)
        if answer_match:
            fingerprint['raw'] = answer_match.group(1).strip()[:100]

        return fingerprint

    def semantic_similarity(fp1, fp2):
        """
        Compare two semantic fingerprints and return similarity score (0-1).
        Returns 1.0 if semantically identical, 0.0 if completely different.
        """
        if not fp1 or not fp2:
            return 0.0

        score = 0.0
        total_weight = 0.0

        # Compare formulas (high weight)
        if fp1.get('formulas') or fp2.get('formulas'):
            total_weight += 3.0
            f1 = set(str(f).strip() for f in fp1.get('formulas', []))
            f2 = set(str(f).strip() for f in fp2.get('formulas', []))
            if f1 and f2:
                overlap = len(f1 & f2) / max(len(f1 | f2), 1)
                score += 3.0 * overlap

        # Compare bounds (high weight)
        if fp1.get('set_bounds') or fp2.get('set_bounds'):
            total_weight += 2.0
            b1 = set(str(b).strip() for b in fp1.get('set_bounds', []))
            b2 = set(str(b).strip() for b in fp2.get('set_bounds', []))
            if b1 and b2:
                overlap = len(b1 & b2) / max(len(b1 | b2), 1)
                score += 2.0 * overlap

        # Compare impossibility claims (medium weight)
        if fp1.get('impossible') or fp2.get('impossible'):
            total_weight += 1.5
            i1 = set(str(i).strip() for i in fp1.get('impossible', []))
            i2 = set(str(i).strip() for i in fp2.get('impossible', []))
            if i1 and i2:
                overlap = len(i1 & i2) / max(len(i1 | i2), 1)
                score += 1.5 * overlap

        # Compare possibility claims (medium weight)
        if fp1.get('possible') or fp2.get('possible'):
            total_weight += 1.5
            p1 = set(str(p).strip() for p in fp1.get('possible', []))
            p2 = set(str(p).strip() for p in fp2.get('possible', []))
            if p1 and p2:
                overlap = len(p1 & p2) / max(len(p1 | p2), 1)
                score += 1.5 * overlap

        # Fallback to raw text similarity if no semantic features found
        if total_weight == 0:
            total_weight = 1.0
            from difflib import SequenceMatcher
            raw1 = fp1.get('raw', '')
            raw2 = fp2.get('raw', '')
            if raw1 and raw2:
                score = SequenceMatcher(None, raw1, raw2).ratio()

        return score / total_weight if total_weight > 0 else 0.0

    previous_semantic_fingerprint = None
    semantic_unchanged_count = 0  # P9: Track semantically unchanged answers

    for round_num in range(max_adversarial_rounds):
        print(f"\n{'='*80}")
        print(f">>>>>>> [RLAC ROUND {round_num + 1}/{max_adversarial_rounds}]")
        print(f">>>>>>> [RLAC METRICS] Consecutive robust: {consecutive_robust}/{consecutive_robust_threshold}")
        print(f">>>>>>> [RLAC METRICS] Stuck count: {stuck_count}/{stuck_threshold}")
        print(f"{'='*80}\n")

        # Critic attacks solution
        print(f">>>>>>> [RLAC CRITIC] Launching adversarial attack...")

        try:
            attack_result = critic.attack_solution(
                problem_statement=problem_statement,
                solution=solution,
                round_num=round_num,
                max_rounds=max_adversarial_rounds,
                api_request_func=send_api_request,
                api_key=get_api_key()
            )

            verdict = attack_result['verdict']
            counterexamples = attack_result['counterexamples']
            total_penalty = attack_result['total_penalty']

            # P3 FIX: Truncation detection - check if attack response was truncated
            attack_text = attack_result.get('full_attack', '')
            attack_length = len(attack_text) if attack_text else 0
            if attack_length < min_valid_attack_length and verdict == "BROKEN":
                print(f"\n>>>>>>> [RLAC TRUNCATION] WARNING: Attack response suspiciously short ({attack_length} chars)")
                print(f">>>>>>> [RLAC TRUNCATION] Minimum expected: {min_valid_attack_length} chars")
                if len(counterexamples) == 0 or (counterexamples and len(counterexamples[0]) < 100):
                    print(f">>>>>>> [RLAC TRUNCATION] Counterexample appears incomplete/truncated")
                    print(f">>>>>>> [RLAC TRUNCATION] Downgrading verdict from BROKEN to SUSPICIOUS")
                    verdict = "SUSPICIOUS"
                    attack_result['verdict'] = "SUSPICIOUS"
                    attack_result['truncation_detected'] = True

            # P4 FIX: Oscillation detection BEFORE processing verdict
            # Record verdict in history for pattern detection
            verdict_history.append(verdict)

            # Detect oscillation pattern (need at least 4 verdicts)
            if len(verdict_history) >= 4 and not oscillation_handled:
                recent_verdicts = verdict_history[-6:] if len(verdict_history) >= 6 else verdict_history[-4:]

                # Convert to binary: ROBUST=1, others=0
                binary_verdicts = [1 if v == "ROBUST" else 0 for v in recent_verdicts]

                # Check for strict alternation (1-0-1-0 or 0-1-0-1)
                is_alternating = True
                for i in range(1, len(binary_verdicts)):
                    if binary_verdicts[i] == binary_verdicts[i-1]:
                        is_alternating = False
                        break

                # Check for near-alternation (>= 70% transitions)
                transitions = sum(1 for i in range(1, len(binary_verdicts)) if binary_verdicts[i] != binary_verdicts[i-1])
                transition_ratio = transitions / (len(binary_verdicts) - 1) if len(binary_verdicts) > 1 else 0

                if is_alternating or transition_ratio >= 0.7:
                    oscillation_detected = True
                    pattern_type = "strict" if is_alternating else "near"

                    print(f"\n{'='*80}")
                    print(f">>>>>>> [RLAC P4] OSCILLATION DETECTED!")
                    print(f">>>>>>> [RLAC P4] Pattern: {pattern_type} alternation")
                    print(f">>>>>>> [RLAC P4] Recent verdicts: {recent_verdicts}")
                    print(f">>>>>>> [RLAC P4] Total ROBUST so far: {total_robust_count}")
                    print(f"{'='*80}\n")

                    # P4 Strategy: If we've had multiple ROBUSTs and are oscillating,
                    # accept the current ROBUST if this verdict is ROBUST
                    if verdict == "ROBUST" and total_robust_count >= 2:
                        print(f">>>>>>> [RLAC P4] Oscillation with ROBUST history - boosting confidence")
                        print(f">>>>>>> [RLAC P4] Setting consecutive_robust to threshold-1 for faster convergence")
                        consecutive_robust = max(consecutive_robust, consecutive_robust_threshold - 1)
                        oscillation_handled = True

                    # If verdict is BROKEN but we have good ROBUST history, use high-reasoning tiebreaker
                    elif verdict == "BROKEN" and total_robust_count >= 3 and not oscillation_handled:
                        print(f">>>>>>> [RLAC P4] BROKEN verdict but strong ROBUST history ({total_robust_count})")
                        print(f">>>>>>> [RLAC P4] Treating as SUSPICIOUS instead of BROKEN")
                        verdict = "SUSPICIOUS"
                        attack_result['verdict'] = "SUSPICIOUS"
                        attack_result['p4_oscillation_override'] = True

            # Log round metrics
            rlac_round_data = {
                'round': round_num + 1,
                'verdict': verdict,
                'counterexamples': len(counterexamples),
                'penalty': total_penalty,
                'solution_length': len(solution),
                'consecutive_robust': consecutive_robust,
                'stuck_count': stuck_count,
                'total_robust': total_robust_count,
                'oscillation_detected': oscillation_detected
            }
            rlac_history.append(rlac_round_data)

            print(f"\n>>>>>>> [RLAC CRITIC] Attack complete")
            print(f">>>>>>> [RLAC RESULT] Verdict: {verdict}")
            print(f">>>>>>> [RLAC RESULT] Penalty: -{total_penalty} points")
            print(f">>>>>>> [RLAC RESULT] Total ROBUST history: {total_robust_count}")

        except Exception as e:
            print(f">>>>>>> [RLAC CRITIC] Error during attack: {e}")
            print(f">>>>>>> [RLAC CRITIC] Skipping this round")
            continue

        # Handle verdict
        if verdict == "ROBUST":
            consecutive_robust += 1
            total_robust_count += 1  # P0-v2: Track total ROBUST count
            consecutive_broken = 0  # Reset broken counter
            stuck_count = 0  # Reset stuck counter on progress

            # Update best solution - ROBUST is best possible
            current_score = 100 - total_penalty  # High base score for ROBUST
            if current_score > best_solution_score:
                best_solution = solution
                best_solution_score = current_score
                best_solution_round = round_num
                print(f">>>>>>> [RLAC TRACKING] New best solution found (ROBUST, score: {current_score})")

            # P2 FIX: Answer lock mechanism - lock answer after near-success
            if consecutive_robust >= lock_threshold and not answer_locked:
                current_answer_result = enhanced_session.extract_answer(solution)
                if current_answer_result.success:
                    locked_answer = current_answer_result.normalized
                    answer_locked = True
                    print(f"\n>>>>>>> [RLAC LOCK] Answer locked after {consecutive_robust} consecutive ROBUST")
                    print(f">>>>>>> [RLAC LOCK] Locked answer: {locked_answer[:100]}...")

            print(f"\n{'='*80}")
            print(f">>>>>>> [RLAC SUCCESS] Solution survived attack! ({consecutive_robust}/{consecutive_robust_threshold})")
            print(f"{'='*80}\n")

            if consecutive_robust >= consecutive_robust_threshold:
                print(f"\n{'='*80}")
                print(f">>>>>>> [RLAC SUCCESS] Solution ROBUST after {consecutive_robust_threshold} consecutive attacks!")
                print(f">>>>>>> [RLAC SUCCESS] Total rounds: {round_num + 1}")
                print(f"{'='*80}\n")

                # Final cooperative verification as sanity check
                print(">>>>>>> [RLAC FINAL] Running cooperative verification as sanity check...")
                verify, good_verify = verify_solution_safe(
                    problem_statement, solution,
                    reasoning_effort=ver_reasoning
                )

                if "yes" in good_verify.lower():
                    print(">>>>>>> [RLAC FINAL] ✓ Passed both adversarial AND cooperative verification!")

                    # Save attack history
                    if memory_file:
                        history_file = memory_file.replace('.json', '_rlac_history.json')
                        critic.save_attack_history(history_file)

                        # Save final solution with RLAC metadata
                        rlac_metadata = {
                            'solution': solution,
                            'rlac_rounds': round_num + 1,
                            'consecutive_robust': consecutive_robust,
                            'attack_history': rlac_history,
                            'critic_metrics': critic.get_metrics_summary(),
                            'timestamp': __import__('datetime').datetime.now().isoformat()
                        }

                        try:
                            with open(memory_file.replace('.json', '_rlac_solution.json'), 'w') as f:
                                json.dump(rlac_metadata, f, indent=2, ensure_ascii=False)
                            print(f">>>>>>> [RLAC FINAL] Solution and metadata saved")
                        except Exception as e:
                            print(f">>>>>>> [RLAC FINAL] Error saving metadata: {e}")

                    return solution
                else:
                    print(">>>>>>> [RLAC FINAL] ⚠️  Failed cooperative verification")
                    print(">>>>>>> [RLAC FINAL] Continuing adversarial refinement...")
                    consecutive_robust = 0  # Reset and continue

        elif verdict == "BROKEN" or verdict == "SUSPICIOUS":
            # P0-v2 FIX: Enhanced near-success protection with lower threshold and history awareness
            # Changed from threshold=2 to threshold=1 + consider total_robust_count
            if consecutive_robust >= 2:
                # At 2/3 ROBUST, give grace failure - decrement instead of reset
                old_robust = consecutive_robust
                consecutive_robust -= 1
                print(f"\n>>>>>>> [RLAC P0-v2] High protection activated!")
                print(f">>>>>>> [RLAC P0-v2] {old_robust}/3 -> {consecutive_robust}/3 (grace failure)")
            elif consecutive_robust >= 1 and total_robust_count >= 2:
                # P0-v2 NEW: At 1/3 ROBUST with history of robustness - give grace failure
                old_robust = consecutive_robust
                consecutive_robust = max(0, consecutive_robust - 1)
                print(f"\n>>>>>>> [RLAC P0-v2] History-aware protection activated!")
                print(f">>>>>>> [RLAC P0-v2] {old_robust}/3 -> {consecutive_robust}/3")
                print(f">>>>>>> [RLAC P0-v2] Total ROBUST history: {total_robust_count}")
            elif total_robust_count >= 3:
                # P0-v2 NEW: Strong ROBUST history - partial protection even at 0 consecutive
                print(f"\n>>>>>>> [RLAC P0-v2] Strong history protection (total_robust={total_robust_count})")
                print(f">>>>>>> [RLAC P0-v2] Not resetting consecutive_robust due to strong history")
                # Don't reset - keep whatever consecutive_robust we have
            else:
                consecutive_robust = 0  # Full reset when no history
            consecutive_broken += 1  # Track consecutive broken verdicts

            print(f"\n{'='*80}")
            print(f">>>>>>> [RLAC GENERATOR] Solution {verdict}")
            print(f">>>>>>> [RLAC GENERATOR] Counterexamples: {len(counterexamples)}")
            print(f">>>>>>> [RLAC GENERATOR] Consecutive broken: {consecutive_broken}")
            print(f"{'='*80}\n")

            # Show first few counterexamples
            if counterexamples:
                print(f">>>>>>> [RLAC GENERATOR] Sample counterexamples:")
                for i, ce in enumerate(counterexamples[:3], 1):
                    print(f">>>>>>> [RLAC GENERATOR]   {i}. {ce[:150]}{'...' if len(ce) > 150 else ''}")
                print()

                # P6 FIX: Accumulate counterexamples across rounds for evidence building
                for ce in counterexamples[:2]:  # Keep top 2 from each round
                    if len(ce) >= 30:  # Only substantive counterexamples
                        accumulated_counterexamples.append((round_num + 1, ce[:400]))
                # Keep only the most recent evidence
                if len(accumulated_counterexamples) > max_accumulated_evidence:
                    accumulated_counterexamples = accumulated_counterexamples[-max_accumulated_evidence:]
                print(f">>>>>>> [RLAC P6] Accumulated evidence: {len(accumulated_counterexamples)} counterexamples")

            # Calculate current solution score for best solution tracking
            current_score = -total_penalty - len(counterexamples) * 5
            if current_score > best_solution_score:
                best_solution = solution
                best_solution_score = current_score
                best_solution_round = round_num
                print(f">>>>>>> [RLAC TRACKING] New best solution found (score: {current_score}, round: {round_num + 1})")

            # Generator responds to attack
            print(f">>>>>>> [RLAC GENERATOR] Generating defense/revision...")

            # Use constructive mode after repeated broken verdicts
            use_constructive = use_constructive_mode and consecutive_broken >= 3
            if use_constructive:
                print(f">>>>>>> [RLAC GENERATOR] Using CONSTRUCTIVE mode (after {consecutive_broken} consecutive broken)")
            elif defense_first:
                print(f">>>>>>> [RLAC GENERATOR] Using defense-first mode for proactive defense")

            # P5 FIX: Answer reconsideration after threshold consecutive BROKEN verdicts
            use_answer_reconsideration = False
            if consecutive_broken >= answer_reconsideration_threshold and not answer_reconsideration_triggered:
                use_answer_reconsideration = True
                answer_reconsideration_triggered = True
                print(f"\n{'='*80}")
                print(f">>>>>>> [RLAC P5] ANSWER RECONSIDERATION TRIGGERED!")
                print(f">>>>>>> [RLAC P5] {consecutive_broken} consecutive BROKEN verdicts - answer may be fundamentally wrong")
                print(f">>>>>>> [RLAC P5] Accumulated evidence: {len(accumulated_counterexamples)} counterexamples")
                print(f"{'='*80}\n")

            # P7 FIX: Extract current answer for change detection
            def extract_answer_from_solution(sol):
                """Extract the final answer portion from solution for comparison."""
                if not sol:
                    return None
                # Look for common answer markers
                patterns = [
                    r"(?:final\s+)?answer[:\s]+([^\n]{10,200})",
                    r"k\s*[=∈]\s*([^\n]{5,100})",
                    r"conclusion[:\s]+([^\n]{10,200})",
                    r"therefore[,:\s]+([^\n]{10,200})",
                ]
                for pattern in patterns:
                    match = re.search(pattern, sol.lower())
                    if match:
                        return match.group(1).strip()[:100]
                # Fallback: last 200 chars
                return sol[-200:].strip()[:100] if len(sol) > 200 else sol.strip()[:100]

            current_answer_extract = extract_answer_from_solution(solution)

            try:
                # P1-v2 FIX: Enhanced counterexample verification with self-contradiction detection
                # Verify that counterexamples are actually valid before using them to guide defense
                verified_counterexamples = []
                p1_downgrade_reasons = []

                if counterexamples and len(counterexamples) > 0:
                    print(f">>>>>>> [RLAC P1-v2] Verifying {len(counterexamples)} counterexample(s)...")

                    # Also check full attack text for self-contradiction
                    full_attack_text = attack_result.get('full_attack', '')

                    for i, ce in enumerate(counterexamples[:3]):  # Verify up to 3 counterexamples
                        ce_lower = ce.lower()

                        # Quick validation: check if counterexample is substantive
                        if len(ce) < 20:
                            print(f">>>>>>> [RLAC P1-v2]   CE #{i+1}: Too short ({len(ce)} chars) - skipping")
                            continue

                        # P1-v2 NEW: Self-contradiction detection patterns
                        # These patterns indicate the critic realized its counterexample is invalid
                        contradiction_patterns = [
                            r"actually\s+(works?|correct|valid|does\s+cover)",
                            r"the\s+(attempted\s+)?counterexample\s+(fails?|is\s+invalid|doesn't\s+work)",
                            r"(never\s*mind|on\s+second\s+thought|wait|correction:)",
                            r"(thus|therefore|so)\s+(the\s+)?construction\s+(does|actually)\s+(work|cover)",
                            r"this\s+(proves?|shows?)\s+(the\s+)?solution\s+(is\s+)?(correct|valid)",
                            r"the\s+solution\s+does\s+cover",
                            r"construction\s+(\*\*)?does(\*\*)?\s+cover",
                            r"works?\s+for\s+n\s*=\s*\d+",
                        ]

                        is_self_contradicting = False
                        contradiction_match = None
                        for pattern in contradiction_patterns:
                            match = re.search(pattern, ce_lower)
                            if match:
                                is_self_contradicting = True
                                contradiction_match = match.group(0)
                                break

                        if is_self_contradicting:
                            print(f">>>>>>> [RLAC P1-v2]   CE #{i+1}: SELF-CONTRADICTION detected!")
                            print(f">>>>>>> [RLAC P1-v2]   Matched: '{contradiction_match}'")
                            p1_downgrade_reasons.append(f"CE #{i+1} self-contradicts: '{contradiction_match}'")
                            verified_counterexamples.append(("self_contradicting", ce))
                            continue

                        # P1-v2 NEW: Check for explicit "but it works" conclusions
                        conclusion_patterns = [
                            r"\*?conclusion:?\*?.*?(works|correct|valid|cover)",
                            r"therefore.*?(works|valid)",
                            r"we\s+must\s+look\s+for\s+(a\s+)?different",
                        ]

                        has_invalidating_conclusion = False
                        for pattern in conclusion_patterns:
                            if re.search(pattern, ce_lower):
                                has_invalidating_conclusion = True
                                break

                        if has_invalidating_conclusion:
                            print(f">>>>>>> [RLAC P1-v2]   CE #{i+1}: Contains invalidating conclusion")
                            p1_downgrade_reasons.append(f"CE #{i+1} has invalidating conclusion")
                            verified_counterexamples.append(("invalidated", ce))
                            continue

                        # Original P1 checks: vague indicators
                        vague_indicators = ["might fail", "could fail", "may not work", "unclear", "possibly wrong"]
                        is_vague = any(ind in ce_lower for ind in vague_indicators)

                        if is_vague:
                            print(f">>>>>>> [RLAC P1-v2]   CE #{i+1}: Appears vague/hypothetical")
                            verified_counterexamples.append(("vague", ce))
                            continue

                        # Original P1 check: concrete values
                        concrete_value_pattern = r'[nkxyzabcm]\s*[=≤≥<>]\s*\d+'
                        has_concrete_values = bool(re.search(concrete_value_pattern, ce, re.IGNORECASE))

                        if has_concrete_values:
                            print(f">>>>>>> [RLAC P1-v2]   CE #{i+1}: VERIFIED - contains concrete values")
                            verified_counterexamples.append(("verified", ce))
                        else:
                            print(f">>>>>>> [RLAC P1-v2]   CE #{i+1}: No concrete values - flagged")
                            verified_counterexamples.append(("unverified", ce))

                    # P1-v2 NEW: Verdict adjustment based on self-contradiction detection
                    valid_ces = [ce for status, ce in verified_counterexamples if status == "verified"]
                    self_contradicting_ces = [ce for status, ce in verified_counterexamples
                                              if status in ("self_contradicting", "invalidated")]

                    if len(self_contradicting_ces) > 0 and len(valid_ces) == 0:
                        print(f"\n>>>>>>> [RLAC P1-v2] ALL counterexamples self-contradicting!")
                        print(f">>>>>>> [RLAC P1-v2] Critic proved solution works - upgrading to ROBUST")
                        verdict = "ROBUST"
                        attack_result['verdict'] = "ROBUST"
                        attack_result['p1_upgraded'] = True
                        attack_result['p1_reasons'] = p1_downgrade_reasons
                    elif len(self_contradicting_ces) > len(valid_ces) and len(valid_ces) == 0:
                        print(f"\n>>>>>>> [RLAC P1-v2] Majority of counterexamples self-contradicting")
                        print(f">>>>>>> [RLAC P1-v2] Downgrading verdict from BROKEN to SUSPICIOUS")
                        verdict = "SUSPICIOUS"
                        attack_result['verdict'] = "SUSPICIOUS"
                        attack_result['p1_downgraded'] = True
                        attack_result['p1_reasons'] = p1_downgrade_reasons
                    elif len(valid_ces) > 0:
                        print(f">>>>>>> [RLAC P1-v2] Using {len(valid_ces)} verified counterexample(s)")
                        attack_result['verified_counterexamples'] = valid_ces
                    else:
                        print(f">>>>>>> [RLAC P1-v2] WARNING: No valid counterexamples")
                        if verdict == "BROKEN":
                            print(f">>>>>>> [RLAC P1-v2] Treating as SUSPICIOUS")
                            verdict = "SUSPICIOUS"
                            attack_result['verdict'] = "SUSPICIOUS"
                            attack_result['p1_downgraded'] = True

                # P2 FIX (continued): Answer lock enforcement in defense prompt
                answer_lock_instruction = ""
                if answer_locked and locked_answer:
                    answer_lock_instruction = f"""
CRITICAL ANSWER LOCK INSTRUCTION:
The answer "{locked_answer[:100]}..." has been validated in previous rounds and MUST be preserved.
You may ONLY fix the PROOF/JUSTIFICATION, not the answer itself.
If you believe the answer must change, you must provide OVERWHELMING evidence with at least 3 concrete counterexamples.
"""
                    print(f">>>>>>> [RLAC LOCK] Adding answer lock instruction to defense prompt")

                # Build defense prompt (P5/P5.1: reconsideration, constructive, or defense-first mode)
                if use_answer_reconsideration:
                    # P5/P6 FIX: Use answer reconsideration with accumulated evidence
                    evidence_summary = "\n".join([
                        f"Round {r}: {ce}" for r, ce in accumulated_counterexamples
                    ]) if accumulated_counterexamples else "Multiple counterexamples found"

                    # Extract previous answer for P7 tracking
                    prev_answer = current_answer_extract or "Unknown answer"

                    # P5.1 FIX: Use enhanced verification prompt after higher threshold
                    use_p51_enhanced = (consecutive_broken >= p51_verification_threshold and
                                        not p51_verification_triggered)

                    if use_p51_enhanced:
                        p51_verification_triggered = True
                        defense_prompt = answer_reconsideration_with_verification_prompt.format(
                            consecutive_broken=consecutive_broken,
                            counterexample_evidence=evidence_summary,
                            previous_answer=prev_answer
                        )
                        print(f"\n{'='*80}")
                        print(f">>>>>>> [RLAC P5.1] ENHANCED VERIFICATION TRIGGERED!")
                        print(f">>>>>>> [RLAC P5.1] {consecutive_broken} consecutive BROKEN - mandatory small case verification")
                        print(f">>>>>>> [RLAC P5.1] Previous answer: {prev_answer[:80]}...")
                        print(f"{'='*80}\n")
                    else:
                        defense_prompt = answer_reconsideration_prompt.format(
                            counterexample_evidence=evidence_summary,
                            previous_answer=prev_answer
                        )
                        print(f">>>>>>> [RLAC P5] Using ANSWER RECONSIDERATION prompt")
                        print(f">>>>>>> [RLAC P5] Previous answer: {prev_answer[:80]}...")
                elif use_constructive:
                    defense_prompt = constructive_defense_prompt.format(
                        constructive_feedback=attack_result.get('full_attack', str(counterexamples))
                    )
                else:
                    defense_prompt = critic.get_defense_prompt(attack_result, defense_first=defense_first)

                # Create revision request with answer lock instruction if active
                # P5 NOTE: Skip answer lock when doing reconsideration (opposite goals)
                revision_prompts = other_prompts + [
                    f"Previous solution:\n{solution}",
                    defense_prompt
                ]
                if answer_lock_instruction and not use_answer_reconsideration:
                    revision_prompts.append(answer_lock_instruction)

                payload = build_request_payload(
                    system_prompt=step1_prompt,
                    question_prompt=problem_statement,
                    other_prompts=revision_prompts,
                    reasoning_effort=sol_reasoning
                )

                # Generate revised solution
                response = send_api_request(get_api_key(), payload, request_label="RLAC defense prompt")
                revised_solution = extract_solution(extract_text_from_response(response))

                # Check if solution actually changed
                if revised_solution == solution or not revised_solution:
                    stuck_count += 1
                    print(f"\n>>>>>>> [RLAC GENERATOR] ⚠️  Solution unchanged! (stuck_count={stuck_count}/{stuck_threshold})")

                    # Try approach diversification before giving up
                    if stuck_count == stuck_threshold - 1 and regeneration_attempts < max_regeneration_attempts:
                        print(f"\n{'='*80}")
                        print(f">>>>>>> [RLAC DIVERSIFY] Attempting approach diversification...")
                        print(f">>>>>>> [RLAC DIVERSIFY] Generator stuck on same approach")
                        print(f"{'='*80}\n")

                        # Summarize failed approach
                        approach_summary = solution[:500] if solution else "No solution"
                        counterexample_summary = "\n".join([f"- {ce[:200]}" for ce in counterexamples[:3]]) if counterexamples else "None"
                        failed_approach_summaries.append(approach_summary[:200])

                        # Build diversification prompt
                        diversify_prompt = approach_diversification_prompt.format(
                            failed_approach_summary="\n".join(failed_approach_summaries[-3:]),
                            counterexamples=counterexample_summary
                        )

                        # Generate completely new solution with different approach
                        diversify_payload = build_request_payload(
                            system_prompt=step1_prompt,
                            question_prompt=problem_statement,
                            other_prompts=other_prompts + [diversify_prompt],
                            reasoning_effort="medium"  # Use medium for diversification
                        )

                        diversify_response = send_api_request(get_api_key(), diversify_payload, request_label="RLAC approach diversification")
                        diversified_solution = extract_solution(extract_text_from_response(diversify_response))

                        if diversified_solution and diversified_solution != solution:
                            print(f">>>>>>> [RLAC DIVERSIFY] ✓ Generated new solution with different approach")
                            print(f">>>>>>> [RLAC DIVERSIFY] Length: {len(diversified_solution)} chars")
                            solution = diversified_solution
                            stuck_count = 0  # Reset stuck counter
                            consecutive_broken = 0
                            regeneration_attempts += 1
                            continue
                        else:
                            print(f">>>>>>> [RLAC DIVERSIFY] ⚠️  Diversification did not produce new solution")

                    if stuck_count >= stuck_threshold:
                        print(f"\n{'='*80}")
                        print(f">>>>>>> [RLAC FAILURE] Generator stuck - unable to address attacks")
                        print(f">>>>>>> [RLAC FAILURE] Same solution for {stuck_count} consecutive rounds")

                        # Return best solution found if it's better than nothing
                        if best_solution and best_solution_score > -100:
                            print(f">>>>>>> [RLAC FALLBACK] Returning best solution found (round {best_solution_round + 1}, score {best_solution_score})")
                            print(f"{'='*80}\n")

                            # Save failure data with best solution
                            if memory_file:
                                failure_data = {
                                    'reason': 'generator_stuck_with_fallback',
                                    'stuck_count': stuck_count,
                                    'last_attack': attack_result,
                                    'rlac_history': rlac_history,
                                    'best_solution': best_solution,
                                    'best_solution_round': best_solution_round,
                                    'best_solution_score': best_solution_score,
                                    'critic_metrics': critic.get_metrics_summary(),
                                    'failed_approaches': failed_approach_summaries
                                }
                                try:
                                    with open(memory_file.replace('.json', '_rlac_failure.json'), 'w') as f:
                                        json.dump(failure_data, f, indent=2, ensure_ascii=False)
                                except:
                                    pass

                            return best_solution
                        else:
                            print(f"{'='*80}\n")
                            # Save failure data
                            if memory_file:
                                failure_data = {
                                    'reason': 'generator_stuck',
                                    'stuck_count': stuck_count,
                                    'last_attack': attack_result,
                                    'rlac_history': rlac_history,
                                    'critic_metrics': critic.get_metrics_summary(),
                                    'failed_approaches': failed_approach_summaries
                                }

                                try:
                                    with open(memory_file.replace('.json', '_rlac_failure.json'), 'w') as f:
                                        json.dump(failure_data, f, indent=2, ensure_ascii=False)
                                except:
                                    pass

                            return None
                else:
                    # Solution changed - progress made
                    stuck_count = 0
                    # FIX: Do NOT reset consecutive_broken here
                    # consecutive_broken tracks how many BROKEN verdicts in a row,
                    # regardless of whether the solution changes.
                    # This allows constructive mode to activate when the generator
                    # keeps trying but critic keeps finding issues.
                    # consecutive_broken is only reset on ROBUST verdict (line ~2313)
                    solution_delta = len(revised_solution) - len(solution)
                    solution = revised_solution

                    print(f">>>>>>> [RLAC GENERATOR] ✓ Solution revised")
                    print(f">>>>>>> [RLAC GENERATOR] Length change: {solution_delta:+d} chars (now {len(solution)} chars)")

                    # P7 FIX: Check if answer actually changed after reconsideration
                    # P9 FIX: Use semantic fingerprinting for meaningful change detection
                    if answer_reconsideration_triggered:
                        new_answer_extract = extract_answer_from_solution(solution)

                        # P9: Extract semantic fingerprint for meaningful comparison
                        new_semantic_fp = extract_semantic_fingerprint(solution)

                        # P7: Text-based similarity (original)
                        text_similarity = 0.0
                        if previous_answer_extract and new_answer_extract:
                            from difflib import SequenceMatcher
                            text_similarity = SequenceMatcher(None, previous_answer_extract, new_answer_extract).ratio()

                        # P9: Semantic similarity (new)
                        sem_similarity = 0.0
                        if previous_semantic_fingerprint:
                            sem_similarity = semantic_similarity(previous_semantic_fingerprint, new_semantic_fp)

                        # Use BOTH metrics - answer is unchanged only if BOTH are high
                        # This prevents superficial text changes from resetting counters
                        text_unchanged = text_similarity > 0.8
                        semantic_unchanged = sem_similarity > 0.7

                        print(f">>>>>>> [RLAC P7] Text similarity: {text_similarity:.2f}")
                        print(f">>>>>>> [RLAC P9] Semantic similarity: {sem_similarity:.2f}")
                        if new_semantic_fp.get('formulas'):
                            print(f">>>>>>> [RLAC P9] Formulas detected: {new_semantic_fp['formulas'][:3]}")
                        if new_semantic_fp.get('impossible'):
                            print(f">>>>>>> [RLAC P9] Impossibility claims: {new_semantic_fp['impossible'][:3]}")

                        # P9: Consider answer unchanged if SEMANTICALLY similar (even if text changed)
                        if semantic_unchanged:
                            semantic_unchanged_count += 1
                            answer_unchanged_after_reconsideration += 1
                            print(f">>>>>>> [RLAC P9] Answer SEMANTICALLY UNCHANGED (sem: {sem_similarity:.2f}, text: {text_similarity:.2f})")
                            print(f">>>>>>> [RLAC P9] Generator made superficial changes but meaning unchanged!")
                            print(f">>>>>>> [RLAC P9] Semantic unchanged count: {semantic_unchanged_count}")
                        elif text_unchanged:
                            answer_unchanged_after_reconsideration += 1
                            print(f">>>>>>> [RLAC P7] Answer TEXT UNCHANGED (similarity: {text_similarity:.2f})")
                            print(f">>>>>>> [RLAC P7] Unchanged count: {answer_unchanged_after_reconsideration}")
                        else:
                            print(f">>>>>>> [RLAC P7/P9] Answer MEANINGFULLY CHANGED!")
                            print(f">>>>>>> [RLAC P7] Previous: {previous_answer_extract[:60] if previous_answer_extract else 'N/A'}...")
                            print(f">>>>>>> [RLAC P7] New:      {new_answer_extract[:60] if new_answer_extract else 'N/A'}...")
                            answer_unchanged_after_reconsideration = 0  # Reset on meaningful change
                            semantic_unchanged_count = 0

                        # Update semantic fingerprint for next comparison
                        previous_semantic_fingerprint = new_semantic_fp

                        # P8 FIX: Fresh start if answer unchanged after reconsideration and still broken
                        # P9 enhancement: Also trigger if semantically unchanged multiple times
                        should_fresh_start = (
                            consecutive_broken >= fresh_start_threshold and
                            (answer_unchanged_after_reconsideration >= 2 or semantic_unchanged_count >= 3) and
                            not fresh_start_triggered and
                            regeneration_attempts < max_regeneration_attempts
                        )
                        if should_fresh_start:

                            fresh_start_triggered = True
                            print(f"\n{'='*80}")
                            print(f">>>>>>> [RLAC P8] FRESH START TRIGGERED!")
                            print(f">>>>>>> [RLAC P8] {consecutive_broken} consecutive BROKEN with same answer")
                            print(f">>>>>>> [RLAC P8] Generator refuses to change answer despite evidence")
                            print(f">>>>>>> [RLAC P8] Starting from scratch with different approach")
                            print(f"{'='*80}\n")

                            # Build fresh start prompt
                            failed_summary = "\n".join(failed_approach_summaries[-3:]) if failed_approach_summaries else "Previous attempts failed"
                            evidence_summary = "\n".join([f"- {ce}" for _, ce in accumulated_counterexamples[-5:]])

                            fresh_prompt = solution_regeneration_prompt.format(
                                failed_approaches=failed_summary,
                                problem_requirements=problem_statement[:500]
                            ) + f"\n\n**Evidence from critic that previous answer was wrong:**\n{evidence_summary}"

                            fresh_payload = build_request_payload(
                                system_prompt=step1_prompt,
                                question_prompt=problem_statement,
                                other_prompts=other_prompts + [fresh_prompt],
                                reasoning_effort="medium"
                            )

                            fresh_response = send_api_request(get_api_key(), fresh_payload, request_label="RLAC P8 fresh start")
                            fresh_solution = extract_solution(extract_text_from_response(fresh_response))

                            if fresh_solution and fresh_solution != solution:
                                print(f">>>>>>> [RLAC P8] ✓ Fresh solution generated ({len(fresh_solution)} chars)")
                                solution = fresh_solution
                                consecutive_broken = 0
                                answer_reconsideration_triggered = False  # Allow reconsideration again
                                regeneration_attempts += 1
                                # Update answer extract for next comparison
                                previous_answer_extract = extract_answer_from_solution(solution)
                                continue
                            else:
                                print(f">>>>>>> [RLAC P8] ⚠️  Fresh start did not produce different solution")

                    # Update previous answer for next iteration
                    previous_answer_extract = extract_answer_from_solution(solution)

                    # Answer stability tracking using enhanced session's LaTeX parser
                    new_answer_result = enhanced_session.extract_answer(solution)
                    new_answer = new_answer_result.normalized if new_answer_result.success else extract_answer_key(solution)

                    if new_answer and answer_history:
                        # Use enhanced session's stability checking
                        stability = enhanced_session.check_answer_stability(new_answer_result)

                        if stability['oscillating']:
                            answer_oscillation_count = stability['oscillation_count']
                            print(f">>>>>>> [RLAC STABILITY] ⚠️  Answer oscillation detected! ({answer_oscillation_count})")
                            print(f">>>>>>> [RLAC STABILITY] Current answer matches earlier attempt")

                            if answer_oscillation_count >= 3:
                                print(f">>>>>>> [RLAC STABILITY] Too many oscillations - solution unstable")
                                # Try approach diversification if stuck in oscillation
                                if regeneration_attempts < max_regeneration_attempts:
                                    print(f">>>>>>> [RLAC STABILITY] Triggering approach diversification due to oscillation")
                                    failed_approach_summaries.append(f"Oscillating between answers: {', '.join(answer_history[-3:])}")

                        elif stability['changes'] > 0:
                            print(f">>>>>>> [RLAC STABILITY] Answer changed ({stability['changes']} total changes)")

                        answer_history.append(new_answer)

                    # Validate answer change
                    answer_validation = validate_answer_change(
                        previous_solution, solution, round_num, verbose=verbose
                    )
                    if answer_validation['narrowed']:
                        print(f">>>>>>> [RLAC GENERATOR] ⚠️  Answer narrowing detected")

                    previous_solution = solution

            except Exception as e:
                print(f">>>>>>> [RLAC GENERATOR] Error generating revision: {e}")
                stuck_count += 1
                if stuck_count >= stuck_threshold:
                    print(f">>>>>>> [RLAC FAILURE] Too many errors, aborting")
                    return None
                continue

        else:  # UNKNOWN verdict
            print(f">>>>>>> [RLAC WARNING] Unknown verdict from critic")
            consecutive_robust = 0

        # Check for critic-detected stuck pattern (must be combined with stuck_count)
        # FIX: Only trigger failure if BOTH conditions are met:
        # 1. stuck_count > 0 (solution is not changing) OR multiple rounds of broken
        # 2. Attack pattern is repeating (same flaws keep appearing)
        # This prevents premature failure when solutions ARE changing but critic keeps finding issues
        critic_stuck = critic.detect_stuck_pattern(recent_rounds=4)
        if critic_stuck and stuck_count > 0:
            # Generator is truly stuck - solution not changing AND attack pattern repeating
            print(f"\n{'='*80}")
            print(f">>>>>>> [RLAC FAILURE] Critic detected stuck pattern")
            print(f">>>>>>> [RLAC FAILURE] Generator unable to address attacks effectively")
            print(f">>>>>>> [RLAC FAILURE] (stuck_count={stuck_count}, attack_pattern=repeated)")
            print(f"{'='*80}\n")
            # Try to return best solution instead of None
            if best_solution and best_solution_score > -100:
                print(f">>>>>>> [RLAC FALLBACK] Returning best solution found (score: {best_solution_score})")
                return best_solution
            return None
        elif critic_stuck and consecutive_broken >= stuck_threshold:
            # Solutions changing but consistently broken - allow more attempts but warn
            print(f">>>>>>> [RLAC WARNING] Attack pattern repeating but solutions still changing")
            print(f">>>>>>> [RLAC WARNING] (consecutive_broken={consecutive_broken}, stuck_count={stuck_count})")
            # Don't fail yet - let it continue until max_rounds or stuck_count triggers

    # Reached max rounds without success
    print(f"\n{'='*80}")
    print(f">>>>>>> [RLAC TIMEOUT] Maximum rounds ({max_adversarial_rounds}) reached")
    print(f">>>>>>> [RLAC TIMEOUT] Best consecutive robust: {consecutive_robust}/{consecutive_robust_threshold}")
    print(f"{'='*80}\n")

    # Save timeout data
    if memory_file:
        timeout_data = {
            'reason': 'max_rounds_exceeded',
            'max_rounds': max_adversarial_rounds,
            'best_consecutive_robust': consecutive_robust,
            'final_solution': solution,
            'rlac_history': rlac_history,
            'critic_metrics': critic.get_metrics_summary()
        }

        try:
            with open(memory_file.replace('.json', '_rlac_timeout.json'), 'w') as f:
                json.dump(timeout_data, f, indent=2, ensure_ascii=False)
        except:
            pass

    return None

def agent(problem_statement, other_prompts=[], memory_file=None, resume_from_memory=False,
          solution_reasoning=None, self_improvement_reasoning=None, verification_reasoning=None,
          num_initial_attempts=1, use_mcts=False, mcts_simulations=5, mcts_exploration=1.414, best_of_n=0,
          use_proof_sketch=False, use_rlac=False, rlac_max_rounds=12, rlac_robust_threshold=3, rlac_stuck_threshold=2,
          rlac_defense_first=True, rlac_max_regeneration=2, rlac_constructive_mode=True, rlac_critic_reasoning=None):
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
        use_rlac: If True, use RLAC (Adversarial Critic) mode (default: False)
        rlac_max_rounds: Maximum RLAC adversarial rounds (default: 12)
        rlac_robust_threshold: Consecutive robust verdicts needed (default: 3)
        rlac_stuck_threshold: Consecutive failed fixes before stuck (default: 2)
        rlac_defense_first: If True, use defense-first mode for proactive attack anticipation (default: True)
        rlac_max_regeneration: Maximum regeneration attempts when initial solution is invalid (default: 2)
        rlac_constructive_mode: Use constructive critic mode after repeated failures (default: True)
        rlac_critic_reasoning: Reasoning effort for RLAC adversarial critic (default: medium). Overrides ver_reasoning for RLAC mode.
    """
    # Set reasoning efforts with CLI overrides if provided
    sol_reasoning = solution_reasoning or SOLUTION_REASONING_EFFORT
    self_imp_reasoning = self_improvement_reasoning or SELF_IMPROVEMENT_REASONING_EFFORT
    ver_reasoning = verification_reasoning or VERIFICATION_REASONING_EFFORT

    # RLAC MODE: Use adversarial critic instead of standard agent loop
    if use_rlac:
        print(f"\n{'='*80}")
        print(f">>>>>>> RLAC MODE SELECTED")
        print(f">>>>>>> Redirecting to adversarial critic agent")
        print(f"{'='*80}\n")

        # Use dedicated RLAC critic reasoning if provided, otherwise fall back to ver_reasoning
        # Default for RLAC critic is "medium" (set via CLI default) for balanced attack quality
        rlac_ver_reasoning = rlac_critic_reasoning or ver_reasoning

        return rlac_agent(
            problem_statement=problem_statement,
            other_prompts=other_prompts,
            sol_reasoning=sol_reasoning,
            self_imp_reasoning=self_imp_reasoning,
            ver_reasoning=rlac_ver_reasoning,
            max_adversarial_rounds=rlac_max_rounds,
            consecutive_robust_threshold=rlac_robust_threshold,
            stuck_threshold=rlac_stuck_threshold,
            memory_file=memory_file,
            verbose=True,
            defense_first=rlac_defense_first,
            max_regeneration_attempts=rlac_max_regeneration,
            use_constructive_mode=rlac_constructive_mode
        )

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
        if use_mcts:
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
                    verify_solution_func=verify_solution,  # Use simple verification
                    sol_reasoning=sol_reasoning,
                    self_imp_reasoning=self_imp_reasoning,
                    ver_reasoning=ver_reasoning,
                    exploration_constant=mcts_exploration,
                    max_depth=2,
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
        # Use the verification reasoning effort
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

                response2 = send_api_request(get_api_key(), p1, request_label="Correction prompt")
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

            # Detect stuck pattern - DISABLED for low/low/low compatibility
            # Threshold of 3 is too aggressive for low reasoning which needs more iterations
            # To re-enable, uncomment and increase threshold to 10+ for low reasoning
            # if detect_stuck_pattern(correct_history, error_history, i, threshold=3, verbose=True):
            #     print(f">>>>>>> [STUCK DETECTION] Stopping due to stuck pattern")
            #     print(f">>>>>>> [STUCK DETECTION] Recommendation: Try different reasoning level or approach")
            #     # Save final state before stopping
            #     if memory_file:
            #         save_memory(memory_file, problem_statement, other_prompts, i, 30, solution, verify,
            #                    sol_reasoning, self_imp_reasoning, ver_reasoning)
            #     return None

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
    parser.add_argument('--mcts-simulations', type=int, default=5,
                       help='Number of MCTS simulations (default: 5, baseline proven config)')
    parser.add_argument('--mcts-exploration', type=float, default=1.414,
                       help='MCTS exploration constant for UCB1 (default: 1.414, sqrt(2) baseline)')
    parser.add_argument('--best-of-n', type=int, default=0,
                       help='If > 0, verify top N MCTS solutions and return first verified (default: 0=disabled). Recommended: 3-5 for higher success rate.')
    parser.add_argument('--use-proof-sketch', action='store_true',
                       help='Use Proof Sketch architecture: outline → verify structure → expand details → verify math')
    parser.add_argument('--use-translation', action='store_true',
                       help='Enable translation layer for asymmetric reasoning (low gen / high ver)')
    parser.add_argument('--verification-timeout', type=int, default=600,
                       help='Timeout for verification in seconds (default: 600 = 10 min). Prevents hangs.')
    parser.add_argument('--verification-max-attempts', type=int, default=3,
                       help='Max verification attempts with exponential backoff before fallback (default: 3)')
    parser.add_argument('--disable-verification-safeguards', action='store_true',
                       help='Disable verification timeout and retry safeguards (not recommended)')

    # RLAC (Adversarial Critic) Arguments
    parser.add_argument('--use-rlac', action='store_true',
                       help='Use RLAC (Adversarial Critic) mode: Generator-Critic adversarial loop')
    parser.add_argument('--rlac-max-rounds', type=int, default=12,
                       help='Maximum RLAC adversarial rounds (default: 12)')
    parser.add_argument('--rlac-robust-threshold', type=int, default=3,
                       help='Consecutive robust verdicts needed for success (default: 3)')
    parser.add_argument('--rlac-stuck-threshold', type=int, default=2,
                       help='Consecutive failed fixes before declaring stuck (default: 2)')
    parser.add_argument('--rlac-defense-first', action='store_true', default=True,
                       help='Enable defense-first mode for proactive attack anticipation (default: True)')
    parser.add_argument('--no-rlac-defense-first', action='store_true',
                       help='Disable defense-first mode')
    parser.add_argument('--rlac-max-regeneration', type=int, default=2,
                       help='Maximum regeneration attempts when initial solution is invalid (default: 2)')
    parser.add_argument('--rlac-constructive-mode', action='store_true', default=True,
                       help='Use constructive critic mode after repeated failures (default: True)')
    parser.add_argument('--no-rlac-constructive-mode', action='store_true',
                       help='Disable constructive critic mode')
    parser.add_argument('--rlac-critic-reasoning', type=str, choices=['low', 'medium', 'high'], default='medium',
                       help='Reasoning effort for RLAC adversarial critic attacks (default: medium). Higher = more rigorous attacks.')

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
    use_rlac = args.use_rlac
    rlac_max_rounds = args.rlac_max_rounds
    rlac_robust_threshold = args.rlac_robust_threshold
    rlac_stuck_threshold = args.rlac_stuck_threshold
    rlac_defense_first = args.rlac_defense_first and not args.no_rlac_defense_first
    rlac_max_regeneration = args.rlac_max_regeneration
    rlac_constructive_mode = args.rlac_constructive_mode and not args.no_rlac_constructive_mode
    rlac_critic_reasoning = args.rlac_critic_reasoning

    # Set verification safeguard module variables (no 'global' needed at module level)
    VERIFICATION_TIMEOUT = args.verification_timeout
    VERIFICATION_MAX_ATTEMPTS = args.verification_max_attempts
    VERIFICATION_SAFEGUARDS_ENABLED = not args.disable_verification_safeguards

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
                       use_proof_sketch, use_rlac, rlac_max_rounds, rlac_robust_threshold, rlac_stuck_threshold,
                       rlac_defense_first, rlac_max_regeneration, rlac_constructive_mode, rlac_critic_reasoning)
            if(sol is not None):
                print(f">>>>>>> Found a correct solution in run {i}.")
                print(json.dumps(sol, indent=4))
                break
        except Exception as e:
            print(f">>>>>>> Error in run {i}: {e}")
            continue

    # Close log file if it was opened
    close_log_file()

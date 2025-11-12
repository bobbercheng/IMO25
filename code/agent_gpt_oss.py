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
API_URL = os.getenv("GPT_OSS_API_URL", "http://localhost:8000/v1/chat/completions")
# Reasoning effort level (low, medium, high)
REASONING_EFFORT = os.getenv("GPT_OSS_REASONING_EFFORT", "high")

# Print configuration on module load
import sys
if not hasattr(sys, '_agent_gpt_oss_config_printed'):
    sys._agent_gpt_oss_config_printed = True
    # Use original_print before we override it
    _original_builtin_print = print
    _original_builtin_print(f"[CONFIG] GPT_OSS API URL: {API_URL}")
    _original_builtin_print(f"[CONFIG] Reasoning Effort: {REASONING_EFFORT}")

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

def build_request_payload(system_prompt, question_prompt, other_prompts=None):
    """
    Builds the JSON payload for the OpenAI-compatible API request.
    """
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
            "effort": REASONING_EFFORT
        },
        # Add repetition penalty to prevent loops
        "repetition_penalty": 1.05
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
    MAX_CONTENT_LENGTH = 50000  # Maximum content length before forcing stop

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
    """
    try:
        message = response_data['choices'][0]['message']
        content = message.get('content', '')

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

    # Try to extract the final message (between last <|channel|>final<|message|> and end)
    # Pattern: <|channel|>final<|message|>ACTUAL_CONTENT (may or may not end with <|end|>)

    # Find the final channel message
    final_match = re.search(r'<\|channel\|>final<\|message\|>(.*?)(?:<\|end\|>)?$', content, re.DOTALL)
    if final_match:
        return final_match.group(1).strip()

    # If no final channel found, try to remove all tags
    # Remove all instances of <|...| > tags
    cleaned = re.sub(r'<\|[^|]+\|>', '', content)
    return cleaned.strip()

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

def verify_solution(problem_statement, solution, verbose=True):

    dsol = extract_detailed_solution(extract_solution(solution))

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
        bug_report = extract_detailed_solution(extract_solution(out), "Detailed Verification", False)

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

    p1 = build_request_payload(system_prompt="", question_prompt=check_complete_prompt)
    r = send_api_request(get_api_key(), p1)
    o = extract_text_from_response(r)

    print(o)
    return "yes" in o.lower()


def init_explorations(problem_statement, verbose=True, other_prompts=[]):
    p1 = build_request_payload(
            system_prompt=step1_prompt,
            question_prompt=problem_statement,
            other_prompts=other_prompts
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

    response2 = send_api_request(get_api_key(), p1)
    solution = extract_solution(extract_text_from_response(response2))
    print(f">>>>>>> Corrected solution:")
    print(json.dumps(solution, indent=4))

    print(f">>>>>>> Vefify the solution.")
    verify, good_verify = verify_solution(problem_statement, solution, verbose)

    print(f">>>>>>> Initial verification:")
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
        try:
            print(f"Number of iterations: {i}, number of corrects: {correct_count}, number of errors: {error_count}")

            if("yes" not in good_verify.lower()):
                # clear
                correct_count = 0
                error_count += 1

                #self improvement
                print(">>>>>>> Verification does not pass, correcting ...")

                p1 = build_request_payload(
                    system_prompt=step1_prompt,
                    question_prompt=problem_statement,
                    other_prompts=other_prompts
                )

                # Append previous solution as assistant message
                # Note: solution is extracted text, should not contain thinking tags
                p1["messages"].append(
                    {"role": "assistant",
                    "content": solution
                    }
                )

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
            print(f">>>>>>> Error in run {i}: {e}")
            continue

    if(not success):
        print(">>>>>>> Failed in finding a correct solution.")
        return None

if __name__ == "__main__":
    # Set up argument parsing
    parser = argparse.ArgumentParser(description='IMO Problem Solver Agent using GPT-OSS')
    parser.add_argument('problem_file', nargs='?', default='problem_statement.txt',
                       help='Path to the problem statement file (default: problem_statement.txt)')
    parser.add_argument('--log', '-l', type=str, help='Path to log file (optional)')
    parser.add_argument('--other_prompts', '-o', type=str, help='Other prompts (optional)')
    parser.add_argument("--max_runs", '-m', type=int, default=10, help='Maximum number of runs (default: 10)')

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

    problem_statement = read_file_content(args.problem_file)

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

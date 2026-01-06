#!/usr/bin/env python3
"""
Extract and compare LLM verdicts from runs 2 and 3
"""

import re
from pathlib import Path

def extract_test_verdicts(log_file):
    """Extract verdicts for each test from a log file."""
    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    verdicts = {}

    # Split by test sections
    test_sections = re.split(r'Running Test: (Test \d+:.*?)$', content, flags=re.MULTILINE)

    for i in range(1, len(test_sections), 2):
        if i+1 >= len(test_sections):
            break

        test_name = test_sections[i]
        test_content = test_sections[i+1]

        # Extract test number
        test_num_match = re.match(r'Test (\d+):', test_name)
        if not test_num_match:
            continue
        test_num = int(test_num_match.group(1))

        # Find the streaming response section
        streaming_match = re.search(
            r'>>>>>>> Streaming Response:\s*={70,}\s*(.*?)\s*={70,}',
            test_content,
            re.DOTALL
        )

        if streaming_match:
            response_text = streaming_match.group(1).strip()

            # Extract first 500 chars or until we hit verification results
            summary = response_text[:1000]

            # Look for Final Verdict
            verdict_match = re.search(r'\*\*Final Verdict\*\*:?\s*(.*?)(?:\n|$)', summary, re.IGNORECASE)
            if verdict_match:
                verdict_text = verdict_match.group(1).strip()
            elif len(response_text) == 0:
                verdict_text = "[EMPTY RESPONSE]"
            else:
                verdict_text = "[NO VERDICT FOUND] Response starts: " + summary[:200]

            verdicts[test_num] = {
                'name': test_name,
                'verdict': verdict_text,
                'response_length': len(response_text),
                'is_empty': len(response_text) == 0
            }
        else:
            # Check for empty content in the JSON response
            empty_content_match = re.search(r'"content":\s*""', test_content)
            if empty_content_match:
                verdicts[test_num] = {
                    'name': test_name,
                    'verdict': "[EMPTY RESPONSE - JSON content: \"\"]",
                    'response_length': 0,
                    'is_empty': True
                }

    return verdicts

# Extract verdicts from runs 2 and 3
run2_file = Path("/home/user/IMO25/test_option_b_full_solution_validation_high_42015fb_2.log")
run3_file = Path("/home/user/IMO25/test_option_b_full_solution_validation_high_42015fb_3.log")

print("="*80)
print("VERDICT COMPARISON: Run 2 (PASS) vs Run 3 (FAIL)")
print("="*80)
print()

run2_verdicts = extract_test_verdicts(run2_file)
run3_verdicts = extract_test_verdicts(run3_file)

for test_num in [1, 2]:
    print(f"{'='*80}")
    print(f"TEST {test_num}")
    print(f"{'='*80}")

    if test_num in run2_verdicts:
        v2 = run2_verdicts[test_num]
        print(f"\nRUN 2 (5/6 - PASS on Test {test_num}):")
        print(f"  Response length: {v2['response_length']} chars")
        print(f"  Is empty: {v2['is_empty']}")
        print(f"  Verdict: {v2['verdict']}")
    else:
        print(f"\nRUN 2: No verdict found for Test {test_num}")

    if test_num in run3_verdicts:
        v3 = run3_verdicts[test_num]
        print(f"\nRUN 3 (1/6 - FAIL on Test {test_num}):")
        print(f"  Response length: {v3['response_length']} chars")
        print(f"  Is empty: {v3['is_empty']}")
        print(f"  Verdict: {v3['verdict']}")
    else:
        print(f"\nRUN 3: No verdict found for Test {test_num}")

    print()

print("="*80)
print("ANALYSIS")
print("="*80)
print()

if 1 in run2_verdicts and 1 in run3_verdicts:
    if run2_verdicts[1]['is_empty'] and not run3_verdicts[1]['is_empty']:
        print("PATTERN IDENTIFIED:")
        print("  - Run 2 (PASS): LLM returned EMPTY response")
        print("  - Run 3 (FAIL): LLM returned detailed analysis")
        print()
        print("ROOT CAUSE: Empty responses bypass verification!")
        print("  When LLM returns empty content, the system asks:")
        print("  'Is the following statement saying the solution is complete?'")
        print("  Statement: [EMPTY]")
        print("  LLM responds: 'Yes' → Test PASSES")
        print()
        print("  When LLM returns detailed analysis:")
        print("  System parses the verdict and finds 'Justification Gap'")
        print("  → Test FAILS")
    elif not run2_verdicts[1]['is_empty'] and run3_verdicts[1]['is_empty']:
        print("PATTERN IDENTIFIED:")
        print("  - Run 2 (PASS): LLM returned detailed analysis")
        print("  - Run 3 (FAIL): LLM returned EMPTY response")
        print()
        print("This contradicts the empty response hypothesis.")
    else:
        print("PATTERN IDENTIFIED:")
        print("  Both runs returned similar response types")
        print("  The difference may be in the verdict content itself")
        print("  - Run 2 may have said 'solution is correct'")
        print("  - Run 3 may have found 'Justification Gaps'")

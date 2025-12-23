#!/usr/bin/env python3
"""
Detailed BFS analysis - which initial attempts led to success?
"""

import re
from pathlib import Path
from collections import defaultdict

def extract_bfs_attempts(log_path):
    """Extract detailed BFS attempt information."""

    attempts = []
    current_attempt = None

    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    for i, line in enumerate(lines):
        # BFS attempt marker
        if 'BFS: Initial attempt' in line:
            match = re.search(r'BFS: Initial attempt (\d+)/(\d+)', line)
            if match:
                if current_attempt:
                    attempts.append(current_attempt)

                current_attempt = {
                    'attempt_num': int(match.group(1)),
                    'total_attempts': int(match.group(2)),
                    'answer': None,
                    'verification_verdict': None,
                    'k_value': None
                }

        # Extract answer from this attempt
        if current_attempt and 'Final Answer:' in line:
            # Look for the answer in nearby lines
            for j in range(i, min(i+20, len(lines))):
                answer_match = re.search(r'Final Answer:\s*\\boxed\{([^}]+)\}', lines[j])
                if not answer_match:
                    answer_match = re.search(r'Final Answer:\s*(\{[^}]+\}|\d+)', lines[j])

                if answer_match:
                    current_attempt['answer'] = answer_match.group(1)
                    break

        # Extract verification verdict
        if current_attempt and 'Verification verdict:' in line:
            if 'CORRECT' in line or 'correct solution' in line.lower():
                current_attempt['verification_verdict'] = 'CORRECT'
            elif 'CRITICAL ERROR' in line:
                current_attempt['verification_verdict'] = 'CRITICAL_ERROR'
            elif 'JUSTIFICATION GAP' in line:
                current_attempt['verification_verdict'] = 'JUSTIFICATION_GAP'
            elif 'SUSPICIOUS' in line:
                current_attempt['verification_verdict'] = 'SUSPICIOUS'

    if current_attempt:
        attempts.append(current_attempt)

    return attempts

def analyze_bfs_logs():
    """Analyze all BFS logs for attempt-level insights."""

    log_dir = Path('/home/user/IMO25/bfs_no_answer_validation')
    log_files = sorted(log_dir.glob('bfs_run*.log'),
                      key=lambda x: int(re.search(r'run(\d+)_', x.name).group(1)))

    all_results = []

    for log_file in log_files:
        run_num = int(re.search(r'run(\d+)_', log_file.name).group(1))

        # Determine success
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            success = 'Found a correct solution' in content

        # Extract BFS attempts
        attempts = extract_bfs_attempts(log_file)

        all_results.append({
            'run': run_num,
            'success': success,
            'attempts': attempts
        })

    return all_results

def main():
    results = analyze_bfs_logs()

    print("\n" + "="*100)
    print("BFS ATTEMPT ANALYSIS - Which initial attempts led to success?")
    print("="*100)

    # Successful runs analysis
    successful_runs = [r for r in results if r['success']]
    failed_runs = [r for r in results if not r['success']]

    print(f"\nSUCCESSFUL RUNS: {len(successful_runs)}")
    print("-"*100)

    for result in successful_runs:
        run = result['run']
        print(f"\nRun {run}:")

        for attempt in result['attempts']:
            attempt_num = attempt['attempt_num']
            answer = attempt['answer'] or 'N/A'
            verdict = attempt['verification_verdict'] or 'UNKNOWN'

            print(f"  Attempt {attempt_num}/3:")
            print(f"    Answer: {answer}")
            print(f"    Verdict: {verdict}")
            print()

    print("\n" + "="*100)
    print("FAILED RUNS ANALYSIS")
    print("="*100)

    # Sample failed runs
    print(f"\nTotal failed runs: {len(failed_runs)}")
    print("\nSample failed run (Run 3):")

    for result in failed_runs[:1]:  # Just show first failed run
        run = result['run']
        print(f"\nRun {run}:")

        for attempt in result['attempts']:
            attempt_num = attempt['attempt_num']
            answer = attempt['answer'] or 'N/A'
            verdict = attempt['verification_verdict'] or 'UNKNOWN'

            print(f"  Attempt {attempt_num}/3:")
            print(f"    Answer: {answer}")
            print(f"    Verdict: {verdict}")

    # Statistics
    print("\n" + "="*100)
    print("BFS ATTEMPT STATISTICS")
    print("="*100)

    # Count verdicts across all attempts
    verdict_counts = defaultdict(int)
    answer_diversity = defaultdict(set)

    for result in results:
        run = result['run']
        for attempt in result['attempts']:
            verdict = attempt['verification_verdict'] or 'UNKNOWN'
            answer = attempt['answer'] or 'N/A'

            verdict_counts[verdict] += 1
            answer_diversity[run].add(answer)

    print("\nVerdict distribution across all BFS attempts:")
    for verdict, count in sorted(verdict_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {verdict}: {count}")

    print("\nAnswer diversity per run:")
    single_answer_runs = sum(1 for answers in answer_diversity.values() if len(answers) == 1)
    multi_answer_runs = sum(1 for answers in answer_diversity.values() if len(answers) > 1)

    print(f"  Runs with same answer in all 3 attempts: {single_answer_runs}")
    print(f"  Runs with different answers: {multi_answer_runs}")

    # Check if successful runs had diverse attempts
    print("\n" + "="*100)
    print("KEY INSIGHT: Did BFS diversity help?")
    print("="*100)

    for result in successful_runs:
        run = result['run']
        answers = set(a['answer'] for a in result['attempts'] if a['answer'])
        print(f"\nRun {run} (SUCCESS):")
        print(f"  Unique answers generated: {len(answers)}")
        print(f"  Answers: {answers}")

        # Check which attempt succeeded
        for attempt in result['attempts']:
            if attempt['verification_verdict'] == 'CORRECT':
                print(f"  *** SUCCESS at attempt {attempt['attempt_num']}/3 ***")

if __name__ == '__main__':
    main()

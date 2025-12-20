#!/usr/bin/env python3
"""
Analyze BFS baseline test results - extract execution metrics, verification patterns, and convergence analysis.
"""

import re
import json
import os
from datetime import datetime
from pathlib import Path

def parse_timestamp(line):
    """Extract timestamp from log line like '[2025-12-19 23:04:13]'"""
    match = re.search(r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]', line)
    if match:
        return datetime.strptime(match.group(1), '%Y-%m-%d %H:%M:%S')
    return None

def extract_answer(text):
    """Extract boxed answer from solution text"""
    matches = re.findall(r'\\boxed\{([^}]+)\}', text)
    if matches:
        return matches[-1]  # Return last boxed answer
    return None

def analyze_log_file(log_path):
    """Extract comprehensive metrics from a single log file"""

    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    lines = content.split('\n')

    metrics = {
        'file': os.path.basename(log_path),
        'start_time': None,
        'end_time': None,
        'duration_minutes': None,
        'iterations': [],
        'total_iterations': 0,
        'verification_results': [],
        'answers': [],
        'final_answer': None,
        'success': False,
        'config': {},
        'file_size_mb': os.path.getsize(log_path) / (1024 * 1024),
        'line_count': len(lines)
    }

    # Extract start timestamp
    for line in lines[:100]:
        ts = parse_timestamp(line)
        if ts and metrics['start_time'] is None:
            metrics['start_time'] = ts
            break

    # Extract end timestamp
    for line in reversed(lines[-100:]):
        ts = parse_timestamp(line)
        if ts:
            metrics['end_time'] = ts
            break

    if metrics['start_time'] and metrics['end_time']:
        duration = metrics['end_time'] - metrics['start_time']
        metrics['duration_minutes'] = duration.total_seconds() / 60

    # Extract config
    for line in lines[:200]:
        if 'solution reasoning:' in line.lower():
            match = re.search(r'solution reasoning:\s*(\w+)', line, re.IGNORECASE)
            if match:
                metrics['config']['solution_reasoning'] = match.group(1)
        if 'verification reasoning:' in line.lower():
            match = re.search(r'verification reasoning:\s*(\w+)', line, re.IGNORECASE)
            if match:
                metrics['config']['verification_reasoning'] = match.group(1)
        if 'self-improvement reasoning:' in line.lower():
            match = re.search(r'self-improvement reasoning:\s*(\w+)', line, re.IGNORECASE)
            if match:
                metrics['config']['self_improvement_reasoning'] = match.group(1)

    # Track iterations and verification
    current_iteration = None
    for i, line in enumerate(lines):
        # Iteration markers
        iter_match = re.search(r'Iteration\s+(\d+)', line, re.IGNORECASE)
        if iter_match:
            current_iteration = int(iter_match.group(1))
            if current_iteration not in [it['num'] for it in metrics['iterations']]:
                metrics['iterations'].append({
                    'num': current_iteration,
                    'line': i,
                    'verification': None,
                    'answer': None,
                    'score': None
                })

        # Verification results
        if 'Is verification good?' in line or 'verification good' in line.lower():
            # Look for verdict in next 50 lines
            for j in range(i, min(i+50, len(lines))):
                next_line = lines[j]
                if 'Critical Error' in next_line:
                    verdict = 'CRITICAL_ERROR'
                    break
                elif 'Justification Gap' in next_line:
                    verdict = 'JUSTIFICATION_GAP'
                    break
                elif 'verification is good' in next_line.lower() or 'verification good' in next_line.lower():
                    verdict = 'GOOD'
                    break
                elif 'Invalid' in next_line or 'invalid' in next_line.lower():
                    verdict = 'INVALID'
                    break
            else:
                verdict = 'UNKNOWN'

            metrics['verification_results'].append({
                'iteration': current_iteration,
                'verdict': verdict,
                'line': i
            })

            # Update iteration record
            for it in metrics['iterations']:
                if it['num'] == current_iteration:
                    it['verification'] = verdict

        # Scores
        score_match = re.search(r'\[SCORE\]\s+Iteration\s+\d+\s+score:\s*([-\d.]+)', line)
        if score_match:
            score = float(score_match.group(1))
            for it in metrics['iterations']:
                if it['num'] == current_iteration:
                    it['score'] = score

        # Extract answers from boxed format
        if '\\boxed{' in line:
            answer = extract_answer(line)
            if answer and current_iteration is not None:
                metrics['answers'].append({
                    'iteration': current_iteration,
                    'answer': answer
                })
                for it in metrics['iterations']:
                    if it['num'] == current_iteration:
                        it['answer'] = answer

    metrics['total_iterations'] = len(metrics['iterations'])

    # Determine final answer
    if metrics['answers']:
        metrics['final_answer'] = metrics['answers'][-1]['answer']

    # Check for success
    correct_answers = ['{0, 1, 3}', '{0,1,3}', '\\{0, 1, 3\\}', '\\{0,1,3\\}']
    if metrics['final_answer']:
        for correct in correct_answers:
            if correct.replace(' ', '') in metrics['final_answer'].replace(' ', ''):
                metrics['success'] = True
                break

    # Also check for SUCCESS marker in log
    if 'Found a correct solution' in content or 'SUCCESS' in content:
        metrics['success'] = True

    return metrics

def analyze_json_file(json_path):
    """Extract metrics from JSON memory file"""
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)

        return {
            'iterations': len(data.get('history', [])),
            'final_answer': data.get('final_answer'),
            'verification_scores': [h.get('verification_score') for h in data.get('history', [])],
            'success': data.get('success', False)
        }
    except Exception as e:
        return {'error': str(e)}

def main():
    results_dir = Path('/home/user/IMO25/bfs_baseline_results')
    log_files = sorted(results_dir.glob('bfs_run*_20251219_225957.log'))

    all_metrics = []

    print("=" * 100)
    print("BFS BASELINE RESULTS ANALYSIS")
    print("=" * 100)
    print()

    for log_file in log_files:
        print(f"Analyzing {log_file.name}...")
        metrics = analyze_log_file(str(log_file))

        # Also load JSON
        json_file = log_file.with_suffix('.json')
        if json_file.exists():
            json_metrics = analyze_json_file(str(json_file))
            metrics['json'] = json_metrics

        all_metrics.append(metrics)

    print()
    print("=" * 100)
    print("SUMMARY TABLE")
    print("=" * 100)
    print()

    # Print summary table
    print(f"{'Run':<6} {'Duration (min)':<15} {'Iterations':<12} {'Log Size (MB)':<15} {'Final Answer':<30} {'Status':<10}")
    print("-" * 100)

    total_duration = 0
    total_iterations = 0
    success_count = 0

    for i, m in enumerate(all_metrics, 1):
        duration = f"{m['duration_minutes']:.1f}" if m['duration_minutes'] else "N/A"
        iterations = m['total_iterations']
        size = f"{m['file_size_mb']:.2f}"
        answer = (m['final_answer'][:27] + '...') if m['final_answer'] and len(m['final_answer']) > 30 else (m['final_answer'] or 'N/A')
        status = 'SUCCESS' if m['success'] else 'FAIL'

        print(f"{i:<6} {duration:<15} {iterations:<12} {size:<15} {answer:<30} {status:<10}")

        if m['duration_minutes']:
            total_duration += m['duration_minutes']
        total_iterations += iterations
        if m['success']:
            success_count += 1

    print("-" * 100)
    avg_duration = total_duration / len(all_metrics) if all_metrics else 0
    avg_iterations = total_iterations / len(all_metrics) if all_metrics else 0
    print(f"{'AVG':<6} {avg_duration:<15.1f} {avg_iterations:<12.1f} {'':15} {'':30} {success_count}/{len(all_metrics)} success")
    print()

    # Detailed verification analysis
    print("=" * 100)
    print("VERIFICATION PATTERNS")
    print("=" * 100)
    print()

    for i, m in enumerate(all_metrics, 1):
        print(f"\nRun {i} - {m['file']}")
        print(f"  Config: sol={m['config'].get('solution_reasoning', 'N/A')}, "
              f"ver={m['config'].get('verification_reasoning', 'N/A')}, "
              f"imp={m['config'].get('self_improvement_reasoning', 'N/A')}")
        print(f"  Iterations: {m['total_iterations']}")
        print(f"  Verification results:")

        for vr in m['verification_results'][:10]:  # First 10
            print(f"    Iteration {vr['iteration']}: {vr['verdict']}")

        if len(m['verification_results']) > 10:
            print(f"    ... ({len(m['verification_results']) - 10} more)")

    # Convergence analysis
    print()
    print("=" * 100)
    print("CONVERGENCE ANALYSIS")
    print("=" * 100)
    print()

    for i, m in enumerate(all_metrics, 1):
        print(f"\nRun {i}:")

        # Find first GOOD verification
        first_good = None
        for vr in m['verification_results']:
            if vr['verdict'] == 'GOOD':
                first_good = vr['iteration']
                break

        if first_good is not None:
            print(f"  First GOOD verification: Iteration {first_good}")
        else:
            print(f"  No GOOD verification found (failed to converge)")

        # Answer changes
        unique_answers = list(set([a['answer'] for a in m['answers']]))
        print(f"  Unique answers: {len(unique_answers)}")
        for ans in unique_answers[:3]:  # First 3
            print(f"    - {ans}")

        # Check if stuck (same answer repeated)
        if len(m['answers']) > 5:
            last_5_answers = [a['answer'] for a in m['answers'][-5:]]
            if len(set(last_5_answers)) == 1:
                print(f"  STUCK: Last 5 iterations have same answer")

    # Save detailed results
    output_file = results_dir / 'analysis_results.json'
    with open(output_file, 'w') as f:
        json.dump(all_metrics, f, indent=2, default=str)

    print()
    print(f"\nDetailed results saved to: {output_file}")

if __name__ == '__main__':
    main()

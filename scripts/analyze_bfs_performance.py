#!/usr/bin/env python3
"""
Performance analysis script for BFS RLAC test runs.
Extracts metrics from log files for cost/duration/efficiency analysis.
"""

import re
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

def parse_timestamp(ts_str):
    """Parse timestamp like [2025-12-23 00:08:15]"""
    match = re.search(r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]', ts_str)
    if match:
        return datetime.strptime(match.group(1), '%Y-%m-%d %H:%M:%S')
    return None

def analyze_log_file(log_path):
    """Extract comprehensive metrics from a single log file."""

    metrics = {
        'run_number': None,
        'start_time': None,
        'end_time': None,
        'duration_minutes': None,
        'success': False,
        'total_iterations': 0,
        'bfs_attempts': 0,
        'rlac_rounds': 0,
        'api_calls': {
            'solution': 0,
            'self_improvement': 0,
            'verification': 0,
            'correction': 0,
            'critic': 0,
            'defense': 0
        },
        'reasoning_effort': {
            'solution': [],
            'verification': [],
            'self_improvement': [],
            'critic': []
        },
        'api_latency': {
            'solution': [],
            'verification': [],
            'self_improvement': [],
            'critic': []
        },
        'token_estimates': {
            'input_chars': 0,
            'output_chars': 0
        },
        'verdicts': defaultdict(int),
        'first_correct_iteration': None,
        'final_answer': None,
        'bfs_answers': []
    }

    # Extract run number from filename
    filename = Path(log_path).name
    match = re.search(r'bfs_run(\d+)_', filename)
    if match:
        metrics['run_number'] = int(match.group(1))

    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    current_request_type = None
    current_request_start = None

    for i, line in enumerate(lines):
        # Extract timestamps
        ts = parse_timestamp(line)
        if ts:
            if metrics['start_time'] is None:
                metrics['start_time'] = ts
            metrics['end_time'] = ts

        # Success detection
        if 'Found a correct solution' in line:
            metrics['success'] = True

        # BFS attempts
        if 'BFS: Initial attempt' in line:
            metrics['bfs_attempts'] += 1
            # Extract answer if present
            for j in range(i, min(i+100, len(lines))):
                if 'Final Answer:' in lines[j]:
                    answer_match = re.search(r'Final Answer:\s*(\{[^}]+\}|\d+)', lines[j])
                    if answer_match:
                        metrics['bfs_answers'].append(answer_match.group(1))
                    break

        # RLAC rounds
        if 'RLAC Round' in line:
            match = re.search(r'RLAC Round (\d+)', line)
            if match:
                round_num = int(match.group(1))
                metrics['rlac_rounds'] = max(metrics['rlac_rounds'], round_num + 1)

        # API call tracking
        if '[REQUEST]' in line:
            if 'Initial solution prompt' in line or 'Correction prompt' in line:
                current_request_type = 'solution'
                metrics['api_calls']['solution'] += 1
            elif 'Self-improvement prompt' in line:
                current_request_type = 'self_improvement'
                metrics['api_calls']['self_improvement'] += 1
            elif 'Verification prompt' in line:
                current_request_type = 'verification'
                metrics['api_calls']['verification'] += 1
            elif 'Adversarial critic' in line or 'ATTACK GENERATION' in line:
                current_request_type = 'critic'
                metrics['api_calls']['critic'] += 1
            elif 'Defense against attack' in line:
                current_request_type = 'defense'
                metrics['api_calls']['defense'] += 1

            current_request_start = ts

        # API response tracking (latency calculation)
        if '[RESPONSE]' in line and current_request_start and ts:
            latency = (ts - current_request_start).total_seconds()
            if current_request_type in metrics['api_latency']:
                metrics['api_latency'][current_request_type].append(latency)
            current_request_start = None

        # Reasoning effort detection
        if 'reasoning effort:' in line.lower() or 'Using medium reasoning' in line or 'Using low reasoning' in line:
            if 'solution' in line.lower() or 'Initial solution' in line:
                if 'medium' in line.lower():
                    metrics['reasoning_effort']['solution'].append('medium')
                elif 'low' in line.lower():
                    metrics['reasoning_effort']['solution'].append('low')
                elif 'high' in line.lower():
                    metrics['reasoning_effort']['solution'].append('high')
            elif 'verification' in line.lower():
                if 'high' in line.lower():
                    metrics['reasoning_effort']['verification'].append('high')
                elif 'medium' in line.lower():
                    metrics['reasoning_effort']['verification'].append('medium')
            elif 'self-improvement' in line.lower():
                if 'medium' in line.lower():
                    metrics['reasoning_effort']['self_improvement'].append('medium')
                elif 'high' in line.lower():
                    metrics['reasoning_effort']['self_improvement'].append('high')
            elif 'critic' in line.lower():
                if 'medium' in line.lower():
                    metrics['reasoning_effort']['critic'].append('medium')
                elif 'low' in line.lower():
                    metrics['reasoning_effort']['critic'].append('low')

        # Token estimation from payload sizes
        if 'Payload size:' in line:
            match = re.search(r'Payload size: (\d+) characters', line)
            if match:
                metrics['token_estimates']['input_chars'] += int(match.group(1))

        if 'Content length:' in line:
            match = re.search(r'Content length: (\d+) characters', line)
            if match:
                metrics['token_estimates']['output_chars'] += int(match.group(1))

        # Verdict tracking
        if 'VERDICT:' in line:
            for verdict in ['ROBUST', 'BROKEN', 'SUSPICIOUS', 'CRITICAL ERROR', 'CORRECT']:
                if verdict in line:
                    metrics['verdicts'][verdict] += 1
                    if verdict == 'CORRECT' and metrics['first_correct_iteration'] is None:
                        # Count iterations so far
                        iterations = metrics['bfs_attempts'] + metrics['rlac_rounds']
                        metrics['first_correct_iteration'] = iterations

        # Final answer extraction
        if 'Final Answer:' in line and i > len(lines) - 100:  # Near end of file
            answer_match = re.search(r'Final Answer:\s*(\{[^}]+\}|\d+)', line)
            if answer_match:
                metrics['final_answer'] = answer_match.group(1)

    # Calculate duration
    if metrics['start_time'] and metrics['end_time']:
        duration = (metrics['end_time'] - metrics['start_time']).total_seconds() / 60
        metrics['duration_minutes'] = round(duration, 2)

    # Calculate total iterations
    metrics['total_iterations'] = metrics['bfs_attempts'] + metrics['rlac_rounds']

    return metrics

def estimate_costs(metrics):
    """Estimate API costs based on token usage and reasoning effort."""

    # GPT-OSS pricing estimates (rough approximations)
    # Characters to tokens: ~4 chars per token
    # Pricing tiers (hypothetical, adjust based on actual pricing):
    # - Low reasoning: $0.50 per 1M tokens
    # - Medium reasoning: $2.00 per 1M tokens
    # - High reasoning: $8.00 per 1M tokens

    pricing = {
        'low': 0.50 / 1_000_000,
        'medium': 2.00 / 1_000_000,
        'high': 8.00 / 1_000_000
    }

    input_tokens = metrics['token_estimates']['input_chars'] / 4
    output_tokens = metrics['token_estimates']['output_chars'] / 4

    # Estimate cost by reasoning effort
    cost_breakdown = {
        'solution': 0,
        'verification': 0,
        'self_improvement': 0,
        'critic': 0
    }

    # Solution calls (mostly medium)
    solution_tokens = (input_tokens + output_tokens) * (metrics['api_calls']['solution'] / max(sum(metrics['api_calls'].values()), 1))
    cost_breakdown['solution'] = solution_tokens * pricing.get('medium', 0)

    # Verification calls (high reasoning)
    verification_tokens = (input_tokens + output_tokens) * (metrics['api_calls']['verification'] / max(sum(metrics['api_calls'].values()), 1))
    cost_breakdown['verification'] = verification_tokens * pricing.get('high', 0)

    # Self-improvement calls (medium)
    si_tokens = (input_tokens + output_tokens) * (metrics['api_calls']['self_improvement'] / max(sum(metrics['api_calls'].values()), 1))
    cost_breakdown['self_improvement'] = si_tokens * pricing.get('medium', 0)

    # Critic calls (medium/low)
    critic_tokens = (input_tokens + output_tokens) * (metrics['api_calls']['critic'] / max(sum(metrics['api_calls'].values()), 1))
    cost_breakdown['critic'] = critic_tokens * pricing.get('medium', 0)

    total_cost = sum(cost_breakdown.values())

    return {
        'total_cost': round(total_cost, 2),
        'breakdown': {k: round(v, 2) for k, v in cost_breakdown.items()},
        'total_tokens': int(input_tokens + output_tokens),
        'input_tokens': int(input_tokens),
        'output_tokens': int(output_tokens)
    }

def main():
    log_dir = Path('/home/user/IMO25/bfs_no_answer_validation')
    log_files = sorted(log_dir.glob('bfs_run*.log'), key=lambda x: int(re.search(r'run(\d+)_', x.name).group(1)))

    all_metrics = []

    print("Analyzing log files...")
    for log_file in log_files:
        print(f"  Processing {log_file.name}...")
        metrics = analyze_log_file(log_file)
        costs = estimate_costs(metrics)
        metrics['costs'] = costs
        all_metrics.append(metrics)

    # Generate summary statistics
    successful_runs = [m for m in all_metrics if m['success']]
    failed_runs = [m for m in all_metrics if not m['success']]

    print("\n" + "="*80)
    print("PERFORMANCE ANALYSIS SUMMARY")
    print("="*80)

    print(f"\nTotal runs: {len(all_metrics)}")
    print(f"Successful: {len(successful_runs)} ({len(successful_runs)/len(all_metrics)*100:.1f}%)")
    print(f"Failed: {len(failed_runs)} ({len(failed_runs)/len(all_metrics)*100:.1f}%)")

    # Detailed table
    print("\n" + "="*80)
    print("DETAILED RUN STATISTICS")
    print("="*80)
    print(f"{'Run':<4} {'Success':<8} {'Iters':<6} {'Duration':<10} {'Cost':<8} {'BFS':<4} {'RLAC':<5} {'Verif':<6} {'Final Answer':<15}")
    print("-"*80)

    for m in all_metrics:
        run_num = m['run_number'] or '?'
        success = 'YES' if m['success'] else 'NO'
        iters = m['total_iterations']
        duration = f"{m['duration_minutes']:.1f}m" if m['duration_minutes'] else 'N/A'
        cost = f"${m['costs']['total_cost']:.2f}" if m['costs']['total_cost'] > 0 else 'N/A'
        bfs = m['bfs_attempts']
        rlac = m['rlac_rounds']
        verif = m['api_calls']['verification']
        answer = m['final_answer'] or 'N/A'

        print(f"{run_num:<4} {success:<8} {iters:<6} {duration:<10} {cost:<8} {bfs:<4} {rlac:<5} {verif:<6} {answer:<15}")

    # Aggregate statistics
    print("\n" + "="*80)
    print("AGGREGATE STATISTICS")
    print("="*80)

    if successful_runs:
        avg_duration_success = sum(m['duration_minutes'] for m in successful_runs if m['duration_minutes']) / len(successful_runs)
        avg_cost_success = sum(m['costs']['total_cost'] for m in successful_runs) / len(successful_runs)
        avg_iterations_success = sum(m['total_iterations'] for m in successful_runs) / len(successful_runs)

        print(f"\nSuccessful runs:")
        print(f"  Average duration: {avg_duration_success:.1f} minutes")
        print(f"  Average cost: ${avg_cost_success:.2f}")
        print(f"  Average iterations: {avg_iterations_success:.1f}")
        print(f"  Cost per success: ${avg_cost_success:.2f}")

    if failed_runs:
        avg_duration_failed = sum(m['duration_minutes'] for m in failed_runs if m['duration_minutes']) / len(failed_runs)
        avg_cost_failed = sum(m['costs']['total_cost'] for m in failed_runs) / len(failed_runs)
        avg_iterations_failed = sum(m['total_iterations'] for m in failed_runs) / len(failed_runs)

        print(f"\nFailed runs:")
        print(f"  Average duration: {avg_duration_failed:.1f} minutes")
        print(f"  Average cost: ${avg_cost_failed:.2f}")
        print(f"  Average iterations: {avg_iterations_failed:.1f}")

    # Overall averages
    avg_duration_all = sum(m['duration_minutes'] for m in all_metrics if m['duration_minutes']) / len(all_metrics)
    avg_cost_all = sum(m['costs']['total_cost'] for m in all_metrics) / len(all_metrics)
    total_cost = sum(m['costs']['total_cost'] for m in all_metrics)

    print(f"\nOverall (all runs):")
    print(f"  Average duration: {avg_duration_all:.1f} minutes")
    print(f"  Average cost per run: ${avg_cost_all:.2f}")
    print(f"  Total cost (N=12): ${total_cost:.2f}")

    if successful_runs:
        cost_per_success = total_cost / len(successful_runs)
        print(f"  Cost per successful solution: ${cost_per_success:.2f}")

    # N=100 projections
    print("\n" + "="*80)
    print("N=100 PROJECTIONS")
    print("="*80)

    success_rate = len(successful_runs) / len(all_metrics)
    expected_successes = 100 * success_rate
    total_cost_n100 = avg_cost_all * 100

    print(f"\nExpected success rate: {success_rate*100:.1f}%")
    print(f"Expected successes in N=100: {expected_successes:.1f}")
    print(f"Total cost for N=100: ${total_cost_n100:.2f}")

    if successful_runs:
        cost_per_success_n100 = total_cost_n100 / expected_successes if expected_successes > 0 else float('inf')
        print(f"Cost per successful solution (N=100): ${cost_per_success_n100:.2f}")

    # Duration projections with MAX_PARALLEL=12
    with_parallel = avg_duration_all * (100 / 12)
    print(f"\nDuration projections:")
    print(f"  Sequential (no parallelism): {avg_duration_all * 100:.0f} minutes ({avg_duration_all * 100 / 60:.1f} hours)")
    print(f"  With MAX_PARALLEL=12: {with_parallel:.0f} minutes ({with_parallel / 60:.1f} hours)")

    # API call analysis
    print("\n" + "="*80)
    print("API CALL ANALYSIS")
    print("="*80)

    total_api_calls = {
        'solution': sum(m['api_calls']['solution'] for m in all_metrics),
        'verification': sum(m['api_calls']['verification'] for m in all_metrics),
        'self_improvement': sum(m['api_calls']['self_improvement'] for m in all_metrics),
        'critic': sum(m['api_calls']['critic'] for m in all_metrics),
        'defense': sum(m['api_calls']['defense'] for m in all_metrics)
    }

    print(f"\nTotal API calls across all runs:")
    for call_type, count in total_api_calls.items():
        avg_per_run = count / len(all_metrics)
        print(f"  {call_type.capitalize()}: {count} total ({avg_per_run:.1f} per run)")

    # Latency analysis
    print("\n" + "="*80)
    print("API LATENCY ANALYSIS")
    print("="*80)

    for call_type in ['solution', 'verification', 'self_improvement', 'critic']:
        all_latencies = []
        for m in all_metrics:
            all_latencies.extend(m['api_latency'].get(call_type, []))

        if all_latencies:
            avg_latency = sum(all_latencies) / len(all_latencies)
            max_latency = max(all_latencies)
            slow_calls = len([l for l in all_latencies if l > 30])

            print(f"\n{call_type.capitalize()}:")
            print(f"  Average latency: {avg_latency:.1f}s")
            print(f"  Max latency: {max_latency:.1f}s")
            print(f"  Slow calls (>30s): {slow_calls} ({slow_calls/len(all_latencies)*100:.1f}%)")

    # Save detailed results to JSON
    output_file = log_dir / 'performance_analysis.json'
    with open(output_file, 'w') as f:
        json.dump({
            'summary': {
                'total_runs': len(all_metrics),
                'successful_runs': len(successful_runs),
                'failed_runs': len(failed_runs),
                'success_rate': success_rate,
                'avg_cost_per_run': avg_cost_all,
                'avg_duration_minutes': avg_duration_all,
                'total_cost': total_cost
            },
            'runs': all_metrics,
            'n100_projections': {
                'expected_successes': expected_successes,
                'total_cost': total_cost_n100,
                'duration_parallel_12': with_parallel
            }
        }, f, indent=2, default=str)

    print(f"\n\nDetailed results saved to: {output_file}")

if __name__ == '__main__':
    main()

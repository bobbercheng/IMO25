#!/usr/bin/env python3
"""Quick timing analysis for BFS baseline runs."""

import re
import glob
from datetime import datetime
from pathlib import Path

log_files = sorted(glob.glob("/home/user/IMO25/bfs_baseline_results/bfs_run*_20251221_111204.log"))

print(f"Analyzing {len(log_files)} log files...\n")
print(f"{'Run':<8} {'Start':<20} {'End':<20} {'Duration (min)':<15} {'Iterations':<12} {'Success':<8}")
print("=" * 95)

total_duration = 0
success_count = 0
iteration_list = []

for log_file in log_files:
    run_num = Path(log_file).stem.split('_')[1].replace('run', '')

    with open(log_file, 'r') as f:
        lines = f.readlines()

    # Find first and last timestamp
    start_time = None
    end_time = None

    for line in lines[:100]:
        match = re.match(r'^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]', line)
        if match:
            start_time = match.group(1)
            break

    for line in reversed(lines[-100:]):
        match = re.match(r'^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]', line)
        if match:
            end_time = match.group(1)
            break

    # Calculate duration
    if start_time and end_time:
        start_dt = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
        end_dt = datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')
        duration_min = (end_dt - start_dt).total_seconds() / 60
        total_duration += duration_min
    else:
        duration_min = 0

    # Count iterations
    iteration_matches = re.findall(r'Iteration (\d+)', ''.join(lines))
    iterations = max([int(i) for i in iteration_matches]) if iteration_matches else 0
    iteration_list.append(iterations)

    # Check success
    success = "YES" if "verification good" in ''.join(lines) else "NO"
    if success == "YES":
        success_count += 1

    print(f"Run {run_num:<4} {start_time:<20} {end_time:<20} {duration_min:<15.1f} {iterations:<12} {success:<8}")

print("=" * 95)
print(f"\nSUMMARY:")
print(f"  Total runs: {len(log_files)}")
print(f"  Success rate: {success_count}/{len(log_files)} ({100*success_count/len(log_files):.0f}%)")
print(f"  Average duration: {total_duration/len(log_files):.1f} minutes ({total_duration/len(log_files)/60:.1f} hours)")
print(f"  Total duration: {total_duration:.1f} minutes ({total_duration/60:.1f} hours)")
print(f"  Average iterations: {sum(iteration_list)/len(iteration_list):.1f}")
print(f"  Max iterations: {max(iteration_list)}")
print(f"  Min iterations: {min(iteration_list)}")
print(f"\nEXPECTED vs ACTUAL:")
print(f"  Expected duration: 20-30 min per run")
print(f"  Actual duration: {total_duration/len(log_files):.1f} min per run")
print(f"  Slowdown: {(total_duration/len(log_files))/25:.1f}x slower than expected")
print(f"\n  Expected total (12 runs @ 25 min): 300 min (5 hours)")
print(f"  Actual total: {total_duration:.1f} min ({total_duration/60:.1f} hours)")
print(f"  Overhead: {total_duration - 300:.1f} min ({(total_duration - 300)/60:.1f} hours)")

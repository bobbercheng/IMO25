#!/usr/bin/env python3
"""Analyze BFS phase timing and iteration breakdown."""

import re
import glob
from datetime import datetime
from pathlib import Path

log_files = sorted(glob.glob("/home/user/IMO25/bfs_baseline_results/bfs_run*_20251221_111204.log"))

print(f"Analyzing BFS phase timing for {len(log_files)} runs...\n")

for log_file in log_files[:3]:  # Analyze first 3 runs in detail
    run_num = Path(log_file).stem.split('_')[1].replace('run', '')
    print(f"{'='*80}")
    print(f"RUN {run_num}")
    print(f"{'='*80}")

    with open(log_file, 'r') as f:
        lines = f.readlines()

    # Find BFS phase start/end
    bfs_start = None
    bfs_end = None
    iteration_start = None

    bfs_attempts = []
    iteration_times = []
    verification_times = []

    for i, line in enumerate(lines):
        # BFS phase
        if 'BFS: Generating' in line:
            match = re.match(r'^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]', line)
            if match:
                bfs_start = datetime.strptime(match.group(1), '%Y-%m-%d %H:%M:%S')

        if 'BFS: Initial attempt' in line:
            match = re.match(r'^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]', line)
            if match:
                bfs_attempts.append(datetime.strptime(match.group(1), '%Y-%m-%d %H:%M:%S'))

        if 'BFS: Completed' in line or 'BFS: Early stop' in line or ('Iteration 0' in line and bfs_start):
            match = re.match(r'^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]', line)
            if match:
                bfs_end = datetime.strptime(match.group(1), '%Y-%m-%d %H:%M:%S')
                break

        # Iteration phase start
        if 'Iteration 0' in line and not iteration_start:
            match = re.match(r'^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]', line)
            if match:
                iteration_start = datetime.strptime(match.group(1), '%Y-%m-%d %H:%M:%S')
                if not bfs_end:
                    bfs_end = iteration_start

    # Extract iteration and verification timestamps
    current_iteration = None
    iteration_data = {}

    for line in lines:
        # Iteration start
        match_iter = re.search(r'Iteration (\d+)', line)
        if match_iter:
            iter_num = int(match_iter.group(1))
            match_time = re.match(r'^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]', line)
            if match_time and iter_num not in iteration_data:
                iteration_data[iter_num] = {
                    'start': datetime.strptime(match_time.group(1), '%Y-%m-%d %H:%M:%S'),
                    'verify_start': None,
                    'verify_end': None
                }
                current_iteration = iter_num

        # Verification start
        if 'Start verification' in line and current_iteration is not None:
            match_time = re.match(r'^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]', line)
            if match_time:
                iteration_data[current_iteration]['verify_start'] = datetime.strptime(match_time.group(1), '%Y-%m-%d %H:%M:%S')

        # Verification end
        if 'verification good' in line or 'verification bad' in line:
            match_time = re.match(r'^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]', line)
            if match_time and current_iteration is not None:
                if iteration_data[current_iteration]['verify_end'] is None:
                    iteration_data[current_iteration]['verify_end'] = datetime.strptime(match_time.group(1), '%Y-%m-%d %H:%M:%S')

    # Calculate durations
    if bfs_start and bfs_end:
        bfs_duration = (bfs_end - bfs_start).total_seconds() / 60
        print(f"\nBFS PHASE:")
        print(f"  Start: {bfs_start.strftime('%H:%M:%S')}")
        print(f"  End: {bfs_end.strftime('%H:%M:%S')}")
        print(f"  Duration: {bfs_duration:.1f} minutes")
        print(f"  Attempts: {len(bfs_attempts)}")
        if len(bfs_attempts) >= 2:
            for i in range(1, len(bfs_attempts)):
                attempt_dur = (bfs_attempts[i] - bfs_attempts[i-1]).total_seconds() / 60
                print(f"    Attempt {i}: {attempt_dur:.1f} min")

    print(f"\nITERATION PHASE:")
    total_iter_time = 0
    total_verify_time = 0

    for iter_num in sorted(iteration_data.keys()):
        data = iteration_data[iter_num]

        # Find next iteration or end
        next_iter = iter_num + 1
        if next_iter in iteration_data:
            iter_end = iteration_data[next_iter]['start']
        else:
            # Use last timestamp
            for line in reversed(lines[-50:]):
                match = re.match(r'^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]', line)
                if match:
                    iter_end = datetime.strptime(match.group(1), '%Y-%m-%d %H:%M:%S')
                    break

        iter_duration = (iter_end - data['start']).total_seconds() / 60
        total_iter_time += iter_duration

        verify_duration = 0
        if data['verify_start'] and data['verify_end']:
            verify_duration = (data['verify_end'] - data['verify_start']).total_seconds() / 60
            total_verify_time += verify_duration

        print(f"  Iteration {iter_num}:")
        print(f"    Total: {iter_duration:.1f} min")
        if verify_duration > 0:
            print(f"    Verification: {verify_duration:.1f} min ({100*verify_duration/iter_duration:.0f}%)")
            print(f"    Generation: {iter_duration - verify_duration:.1f} min ({100*(iter_duration-verify_duration)/iter_duration:.0f}%)")

    if total_iter_time > 0:
        print(f"\n  TOTAL ITERATION PHASE: {total_iter_time:.1f} min")
        print(f"    Verification time: {total_verify_time:.1f} min ({100*total_verify_time/total_iter_time:.0f}%)")
        print(f"    Generation time: {total_iter_time - total_verify_time:.1f} min ({100*(total_iter_time-total_verify_time)/total_iter_time:.0f}%)")

    print()

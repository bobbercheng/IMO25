#!/usr/bin/env python3
"""
Extract errors from MCTS log for Phase 2.1 analysis
"""

import sys
import os
import json

# Import extraction functions from stage1_error_analysis
sys.path.insert(0, os.path.dirname(__file__))
from stage1_error_analysis import extract_errors_from_log

def main():
    log_file = 'run_log_gpt_oss/mcts_phase1_validation_p1.log'

    print("\n" + "="*80)
    print("PHASE 2.1: EXTRACT ERRORS FROM MCTS LOG")
    print("="*80 + "\n")

    # Extract errors from MCTS log
    errors = extract_errors_from_log(log_file)

    # Calculate totals
    total = sum(len(v) for v in errors.values())

    print(f"\n[MCTS EXTRACTION COMPLETE]")
    print(f"  Critical Errors: {len(errors['critical_errors'])}")
    print(f"  Justification Gaps: {len(errors['justification_gaps'])}")
    print(f"  Construction Failures: {len(errors['construction_failures'])}")
    print(f"  Other Errors: {len(errors['other_errors'])}")
    print(f"  TOTAL: {total}")

    # Save to JSON for later merging
    output_file = 'mcts_errors.json'
    with open(output_file, 'w') as f:
        json.dump({
            'source': 'MCTS',
            'log_file': log_file,
            'error_counts': {
                'critical_errors': len(errors['critical_errors']),
                'justification_gaps': len(errors['justification_gaps']),
                'construction_failures': len(errors['construction_failures']),
                'other_errors': len(errors['other_errors']),
                'total': total
            },
            'errors': errors
        }, f, indent=2)

    print(f"\n✅ Saved to {output_file}")

    # Compare with original BFS extraction (from stage1_results.json)
    if os.path.exists('stage1_results.json'):
        with open('stage1_results.json', 'r') as f:
            stage1 = json.load(f)
            bfs_total = stage1['error_extraction']['total_errors']
            print(f"\n[COMPARISON]")
            print(f"  BFS (original): {bfs_total} errors")
            print(f"  MCTS (new): {total} errors")
            print(f"  Combined: {bfs_total + total} errors")
            print(f"  Increase: +{total/bfs_total*100:.1f}%")

    return 0

if __name__ == '__main__':
    sys.exit(main())

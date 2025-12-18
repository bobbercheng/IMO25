#!/usr/bin/env python3
"""
Production Phase 1: Extract high-impact BFS errors for template application

Goal: Find ~15-20 critical errors that:
1. Blocked the agent from finding correct solutions
2. Appear in failed iterations (not in successful ones)
3. Are diverse across the 7 error categories
4. Can be fixed with our prescriptive templates
"""

import os
import sys
import json
import re
from collections import defaultdict

sys.path.insert(0, os.path.dirname(__file__))
from stage1_error_analysis import extract_errors_from_log

def analyze_log_for_success(log_file):
    """
    Analyze log to identify successful vs. failed iterations.
    Returns: (success_found, total_iterations, errors_by_iteration)
    """
    with open(log_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Check for success markers
    success_markers = [
        "Found a correct solution",
        "SUCCESS",
        "solution is correct",
        "Verification: PASS"
    ]

    success_found = any(marker.lower() in content.lower() for marker in success_markers)

    # Extract iteration count
    iteration_pattern = r'Iteration (\d+)'
    iterations = re.findall(iteration_pattern, content)
    total_iterations = max([int(i) for i in iterations]) if iterations else 0

    # Extract verification blocks per iteration
    verify_pattern = r'Iteration (\d+).*?>>>>>>> Verification results:\s*"(.+?)"'
    iter_verifications = re.findall(verify_pattern, content, re.DOTALL)

    errors_by_iteration = defaultdict(list)
    for iter_num, verification in iter_verifications:
        # Parse errors from verification
        if "Critical Error" in verification:
            error_match = re.search(r'\*\*Critical Error\*\*[:\-–—]\s*(.+?)(?=\n\*\*|###|\Z)',
                                   verification, re.DOTALL | re.IGNORECASE)
            if error_match:
                errors_by_iteration[int(iter_num)].append({
                    'type': 'critical',
                    'text': error_match.group(1).strip()[:300]
                })

        if "Justification Gap" in verification:
            gap_match = re.search(r'\*\*Justification Gap\*\*[:\-–—]\s*(.+?)(?=\n\*\*|###|\Z)',
                                 verification, re.DOTALL | re.IGNORECASE)
            if gap_match:
                errors_by_iteration[int(iter_num)].append({
                    'type': 'justification_gap',
                    'text': gap_match.group(1).strip()[:300]
                })

    return success_found, total_iterations, errors_by_iteration

def categorize_error(error_text):
    """
    Simple keyword-based categorization using our 7 templates.
    """
    error_lower = error_text.lower()

    categories = {
        "Integer/Denominator Reasoning": ["integer", "lattice", "divisibility", "denominator", "gcd", "rational", "coprime"],
        "Faulty Construction": ["construction", "cover", "satisfy", "counterexample", "violate", "fail", "not all"],
        "Missing Justification": ["without proof", "unjustified", "claimed", "missing", "gap", "not shown", "not proven"],
        "Quantitative Bounds": ["bound", "count", "inequality", "estimate", "maximum", "minimum", "at least", "at most"],
        "Logical Deduction": ["converse", "circular", "non sequitur", "implication", "assumes", "invalid", "does not follow"],
        "Case Analysis": ["case", "incomplete", "missing", "overlapping", "boundary", "edge", "scenario"],
        "Coverage Counting": ["inclusion-exclusion", "overlap", "distinct", "double-count", "unique"]
    }

    matches = []
    for category, keywords in categories.items():
        if any(keyword in error_lower for keyword in keywords):
            matches.append(category)

    return matches[0] if matches else "Uncategorized"

def select_high_impact_errors(errors_by_iteration, total_iterations, success_found):
    """
    Select high-impact errors for template application.

    Priority:
    1. Errors that persist across multiple iterations
    2. Errors from the final (failed) iteration
    3. Diverse across categories
    """
    # Count error frequency
    error_freq = defaultdict(int)
    error_details = {}

    for iter_num, errors in errors_by_iteration.items():
        for error in errors:
            key = error['text'][:100]  # Use first 100 chars as key
            error_freq[key] += 1
            if key not in error_details:
                error_details[key] = {
                    'full_text': error['text'],
                    'type': error['type'],
                    'first_iteration': iter_num,
                    'category': categorize_error(error['text'])
                }
            error_details[key]['last_iteration'] = iter_num

    # Score errors by impact
    scored_errors = []
    for key, freq in error_freq.items():
        details = error_details[key]

        # Impact score = frequency * recency * severity
        recency = details['last_iteration'] / total_iterations if total_iterations > 0 else 1
        severity = 2 if details['type'] == 'critical' else 1

        impact_score = freq * recency * severity

        scored_errors.append({
            'text': details['full_text'],
            'type': details['type'],
            'category': details['category'],
            'frequency': freq,
            'first_iter': details['first_iteration'],
            'last_iter': details['last_iteration'],
            'impact_score': impact_score
        })

    # Sort by impact score
    scored_errors.sort(key=lambda x: x['impact_score'], reverse=True)

    return scored_errors

def main():
    print("\n" + "="*80)
    print("PRODUCTION PHASE 1: EXTRACT HIGH-IMPACT BFS ERRORS")
    print("="*80 + "\n")

    # Use the main BFS revalidation log
    log_file = 'run_log_gpt_oss/bfs_medium_fresh_test.log'

    print(f"[ANALYZE] Analyzing {log_file}...")
    success_found, total_iterations, errors_by_iteration = analyze_log_for_success(log_file)

    print(f"[ANALYZE] Results:")
    print(f"  Success found: {success_found}")
    print(f"  Total iterations: {total_iterations}")
    print(f"  Iterations with errors: {len(errors_by_iteration)}")

    # Select high-impact errors
    print(f"\n[SELECT] Selecting high-impact errors...")
    high_impact_errors = select_high_impact_errors(errors_by_iteration, total_iterations, success_found)

    print(f"[SELECT] Found {len(high_impact_errors)} unique errors")

    # Select top 20 for template application
    selected_errors = high_impact_errors[:20]

    # Ensure diversity across categories
    category_counts = defaultdict(int)
    diverse_selection = []

    # First pass: include at least 2 from each category
    for error in selected_errors:
        cat = error['category']
        if category_counts[cat] < 3:
            diverse_selection.append(error)
            category_counts[cat] += 1

    # Second pass: fill remaining slots
    for error in selected_errors:
        if error not in diverse_selection and len(diverse_selection) < 20:
            diverse_selection.append(error)

    print(f"\n[DIVERSITY] Selected {len(diverse_selection)} diverse errors:")
    for cat, count in sorted(category_counts.items()):
        print(f"  {cat}: {count}")

    # Display selected errors
    print(f"\n{'='*80}")
    print("SELECTED HIGH-IMPACT ERRORS")
    print(f"{'='*80}\n")

    for i, error in enumerate(diverse_selection, 1):
        print(f"\n{'='*80}")
        print(f"ERROR #{i}")
        print(f"{'='*80}")
        print(f"Category: {error['category']}")
        print(f"Type: {error['type']}")
        print(f"Frequency: {error['frequency']} iterations")
        print(f"Iterations: {error['first_iter']} → {error['last_iter']}")
        print(f"Impact Score: {error['impact_score']:.2f}")
        print(f"\nError Text:")
        print(error['text'])

    # Save results
    output = {
        'log_file': log_file,
        'success_found': success_found,
        'total_iterations': total_iterations,
        'total_unique_errors': len(high_impact_errors),
        'selected_for_application': len(diverse_selection),
        'category_distribution': dict(category_counts),
        'errors': diverse_selection
    }

    with open('production_phase1_selected_errors.json', 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\n✅ Results saved to production_phase1_selected_errors.json")

    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}\n")
    print(f"Log analyzed: {log_file}")
    print(f"Success found: {success_found}")
    print(f"Total iterations: {total_iterations}")
    print(f"Unique errors: {len(high_impact_errors)}")
    print(f"Selected for template application: {len(diverse_selection)}")
    print(f"\nCategory distribution:")
    for cat, count in sorted(category_counts.items()):
        print(f"  {cat}: {count}")

    return 0

if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
"""
Extract all Iteration 0 solutions from Run 8 to see what answers were claimed.
These are the solutions that passed initial verification (corrects=1, errors=0).
"""

import re
import json
from typing import List, Dict, Any

def extract_answer_detailed(solution_text: str) -> Dict[str, Any]:
    """Extract claimed answer with detailed parsing."""

    result = {
        'raw_answer': None,
        'parsed_set': None,
        'answer_type': None,
        'includes_k2': None,
        'matches_truth': None
    }

    # Ground truth for comparison
    truth = {0, 1, 3}

    # Pattern 1: \boxed{...}
    boxed_match = re.search(r'\\boxed\{([^}]+)\}', solution_text)
    if boxed_match:
        result['raw_answer'] = boxed_match.group(1).strip()

    # Pattern 2: "all nonnegative integers k" or "k ∈ {...}"
    # Look for the final answer section
    answer_section = re.search(r'(?:Final answer|answer is|conclude that|Therefore,?|Thus,?).*?k\s*(?:=|∈)\s*([^\n\.]+)',
                               solution_text, re.IGNORECASE | re.DOTALL)
    if answer_section:
        answer_expr = answer_section.group(1).strip()
        if not result['raw_answer']:
            result['raw_answer'] = answer_expr

    # Pattern 3: Extract from boxed or raw answer
    if result['raw_answer']:
        answer_str = result['raw_answer']

        # Case 1: Explicit set {0, 1, 3}
        explicit_match = re.search(r'\{(\d+(?:\s*,\s*\d+)*)\}', answer_str)
        if explicit_match:
            nums_str = explicit_match.group(1)
            nums = [int(n.strip()) for n in nums_str.split(',')]
            result['parsed_set'] = set(nums)
            result['answer_type'] = 'EXPLICIT_SET'

        # Case 2: Range {0,1,...,n-2} or {0,1,2,...,n-2}
        elif re.search(r'\{0\s*,\s*1.*?n\s*-\s*2\}', answer_str):
            result['answer_type'] = 'RANGE_0_TO_N_MINUS_2'
            result['parsed_set'] = 'PARAMETRIC'
            result['includes_k2'] = True  # This range includes k=2

        # Case 3: {0,1,...,n}
        elif re.search(r'\{0\s*,\s*1.*?n\}', answer_str):
            result['answer_type'] = 'RANGE_0_TO_N'
            result['parsed_set'] = 'PARAMETRIC'
            result['includes_k2'] = True

        # Case 4: {0, 1} only
        elif re.search(r'\{0\s*,\s*1\}', answer_str) and 'dot' not in answer_str.lower():
            result['parsed_set'] = {0, 1}
            result['answer_type'] = 'EXPLICIT_SET'

        # Case 5: k = 0 only
        elif re.search(r'k\s*=\s*0\s*(?:only|$)', answer_str):
            result['parsed_set'] = {0}
            result['answer_type'] = 'EXPLICIT_SET'

        # Check if includes k=2
        if result['parsed_set'] == 'PARAMETRIC':
            # Already set above
            pass
        elif result['parsed_set'] and isinstance(result['parsed_set'], set):
            result['includes_k2'] = 2 in result['parsed_set']

        # Compare to truth
        if result['parsed_set'] == truth:
            result['matches_truth'] = 'CORRECT'
        elif isinstance(result['parsed_set'], set):
            if result['parsed_set'].issubset(truth):
                result['matches_truth'] = 'INCOMPLETE'
            elif truth.issubset(result['parsed_set']):
                result['matches_truth'] = 'OVERGENERALIZED'
            else:
                result['matches_truth'] = 'WRONG'
        elif result['parsed_set'] == 'PARAMETRIC':
            result['matches_truth'] = 'WRONG' if result['includes_k2'] else 'UNKNOWN'

    return result

def extract_iteration0_solutions(log_path: str) -> List[Dict[str, Any]]:
    """Extract all Iteration 0 solutions from the log."""

    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    # Find all "Iteration 0: corrects=1, errors=0" markers
    iter0_pattern = r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] >>>>>>> Iteration 0: corrects=1, errors=0'
    iter0_matches = list(re.finditer(iter0_pattern, content))

    print(f"Found {len(iter0_matches)} Iteration 0 occurrences with corrects=1, errors=0")

    solutions = []

    for i, match in enumerate(iter0_matches, 1):
        timestamp = match.group(1)
        start_pos = match.start()

        # Extract solution: look backwards for the assistant's response
        # The solution is typically in the previous assistant message before verification
        # Search backwards for "Streaming Response:" or similar marker

        # Look back up to 100KB for the solution
        search_start = max(0, start_pos - 100000)
        context = content[search_start:start_pos]

        # Find the last assistant response before this iteration marker
        # Pattern: >>>>>>> Streaming Response: followed by the solution
        streaming_pattern = r'>>>>>>> Streaming Response:\s*\n(.+?)(?=>>>>>>> (?:Initial verification|verify results|Iteration \d+))'
        streaming_matches = list(re.finditer(streaming_pattern, context, re.DOTALL))

        if streaming_matches:
            # Get the last streaming response before this iteration
            solution_text = streaming_matches[-1].group(1)
        else:
            # Try alternative: look for the solution in messages payload
            # Pattern: "content": "...solution..."
            content_pattern = r'"content":\s*"((?:[^"\\]|\\.)*)"\s*\}\s*\],\s*"model":'
            content_matches = list(re.finditer(content_pattern, context, re.DOTALL))
            if content_matches:
                solution_text = content_matches[-1].group(1)
                # Unescape JSON
                solution_text = solution_text.replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\')
            else:
                solution_text = "NOT_FOUND"

        # Extract answer from solution
        answer_info = extract_answer_detailed(solution_text)

        solutions.append({
            'run_number': i,
            'timestamp': timestamp,
            'solution_length': len(solution_text),
            'solution_preview': solution_text[:500] if solution_text != "NOT_FOUND" else "NOT_FOUND",
            'answer_info': answer_info
        })

    return solutions

def main():
    log_path = 'bfs_baseline_results/bfs_run8_20251219_225957.log'

    print("Extracting Iteration 0 solutions from Run 8...")
    print("="*80)

    solutions = extract_iteration0_solutions(log_path)

    print(f"\n{'='*80}")
    print(f"ITERATION 0 SOLUTIONS ANALYSIS")
    print(f"{'='*80}\n")

    for sol in solutions:
        print(f"--- Run {sol['run_number']} @ {sol['timestamp']} ---")
        print(f"Solution length: {sol['solution_length']} chars")

        answer_info = sol['answer_info']
        print(f"\nClaimed Answer: {answer_info['raw_answer']}")
        print(f"Answer Type: {answer_info['answer_type']}")
        print(f"Parsed Set: {answer_info['parsed_set']}")
        print(f"Includes k=2: {answer_info['includes_k2']}")
        print(f"Match vs Truth (k∈{{0,1,3}}): {answer_info['matches_truth']}")

        # Show preview
        if sol['solution_preview'] != "NOT_FOUND":
            # Try to find the summary section
            preview = sol['solution_preview']
            if '### Summary' in preview or 'Summary ###' in preview:
                summary_match = re.search(r'###\s*Summary\s*###(.+?)(?:###|$)', preview, re.DOTALL)
                if summary_match:
                    print(f"\nSummary preview:")
                    print(summary_match.group(1).strip()[:300])

        print(f"\n")

    # Summary statistics
    print(f"{'='*80}")
    print(f"SUMMARY STATISTICS")
    print(f"{'='*80}\n")

    total = len(solutions)
    correct = sum(1 for s in solutions if s['answer_info']['matches_truth'] == 'CORRECT')
    incomplete = sum(1 for s in solutions if s['answer_info']['matches_truth'] == 'INCOMPLETE')
    overgeneralized = sum(1 for s in solutions if s['answer_info']['matches_truth'] == 'OVERGENERALIZED')
    wrong = sum(1 for s in solutions if s['answer_info']['matches_truth'] == 'WRONG')
    unknown = sum(1 for s in solutions if s['answer_info']['matches_truth'] == 'UNKNOWN')

    includes_k2 = sum(1 for s in solutions if s['answer_info']['includes_k2'] == True)

    print(f"Total Iteration 0 solutions: {total}")
    print(f"  ✅ CORRECT (k∈{{0,1,3}}): {correct}/{total} ({100*correct//total if total else 0}%)")
    print(f"  ⚠️  INCOMPLETE (subset): {incomplete}/{total} ({100*incomplete//total if total else 0}%)")
    print(f"  ⚠️  OVERGENERALIZED (superset): {overgeneralized}/{total} ({100*overgeneralized//total if total else 0}%)")
    print(f"  ❌ WRONG: {wrong}/{total} ({100*wrong//total if total else 0}%)")
    print(f"  ❓ UNKNOWN: {unknown}/{total} ({100*unknown//total if total else 0}%)")
    print(f"\n  ❌ Includes impossible k=2: {includes_k2}/{total} ({100*includes_k2//total if total else 0}%)")

    # Save to JSON
    output = {
        'total_iteration0_solutions': total,
        'summary_stats': {
            'correct': correct,
            'incomplete': incomplete,
            'overgeneralized': overgeneralized,
            'wrong': wrong,
            'unknown': unknown,
            'includes_k2': includes_k2
        },
        'solutions': solutions
    }

    output_path = 'run8_iteration0_solutions.json'
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\nDetailed results saved to: {output_path}")

    # Generate markdown report
    generate_markdown_report(output)

def generate_markdown_report(data: Dict[str, Any]):
    """Generate markdown report of findings."""

    md = []
    md.append("# Run 8 Iteration 0 Solutions - Answer Analysis\n\n")
    md.append("**Ground Truth**: k ∈ {0, 1, 3}\n\n")
    md.append("## Summary\n\n")

    stats = data['summary_stats']
    total = data['total_iteration0_solutions']

    md.append(f"Run 8 generated **{total} Iteration 0 solutions** that passed initial verification.\n\n")
    md.append("### Answer Correctness\n\n")
    md.append(f"- ✅ **CORRECT** (k ∈ {{0,1,3}}): {stats['correct']}/{total}\n")
    md.append(f"- ⚠️ **INCOMPLETE** (missing values): {stats['incomplete']}/{total}\n")
    md.append(f"- ⚠️ **OVERGENERALIZED** (extra values): {stats['overgeneralized']}/{total}\n")
    md.append(f"- ❌ **WRONG** (different set): {stats['wrong']}/{total}\n")
    md.append(f"- ❓ **UNKNOWN** (couldn't parse): {stats['unknown']}/{total}\n\n")

    md.append(f"### Critical Finding\n\n")
    md.append(f"**{stats['includes_k2']}/{total} solutions incorrectly included k=2** (impossible value)\n\n")

    md.append("## Solution-by-Solution Breakdown\n\n")

    for sol in data['solutions']:
        answer_info = sol['answer_info']

        md.append(f"### Run {sol['run_number']} @ {sol['timestamp']}\n\n")
        md.append(f"- **Claimed Answer**: `{answer_info['raw_answer']}`\n")
        md.append(f"- **Answer Type**: {answer_info['answer_type']}\n")
        md.append(f"- **Parsed Set**: {answer_info['parsed_set']}\n")
        md.append(f"- **Includes k=2**: {answer_info['includes_k2']}\n")

        # Verdict with emoji
        match = answer_info['matches_truth']
        if match == 'CORRECT':
            md.append(f"- **Verdict**: ✅ CORRECT\n\n")
        elif match == 'INCOMPLETE':
            md.append(f"- **Verdict**: ⚠️ INCOMPLETE (subset of truth)\n\n")
        elif match == 'OVERGENERALIZED':
            md.append(f"- **Verdict**: ⚠️ OVERGENERALIZED (includes impossible values)\n\n")
        elif match == 'WRONG':
            md.append(f"- **Verdict**: ❌ WRONG\n\n")
        else:
            md.append(f"- **Verdict**: ❓ UNKNOWN\n\n")

    md.append("## Key Insights\n\n")

    if stats['correct'] > 0:
        md.append(f"✅ **SUCCESS**: {stats['correct']} Iteration 0 solution(s) found the CORRECT answer k ∈ {{0,1,3}}!\n\n")
        md.append("This proves the system CAN find correct solutions. The failure is in maintaining them through corrections.\n\n")
    elif stats['incomplete'] > 0:
        md.append(f"⚠️ **PARTIAL SUCCESS**: {stats['incomplete']} solution(s) found subset of correct answer.\n\n")
        md.append("System found some correct values but missed others (likely k=3).\n\n")
    else:
        md.append(f"❌ **FAILURE**: No Iteration 0 solutions found correct answer.\n\n")
        md.append(f"Most common error: Including impossible k=2 ({stats['includes_k2']}/{total} solutions).\n\n")

    if stats['includes_k2'] > 0:
        md.append(f"### Why k=2 is Impossible\n\n")
        md.append("The correct answer has a **gap at k=2**:\n")
        md.append("- k=0: All n diagonals (none sunny) ✓\n")
        md.append("- k=1: One sunny line replacing diagonal ✓\n")
        md.append("- k=2: **IMPOSSIBLE** - geometric constraints prevent this configuration ✗\n")
        md.append("- k=3: Novel construction with 3 specific sunny lines ✓\n")
        md.append("- k≥4: **IMPOSSIBLE** - upper bound proof ✗\n\n")
        md.append(f"Yet {stats['includes_k2']}/{total} solutions claimed ranges like k ∈ {{0,1,2,...,n-2}} that include k=2.\n\n")

    content = ''.join(md)

    with open('run8_iteration0_answers_report.md', 'w') as f:
        f.write(content)

    print(f"Markdown report saved to: run8_iteration0_answers_report.md")

if __name__ == '__main__':
    main()

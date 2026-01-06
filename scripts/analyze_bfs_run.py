#!/usr/bin/env python3
"""
Comprehensive BFS run analysis - creates knowledge graph with Iteration 0 solutions.
Works for any BFS run log file.

Usage:
  python analyze_bfs_run.py bfs_baseline_results/bfs_run8_20251219_225957.log
  python analyze_bfs_run.py bfs_baseline_results/bfs_run1_*.log --all  # Analyze all runs
"""

import re
import json
import sys
import os
import glob
from collections import defaultdict
from typing import List, Dict, Any, Tuple

# Ground truth for IMO 2025 Problem 1
GROUND_TRUTH = {0, 1, 3}

def extract_answer_detailed(solution_text: str) -> Dict[str, Any]:
    """Extract claimed answer with detailed parsing and comparison to ground truth."""

    result = {
        'raw_answer': None,
        'parsed_set': None,
        'answer_type': None,
        'includes_k2': None,
        'matches_truth': None
    }

    # Pattern 1: \boxed{...}
    boxed_match = re.search(r'\\boxed\{([^}]+)\}', solution_text)
    if boxed_match:
        result['raw_answer'] = boxed_match.group(1).strip()

    # Pattern 2: Look for final answer in text
    if not result['raw_answer']:
        answer_section = re.search(r'(?:Final answer|answer is|conclude that|Therefore,?|Thus,?).*?k\s*(?:=|∈)\s*([^\n\.]+)',
                                   solution_text, re.IGNORECASE | re.DOTALL)
        if answer_section:
            result['raw_answer'] = answer_section.group(1).strip()

    # Parse the answer
    if result['raw_answer']:
        answer_str = result['raw_answer']

        # Case 1: Explicit set {0, 1, 3}
        explicit_match = re.search(r'\{(\d+(?:\s*,\s*\d+)*)\}', answer_str)
        if explicit_match and 'dot' not in answer_str.lower():
            nums_str = explicit_match.group(1)
            nums = [int(n.strip()) for n in nums_str.split(',')]
            result['parsed_set'] = set(nums)
            result['answer_type'] = 'EXPLICIT_SET'

        # Case 2: Range {0,1,...,n-2} or {0,1,2,...,n-2}
        elif re.search(r'\{0\s*,\s*1.*?n\s*-\s*2\}', answer_str):
            result['answer_type'] = 'RANGE_0_TO_N_MINUS_2'
            result['parsed_set'] = 'PARAMETRIC'
            result['includes_k2'] = True

        # Case 3: {0,1,...,n}
        elif re.search(r'\{0\s*,\s*1.*?n\}', answer_str):
            result['answer_type'] = 'RANGE_0_TO_N'
            result['parsed_set'] = 'PARAMETRIC'
            result['includes_k2'] = True

        # Check if includes k=2
        if result['parsed_set'] == 'PARAMETRIC':
            pass  # Already set above
        elif result['parsed_set'] and isinstance(result['parsed_set'], set):
            result['includes_k2'] = 2 in result['parsed_set']

        # Compare to ground truth
        if result['parsed_set'] == GROUND_TRUTH:
            result['matches_truth'] = 'CORRECT'
        elif isinstance(result['parsed_set'], set):
            if result['parsed_set'].issubset(GROUND_TRUTH):
                result['matches_truth'] = 'INCOMPLETE'
            elif GROUND_TRUTH.issubset(result['parsed_set']):
                result['matches_truth'] = 'OVERGENERALIZED'
            else:
                result['matches_truth'] = 'WRONG'
        elif result['parsed_set'] == 'PARAMETRIC':
            result['matches_truth'] = 'WRONG' if result['includes_k2'] else 'UNKNOWN'

    return result

def extract_iteration0_solutions(log_content: str) -> List[Dict[str, Any]]:
    """Extract all Iteration 0 solutions that passed verification."""

    # Find all "Iteration 0: corrects=1, errors=0" markers
    iter0_pattern = r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] >>>>>>> Iteration 0: corrects=1, errors=0'
    iter0_matches = list(re.finditer(iter0_pattern, log_content))

    solutions = []

    for i, match in enumerate(iter0_matches, 1):
        timestamp = match.group(1)
        start_pos = match.start()

        # Look back up to 100KB for the solution
        search_start = max(0, start_pos - 100000)
        context = log_content[search_start:start_pos]

        # Find the last streaming response before this iteration
        streaming_pattern = r'>>>>>>> Streaming Response:\s*\n(.+?)(?=>>>>>>> (?:Initial verification|verify results|Iteration \d+))'
        streaming_matches = list(re.finditer(streaming_pattern, context, re.DOTALL))

        if streaming_matches:
            solution_text = streaming_matches[-1].group(1)
        else:
            # Try alternative: look in message payload
            content_pattern = r'"content":\s*"((?:[^"\\]|\\.)*)"\s*\}\s*\],\s*"model":'
            content_matches = list(re.finditer(content_pattern, context, re.DOTALL))
            if content_matches:
                solution_text = content_matches[-1].group(1)
                solution_text = solution_text.replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\')
            else:
                solution_text = "NOT_FOUND"

        # Extract answer
        answer_info = extract_answer_detailed(solution_text)

        solutions.append({
            'run_number': i,
            'timestamp': timestamp,
            'solution_length': len(solution_text) if solution_text != "NOT_FOUND" else 0,
            'answer_info': answer_info,
            'solution_text': solution_text[:1000] if solution_text != "NOT_FOUND" else ""  # First 1KB
        })

    return solutions

def parse_log_file(log_path: str) -> Dict[str, Any]:
    """Parse the full log file and extract solution evolution."""

    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    # Extract iterations
    iteration_pattern = r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] >>>>>>> Iteration (\d+): corrects=(\d+), errors=(\d+)'
    iterations = list(re.finditer(iteration_pattern, content))

    # Extract BFS attempts
    bfs_pattern = r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] >>>>>>> BFS: Attempt (\d+) score: ([-\d.]+)'
    bfs_attempts = list(re.finditer(bfs_pattern, content))

    result = {
        'total_iterations': len(iterations),
        'bfs_attempts': len(bfs_attempts),
        'iterations': [],
        'bfs_initial_attempts': [],
        'iteration0_solutions': []
    }

    # Extract BFS initial attempts
    for match in bfs_attempts:
        timestamp, attempt_num, score = match.groups()
        result['bfs_initial_attempts'].append({
            'timestamp': timestamp,
            'attempt': int(attempt_num),
            'score': float(score)
        })

    # Extract iterations
    for match in iterations:
        timestamp, iter_num, corrects, errors = match.groups()
        result['iterations'].append({
            'timestamp': timestamp,
            'iteration': int(iter_num),
            'corrects': int(corrects),
            'errors': int(errors),
            'passed_verification': int(corrects) > 0 and int(errors) == 0
        })

    # Extract Iteration 0 solutions
    result['iteration0_solutions'] = extract_iteration0_solutions(content)

    return result

def analyze_iteration_patterns(data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze patterns in iteration progression."""

    iterations = data['iterations']

    # Group by runs (each Iteration 0 starts a new run)
    runs = []
    current_run = []

    for iter_data in iterations:
        if iter_data['iteration'] == 0 and current_run:
            runs.append(current_run)
            current_run = []
        current_run.append(iter_data)

    if current_run:
        runs.append(current_run)

    analysis = {
        'total_runs': len(runs),
        'runs': []
    }

    for run_idx, run in enumerate(runs):
        run_analysis = {
            'run_number': run_idx + 1,
            'total_iterations': len(run),
            'start_time': run[0]['timestamp'],
            'end_time': run[-1]['timestamp'],
            'iterations': run,
            'pattern': 'UNKNOWN'
        }

        # Detect patterns
        corrects = [it['corrects'] for it in run]
        errors = [it['errors'] for it in run]

        if corrects[0] == 1 and all(c == 0 for c in corrects[1:]):
            run_analysis['pattern'] = 'DEGRADE (started valid, became invalid)'
        elif all(c == 0 for c in corrects):
            run_analysis['pattern'] = 'NEVER_VALID (never passed verification)'
        elif corrects[0] == 1 and corrects[-1] == 1:
            run_analysis['pattern'] = 'MAINTAINED (stayed valid)'

        # Check error accumulation
        if errors == sorted(errors):
            run_analysis['error_trend'] = 'ACCUMULATING (errors increasing)'
        elif errors == sorted(errors, reverse=True):
            run_analysis['error_trend'] = 'IMPROVING (errors decreasing)'
        else:
            run_analysis['error_trend'] = 'OSCILLATING'

        # Add Iteration 0 solution if available
        if run_idx < len(data['iteration0_solutions']):
            run_analysis['iteration0_solution'] = data['iteration0_solutions'][run_idx]

        analysis['runs'].append(run_analysis)

    return analysis

def create_knowledge_graph(log_path: str, json_path: str) -> Dict[str, Any]:
    """Create comprehensive knowledge graph of solution evolution."""

    print(f"Parsing log file: {log_path}")
    log_data = parse_log_file(log_path)

    print(f"Loading final state: {json_path}")
    with open(json_path, 'r') as f:
        final_state = json.load(f)

    print("Analyzing iteration patterns...")
    pattern_analysis = analyze_iteration_patterns(log_data)

    # Extract final answer
    final_solution = final_state.get('solution', '')
    final_answer_info = extract_answer_detailed(final_solution)

    # Iteration 0 statistics
    iter0_solutions = log_data['iteration0_solutions']
    iter0_stats = {
        'total': len(iter0_solutions),
        'correct': sum(1 for s in iter0_solutions if s['answer_info']['matches_truth'] == 'CORRECT'),
        'incomplete': sum(1 for s in iter0_solutions if s['answer_info']['matches_truth'] == 'INCOMPLETE'),
        'overgeneralized': sum(1 for s in iter0_solutions if s['answer_info']['matches_truth'] == 'OVERGENERALIZED'),
        'wrong': sum(1 for s in iter0_solutions if s['answer_info']['matches_truth'] == 'WRONG'),
        'includes_k2': sum(1 for s in iter0_solutions if s['answer_info']['includes_k2'] == True)
    }

    graph = {
        'metadata': {
            'log_file': os.path.basename(log_path),
            'json_file': os.path.basename(json_path),
            'ground_truth': list(GROUND_TRUTH)
        },
        'summary': {
            'total_iterations': log_data['total_iterations'],
            'total_bfs_attempts': log_data['bfs_attempts'],
            'total_runs': pattern_analysis['total_runs'],
            'final_answer': final_answer_info,
            'resume_count': final_state.get('resume_count', 0),
            'total_iterations_across_resumes': final_state.get('total_iterations_across_resumes', 0)
        },
        'bfs_initial_phase': {
            'attempts': log_data['bfs_initial_attempts'],
            'best_score': max([a['score'] for a in log_data['bfs_initial_attempts']]) if log_data['bfs_initial_attempts'] else None,
            'worst_score': min([a['score'] for a in log_data['bfs_initial_attempts']]) if log_data['bfs_initial_attempts'] else None
        },
        'iteration0_analysis': {
            'statistics': iter0_stats,
            'solutions': iter0_solutions
        },
        'runs': pattern_analysis['runs']
    }

    return graph

def generate_visual_summary(graph: Dict[str, Any], output_file: str):
    """Generate markdown summary with Iteration 0 solutions."""

    md = []
    md.append(f"# {graph['metadata']['log_file']} - Solution Evolution Analysis\n\n")
    md.append(f"**Ground Truth**: k ∈ {{{', '.join(map(str, sorted(graph['metadata']['ground_truth'])))}}}\n")
    md.append(f"**Final Answer**: {graph['summary']['final_answer']['raw_answer']}\n")
    md.append(f"**Final Answer Match**: {graph['summary']['final_answer']['matches_truth']}\n\n")

    # Iteration 0 Summary
    md.append("## Iteration 0 Solutions (Passed Initial Verification)\n\n")
    stats = graph['iteration0_analysis']['statistics']
    total = stats['total']

    if total > 0:
        md.append(f"Found **{total} Iteration 0 solutions** that passed verification:\n\n")
        md.append(f"- ✅ **CORRECT** (k ∈ {{0,1,3}}): {stats['correct']}/{total} ({100*stats['correct']//total}%)\n")
        md.append(f"- ⚠️ **INCOMPLETE** (subset): {stats['incomplete']}/{total} ({100*stats['incomplete']//total}%)\n")
        md.append(f"- ⚠️ **OVERGENERALIZED** (superset): {stats['overgeneralized']}/{total} ({100*stats['overgeneralized']//total}%)\n")
        md.append(f"- ❌ **WRONG**: {stats['wrong']}/{total} ({100*stats['wrong']//total}%)\n")
        md.append(f"- ❌ **Includes impossible k=2**: {stats['includes_k2']}/{total} ({100*stats['includes_k2']//total}%)\n\n")

        # Detail each solution
        md.append("### Iteration 0 Solution Details\n\n")
        for sol in graph['iteration0_analysis']['solutions']:
            ans = sol['answer_info']
            md.append(f"**Run {sol['run_number']}** @ {sol['timestamp']}\n")
            md.append(f"- Answer: `{ans['raw_answer']}`\n")
            md.append(f"- Type: {ans['answer_type']}\n")
            md.append(f"- Parsed: {ans['parsed_set']}\n")

            if ans['matches_truth'] == 'CORRECT':
                md.append(f"- Verdict: ✅ **CORRECT**\n\n")
            elif ans['matches_truth'] == 'INCOMPLETE':
                md.append(f"- Verdict: ⚠️ INCOMPLETE (missing values)\n\n")
            elif ans['matches_truth'] == 'OVERGENERALIZED':
                md.append(f"- Verdict: ⚠️ OVERGENERALIZED (includes k={ans['parsed_set'] - GROUND_TRUTH if isinstance(ans['parsed_set'], set) else '2,...'})\n\n")
            else:
                md.append(f"- Verdict: ❌ WRONG\n\n")
    else:
        md.append("No Iteration 0 solutions passed initial verification.\n\n")

    # Timeline
    md.append("## Solution Evolution Timeline\n\n")
    md.append("```\n")

    for run in graph['runs']:
        md.append(f"Run {run['run_number']} ({run['total_iterations']} iterations):\n")
        md.append(f"  {run['start_time']}\n")

        # Show Iteration 0 answer if available
        if 'iteration0_solution' in run:
            ans = run['iteration0_solution']['answer_info']
            md.append(f"  Iter 0 Answer: {ans['raw_answer']} → {ans['matches_truth']}\n")

        for it in run['iterations']:
            symbol = "✓" if it['passed_verification'] else "✗"
            md.append(f"  Iter {it['iteration']}: {symbol} (corrects={it['corrects']}, errors={it['errors']})\n")

        md.append(f"  Pattern: {run['pattern']}\n")
        md.append(f"  Error Trend: {run.get('error_trend', 'N/A')}\n")
        md.append("\n")

    md.append("```\n\n")

    # Key Findings
    md.append("## Key Findings\n\n")

    if stats['total'] > 0:
        if stats['correct'] > 0:
            md.append(f"✅ **CRITICAL FINDING**: {stats['correct']} Iteration 0 solution(s) found the CORRECT answer!\n\n")
            md.append("This proves the system CAN find correct solutions. The failure is in maintaining them.\n\n")
        elif stats['incomplete'] > 0:
            md.append(f"⚠️ **PARTIAL SUCCESS**: {stats['incomplete']} Iteration 0 solution(s) found partial answer.\n\n")

        if stats['includes_k2'] > 0:
            md.append(f"❌ **SYSTEMATIC ERROR**: {stats['includes_k2']}/{total} solutions incorrectly included k=2 (impossible).\n\n")

    # Verification Pattern
    total_runs = len(graph['runs'])
    degrade_runs = sum(1 for r in graph['runs'] if r['pattern'] == 'DEGRADE (started valid, became invalid)')

    md.append("### Verification & Correction Pattern\n\n")
    md.append(f"- Total runs: {total_runs}\n")
    md.append(f"- Runs that DEGRADED (valid → invalid): {degrade_runs}/{total_runs}\n")

    if degrade_runs > 0:
        md.append(f"- **Pattern**: Corrections make solutions WORSE (error accumulation)\n\n")

    # Error Accumulation
    md.append("### Error Accumulation\n\n")
    for run in graph['runs']:
        errors_list = [it['errors'] for it in run['iterations']]
        md.append(f"- Run {run['run_number']}: errors = {errors_list} → {run.get('error_trend', 'N/A')}\n")
    md.append("\n")

    # Write file
    with open(output_file, 'w') as f:
        f.write(''.join(md))

    print(f"Visual summary saved to: {output_file}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze_bfs_run.py <log_file> [--all]")
        print("Example: python analyze_bfs_run.py bfs_baseline_results/bfs_run8_20251219_225957.log")
        print("         python analyze_bfs_run.py bfs_baseline_results --all")
        sys.exit(1)

    path = sys.argv[1]

    # Check if analyzing all runs
    if len(sys.argv) > 2 and sys.argv[2] == '--all':
        log_files = sorted(glob.glob(os.path.join(path, 'bfs_run*_*.log')))
        print(f"Found {len(log_files)} log files to analyze")

        for log_path in log_files:
            json_path = log_path.replace('.log', '.json')
            if not os.path.exists(json_path):
                print(f"Skipping {log_path} (no JSON file)")
                continue

            basename = os.path.basename(log_path).replace('.log', '')
            print(f"\n{'='*80}")
            print(f"Analyzing {basename}...")
            print(f"{'='*80}")

            graph = create_knowledge_graph(log_path, json_path)

            # Save outputs
            json_output = f"{basename}_knowledge_graph.json"
            with open(json_output, 'w') as f:
                json.dump(graph, f, indent=2)
            print(f"Knowledge graph saved to: {json_output}")

            md_output = f"{basename}_analysis.md"
            generate_visual_summary(graph, md_output)
    else:
        # Single file analysis
        log_path = path
        json_path = log_path.replace('.log', '.json')

        if not os.path.exists(json_path):
            print(f"Error: JSON file not found: {json_path}")
            sys.exit(1)

        basename = os.path.basename(log_path).replace('.log', '')

        graph = create_knowledge_graph(log_path, json_path)

        # Save outputs
        json_output = f"{basename}_knowledge_graph.json"
        with open(json_output, 'w') as f:
            json.dump(graph, f, indent=2)
        print(f"\nKnowledge graph saved to: {json_output}")

        md_output = f"{basename}_analysis.md"
        generate_visual_summary(graph, md_output)

        # Print summary
        print(f"\n{'='*80}")
        print(f"SUMMARY")
        print(f"{'='*80}")
        stats = graph['iteration0_analysis']['statistics']
        print(f"Iteration 0 Solutions: {stats['total']}")
        print(f"  ✅ Correct: {stats['correct']}")
        print(f"  ⚠️  Incomplete: {stats['incomplete']}")
        print(f"  ⚠️  Overgeneralized: {stats['overgeneralized']}")
        print(f"  ❌ Wrong: {stats['wrong']}")
        print(f"  ❌ Includes k=2: {stats['includes_k2']}")

        print(f"\nFinal Answer: {graph['summary']['final_answer']['raw_answer']}")
        print(f"Final Verdict: {graph['summary']['final_answer']['matches_truth']}")

if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Deep analysis of bfs_run8 to create knowledge graph of solution evolution.
Traces all solution attempts, verification results, and how solutions evolved.
"""

import re
import json
from collections import defaultdict
from typing import List, Dict, Any, Tuple

def extract_answer_from_solution(solution_text: str) -> str:
    """Extract the claimed answer (what k values are possible)."""
    # Pattern 1: \boxed{...}
    match = re.search(r'\\boxed\{([^}]+)\}', solution_text)
    if match:
        return match.group(1).strip()

    # Pattern 2: k ∈ {...}
    match = re.search(r'k\s*\\in\s*\\{([^}]+)\\}', solution_text)
    if match:
        return f"k ∈ {{{match.group(1)}}}"

    # Pattern 3: "exactly k" or "k ="
    match = re.search(r'k\s*=\s*([0-9]+)', solution_text)
    if match:
        return f"k = {match.group(1)}"

    return "UNKNOWN"

def extract_verdict_from_verification(verify_text: str) -> Tuple[str, List[str]]:
    """Extract verification verdict and key errors."""
    verdict = "UNKNOWN"
    errors = []

    # Final verdict
    if "**invalid**" in verify_text.lower():
        verdict = "INVALID"
    elif "**valid**" in verify_text.lower() or "rigorous" in verify_text.lower():
        verdict = "VALID"
    elif "correct" in verify_text.lower() and "solution" in verify_text.lower():
        verdict = "VALID"

    # Extract critical errors
    critical_matches = re.findall(r'\*\*Critical Error\*\*[^\n]*', verify_text, re.IGNORECASE)
    for err in critical_matches:
        errors.append(err.strip())

    # Extract justification gaps
    gap_matches = re.findall(r'\*\*Justification Gap\*\*[^\n]*', verify_text, re.IGNORECASE)
    for gap in gap_matches:
        errors.append(gap.strip())

    return verdict, errors

def parse_log_file(log_path: str) -> Dict[str, Any]:
    """Parse the full log file and extract solution evolution."""

    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    # Find all major sections
    attempts = []

    # Pattern 1: Find all "Iteration X" markers
    iteration_pattern = r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] >>>>>>> Iteration (\d+): corrects=(\d+), errors=(\d+)'
    iterations = list(re.finditer(iteration_pattern, content))

    # Pattern 2: Find all BFS attempt scores
    bfs_pattern = r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] >>>>>>> BFS: Attempt (\d+) score: ([-\d.]+)'
    bfs_attempts = list(re.finditer(bfs_pattern, content))

    # Pattern 3: Find score history
    score_pattern = r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] >>>>>>> \[SCORE\] .* score: ([-\d.]+)'
    scores = list(re.finditer(score_pattern, content))

    result = {
        'total_iterations': len(iterations),
        'bfs_attempts': len(bfs_attempts),
        'iterations': [],
        'bfs_initial_attempts': [],
        'timeline': []
    }

    # Extract BFS initial attempts
    for match in bfs_attempts:
        timestamp, attempt_num, score = match.groups()
        result['bfs_initial_attempts'].append({
            'timestamp': timestamp,
            'attempt': int(attempt_num),
            'score': float(score)
        })
        result['timeline'].append({
            'timestamp': timestamp,
            'event': f'BFS_ATTEMPT_{attempt_num}',
            'score': float(score)
        })

    # Extract iterations
    for i, match in enumerate(iterations):
        timestamp, iter_num, corrects, errors = match.groups()

        # Find the next iteration or end of file
        start_pos = match.start()
        end_pos = iterations[i+1].start() if i+1 < len(iterations) else len(content)

        section = content[start_pos:end_pos]

        # Try to extract solution from this section (look backwards for context)
        context_start = max(0, start_pos - 50000)  # 50KB context
        context = content[context_start:end_pos]

        # Extract answer if visible
        answer = "NOT_EXTRACTED"
        if '\\boxed' in section or 'k \\in' in section:
            answer = extract_answer_from_solution(section)

        result['iterations'].append({
            'timestamp': timestamp,
            'iteration': int(iter_num),
            'corrects': int(corrects),
            'errors': int(errors),
            'answer': answer,
            'passed_verification': int(corrects) > 0 and int(errors) == 0
        })

        result['timeline'].append({
            'timestamp': timestamp,
            'event': f'ITERATION_{iter_num}',
            'corrects': int(corrects),
            'errors': int(errors)
        })

    return result

def analyze_iteration_patterns(data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze patterns in iteration progression."""

    iterations = data['iterations']

    # Group iterations by "run" (each time iteration 0 appears, it's a new run)
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

    # Extract final answer and verification
    final_answer = extract_answer_from_solution(final_state.get('solution', ''))
    final_verification = final_state.get('verify', '')
    final_verdict, final_errors = extract_verdict_from_verification(final_verification)

    graph = {
        'summary': {
            'total_iterations': log_data['total_iterations'],
            'total_bfs_attempts': log_data['bfs_attempts'],
            'total_runs': pattern_analysis['total_runs'],
            'final_answer': final_answer,
            'final_verdict': final_verdict,
            'final_error_count': len(final_errors),
            'resume_count': final_state.get('resume_count', 0),
            'total_iterations_across_resumes': final_state.get('total_iterations_across_resumes', 0)
        },
        'bfs_initial_phase': {
            'attempts': log_data['bfs_initial_attempts'],
            'best_score': max([a['score'] for a in log_data['bfs_initial_attempts']]) if log_data['bfs_initial_attempts'] else None,
            'worst_score': min([a['score'] for a in log_data['bfs_initial_attempts']]) if log_data['bfs_initial_attempts'] else None
        },
        'runs': pattern_analysis['runs'],
        'final_state': {
            'answer': final_answer,
            'verdict': final_verdict,
            'errors': final_errors,
            'current_iteration': final_state.get('current_iteration', 0),
            'max_runs': final_state.get('max_runs', 0)
        }
    }

    return graph

def print_knowledge_graph(graph: Dict[str, Any]):
    """Print knowledge graph in readable format."""

    print("\n" + "="*80)
    print("KNOWLEDGE GRAPH: BFS Run 8 Solution Evolution")
    print("="*80)

    print("\n### SUMMARY ###")
    summary = graph['summary']
    print(f"Total Iterations: {summary['total_iterations']}")
    print(f"Total BFS Attempts: {summary['total_bfs_attempts']}")
    print(f"Total Runs (restarts): {summary['total_runs']}")
    print(f"Resume Count: {summary['resume_count']}")
    print(f"Total Iterations Across Resumes: {summary['total_iterations_across_resumes']}")
    print(f"\nFinal Answer: {summary['final_answer']}")
    print(f"Final Verdict: {summary['final_verdict']}")
    print(f"Final Error Count: {summary['final_error_count']}")

    print("\n### BFS INITIAL PHASE ###")
    bfs = graph['bfs_initial_phase']
    print(f"Number of Initial Attempts: {len(bfs['attempts'])}")
    if bfs['attempts']:
        print(f"Best Score: {bfs['best_score']}")
        print(f"Worst Score: {bfs['worst_score']}")
        for attempt in bfs['attempts']:
            print(f"  Attempt {attempt['attempt']}: score={attempt['score']:.2f} @ {attempt['timestamp']}")

    print("\n### RUN-BY-RUN ANALYSIS ###")
    for run in graph['runs']:
        print(f"\n--- Run {run['run_number']} ---")
        print(f"Duration: {run['start_time']} → {run['end_time']}")
        print(f"Iterations: {run['total_iterations']}")
        print(f"Pattern: {run['pattern']}")
        print(f"Error Trend: {run.get('error_trend', 'N/A')}")
        print(f"Iteration Details:")
        for it in run['iterations']:
            status = "✓ PASS" if it['passed_verification'] else "✗ FAIL"
            print(f"  Iter {it['iteration']}: corrects={it['corrects']}, errors={it['errors']} {status}")
            if it['answer'] != "NOT_EXTRACTED":
                print(f"    Answer: {it['answer']}")

    print("\n### FINAL STATE ###")
    final = graph['final_state']
    print(f"Final Answer: {final['answer']}")
    print(f"Verification Verdict: {final['verdict']}")
    print(f"Current Iteration: {final['current_iteration']}")
    print(f"Max Runs Allowed: {final['max_runs']}")
    print(f"\nCritical Errors Found ({len(final['errors'])}):")
    for i, err in enumerate(final['errors'], 1):
        print(f"  {i}. {err}")

    print("\n" + "="*80)

def main():
    import sys

    log_path = 'bfs_baseline_results/bfs_run8_20251219_225957.log'
    json_path = 'bfs_baseline_results/bfs_run8_20251219_225957.json'

    graph = create_knowledge_graph(log_path, json_path)

    # Print to console
    print_knowledge_graph(graph)

    # Save to JSON
    output_path = 'bfs_run8_knowledge_graph.json'
    with open(output_path, 'w') as f:
        json.dump(graph, f, indent=2)
    print(f"\nKnowledge graph saved to: {output_path}")

    # Create visual summary
    create_visual_summary(graph)

def create_visual_summary(graph: Dict[str, Any]):
    """Create visual markdown summary."""

    md = []
    md.append("# Run 8 Solution Evolution - Visual Summary\n")
    md.append(f"**Ground Truth**: k ∈ {{0, 1, 3}} (NOT k ∈ {{0,...,n-2}})\n")
    md.append(f"**Run 8 Final Answer**: {graph['summary']['final_answer']}\n")
    md.append(f"**Run 8 Verdict**: {graph['summary']['final_verdict']}\n\n")

    md.append("## Solution Evolution Timeline\n\n")
    md.append("```\n")

    # Create ASCII timeline
    for run_idx, run in enumerate(graph['runs'], 1):
        md.append(f"Run {run_idx} ({run['total_iterations']} iterations):\n")
        md.append(f"  {run['start_time']}\n")

        for it in run['iterations']:
            symbol = "✓" if it['passed_verification'] else "✗"
            md.append(f"  Iter {it['iteration']}: {symbol} (corrects={it['corrects']}, errors={it['errors']})\n")

        md.append(f"  Pattern: {run['pattern']}\n")
        md.append(f"  Error Trend: {run.get('error_trend', 'N/A')}\n")
        md.append("\n")

    md.append("```\n\n")

    md.append("## Key Findings\n\n")

    # Analyze if answer got closer to truth
    final_answer = graph['summary']['final_answer']
    if "0,1,2" in final_answer or "0,1,\\dots" in final_answer or "n-2" in final_answer:
        md.append(f"❌ **Wrong Answer**: Claimed `{final_answer}` includes k=2, which is IMPOSSIBLE.\n\n")
    elif "0,1,3" in final_answer:
        md.append(f"✅ **Correct Answer**: Found `{final_answer}`!\n\n")
    elif "{0,1}" in final_answer or "k=0" in final_answer or "k=1" in final_answer:
        md.append(f"⚠️ **Incomplete Answer**: `{final_answer}` is subset of truth but missing k=3.\n\n")
    else:
        md.append(f"❓ **Unknown Answer**: `{final_answer}` - unclear relation to truth.\n\n")

    # Verification effectiveness
    total_runs = len(graph['runs'])
    degrade_runs = sum(1 for r in graph['runs'] if r['pattern'] == 'DEGRADE (started valid, became invalid)')

    md.append(f"### Verification Pattern\n\n")
    md.append(f"- Total runs: {total_runs}\n")
    md.append(f"- Runs that started VALID but became INVALID: {degrade_runs}/{total_runs}\n")
    md.append(f"- This suggests: **Verification initially passes wrong solutions, then fails them later**\n\n")

    # BFS effectiveness
    bfs = graph['bfs_initial_phase']
    if bfs['attempts']:
        md.append(f"### BFS Initial Exploration\n\n")
        md.append(f"- Generated {len(bfs['attempts'])} initial solutions\n")
        md.append(f"- Score range: [{bfs['worst_score']:.2f}, {bfs['best_score']:.2f}]\n")
        md.append(f"- All scores NEGATIVE → None of the initial attempts were promising\n\n")

    # Error accumulation
    md.append(f"### Error Accumulation\n\n")
    for run in graph['runs']:
        errors_list = [it['errors'] for it in run['iterations']]
        md.append(f"- Run {run['run_number']}: errors = {errors_list} → {run.get('error_trend', 'N/A')}\n")

    md.append("\n")
    md.append("## Conclusion\n\n")

    if graph['summary']['final_verdict'] == 'INVALID':
        md.append("**Run 8 FAILED to find correct solution.**\n\n")
        md.append("The reasoning process:\n")
        md.append("1. Generated multiple initial attempts (BFS), all with negative scores\n")
        md.append("2. Selected best initial solution\n")
        md.append("3. Iterated to improve, but errors accumulated\n")
        md.append("4. Final solution still contains critical errors\n")
        md.append(f"5. Final answer `{final_answer}` is WRONG (includes impossible k=2)\n\n")

    content = ''.join(md)

    with open('bfs_run8_visual_summary.md', 'w') as f:
        f.write(content)

    print(f"Visual summary saved to: bfs_run8_visual_summary.md")

if __name__ == '__main__':
    main()

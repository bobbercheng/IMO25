#!/usr/bin/env python3
"""
Comprehensive Analysis of BFS Validation Test Results (N=12)
Analyzes bfs_validation_test/ logs and JSON files
"""

import json
import re
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Any

def extract_answer_validator_verdicts(log_file: Path) -> List[Dict[str, Any]]:
    """Extract all answer validator verdicts from log file."""
    verdicts = []

    with open(log_file, 'r') as f:
        content = f.read()

    # Find all validator output
    pattern = r'\[ANSWER VALIDATION\] Details: ({[^}]+(?:\{[^}]*\})?[^}]*})'
    matches = re.finditer(pattern, content)

    for match in matches:
        try:
            details_str = match.group(1)
            # Parse the dictionary
            details = eval(details_str)
            verdicts.append(details)
        except Exception as e:
            print(f"Error parsing verdict in {log_file.name}: {e}")

    return verdicts

def extract_final_answer(log_file: Path) -> str:
    """Extract final boxed answer from log."""
    with open(log_file, 'r') as f:
        content = f.read()

    # Find last boxed answer
    matches = list(re.finditer(r'\\boxed\{([^}]+)\}', content))
    if matches:
        return matches[-1].group(1)
    return "NOT_FOUND"

def count_iterations(log_file: Path) -> int:
    """Count number of BFS iterations."""
    with open(log_file, 'r') as f:
        content = f.read()

    # Count exploration attempts
    return content.count('>>>>>>> Corrected solution:')

def extract_verification_verdict(log_file: Path) -> List[str]:
    """Extract verification verdicts (good/bad)."""
    with open(log_file, 'r') as f:
        content = f.read()

    verdicts = re.findall(r'>>>>>>> Verification verdict: (.+)', content)
    return verdicts

def analyze_exploration_path(log_file: Path) -> List[str]:
    """Extract what k values were explored."""
    with open(log_file, 'r') as f:
        content = f.read()

    # Look for boxed answers throughout iterations
    all_answers = re.findall(r'\\boxed\{([^}]+)\}', content)
    return all_answers

def analyze_run(run_num: int, timestamp: str = "20251222_213001") -> Dict[str, Any]:
    """Comprehensive analysis of a single run."""
    log_file = Path(f"bfs_validation_test/bfs_run{run_num}_{timestamp}.log")
    json_file = Path(f"bfs_validation_test/bfs_run{run_num}_{timestamp}.json")

    if not log_file.exists():
        return {"error": "Log file not found"}

    analysis = {
        "run": run_num,
        "log_file": log_file.name,
        "iterations": count_iterations(log_file),
        "final_answer": extract_final_answer(log_file),
        "validator_verdicts": extract_answer_validator_verdicts(log_file),
        "verification_verdicts": extract_verification_verdict(log_file),
        "exploration_path": analyze_exploration_path(log_file),
    }

    # Determine final verdict
    if analysis["validator_verdicts"]:
        final_verdict = analysis["validator_verdicts"][-1]
        analysis["final_verdict"] = final_verdict.get("verdict", "UNKNOWN")
        analysis["claimed_answer"] = final_verdict.get("claimed", set())
        analysis["correct_answer"] = final_verdict.get("correct", set())
        analysis["missing"] = final_verdict.get("missing", set())
    else:
        analysis["final_verdict"] = "NO_VALIDATOR_RUN"

    # Load JSON memory if available
    if json_file.exists():
        with open(json_file, 'r') as f:
            try:
                memory = json.load(f)
                analysis["memory"] = {
                    "total_attempts": len(memory.get("attempts", [])),
                    "last_solution": memory.get("last_solution", "")[:100]
                }
            except Exception as e:
                analysis["memory"] = {"error": str(e)}

    return analysis

def main():
    print("="*80)
    print("BFS VALIDATION TEST DETAILED ANALYSIS (N=12)")
    print("="*80)
    print()

    # Analyze all 12 runs
    results = []
    for run_num in range(1, 13):
        analysis = analyze_run(run_num)
        results.append(analysis)

    # Summary statistics
    print("="*80)
    print("SUMMARY STATISTICS")
    print("="*80)
    print()

    correct_count = sum(1 for r in results if r.get("final_verdict") == "CORRECT")
    incomplete_count = sum(1 for r in results if r.get("final_verdict") == "INCOMPLETE")
    wrong_count = sum(1 for r in results if r.get("final_verdict") == "WRONG")

    print(f"Total runs: {len(results)}")
    print(f"CORRECT: {correct_count}/12 ({correct_count/12*100:.1f}%)")
    print(f"INCOMPLETE: {incomplete_count}/12 ({incomplete_count/12*100:.1f}%)")
    print(f"WRONG: {wrong_count}/12 ({wrong_count/12*100:.1f}%)")
    print()

    # Iteration statistics
    iterations = [r["iterations"] for r in results if "iterations" in r]
    if iterations:
        print(f"Iteration statistics:")
        print(f"  Mean: {sum(iterations)/len(iterations):.1f}")
        print(f"  Min: {min(iterations)}")
        print(f"  Max: {max(iterations)}")
        print(f"  Median: {sorted(iterations)[len(iterations)//2]}")
    print()

    # Detailed breakdown
    print("="*80)
    print("DETAILED BREAKDOWN BY RUN")
    print("="*80)
    print()

    for r in results:
        status_emoji = "✅" if r.get("final_verdict") == "CORRECT" else "❌"
        print(f"{status_emoji} Run {r['run']:2d}: {r.get('final_verdict', 'UNKNOWN'):12s} | "
              f"Iters: {r.get('iterations', 0):2d} | "
              f"Claimed: {r.get('claimed_answer', 'N/A')} | "
              f"Final: {r.get('final_answer', 'N/A')[:30]}")

    print()
    print("="*80)
    print("UNSUCCESSFUL RUNS DEEP DIVE")
    print("="*80)
    print()

    for r in results:
        if r.get("final_verdict") in ["INCOMPLETE", "WRONG"]:
            print(f"\n--- Run {r['run']} ---")
            print(f"Final Verdict: {r.get('final_verdict')}")
            print(f"Iterations: {r.get('iterations')}")
            print(f"Claimed Answer: {r.get('claimed_answer')}")
            print(f"Missing: {r.get('missing')}")
            print(f"Final Boxed Answer: {r.get('final_answer')}")
            print(f"\nExploration Path ({len(r.get('exploration_path', []))} answers generated):")
            path = r.get('exploration_path', [])
            for i, ans in enumerate(path[:10], 1):
                print(f"  [{i}] {ans}")
            if len(path) > 10:
                print(f"  ... ({len(path)-10} more)")

            print(f"\nValidator Verdicts ({len(r.get('validator_verdicts', []))}):")
            for i, v in enumerate(r.get('validator_verdicts', [])[:5], 1):
                print(f"  [{i}] {v.get('verdict')}: claimed={v.get('claimed', 'N/A')}, missing={v.get('missing', 'N/A')}")

    print()
    print("="*80)
    print("SUCCESSFUL RUNS PATTERN")
    print("="*80)
    print()

    for r in results:
        if r.get("final_verdict") == "CORRECT":
            print(f"Run {r['run']:2d}: {r.get('iterations'):2d} iterations, "
                  f"{len(r.get('exploration_path', [])):2d} answers generated")

    print()
    print("="*80)
    print("CRITICAL FINDINGS")
    print("="*80)
    print()

    # Find the metric discrepancy
    verification_good_count = sum(1 for r in results
                                  if 'verification good' in ' '.join(r.get('verification_verdicts', [])))

    print(f"1. SUCCESS METRIC DISCREPANCY:")
    print(f"   - 'verification good' metric: {verification_good_count}/12 (WRONG)")
    print(f"   - 'verdict CORRECT' metric: {correct_count}/12 (ACTUAL)")
    print(f"   - Discrepancy: {verification_good_count - correct_count} runs")
    print()

    print(f"2. INCOMPLETE RUNS:")
    incomplete_runs = [r for r in results if r.get("final_verdict") == "INCOMPLETE"]
    if incomplete_runs:
        print(f"   Runs {[r['run'] for r in incomplete_runs]} only found partial answer")
        for r in incomplete_runs:
            print(f"   - Run {r['run']}: Found {r.get('claimed_answer')}, Missing {r.get('missing')}")
    print()

    print(f"3. ITERATION EFFICIENCY:")
    if incomplete_runs:
        incomplete_iters = [r["iterations"] for r in incomplete_runs]
        correct_runs = [r for r in results if r.get("final_verdict") == "CORRECT"]
        correct_iters = [r["iterations"] for r in correct_runs]

        print(f"   - INCOMPLETE runs: {sum(incomplete_iters)/len(incomplete_iters):.1f} avg iterations")
        print(f"   - CORRECT runs: {sum(correct_iters)/len(correct_iters):.1f} avg iterations")
        print(f"   - Fast failures detected!")

if __name__ == "__main__":
    main()

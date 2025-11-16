#!/usr/bin/env python3
"""
Test Feedback Mechanisms on Failed Asymmetric Case

This script extracts feedback from the failed asymmetric test and applies
different feedback mechanisms to see which produces better corrections.

Usage:
    python test_feedback_mechanisms.py --log run_log_gpt_oss/agent_gpt_oss_asym_output_1.log
"""

import json
import re
import argparse
from pathlib import Path
from typing import Dict, List, Tuple
import sys

# Import our feedback mechanisms
sys.path.append(str(Path(__file__).parent))
from FEEDBACK_IMPLEMENTATION_EXAMPLES import (
    convert_prose_to_json_feedback,
    prioritize_top_n_errors,
    generate_all_diffs,
    score_solution_progressively,
    format_progressive_score,
    create_enhanced_feedback_pipeline
)


def extract_verification_instance(log_path: str, iteration: int = 1) -> Tuple[str, str, str]:
    """
    Extract problem, solution, and verification feedback from log.

    Args:
        log_path: Path to agent log file
        iteration: Which iteration to extract (default: 1 for first failure)

    Returns:
        Tuple of (problem_statement, solution, verification_feedback)
    """
    with open(log_path, 'r') as f:
        log_content = f.read()

    # Extract problem statement (should be near the beginning)
    problem_match = re.search(r'\*\*\* Problem Statement \*\*\*(.*?)(?=\n\n[A-Z]|\Z)', log_content, re.DOTALL)
    if problem_match:
        problem = problem_match.group(1).strip()
    else:
        problem = "[Problem not found in log]"

    # Find verification instances
    verification_pattern = r'>>>>>>> Verification results:(.*?)>>>>>>> Is verification good\?'
    verifications = re.findall(verification_pattern, log_content, re.DOTALL)

    if not verifications or iteration > len(verifications):
        print(f"Warning: Could not find verification #{iteration} in log")
        return problem, "", ""

    verification_json = verifications[iteration - 1]

    # Parse the verification response
    try:
        verification_data = json.loads(verification_json.strip())
        verification_feedback = verification_data
    except json.JSONDecodeError:
        # Try to extract from text
        verification_feedback = verification_json.strip()

    # Extract the solution that was verified
    # Look backward from this verification to find the solution
    solution_pattern = r'Corrected solution:(.*?)>>>>>>> Start verification'
    solution_matches = re.findall(solution_pattern, log_content[:log_content.find(verification_json)], re.DOTALL)

    if solution_matches:
        solution = solution_matches[-1].strip()
        # Clean up JSON formatting if present
        solution = solution.strip('"').replace('\\n', '\n')
    else:
        solution = "[Solution not found in log]"

    return problem, solution, verification_feedback


def test_json_feedback(verification_feedback: str, output_dir: Path):
    """Test JSON structured feedback approach."""
    print("\n" + "="*70)
    print("TEST 1: JSON STRUCTURED FEEDBACK")
    print("="*70)

    # Mock API call for testing
    def mock_api_call(system_prompt, user_prompt, temperature, reasoning_effort):
        # In real use, this would call GPT API
        # For testing, we'll manually create a structured version
        return """
{
  "overall_status": "fail",
  "score": 65,
  "errors": [
    {
      "id": "E1",
      "location": "Lemma 4, case a=n-1, b=1",
      "type": "LOGIC",
      "severity": 85,
      "issue": "Parity analysis missing for when (n-1,1) lies on ℓ_s vs ℓ_d",
      "current_claim": "The point (n-1,1) lies on ℓ_s",
      "correct_version": "The point (n-1,1) lies on ℓ_s when n is even, on ℓ_d when n is odd",
      "fix_template": "Split into two cases: (1) n even: verify (n-1,1) on ℓ_s, (2) n odd: verify (n-1,1) on ℓ_d",
      "dependencies": []
    },
    {
      "id": "E2",
      "location": "Lemma 4, verification step",
      "type": "GAP",
      "severity": 70,
      "issue": "Missing explicit verification for case a=n-2, b=2",
      "current_claim": "Both (n-2,1) and (n-2,2) lie on ℓ_s",
      "correct_version": "For (n-2,1): 1 = (n-2)-(n-2) = 0, INCORRECT. For (n-2,2): 2 = (n-2)-(n-2)+1 = 1, INCORRECT",
      "fix_template": "Recalculate: ℓ_s has equation y = x-(n-2), so for x=n-2: y = 0, not y=1 or y=2",
      "dependencies": ["E1"]
    }
  ],
  "strongest_parts": [
    "Lemma 1 (maximal points on a line) is correct",
    "Lemma 2 (upper bound on sunny lines) is correct",
    "Lemma 3 (construction with k=0) is correct"
  ],
  "priority_fixes": ["E1", "E2"]
}
"""

    try:
        json_feedback = json.loads(mock_api_call(None, None, None, None))

        # Save to file
        output_file = output_dir / "feedback_json_structured.json"
        with open(output_file, 'w') as f:
            json.dump(json_feedback, f, indent=2)

        print(f"\n✓ Created JSON structured feedback: {output_file}")
        print("\nPreview:")
        print(json.dumps(json_feedback, indent=2)[:500] + "...")

        return json_feedback
    except Exception as e:
        print(f"\n✗ Error creating JSON feedback: {e}")
        return None


def test_top3_prioritization(json_feedback: Dict, output_dir: Path):
    """Test Top-3 error prioritization."""
    print("\n" + "="*70)
    print("TEST 2: TOP-3 PRIORITIZATION")
    print("="*70)

    try:
        compressed = prioritize_top_n_errors(json_feedback, n=3)

        output_file = output_dir / "feedback_top3_prioritized.json"
        with open(output_file, 'w') as f:
            json.dump(compressed, f, indent=2)

        print(f"\n✓ Created Top-3 prioritized feedback: {output_file}")
        print(f"\nTotal errors: {compressed['total_errors']}")
        print(f"Showing top: {compressed['showing_top']}")
        print(f"\nPriority fixes: {compressed['priority_fixes']}")
        print(f"\nMessage:\n{compressed['message']}")

        return compressed
    except Exception as e:
        print(f"\n✗ Error creating Top-3 prioritization: {e}")
        return None


def test_diff_generation(solution: str, json_feedback: Dict, output_dir: Path):
    """Test diff-based feedback generation."""
    print("\n" + "="*70)
    print("TEST 3: DIFF-BASED FEEDBACK")
    print("="*70)

    try:
        diffs = generate_all_diffs(solution, json_feedback)

        output_file = output_dir / "feedback_diffs.txt"
        with open(output_file, 'w') as f:
            f.write(diffs)

        print(f"\n✓ Created diff-based feedback: {output_file}")
        print("\nPreview:")
        print(diffs[:500] + "...")

        return diffs
    except Exception as e:
        print(f"\n✗ Error creating diffs: {e}")
        return None


def test_progressive_scoring(solution: str, verification_feedback: str, output_dir: Path):
    """Test progressive scoring."""
    print("\n" + "="*70)
    print("TEST 4: PROGRESSIVE SCORING")
    print("="*70)

    try:
        score, components = score_solution_progressively(solution, str(verification_feedback))
        score_text = format_progressive_score(score, components, threshold=85)

        output_file = output_dir / "feedback_progressive_score.txt"
        with open(output_file, 'w') as f:
            f.write(score_text)

        print(f"\n✓ Created progressive score feedback: {output_file}")
        print(score_text)

        return score, components
    except Exception as e:
        print(f"\n✗ Error creating progressive score: {e}")
        return None, None


def test_combined_pipeline(prose_feedback: str, solution: str, output_dir: Path):
    """Test complete combined pipeline."""
    print("\n" + "="*70)
    print("TEST 5: COMBINED PIPELINE (JSON + Top-3 + Diff)")
    print("="*70)

    def mock_api_call(system_prompt, user_prompt, temperature, reasoning_effort):
        # Return the same mock JSON as before
        return """
{
  "overall_status": "fail",
  "score": 65,
  "errors": [
    {
      "id": "E1",
      "location": "Lemma 4, case a=n-1, b=1",
      "type": "LOGIC",
      "severity": 85,
      "issue": "Parity analysis missing",
      "current_claim": "point (n-1,1) lies on ℓ_s",
      "correct_version": "point (n-1,1) lies on ℓ_s when n is even, on ℓ_d when n is odd",
      "fix_template": "Add parity case split",
      "dependencies": []
    }
  ],
  "strongest_parts": ["Lemmas 1-3 are correct"],
  "priority_fixes": ["E1"]
}
"""

    try:
        combined = create_enhanced_feedback_pipeline(
            prose_feedback=str(prose_feedback),
            solution=solution,
            api_call_fn=mock_api_call,
            strategy="json_top3_diff"
        )

        output_file = output_dir / "feedback_combined_pipeline.txt"
        with open(output_file, 'w') as f:
            f.write(combined)

        print(f"\n✓ Created combined pipeline feedback: {output_file}")
        print("\nPreview:")
        print(combined[:600] + "...")

        return combined
    except Exception as e:
        print(f"\n✗ Error creating combined pipeline: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="Test feedback mechanisms on failed asymmetric case")
    parser.add_argument('--log', type=str, default='run_log_gpt_oss/agent_gpt_oss_asym_output_1.log',
                       help='Path to agent log file')
    parser.add_argument('--iteration', type=int, default=1,
                       help='Which iteration to extract (default: 1)')
    parser.add_argument('--output-dir', type=str, default='feedback_tests',
                       help='Directory to save test outputs')

    args = parser.parse_args()

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)

    print("="*70)
    print("TESTING FEEDBACK MECHANISMS")
    print("="*70)
    print(f"\nLog file: {args.log}")
    print(f"Iteration: {args.iteration}")
    print(f"Output directory: {output_dir}")

    # Extract problem, solution, and feedback from log
    print("\n" + "="*70)
    print("EXTRACTING FROM LOG")
    print("="*70)

    problem, solution, verification_feedback = extract_verification_instance(args.log, args.iteration)

    print(f"\n✓ Extracted problem ({len(problem)} chars)")
    print(f"✓ Extracted solution ({len(solution)} chars)")
    print(f"✓ Extracted verification ({len(str(verification_feedback))} chars)")

    # Save originals
    (output_dir / "original_problem.txt").write_text(problem)
    (output_dir / "original_solution.txt").write_text(solution)
    (output_dir / "original_verification.txt").write_text(str(verification_feedback))

    # Run tests
    json_feedback = test_json_feedback(verification_feedback, output_dir)

    if json_feedback:
        test_top3_prioritization(json_feedback, output_dir)
        test_diff_generation(solution, json_feedback, output_dir)

    test_progressive_scoring(solution, verification_feedback, output_dir)

    test_combined_pipeline(verification_feedback, solution, output_dir)

    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"\nAll test outputs saved to: {output_dir}/")
    print("\nGenerated feedback formats:")
    for f in sorted(output_dir.glob("feedback_*")):
        print(f"  - {f.name}")

    print("\n" + "="*70)
    print("NEXT STEPS")
    print("="*70)
    print("""
1. Review the generated feedback files in the output directory
2. Compare them to the original prose feedback
3. Manually assess which format would be most actionable for low-reasoning LLM
4. Select the best format and integrate into agent_gpt_oss.py
5. Re-run the asymmetric test with enhanced feedback
6. Measure improvement in iterations-to-success and fix accuracy

Recommended order to implement:
1. Top-3 Prioritization (easiest, immediate impact)
2. JSON Structured Feedback (most comprehensive)
3. Diff-based additions (makes JSON even more actionable)
4. Progressive Scoring (for tracking improvement)
""")


if __name__ == "__main__":
    main()

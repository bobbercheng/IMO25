#!/usr/bin/env python3
"""
Solution Gap Detection Tool

This script analyzes solution logs to detect gaps between successful and failed attempts.
It identifies patterns that indicate why a solution attempt failed.
"""

import re
import json
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass, field


@dataclass
class GapAnalysis:
    """Results of gap analysis between two solution attempts"""

    # File metadata
    failed_log: str
    successful_log: str

    # Critical issues in failed attempt
    content_truncations: int = 0
    empty_solutions: int = 0
    verification_failures: int = 0
    iterations: int = 0

    # Success metrics in successful attempt
    has_final_answer: bool = False
    has_complete_solution: bool = False
    verification_passed: bool = False

    # Detailed findings
    critical_gaps: List[str] = field(default_factory=list)
    timestamps: Dict[str, List[str]] = field(default_factory=dict)

    def __str__(self) -> str:
        return f"""
=== Gap Analysis Report ===

Files Analyzed:
  Failed:     {Path(self.failed_log).name}
  Successful: {Path(self.successful_log).name}

Critical Issues in Failed Attempt:
  - Content Truncations: {self.content_truncations}
  - Empty Solutions: {self.empty_solutions}
  - Verification Failures: {self.verification_failures}
  - Total Iterations: {self.iterations}

Success Indicators in Successful Attempt:
  - Has Final Answer: {self.has_final_answer}
  - Has Complete Solution: {self.has_complete_solution}
  - Verification Passed: {self.verification_passed}

Identified Gaps:
{chr(10).join(f"  {i+1}. {gap}" for i, gap in enumerate(self.critical_gaps))}

Timestamps:
  Failed log started: {self.timestamps.get('failed_start', ['N/A'])[0]}
  Failed log ended: {self.timestamps.get('failed_end', ['N/A'])[0]}
  Successful log started: {self.timestamps.get('success_start', ['N/A'])[0]}
  Successful log ended: {self.timestamps.get('success_end', ['N/A'])[0]}
"""


class SolutionGapDetector:
    """Detects gaps between failed and successful solution attempts"""

    def __init__(self, failed_log: str, successful_log: str):
        self.failed_log = Path(failed_log)
        self.successful_log = Path(successful_log)
        self.analysis = GapAnalysis(
            failed_log=str(self.failed_log),
            successful_log=str(self.successful_log)
        )

    def analyze(self) -> GapAnalysis:
        """Perform comprehensive gap analysis"""

        print("Analyzing failed attempt...")
        self._analyze_failed_log()

        print("Analyzing successful attempt...")
        self._analyze_successful_log()

        print("Identifying critical gaps...")
        self._identify_gaps()

        return self.analysis

    def _analyze_failed_log(self):
        """Analyze the failed solution log"""

        try:
            with open(self.failed_log, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            self.analysis.critical_gaps.append(f"Failed to read failed log: {e}")
            return

        # Count content truncations
        self.analysis.content_truncations = len(
            re.findall(r'\[WARNING\].*Maximum content.*exceeded', content)
        )

        # Count empty solutions
        empty_pattern = r'Corrected solution:\s*"\s*"'
        self.analysis.empty_solutions = len(re.findall(empty_pattern, content))

        # Count verification failures
        self.analysis.verification_failures = len(
            re.findall(r'verify results?:\s*no|Verification does not pass', content, re.IGNORECASE)
        )

        # Count iterations (Run X of Y)
        run_matches = re.findall(r'Run (\d+) of (\d+)', content)
        if run_matches:
            self.analysis.iterations = int(run_matches[0][1])

        # Extract timestamps
        timestamp_pattern = r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]'
        timestamps = re.findall(timestamp_pattern, content)
        if timestamps:
            self.analysis.timestamps['failed_start'] = [timestamps[0]]
            self.analysis.timestamps['failed_end'] = [timestamps[-1]]

    def _analyze_successful_log(self):
        """Analyze the successful solution log"""

        try:
            with open(self.successful_log, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            self.analysis.critical_gaps.append(f"Failed to read successful log: {e}")
            return

        # Check for final answer
        self.analysis.has_final_answer = bool(
            re.search(r'final answer|successfully solved', content, re.IGNORECASE)
        )

        # Check for complete solution
        self.analysis.has_complete_solution = bool(
            re.search(r'Check if solution is complete:\s*yes', content, re.IGNORECASE)
        )

        # Check verification status
        self.analysis.verification_passed = bool(
            re.search(r'verify results?:\s*yes|verification.*pass', content, re.IGNORECASE)
        )

        # Extract timestamps
        timestamp_pattern = r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]'
        timestamps = re.findall(timestamp_pattern, content)
        if timestamps:
            self.analysis.timestamps['success_start'] = [timestamps[0]]
            self.analysis.timestamps['success_end'] = [timestamps[-1]]

    def _identify_gaps(self):
        """Identify critical gaps between failed and successful attempts"""

        gaps = []

        # Gap 1: Content generation exceeded limits
        if self.analysis.content_truncations > 0:
            gaps.append(
                f"CONTENT OVERFLOW: Model generated too much content "
                f"({self.analysis.content_truncations} truncations). This suggests "
                f"excessive exploration/reasoning without converging to a solution."
            )

        # Gap 2: Empty solutions after correction
        if self.analysis.empty_solutions > 0:
            gaps.append(
                f"EMPTY SOLUTIONS: Generated {self.analysis.empty_solutions} empty "
                f"solutions. This indicates failure to recover from errors or "
                f"produce structured output after self-correction."
            )

        # Gap 3: Persistent verification failures
        if self.analysis.verification_failures > 5:
            gaps.append(
                f"VERIFICATION LOOP: Failed verification {self.analysis.verification_failures} "
                f"times. This suggests inability to produce rigorous proofs or "
                f"correct identified errors."
            )

        # Gap 4: No final answer in failed attempt vs. clear answer in success
        if not self.analysis.has_final_answer and self.analysis.verification_passed:
            gaps.append(
                "MISSING ANSWER: Failed attempt produced no final answer while "
                "successful attempt provided clear solution. This indicates "
                "fundamental inability to complete the problem."
            )

        # Gap 5: Incompleteness
        if not self.analysis.has_complete_solution and self.analysis.has_complete_solution:
            gaps.append(
                "INCOMPLETE SOLUTION: Failed attempt never reached completion "
                "while successful attempt provided complete solution."
            )

        # Gap 6: Model-specific capabilities
        if self.analysis.content_truncations > 0 or self.analysis.empty_solutions > 5:
            gaps.append(
                "MODEL CAPABILITY GAP: The failed model may lack efficient "
                "reasoning, structured output generation, or error recovery "
                "mechanisms present in the successful model."
            )

        # Gap 7: Time/resource inefficiency
        if self.analysis.iterations > 0:
            gaps.append(
                f"ITERATION INEFFICIENCY: Used {self.analysis.iterations} iterations "
                f"but still failed, suggesting inefficient solution strategy."
            )

        self.analysis.critical_gaps = gaps

    def export_json(self, output_path: str):
        """Export analysis to JSON format"""

        data = {
            'files': {
                'failed': self.analysis.failed_log,
                'successful': self.analysis.successful_log
            },
            'metrics': {
                'failed': {
                    'content_truncations': self.analysis.content_truncations,
                    'empty_solutions': self.analysis.empty_solutions,
                    'verification_failures': self.analysis.verification_failures,
                    'iterations': self.analysis.iterations
                },
                'successful': {
                    'has_final_answer': self.analysis.has_final_answer,
                    'has_complete_solution': self.analysis.has_complete_solution,
                    'verification_passed': self.analysis.verification_passed
                }
            },
            'gaps': self.analysis.critical_gaps,
            'timestamps': self.analysis.timestamps
        }

        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"Analysis exported to {output_path}")


def main():
    """Main entry point"""

    import argparse

    parser = argparse.ArgumentParser(
        description='Detect gaps between failed and successful solution attempts'
    )
    parser.add_argument(
        '--failed',
        required=True,
        help='Path to failed solution log'
    )
    parser.add_argument(
        '--successful',
        required=True,
        help='Path to successful solution log'
    )
    parser.add_argument(
        '--output',
        help='Output JSON file for analysis results'
    )

    args = parser.parse_args()

    detector = SolutionGapDetector(args.failed, args.successful)
    analysis = detector.analyze()

    print(analysis)

    if args.output:
        detector.export_json(args.output)


if __name__ == '__main__':
    main()

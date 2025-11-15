#!/usr/bin/env python3
"""
Real-time Agent Progress Monitor

This script monitors a running agent log file and provides early indicators
of success/failure without waiting for final completion.

Usage:
    python monitor_agent_progress.py <log_file> [--interval 60]
"""

import re
import sys
import time
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Tuple


class AgentProgressMonitor:
    """Monitor agent progress and provide early success indicators."""

    def __init__(self, log_file: str):
        self.log_file = Path(log_file)
        self.last_position = 0
        self.metrics = {
            'iterations': 0,
            'truncations': 0,
            'empty_solutions': 0,
            'verifications': {'yes': 0, 'no': 0},
            'correct_count_history': [],
            'error_count_history': [],
            'solution_lengths': [],
            'verification_scores': [],
            'bug_reports': [],
            'timestamps': []
        }

    def read_new_content(self) -> str:
        """Read only new content since last check."""
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                f.seek(self.last_position)
                new_content = f.read()
                self.last_position = f.tell()
                return new_content
        except FileNotFoundError:
            return ""
        except Exception as e:
            print(f"Error reading log: {e}")
            return ""

    def update_metrics(self, content: str):
        """Update metrics from new content."""

        # Count iterations
        new_iterations = len(re.findall(r'Number of iterations: (\d+)', content))
        if new_iterations > 0:
            iter_match = re.findall(r'Number of iterations: (\d+)', content)
            if iter_match:
                self.metrics['iterations'] = int(iter_match[-1])

        # Count truncations
        self.metrics['truncations'] += len(re.findall(r'\[WARNING\].*Maximum content.*exceeded', content))

        # Count empty solutions
        self.metrics['empty_solutions'] += len(re.findall(r'Corrected solution:\s*"\s*"', content))

        # Track verification results
        for match in re.finditer(r'verify results?:\s*(yes|no)', content, re.IGNORECASE):
            result = match.group(1).lower()
            self.metrics['verifications'][result] += 1

        # Track correct/error counts
        for match in re.finditer(r'number of corrects: (\d+), number of errors: (\d+)', content):
            correct = int(match.group(1))
            error = int(match.group(2))
            self.metrics['correct_count_history'].append(correct)
            self.metrics['error_count_history'].append(error)

        # Track solution lengths
        for match in re.finditer(r'Corrected solution:\s*"([^"]*)"', content):
            solution = match.group(1)
            if solution and solution != "":
                self.metrics['solution_lengths'].append(len(solution))

        # Extract timestamps
        for match in re.finditer(r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]', content):
            timestamp = match.group(1)
            if timestamp not in self.metrics['timestamps']:
                self.metrics['timestamps'].append(timestamp)

    def calculate_health_score(self) -> Tuple[float, str]:
        """Calculate overall health score (0-100) and status."""
        score = 100.0
        reasons = []

        # Check iterations
        if self.metrics['iterations'] == 0:
            return 50.0, "🟡 STARTING - No iterations yet"

        # Red flag: High truncation rate
        truncation_rate = self.metrics['truncations'] / max(self.metrics['iterations'], 1)
        if truncation_rate > 3:  # More than 3 per iteration
            score -= 30
            reasons.append(f"❌ High truncation rate: {truncation_rate:.1f}/iter")
        elif truncation_rate > 1:
            score -= 15
            reasons.append(f"⚠️ Moderate truncation rate: {truncation_rate:.1f}/iter")
        else:
            reasons.append(f"✅ Low truncation rate: {truncation_rate:.1f}/iter")

        # Red flag: High empty solution rate
        empty_rate = self.metrics['empty_solutions'] / max(self.metrics['iterations'], 1)
        if empty_rate > 0.5:  # More than 50% empty
            score -= 25
            reasons.append(f"❌ High empty rate: {empty_rate:.0%}")
        elif empty_rate > 0.2:
            score -= 10
            reasons.append(f"⚠️ Some empty solutions: {empty_rate:.0%}")
        else:
            reasons.append(f"✅ Low empty rate: {empty_rate:.0%}")

        # Green flag: Verification improving
        total_verifications = sum(self.metrics['verifications'].values())
        if total_verifications > 0:
            pass_rate = self.metrics['verifications']['yes'] / total_verifications
            if pass_rate > 0.3:  # >30% passing
                score += 15
                reasons.append(f"✅ Good pass rate: {pass_rate:.0%}")
            elif pass_rate > 0.1:
                reasons.append(f"🟡 Moderate pass rate: {pass_rate:.0%}")
            else:
                score -= 15
                reasons.append(f"❌ Low pass rate: {pass_rate:.0%}")

        # Green flag: correct_count increasing
        if len(self.metrics['correct_count_history']) > 0:
            recent_correct = self.metrics['correct_count_history'][-3:]  # Last 3
            max_correct = max(recent_correct) if recent_correct else 0

            if max_correct >= 3:
                score += 20
                reasons.append(f"✅✅ High correct count: {max_correct}/5")
            elif max_correct >= 1:
                score += 10
                reasons.append(f"✅ Making progress: {max_correct}/5")
            else:
                score -= 10
                reasons.append(f"⚠️ No correct count progress")

        # Red flag: error_count stuck high
        if len(self.metrics['error_count_history']) > 0:
            recent_errors = self.metrics['error_count_history'][-3:]
            avg_errors = sum(recent_errors) / len(recent_errors)

            if avg_errors > 5:
                score -= 20
                reasons.append(f"❌ High error count: {avg_errors:.1f}/10")
            elif avg_errors > 2:
                score -= 5
                reasons.append(f"⚠️ Moderate errors: {avg_errors:.1f}/10")

        # Green flag: Solution lengths stabilizing (not growing unbounded)
        if len(self.metrics['solution_lengths']) >= 3:
            recent_lengths = self.metrics['solution_lengths'][-3:]
            growth_rate = (recent_lengths[-1] - recent_lengths[0]) / recent_lengths[0]

            if abs(growth_rate) < 0.2:  # Stable within 20%
                score += 10
                reasons.append(f"✅ Solution length stable")
            elif growth_rate > 1.0:  # Growing >100%
                score -= 15
                reasons.append(f"❌ Solution length growing: +{growth_rate:.0%}")

        # Determine status
        if score >= 75:
            status = "🟢 HEALTHY"
        elif score >= 50:
            status = "🟡 MODERATE"
        elif score >= 25:
            status = "🟠 CONCERNING"
        else:
            status = "🔴 FAILING"

        return score, status, reasons

    def print_dashboard(self):
        """Print a visual dashboard of current status."""
        score, status, reasons = self.calculate_health_score()

        # Header
        print("\n" + "="*70)
        print(f"📊 AGENT PROGRESS MONITOR - {datetime.now().strftime('%H:%M:%S')}")
        print("="*70)

        # Health Score
        print(f"\n{'HEALTH SCORE:':<20} {score:.1f}/100 - {status}")

        # Key Metrics
        print(f"\n{'ITERATIONS:':<20} {self.metrics['iterations']}")
        print(f"{'TRUNCATIONS:':<20} {self.metrics['truncations']} ({self.metrics['truncations']/max(self.metrics['iterations'], 1):.1f}/iter)")
        print(f"{'EMPTY SOLUTIONS:':<20} {self.metrics['empty_solutions']} ({self.metrics['empty_solutions']/max(self.metrics['iterations'], 1):.0%} rate)")

        total_verify = sum(self.metrics['verifications'].values())
        print(f"{'VERIFICATIONS:':<20} {self.metrics['verifications']['yes']} pass / {total_verify} total ({self.metrics['verifications']['yes']/max(total_verify, 1):.0%})")

        # Current State
        if self.metrics['correct_count_history']:
            current_correct = self.metrics['correct_count_history'][-1]
            current_error = self.metrics['error_count_history'][-1]
            print(f"{'CURRENT STATE:':<20} {current_correct} correct, {current_error} errors")

            # Progress bar for correct count
            progress = "█" * current_correct + "░" * (5 - current_correct)
            print(f"{'CORRECT PROGRESS:':<20} [{progress}] {current_correct}/5")

            # Progress bar for error threshold
            error_progress = "█" * current_error + "░" * (10 - current_error)
            print(f"{'ERROR THRESHOLD:':<20} [{error_progress}] {current_error}/10")

        # Time elapsed
        if len(self.metrics['timestamps']) >= 2:
            start = datetime.strptime(self.metrics['timestamps'][0], '%Y-%m-%d %H:%M:%S')
            end = datetime.strptime(self.metrics['timestamps'][-1], '%Y-%m-%d %H:%M:%S')
            elapsed = end - start
            print(f"{'TIME ELAPSED:':<20} {elapsed}")

        # Health Indicators
        print(f"\n{'HEALTH INDICATORS:':}")
        for reason in reasons:
            print(f"  {reason}")

        # Early Prediction
        print(f"\n{'EARLY PREDICTION:':}")
        self._print_prediction(score)

        print("="*70 + "\n")

    def _print_prediction(self, score: float):
        """Print early prediction based on current metrics."""

        # After at least 3 iterations, we can make predictions
        if self.metrics['iterations'] < 3:
            print("  ⏳ Too early to predict (need 3+ iterations)")
            return

        # Success indicators
        max_correct = max(self.metrics['correct_count_history']) if self.metrics['correct_count_history'] else 0

        if max_correct >= 3:
            print("  🎉 LIKELY SUCCESS - Already reached 3/5 correct!")
            print("  📈 If this continues, solution within next few iterations")
        elif max_correct >= 1 and score >= 60:
            print("  ✅ GOOD PROGRESS - Reached some correct verifications")
            print("  📈 Trends are positive, continue monitoring")
        elif score >= 70:
            print("  ✅ HEALTHY START - No major issues detected")
            print("  📈 Better than original version baseline")
        elif score >= 50:
            print("  🟡 UNCERTAIN - Some issues but not critical yet")
            print("  ⏰ Monitor next 2-3 iterations for trend")
        elif score >= 30:
            print("  ⚠️ CONCERNING - Multiple red flags detected")
            print("  🔍 Review logs for specific issues")

            # Specific warnings
            if self.metrics['truncations'] / max(self.metrics['iterations'], 1) > 2:
                print("  ❌ HIGH TRUNCATIONS - reasoning_effort may still be too high")
            if self.metrics['empty_solutions'] / max(self.metrics['iterations'], 1) > 0.5:
                print("  ❌ MANY EMPTY SOLUTIONS - format validation needed")
        else:
            print("  🔴 LIKELY FAILURE - Similar pattern to original version")
            print("  🛑 Consider stopping and investigating")

        # Comparison to original baseline
        if self.metrics['iterations'] >= 5:
            truncation_rate = self.metrics['truncations'] / self.metrics['iterations']
            original_truncation_rate = 122 / 10  # Original: 122 truncations in 10 iterations

            if truncation_rate < original_truncation_rate * 0.5:
                print(f"  ✅ Truncation rate 50%+ better than original ({truncation_rate:.1f} vs {original_truncation_rate:.1f})")
            elif truncation_rate < original_truncation_rate:
                print(f"  🟡 Truncation rate improved over original ({truncation_rate:.1f} vs {original_truncation_rate:.1f})")
            else:
                print(f"  🔴 Truncation rate NOT improved ({truncation_rate:.1f} vs {original_truncation_rate:.1f})")

    def monitor_continuously(self, interval: int = 60):
        """Monitor log file continuously and update dashboard."""
        print(f"🔍 Monitoring {self.log_file}")
        print(f"⏰ Update interval: {interval} seconds")
        print(f"🛑 Press Ctrl+C to stop\n")

        try:
            while True:
                content = self.read_new_content()
                if content:
                    self.update_metrics(content)
                    self.print_dashboard()

                    # Check for terminal conditions
                    if "Correct solution found" in content:
                        print("🎉 SUCCESS DETECTED! Agent found correct solution.")
                        break
                    elif "Failed in finding a correct solution" in content:
                        print("🛑 FAILURE DETECTED! Agent terminated without solution.")
                        break

                time.sleep(interval)

        except KeyboardInterrupt:
            print("\n\n🛑 Monitoring stopped by user.")
            self.print_dashboard()

    def export_metrics(self, output_file: str):
        """Export current metrics to JSON."""
        with open(output_file, 'w') as f:
            json.dump(self.metrics, f, indent=2)
        print(f"📊 Metrics exported to {output_file}")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Monitor agent progress in real-time'
    )
    parser.add_argument('log_file', help='Path to agent log file')
    parser.add_argument(
        '--interval', '-i', type=int, default=60,
        help='Update interval in seconds (default: 60)'
    )
    parser.add_argument(
        '--once', action='store_true',
        help='Run once and exit (no continuous monitoring)'
    )
    parser.add_argument(
        '--export', '-e', type=str,
        help='Export metrics to JSON file'
    )

    args = parser.parse_args()

    monitor = AgentProgressMonitor(args.log_file)

    if args.once:
        # Single check
        content = monitor.read_new_content()
        monitor.update_metrics(content)
        monitor.print_dashboard()

        if args.export:
            monitor.export_metrics(args.export)
    else:
        # Continuous monitoring
        monitor.monitor_continuously(args.interval)


if __name__ == '__main__':
    main()

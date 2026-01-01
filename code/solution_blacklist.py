"""
Solution Blacklist for BFS Diversity Enhancement

Maintains a persistent blacklist of previously attempted solutions across ALL BFS runs.
Prevents parallel runs from redundantly exploring the same wrong approaches.

Features:
- File-based persistence (survives across runs)
- Thread-safe read/write with file locking
- Automatic refresh before each use
- Supports multiple problem instances
"""

import json
import os
import time
from pathlib import Path
from typing import Dict, List, Optional
from filelock import FileLock
import hashlib


class SolutionBlacklist:
    """Persistent blacklist of attempted solutions."""

    def __init__(self, problem_id: str, blacklist_dir: str = "blacklists"):
        """
        Initialize blacklist for a specific problem.

        Args:
            problem_id: Unique identifier for problem (e.g., "imo06")
            blacklist_dir: Directory to store blacklist files
        """
        self.problem_id = problem_id
        self.blacklist_dir = Path(blacklist_dir)
        self.blacklist_dir.mkdir(exist_ok=True)

        # File paths
        self.blacklist_file = self.blacklist_dir / f"{problem_id}_blacklist.json"
        self.lock_file = self.blacklist_dir / f"{problem_id}_blacklist.lock"

        # In-memory cache
        self.cache = {
            "solutions": [],
            "last_updated": 0
        }

        # Initialize file if doesn't exist
        if not self.blacklist_file.exists():
            self._save_blacklist([])

    def _save_blacklist(self, solutions: List[Dict]):
        """Save blacklist to file with locking."""
        lock = FileLock(str(self.lock_file), timeout=10)

        with lock:
            data = {
                "problem_id": self.problem_id,
                "solutions": solutions,
                "last_updated": time.time(),
                "count": len(solutions)
            }

            with open(self.blacklist_file, 'w') as f:
                json.dump(data, f, indent=2)

    def _load_blacklist(self) -> List[Dict]:
        """Load blacklist from file with locking."""
        lock = FileLock(str(self.lock_file), timeout=10)

        with lock:
            if not self.blacklist_file.exists():
                return []

            with open(self.blacklist_file, 'r') as f:
                data = json.load(f)

            self.cache = {
                "solutions": data.get("solutions", []),
                "last_updated": data.get("last_updated", 0)
            }

            return self.cache["solutions"]

    def refresh(self):
        """Refresh in-memory cache from disk (call before each use)."""
        self._load_blacklist()

    def add_solution(self, answer: str, method: str, run_id: str,
                     verdict: str = "UNKNOWN", iterations: int = 0):
        """
        Add a solution to the blacklist.

        Args:
            answer: The numerical/symbolic answer
            method: The approach used (e.g., "ferrers_diagram", "dilworth")
            run_id: BFS run identifier
            verdict: Verification verdict (FAIL, SUSPICIOUS_OPTIMALITY, etc.)
            iterations: Number of iterations before convergence
        """
        # Refresh to get latest state
        self.refresh()

        # Create solution entry
        solution_entry = {
            "answer": str(answer),
            "method": method,
            "run_id": run_id,
            "verdict": verdict,
            "iterations": iterations,
            "timestamp": time.time()
        }

        # Add to cache
        solutions = self.cache["solutions"]
        solutions.append(solution_entry)

        # Save to disk
        self._save_blacklist(solutions)

    def is_blacklisted(self, answer: str, method: Optional[str] = None) -> bool:
        """
        Check if a solution is blacklisted.

        Args:
            answer: The answer to check
            method: Optional method to check (if None, checks answer only)

        Returns:
            True if blacklisted, False otherwise
        """
        # Refresh before check
        self.refresh()

        for entry in self.cache["solutions"]:
            if entry["answer"] == str(answer):
                if method is None or entry["method"] == method:
                    return True

        return False

    def get_blacklist_prompt(self, max_entries: int = 5) -> str:
        """
        Generate a prompt warning about blacklisted solutions.

        Args:
            max_entries: Maximum number of blacklisted entries to show

        Returns:
            Formatted prompt string
        """
        # Refresh before generating prompt
        self.refresh()

        solutions = self.cache["solutions"]

        if not solutions:
            return ""

        # Sort by most recent first
        recent_solutions = sorted(solutions, key=lambda x: x["timestamp"], reverse=True)[:max_entries]

        prompt_lines = [
            "\n⚠️ FORBIDDEN APPROACHES (already explored by other runs):\n"
        ]

        for i, entry in enumerate(recent_solutions, 1):
            verdict_emoji = {
                "FAIL": "❌",
                "SUSPICIOUS_OPTIMALITY": "⚠️",
                "CRITICAL_ERROR": "💀",
                "PASS": "⚠️"  # Even if passed, we want diversity
            }.get(entry["verdict"], "❓")

            prompt_lines.append(
                f"{i}. {verdict_emoji} Method: {entry['method']} → Answer: {entry['answer']} "
                f"(Verdict: {entry['verdict']}, Run: {entry['run_id']})"
            )

        prompt_lines.append(
            "\n✅ REQUIRED: You MUST use a DIFFERENT theorem/approach/construction!\n"
            "DO NOT repeat the above methods. Explore alternative mathematical frameworks.\n"
        )

        return "\n".join(prompt_lines)

    def get_statistics(self) -> Dict:
        """Get blacklist statistics."""
        self.refresh()

        solutions = self.cache["solutions"]

        # Count unique answers and methods
        unique_answers = set(s["answer"] for s in solutions)
        unique_methods = set(s["method"] for s in solutions)

        # Verdict distribution
        verdict_counts = {}
        for s in solutions:
            verdict = s["verdict"]
            verdict_counts[verdict] = verdict_counts.get(verdict, 0) + 1

        return {
            "total_attempts": len(solutions),
            "unique_answers": len(unique_answers),
            "unique_methods": len(unique_methods),
            "answers": list(unique_answers),
            "methods": list(unique_methods),
            "verdict_distribution": verdict_counts
        }

    def clear(self):
        """Clear the blacklist (use with caution!)."""
        self._save_blacklist([])

    def export_summary(self) -> str:
        """Export blacklist summary for analysis."""
        self.refresh()

        stats = self.get_statistics()

        lines = [
            f"=== Solution Blacklist Summary for {self.problem_id} ===",
            f"Total attempts: {stats['total_attempts']}",
            f"Unique answers: {stats['unique_answers']} - {stats['answers']}",
            f"Unique methods: {stats['unique_methods']} - {stats['methods']}",
            "",
            "Verdict distribution:"
        ]

        for verdict, count in sorted(stats['verdict_distribution'].items(), key=lambda x: -x[1]):
            pct = 100 * count / stats['total_attempts']
            lines.append(f"  {verdict}: {count} ({pct:.1f}%)")

        return "\n".join(lines)


def extract_method_from_solution(solution_text: str) -> str:
    """
    Extract the primary method used from solution text.

    Args:
        solution_text: The solution text

    Returns:
        Method identifier (e.g., "ferrers_diagram", "dilworth", "unknown")
    """
    text_lower = solution_text.lower()

    # Method detection patterns
    if "ferrers" in text_lower:
        return "ferrers_diagram"
    elif "dilworth" in text_lower:
        return "dilworth_decomposition"
    elif "block decomposition" in text_lower or "block structure" in text_lower:
        return "block_decomposition"
    elif "könig" in text_lower or "konig" in text_lower or "egerváry" in text_lower:
        return "konig_egervary"
    elif "greedy" in text_lower:
        return "greedy_construction"
    elif "diagonal" in text_lower:
        return "diagonal_permutation"
    elif "random" in text_lower or "probabilistic" in text_lower:
        return "probabilistic_construction"
    else:
        return "unknown_method"


if __name__ == "__main__":
    # Test the blacklist system
    print("Testing Solution Blacklist System")
    print("="*60)

    # Create blacklist for problem 6
    blacklist = SolutionBlacklist("imo06")

    # Clear any existing data
    blacklist.clear()

    # Add some test solutions
    print("\n1. Adding test solutions...")
    blacklist.add_solution("4048", "ferrers_diagram", "run1", "SUSPICIOUS_OPTIMALITY", 2)
    blacklist.add_solution("4048", "diagonal_permutation", "run2", "SUSPICIOUS_OPTIMALITY", 1)
    blacklist.add_solution("4050", "greedy_construction", "run3", "FAIL", 3)

    # Check statistics
    print("\n2. Statistics:")
    print(blacklist.export_summary())

    # Generate blacklist prompt
    print("\n3. Blacklist prompt for next run:")
    print(blacklist.get_blacklist_prompt())

    # Test blacklisting check
    print("\n4. Blacklist checks:")
    print(f"   Is 4048 blacklisted? {blacklist.is_blacklisted('4048')}")
    print(f"   Is 2112 blacklisted? {blacklist.is_blacklisted('2112')}")
    print(f"   Is 4048+ferrers blacklisted? {blacklist.is_blacklisted('4048', 'ferrers_diagram')}")

    print("\n✓ Test complete!")

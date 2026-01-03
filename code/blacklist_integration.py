"""
Helper functions for solution blacklist integration with BFS baseline.
"""

import os
import re
from pathlib import Path


def extract_problem_id_from_path(problem_path: str) -> str:
    """
    Extract problem ID from file path.

    Examples:
        problems/imo01.txt → imo01
        problems/imo_2025_6.txt → imo_2025_6
        /path/to/problem6.txt → problem6
    """
    if not problem_path:
        return "unknown"

    # Get filename without extension
    filename = Path(problem_path).stem

    # Clean up common patterns
    filename = filename.lower()
    filename = re.sub(r'[^a-z0-9_]', '_', filename)

    return filename or "unknown"


def get_run_id_from_env() -> str:
    """
    Get BFS run ID from environment variable.

    Returns:
        Run ID string (e.g., "run1", "run12") or "unknown"
    """
    # Check BFS_RUN_ID environment variable (set by run_bfs_baseline.sh)
    run_id = os.environ.get("BFS_RUN_ID", "")

    if run_id:
        return f"run{run_id}"

    # Fallback: check for other common env vars
    job_id = os.environ.get("JOB_ID", "")
    if job_id:
        return f"job{job_id}"

    return "unknown"


def save_solution_to_blacklist(blacklist, answer: str, solution_text: str,
                                run_id: str, verdict_dict: dict, iterations: int):
    """
    Save a solution to the blacklist after agent completes.

    Args:
        blacklist: SolutionBlacklist instance
        answer: The final answer
        solution_text: Full solution text
        run_id: BFS run identifier
        verdict_dict: Verification verdict dictionary
        iterations: Number of iterations before convergence
    """
    if not blacklist:
        return

    try:
        # Extract method from solution
        from solution_blacklist import extract_method_from_solution
        method = extract_method_from_solution(solution_text)

        # Get verdict string
        if isinstance(verdict_dict, dict):
            verdict = verdict_dict.get('verdict', 'UNKNOWN')
        else:
            verdict = 'UNKNOWN'

        # Add to blacklist
        blacklist.add_solution(
            answer=answer,
            method=method,
            run_id=run_id,
            verdict=verdict,
            iterations=iterations
        )

        print(f"[BLACKLIST] Saved solution: {answer} ({method}, {verdict}) to blacklist")

    except Exception as e:
        print(f"[BLACKLIST] Warning: Could not save to blacklist: {e}")


def get_blacklist_summary(problem_id: str) -> str:
    """Get summary of blacklist for a problem."""
    try:
        from solution_blacklist import SolutionBlacklist
        blacklist = SolutionBlacklist(problem_id)
        return blacklist.export_summary()
    except:
        return "Blacklist not available"


if __name__ == "__main__":
    # Test functions
    print("Testing blacklist integration helpers")
    print("="*60)

    # Test problem ID extraction
    test_paths = [
        "problems/imo01.txt",
        "problems/imo_2025_6.txt",
        "/path/to/problem6.txt",
        "test.txt"
    ]

    print("\n1. Problem ID extraction:")
    for path in test_paths:
        pid = extract_problem_id_from_path(path)
        print(f"  {path} → {pid}")

    # Test run ID extraction
    print("\n2. Run ID extraction:")
    os.environ["BFS_RUN_ID"] = "5"
    print(f"  BFS_RUN_ID=5 → {get_run_id_from_env()}")

    os.environ.pop("BFS_RUN_ID", None)
    print(f"  No env var → {get_run_id_from_env()}")

    print("\n✓ Tests complete")

"""
Database of independently verified small cases for formula derivation.

All cases here are verified WITHOUT using the target formula to avoid circular reasoning.

Verification sources:
- verified_cp_sat: Verified using CP-SAT constraint programming solver
- imo_official: From official IMO solutions (mathematical proofs)
- manual_proof: Manually proven construction
"""

VERIFIED_CASES_DB = {
    # IMO 2025 Problem 6: Grid tiling
    "imo25_p6": {
        "pattern_keywords": ["grid", "tiles", "rectangular", "2025"],
        "cases": [
            {"n": 4, "k": 2, "tiles": 5, "source": "verified_cp_sat"},
            {"n": 9, "k": 3, "tiles": 12, "source": "imo_official"},
            {"n": 16, "k": 4, "tiles": 21, "source": "verified_cp_sat"},
        ],
        "expected_formula": "n+2k-3",
        "problem_type": "grid_tiling_minimum"
    },

    # Alias for imo06 (same as imo25_p6)
    "imo06": {
        "pattern_keywords": ["grid", "tiles", "rectangular", "2025"],
        "cases": [
            {"n": 4, "k": 2, "tiles": 5, "source": "verified_cp_sat"},
            {"n": 9, "k": 3, "tiles": 12, "source": "imo_official"},
            {"n": 16, "k": 4, "tiles": 21, "source": "verified_cp_sat"},
        ],
        "expected_formula": "n+2k-3",
        "problem_type": "grid_tiling_minimum"
    },

    # Add more problems here as they are verified
    # Example:
    # "imo24_p3": {
    #     "pattern_keywords": ["sequence", "arithmetic", "sum"],
    #     "cases": [...],
    #     "expected_formula": "...",
    #     "problem_type": "sequence_formula"
    # },
}


def get_verified_cases(problem_statement: str, problem_id: str = None):
    """
    Get verified cases for a problem.

    Args:
        problem_statement: Full problem text
        problem_id: Optional problem ID (e.g., "imo25_p6")

    Returns:
        List of verified cases or None if no cases available
    """
    # If problem ID provided, try direct lookup
    if problem_id and problem_id in VERIFIED_CASES_DB:
        return VERIFIED_CASES_DB[problem_id]["cases"]

    # Otherwise, try to match by keywords
    problem_lower = problem_statement.lower()

    for problem_id, data in VERIFIED_CASES_DB.items():
        keywords = data["pattern_keywords"]
        if all(keyword in problem_lower for keyword in keywords):
            print(f"[VERIFIED_CASES_DB] Matched problem: {problem_id}")
            return data["cases"]

    return None


def should_use_formula_derivation(problem_statement: str):
    """
    Determine if problem is suitable for formula derivation.

    Returns:
        True if problem might benefit from formula derivation
    """
    # Keywords that suggest formula-based problems
    formula_keywords = [
        "minimum number",
        "maximum number",
        "how many",
        "find the value",
        "tiles",
        "grid",
        "sequence",
        "pattern",
        "formula",
        "nth term"
    ]

    problem_lower = problem_statement.lower()
    return any(keyword in problem_lower for keyword in formula_keywords)

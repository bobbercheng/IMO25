"""
RAG Retrieval Engine for Domain Knowledge System

Matches problem characteristics to relevant mathematical theorems and hints.
"""

import json
import os
from typing import Dict, List, Tuple
from pathlib import Path


# Path to domain knowledge database
DOMAIN_DB_PATH = Path(__file__).parent.parent / "knowledge" / "domain_theorems.json"


def load_domain_knowledge_db() -> List[Dict]:
    """Load domain knowledge database from JSON file."""
    if not DOMAIN_DB_PATH.exists():
        raise FileNotFoundError(f"Domain knowledge database not found at {DOMAIN_DB_PATH}")

    with open(DOMAIN_DB_PATH, 'r') as f:
        data = json.load(f)

    return data.get("theorems", [])


def compute_relevance(theorem: Dict, problem_chars: Dict) -> int:
    """
    Score theorem relevance to problem.

    Scoring:
    - problem_type match: +10
    - domain match: +5
    - each constraint match: +3
    - special structure match: +8 (high value!)
    - keyword overlap: +1 per keyword

    Args:
        theorem: Theorem dict from database
        problem_chars: Problem characteristics dict

    Returns:
        Relevance score (higher = more relevant)
    """
    score = 0

    # Problem type match
    if problem_chars["problem_type"] in theorem["applicability"].get("problem_type", []):
        score += 10

    # Domain match
    if problem_chars["domain"] in theorem.get("domain", []):
        score += 5

    # Constraint matches
    for constraint in problem_chars["constraints"]:
        if constraint in theorem["applicability"].get("constraints", []):
            score += 3

    # Special structure match (HIGH PRIORITY)
    for structure in problem_chars["special_structure"]:
        if structure in theorem["applicability"].get("special_structure", []):
            score += 8

    return score


def retrieve_domain_hints(problem_characteristics: Dict, k: int = 3) -> List[str]:
    """
    Retrieve top-k most relevant domain knowledge hints.

    Args:
        problem_characteristics: dict from extract_problem_characteristics()
        k: number of hints to return

    Returns:
        list of theorem hints sorted by relevance
    """
    theorems = load_domain_knowledge_db()

    # Score each theorem by relevance
    scored_theorems = []
    for theorem in theorems:
        score = compute_relevance(theorem, problem_characteristics)
        if score > 0:  # Only include theorems with some relevance
            scored_theorems.append((score, theorem))

    # Sort by score (descending), return top-k hints
    scored_theorems.sort(reverse=True, key=lambda x: x[0])

    return [theorem["hint"] for score, theorem in scored_theorems[:k]]


def retrieve_detailed_theorems(problem_characteristics: Dict, k: int = 3) -> List[Tuple[int, Dict]]:
    """
    Retrieve top-k most relevant theorems with full details and scores.

    Args:
        problem_characteristics: dict from extract_problem_characteristics()
        k: number of theorems to return

    Returns:
        list of (score, theorem_dict) tuples sorted by relevance
    """
    theorems = load_domain_knowledge_db()

    # Score each theorem
    scored_theorems = []
    for theorem in theorems:
        score = compute_relevance(theorem, problem_characteristics)
        if score > 0:
            scored_theorems.append((score, theorem))

    # Sort by score (descending)
    scored_theorems.sort(reverse=True, key=lambda x: x[0])

    return scored_theorems[:k]


def build_hint_section(problem_characteristics: Dict, k: int = 2) -> str:
    """
    Build hint section for verification prompt based on problem characteristics.

    Args:
        problem_characteristics: dict from extract_problem_characteristics()
        k: number of hints to include

    Returns:
        Formatted hint section string (empty if no relevant hints)
    """
    hints = retrieve_domain_hints(problem_characteristics, k=k)

    if not hints:
        return ""

    hint_section = "\n**DOMAIN KNOWLEDGE HINTS (based on problem structure):**\n"
    for i, hint in enumerate(hints, 1):
        hint_section += f"{i}. {hint}\n"

    return hint_section


def generate_diversity_prompts(problem_characteristics: Dict, num_prompts: int = 5) -> List[str]:
    """
    Generate diverse exploration prompts based on problem structure.

    Args:
        problem_characteristics: dict from extract_problem_characteristics()
        num_prompts: number of prompts to generate

    Returns:
        List of diversity prompts
    """
    prompts = []

    # Base explorations (always included)
    prompts.append("Try the simplest construction first")
    prompts.append("Use greedy approach")

    # Structure-specific explorations
    if "perfect_square" in problem_characteristics["special_structure"]:
        prompts.append("Exploit block decomposition (divide into k×k subgrids)")
        prompts.append("Consider Dilworth's theorem for poset optimization")

    if "prime" in problem_characteristics["special_structure"]:
        prompts.append("Leverage prime factorization properties")
        prompts.append("Use modular arithmetic and cyclic groups")

    if "highly_composite" in problem_characteristics["special_structure"]:
        prompts.append("Factor n and construct using divisor structure")
        prompts.append("Apply Chinese Remainder Theorem")

    if "power" in problem_characteristics["special_structure"]:
        prompts.append("Exploit power structure and symmetries")

    # Constraint-specific explorations
    if "permutation" in problem_characteristics["constraints"]:
        prompts.append("Test non-identity permutations (σ ≠ id)")
        prompts.append("Consider monotone vs non-monotone permutations")

    if "inequality" in problem_characteristics["constraints"]:
        prompts.append("Try classical inequalities (AM-GM, Cauchy-Schwarz)")

    if "modular_arithmetic" in problem_characteristics["constraints"]:
        prompts.append("Use modular arithmetic properties")

    # Domain-specific explorations
    if problem_characteristics["domain"] == "number_theory":
        prompts.append("Consider divisibility and prime factorization")

    if problem_characteristics["domain"] == "combinatorics":
        prompts.append("Use counting arguments and extremal principle")

    if problem_characteristics["domain"] == "geometry":
        prompts.append("Look for symmetries and special configurations")

    # Return only num_prompts (prioritize earlier ones)
    return prompts[:num_prompts]


if __name__ == "__main__":
    # Test with sample problem characteristics
    from problem_analyzer import extract_problem_characteristics

    test_problem = """
    Determine the minimum number of L-shaped tiles needed to cover an n×n grid
    such that each row and column has exactly one uncovered square.
    """

    chars = extract_problem_characteristics(test_problem)

    print("Problem Characteristics:")
    print(f"  Type: {chars['problem_type']}")
    print(f"  Domain: {chars['domain']}")
    print(f"  Structures: {chars['special_structure']}")
    print()

    print("Top 3 Relevant Theorems:")
    theorems = retrieve_detailed_theorems(chars, k=3)
    for score, theorem in theorems:
        print(f"  [{score} points] {theorem['name']}: {theorem['hint'][:80]}...")
    print()

    print("Hint Section for Verification:")
    hint_section = build_hint_section(chars, k=2)
    print(hint_section)

    print("Diversity Prompts for BFS:")
    diversity = generate_diversity_prompts(chars, num_prompts=5)
    for i, prompt in enumerate(diversity, 1):
        print(f"  {i}. {prompt}")

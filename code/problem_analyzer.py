"""
Problem Characteristic Extraction for RAG-Based Domain Knowledge System

Extracts structural features from mathematical problem statements without
using problem IDs or specific parameter values.
"""

import re
from typing import Dict, List
import math


def extract_problem_characteristics(problem_statement: str) -> Dict:
    """
    Extract structural features from problem without looking at problem ID.

    Args:
        problem_statement: Raw problem text

    Returns:
        dict with keys:
        - problem_type: "optimization", "counting", "proof", "construction"
        - domain: "number_theory", "combinatorics", "geometry", "algebra"
        - parameters: list of variable names (e.g., ["n", "k", "p"])
        - constraints: list of constraint types
        - special_structure: detected structures
    """
    features = {
        "problem_type": detect_problem_type(problem_statement),
        "domain": detect_domain(problem_statement),
        "parameters": extract_parameters(problem_statement),
        "constraints": extract_constraints(problem_statement),
        "special_structure": []
    }

    # Detect special structures from problem text
    features["special_structure"] = detect_special_structure(problem_statement, features["parameters"])

    return features


def detect_problem_type(problem: str) -> str:
    """Detect if problem is optimization, counting, proof, or construction."""
    problem_lower = problem.lower()

    # Optimization keywords
    if any(kw in problem_lower for kw in [
        "minimum", "maximum", "smallest", "largest",
        "minimize", "maximize", "optimal", "least", "greatest"
    ]):
        return "optimization"

    # Counting keywords
    if any(kw in problem_lower for kw in [
        "count", "how many", "number of ways", "combinations"
    ]):
        return "counting"

    # Proof keywords
    if any(kw in problem_lower for kw in [
        "prove", "show that", "demonstrate", "establish"
    ]):
        return "proof"

    # Construction keywords
    if any(kw in problem_lower for kw in [
        "construct", "find all", "determine", "exhibit"
    ]):
        return "construction"

    return "unknown"


def detect_domain(problem: str) -> str:
    """Detect mathematical domain of the problem."""
    problem_lower = problem.lower()

    # Domain indicators
    domains = {
        "number_theory": ["prime", "divisor", "gcd", "lcm", "modular", "integer", "coprime"],
        "combinatorics": ["permutation", "combination", "graph", "grid", "tile", "cover", "partition"],
        "geometry": ["triangle", "circle", "angle", "polygon", "point", "line", "area"],
        "algebra": ["polynomial", "equation", "inequality", "root", "coefficient"]
    }

    scores = {domain: 0 for domain in domains}

    for domain, keywords in domains.items():
        for kw in keywords:
            if kw in problem_lower:
                scores[domain] += 1

    # Return domain with highest score
    if max(scores.values()) > 0:
        return max(scores, key=scores.get)

    return "unknown"


def extract_parameters(problem: str) -> List[str]:
    """Extract parameter variable names from problem statement."""
    params = set()

    # Match single-letter variables (common in math problems)
    # Look for patterns like "n×n", "for n", "where n", etc.
    patterns = [
        r'\b([a-z])\s*×\s*\1\b',  # n×n pattern
        r'\bfor\s+([a-z])\b',      # "for n"
        r'\bwhere\s+([a-z])\b',    # "where n"
        r'\b([a-z])\s*=\s*\d+',    # "n = 2025"
        r'\b([a-z])[²³⁴]',          # n², n³, etc.
    ]

    for pattern in patterns:
        matches = re.findall(pattern, problem, re.IGNORECASE)
        params.update(m.lower() if isinstance(m, str) else m[0].lower() for m in matches)

    return sorted(list(params))


def extract_constraints(problem: str) -> List[str]:
    """Extract constraint types from problem statement."""
    problem_lower = problem.lower()
    constraints = []

    # Check for various constraint types
    constraint_keywords = {
        "permutation": ["permutation", "reordering", "bijection"],
        "grid": ["grid", "matrix", "board", "square"],
        "coverage": ["cover", "tile", "fill"],
        "ordering": ["order", "sequence", "arrange"],
        "partition": ["partition", "split", "divide"],
        "cardinality": ["size", "cardinality", "count"],
        "existence": ["exists", "there is", "for all"],
        "modular_arithmetic": ["mod", "modulo", "remainder", "congruent"],
        "coprime": ["coprime", "relatively prime", "gcd"],
        "inequality": ["≤", "≥", "<", ">", "less than", "greater than"],
        "continuous": ["continuous", "differentiable", "smooth"],
        "differentiable": ["derivative", "gradient", "differentiable"],
        "union": ["union", "or"],
        "intersection": ["intersection", "and", "both"],
        "positive_reals": ["positive real", "positive number"],
        "product": ["product", "multiply"],
        "quadratic": ["quadratic", "square"],
        "integer_solutions": ["integer solution", "integer", "whole number"],
        "finite_set": ["finite", "bounded"]
    }

    for constraint_type, keywords in constraint_keywords.items():
        if any(kw in problem_lower for kw in keywords):
            constraints.append(constraint_type)

    return constraints


def is_perfect_square(n: int) -> bool:
    """Check if a number is a perfect square."""
    if n < 0:
        return False
    sqrt_n = int(n ** 0.5)
    return sqrt_n * sqrt_n == n


def detect_special_structure(problem: str, params: List[str]) -> List[str]:
    """
    Detect special mathematical structures in the problem.

    This function detects STRUCTURAL properties based on:
    1. Variable patterns (n×n, k², etc.)
    2. Mathematical properties of specific constants (e.g., 2025 is 45²)

    NOTE: We detect that 2025 IS a perfect square (structural property),
    but we do NOT leak that "2025" is the specific value - hints use "n=k²" notation.
    """
    structures = []
    problem_lower = problem.lower()

    # Detect perfect square STRUCTURE
    # Method 1: Variable patterns like "n×n", "k×k"
    # Also handle LaTeX \times notation
    if any(pattern in problem_lower for pattern in [
        "×", "\\times", "square grid", "n × n", "k × k", "m × m"
    ]):
        # Check if we can detect k² pattern from variables
        for param in params:
            # Look for "n×n" pattern
            if f"{param}×{param}" in problem_lower or f"{param} × {param}" in problem_lower:
                structures.append("perfect_square")
                break

        # Method 2: Detect specific numbers that are perfect squares
        # Look for patterns like "2025×2025", "2025\times2025", etc.
        # This detects the STRUCTURE (it's a perfect square) without leaking the value
        # Handle both Unicode × and LaTeX \times
        grid_patterns = re.findall(r'(\d+)\s*(?:×|\\times)\s*\1', problem)  # Match "N×N" or "N\timesN"
        for num_str in grid_patterns:
            try:
                num = int(num_str)
                if is_perfect_square(num):
                    structures.append("perfect_square")
                    break
            except ValueError:
                continue

    # Detect prime structure
    if any(kw in problem_lower for kw in ["prime", "prime number", "p is prime"]):
        structures.append("prime")

    # Detect highly composite structure
    if any(kw in problem_lower for kw in [
        "highly composite", "many divisors", "factorization"
    ]):
        structures.append("highly_composite")

    # Detect power structure (n^k)
    if any(pattern in problem_lower for pattern in ["power", "^", "²", "³"]):
        structures.append("power")

    return structures


def format_characteristics(chars: Dict) -> str:
    """Format characteristics as readable string for debugging."""
    lines = [
        f"Problem Type: {chars['problem_type']}",
        f"Domain: {chars['domain']}",
        f"Parameters: {', '.join(chars['parameters']) if chars['parameters'] else 'none'}",
        f"Constraints: {', '.join(chars['constraints']) if chars['constraints'] else 'none'}",
        f"Special Structures: {', '.join(chars['special_structure']) if chars['special_structure'] else 'none'}"
    ]
    return '\n'.join(lines)


if __name__ == "__main__":
    # Test with sample problem
    test_problem = """
    Determine the minimum number of L-shaped tiles needed to cover an n×n grid
    such that each row and column has exactly one uncovered square, where the
    uncovered squares form a permutation pattern.
    """

    chars = extract_problem_characteristics(test_problem)
    print("Extracted Characteristics:")
    print(format_characteristics(chars))

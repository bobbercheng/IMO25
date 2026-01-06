#!/usr/bin/env python3
"""
Dynamic BFS Prompt Generator

Automatically generates explicit exploration prompts based on problem structure.
Forces BFS to systematically try different parameter values.

From Expert Panel (RUN3_EXPERT_PANEL_SYNTHESIS.md):
- Priority 3 alternative: Explicit BFS prompts for k=1,2,3
- If we had explicitly told agent "Now try k=1", it might have found it
- Temperature 0.1 blocks sampling low-probability constructions

Usage:
  Integrated into agent_gpt_oss.py during BFS initial attempts phase.
"""

import re
from typing import List, Dict, Any, Optional, Tuple


def parse_problem_parameters(problem_statement: str) -> Dict[str, Any]:
    """
    Parse problem statement to extract key parameters and search space.

    Returns:
    {
        'variable': str,          # e.g., 'k'
        'description': str,       # e.g., 'sunny lines'
        'min_value': int,         # e.g., 0
        'max_value': int or str,  # e.g., 'n' or 3
        'constraint': str,        # e.g., 'n ≥ 3'
    }
    """
    result = {
        'variable': None,
        'description': None,
        'min_value': None,
        'max_value': None,
        'constraint': None,
        'problem_type': None  # 'FIND', 'PROVE', 'DETERMINE'
    }

    # P1 FIX (2026-01-05): Detect problem type more accurately
    # Priority: MINIMIZE/MAXIMIZE > FIND > PROVE (order matters!)
    if re.search(r'\bminimize\b|\bminimum\b|\bsmallest\b|\bleast\b|\bminimal\b', problem_statement, re.IGNORECASE):
        result['problem_type'] = 'MINIMIZE'
    elif re.search(r'\bmaximize\b|\bmaximum\b|\blargest\b|\bgreatest\b|\bmaximal\b', problem_statement, re.IGNORECASE):
        result['problem_type'] = 'MAXIMIZE'
    elif re.search(r'\bfind\s+all\b|\bdetermine\s+all\b', problem_statement, re.IGNORECASE):
        result['problem_type'] = 'FIND_ALL'
    elif re.search(r'\bfind\b|\bdetermine\b', problem_statement, re.IGNORECASE):
        result['problem_type'] = 'FIND'
    elif re.search(r'\bprove\b|\bshow\b', problem_statement, re.IGNORECASE):
        result['problem_type'] = 'PROVE'

    # Pattern 1: "determine all k for which..." or "find all k such that..."
    # Handle formats like "all nonnegative integers $k$" or "all k"
    # Try to match $variable$ format first (LaTeX), then fall back to last word
    match = re.search(r'(?:determine|find|identify)\s+all\s+.*?\$(\w+)\$\s*(?:for which|such that|where)',
                     problem_statement, re.IGNORECASE)
    if not match:
        # Fallback: capture last word before "such that" or "for which"
        match = re.search(r'(?:determine|find|identify)\s+all\s+.*?\s+(\w+)\s+(?:for which|such that|where)',
                         problem_statement, re.IGNORECASE)
    if match:
        result['variable'] = match.group(1)

    # Pattern 2: Look for "exactly k" or "k ∈"
    # P1 FIX: Skip this for MINIMIZE/MAXIMIZE problems (avoids extracting "one" from "exactly one unit")
    if not result['variable'] and result['problem_type'] not in ['MINIMIZE', 'MAXIMIZE']:
        match = re.search(r'exactly\s+(\w+)\s+(\w+)', problem_statement)
        if match:
            # Additional check: don't extract common words like "one", "two", "three"
            potential_var = match.group(1)
            if potential_var.lower() not in ['one', 'two', 'three', 'four', 'five', 'a', 'the']:
                result['variable'] = potential_var
                result['description'] = match.group(2)

    # Pattern 3: Extract constraints like "n ≥ 3" or "n >= 3"
    # Prioritize constraints in "Let" statements
    constraint_match = re.search(r'Let\s+\$?(\w+)\$?\s*\\?ge\s*(\d+)', problem_statement, re.IGNORECASE)
    if not constraint_match:
        constraint_match = re.search(r'Let\s+\$?(\w+)\$?\s*[≥>=]+\s*(\d+)', problem_statement, re.IGNORECASE)
    if not constraint_match:
        # Fallback: any constraint in the problem
        constraint_match = re.search(r'(\w+)\s*[≥>=]+\s*(\d+)', problem_statement)

    if constraint_match:
        param_name, min_val = constraint_match.groups()
        result['constraint'] = f"{param_name} ≥ {min_val}"

        # If we found k and n>=3, we can infer k ∈ {0,1,2,3,...,n}
        if result['variable'] and result['variable'] != param_name:
            result['min_value'] = 0
            result['max_value'] = param_name  # 'n'

    # Pattern 4: Look for description of what we're counting
    # e.g., "sunny lines" in "exactly k of the lines are sunny"
    # Handle both "exactly k <desc>" and "exactly $k$ of the <desc> are <adj>"
    if result['variable'] and not result['description']:
        # Try "of the <noun> are <adj>" format: "exactly $k$ of the lines are sunny"
        desc_pattern = rf'exactly\s+\$?{result["variable"]}\$?\s+of\s+the\s+([a-z]+)\s+are\s+([a-z]+)'
        desc_match = re.search(desc_pattern, problem_statement, re.IGNORECASE)
        if desc_match:
            # Reorder from "lines are sunny" to "sunny lines"
            noun = desc_match.group(1).strip()
            adjective = desc_match.group(2).strip()
            result['description'] = f"{adjective} {noun}"
        else:
            # Fallback: "exactly k <description>"
            desc_pattern = rf'exactly\s+\$?{result["variable"]}\$?\s+([^,\.]+?)(?:\s+exist|\s+are|\s+can|,|\.|$)'
            desc_match = re.search(desc_pattern, problem_statement, re.IGNORECASE)
            if desc_match:
                result['description'] = desc_match.group(1).strip()

    return result


def generate_bfs_prompts(problem_statement: str, num_prompts: int = 5) -> List[str]:
    """
    Generate explicit BFS exploration prompts.

    Strategy:
    1. Parse problem to extract variable (e.g., 'k') and constraint (e.g., 'n ≥ 3')
    2. Generate prompts forcing specific values (e.g., k=0, k=1, k=2, k=3)
    3. Include edge cases (minimum, maximum, intermediate)

    P1 FIX (2026-01-05): Handle MINIMIZE/MAXIMIZE problems differently
    - For optimization problems: construction strategy prompts
    - For FIND_ALL problems: parameter exploration prompts

    Args:
        problem_statement: The problem text
        num_prompts: Number of prompts to generate (default: 5)

    Returns:
        List of explicit exploration prompts
    """
    params = parse_problem_parameters(problem_statement)

    # P1 FIX: For MINIMIZE/MAXIMIZE problems, use construction strategy prompts
    if params['problem_type'] in ['MINIMIZE', 'MAXIMIZE']:
        return generate_optimization_prompts(problem_statement, num_prompts, params['problem_type'])

    if not params['variable']:
        # Fallback: generic exploration prompts
        return generate_generic_prompts(num_prompts)

    var = params['variable']
    desc = params['description'] or 'elements'

    prompts = []

    # For FIND problems with constraints like n≥3, try small concrete cases
    if params['problem_type'] == 'FIND' and params['constraint']:
        # Extract minimum n value
        min_n_match = re.search(r'≥\s*(\d+)', params['constraint'])
        if min_n_match:
            min_n = int(min_n_match.group(1))

            # BFS Diversity Fix (2025-12-30): Generate more prompts for larger pool
            # Generate prompts for k=0,1,2,3,...,min_n at n=min_n
            prompts.append(
                f"**Explicit Task**: For n={min_n} (the minimal case), "
                f"try to construct a configuration with exactly {var}=0 {desc}. "
                f"Provide explicit construction or prove it's impossible."
            )

            # Generate more parameter values to fill the pool
            for k_val in range(1, min(num_prompts, max(min_n + 2, 15))):
                prompts.append(
                    f"**Explicit Task**: For n={min_n}, "
                    f"try to construct a configuration with exactly {var}={k_val} {desc}. "
                    f"Provide explicit construction or prove it's impossible."
                )

            # Add exploration prompts for edge cases and variations
            if len(prompts) < num_prompts:
                prompts.append(
                    f"**Explicit Task**: For n={min_n}, "
                    f"try to construct a configuration with exactly {var}={min_n} {desc}. "
                    f"This is the maximum possible case."
                )

            # Add larger n values for more diversity
            if len(prompts) < num_prompts:
                for n_val in [min_n + 1, min_n + 2, 2 * min_n, min_n * min_n]:
                    if len(prompts) >= num_prompts:
                        break
                    prompts.append(
                        f"**Explicit Task**: For n={n_val}, "
                        f"explore possible values of {var}. "
                        f"What constructions work for this larger case?"
                    )

    else:
        # Generic prompts based on variable
        prompts.extend([
            f"**Explicit Task**: Explore the case where {var}=0 (minimum possible). "
            f"Does this satisfy all constraints?",

            f"**Explicit Task**: Explore the case where {var}=1 (smallest non-zero). "
            f"Can you construct an explicit example?",

            f"**Explicit Task**: Explore intermediate values of {var}. "
            f"Which values are achievable?",

            f"**Explicit Task**: Explore the maximum possible value of {var}. "
            f"What is the upper bound?",

            f"**Explicit Task**: Systematically check each value from {var}=0 upward. "
            f"For each value, either construct an example or prove impossibility."
        ])

    return prompts[:num_prompts]


def generate_optimization_prompts(problem_statement: str, num_prompts: int, problem_type: str) -> List[str]:
    """
    Generate construction strategy prompts for MINIMIZE/MAXIMIZE problems.

    P1 FIX (2026-01-05): Created to handle optimization problems properly.
    Instead of exploring parameter values, these prompts guide construction strategies.

    Args:
        problem_statement: The problem text
        num_prompts: Number of prompts to generate
        problem_type: 'MINIMIZE' or 'MAXIMIZE'

    Returns:
        List of construction strategy prompts
    """
    # Detect if problem involves special structures
    has_perfect_square = False
    n_value = None

    # Extract n value from problem
    n_match = re.search(r'(\d+)\s*\\?times\s*(\d+)', problem_statement)
    if n_match and n_match.group(1) == n_match.group(2):
        n_value = int(n_match.group(1))
        sqrt_n = int(n_value ** 0.5)
        if sqrt_n * sqrt_n == n_value:
            has_perfect_square = True

    action = "minimize" if problem_type == "MINIMIZE" else "maximize"

    prompts = [
        f"**Explicit Task**: Try a greedy construction strategy. At each step, make the choice that immediately {action}s the objective. Verify this approach works.",

        f"**Explicit Task**: Test small cases (n=3, n=4, n=5) to identify patterns. Use these patterns to construct a solution for larger n.",

        f"**Explicit Task**: Try a block-based or modular construction. Can you decompose the problem into smaller independent subproblems?",

        f"**Explicit Task**: Consider symmetry and structural properties. Are there special configurations (diagonal, cyclic, regular patterns) that {action} the objective?",

        f"**Explicit Task**: Challenge the obvious formula. The first valid construction may not be optimal. Can you find a better approach?",
    ]

    # Add perfect square-specific prompts if detected
    if has_perfect_square and n_value:
        sqrt_n = int(n_value ** 0.5)
        prompts.insert(2,
            f"**Explicit Task**: Exploit the perfect square structure (n={n_value}={sqrt_n}²). "
            f"Try block decomposition, Dilworth's theorem for posets, or grid-based approaches."
        )

    # Add more diversity prompts if needed
    additional_prompts = [
        f"**Explicit Task**: Use a probabilistic or randomized construction. Does randomization help achieve better bounds?",

        f"**Explicit Task**: Apply algebraic or combinatorial lower/upper bounds. What theoretical limits exist?",

        f"**Explicit Task**: Consider adversarial or worst-case constructions. What configuration makes {action}ing hardest?",

        f"**Explicit Task**: Try induction or recursive approaches. Can you build larger solutions from smaller ones while maintaining optimality?",

        f"**Explicit Task**: Explore dual or complementary formulations. Does transforming the problem reveal better strategies?",
    ]

    prompts.extend(additional_prompts)
    return prompts[:num_prompts]


def generate_generic_prompts(num_prompts: int) -> List[str]:
    """
    Generate generic exploration prompts when parameter parsing fails.

    BFS Diversity Fix (2025-12-30): Extended to generate up to 20+ diverse prompts
    to support run-specific prompt rotation across multiple parallel runs.
    """
    base_prompts = [
        "**Explicit Task**: Start with the simplest/smallest possible case. "
        "What happens in the minimal configuration?",

        "**Explicit Task**: Explore the next simplest case. "
        "Can you find a pattern or construction?",

        "**Explicit Task**: Try an intermediate case. "
        "Does the pattern hold?",

        "**Explicit Task**: Explore boundary cases and extremes. "
        "What are the limits?",

        "**Explicit Task**: Systematically enumerate all possibilities for small cases. "
        "Which configurations are valid?",

        # Additional prompts for larger diversity pool (prompts 6-20)
        "**Explicit Task**: Consider a greedy construction. "
        "What is the optimal choice at each step?",

        "**Explicit Task**: Try a probabilistic or random construction. "
        "Can you find a configuration by random selection?",

        "**Explicit Task**: Use a constructive proof approach. "
        "Build the solution step by step.",

        "**Explicit Task**: Consider the dual or complementary problem. "
        "What insights does the inverse provide?",

        "**Explicit Task**: Explore symmetry and structural properties. "
        "Are there patterns or invariants?",

        "**Explicit Task**: Try a case-based analysis. "
        "What if we partition into different scenarios?",

        "**Explicit Task**: Use induction or recursion. "
        "Can we build larger solutions from smaller ones?",

        "**Explicit Task**: Consider algebraic formulations. "
        "Can we express this with equations or formulas?",

        "**Explicit Task**: Explore graph-theoretic interpretations. "
        "Can we model this as a graph problem?",

        "**Explicit Task**: Try combinatorial arguments. "
        "How many ways can we arrange or count?",

        "**Explicit Task**: Consider optimization approaches. "
        "What minimizes or maximizes the objective?",

        "**Explicit Task**: Use pigeonhole or counting principles. "
        "What bounds can we establish?",

        "**Explicit Task**: Explore modular arithmetic or number-theoretic properties. "
        "Are there divisibility or congruence patterns?",

        "**Explicit Task**: Try geometric or spatial interpretations. "
        "Can we visualize this problem?",

        "**Explicit Task**: Consider adversarial constructions. "
        "What is the worst-case scenario?",
    ]

    # If more prompts needed, cycle through with variations
    prompts = base_prompts[:num_prompts]
    if len(prompts) < num_prompts:
        # Add variations of base prompts
        for i in range(len(prompts), num_prompts):
            idx = i % len(base_prompts)
            prompts.append(f"{base_prompts[idx]} (Alternative approach {i+1})")

    return prompts


def should_use_dynamic_prompts(problem_statement: str, num_initial_attempts: int) -> bool:
    """
    Determine if dynamic prompts should be used.

    Criteria:
    - Problem is FIND/DETERMINE type (not pure PROVE)
    - Has parameters to explore (k, n, etc.)
    - Using BFS (num_initial_attempts > 1)

    P1 FIX (2026-01-05): Also enable for MINIMIZE/MAXIMIZE problems
    """
    if num_initial_attempts <= 1:
        return False

    params = parse_problem_parameters(problem_statement)

    # P1 FIX: Use dynamic prompts for MINIMIZE/MAXIMIZE (construction strategies)
    if params['problem_type'] in ['MINIMIZE', 'MAXIMIZE']:
        return True

    # Use if we found a variable to explore
    if params['variable'] and params['problem_type'] in ['FIND', 'FIND_ALL', None]:
        return True

    return False


def get_bfs_prompt_for_attempt(
    problem_statement: str,
    attempt_number: int,
    total_attempts: int
) -> Optional[str]:
    """
    Get specific BFS prompt for a given attempt number.

    Args:
        problem_statement: The problem text
        attempt_number: Current attempt (0-indexed)
        total_attempts: Total number of BFS attempts

    Returns:
        Explicit prompt string or None if not using dynamic prompts
    """
    if not should_use_dynamic_prompts(problem_statement, total_attempts):
        return None

    prompts = generate_bfs_prompts(problem_statement, total_attempts)

    if attempt_number < len(prompts):
        return prompts[attempt_number]

    # Fallback: generic exploration
    return None


# Example usage and testing
if __name__ == '__main__':
    import sys

    # Test with IMO 2025 Problem 1
    if len(sys.argv) > 1:
        # Use problem file from command line
        with open(sys.argv[1], 'r') as f:
            problem = f.read()
    else:
        # Default test problem
        problem = """
        Let n ≥ 3 be an integer. A line ℓ is called sunny if it passes through at least two points
        of a set of n points in the plane, and if it contains at least one sunny point (a point through
        which exactly one sunny line passes).

        Determine all k for which there exists a configuration of n points such that exactly k sunny lines exist.
        """

    print("Testing Dynamic BFS Prompt Generator")
    print("="*80)

    params = parse_problem_parameters(problem)
    print("\nExtracted Parameters:")
    print(f"  Variable: {params['variable']}")
    print(f"  Description: {params['description']}")
    print(f"  Constraint: {params['constraint']}")
    print(f"  Problem Type: {params['problem_type']}")

    print("\n\nGenerated BFS Prompts (n=5):")
    print("="*80)
    prompts = generate_bfs_prompts(problem, num_prompts=5)
    for i, prompt in enumerate(prompts, 1):
        print(f"\nPrompt {i}:")
        print(prompt)

    print("\n\nShould Use Dynamic Prompts?")
    print(f"  BFS with 3 attempts: {should_use_dynamic_prompts(problem, 3)}")
    print(f"  Single attempt: {should_use_dynamic_prompts(problem, 1)}")

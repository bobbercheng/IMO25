#!/usr/bin/env python3
"""
Schema-based blacklist enforcement for LLM structured output.

This module implements constrained decoding via JSON schema to physically prevent
the model from generating blacklisted answers, solving the prompt blindness problem.

Key insight: JSON schema enum acts as a HARD CONSTRAINT on generation, not a soft prompt.
Model cannot generate values outside the enum, guaranteeing 100% compliance.

Usage:
    schema = get_blacklist_constrained_schema(problem, blacklist)
    response = llm.generate(problem, response_format={"type": "json_schema", "json_schema": schema})
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional


def extract_problem_parameter(problem_text: str) -> int:
    """
    Extract the main problem parameter (usually grid size n).

    For IMO Problem 6: "2025 × 2025 grid" → returns 2025
    """
    # Look for "n × n grid" or "n×n grid" pattern
    match = re.search(r'(\d+)\s*[×x]\s*\1\s+grid', problem_text, re.IGNORECASE)
    if match:
        return int(match.group(1))

    # Look for standalone large numbers (likely problem parameters)
    numbers = re.findall(r'\b(\d{4,})\b', problem_text)
    if numbers:
        return int(numbers[0])

    # Default fallback
    return 2025


def estimate_answer_range(problem_text: str, n: Optional[int] = None) -> Tuple[int, int]:
    """
    Estimate plausible answer range for the problem.

    Strategy:
    - For "minimum number of tiles" problems: plausible range [n/2, 3n]
    - Use conservative wide range to ensure correct answer is included
    - Trade-off: Larger enum vs. risk of excluding correct answer

    Args:
        problem_text: Problem statement
        n: Problem parameter (if already extracted)

    Returns:
        (min_val, max_val) tuple
    """
    if n is None:
        n = extract_problem_parameter(problem_text)

    # Detect problem type
    if 'minimum' in problem_text.lower() and ('tile' in problem_text.lower() or 'rectangle' in problem_text.lower()):
        # Tiling problems: typically O(n) to O(2n)
        min_val = max(1, n // 2)      # At least n/2
        max_val = min(3 * n, 10000)   # At most 3n (conservative)
    else:
        # General problems: use wide range
        min_val = max(1, n // 10)
        max_val = min(10 * n, 100000)

    return min_val, max_val


def load_blacklist(problem_file: str) -> List[Dict[str, Any]]:
    """
    Load blacklist for the given problem.

    Args:
        problem_file: Path to problem file (e.g., "problems/imo06.txt")

    Returns:
        List of blacklist entries: [{"answer": "4048", "verdict": "FAIL", ...}, ...]
    """
    # Extract problem ID from file name
    problem_id = Path(problem_file).stem  # "imo06" from "problems/imo06.txt"

    blacklist_path = Path(f"blacklists/{problem_id}_blacklist.json")

    if not blacklist_path.exists():
        return []

    with open(blacklist_path) as f:
        data = json.load(f)

    return data.get("solutions", [])


def extract_blacklisted_numbers(blacklist: List[Dict[str, Any]]) -> List[int]:
    """
    Extract numerical values from blacklist entries.

    Handles:
    - Direct integers: "4048" → 4048
    - Formula answers: "n = 2025" → ignore (not numerical)
    - FAIL verdicts only (ignore PASS entries)

    Args:
        blacklist: List of blacklist entries

    Returns:
        List of blacklisted integers
    """
    blacklisted_nums = []

    for entry in blacklist:
        # Only blacklist FAIL entries
        if entry.get("verdict") != "FAIL":
            continue

        answer = entry.get("answer", "")

        # Try to parse as integer
        try:
            num = int(answer)
            blacklisted_nums.append(num)
        except ValueError:
            # Try to extract number from string like "n = 2025"
            match = re.search(r'\b(\d+)\b', answer)
            if match:
                num = int(match.group(1))
                blacklisted_nums.append(num)

    return blacklisted_nums


def get_blacklist_constrained_schema(
    problem_file: str,
    problem_text: Optional[str] = None,
    blacklist: Optional[List[Dict[str, Any]]] = None,
    use_enum: bool = False,  # Changed default to False to avoid context explosion
    max_enum_size: int = 50   # Reduced from 10000 to 50 - only use enum for tiny blacklists
) -> Dict[str, Any]:
    """
    Generate JSON schema that excludes blacklisted answers.

    This is the main function that implements constrained decoding via JSON schema.

    IMPORTANT: Uses compact "not" constraint instead of large enum to avoid context explosion.
    For example, instead of listing 5000+ allowed values, we list 2-3 forbidden values.

    Args:
        problem_file: Path to problem file (for loading blacklist)
        problem_text: Problem statement text (for range estimation)
        blacklist: Pre-loaded blacklist (optional, will load if not provided)
        use_enum: If True, use enum constraint (ONLY for tiny ranges <50 values)
        max_enum_size: Maximum enum size before falling back to "not" constraint

    Returns:
        JSON schema dict with blacklist constraints

    Example:
        >>> schema = get_blacklist_constrained_schema("problems/imo06.txt")
        >>> # Uses "not": {"enum": [4048, 4050]} instead of huge allowed enum
    """
    # Load blacklist if not provided
    if blacklist is None:
        blacklist = load_blacklist(problem_file)

    # Read problem text if not provided
    if problem_text is None:
        with open(problem_file) as f:
            problem_text = f.read()

    # Extract blacklisted numbers
    blacklisted_nums = extract_blacklisted_numbers(blacklist)

    # Estimate answer range
    n = extract_problem_parameter(problem_text)
    min_val, max_val = estimate_answer_range(problem_text, n)

    # Build schema based on size
    range_size = max_val - min_val + 1

    # Helper function to generate anyOf ranges excluding blacklisted values
    def build_anyof_ranges(min_val, max_val, blacklisted_nums):
        """
        Build anyOf constraint that excludes blacklisted values using range splits.

        Example: range [1012, 6075], blacklist [4048, 4050]
        Returns:
            [
                {"type": "integer", "minimum": 1012, "maximum": 4047},
                {"type": "integer", "enum": [4049]},
                {"type": "integer", "minimum": 4051, "maximum": 6075}
            ]

        This is compact (~200 bytes) and works on OpenRouter (unlike "not" constraint).
        """
        # Sort blacklisted numbers
        sorted_blacklist = sorted(set(blacklisted_nums))

        # Build ranges between blacklisted values
        anyof_ranges = []
        current_min = min_val

        for blacklisted_val in sorted_blacklist:
            if blacklisted_val < current_min or blacklisted_val > max_val:
                # Blacklisted value is outside the range, ignore it
                continue

            # Add range before blacklisted value
            if current_min < blacklisted_val:
                if current_min == blacklisted_val - 1:
                    # Single value - use enum
                    anyof_ranges.append({
                        "type": "integer",
                        "enum": [current_min]
                    })
                else:
                    # Range - use minimum/maximum
                    anyof_ranges.append({
                        "type": "integer",
                        "minimum": current_min,
                        "maximum": blacklisted_val - 1
                    })

            # Move current_min past blacklisted value
            current_min = blacklisted_val + 1

        # Add final range after last blacklisted value
        if current_min <= max_val:
            if current_min == max_val:
                # Single value - use enum
                anyof_ranges.append({
                    "type": "integer",
                    "enum": [current_min]
                })
            else:
                # Range - use minimum/maximum
                anyof_ranges.append({
                    "type": "integer",
                    "minimum": current_min,
                    "maximum": max_val
                })

        return anyof_ranges

    # OPTION 1: Use enum ONLY for very small ranges (< 50 values)
    if use_enum and range_size <= max_enum_size:
        valid_answers = [
            x for x in range(min_val, max_val + 1)
            if x not in blacklisted_nums
        ]

        schema = {
            "type": "object",
            "properties": {
                "solution": {
                    "type": "string",
                    "description": "Detailed mathematical solution with step-by-step reasoning"
                },
                "method": {
                    "type": "string",
                    "description": "Mathematical method or technique used (e.g., 'Dilworth theorem', 'bipartite matching', 'permutation optimization')"
                },
                "final_answer": {
                    "type": "integer",
                    "enum": valid_answers,
                    "description": f"Final numerical answer. BLACKLISTED (do not use): {blacklisted_nums}. These have been proven INCORRECT."
                }
            },
            "required": ["solution", "method", "final_answer"]
        }
    # OPTION 2: Use "anyOf" with range splits for compact blacklist (RECOMMENDED)
    # This works on OpenRouter (unlike "not" constraint which is not supported)
    elif blacklisted_nums:
        anyof_ranges = build_anyof_ranges(min_val, max_val, blacklisted_nums)

        schema = {
            "type": "object",
            "properties": {
                "solution": {
                    "type": "string",
                    "description": "Detailed mathematical solution with step-by-step reasoning"
                },
                "method": {
                    "type": "string",
                    "description": "Mathematical method or technique used (e.g., 'Dilworth theorem', 'bipartite matching', 'permutation optimization')"
                },
                "final_answer": {
                    "type": "integer",
                    "anyOf": anyof_ranges,
                    "description": f"Final numerical answer in range [{min_val}, {max_val}]. FORBIDDEN (proven incorrect): {blacklisted_nums}. You MUST use a different approach."
                }
            },
            "required": ["solution", "method", "final_answer"]
        }
    # OPTION 3: Fallback to range + description only (no blacklist entries yet)
    else:
        schema = {
            "type": "object",
            "properties": {
                "solution": {
                    "type": "string",
                    "description": "Detailed mathematical solution with step-by-step reasoning"
                },
                "method": {
                    "type": "string",
                    "description": "Mathematical method or technique used"
                },
                "final_answer": {
                    "type": "integer",
                    "minimum": min_val,
                    "maximum": max_val,
                    "description": f"Final numerical answer in range [{min_val}, {max_val}]."
                }
            },
            "required": ["solution", "method", "final_answer"]
        }

    return schema


def get_schema_metadata(schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract metadata about the schema for logging/debugging.

    Args:
        schema: JSON schema

    Returns:
        Metadata dict with constraint type, blacklisted_values, etc.
    """
    final_answer = schema.get("properties", {}).get("final_answer", {})

    # Check for different constraint types
    has_not_constraint = "not" in final_answer
    has_enum = "enum" in final_answer
    has_anyof = "anyOf" in final_answer

    # Extract blacklisted values (from "not" constraint in description)
    blacklisted_values = []
    if has_not_constraint:
        blacklisted_values = final_answer.get("not", {}).get("enum", [])
    elif has_anyof:
        # For anyOf, extract blacklisted values from description
        # Example: "FORBIDDEN (proven incorrect): [4048, 4050]"
        desc = final_answer.get("description", "")
        import re
        match = re.search(r'FORBIDDEN.*?:\s*\[([^\]]+)\]', desc)
        if match:
            blacklisted_str = match.group(1)
            blacklisted_values = [int(x.strip()) for x in blacklisted_str.split(",")]

    # Determine constraint type
    if has_anyof:
        constraint_type = "anyOf"
    elif has_not_constraint:
        constraint_type = "not"
    elif has_enum:
        constraint_type = "enum"
    else:
        constraint_type = "range"

    # Extract range info
    has_range = "minimum" in final_answer and "maximum" in final_answer
    range_val = (final_answer.get("minimum"), final_answer.get("maximum"))

    # For anyOf, extract range from first and last constraints
    if has_anyof and not has_range:
        anyof_list = final_answer.get("anyOf", [])
        if anyof_list:
            # Get min from first range
            first_range = anyof_list[0]
            min_val = first_range.get("minimum", first_range.get("enum", [None])[0])

            # Get max from last range
            last_range = anyof_list[-1]
            max_val = last_range.get("maximum", last_range.get("enum", [None])[-1] if last_range.get("enum") else None)

            if min_val is not None and max_val is not None:
                has_range = True
                range_val = (min_val, max_val)

    metadata = {
        "constraint_type": constraint_type,
        "has_enum": has_enum,
        "enum_size": len(final_answer.get("enum", [])),
        "has_not_constraint": has_not_constraint,
        "has_anyof": has_anyof,
        "anyof_segments": len(final_answer.get("anyOf", [])),
        "blacklisted_values": blacklisted_values,
        "has_range": has_range,
        "range": range_val,
        "description": final_answer.get("description", "")
    }

    return metadata


def validate_answer_against_blacklist(answer: Any, blacklist: List[Dict[str, Any]]) -> bool:
    """
    Check if an answer violates the blacklist.

    Args:
        answer: Generated answer (int, str, or dict)
        blacklist: Blacklist entries

    Returns:
        True if answer is valid (not blacklisted), False if blacklisted
    """
    # Extract numerical value from answer
    if isinstance(answer, dict):
        answer = answer.get("final_answer", answer.get("answer", ""))

    try:
        answer_num = int(answer)
    except (ValueError, TypeError):
        # Non-numerical answer, can't check against numerical blacklist
        return True

    # Check against blacklisted numbers
    blacklisted_nums = extract_blacklisted_numbers(blacklist)

    return answer_num not in blacklisted_nums


# Example usage and testing
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python schema_blacklist.py <problem_file>")
        print("Example: python schema_blacklist.py problems/imo06.txt")
        sys.exit(1)

    problem_file = sys.argv[1]

    # Generate schema
    schema = get_blacklist_constrained_schema(problem_file)

    # Print schema
    print("=" * 70)
    print("BLACKLIST-CONSTRAINED JSON SCHEMA")
    print("=" * 70)
    print(json.dumps(schema, indent=2))

    # Print metadata
    print("\n" + "=" * 70)
    print("SCHEMA METADATA")
    print("=" * 70)
    metadata = get_schema_metadata(schema)
    for key, value in metadata.items():
        print(f"  {key}: {value}")

    # Print blacklist info
    print("\n" + "=" * 70)
    print("BLACKLIST INFO")
    print("=" * 70)
    blacklist = load_blacklist(problem_file)
    blacklisted_nums = extract_blacklisted_numbers(blacklist)
    print(f"  Blacklisted numbers: {blacklisted_nums}")
    print(f"  Total FAIL entries: {len([e for e in blacklist if e.get('verdict') == 'FAIL'])}")

    # Validate example answers
    print("\n" + "=" * 70)
    print("VALIDATION EXAMPLES")
    print("=" * 70)
    test_answers = [4048, 4050, 2112, 2025]
    for ans in test_answers:
        is_valid = validate_answer_against_blacklist(ans, blacklist)
        status = "✅ VALID" if is_valid else "❌ BLACKLISTED"
        print(f"  Answer {ans}: {status}")

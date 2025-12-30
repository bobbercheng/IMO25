"""
Test format bridge function to ensure it works correctly.
"""

import sys
sys.path.insert(0, 'code')

from agent_gpt_oss import ensure_tier2_format_compatibility, extract_detailed_solution

def test_short_solution():
    """Test format bridge with short (214 char) solution like problem 1."""
    short_solution = """Summary of admissible \\(k\\)

Combining the constructions and impossibility results we obtain:

\\[
k\\in
\\begin{cases}
\\{0,1,3\\}, & 3\\le n\\le 7,\\\\[2mm]
\\{0,1\\},   & n\\ge 8.
\\end{cases}
\\]

This list is exhaustive.  ∎"""

    print("=" * 80)
    print("TEST 1: Short solution (214 chars, answer-only)")
    print("=" * 80)
    print(f"Input length: {len(short_solution)}")

    formatted = ensure_tier2_format_compatibility(short_solution, "Problem about k and n")
    print(f"Output length: {len(formatted)}")

    # Check markers exist
    assert "### Detailed Solution ###" in formatted, "Missing required marker!"
    print("✓ Required marker added")

    # Check original content preserved
    assert "admissible" in formatted, "Original content lost!"
    print("✓ Original content preserved")

    # Check extraction works now
    extracted = extract_detailed_solution(formatted)
    print(f"Extracted length: {len(extracted)}")
    assert len(extracted) >= 100, f"Extraction failed! Only {len(extracted)} chars"
    print("✓ Extraction successful")

    print()

def test_long_solution_with_marker():
    """Test format bridge with properly formatted solution (problem 2)."""
    long_solution = """### Summary ###

Solution found with answer: \\boxed{\\text{The line through }H\\text{ parallel to }AP\\text{ is tangent}}

### Detailed Solution ###

**Step 1 – Coordinate set‑up.**
Place the line \\(MN\\) on the \\(x\\)-axis and denote
\\[ M=(0,0),\\qquad N=(d,0)... \\]

""" + "x" * 7000  # Simulate long proof

    print("=" * 80)
    print("TEST 2: Long solution with markers (like problem 2)")
    print("=" * 80)
    print(f"Input length: {len(long_solution)}")

    formatted = ensure_tier2_format_compatibility(long_solution, "Problem about geometry")
    print(f"Output length: {len(formatted)}")

    # Should return unchanged
    assert formatted == long_solution, "Should not modify already-formatted solution!"
    print("✓ Already-formatted solution unchanged")

    # Check extraction works
    extracted = extract_detailed_solution(formatted)
    print(f"Extracted length: {len(extracted)}")
    assert len(extracted) > 6000, f"Extraction truncated! Only {len(extracted)} chars"
    print("✓ Extraction preserves content")

    print()

def test_medium_solution_without_marker():
    """Test format bridge with medium-length solution (500-1000 chars)."""
    medium_solution = """We prove the result by construction.

For \\(3 \\le n \\le 7\\), we can construct configurations with \\(k \\in \\{0,1,3\\}\\) sunny lines:

- \\(k=0\\): Use only horizontal, vertical, and diagonal lines
- \\(k=1\\): Replace one non-sunny line with a sunny line
- \\(k=3\\): All three lines are sunny with appropriate slopes

For \\(n \\ge 8\\), the constraint forces \\(k \\in \\{0,1\\}\\) only.

The complete answer is:
\\[
k\\in
\\begin{cases}
\\{0,1,3\\}, & 3\\le n\\le 7,\\\\
\\{0,1\\},   & n\\ge 8.
\\end{cases}
\\]

This covers all lattice points required by the problem. \\(\\boxed{\\text{Answer above}}\\)"""

    print("=" * 80)
    print("TEST 3: Medium solution without marker (500-1000 chars)")
    print("=" * 80)
    print(f"Input length: {len(medium_solution)}")

    formatted = ensure_tier2_format_compatibility(medium_solution, "Problem")
    print(f"Output length: {len(formatted)}")

    # Should add markers
    assert "### Detailed Solution ###" in formatted, "Missing required marker!"
    print("✓ Required marker added")

    # Should preserve content
    assert "construction" in formatted, "Original content lost!"
    print("✓ Original content preserved")

    # Should NOT add truncation warning (length > 300)
    assert "truncated" not in formatted, "Should not warn about truncation for 500+ char solutions"
    print("✓ No false truncation warning")

    print()

def test_extract_detailed_solution_improved():
    """Test improved extract_detailed_solution with content-based validation."""
    print("=" * 80)
    print("TEST 4: Improved extract_detailed_solution validation")
    print("=" * 80)

    # Test 1: Short but valid proof (200 chars with math)
    short_valid = """We have \\(x^2 + y^2 = r^2\\).
Therefore \\(x = r\\cos\\theta\\) and \\(y = r\\sin\\theta\\).
Thus the distance is \\[d = \\sqrt{x^2 + y^2} = r.\\]
Hence \\boxed{r}.
"""
    print(f"\nTest 4a: Short valid proof ({len(short_valid)} chars)")
    extracted = extract_detailed_solution(short_valid)
    assert len(extracted) > 0, "Should accept short but valid math proof!"
    print(f"✓ Accepted: {len(extracted)} chars")

    # Test 2: Very short answer-only (< 100 chars)
    too_short = "The answer is \\boxed{5}."
    print(f"\nTest 4b: Too short ({len(too_short)} chars)")
    extracted = extract_detailed_solution(too_short)
    assert len(extracted) == 0, "Should reject very short answer-only"
    print("✓ Rejected correctly")

    # Test 3: Solution with markers
    with_marker = "### Detailed Solution ###\n\nThis is the proof..."
    print(f"\nTest 4c: With marker ({len(with_marker)} chars)")
    extracted = extract_detailed_solution(with_marker)
    assert "This is the proof" in extracted, "Should extract after marker"
    print(f"✓ Extracted: {len(extracted)} chars")

    print()

if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING FORMAT BRIDGE AND IMPROVED EXTRACTION")
    print("="*80 + "\n")

    test_short_solution()
    test_long_solution_with_marker()
    test_medium_solution_without_marker()
    test_extract_detailed_solution_improved()

    print("="*80)
    print("ALL TESTS PASSED ✓")
    print("="*80)
    print("\nFixes implemented:")
    print("1. ✓ Format bridge wraps solutions in required TIER 2 markers")
    print("2. ✓ Improved content validation (100-char threshold, content-based)")
    print("3. ✓ Handles short/medium/long solutions appropriately")
    print("4. ✓ Preserves already-formatted solutions unchanged")

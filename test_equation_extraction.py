#!/usr/bin/env python3
"""
Test the improved equation extraction for LaTeX format.
"""

import sys
sys.path.insert(0, '/home/user/IMO25/code')

from tier2_refinement import extract_equations_from_proof, clean_latex_equation

# Test case 1: LaTeX display equations with \tag{}
test_proof_1 = r"""
Because the circles intersect, we have:

\[
AB\perp MN .
\tag{5}
\]

The point P satisfies:

\[
PA=PC=PD .
\tag{4}
\]

And the coordinates are:

\[
A=\Bigl(\tfrac23,\;\tfrac{4\sqrt2}{3}\Bigr),\qquad
B=\Bigl(\tfrac23,\;-\tfrac{4\sqrt2}{3}\Bigr).
\]

The circumcenter is:

\[
P=(2,\,-2\sqrt2).
\]
"""

print("="*80)
print("TEST 1: LaTeX display equations with \\tag{}")
print("="*80)
equations_1 = extract_equations_from_proof(test_proof_1)
print(f"\nExtracted {len(equations_1)} equations:")
for i, eq in enumerate(equations_1, 1):
    print(f"  {i}. {eq}")

# Expected: Should extract algebraic equations (PA=PC=PD, coordinates)
# Should skip geometric equation (AB⊥MN)

# Test case 2: Inline numbered equations
test_proof_2 = """
We have the following equations:

(3.1) x0 = (r^2 - R^2 + d^2) / (2*d)

(3.2) y0 = sqrt(r^2 - x0^2)

(3.3) p = (-r + d + R) / 2
"""

print("\n" + "="*80)
print("TEST 2: Inline numbered equations")
print("="*80)
equations_2 = extract_equations_from_proof(test_proof_2)
print(f"\nExtracted {len(equations_2)} equations:")
for i, eq in enumerate(equations_2, 1):
    print(f"  {i}. {eq}")

# Test case 3: Complex LaTeX with fractions
test_proof_3 = r"""
The distance formula gives:

\[
d=\frac{|(1.375)(2.076)-(-6.493)(0.418)|}{\sqrt{1.375^{2}+6.493^{2}}}
\]

And the angle is:

\[
\angle BFE\approx 38.9^{\circ}.
\]
"""

print("\n" + "="*80)
print("TEST 3: LaTeX with fractions and special symbols")
print("="*80)
equations_3 = extract_equations_from_proof(test_proof_3)
print(f"\nExtracted {len(equations_3)} equations:")
for i, eq in enumerate(equations_3, 1):
    print(f"  {i}. {eq}")

# Test case 4: Test clean_latex_equation directly
print("\n" + "="*80)
print("TEST 4: LaTeX cleaning function")
print("="*80)

test_cases = [
    (r"\frac{a}{b} = c", "Fraction conversion"),
    (r"\sqrt{x^2 + y^2} = r", "Square root"),
    (r"AB\perp CD", "Geometric symbol (should skip)"),
    (r"\tfrac{2}{3}", "tfrac variant"),
    (r"\left(\frac{1}{2}\right)", "Nested with sizing"),
]

for latex, desc in test_cases:
    cleaned = clean_latex_equation(latex)
    print(f"\n{desc}:")
    print(f"  Input:  {latex}")
    print(f"  Output: {cleaned if cleaned else '(skipped)'}")

print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"Test 1: {len(equations_1)} equations extracted (expected: 3-4, skip geometric)")
print(f"Test 2: {len(equations_2)} equations extracted (expected: 3)")
print(f"Test 3: {len(equations_3)} equations extracted (expected: 1-2)")
print("\n✅ If numbers look reasonable, equation extraction is working!")

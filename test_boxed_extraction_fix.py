#!/usr/bin/env python3
"""
Test the fixed extract_boxed_answer() function with nested LaTeX braces.
"""

import sys
sys.path.insert(0, 'code')

from tier2_refinement import extract_boxed_answer

print("="*80)
print("BOXED ANSWER EXTRACTION - REGRESSION TEST")
print("="*80)

# Test cases from actual TIER 2 runs
test_cases = [
    {
        "name": "Problem 2 Answer (nested dfrac and Bigl)",
        "solution": r"""
Some text before...

\boxed{P=\Bigl(X_{c},-\dfrac{X_{c}(r+x_{0})}{y_{0}}\Bigr)}

Some text after...
        """,
        "expected": r"P=\Bigl(X_{c},-\dfrac{X_{c}(r+x_{0})}{y_{0}}\Bigr)"
    },
    {
        "name": "Simple answer (no nested braces)",
        "solution": r"The answer is \boxed{42}.",
        "expected": "42"
    },
    {
        "name": "Answer with spacing (\\;)",
        "solution": r"\boxed{P=\Bigl(X_{c},\;-\dfrac{X_{c}(r+x_{0})}{y_{0}}\Bigr)}",
        "expected": r"P=\Bigl(X_{c},\;-\dfrac{X_{c}(r+x_{0})}{y_{0}}\Bigr)"
    },
    {
        "name": "Deeply nested braces",
        "solution": r"\boxed{\frac{a+\frac{b}{c}}{d+\frac{e}{f}}}",
        "expected": r"\frac{a+\frac{b}{c}}{d+\frac{e}{f}}"
    },
    {
        "name": "boxed without backslash",
        "solution": r"The result is boxed{x^2+y^2}.",
        "expected": "x^2+y^2"
    },
    {
        "name": "No boxed answer",
        "solution": "Just some text without boxed content.",
        "expected": None
    }
]

print("\nRunning tests...\n")

all_passed = True
for i, test in enumerate(test_cases, 1):
    extracted = extract_boxed_answer(test["solution"])
    passed = extracted == test["expected"]
    all_passed = all_passed and passed

    status = "✓ PASS" if passed else "✗ FAIL"
    print(f"Test {i}: {test['name']}")
    print(f"  Status: {status}")
    if not passed:
        print(f"  Expected: {test['expected']}")
        print(f"  Got:      {extracted}")
    print()

print("="*80)
if all_passed:
    print("✓✓ ALL TESTS PASSED!")
    print("✓✓ Nested brace extraction is working correctly!")
else:
    print("✗✗ SOME TESTS FAILED!")
    print("✗✗ Check the implementation of extract_boxed_answer()")
print("="*80)

sys.exit(0 if all_passed else 1)

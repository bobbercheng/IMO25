"""
Quick test to validate the TIER 2 parsing fix works with actual Problem 2 feedback
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'code'))

from tier2_refinement import parse_verification_feedback

# Actual verification feedback from Problem 2 log
actual_feedback = """
### List of Findings
* **Location:** Lemma 2 – "\(AE\perp PN\) and \(AF\perp PM\)..."
  * **Issue:** **Critical Error** – the claimed perpendicularities are false
* **Location:** Lemma 3 – "\(A\) lies on the circum‑circle..."
  * **Issue:** **Critical Error** – the conclusion relies on Lemma 2...
* **Location:** Lemma 4 – "\(E\) is the second intersection of \(PN\)..."
  * **Issue:** **Critical Error** – definition depends on the false Lemma 2
* **Location:** Final claim – "line through \(H\) parallel to \(AP\)..."
  * **Issue:** **Critical Error** – relies entirely on the broken lemmas
* **Location:** General proof structure
  * **Issue:** **Justification Gap** – no independent verification provided
"""

print("="*80)
print("TIER 2 PARSING FIX - VALIDATION TEST")
print("="*80)

print("\nTesting with actual Problem 2 verification feedback...\n")

issues = parse_verification_feedback(actual_feedback)

print(f"✓ Parsed {len(issues)} issues:")
print()

for i, issue in enumerate(issues, 1):
    print(f"{i}. Type: {issue['type']}")
    print(f"   Location: {issue['location'][:60]}...")
    print(f"   Description: {issue['description'][:60]}...")
    print()

# Validate results
critical_errors = [i for i in issues if i['type'] == 'CRITICAL_ERROR']
gaps = [i for i in issues if i['type'] == 'JUSTIFICATION_GAP']

print("="*80)
print("VALIDATION RESULTS:")
print("="*80)
print(f"Critical Errors: {len(critical_errors)}")
print(f"Justification Gaps: {len(gaps)}")
print(f"Total: {len(issues)}")
print()

expected_total = 5
if len(issues) == expected_total:
    print(f"✓✓ SUCCESS: Parsed all {expected_total} issues correctly!")
    print("✓✓ TIER 2 parsing fix is working!")
    sys.exit(0)
else:
    print(f"✗ FAILED: Expected {expected_total} issues, got {len(issues)}")
    sys.exit(1)

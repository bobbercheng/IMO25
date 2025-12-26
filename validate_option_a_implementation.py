#!/usr/bin/env python3
"""
Option A Implementation Validation Script

Validates that Option A changes are correctly implemented in code/agent_oai.py:
1. Enhanced verification constraints (7 guidelines including construction check)
2. max_completion_tokens parameter in build_request_payload
3. Proper constraint integration in verify_solution function

This validation runs WITHOUT API calls - just code inspection.
"""

import os
import sys
import re

def validate_implementation():
    """Validate Option A implementation in agent_oai.py"""

    print("="*80)
    print("OPTION A IMPLEMENTATION VALIDATION")
    print("="*80)

    # Read agent_oai.py
    agent_file = os.path.join(os.path.dirname(__file__), 'code', 'agent_oai.py')
    if not os.path.exists(agent_file):
        print(f"❌ ERROR: {agent_file} not found")
        return False

    with open(agent_file, 'r') as f:
        content = f.read()

    all_checks_passed = True

    # Check 1: max_completion_tokens parameter exists
    print("\n" + "─"*80)
    print("CHECK 1: max_completion_tokens parameter in build_request_payload")
    print("─"*80)

    if re.search(r'def build_request_payload.*max_completion_tokens', content, re.DOTALL):
        print("✓ PASS: Function signature includes max_completion_tokens parameter")
    else:
        print("❌ FAIL: max_completion_tokens parameter not found in function signature")
        all_checks_passed = False

    if 'max_completion_tokens": max_completion_tokens' in content or '"max_completion_tokens": 8192' in content:
        print("✓ PASS: max_completion_tokens added to payload")
    else:
        print("❌ FAIL: max_completion_tokens not added to payload")
        all_checks_passed = False

    # Check 2: Verification constraints exist
    print("\n" + "─"*80)
    print("CHECK 2: Enhanced verification constraints in verify_solution")
    print("─"*80)

    constraints_to_check = [
        ("Output Length Limit", r"Output Length Limit.*≤2000 tokens"),
        ("Evaluate, Don't Re-Prove", r"Evaluate, Don't Re-Prove"),
        ("No Manual Case Testing", r"No Manual Case Testing"),
        ("Trust Valid Methods", r"Trust Valid Methods"),
        ("Early Classification", r"Early Classification"),
        ("Focus on Missing Elements", r"Focus on What's Missing"),
        ("Construction Verification", r"Construction Verification.*FIND/DETERMINE")
    ]

    for constraint_name, pattern in constraints_to_check:
        if re.search(pattern, content, re.IGNORECASE | re.DOTALL):
            print(f"✓ PASS: Constraint '{constraint_name}' found")
        else:
            print(f"❌ FAIL: Constraint '{constraint_name}' not found")
            all_checks_passed = False

    # Check 3: Construction verification examples
    print("\n" + "─"*80)
    print("CHECK 3: Construction verification examples (Constraint 7)")
    print("─"*80)

    if re.search(r'For k=3.*use lines.*covering points', content, re.IGNORECASE):
        print("✓ PASS: PASS example found (explicit construction)")
    else:
        print("❌ FAIL: PASS example not found")
        all_checks_passed = False

    if re.search(r'k=3 is possible.*no explicit construction', content, re.IGNORECASE):
        print("✓ PASS: FAIL example found (abstract claim)")
    else:
        print("❌ FAIL: FAIL example not found")
        all_checks_passed = False

    # Check 4: Constraint integration in verify_solution
    print("\n" + "─"*80)
    print("CHECK 4: Constraints integrated in verify_solution function")
    print("─"*80)

    # Find verify_solution function
    verify_match = re.search(r'def verify_solution\(.*?\):(.*?)(?=\ndef |\Z)', content, re.DOTALL)
    if verify_match:
        verify_content = verify_match.group(1)

        if 'verification_constraint' in verify_content:
            print("✓ PASS: verification_constraint variable found in verify_solution")
        else:
            print("❌ FAIL: verification_constraint variable not found")
            all_checks_passed = False

        if re.search(r'CRITICAL CONSTRAINTS FOR VERIFICATION', verify_content):
            print("✓ PASS: Constraint header found in verify_solution")
        else:
            print("❌ FAIL: Constraint header not found")
            all_checks_passed = False
    else:
        print("❌ FAIL: Could not find verify_solution function")
        all_checks_passed = False

    # Check 5: Comment indicating Option A
    print("\n" + "─"*80)
    print("CHECK 5: Option A implementation markers")
    print("─"*80)

    if 'Option A' in content or 'OPTION A' in content:
        print("✓ PASS: Option A marker found in comments")
    else:
        print("⚠️  WARNING: No explicit Option A marker (not critical)")

    # Final summary
    print("\n" + "="*80)
    print("VALIDATION SUMMARY")
    print("="*80)

    if all_checks_passed:
        print("✅ ALL CHECKS PASSED - Option A implementation is correct")
        print("\nImplementation includes:")
        print("  • 7 verification constraints (including construction check)")
        print("  • max_completion_tokens=8192 for truncation prevention")
        print("  • Proper integration in verify_solution function")
        print("\nReady for API testing with OpenAI o3 model.")
        return True
    else:
        print("❌ SOME CHECKS FAILED - Review implementation")
        return False


def extract_constraints():
    """Extract and display the full constraint text"""
    agent_file = os.path.join(os.path.dirname(__file__), 'code', 'agent_oai.py')

    with open(agent_file, 'r') as f:
        content = f.read()

    # Find verification_constraint section
    match = re.search(
        r'verification_constraint = """(.*?)"""',
        content,
        re.DOTALL
    )

    if match:
        print("\n" + "="*80)
        print("EXTRACTED VERIFICATION CONSTRAINTS")
        print("="*80)
        print(match.group(1))
        print("="*80)


if __name__ == "__main__":
    print("Validating Option A implementation in code/agent_oai.py...\n")

    success = validate_implementation()

    if success and "--show-constraints" in sys.argv:
        extract_constraints()

    sys.exit(0 if success else 1)

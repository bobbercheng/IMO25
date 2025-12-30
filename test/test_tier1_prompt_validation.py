#!/usr/bin/env python3
"""
TIER 1 Optimality Prompt Validation Tests
Validates that the verification prompts include optimality checking logic

This test doesn't require API calls - just checks prompt content

Date: 2025-12-30
"""

import os
import sys

# Add code directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'code'))

def test_verification_prompt_contains_optimality():
    """Test that verification_system_prompt includes Level 1.5 optimality check"""
    print("\n" + "="*80)
    print("TEST 1: Verification Prompt Contains Optimality Logic")
    print("="*80)

    try:
        from agent_oai import verification_system_prompt

        # Check for key Level 1.5 components
        checks = [
            ("Level 1.5 header", "**LEVEL 1.5: Check Optimality"),
            ("Optimization detection", "MINIMUM/MAXIMUM"),
            ("Small-case testing", "Test small cases"),
            ("Perfect square detection", "perfect square"),
            ("Formula simplicity check", "simple formula"),
            ("SUSPICIOUS_OPTIMALITY verdict", "SUSPICIOUS_OPTIMALITY"),
            ("Example Problem 6", "2025 = 45²" or "2025=45"),
        ]

        passed = 0
        failed = 0

        for check_name, keyword in checks:
            if keyword in verification_system_prompt:
                print(f"✅ {check_name}: Found '{keyword}'")
                passed += 1
            else:
                print(f"❌ {check_name}: Missing '{keyword}'")
                failed += 1

        print(f"\n{passed}/{len(checks)} checks passed")

        if failed == 0:
            print("\n✅ TEST PASSED: Verification prompt includes Level 1.5 optimality logic")
            return True
        else:
            print(f"\n❌ TEST FAILED: {failed} required components missing")
            return False

    except Exception as e:
        print(f"\n❌ TEST ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_json_schema_accepts_suspicious():
    """Test that verdict validation accepts SUSPICIOUS_OPTIMALITY"""
    print("\n" + "="*80)
    print("TEST 2: JSON Schema Accepts SUSPICIOUS_OPTIMALITY")
    print("="*80)

    try:
        from agent_gpt_oss import validate_verdict_schema

        # Test cases
        test_verdicts = [
            {"verdict": "PASS", "confidence": 0.9, "issues": [], "answer_correctness": "CORRECT", "reasoning": "test"},
            {"verdict": "FAIL", "confidence": 0.8, "issues": [], "answer_correctness": "INCORRECT", "reasoning": "test"},
            {"verdict": "SUSPICIOUS_OPTIMALITY", "confidence": 0.7, "issues": [], "answer_correctness": "CORRECT", "reasoning": "test"},
        ]

        passed = 0
        failed = 0

        for verdict_obj in test_verdicts:
            is_valid, error_msg = validate_verdict_schema(verdict_obj)
            verdict_type = verdict_obj["verdict"]

            if is_valid:
                print(f"✅ {verdict_type}: Accepted by schema")
                passed += 1
            else:
                print(f"❌ {verdict_type}: Rejected - {error_msg}")
                failed += 1

        print(f"\n{passed}/{len(test_verdicts)} verdict types accepted")

        if failed == 0:
            print("\n✅ TEST PASSED: JSON schema accepts all verdict types including SUSPICIOUS_OPTIMALITY")
            return True
        else:
            print(f"\n❌ TEST FAILED: {failed} verdict type(s) rejected")
            return False

    except Exception as e:
        print(f"\n❌ TEST ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_output_format_documentation():
    """Test that output format documentation includes Level 1.5"""
    print("\n" + "="*80)
    print("TEST 3: Output Format Documentation Includes Level 1.5")
    print("="*80)

    try:
        from agent_oai import verification_system_prompt

        # Check for output format documentation
        checks = [
            ("Level 1.5 Result documentation", "**Level 1.5 Result:**"),
            ("SUSPICIOUS_OPTIMALITY verdict type", "SUSPICIOUS_OPTIMALITY"),
            ("Optimality concerns explanation", "optimality concerns detected"),
        ]

        passed = 0
        failed = 0

        for check_name, keyword in checks:
            if keyword in verification_system_prompt:
                print(f"✅ {check_name}: Found")
                passed += 1
            else:
                print(f"❌ {check_name}: Missing")
                failed += 1

        print(f"\n{passed}/{len(checks)} documentation checks passed")

        if failed == 0:
            print("\n✅ TEST PASSED: Output format properly documents Level 1.5")
            return True
        else:
            print(f"\n❌ TEST FAILED: {failed} documentation item(s) missing")
            return False

    except Exception as e:
        print(f"\n❌ TEST ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all TIER 1 prompt validation tests"""
    print("\n" + "="*80)
    print("TIER 1 OPTIMALITY - PROMPT VALIDATION TESTS")
    print("="*80)
    print("Validating that verification prompts include optimality checking")
    print("Date: 2025-12-30")

    results = []

    # Run tests
    results.append(("Verification Prompt Content", test_verification_prompt_contains_optimality()))
    results.append(("JSON Schema Validation", test_json_schema_accepts_suspicious()))
    results.append(("Output Format Documentation", test_output_format_documentation()))

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 ALL VALIDATION TESTS PASSED - TIER 1 Prompts Correctly Updated!")
        print("\nNext Step: Run with API to test actual verification behavior:")
        print("  export GPT_OSS_API_KEY=your_key")
        print("  python test_tier1_optimality.py")
        return True
    else:
        print(f"\n⚠️  {total - passed} test(s) failed - Review prompt modifications")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

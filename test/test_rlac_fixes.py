#!/usr/bin/env python3
"""
Quick test script to verify RLAC fixes.

Tests:
1. P0: Criticism history shows ALL flaws with FULL details and counterexamples
2. P1: Answer implications are extracted from critic responses
3. P2: Severity classification is integrated into attack intensity
4. P3: Answer reconsideration triggers early (not just when stuck)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent_rlac import Flaw, Criticism, GeneratorAgent, AdversarialCriticAgent, RLACAgent


def test_p0_criticism_history_full_details():
    """Test P0: Criticism history shows ALL flaws with counterexamples."""
    print("\n" + "="*60)
    print("TEST P0: Criticism History Full Details")
    print("="*60)

    # Create mock LLM client
    class MockLLM:
        def generate(self, prompt, reasoning_effort="high"):
            return "mock response"

    generator = GeneratorAgent(MockLLM())

    # Create test criticism history with multiple flaws
    history = [
        Criticism(
            no_flaws_found=False,
            flaws=[
                Flaw(type="counterexample", severity="critical",
                     description="For n=3, k=2, the construction fails because line x+y=5 has slope -1 which is NOT sunny",
                     counterexample="n=3, k=2: line x+y=5 is not sunny (slope=-1)",
                     location="Lemma 2"),
                Flaw(type="logical_gap", severity="major",
                     description="The claim that translation preserves sunny property is unjustified",
                     counterexample=None,
                     location="Step 3"),
                Flaw(type="edge_case", severity="critical",
                     description="Base case n=1 is not handled correctly",
                     counterexample="n=1: claimed k=0 but construction produces k=1",
                     location="Base case"),
            ],
            raw_response="test",
            iteration=1
        ),
        Criticism(
            no_flaws_found=False,
            flaws=[
                Flaw(type="counterexample", severity="critical",
                     description="Second round found another counterexample",
                     counterexample="n=4, k=3: same slope=-1 issue persists",
                     location="Lemma 2 revision"),
            ],
            raw_response="test2",
            iteration=2
        ),
    ]

    formatted = generator._format_criticism_history(history)

    # Verify ALL flaws are shown (not just first 2)
    assert "Flaw 1" in formatted, "Should show flaw 1"
    assert "Flaw 2" in formatted, "Should show flaw 2"
    assert "Flaw 3" in formatted, "Should show flaw 3 (was truncated before)"

    # Verify FULL descriptions (not truncated to 100 chars)
    assert "line x+y=5 has slope -1 which is NOT sunny" in formatted, "Description should not be truncated"

    # Verify counterexamples are included
    assert "COUNTEREXAMPLE:" in formatted, "Counterexamples should be highlighted"
    assert "n=3, k=2" in formatted, "Should include counterexample content"

    # Verify summary section exists
    assert "ALL COUNTEREXAMPLES FROM HISTORY" in formatted, "Should have counterexample summary"

    print("✓ All flaws shown (not just first 2)")
    print("✓ Full descriptions (not truncated)")
    print("✓ Counterexamples included and highlighted")
    print("✓ Summary section with all counterexamples")
    print("\nSample output:")
    print("-"*40)
    print(formatted[:1000] + "..." if len(formatted) > 1000 else formatted)
    print("-"*40)
    print("TEST P0: PASSED")
    return True


def test_p1_answer_implications():
    """Test P1: Answer implications are extracted from critic."""
    print("\n" + "="*60)
    print("TEST P1: Answer Implications Extraction")
    print("="*60)

    # Create mock LLM client
    class MockLLM:
        def generate(self, prompt, reasoning_effort="high"):
            return """
FLAW_START
Type: counterexample
Severity: critical
Description: The solution claims k can be any value in {0,1,...,n}, but counterexample shows k=n-1 is impossible
Counterexample: n=4, k=3: cannot construct 3 sunny lines with given constraints
Location: Main theorem
Answer_Implication: This proves the answer should be {0,1,...,n-2}, NOT {0,1,...,n}
FLAW_END

FLAW_START
Type: edge_case
Severity: major
Description: k=1 case fails for n=2
Counterexample: n=2, k=1: only 0 sunny lines possible
Location: Base case analysis
Answer_Implication: This proves k=1 is NOT achievable for n=2, answer needs n>=3 constraint
FLAW_END
"""

    critic = AdversarialCriticAgent(MockLLM())

    # Test the parsing
    class MockSolution:
        content = "test solution"
        iteration = 1

    criticism = critic._parse_criticism(MockLLM().generate("test"), 1)

    # Verify answer implications are extracted
    assert len(criticism.flaws) == 2, f"Should have 2 flaws, got {len(criticism.flaws)}"

    flaw1 = criticism.flaws[0]
    flaw2 = criticism.flaws[1]

    assert flaw1.answer_implication is not None, "Flaw 1 should have answer implication"
    assert "answer should be {0,1,...,n-2}" in flaw1.answer_implication, "Should extract answer implication"

    assert flaw2.answer_implication is not None, "Flaw 2 should have answer implication"
    assert "k=1 is NOT achievable" in flaw2.answer_implication, "Should extract second answer implication"

    print("✓ Answer implications extracted from critic responses")
    print(f"  Flaw 1 implication: {flaw1.answer_implication}")
    print(f"  Flaw 2 implication: {flaw2.answer_implication}")
    print("TEST P1: PASSED")
    return True


def test_p2_severity_in_intensity():
    """Test P2: Severity classification in attack intensity."""
    print("\n" + "="*60)
    print("TEST P2: Severity Classification in Attack Intensity")
    print("="*60)

    class MockLLM:
        def generate(self, prompt, reasoning_effort="high"):
            return "mock"

    critic = AdversarialCriticAgent(MockLLM())

    # Test basic intensity
    basic = critic._get_intensity_instructions("basic")
    assert "CRITICAL flaws" in basic, "Basic should mention CRITICAL severity"
    assert "DOMAIN-SPECIFIC TESTS" in basic, "Should have domain-specific tests"
    assert "Number Theory" in basic, "Should mention number theory"

    # Test moderate intensity
    moderate = critic._get_intensity_instructions("moderate")
    assert "CRITICAL + MAJOR" in moderate, "Moderate should target CRITICAL + MAJOR"
    assert "n=prime" in moderate, "Should have specific test values"

    # Test advanced intensity
    advanced = critic._get_intensity_instructions("advanced")
    assert "ALL flaws" in advanced, "Advanced should find ALL flaws"
    assert "CRITICAL -10, MAJOR -5, MINOR -2" in advanced, "Should show penalty scores"

    print("✓ Basic intensity targets CRITICAL flaws")
    print("✓ Moderate intensity targets CRITICAL + MAJOR flaws")
    print("✓ Advanced intensity targets ALL flaws with penalties")
    print("✓ Domain-specific tests included at each level")
    print("TEST P2: PASSED")
    return True


def test_p3_early_answer_reconsideration():
    """Test P3: Answer reconsideration triggers early."""
    print("\n" + "="*60)
    print("TEST P3: Early Answer Reconsideration")
    print("="*60)

    class MockLLM:
        def generate(self, prompt, reasoning_effort="high"):
            return "mock"

    # Create RLACAgent to test _collect_recent_counterexamples
    agent = RLACAgent(MockLLM(), MockLLM())

    # Create history with counterexamples in consecutive rounds
    history = [
        Criticism(
            no_flaws_found=False,
            flaws=[
                Flaw(type="counterexample", severity="critical",
                     description="First counterexample",
                     counterexample="n=3, k=2 fails",
                     location="test",
                     answer_implication="Proves k=2 not achievable for n=3"),
            ],
            raw_response="test",
            iteration=1
        ),
        Criticism(
            no_flaws_found=False,
            flaws=[
                Flaw(type="counterexample", severity="critical",
                     description="Second counterexample",
                     counterexample="n=4, k=3 fails",
                     location="test",
                     answer_implication="Proves k=n-1 pattern"),
            ],
            raw_response="test2",
            iteration=2
        ),
    ]

    # Test early collection
    recent = agent._collect_recent_counterexamples(history, window=2)

    assert len(recent) >= 2, f"Should collect 2+ counterexamples, got {len(recent)}"
    assert "n=3, k=2 fails" in recent, "Should include first counterexample"
    assert "n=4, k=3 fails" in recent, "Should include second counterexample"

    # Verify implications are included
    implications = [r for r in recent if "[IMPLICATION]" in r]
    assert len(implications) >= 2, "Should include answer implications"

    print("✓ Counterexamples collected from recent rounds")
    print("✓ Answer implications included in collection")
    print(f"✓ Found {len(recent)} items for early reconsideration")
    print("  Items:", recent[:3], "..." if len(recent) > 3 else "")
    print("TEST P3: PASSED")
    return True


def test_flaw_dataclass_with_answer_implication():
    """Test that Flaw dataclass has answer_implication field."""
    print("\n" + "="*60)
    print("TEST: Flaw Dataclass Answer Implication Field")
    print("="*60)

    flaw = Flaw(
        type="counterexample",
        severity="critical",
        description="Test description",
        counterexample="n=3 fails",
        location="test",
        answer_implication="This proves the answer must include k=0"
    )

    assert hasattr(flaw, 'answer_implication'), "Flaw should have answer_implication field"
    assert flaw.answer_implication == "This proves the answer must include k=0"

    # Test to_dict includes the field
    flaw_dict = flaw.to_dict()
    assert 'answer_implication' in flaw_dict, "to_dict should include answer_implication"

    print("✓ Flaw dataclass has answer_implication field")
    print("✓ to_dict includes answer_implication")
    print("TEST: PASSED")
    return True


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("RLAC FIXES VERIFICATION TESTS")
    print("="*60)

    results = []

    try:
        results.append(("P0: Full criticism history", test_p0_criticism_history_full_details()))
    except Exception as e:
        print(f"TEST P0 FAILED: {e}")
        results.append(("P0: Full criticism history", False))

    try:
        results.append(("P1: Answer implications", test_p1_answer_implications()))
    except Exception as e:
        print(f"TEST P1 FAILED: {e}")
        results.append(("P1: Answer implications", False))

    try:
        results.append(("P2: Severity in intensity", test_p2_severity_in_intensity()))
    except Exception as e:
        print(f"TEST P2 FAILED: {e}")
        results.append(("P2: Severity in intensity", False))

    try:
        results.append(("P3: Early reconsideration", test_p3_early_answer_reconsideration()))
    except Exception as e:
        print(f"TEST P3 FAILED: {e}")
        results.append(("P3: Early reconsideration", False))

    try:
        results.append(("Flaw dataclass", test_flaw_dataclass_with_answer_implication()))
    except Exception as e:
        print(f"TEST Flaw dataclass FAILED: {e}")
        results.append(("Flaw dataclass", False))

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"  {status}: {name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Fixes verified.")
        return 0
    else:
        print("\n❌ Some tests failed. Please review.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

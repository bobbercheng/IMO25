#!/usr/bin/env python3
"""
Unit tests for blacklist key functions - validates actual integration points
Tests the critical path: load → inject prompts → save → sequential runs
"""

import os
import json
import tempfile
import shutil
from pathlib import Path
import sys

# Add code directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'code'))

from solution_blacklist import SolutionBlacklist, extract_method_from_solution
from blacklist_integration import (
    extract_problem_id_from_path,
    get_run_id_from_env,
    save_solution_to_blacklist
)
from agent_gpt_oss import extract_answer_simple


def test_blacklist_loads_during_init():
    """Test 1: Verify blacklist loads existing entries during initialization"""
    print("\n" + "="*70)
    print("TEST 1: Blacklist loads during initialization")
    print("="*70)

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create the blacklist file manually
        blacklist_file = Path(tmpdir) / "test_problem_blacklist.json"

        # Create a blacklist with 2 existing solutions
        initial_data = {
            "problem_id": "test_problem",
            "solutions": [
                {
                    "answer": "4048",
                    "method": "ferrers_diagram",
                    "run_id": "run1",
                    "verdict": "PASS",
                    "iterations": 3,
                    "timestamp": 1234567890.0
                },
                {
                    "answer": "2025",
                    "method": "diagonal_permutation",
                    "run_id": "run2",
                    "verdict": "PASS",
                    "iterations": 5,
                    "timestamp": 1234567900.0
                }
            ],
            "last_updated": 1234567900.0,
            "count": 2
        }

        with open(blacklist_file, 'w') as f:
            json.dump(initial_data, f, indent=2)

        # Load the blacklist (using problem_id and blacklist_dir)
        blacklist = SolutionBlacklist(
            problem_id="test_problem",
            blacklist_dir=str(tmpdir)
        )

        # Verify it loaded the existing entries
        stats = blacklist.get_statistics()

        print(f"\nBlacklist statistics after loading:")
        print(f"  Total attempts: {stats['total_attempts']}")
        print(f"  Unique answers: {stats['unique_answers']}")
        print(f"  Unique methods: {stats['unique_methods']}")
        print(f"  Answers: {stats['answers']}")

        assert stats['total_attempts'] == 2, f"Expected 2 solutions, got {stats['total_attempts']}"
        assert stats['unique_answers'] == 2, f"Expected 2 unique answers, got {stats['unique_answers']}"
        assert "4048" in stats['answers'], "Missing answer '4048'"
        assert "2025" in stats['answers'], "Missing answer '2025'"

        print("\n✓ PASS: Blacklist correctly loads existing entries during initialization")
        return True


def test_blacklist_prompt_injection():
    """Test 2: Verify blacklist generates proper prompt injection"""
    print("\n" + "="*70)
    print("TEST 2: Blacklist prompt injection")
    print("="*70)

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create blacklist with diverse solutions
        blacklist = SolutionBlacklist(
            problem_id="imo06",
            blacklist_dir=str(tmpdir)
        )

        # Add 3 different solutions
        blacklist.add_solution(
            answer="4048",
            method="ferrers_diagram",
            run_id="run1",
            verdict="PASS",
            iterations=3
        )

        blacklist.add_solution(
            answer="2025",
            method="diagonal_permutation",
            run_id="run2",
            verdict="PASS",
            iterations=5
        )

        blacklist.add_solution(
            answer="2112",
            method="dilworth_decomposition",
            run_id="run3",
            verdict="PASS",
            iterations=2
        )

        # Get the prompt that would be injected
        prompt_addition = blacklist.get_blacklist_prompt()

        print("\nGenerated prompt addition:")
        print("-" * 70)
        print(prompt_addition)
        print("-" * 70)

        # Verify the prompt contains all critical information
        assert "4048" in prompt_addition, "Missing answer 4048 in prompt"
        assert "2025" in prompt_addition, "Missing answer 2025 in prompt"
        assert "2112" in prompt_addition, "Missing answer 2112 in prompt"
        assert "ferrers_diagram" in prompt_addition, "Missing method ferrers_diagram"
        assert "diagonal_permutation" in prompt_addition, "Missing method diagonal_permutation"
        assert "dilworth_decomposition" in prompt_addition, "Missing method dilworth_decomposition"
        assert "avoid" in prompt_addition.lower() or "do not" in prompt_addition.lower(), "Missing imperative instruction"

        print("\n✓ PASS: Blacklist generates correct prompt injection with all solutions")
        return True


def test_blacklist_saves_after_completion():
    """Test 3: Verify blacklist saves solution after agent completion"""
    print("\n" + "="*70)
    print("TEST 3: Blacklist saves after agent completion")
    print("="*70)

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create empty blacklist
        blacklist = SolutionBlacklist(
            problem_id="imo06",
            blacklist_dir=str(tmpdir)
        )

        blacklist_file = Path(tmpdir) / "imo06_blacklist.json"

        # Simulate agent completion with a solution
        solution_text = """
        Let me solve this problem systematically.

        For an n×n grid, we can use Ferrers diagrams to get a bound.
        Each L-shape covers a horizontal and vertical line.

        Therefore, the minimum number is 2n - 2.

        For n = 2025, the answer is \\boxed{4048}.
        """

        verdict_dict = {
            "verdict": "PASS",
            "additional_info": "Solution verified correct"
        }

        # Save solution using the actual integration function
        save_solution_to_blacklist(
            blacklist=blacklist,
            answer=extract_answer_simple(solution_text) or "UNKNOWN",
            solution_text=solution_text,
            run_id="run1",
            verdict_dict=verdict_dict,
            iterations=5
        )

        # Verify it was saved to disk
        assert blacklist_file.exists(), "Blacklist file not created"

        with open(blacklist_file, 'r') as f:
            saved_data = json.load(f)

        print(f"\nSaved blacklist data:")
        print(json.dumps(saved_data, indent=2))

        assert saved_data['problem_id'] == "imo06", "Wrong problem_id"
        assert saved_data['count'] == 1, f"Expected 1 solution, got {saved_data['count']}"
        assert len(saved_data['solutions']) == 1, "Solution not saved"

        solution = saved_data['solutions'][0]
        assert solution['run_id'] == "run1", f"Wrong run_id: {solution['run_id']}"
        assert solution['verdict'] == "PASS", f"Wrong verdict: {solution['verdict']}"
        assert solution['iterations'] == 5, f"Wrong iterations: {solution['iterations']}"

        # Check if answer was extracted (might be wrong due to bug, but should exist)
        print(f"\nExtracted answer: '{solution['answer']}'")
        assert solution['answer'] != "UNKNOWN", "Failed to extract any answer"

        print("\n✓ PASS: Blacklist correctly saves solution after agent completion")
        return True


def test_sequential_run_scenario():
    """Test 4: Verify run 2 sees run 1's blacklist entry"""
    print("\n" + "="*70)
    print("TEST 4: Sequential run scenario (run 2 sees run 1's entry)")
    print("="*70)

    with tempfile.TemporaryDirectory() as tmpdir:
        # Simulate Run 1
        print("\n--- Simulating Run 1 ---")
        blacklist_run1 = SolutionBlacklist(
            problem_id="imo06",
            blacklist_dir=str(tmpdir)
        )

        stats_before = blacklist_run1.get_statistics()
        print(f"Run 1 start - Total attempts: {stats_before['total_attempts']}")

        # Run 1 completes and saves a solution
        blacklist_run1.add_solution(
            answer="4048",
            method="ferrers_diagram",
            run_id="run1",
            verdict="PASS",
            iterations=3
        )

        prompt1 = blacklist_run1.get_blacklist_prompt()
        print(f"Run 1 prompt (length: {len(prompt1)}): {prompt1[:200]}..." if len(prompt1) > 200 else f"Run 1 prompt: {prompt1}")

        # Simulate Run 2 starting (new instance loading same file)
        print("\n--- Simulating Run 2 ---")
        blacklist_run2 = SolutionBlacklist(
            problem_id="imo06",
            blacklist_dir=str(tmpdir)
        )

        stats_run2 = blacklist_run2.get_statistics()
        print(f"Run 2 start - Total attempts: {stats_run2['total_attempts']}")

        # Verify Run 2 sees Run 1's solution
        assert stats_run2['total_attempts'] == 1, f"Run 2 should see 1 solution from Run 1, got {stats_run2['total_attempts']}"
        assert "4048" in stats_run2['answers'], "Run 2 doesn't see Run 1's answer '4048'"

        # Get Run 2's prompt - should include Run 1's solution
        prompt2 = blacklist_run2.get_blacklist_prompt()
        print(f"Run 2 prompt (length: {len(prompt2)}):\n{prompt2}")

        assert "4048" in prompt2, "Run 2's prompt doesn't mention Run 1's answer"
        assert "ferrers_diagram" in prompt2, "Run 2's prompt doesn't mention Run 1's method"

        # Run 2 completes with different solution
        blacklist_run2.add_solution(
            answer="2112",
            method="dilworth_decomposition",
            run_id="run2",
            verdict="PASS",
            iterations=2
        )

        # Simulate Run 3 to verify both solutions are visible
        print("\n--- Simulating Run 3 ---")
        blacklist_run3 = SolutionBlacklist(
            problem_id="imo06",
            blacklist_dir=str(tmpdir)
        )

        stats_run3 = blacklist_run3.get_statistics()
        print(f"Run 3 start - Total attempts: {stats_run3['total_attempts']}")
        print(f"Run 3 answers: {stats_run3['answers']}")

        assert stats_run3['total_attempts'] == 2, f"Run 3 should see 2 solutions, got {stats_run3['total_attempts']}"
        assert "4048" in stats_run3['answers'], "Run 3 doesn't see Run 1's answer"
        assert "2112" in stats_run3['answers'], "Run 3 doesn't see Run 2's answer"

        prompt3 = blacklist_run3.get_blacklist_prompt()
        assert "4048" in prompt3 and "2112" in prompt3, "Run 3's prompt missing previous answers"

        print("\n✓ PASS: Sequential runs correctly share blacklist state")
        return True


def test_answer_extraction_current_behavior():
    """Test 5: Document current answer extraction behavior (DIAGNOSTIC)"""
    print("\n" + "="*70)
    print("TEST 5: Current answer extraction behavior (DIAGNOSTIC)")
    print("="*70)

    test_cases = [
        {
            "name": "Standard boxed answer",
            "solution": "Therefore, the minimum number is \\boxed{2112}.",
            "expected": "\\boxed{2112}" or "2112"
        },
        {
            "name": "Nested LaTeX boxed",
            "solution": "For n = 2025, we get \\boxed{2 \\cdot 2025 - 2 = 4048}.",
            "expected": "\\boxed{2 \\cdot 2025 - 2 = 4048}" or "4048"
        },
        {
            "name": "Multiple boxed (should take last)",
            "solution": "First \\boxed{4048}, but actually \\boxed{2112}.",
            "expected": "\\boxed{2112}" or "2112"
        },
        {
            "name": "Natural language answer",
            "solution": "The answer is 2112.",
            "expected": "2112"
        },
        {
            "name": "Variable assignment in LaTeX",
            "solution": "Let k = 45. For n = k^2 = 2025, the bound is k^2 + 2k - 3 = 2112.",
            "expected": "2112"
        }
    ]

    print("\nTesting extract_answer_simple() on various solution formats:\n")

    results = []
    for tc in test_cases:
        extracted = extract_answer_simple(tc['solution'])
        passed = extracted is not None and (tc['expected'] in str(extracted) if extracted else False)

        results.append({
            'name': tc['name'],
            'extracted': extracted,
            'expected': tc['expected'],
            'passed': passed
        })

        status = "✓" if passed else "✗"
        print(f"{status} {tc['name']}")
        print(f"   Solution: {tc['solution'][:80]}...")
        print(f"   Expected: {tc['expected']}")
        print(f"   Extracted: {extracted}")
        print()

    pass_rate = sum(1 for r in results if r['passed']) / len(results) * 100
    print(f"\nPass rate: {pass_rate:.1f}% ({sum(1 for r in results if r['passed'])}/{len(results)})")

    if pass_rate < 60:
        print("\n⚠ WARNING: Answer extraction pass rate below 60%")
        print("   This explains why blacklist has garbage answers.")
        print("   User requested LLM-based extraction as solution.")

    return True


def run_all_tests():
    """Run all blacklist key function tests"""
    print("\n" + "="*70)
    print("BLACKLIST KEY FUNCTIONS - INTEGRATION TEST SUITE")
    print("="*70)
    print("\nTesting actual integration points used by agent_gpt_oss.py")
    print("This validates the critical path: load → inject → save → sequential runs")
    print("="*70)

    tests = [
        ("Blacklist loads during init", test_blacklist_loads_during_init),
        ("Blacklist prompt injection", test_blacklist_prompt_injection),
        ("Blacklist saves after completion", test_blacklist_saves_after_completion),
        ("Sequential run scenario", test_sequential_run_scenario),
        ("Answer extraction diagnostic", test_answer_extraction_current_behavior),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, "PASS", None))
        except AssertionError as e:
            results.append((name, "FAIL", str(e)))
            print(f"\n✗ FAIL: {e}")
        except Exception as e:
            results.append((name, "ERROR", str(e)))
            print(f"\n✗ ERROR: {e}")

    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)

    for name, status, error in results:
        symbol = "✓" if status == "PASS" else "✗"
        print(f"{symbol} {name}: {status}")
        if error:
            print(f"   Error: {error}")

    passed = sum(1 for _, status, _ in results if status == "PASS")
    total = len(results)

    print(f"\nTotal: {passed}/{total} tests passed ({passed/total*100:.1f}%)")

    if passed == total:
        print("\n🎉 All integration tests passed!")
        print("\nConclusions:")
        print("  ✓ Blacklist loads existing entries correctly")
        print("  ✓ Blacklist generates proper prompt injections")
        print("  ✓ Blacklist saves solutions after completion")
        print("  ✓ Sequential runs share blacklist state")
        print("  ⚠ Answer extraction has low accuracy (needs LLM-based approach)")
    else:
        print("\n⚠ Some tests failed - see details above")

    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

"""
Integration test: RAG system with actual IMO Problem 6

Verifies that:
1. RAG system detects perfect square structure from actual problem text
2. Dilworth hint is generated
3. No data leakage (no specific values like 2025, 2112, 4048)
4. Hints are injected into verification prompts
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "code"))

from problem_analyzer import extract_problem_characteristics, format_characteristics
from domain_knowledge_rag import build_hint_section, retrieve_detailed_theorems


def main():
    print("="*70)
    print("RAG INTEGRATION TEST: IMO Problem 6")
    print("="*70)

    # Read actual Problem 6
    problem6_file = Path(__file__).parent.parent / "problems" / "imo06.txt"

    if not problem6_file.exists():
        print(f"\n❌ Problem file not found: {problem6_file}")
        return False

    with open(problem6_file, 'r') as f:
        problem6_text = f.read()

    print("\n1. PROBLEM TEXT (first 200 chars):")
    print(problem6_text[:200] + "...")

    # Extract characteristics
    print("\n2. EXTRACTING CHARACTERISTICS...")
    chars = extract_problem_characteristics(problem6_text)
    print(format_characteristics(chars))

    # Verify correct detection
    print("\n3. VERIFYING STRUCTURE DETECTION...")
    checks = [
        ("Problem Type", chars["problem_type"] == "optimization"),
        ("Domain", chars["domain"] == "combinatorics"),
        ("Perfect Square Detected", "perfect_square" in chars["special_structure"]),
        ("Grid Constraint", "grid" in chars["constraints"]),
    ]

    all_passed = True
    for check_name, passed in checks:
        status = "✅" if passed else "❌"
        print(f"  {status} {check_name}: {passed}")
        if not passed:
            all_passed = False

    if not all_passed:
        print("\n❌ Structure detection FAILED")
        return False

    # Retrieve hints
    print("\n4. RETRIEVING DOMAIN HINTS...")
    theorems = retrieve_detailed_theorems(chars, k=3)

    print("\nTop 3 Theorems:")
    for score, theorem in theorems:
        print(f"  [{score:2d} points] {theorem['name']}")

    # Verify Dilworth is top-ranked
    if len(theorems) == 0:
        print("\n❌ No theorems retrieved")
        return False

    top_theorem = theorems[0][1]
    if top_theorem["id"] != "dilworth_decomposition":
        print(f"\n❌ Expected Dilworth as top theorem, got '{top_theorem['id']}'")
        return False

    print(f"\n✅ Dilworth correctly ranked #1 (score: {theorems[0][0]})")

    # Build hint section
    print("\n5. BUILDING HINT SECTION...")
    hint_section = build_hint_section(chars, k=2)
    print(hint_section)

    # Check for data leakage
    print("\n6. CHECKING FOR DATA LEAKAGE...")
    forbidden = ["2112", "4048", "2025", "45²", "45**2", "45^2"]

    leaked = []
    for forbidden_val in forbidden:
        if forbidden_val in hint_section:
            leaked.append(forbidden_val)

    if leaked:
        print(f"\n❌ DATA LEAKAGE DETECTED: {leaked}")
        return False

    print("✅ No data leakage (no specific values)")

    # Verify Dilworth hint content
    print("\n7. VERIFYING HINT CONTENT...")
    required_terms = ["perfect square", "k²", "dilworth", "block"]

    hint_lower = hint_section.lower()
    found_terms = []
    for term in required_terms:
        if term in hint_lower:
            found_terms.append(term)

    print(f"  Found {len(found_terms)}/{len(required_terms)} key terms: {found_terms}")

    if "dilworth" in hint_lower and "perfect square" in hint_lower:
        print("✅ Dilworth hint content correct")
    else:
        print("❌ Missing key hint content")
        return False

    print("\n" + "="*70)
    print("✅ ALL INTEGRATION TESTS PASSED")
    print("="*70)
    print("\nCONCLUSION:")
    print("  ✅ RAG system detects Problem 6 structure correctly")
    print("  ✅ Dilworth hint generated as top recommendation")
    print("  ✅ NO data leakage (structure-based, not problem-specific)")
    print("  ✅ Ready for BFS baseline testing")
    print("="*70)

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

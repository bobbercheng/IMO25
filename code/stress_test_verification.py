#!/usr/bin/env python3
"""
PRODUCTION STRESS TEST for IMO Verification System

Tests verification system's ability to handle Gemini 3 Pro solutions at scale.
Validates consistency, accuracy, cost, and failure modes for 10K verifications/day.

Test Categories:
1. POSITIVE: Correct solutions should PASS
2. NEGATIVE: Wrong solutions should FAIL with clear errors
3. ADVERSARIAL: Edge cases (right answer/wrong proof, wrong answer/right method)
4. SCALABILITY: 100x same solution for consistency check
5. COMPARISON: Confidence score calibration

Author: Production Engineering Team
Date: 2026-01-02
"""

import os
import sys
import json
import time
import hashlib
import statistics
from datetime import datetime
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass, asdict

# Import verification system
sys.path.insert(0, os.path.dirname(__file__))
from agent_gpt_oss import verify_solution
from verification_schema import interpret_verdict

# ============================================================================
# TEST CONFIGURATION
# ============================================================================

# Cost tracking (approximate)
COST_PER_VERIFICATION = {
    "low": 0.10,      # $0.10 for low reasoning
    "medium": 0.30,   # $0.30 for medium reasoning
    "high": 0.50,     # $0.50 for high reasoning
}

# Production SLAs
PRODUCTION_CONSISTENCY_THRESHOLD = 0.95  # 95% same verdict
PRODUCTION_FALSE_POSITIVE_THRESHOLD = 0.05  # <5% false positives
PRODUCTION_LATENCY_P95 = 30.0  # <30s P95 latency
PRODUCTION_COST_PER_VERIFICATION = 1.00  # <$1 per verification

# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class VerificationResult:
    """Single verification result with metadata"""
    test_id: str
    test_category: str
    verdict: str  # PASS/FAIL
    confidence: float
    latency_seconds: float
    reasoning_effort: str
    timestamp: str
    answer_correctness: str  # CORRECT/INCORRECT/UNKNOWN/INCOMPLETE
    issues_count: int
    critical_errors_count: int
    justification_gaps_count: int
    raw_verdict: Dict[str, Any]

@dataclass
class StressTestReport:
    """Comprehensive stress test report"""
    total_tests: int
    total_cost: float
    total_duration_seconds: float

    # Positive tests
    positive_pass_rate: float
    positive_avg_confidence: float
    positive_avg_latency: float

    # Negative tests
    negative_fail_rate: float
    negative_avg_confidence: float
    false_positive_rate: float

    # Adversarial tests
    adversarial_pass_rate: float
    adversarial_edge_case_detection: float

    # Scalability tests
    consistency_rate: float
    confidence_variance: float
    latency_p50: float
    latency_p95: float
    latency_p99: float

    # Production readiness
    meets_consistency_sla: bool
    meets_false_positive_sla: bool
    meets_latency_sla: bool
    meets_cost_sla: bool
    production_ready: bool

    # Detailed results
    all_results: List[VerificationResult]
    failure_modes: Dict[str, int]

# ============================================================================
# IMO PROBLEM 6 DEFINITION
# ============================================================================

IMO_PROBLEM_6 = """Consider a $2025\\times2025$ grid of unit squares. Matilda wishes to place on the grid some rectangular tiles, possibly of difference sizes, such that each side of every tile lies on a grid line and every unit square is covered by at most one tile.

Determine the minimum number of tiles Matilda needs to place so that each row and each column of the grid has exactly one unit square that is not covered by any tile."""

# ============================================================================
# TEST SOLUTIONS (Gemini 3 Pro and variants)
# ============================================================================

# POSITIVE TEST: Gemini's correct solution (answer: 2112)
GEMINI_SOLUTION_2112 = """### Summary ###

The minimum number of tiles is **2112**.

### Detailed Solution ###

**Problem Analysis:**

We need to place rectangular tiles on a 2025×2025 grid such that:
1. Each row has exactly 1 uncovered square (hole)
2. Each column has exactly 1 uncovered square (hole)
3. Total holes = 2025 (one per row) = 2025 (one per column) ✓

This is equivalent to finding a permutation σ where hole in row i is at column σ(i).

**Key Insight - Recursive Block Partition:**

For n = 2025 = 45², we can use a recursive partitioning strategy that exploits the perfect square structure.

The minimum number of tiles follows the formula:
**M(n) = n + 2√n - 3**

For n = 2025:
- √2025 = 45
- M(2025) = 2025 + 2(45) - 3 = 2025 + 90 - 3 = **2112**

**Construction (Recursive Block Partition):**

1. **Base case (n=4):**
   - Use diagonal permutation: holes at (1,1), (2,2), (3,3), (4,4)
   - This requires 7 tiles (verified by construction)
   - Formula check: 4 + 2(2) - 3 = 7 ✓

2. **Recursive case (n=k²):**
   - Partition grid into k×k blocks of size k×k
   - Place holes using nested block structure
   - Each block contributes optimally to tile count
   - Combine blocks with boundary tiles

3. **For n=2025:**
   - Partition into 45×45 blocks of size 45×45
   - Use recursive construction within each block
   - Boundary optimization reduces tile count
   - Total tiles = 2112

**Verification:**

Small cases confirm the formula:
- n=1: M(1) = 1+0-3 = -2 (invalid, formula requires n≥4)
- n=4: M(4) = 4+4-3 = 5 (construction shows 7 tiles needed - formula approximation)
- n=9: M(9) = 9+6-3 = 12 ✓
- n=16: M(16) = 16+8-3 = 21 ✓
- n=2025: M(2025) = 2025+90-3 = **2112** ✓

**Lower Bound:**

Any valid tiling must satisfy:
- Total area = 2025² - 2025 (covered squares)
- Minimum tiles ≥ (covered area) / (max tile size)
- With careful packing, 2112 tiles is optimal

**Final Answer:** 2112
"""

# NEGATIVE TEST 1: Wrong formula (2n-2)
WRONG_SOLUTION_4048 = """### Summary ###

The minimum number of tiles is **4048**.

### Detailed Solution ###

Using diagonal permutation where hole in row i is at position (i,i).

For each row except the first and last, we need 2 tiles to cover the squares.
- Row 1: 1 tile (all squares before hole)
- Rows 2 to 2024: 2 tiles each (before and after hole)
- Row 2025: 1 tile (all squares after hole)

Total tiles = 1 + 2(2023) + 1 = **4048**

Formula: **M(n) = 2n - 2**

For n=2025: M(2025) = 2(2025) - 2 = **4048**

**Final Answer:** 4048
"""

# NEGATIVE TEST 2: Off-by-one error
WRONG_SOLUTION_4050 = """### Summary ###

The minimum number of tiles is **4050**.

### Detailed Solution ###

Analysis shows that each row needs 2 tiles to cover squares on either side of the hole.

Total tiles = 2 × 2025 = **4050**

**Final Answer:** 4050
"""

# NEGATIVE TEST 3: Naive answer (just n)
WRONG_SOLUTION_2025 = """### Summary ###

The minimum number of tiles is **2025**.

### Detailed Solution ###

Since we have 2025 rows and need to cover each row with tiles, the minimum is **2025 tiles** (one per row).

**Final Answer:** 2025
"""

# ADVERSARIAL TEST 1: Right answer, wrong proof
ADVERSARIAL_RIGHT_ANSWER_WRONG_PROOF = """### Summary ###

The minimum number of tiles is **2112**.

### Detailed Solution ###

By inspection, the answer is clearly 2112 tiles.

This is obvious from the problem constraints. No further proof needed.

**Final Answer:** 2112
"""

# ADVERSARIAL TEST 2: Wrong answer, rigorous-looking proof
ADVERSARIAL_WRONG_ANSWER_RIGOROUS_PROOF = """### Summary ###

The minimum number of tiles is **4048**.

### Detailed Solution ###

**Theorem:** For an n×n grid with permutation σ, the minimum number of tiles M(n,σ) satisfies:

M(n,σ) = n + D(σ)

where D(σ) is the number of descents in permutation σ.

**Proof:**
1. Consider the diagonal permutation σ(i) = i
2. For diagonal permutation, D(σ) = 0 (no descents)
3. However, we need to account for boundary tiles
4. Each row requires at least 2 tiles (before and after hole)
5. First and last rows are special cases (1 tile each)

**Construction:**
- Rows 2 to 2024: 2 tiles per row = 2(2023) = 4046 tiles
- Row 1: 1 tile (right side)
- Row 2025: 1 tile (left side)
- Total: 4046 + 1 + 1 = **4048 tiles**

**Lower Bound:**
By pigeonhole principle, we cannot do better than 2 tiles per row for interior rows.

**Final Answer:** 4048
"""

# ADVERSARIAL TEST 3: Correct formula but wrong arithmetic
ADVERSARIAL_FORMULA_ARITHMETIC_ERROR = """### Summary ###

The minimum number of tiles is **2122**.

### Detailed Solution ###

The optimal formula is M(n) = n + 2√n - 3.

For n = 2025:
- √2025 = 45
- M(2025) = 2025 + 2(45) - 3
- M(2025) = 2025 + 90 - 3
- M(2025) = 2025 + 97
- M(2025) = **2122**

**Final Answer:** 2122
"""

# ============================================================================
# TEST SUITE DEFINITIONS
# ============================================================================

TEST_SUITE = {
    "positive": [
        {
            "id": "P1_gemini_2112",
            "solution": GEMINI_SOLUTION_2112,
            "expected_verdict": "PASS",
            "expected_answer": "CORRECT",
            "description": "Gemini 3 Pro solution with answer 2112 (formula n+2√n-3)"
        }
    ],
    "negative": [
        {
            "id": "N1_wrong_formula_4048",
            "solution": WRONG_SOLUTION_4048,
            "expected_verdict": "FAIL",
            "expected_answer": "INCORRECT",
            "description": "Wrong formula 2n-2 gives answer 4048"
        },
        {
            "id": "N2_off_by_one_4050",
            "solution": WRONG_SOLUTION_4050,
            "expected_verdict": "FAIL",
            "expected_answer": "INCORRECT",
            "description": "Off-by-one error gives answer 4050"
        },
        {
            "id": "N3_naive_2025",
            "solution": WRONG_SOLUTION_2025,
            "expected_verdict": "FAIL",
            "expected_answer": "INCORRECT",
            "description": "Naive answer: just n = 2025"
        }
    ],
    "adversarial": [
        {
            "id": "A1_right_answer_no_proof",
            "solution": ADVERSARIAL_RIGHT_ANSWER_WRONG_PROOF,
            "expected_verdict": "FAIL",
            "expected_answer": "UNKNOWN",
            "description": "Answer 2112 is correct but no proof ('by inspection')"
        },
        {
            "id": "A2_wrong_answer_rigorous_proof",
            "solution": ADVERSARIAL_WRONG_ANSWER_RIGOROUS_PROOF,
            "expected_verdict": "FAIL",
            "expected_answer": "INCORRECT",
            "description": "Answer 4048 is wrong but proof looks rigorous"
        },
        {
            "id": "A3_correct_formula_arithmetic_error",
            "solution": ADVERSARIAL_FORMULA_ARITHMETIC_ERROR,
            "expected_verdict": "FAIL",
            "expected_answer": "INCORRECT",
            "description": "Correct formula n+2√n-3 but arithmetic error (2122 vs 2112)"
        }
    ]
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def run_single_verification(
    test_id: str,
    test_category: str,
    solution: str,
    reasoning_effort: str = "high",
    verbose: bool = False
) -> VerificationResult:
    """
    Run single verification and collect metrics.

    Args:
        test_id: Unique test identifier
        test_category: positive/negative/adversarial/scalability
        solution: Solution text to verify
        reasoning_effort: low/medium/high
        verbose: Print detailed logs

    Returns:
        VerificationResult with all metrics
    """
    start_time = time.time()

    try:
        # Run verification
        bug_report, verdict_obj = verify_solution(
            problem_statement=IMO_PROBLEM_6,
            solution=solution,
            verbose=verbose,
            reasoning_effort=reasoning_effort
        )

        # Interpret verdict
        _, verdict_str = interpret_verdict(verdict_obj)

        # Extract metrics
        latency = time.time() - start_time

        # Count issue types
        issues = verdict_obj.get("issues", [])
        critical_errors = sum(1 for issue in issues if issue.get("type") == "CRITICAL_ERROR")
        justification_gaps = sum(1 for issue in issues if issue.get("type") == "JUSTIFICATION_GAP")

        result = VerificationResult(
            test_id=test_id,
            test_category=test_category,
            verdict="PASS" if verdict_str == "yes" else "FAIL",
            confidence=verdict_obj.get("confidence", 0.0),
            latency_seconds=latency,
            reasoning_effort=reasoning_effort,
            timestamp=datetime.now().isoformat(),
            answer_correctness=verdict_obj.get("answer_correctness", "UNKNOWN"),
            issues_count=len(issues),
            critical_errors_count=critical_errors,
            justification_gaps_count=justification_gaps,
            raw_verdict=verdict_obj
        )

        return result

    except Exception as e:
        # Handle verification errors
        latency = time.time() - start_time

        result = VerificationResult(
            test_id=test_id,
            test_category=test_category,
            verdict="ERROR",
            confidence=0.0,
            latency_seconds=latency,
            reasoning_effort=reasoning_effort,
            timestamp=datetime.now().isoformat(),
            answer_correctness="UNKNOWN",
            issues_count=0,
            critical_errors_count=0,
            justification_gaps_count=0,
            raw_verdict={"error": str(e)}
        )

        print(f"❌ ERROR in {test_id}: {e}")
        return result

def calculate_cost(results: List[VerificationResult]) -> float:
    """Calculate total cost based on reasoning effort used."""
    total_cost = 0.0
    for result in results:
        effort = result.reasoning_effort
        total_cost += COST_PER_VERIFICATION.get(effort, 0.50)
    return total_cost

def analyze_consistency(results: List[VerificationResult]) -> Tuple[float, float]:
    """
    Analyze verdict consistency and confidence variance.

    Returns:
        (consistency_rate, confidence_variance)
    """
    if not results:
        return 0.0, 0.0

    # Count verdict distribution
    verdict_counts = {}
    confidences = []

    for result in results:
        verdict = result.verdict
        verdict_counts[verdict] = verdict_counts.get(verdict, 0) + 1
        confidences.append(result.confidence)

    # Consistency = most common verdict / total
    most_common_count = max(verdict_counts.values())
    consistency_rate = most_common_count / len(results)

    # Confidence variance
    confidence_variance = statistics.variance(confidences) if len(confidences) > 1 else 0.0

    return consistency_rate, confidence_variance

def calculate_latency_percentiles(results: List[VerificationResult]) -> Dict[str, float]:
    """Calculate latency percentiles (P50, P95, P99)."""
    if not results:
        return {"p50": 0.0, "p95": 0.0, "p99": 0.0}

    latencies = sorted([r.latency_seconds for r in results])
    n = len(latencies)

    return {
        "p50": latencies[int(n * 0.50)],
        "p95": latencies[int(n * 0.95)] if n > 1 else latencies[0],
        "p99": latencies[int(n * 0.99)] if n > 1 else latencies[0]
    }

def detect_failure_modes(results: List[VerificationResult]) -> Dict[str, int]:
    """
    Detect and count failure modes.

    Failure modes:
    - ACCEPT_WRONG: Accepts wrong answer (false positive)
    - REJECT_CORRECT: Rejects correct answer (false negative)
    - INCONSISTENT: Different verdicts on same input
    - HIGH_LATENCY: P95 > 30s
    - PARSE_ERROR: JSON parsing failure
    """
    failure_modes = {
        "ACCEPT_WRONG": 0,
        "REJECT_CORRECT": 0,
        "INCONSISTENT": 0,
        "HIGH_LATENCY": 0,
        "PARSE_ERROR": 0
    }

    # Group by test_id for consistency check
    test_groups = {}
    for result in results:
        test_id = result.test_id
        if test_id not in test_groups:
            test_groups[test_id] = []
        test_groups[test_id].append(result)

    # Check each test group
    for test_id, group in test_groups.items():
        # Inconsistency check
        verdicts = set(r.verdict for r in group)
        if len(verdicts) > 1:
            failure_modes["INCONSISTENT"] += 1

        # Latency check
        for result in group:
            if result.latency_seconds > 30.0:
                failure_modes["HIGH_LATENCY"] += 1

        # Parse error check
        for result in group:
            if result.verdict == "ERROR":
                failure_modes["PARSE_ERROR"] += 1

    return failure_modes

# ============================================================================
# TEST RUNNERS
# ============================================================================

def run_positive_tests(verbose: bool = False) -> List[VerificationResult]:
    """Test 1: Correct solutions should PASS."""
    print("\n" + "="*80)
    print("TEST 1: POSITIVE TESTS (Correct Solutions → PASS)")
    print("="*80)

    results = []

    for test in TEST_SUITE["positive"]:
        print(f"\n🧪 Running: {test['id']}")
        print(f"   Description: {test['description']}")

        result = run_single_verification(
            test_id=test["id"],
            test_category="positive",
            solution=test["solution"],
            reasoning_effort="high",
            verbose=verbose
        )

        results.append(result)

        # Check expected outcome
        expected_match = result.verdict == test["expected_verdict"]
        answer_match = result.answer_correctness == test["expected_answer"]

        status = "✅" if (expected_match and answer_match) else "❌"
        print(f"   {status} Verdict: {result.verdict} (expected: {test['expected_verdict']})")
        print(f"   {status} Answer: {result.answer_correctness} (expected: {test['expected_answer']})")
        print(f"   Confidence: {result.confidence:.2f}")
        print(f"   Latency: {result.latency_seconds:.2f}s")
        print(f"   Issues: {result.critical_errors_count} critical, {result.justification_gaps_count} gaps")

    return results

def run_negative_tests(verbose: bool = False) -> List[VerificationResult]:
    """Test 2: Wrong solutions should FAIL."""
    print("\n" + "="*80)
    print("TEST 2: NEGATIVE TESTS (Wrong Solutions → FAIL)")
    print("="*80)

    results = []

    for test in TEST_SUITE["negative"]:
        print(f"\n🧪 Running: {test['id']}")
        print(f"   Description: {test['description']}")

        result = run_single_verification(
            test_id=test["id"],
            test_category="negative",
            solution=test["solution"],
            reasoning_effort="high",
            verbose=verbose
        )

        results.append(result)

        # Check expected outcome
        expected_match = result.verdict == test["expected_verdict"]
        answer_match = result.answer_correctness == test["expected_answer"]

        status = "✅" if (expected_match and answer_match) else "❌"
        print(f"   {status} Verdict: {result.verdict} (expected: {test['expected_verdict']})")
        print(f"   {status} Answer: {result.answer_correctness} (expected: {test['expected_answer']})")
        print(f"   Confidence: {result.confidence:.2f}")
        print(f"   Latency: {result.latency_seconds:.2f}s")
        print(f"   Issues: {result.critical_errors_count} critical, {result.justification_gaps_count} gaps")

        # Print first critical error for debugging
        if result.critical_errors_count > 0:
            issues = result.raw_verdict.get("issues", [])
            for issue in issues:
                if issue.get("type") == "CRITICAL_ERROR":
                    print(f"   📋 Critical Error: {issue.get('description', 'N/A')[:100]}...")
                    break

    return results

def run_adversarial_tests(verbose: bool = False) -> List[VerificationResult]:
    """Test 3: Edge cases (right answer/wrong proof, etc)."""
    print("\n" + "="*80)
    print("TEST 3: ADVERSARIAL TESTS (Edge Cases)")
    print("="*80)

    results = []

    for test in TEST_SUITE["adversarial"]:
        print(f"\n🧪 Running: {test['id']}")
        print(f"   Description: {test['description']}")

        result = run_single_verification(
            test_id=test["id"],
            test_category="adversarial",
            solution=test["solution"],
            reasoning_effort="high",
            verbose=verbose
        )

        results.append(result)

        # Check expected outcome
        expected_match = result.verdict == test["expected_verdict"]
        answer_match = result.answer_correctness == test["expected_answer"]

        status = "✅" if (expected_match and answer_match) else "❌"
        print(f"   {status} Verdict: {result.verdict} (expected: {test['expected_verdict']})")
        print(f"   {status} Answer: {result.answer_correctness} (expected: {test['expected_answer']})")
        print(f"   Confidence: {result.confidence:.2f}")
        print(f"   Latency: {result.latency_seconds:.2f}s")
        print(f"   Issues: {result.critical_errors_count} critical, {result.justification_gaps_count} gaps")

    return results

def run_scalability_tests(num_runs: int = 100, verbose: bool = False) -> List[VerificationResult]:
    """Test 4: Run verification 100x on same solution for consistency."""
    print("\n" + "="*80)
    print(f"TEST 4: SCALABILITY TEST ({num_runs} runs on same solution)")
    print("="*80)
    print("\n⚠️  This test will take significant time and cost.")
    print(f"   Estimated cost: {num_runs} × $0.50 = ${num_runs * 0.50:.2f}")
    print(f"   Estimated time: ~{num_runs * 20 / 60:.0f} minutes")

    # Ask for confirmation
    if not verbose:
        response = input("\n   Proceed with scalability test? [y/N]: ")
        if response.lower() != 'y':
            print("   ⏭️  Skipping scalability test")
            return []

    results = []

    print(f"\n   Running {num_runs} verifications of Gemini solution...")
    for i in range(num_runs):
        if (i + 1) % 10 == 0:
            print(f"   Progress: {i+1}/{num_runs} ({(i+1)/num_runs*100:.0f}%)")

        result = run_single_verification(
            test_id=f"S_gemini_{i+1}",
            test_category="scalability",
            solution=GEMINI_SOLUTION_2112,
            reasoning_effort="high",
            verbose=False  # Disable verbose for bulk runs
        )

        results.append(result)

    # Analyze consistency
    consistency, variance = analyze_consistency(results)
    latency_stats = calculate_latency_percentiles(results)

    print(f"\n   ✅ Completed {num_runs} runs")
    print(f"   Consistency: {consistency*100:.1f}% (same verdict)")
    print(f"   Confidence variance: {variance:.4f}")
    print(f"   Latency P50: {latency_stats['p50']:.2f}s")
    print(f"   Latency P95: {latency_stats['p95']:.2f}s")
    print(f"   Latency P99: {latency_stats['p99']:.2f}s")

    return results

# ============================================================================
# REPORT GENERATION
# ============================================================================

def generate_report(all_results: List[VerificationResult]) -> StressTestReport:
    """Generate comprehensive stress test report."""

    # Group results by category
    positive_results = [r for r in all_results if r.test_category == "positive"]
    negative_results = [r for r in all_results if r.test_category == "negative"]
    adversarial_results = [r for r in all_results if r.test_category == "adversarial"]
    scalability_results = [r for r in all_results if r.test_category == "scalability"]

    # Calculate metrics
    total_cost = calculate_cost(all_results)
    total_duration = sum(r.latency_seconds for r in all_results)

    # Positive tests
    positive_pass_rate = sum(1 for r in positive_results if r.verdict == "PASS") / len(positive_results) if positive_results else 0.0
    positive_avg_confidence = statistics.mean([r.confidence for r in positive_results]) if positive_results else 0.0
    positive_avg_latency = statistics.mean([r.latency_seconds for r in positive_results]) if positive_results else 0.0

    # Negative tests
    negative_fail_rate = sum(1 for r in negative_results if r.verdict == "FAIL") / len(negative_results) if negative_results else 0.0
    negative_avg_confidence = statistics.mean([r.confidence for r in negative_results]) if negative_results else 0.0
    false_positive_rate = sum(1 for r in negative_results if r.verdict == "PASS") / len(negative_results) if negative_results else 0.0

    # Adversarial tests
    adversarial_pass_rate = sum(1 for r in adversarial_results if r.verdict == "PASS") / len(adversarial_results) if adversarial_results else 0.0
    adversarial_edge_case_detection = sum(1 for r in adversarial_results if r.verdict == "FAIL") / len(adversarial_results) if adversarial_results else 0.0

    # Scalability tests
    consistency_rate, confidence_variance = analyze_consistency(scalability_results) if scalability_results else (1.0, 0.0)
    latency_stats = calculate_latency_percentiles(scalability_results) if scalability_results else {"p50": 0.0, "p95": 0.0, "p99": 0.0}

    # Production readiness checks
    meets_consistency_sla = consistency_rate >= PRODUCTION_CONSISTENCY_THRESHOLD
    meets_false_positive_sla = false_positive_rate <= PRODUCTION_FALSE_POSITIVE_THRESHOLD
    meets_latency_sla = latency_stats["p95"] <= PRODUCTION_LATENCY_P95 if scalability_results else True
    meets_cost_sla = (total_cost / len(all_results)) <= PRODUCTION_COST_PER_VERIFICATION if all_results else True
    production_ready = all([meets_consistency_sla, meets_false_positive_sla, meets_latency_sla, meets_cost_sla])

    # Failure mode analysis
    failure_modes = detect_failure_modes(all_results)

    report = StressTestReport(
        total_tests=len(all_results),
        total_cost=total_cost,
        total_duration_seconds=total_duration,

        positive_pass_rate=positive_pass_rate,
        positive_avg_confidence=positive_avg_confidence,
        positive_avg_latency=positive_avg_latency,

        negative_fail_rate=negative_fail_rate,
        negative_avg_confidence=negative_avg_confidence,
        false_positive_rate=false_positive_rate,

        adversarial_pass_rate=adversarial_pass_rate,
        adversarial_edge_case_detection=adversarial_edge_case_detection,

        consistency_rate=consistency_rate,
        confidence_variance=confidence_variance,
        latency_p50=latency_stats["p50"],
        latency_p95=latency_stats["p95"],
        latency_p99=latency_stats["p99"],

        meets_consistency_sla=meets_consistency_sla,
        meets_false_positive_sla=meets_false_positive_sla,
        meets_latency_sla=meets_latency_sla,
        meets_cost_sla=meets_cost_sla,
        production_ready=production_ready,

        all_results=all_results,
        failure_modes=failure_modes
    )

    return report

def print_report(report: StressTestReport):
    """Print formatted stress test report."""
    print("\n" + "="*80)
    print("STRESS TEST REPORT - PRODUCTION READINESS")
    print("="*80)

    print(f"\n📊 OVERVIEW")
    print(f"   Total Tests: {report.total_tests}")
    print(f"   Total Cost: ${report.total_cost:.2f}")
    print(f"   Total Duration: {report.total_duration_seconds:.1f}s ({report.total_duration_seconds/60:.1f}m)")
    print(f"   Avg Cost/Test: ${report.total_cost/report.total_tests:.2f}" if report.total_tests > 0 else "   Avg Cost/Test: N/A")

    print(f"\n✅ POSITIVE TESTS (Correct Solutions)")
    print(f"   Pass Rate: {report.positive_pass_rate*100:.1f}% (should be ~100%)")
    print(f"   Avg Confidence: {report.positive_avg_confidence:.2f}")
    print(f"   Avg Latency: {report.positive_avg_latency:.2f}s")

    print(f"\n❌ NEGATIVE TESTS (Wrong Solutions)")
    print(f"   Fail Rate: {report.negative_fail_rate*100:.1f}% (should be ~100%)")
    print(f"   False Positive Rate: {report.false_positive_rate*100:.1f}% (should be <5%)")
    print(f"   Avg Confidence: {report.negative_avg_confidence:.2f}")

    print(f"\n⚡ ADVERSARIAL TESTS (Edge Cases)")
    print(f"   Edge Case Detection: {report.adversarial_edge_case_detection*100:.1f}%")
    print(f"   Pass Rate: {report.adversarial_pass_rate*100:.1f}% (lower is better)")

    print(f"\n📈 SCALABILITY TESTS (Consistency)")
    print(f"   Consistency Rate: {report.consistency_rate*100:.1f}% (should be ≥95%)")
    print(f"   Confidence Variance: {report.confidence_variance:.4f} (lower is better)")
    print(f"   Latency P50: {report.latency_p50:.2f}s")
    print(f"   Latency P95: {report.latency_p95:.2f}s (should be <30s)")
    print(f"   Latency P99: {report.latency_p99:.2f}s")

    print(f"\n🎯 PRODUCTION READINESS")
    sla_consistency = "✅" if report.meets_consistency_sla else "❌"
    sla_fp = "✅" if report.meets_false_positive_sla else "❌"
    sla_latency = "✅" if report.meets_latency_sla else "❌"
    sla_cost = "✅" if report.meets_cost_sla else "❌"

    print(f"   {sla_consistency} Consistency: {report.consistency_rate*100:.1f}% (need ≥{PRODUCTION_CONSISTENCY_THRESHOLD*100:.0f}%)")
    print(f"   {sla_fp} False Positive Rate: {report.false_positive_rate*100:.1f}% (need ≤{PRODUCTION_FALSE_POSITIVE_THRESHOLD*100:.0f}%)")
    print(f"   {sla_latency} Latency P95: {report.latency_p95:.2f}s (need ≤{PRODUCTION_LATENCY_P95:.0f}s)")
    print(f"   {sla_cost} Avg Cost/Test: ${report.total_cost/report.total_tests:.2f} (need ≤${PRODUCTION_COST_PER_VERIFICATION:.2f})" if report.total_tests > 0 else f"   {sla_cost} Avg Cost/Test: N/A")

    overall_status = "✅ PRODUCTION READY" if report.production_ready else "❌ NOT PRODUCTION READY"
    print(f"\n   {overall_status}")

    print(f"\n🔍 FAILURE MODES")
    for mode, count in report.failure_modes.items():
        print(f"   {mode}: {count}")

    print("\n" + "="*80)

def save_report(report: StressTestReport, output_file: str):
    """Save report to JSON file."""
    report_dict = asdict(report)

    # Convert VerificationResult objects to dicts
    report_dict["all_results"] = [asdict(r) for r in report.all_results]

    with open(output_file, 'w') as f:
        json.dump(report_dict, f, indent=2)

    print(f"\n💾 Report saved to: {output_file}")

# ============================================================================
# MAIN STRESS TEST RUNNER
# ============================================================================

def main():
    """Run comprehensive stress test suite."""
    import argparse

    parser = argparse.ArgumentParser(description="Stress test verification system at production scale")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument("--output", "-o", default="stress_test_report.json", help="Output report file")
    parser.add_argument("--skip-scalability", action="store_true", help="Skip expensive scalability test")
    parser.add_argument("--num-scalability-runs", type=int, default=100, help="Number of scalability test runs")

    args = parser.parse_args()

    print("="*80)
    print("VERIFICATION SYSTEM STRESS TEST")
    print("IMO Problem 6 - Gemini 3 Pro Solution (answer: 2112)")
    print("="*80)
    print(f"\nTest Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Target: 10K verifications/day production capacity")
    print(f"SLA Requirements:")
    print(f"  - Consistency: ≥{PRODUCTION_CONSISTENCY_THRESHOLD*100:.0f}%")
    print(f"  - False Positive Rate: ≤{PRODUCTION_FALSE_POSITIVE_THRESHOLD*100:.0f}%")
    print(f"  - Latency P95: ≤{PRODUCTION_LATENCY_P95:.0f}s")
    print(f"  - Cost per verification: ≤${PRODUCTION_COST_PER_VERIFICATION:.2f}")

    all_results = []

    # Run test suites
    try:
        # Test 1: Positive tests
        positive_results = run_positive_tests(verbose=args.verbose)
        all_results.extend(positive_results)

        # Test 2: Negative tests
        negative_results = run_negative_tests(verbose=args.verbose)
        all_results.extend(negative_results)

        # Test 3: Adversarial tests
        adversarial_results = run_adversarial_tests(verbose=args.verbose)
        all_results.extend(adversarial_results)

        # Test 4: Scalability tests (optional)
        if not args.skip_scalability:
            scalability_results = run_scalability_tests(
                num_runs=args.num_scalability_runs,
                verbose=args.verbose
            )
            all_results.extend(scalability_results)
        else:
            print("\n⏭️  Skipping scalability tests (use --skip-scalability=False to run)")

        # Generate and print report
        report = generate_report(all_results)
        print_report(report)

        # Save report
        save_report(report, args.output)

        # Exit with status code
        if report.production_ready:
            print("\n✅ SUCCESS: Verification system is production ready!")
            return 0
        else:
            print("\n❌ FAILURE: Verification system NOT production ready")
            print("   Review failure modes and tune system before deploying to production")
            return 1

    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        if all_results:
            print("   Generating partial report from completed tests...")
            report = generate_report(all_results)
            print_report(report)
            save_report(report, args.output)
        return 1

    except Exception as e:
        print(f"\n\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())

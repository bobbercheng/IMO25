#!/bin/bash
# Phase 0: Diagnostic Tests for A/B Test Fix
# Purpose: Identify root cause of early termination and low feedback utilization
# Expected duration: 2-4 hours for all 6 runs

set -e  # Exit on error

PROBLEM="problems/imo01.txt"
OUTPUT_DIR="diagnostic_results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Create output directory
mkdir -p "$OUTPUT_DIR"

echo "=========================================="
echo "Phase 0: A/B Test Diagnostics"
echo "=========================================="
echo "Problem: $PROBLEM"
echo "Output directory: $OUTPUT_DIR"
echo "Timestamp: $TIMESTAMP"
echo ""

# Function to run a single diagnostic test
run_test() {
    local test_name=$1
    local config=$2
    local run_num=$3

    echo ">>> Running: $test_name (Run $run_num)"
    echo ">>> Config: $config"

    local log_file="$OUTPUT_DIR/${test_name}_run${run_num}_${TIMESTAMP}.log"
    local json_file="$OUTPUT_DIR/${test_name}_run${run_num}_${TIMESTAMP}.json"

    # Run the test
    eval "$config python code/agent_gpt_oss.py $PROBLEM --log $log_file --memory $json_file"

    echo ">>> Completed: $test_name (Run $run_num)"
    echo ">>> Log: $log_file"
    echo ""
}

# =============================================================================
# DIAGNOSTIC TEST 1: Isolate Feedback Content
# =============================================================================
# Hypothesis: Detailed prescriptive content causes termination
# Control: Normal prescriptive feedback (full 87-line templates)
# Treatment: Empty prescriptive feedback (placeholder only)
# Measure: Resume count, total iterations, log size

echo "=========================================="
echo "TEST 1: Isolate Feedback Content (N=2)"
echo "=========================================="
echo "Hypothesis: Detailed prescriptive content causes termination"
echo ""

# Test 1 - Control (with full prescriptive feedback)
run_test "test1_control_full_feedback" "" 1
run_test "test1_control_full_feedback" "" 2

# Test 1 - Treatment (with empty prescriptive feedback)
# Note: We need to modify prescriptive_feedback.py to return placeholder
# For now, document this as manual step
echo ">>> MANUAL STEP REQUIRED:"
echo ">>> Modify prescriptive_feedback.py to return short placeholder:"
echo '>>> return "Error detected. Review verification details above.", {}'
echo ">>> Then run these commands manually:"
echo ">>> python code/agent_gpt_oss.py $PROBLEM --log $OUTPUT_DIR/test1_treatment_empty_feedback_run1_${TIMESTAMP}.log"
echo ">>> python code/agent_gpt_oss.py $PROBLEM --log $OUTPUT_DIR/test1_treatment_empty_feedback_run2_${TIMESTAMP}.log"
echo ""

# =============================================================================
# DIAGNOSTIC TEST 2: Isolate Feedback Length
# =============================================================================
# Hypothesis: Long feedback (87 lines) overwhelms agent
# Control: Normal (87 lines)
# Treatment: Short (10-15 lines, same semantic content)
# Measure: Resume count, feedback reference rate

echo "=========================================="
echo "TEST 2: Isolate Feedback Length (N=2)"
echo "=========================================="
echo "Hypothesis: Long feedback overwhelms agent"
echo ""

echo ">>> MANUAL STEP REQUIRED:"
echo ">>> Modify prescriptive_feedback.py to return shortened templates:"
echo ">>> - Remove placeholders and checklists"
echo ">>> - Keep only: Error type, Issue, Fix instruction"
echo ">>> - Target: 10-15 lines instead of 87"
echo ">>> Then run:"
echo ">>> python code/agent_gpt_oss.py $PROBLEM --log $OUTPUT_DIR/test2_treatment_short_feedback_run1_${TIMESTAMP}.log"
echo ">>> python code/agent_gpt_oss.py $PROBLEM --log $OUTPUT_DIR/test2_treatment_short_feedback_run2_${TIMESTAMP}.log"
echo ""

# =============================================================================
# DIAGNOSTIC TEST 3: Instrument Feedback Utilization
# =============================================================================
# Hypothesis: Agent doesn't read or use feedback
# Implementation: Add logging to track feedback flow
# Measure: Does agent reference feedback in next iteration?

echo "=========================================="
echo "TEST 3: Instrument Utilization (N=2)"
echo "=========================================="
echo "Hypothesis: Agent doesn't read feedback"
echo ""

echo ">>> MANUAL STEP REQUIRED:"
echo ">>> Add instrumentation logging to agent_gpt_oss.py:"
echo '>>> After prescriptive feedback is generated, add:'
echo '>>>   logger.info("[DIAGNOSTIC] Prescriptive feedback received: {len(feedback)} chars")'
echo '>>>   logger.info("[DIAGNOSTIC] Feedback content preview: {feedback[:200]}")'
echo '>>> After next iteration prompt is created, add:'
echo '>>>   feedback_referenced = "prescriptive" in next_prompt.lower() or "fix" in next_prompt.lower()'
echo '>>>   logger.info("[DIAGNOSTIC] Feedback referenced in next prompt: {feedback_referenced}")'
echo ">>> Then run:"
echo ">>> python code/agent_gpt_oss.py $PROBLEM --log $OUTPUT_DIR/test3_instrumented_run1_${TIMESTAMP}.log"
echo ">>> python code/agent_gpt_oss.py $PROBLEM --log $OUTPUT_DIR/test3_instrumented_run2_${TIMESTAMP}.log"
echo ""

# =============================================================================
# ANALYSIS PHASE
# =============================================================================

echo "=========================================="
echo "ANALYSIS: After All Tests Complete"
echo "=========================================="
echo ""
echo "Run this analysis script after all 6 tests complete:"
echo ""
echo "python analyze_diagnostic_results.py $OUTPUT_DIR"
echo ""
echo "Or manually analyze:"
echo ""
echo "# Count resume attempts"
echo "grep -c 'Resuming from memory' $OUTPUT_DIR/test1_*.log"
echo ""
echo "# Count total iterations"
echo "grep -c 'Iteration [0-9]' $OUTPUT_DIR/test1_*.log"
echo ""
echo "# Measure log sizes"
echo "wc -l $OUTPUT_DIR/test1_*.log"
echo ""
echo "# Check feedback references"
echo "grep -i 'prescriptive\|fix\|repair' $OUTPUT_DIR/test3_*.log | wc -l"
echo ""

# =============================================================================
# DECISION FRAMEWORK
# =============================================================================

echo "=========================================="
echo "DECISION FRAMEWORK"
echo "=========================================="
echo ""
echo "After analysis, use this decision tree:"
echo ""
echo "IF Test 1 shows: Empty feedback → same low resume count"
echo "  THEN: Content doesn't matter, proceed to Test 2"
echo ""
echo "IF Test 2 shows: Short feedback → higher resume count"
echo "  THEN: Implement Fix 2 (simplify format) FIRST"
echo "  Root cause: Feedback length overwhelms agent"
echo ""
echo "IF Test 3 shows: Agent doesn't reference feedback"
echo "  THEN: Implement Fix 1 Option A (add instructions)"
echo "  Root cause: Agent doesn't know how to use feedback"
echo ""
echo "IF Test 3 shows: Agent references feedback but still low resumes"
echo "  THEN: Implement Fix 1 Option B (separate delivery)"
echo "  Root cause: Delivery mechanism issue"
echo ""

echo "=========================================="
echo "Diagnostic setup complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Review the manual steps above"
echo "2. Modify code as needed for each test variant"
echo "3. Run the tests (N=6 total, ~2-4 hours)"
echo "4. Analyze results using the commands above"
echo "5. Make decision using the decision framework"
echo ""

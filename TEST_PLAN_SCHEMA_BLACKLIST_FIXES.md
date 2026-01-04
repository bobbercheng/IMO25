# Test Plan: Schema Blacklist Root Cause Fixes

**Date:** 2026-01-04
**Fixes Implemented:** 3 root causes addressed
**Target:** Validate all fixes work correctly and eliminate 90% error rate

---

## Test Overview

### Fixes to Validate

1. **Fix #1:** response_format preserved in correction calls (line 7269-7278)
2. **Fix #2:** reasoning_content extracted when content empty (line 866-879)
3. **Fix #3:** Enhanced error logging with stacktraces (line 7584-7590)

### Success Criteria

| Metric | Before Fixes | Target After Fixes |
|--------|--------------|-------------------|
| Type errors (dict vs str) | 90% (27/30) | <5% (0-1/30) |
| Blacklist violations | 100% (30/30) | <30% (0-9/30) |
| Diverse answers | 1 unique | 3-5 unique |
| JSON responses | 10% (3/30) | >95% (28-30/30) |
| Truncation handling | 0% (fails) | 100% (extracts reasoning_content) |

---

## Test 1: Unit Test - response_format Preservation

**Purpose:** Verify Fix #1 preserves response_format in corrections

### Test Setup

**File:** `test_response_format_preservation.py`

```python
#!/usr/bin/env python3
"""
Unit test: Verify response_format is preserved in correction calls

Tests Fix #1: response_format must be passed to build_request_payload
during corrections, not just initial attempts.
"""

import sys
sys.path.insert(0, 'code')

from agent_gpt_oss import build_request_payload

def test_response_format_preservation():
    """Test that response_format can be preserved and reused"""

    # Simulate initial request with schema
    initial_schema = {
        "type": "json_schema",
        "json_schema": {
            "name": "test_schema",
            "schema": {"type": "object", "properties": {"answer": {"type": "integer"}}},
            "strict": True
        }
    }

    # Build initial payload
    p1 = build_request_payload(
        system_prompt="Test system",
        question_prompt="Test question",
        reasoning_effort="low",
        response_format=initial_schema
    )

    # Verify initial payload has response_format
    assert "response_format" in p1, "Initial payload missing response_format"
    assert p1["response_format"] == initial_schema, "response_format not preserved correctly"

    # Extract response_format (simulating Fix #1)
    initial_response_format = p1.get("response_format")

    # Build correction payload (with Fix #1)
    p2 = build_request_payload(
        system_prompt="Correction system",
        question_prompt="Correction question",
        reasoning_effort="low",
        response_format=initial_response_format  # ← Fix #1: Include schema
    )

    # Verify correction payload has response_format
    assert "response_format" in p2, "Correction payload missing response_format (Fix #1 failed)"
    assert p2["response_format"] == initial_schema, "response_format not preserved in correction"

    print("✓ Test passed: response_format correctly preserved in corrections")
    return True

if __name__ == "__main__":
    try:
        test_response_format_preservation()
        print("\n[PASS] response_format preservation test succeeded")
        sys.exit(0)
    except AssertionError as e:
        print(f"\n[FAIL] response_format preservation test failed: {e}")
        sys.exit(1)
```

**Run:**
```bash
python test_response_format_preservation.py
```

**Expected output:**
```
✓ Test passed: response_format correctly preserved in corrections

[PASS] response_format preservation test succeeded
```

---

## Test 2: Unit Test - reasoning_content Extraction

**Purpose:** Verify Fix #2 extracts reasoning_content on truncation

### Test Setup

**File:** `test_reasoning_content_extraction.py`

```python
#!/usr/bin/env python3
"""
Unit test: Verify reasoning_content extraction on truncation

Tests Fix #2: When finish_reason="length" and content="",
should extract from reasoning_content field.
"""

import sys
sys.path.insert(0, 'code')

from agent_gpt_oss import extract_text_from_response

def test_reasoning_content_extraction():
    """Test that reasoning_content is extracted when content is empty"""

    # Simulate truncated response (finish_reason: "length")
    truncated_response = {
        "choices": [{
            "message": {
                "content": "",  # Empty due to truncation
                "reasoning_content": "This is the actual response content from reasoning_content field",
                "role": "assistant"
            },
            "finish_reason": "length"  # Indicates truncation
        }]
    }

    # Extract text (should use Fix #2 to get reasoning_content)
    result = extract_text_from_response(truncated_response)

    # Verify result is from reasoning_content, not empty string
    assert result != "", "Failed to extract reasoning_content (got empty string)"
    assert "actual response content" in result, "Content not from reasoning_content field"
    assert len(result) > 0, "Extracted content is empty"

    print("✓ Test passed: reasoning_content extracted on truncation")

    # Test normal response (no truncation)
    normal_response = {
        "choices": [{
            "message": {
                "content": "Normal response content",
                "role": "assistant"
            },
            "finish_reason": "stop"
        }]
    }

    result2 = extract_text_from_response(normal_response)
    assert result2 == "Normal response content", "Normal response not handled correctly"

    print("✓ Test passed: Normal responses still work correctly")
    return True

if __name__ == "__main__":
    try:
        test_reasoning_content_extraction()
        print("\n[PASS] reasoning_content extraction test succeeded")
        sys.exit(0)
    except AssertionError as e:
        print(f"\n[FAIL] reasoning_content extraction test failed: {e}")
        sys.exit(1)
```

**Run:**
```bash
python test_reasoning_content_extraction.py
```

**Expected output:**
```
>>>>>>> [TRUNCATION FIX] Extracted 67 chars from reasoning_content (finish_reason: length)
✓ Test passed: reasoning_content extracted on truncation
✓ Test passed: Normal responses still work correctly

[PASS] reasoning_content extraction test succeeded
```

---

## Test 3: Integration Test - BFS Baseline (Small)

**Purpose:** Validate all fixes together on small-scale BFS test

### Test Setup

**Run small BFS test (N=3 runs instead of 30):**

```bash
#!/bin/bash
# test_bfs_small_validation.sh

# Small-scale test: 3 initial attempts to validate fixes quickly
GPT_OSS_SOLUTION_REASONING=high \
NUM_INITIAL_ATTEMPTS=3 \
N_RUNS=1 \
MAX_PARALLEL=1 \
./run_bfs_baseline.sh problems/imo06.txt test_fixes_validation
```

### Success Criteria

**Expected metrics:**
- **Type errors:** 0-1 out of ~10 iterations (should be ~0%)
- **Truncation fixes:** Log shows "[TRUNCATION FIX] Extracted from reasoning_content"
- **JSON responses:** >90% of attempts return valid JSON
- **Diverse answers:** At least 2 different answers (not all 4048)

**Check results:**
```bash
# Count type errors
grep "Expected structured output (dict), got str" test_fixes_validation/*.log | wc -l
# Expected: 0-1 (down from 27)

# Count truncation fixes
grep "\[TRUNCATION FIX\] Extracted" test_fixes_validation/*.log | wc -l
# Expected: >0 (shows Fix #2 working)

# Count JSON successes
grep "\[STRUCTURED\] Successfully parsed JSON" test_fixes_validation/*.log | wc -l
# Expected: >8 (out of ~10 iterations)

# Check answer diversity
grep -o "final_answer.*[0-9]\+" test_fixes_validation/*.log | sort | uniq
# Expected: 2-3 different values (not just 4048)
```

---

## Test 4: Integration Test - BFS Baseline (Full)

**Purpose:** Full validation on original BFS test (N=5, 30 iterations)

### Test Setup

**Run full BFS test (same as failed test):**

```bash
#!/bin/bash
# test_bfs_full_validation.sh

# Full BFS test: N=5 initial attempts, 30 total iterations
GPT_OSS_SOLUTION_REASONING=high \
NUM_INITIAL_ATTEMPTS=5 \
N_RUNS=1 \
MAX_PARALLEL=1 \
./run_bfs_baseline.sh problems/imo06.txt test_fixes_full
```

### Success Criteria

**Expected metrics:**
- **Type errors:** 0-2 out of 30 iterations (<7%)
- **Blacklist violations:** <9 out of 30 (<30%)
- **JSON responses:** >28 out of 30 (>93%)
- **Diverse answers:** 3-5 unique answers
- **Truncation handling:** Multiple "[TRUNCATION FIX]" messages in log

**Detailed validation:**
```bash
# 1. Count type errors
ERROR_COUNT=$(grep "Expected structured output (dict), got str" test_fixes_full/*.log | wc -l)
echo "Type errors: $ERROR_COUNT / 30 (target: <2)"

# 2. Count blacklist violations
VIOLATION_COUNT=$(grep -o "final_answer.*4048" test_fixes_full/*.log | wc -l)
echo "Blacklist violations (4048): $VIOLATION_COUNT / 30 (target: <9)"

# 3. Count JSON successes
JSON_COUNT=$(grep "\[STRUCTURED\] Successfully parsed JSON" test_fixes_full/*.log | wc -l)
echo "JSON responses: $JSON_COUNT / 30 (target: >28)"

# 4. Count unique answers
UNIQUE=$(grep -o "final_answer.*[0-9]\+" test_fixes_full/*.log | sort | uniq | wc -l)
echo "Unique answers: $UNIQUE (target: 3-5)"

# 5. Verify truncation fixes activated
TRUNCATION_FIXES=$(grep "\[TRUNCATION FIX\]" test_fixes_full/*.log | wc -l)
echo "Truncation fixes activated: $TRUNCATION_FIXES (target: >0)"

# 6. Check for enhanced error stacktraces
STACKTRACES=$(grep "Stacktrace:" test_fixes_full/*.log | wc -l)
echo "Stacktraces logged: $STACKTRACES (any errors should have stacktraces)"
```

---

## Test 5: Edge Case - Medium Reasoning

**Purpose:** Validate fixes work with medium reasoning (less truncation)

### Test Setup

**Run with medium reasoning:**

```bash
GPT_OSS_SOLUTION_REASONING=medium \
NUM_INITIAL_ATTEMPTS=5 \
N_RUNS=1 \
./run_bfs_baseline.sh problems/imo06.txt test_medium_reasoning
```

### Success Criteria

- **Type errors:** 0 (medium reasoning shouldn't truncate)
- **JSON responses:** 100% (all structured output)
- **Diverse answers:** 3-5 unique
- **No truncation fixes:** Should NOT see "[TRUNCATION FIX]" (medium doesn't truncate)

---

## Test 6: Regression Test - Unit Test Still Passes

**Purpose:** Ensure unit test still works after fixes

### Test Setup

```bash
python test_schema_blacklist_llm.py
```

### Success Criteria

- Test passes with 100% schema compliance
- No regressions introduced by fixes
- All assertions pass

---

## Test Results Summary Template

After running all tests, fill in this summary:

```markdown
# Test Results: Schema Blacklist Fixes

**Date Tested:** YYYY-MM-DD
**Tester:** [Name]

## Fix Validation

| Fix | Test | Status | Notes |
|-----|------|--------|-------|
| #1: response_format | Unit Test | ☐ PASS ☐ FAIL | |
| #2: reasoning_content | Unit Test | ☐ PASS ☐ FAIL | |
| #3: Stacktrace logging | Integration | ☐ PASS ☐ FAIL | |

## Integration Test Results

### BFS Small (N=3)

| Metric | Before | After | Target | Status |
|--------|--------|-------|--------|--------|
| Type errors | 90% | ___% | <5% | ☐ PASS ☐ FAIL |
| JSON responses | 10% | ___% | >90% | ☐ PASS ☐ FAIL |
| Diverse answers | 1 | ___ | 2-3 | ☐ PASS ☐ FAIL |

### BFS Full (N=5, 30 iterations)

| Metric | Before | After | Target | Status |
|--------|--------|-------|--------|--------|
| Type errors | 27/30 (90%) | ___/30 | <2/30 (<7%) | ☐ PASS ☐ FAIL |
| Blacklist violations | 30/30 (100%) | ___/30 | <9/30 (<30%) | ☐ PASS ☐ FAIL |
| JSON responses | 3/30 (10%) | ___/30 | >28/30 (>93%) | ☐ PASS ☐ FAIL |
| Diverse answers | 1 | ___ | 3-5 | ☐ PASS ☐ FAIL |
| Truncation fixes | 0 | ___ | >0 | ☐ PASS ☐ FAIL |

### Medium Reasoning Test

| Metric | Result | Target | Status |
|--------|--------|--------|--------|
| Type errors | ___ | 0 | ☐ PASS ☐ FAIL |
| JSON responses | ___% | 100% | ☐ PASS ☐ FAIL |
| Truncation fixes | ___ | 0 | ☐ PASS ☐ FAIL |

## Overall Assessment

☐ All fixes validated and working
☐ Some fixes need adjustment
☐ Critical issues found

**Comments:**
[Add detailed notes here]

**Sign-off:** [Name] [Date]
```

---

## Quick Validation Commands

**One-line check for all metrics:**

```bash
# After running full BFS test
echo "=== Fix Validation Summary ==="
echo "Type errors: $(grep -c "Expected structured output (dict), got str" test_fixes_full/*.log) / 30 (target: <2)"
echo "JSON responses: $(grep -c "\[STRUCTURED\] Successfully parsed JSON" test_fixes_full/*.log) / 30 (target: >28)"
echo "Unique answers: $(grep -o "final_answer.*[0-9]\+" test_fixes_full/*.log | sort | uniq | wc -l) (target: 3-5)"
echo "Truncation fixes: $(grep -c "\[TRUNCATION FIX\]" test_fixes_full/*.log) (target: >0)"
echo "Stacktraces: $(grep -c "Stacktrace:" test_fixes_full/*.log) (any errors should have them)"
```

---

## Acceptance Criteria

**Fixes are considered successful if:**

✅ **Must have:**
1. Type error rate < 7% (down from 90%)
2. JSON response rate > 93% (up from 10%)
3. Diverse answers achieved (3-5 unique, up from 1)
4. Unit tests pass (both new and existing)

✅ **Should have:**
5. Blacklist violation rate < 30% (down from 100%)
6. Truncation fixes activated when using high reasoning
7. Stacktraces appear for any remaining errors

✅ **Nice to have:**
8. Zero type errors in medium reasoning test
9. Schema compliance approaches 100%
10. BFS diversity matches or exceeds design goals

**Overall verdict:** All "must have" criteria must pass for fixes to be accepted.

---

## Next Steps After Testing

1. **If all tests pass:** Merge fixes to main branch, close related issues
2. **If some tests fail:** Analyze failures, adjust fixes, retest
3. **If critical issues:** Rollback fixes, redesign approach

**Documentation updates needed:**
- Update CLAUDE.md with new fix information
- Update ERROR_ANALYSIS_AND_STACKTRACE.md with test results
- Create release notes for fix deployment

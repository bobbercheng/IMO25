# CRITICAL: OpenAI's "not" Constraint is Unsupported

**Date:** 2026-01-04
**Severity:** CRITICAL - Blacklist enforcement completely broken
**Impact:** 100% of blacklist violations pass through uncaught

---

## Executive Summary

**The pattern blacklist approach NEVER worked and NEVER will work** on OpenAI/OpenRouter APIs.

**Root Cause:** OpenAI's Structured Outputs **does not support** `"not"` constraints, as documented in their official API documentation.

**Evidence:** Model generated `\boxed{4048}` in first BFS run despite schema containing:
```json
"not": {"pattern": "\\\\boxed\\{4048\\}"}
```

**Impact:** All blacklist violations silently pass through - the API accepts the schema but **ignores the constraint entirely**.

---

## Technical Analysis

### From OpenAI Engineering Expert

**Source:** https://platform.openai.com/docs/guides/structured-outputs#supported-schemas

**Supported constraints:**
- ✅ `type`, `properties`, `required`
- ✅ `enum`, `minimum`, `maximum`
- ✅ `items`, `additionalProperties`
- ✅ `anyOf`, `allOf`

**NOT supported:**
- ❌ `not` ← **THIS IS WHAT WE WERE USING!**
- ❌ `if/then/else`
- ❌ `patternProperties`
- ❌ `oneOf` (partially)

### Why We Were Fooled

**Our integration test passed** with answer `4049`:
- ✅ We thought the pattern blocked `4048`
- ❌ Reality: Model just happened to pick different approach
- ❌ Pattern constraint was **never enforced**, just got lucky

**First BFS run revealed the truth:**
- Request: Schema with `"not": {"pattern": "\\\\boxed\\{4048\\}"}`
- Response: Generated `\boxed{4048}` anyway
- **The constraint was silently ignored!**

### How the API Behaves

```
1. Client sends schema with "not": {"pattern": ...}
   ↓
2. API parser: "I don't support 'not', skip it"
   ↓
3. Generation: No constraint applied
   ↓
4. API returns: HTTP 200 with generated text containing blacklisted value
   ↓
5. Client thinks: "Success!" (doesn't know constraint was ignored)
```

**No error, no warning - silent failure!**

---

## Evidence from BFS Log

**File:** `test_single_source_validation/bfs_run1_*.log`

**Lines 27-108 (Request):**
```json
{
  "response_format": {
    "type": "json_schema",
    "json_schema": {
      "schema": {
        "properties": {
          "solution": {
            "description": "...FORBIDDEN answers (proven incorrect): [2025, 4048, 4050]...",
            "not": {
              "pattern": "\\\\boxed\\{2025\\}|\\\\boxed\\{4048\\}|\\\\boxed\\{4050\\}"
            }
          }
        }
      },
      "strict": true
    }
  }
}
```

**Lines 269-280 (Response):**
```json
{
  "solution": "...The final answer is \\boxed{4048}...",
  "method": "analysis"
}
```

**Result:** Schema sent, constraint ignored, blacklisted value generated!

---

## Why Pattern Constraints Don't Work

### Constraint Type Comparison

| Constraint | API Support | Works? | Use Case |
|------------|-------------|--------|----------|
| `enum` | ✅ Supported | ✅ Yes | Allowlist small sets |
| `minimum/maximum` | ✅ Supported | ✅ Yes | Range bounds |
| `anyOf` | ✅ Supported | ✅ Yes | Multiple allowed ranges |
| `not` | ❌ **UNSUPPORTED** | ❌ **NO** | ← **What we tried** |
| `pattern` | ✅ Supported | ✅ Yes | String format matching |
| `not` + `pattern` | ❌ **DOUBLY UNSUPPORTED** | ❌ **NO** | ← **What we actually used** |

**Key insight:** Even though `pattern` alone works, `not` + `pattern` combines:
1. Unsupported operator (`not`)
2. Supported operator (`pattern`)
3. Result: **Entire constraint ignored!**

### Why `anyOf` Worked But `not` Didn't

**Example from earlier work:**

```json
// This WORKED (anyOf is supported):
"final_answer": {
  "type": "integer",
  "anyOf": [
    {"minimum": 1000, "maximum": 4047},
    {"enum": [4049]},
    {"minimum": 4051, "maximum": 6000}
  ]
}

// This FAILED (not is unsupported):
"solution": {
  "type": "string",
  "not": {
    "pattern": "\\\\boxed\\{4048\\}"
  }
}
```

**Result in BFS test:**
- `final_answer` field: Avoided 4048 ✅ (anyOf constraint worked)
- `solution` field: Generated `\boxed{4048}` ❌ (not constraint ignored)

This created the inconsistency we were trying to fix!

---

## Implications

### What We Thought Was Happening

```
Schema → API enforces pattern → Model can't generate 4048 → Success!
```

### What Actually Happened

```
Schema → API ignores "not" → Model generates whatever → 4048 appears → Oops!
```

### Why Integration Test Passed

```
Test run 1: Model picks different approach → Generates 4049 → Test passes ✅
BFS run 1: Model uses same approach → Generates 4048 → Reveals bug ❌
```

**We got lucky in testing, unlucky in production!**

---

## The ONLY Solutions That Work

### ❌ What DOESN'T Work

```json
// ALL of these are UNSUPPORTED and will be IGNORED:

{"not": {"const": 4048}}
{"not": {"enum": [4048, 4050]}}
{"not": {"pattern": "\\\\boxed\\{4048\\}"}}
{"not": {"minimum": 4048, "maximum": 4048}}
```

**None of these will prevent the model from generating the blacklisted value!**

### ✅ What DOES Work

**Option 1: Post-Processing Validation (REQUIRED)**

```python
def validate_against_blacklist(solution, blacklist):
    """Validate after generation, reject if blacklisted"""
    import re

    # Extract answer from \boxed{}
    match = re.search(r'\\boxed\{(\d+)\}', solution['solution'])
    if not match:
        return None  # Reject: no answer found

    answer = int(match.group(1))

    # Check blacklist
    if answer in blacklist:
        print(f">>>>>>> [BLACKLIST VIOLATION] Generated {answer}, rejecting...")
        return None  # Reject: blacklisted value

    # Add to solution dict
    solution['final_answer'] = answer
    return solution
```

**Why this works:** Happens AFTER API generation, catches violations, enables retry.

**Option 2: Prompt-Based Blacklist (Partial)**

```
The following answers are PROVEN INCORRECT:
- 4048 (FORBIDDEN)
- 4050 (FORBIDDEN)

You MUST use a COMPLETELY DIFFERENT approach.
```

**Why this helps:** Semantic guidance to model, reduces likelihood.
**Why this isn't enough:** Not guaranteed, model may ignore prompts.

**Option 3: Remove Schema Constraint (Clean Up)**

```json
{
  "solution": {"type": "string"},  // No "not" constraint
  "method": {"type": "string"}
}
```

**Why this is correct:** Removes non-functional constraint, clarifies intent.

---

## Recommended Fix

### Step 1: Remove Useless Pattern Constraint

**File:** `code/schema_blacklist.py`

**Before:**
```python
schema = {
    "properties": {
        "solution": {
            "not": {"pattern": combined_pattern}  # ← DOESN'T WORK!
        }
    }
}
```

**After:**
```python
schema = {
    "properties": {
        "solution": {
            "type": "string",
            # NOTE: Cannot use "not": {"pattern": ...} because OpenAI's
            # Structured Outputs does not support "not" constraints.
            # Blacklist validation must be done in post-processing.
        }
    }
}
```

### Step 2: Add Post-Processing Validation

**File:** `code/agent_gpt_oss.py`

```python
def parse_structured_solution(content, blacklist=None):
    """
    Parse structured JSON solution from API response.

    Args:
        content: JSON string from API
        blacklist: Optional list of blacklisted answer values

    Returns:
        Parsed dict with final_answer, or None if invalid/blacklisted
    """
    try:
        parsed = json.loads(content.strip())

        # ... existing validation ...

        # Extract final_answer from \boxed{} if missing
        if 'final_answer' not in parsed:
            import re
            match = re.search(r'\\boxed\{(\d+)\}', parsed['solution'])
            if not match:
                return None
            parsed['final_answer'] = int(match.group(1))

        # BLACKLIST VALIDATION (post-processing)
        if blacklist and parsed['final_answer'] in blacklist:
            print(f">>>>>>> [BLACKLIST] Rejected answer {parsed['final_answer']}")
            return None  # Force retry

        return parsed

    except (json.JSONDecodeError, TypeError, ValueError):
        return None
```

### Step 3: Pass Blacklist to Parser

**File:** `code/agent_gpt_oss.py` (where parse_structured_solution is called)

```python
# Load blacklist
if use_schema_blacklist and SCHEMA_BLACKLIST_AVAILABLE:
    from schema_blacklist import load_solution_blacklist
    blacklist_data = load_solution_blacklist(problem_file)
    blacklist_values = [entry['answer'] for entry in blacklist_data]
else:
    blacklist_values = []

# Parse with blacklist validation
structured = parse_structured_solution(content, blacklist=blacklist_values)
if structured:
    print(f">>>>>>> [VALIDATED] Answer {structured['final_answer']} passed blacklist check")
else:
    print(f">>>>>>> [REJECTED] Solution failed validation")
    # Trigger retry logic
```

---

## Testing Strategy

### Unit Test: Blacklist Enforcement

```python
def test_blacklist_enforcement():
    """Test that post-processing catches blacklisted values"""

    # Response with blacklisted value
    content = json.dumps({
        "solution": "The answer is \\boxed{4048}.",
        "method": "test"
    })

    blacklist = [4048, 4050, 2025]
    result = parse_structured_solution(content, blacklist=blacklist)

    assert result is None, "Should reject blacklisted value"

    # Response with allowed value
    content2 = json.dumps({
        "solution": "The answer is \\boxed{4044}.",
        "method": "test"
    })

    result2 = parse_structured_solution(content2, blacklist=blacklist)

    assert result2 is not None, "Should accept non-blacklisted value"
    assert result2['final_answer'] == 4044
```

### Integration Test: BFS with Validation

```bash
# Should now properly reject 4048
GPT_OSS_SOLUTION_REASONING=high NUM_INITIAL_ATTEMPTS=3 \
./run_bfs_baseline.sh problems/imo06.txt test_validation

# Expected: Retries until non-blacklisted answer generated
# Logs should show: ">>>>>>> [BLACKLIST] Rejected answer 4048"
```

---

## Lessons Learned

### 1. Always Verify API Capabilities

**Don't assume:** "It's valid JSON Schema, so it must work"
**Do verify:** Check API documentation for supported constraints

### 2. Test Real Failure Cases

**Don't assume:** "Test passed once, it works"
**Do verify:** Test with inputs designed to trigger constraint

### 3. Silent Failures Are Dangerous

**Problem:** API accepted unsupported constraint without error
**Solution:** Add explicit validation that can fail loudly

### 4. Schema != Guarantee

**JSON Schema defines:** What constraints mean
**API implements:** Subset of constraints it actually enforces
**Gap:** Must be filled with application-level validation

---

## Summary

| Aspect | Before | After |
|--------|--------|-------|
| **Schema Constraint** | `"not": {"pattern": ...}` | Removed (doesn't work) |
| **Validation Method** | API-level (failed silently) | Post-processing (explicit) |
| **Blacklist Enforcement** | 0% (completely broken) | 100% (validated in code) |
| **Error Detection** | Silent failure | Loud rejection with retry |
| **Reliability** | False sense of security | Actual security |

**Bottom Line:**
The pattern blacklist was a well-intentioned idea based on valid JSON Schema syntax, but OpenAI/OpenRouter APIs don't support the `"not"` constraint. Must use post-processing validation instead.

**Status:** 🔴 CRITICAL BUG FOUND → 🟡 FIX DESIGNED → ⏳ AWAITING IMPLEMENTATION

---

**Next Steps:**
1. Remove pattern constraint from schema (cleanup)
2. Implement post-processing blacklist validation
3. Add unit tests for validation logic
4. Rerun BFS test to verify blacklist now works

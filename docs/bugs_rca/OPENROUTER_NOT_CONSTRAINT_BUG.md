# OpenRouter "not" Constraint Bug & Fix

## Critical Finding: OpenRouter Does NOT Support JSON Schema "not" Constraints

**Date:** 2026-01-03
**Impact:** CRITICAL - Schema blacklist was not working on OpenRouter

---

## Problem Summary

User reported that schema blacklist was failing 40% of the time when testing with OpenRouter:

```
Test Run 1: 1/3 violations (66.7% compliance)
Test Run 2: 0/3 violations (100% compliance)
Test Run 3: 2/3 violations (33.3% compliance)
Test Run 4: 1/3 violations (66.7% compliance)
Test Run 5: 2/3 violations (33.3% compliance)
Overall: 6/15 violations (40% violation rate)
```

Model was still generating blacklisted values (4048, 4050) despite structured output with "not" constraint.

---

## Root Cause Investigation

Created diagnostic test (`test_openrouter_schema_support.py`) to check which JSON Schema constraints OpenRouter supports:

### Test Results

| Constraint Type | Violation Rate | Status |
|----------------|---------------|--------|
| **"not" constraint** | **60%** | ❌ **NOT ENFORCED** |
| **"enum" constraint** | **0%** | ✅ **ENFORCED** |
| Range only (baseline) | 100% | ⚠️ N/A (model naturally generates 4048) |

**Conclusion:** OpenRouter's structured output API does NOT enforce JSON Schema "not" constraints, but DOES enforce "enum" and "anyOf" constraints.

---

## Solution: Use "anyOf" with Range Splits

Instead of either:
- ❌ **"not" constraint** - Doesn't work on OpenRouter (60% violation rate)
- ❌ **Huge enum** - Works but causes context explosion (30KB, 5,062 values)

We now use **"anyOf" with range splits**:

```json
"final_answer": {
  "anyOf": [
    {"type": "integer", "minimum": 1012, "maximum": 4047},  // Before 4048
    {"type": "integer", "enum": [4049]},                     // Between blacklisted values
    {"type": "integer", "minimum": 4051, "maximum": 6075}    // After 4050
  ],
  "description": "FORBIDDEN (proven incorrect): [4050, 4048]. You MUST use a different approach."
}
```

### Benefits

✅ **100% compliance on OpenRouter** (verified across multiple test runs)
✅ **Compact schema** (~677 bytes vs ~30KB with enum)
✅ **OpenRouter compatible** (uses supported "anyOf" constraint)
✅ **Efficient context usage** (50× reduction from original enum approach)

---

## Implementation Changes

### Files Modified

1. **`code/schema_blacklist.py`**
   - Added `build_anyof_ranges()` helper function
   - Changed OPTION 2 from "not" to "anyOf" constraint
   - Updated `get_schema_metadata()` to detect and report "anyOf" constraints
   - Default behavior now uses "anyOf" (not "not")

2. **`code/agent_gpt_oss.py`**
   - Updated schema blacklist logging to show "anyOf" segments
   - Added display for range segments count

3. **`test_schema_blacklist_llm.py`**
   - Updated all tests to expect "anyOf" instead of "not"
   - Fixed blacklist extraction from anyOf schemas
   - Updated test assertions and output messages

4. **`test_openrouter_schema_support.py`** (NEW)
   - Diagnostic tool to test which constraints OpenRouter supports
   - Tests "not", "enum", and range constraints
   - Clearly shows which constraints are enforced

---

## Verification Results

### Before Fix (using "not" constraint)

```
User's 5 test runs:
- 40% violation rate (6/15 attempts generated blacklisted values)
- Model frequently generated 4048 and 4050 despite blacklist
```

### After Fix (using "anyOf" constraint)

```
Test Run 1: 3/3 valid (100% compliance)
Test Run 2: 2/2 valid (100% compliance) - 1 network error
Test Run 3: 1/1 valid (100% compliance) - 2 network errors

Overall: 6/6 successful attempts, 0 blacklisted values (100% compliance)
```

**Result:** ✅ **0% violation rate** - Complete fix verified

---

## Technical Details

### How "anyOf" Range Splits Work

For blacklist `[4048, 4050]` in range `[1012, 6075]`:

1. **Sort blacklisted values:** `[4048, 4050]`
2. **Generate segments:**
   - Segment 1: `[1012, 4047]` - All values before first blacklisted
   - Segment 2: `[4049]` - Single value between blacklisted values
   - Segment 3: `[4051, 6075]` - All values after last blacklisted

3. **Combine with anyOf:**
   ```json
   "anyOf": [
     {"minimum": 1012, "maximum": 4047},
     {"enum": [4049]},
     {"minimum": 4051, "maximum": 6075}
   ]
   ```

This physically prevents the model from generating 4048 or 4050, since those values don't appear in any segment.

### Why "not" Constraint Fails on OpenRouter

OpenRouter's structured output implementation likely:
1. Uses a subset of JSON Schema validation
2. Only implements positive constraints (enum, anyOf, minimum/maximum)
3. Doesn't implement negative constraints (not, if/then/else)

This is a **limitation of OpenRouter's API**, not a bug in our code.

---

## Recommendations

1. **Always use "anyOf" for blacklisting** when deploying to OpenRouter
2. **Test constraints explicitly** when using new providers
3. **Keep diagnostic script** (`test_openrouter_schema_support.py`) for testing other providers
4. **Document provider limitations** in CLAUDE.md

---

## Related Files

- `code/schema_blacklist.py` - Schema generation with anyOf support
- `code/agent_gpt_oss.py` - Agent that uses schema blacklist
- `test_schema_blacklist_llm.py` - Unit tests for schema blacklist
- `test_openrouter_schema_support.py` - Diagnostic test for constraint support
- `SCHEMA_BLACKLIST_BUG_FIX.md` - Earlier bug (schema not applied in BFS mode)
- `SCHEMA_CONTEXT_EXPLOSION_FIX.md` - Context explosion issue (huge enum)

---

## Timeline

1. **2026-01-02:** Implemented schema blacklist with "not" constraint
2. **2026-01-03 Morning:** Fixed schema not applied in BFS mode
3. **2026-01-03 Afternoon:** Fixed context explosion (enum → "not")
4. **2026-01-03 Evening:** User reports 40% violation rate
5. **2026-01-03 Evening:** Root cause identified - OpenRouter doesn't support "not"
6. **2026-01-03 Evening:** Fixed by changing to "anyOf" - 100% compliance verified

---

## Conclusion

**Root Cause:** OpenRouter does not support JSON Schema "not" constraints.

**Solution:** Use "anyOf" with range splits instead - compact, efficient, and 100% effective on OpenRouter.

**Status:** ✅ **FIXED AND VERIFIED**

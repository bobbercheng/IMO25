# MCTS Quick Fix Guide: Restoring 50-Minute Success

## TL;DR - What Changed and How to Fix

**Status:** MCTS code IS present on current branch but has been modified. Baseline configuration was reverted in commit 8d84155, but additional changes may still interfere.

## Key Finding: Potential Control Flow Bug

**File:** `code/agent_gpt_oss.py`, Line 1503

**Current code:**
```python
if use_proof_sketch:
    # Proof sketch pipeline

elif use_mcts:  # ← BUG: This is 'elif' instead of 'if'
    # MCTS code
```

**At bfbebaf (working):**
```python
if use_mcts:  # ← Was 'if', allowing both to potentially run
    # MCTS code

if not use_mcts and num_initial_attempts > 1:
    # BFS code
```

**Impact:** If `use_proof_sketch=True` (or defaults to True somewhere), MCTS is skipped entirely.

**Quick Test:**
```bash
# Check if MCTS actually runs:
python code/agent_gpt_oss.py problems/imo01.txt \
  --use-mcts \
  --mcts-simulations 5 \
  --mcts-exploration 1.414 \
  --solution-reasoning low \
  --self-improvement-reasoning low \
  --verification-reasoning low \
  --log test_mcts.log

# Search log for "MCTS MODE ACTIVATED"
grep "MCTS MODE ACTIVATED" test_mcts.log
```

**If MCTS MODE not found:** Fix line 1503 from `elif use_mcts:` to `if use_mcts:`

## Additional Differences to Check

### 1. Hybrid Strategies at Root (May Dilute Exploration)

**File:** `code/mcts_bfs.py`, Lines 142-150

**Current version adds 4 hybrid strategies:**
```python
hybrid_strategies = [
    "Induction with extremal principle",
    "Contradiction with pigeonhole principle",
    "Construction with algebraic manipulation",
    "Combinatorial with geometric insight"
]
all_strategies = common_strategies + hybrid_strategies  # 12 total
```

**At bfbebaf:** Only 8 base strategies, no hybrids at root

**Fix:** Comment out lines 142-150 to remove hybrids:
```python
# hybrid_strategies = [...]
# all_strategies = common_strategies + hybrid_strategies
all_strategies = common_strategies  # Just 8 base strategies
```

### 2. Best-of-N Parameter (Defaults to 0, Safe)

**File:** `code/agent_gpt_oss.py`, Line 1526

**Current:** Passes `best_of_n=best_of_n` to mcts_bfs_search()

**Default:** 0 (disabled)

**Risk:** If user passes `--best-of-n 3` (or any non-zero), triggers re-verification loop that could hang

**Fix:** Don't pass `--best-of-n` flag, OR remove line 1526 entirely

### 3. Content Length Limit (2× Larger)

**File:** `code/agent_gpt_oss.py`, Line 239

**Current:**
```python
MAX_CONTENT_LENGTH = 50000*2  # 100000
```

**At bfbebaf:**
```python
MAX_CONTENT_LENGTH = 50000
```

**Impact:** Allows longer responses, may slow generation

**Fix:** Change line 239 to:
```python
MAX_CONTENT_LENGTH = 50000
```

### 4. Verification Not Using Safeguards (Could Hang)

**File:** `code/agent_gpt_oss.py`, Line 1519

**Current:** MCTS uses `verify_solution` (no timeout protection)
```python
verify_solution_func=verify_solution,
```

**Risk:** If verification hangs (e.g., high reasoning gets stuck), MCTS hangs

**Fix:** Change line 1519 to:
```python
verify_solution_func=verify_solution_safe,
```

## Recommended Testing Sequence

### Test 1: Verify MCTS Actually Runs
```bash
python code/agent_gpt_oss.py problems/imo01.txt \
  --use-mcts \
  --mcts-simulations 5 \
  --mcts-exploration 1.414 \
  --solution-reasoning low \
  --self-improvement-reasoning low \
  --verification-reasoning low \
  --log test1_check_mcts_runs.log 2>&1

# Check log:
grep "MCTS MODE ACTIVATED" test1_check_mcts_runs.log
grep "\[MCTS\]" test1_check_mcts_runs.log | head -20
```

**Expected:** Should see MCTS MODE ACTIVATED and [MCTS] log messages

**If NOT found:** Apply control flow fix (elif → if)

### Test 2: With Control Flow Fix Only
```bash
# Edit code/agent_gpt_oss.py line 1503: elif → if

python code/agent_gpt_oss.py problems/imo01.txt \
  --use-mcts \
  --mcts-simulations 5 \
  --mcts-exploration 1.414 \
  --solution-reasoning low \
  --self-improvement-reasoning low \
  --verification-reasoning low \
  --log test2_control_flow_fix.log 2>&1
```

**Expected:** 50-minute success (like bfbebaf)

### Test 3: Add Hybrid Strategy Removal
```bash
# Edit code/mcts_bfs.py lines 142-150: Comment out hybrids

python code/agent_gpt_oss.py problems/imo01.txt \
  --use-mcts \
  --mcts-simulations 5 \
  --mcts-exploration 1.414 \
  --solution-reasoning low \
  --self-improvement-reasoning low \
  --verification-reasoning low \
  --log test3_no_hybrids.log 2>&1
```

### Test 4: Add Verification Safeguards
```bash
# Edit code/agent_gpt_oss.py line 1519: verify_solution → verify_solution_safe

python code/agent_gpt_oss.py problems/imo01.txt \
  --use-mcts \
  --mcts-simulations 5 \
  --mcts-exploration 1.414 \
  --solution-reasoning low \
  --self-improvement-reasoning low \
  --verification-reasoning low \
  --log test4_with_safeguards.log 2>&1
```

### Test 5: All Fixes Applied
Apply all 4 fixes and run complete test.

## Code Diffs for Quick Fixes

### Fix #1: Control Flow (CRITICAL)

**File:** `code/agent_gpt_oss.py`

```diff
--- a/code/agent_gpt_oss.py
+++ b/code/agent_gpt_oss.py
@@ -1500,7 +1500,7 @@ def agent(problem_statement, other_prompts=[], memory_file=None, resume_from_me
                 use_proof_sketch = False

         # MCTS-guided exploration if requested
-        elif use_mcts:
+        if use_mcts:
             print(f"\n{'='*80}")
             print(f">>>>>>> MCTS MODE ACTIVATED")
             print(f">>>>>>> Running {mcts_simulations} MCTS-guided simulations")
```

### Fix #2: Remove Hybrid Strategies

**File:** `code/mcts_bfs.py`

```diff
--- a/code/mcts_bfs.py
+++ b/code/mcts_bfs.py
@@ -139,16 +139,7 @@ class MCTSExplorer:
             "Extremal principle"
         ]

-        # Add hybrid strategies that combine multiple approaches
-        hybrid_strategies = [
-            "Induction with extremal principle",
-            "Contradiction with pigeonhole principle",
-            "Construction with algebraic manipulation",
-            "Combinatorial with geometric insight"
-        ]
-
-        all_strategies = common_strategies + hybrid_strategies
-
+        all_strategies = common_strategies
         for strategy in all_strategies:
             self.root.add_child(strategy)

-        print(f">>>>>>> [MCTS] Initialized with {len(common_strategies)} base + {len(hybrid_strategies)} hybrid strategies")
+        print(f">>>>>>> [MCTS] Initialized with {len(common_strategies)} base strategies")
```

### Fix #3: Use Verification Safeguards

**File:** `code/agent_gpt_oss.py`

```diff
--- a/code/agent_gpt_oss.py
+++ b/code/agent_gpt_oss.py
@@ -1516,7 +1516,7 @@ def agent(problem_statement, other_prompts=[], memory_file=None, resume_from_me
                 mcts_result = mcts_bfs_search(
                     problem_statement=problem_statement,
                     num_simulations=mcts_simulations,
                     generate_solution_func=init_explorations,
-                    verify_solution_func=verify_solution,
+                    verify_solution_func=verify_solution_safe,
                     sol_reasoning=sol_reasoning,
                     self_imp_reasoning=self_imp_reasoning,
                     ver_reasoning=ver_reasoning,
```

### Fix #4: Restore Content Length

**File:** `code/agent_gpt_oss.py`

```diff
--- a/code/agent_gpt_oss.py
+++ b/code/agent_gpt_oss.py
@@ -236,7 +236,7 @@ def _handle_streaming_response(response):
     # Repetition detection parameters
     REPETITION_WINDOW = 50  # Check last N characters
     REPETITION_THRESHOLD = 5  # Number of times a pattern can repeat
-    MAX_CONTENT_LENGTH = 50000*2  # Maximum content length before forcing stop
+    MAX_CONTENT_LENGTH = 50000  # Maximum content length before forcing stop

     def detect_repetition(text, window_size=REPETITION_WINDOW):
         """Detect if the same pattern repeats excessively at the end of text."""
```

## Expected Outcome

**After applying Fix #1 (minimum):** MCTS should run and complete in ~50 minutes with the proven baseline configuration.

**After applying all fixes:** Maximum compatibility with bfbebaf baseline while maintaining safety improvements.

## Verification Checklist

- [ ] Test 1: Confirm MCTS MODE ACTIVATED appears in log
- [ ] Test 1: Confirm [MCTS] log messages appear
- [ ] Test 2: With Fix #1, runtime ~50 minutes
- [ ] Test 2: With Fix #1, solution found and verified
- [ ] Test 3: With Fixes #1+#2, compare runtime to Test 2
- [ ] Test 4: With Fixes #1+#2+#3, confirm no hangs
- [ ] Test 5: With all fixes, final runtime and success rate

## Summary

**Most Likely Culprit:** Control flow bug (elif use_mcts) preventing MCTS from running

**Quick Fix:** Change line 1503 from `elif use_mcts:` to `if use_mcts:`

**Additional Improvements:** Remove hybrid strategies, use verification safeguards, restore content length

**Test First:** Run Test 1 to confirm MCTS actually executes before applying fixes

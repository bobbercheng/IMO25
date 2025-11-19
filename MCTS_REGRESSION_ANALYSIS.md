# MCTS Regression Analysis: bfbebaf vs Current HEAD

## Executive Summary

**Finding:** The current branch (claude/review-agent-gpt-log-01RALGVX66B81F1WF2bRsRxe @ 6f43597) **DOES contain MCTS code** and the integration appears structurally correct. However, there are significant changes between bfbebaf and HEAD that may affect performance.

**Branch Relationship:**
- Commit bfbebaf (working MCTS, 50 min success) and current HEAD (6f43597) are BOTH descended from common ancestor 4724f9b
- bfbebaf introduced MCTS-Enhanced BFS
- Current HEAD includes all of bfbebaf's changes PLUS 14 additional commits with enhancements and fixes

## Working Implementation at bfbebaf (BASELINE)

### 1. MCTS Configuration at bfbebaf
**File:** `code/mcts_bfs.py` (549 lines)

**Key Parameters:**
```python
def mcts_bfs_search(
    problem_statement: str,
    num_simulations: int,
    exploration_constant: float = 1.414,  # sqrt(2) - baseline
    max_depth: int = 2,                    # Baseline depth
    save_tree_path: Optional[str] = None
) -> Optional[Dict]  # Returns single Dict
```

**Search Function Return:**
```python
def search(...) -> Dict:
    # Returns: best_solution (Dict)
    return best_solution
```

**Strategy Tree:**
- 8 base strategies: induction, contradiction, construction, pigeonhole, combinatorial, algebraic, geometric, extremal
- NO hybrid strategies at root
- Dynamic hybrid generation from successful children

### 2. Agent Integration at bfbebaf
**File:** `code/agent_gpt_oss.py` (1256 lines)

**Agent Function Signature:**
```python
def agent(problem_statement, other_prompts=[], memory_file=None, resume_from_memory=False,
          solution_reasoning=None, self_improvement_reasoning=None, verification_reasoning=None,
          num_initial_attempts=1,
          use_mcts=False,           # Enable MCTS
          mcts_simulations=5,       # Baseline: 5 simulations
          mcts_exploration=1.414):  # Baseline: sqrt(2)
```

**MCTS Integration (lines 905-944):**
```python
if use_mcts:
    from mcts_bfs import mcts_bfs_search

    mcts_result = mcts_bfs_search(
        problem_statement=problem_statement,
        num_simulations=mcts_simulations,
        generate_solution_func=init_explorations,
        verify_solution_func=verify_solution,
        sol_reasoning=sol_reasoning,
        self_imp_reasoning=self_imp_reasoning,
        ver_reasoning=ver_reasoning,
        exploration_constant=mcts_exploration,
        max_depth=2,
        save_tree_path=f"{memory_file.replace('.json', '_mcts_tree.json')}" if memory_file else None
    )

    if mcts_result:
        solution = mcts_result['solution']
        verify = mcts_result['verify']
        good_verify = mcts_result['good_verify']
```

**Working Command (50 minutes):**
```bash
python code/agent_gpt_oss.py problems/imo01.txt \
  --use-mcts \
  --mcts-simulations 5 \
  --mcts-exploration 1.414 \
  --solution-reasoning low \
  --self-improvement-reasoning low \
  --verification-reasoning low \
  --log baseline.log
```

## Changes Between bfbebaf and HEAD (14 Commits)

### Commit Timeline
1. `3b7a292` - upload output log files of test_mcts_translation.sh
2. `2427765` - Add Tier 1 Features: Answer Validation, Stuck Detection, Score Tracking
3. `7393ccb` - add test 4 log
4. `069fe2f` - Add comprehensive Test 4 and Tier 1/3 analysis reports
5. `eb3211f` - **Implement three major enhancements to GPT-OSS agent** ⚠️
6. `72ef35e` - add test_enhancements log
7. `4601809` - Add comprehensive analysis of failed enhancement tests
8. `8d84155` - **Implement Priority 1 & 2: Emergency fixes and verification safeguards** ⚠️
9. `254477f` - Add baseline restoration test script
10. `b3d6be1` - Add comprehensive Priority 1 & 2 implementation documentation
11. `dd8e76e` - Fix Python scoping syntax error in verification safeguards
12. `7002797` - Fix problem file path in baseline restoration test
13. `277558f` - Add test output directories to .gitignore
14. `6f43597` - add test_baseline_logs

### Critical Change #1: commit eb3211f (Enhancements)

**MCTS "Optimizations" (Later proved to cause 12× regression):**
```diff
# mcts_bfs.py changes:
- mcts_simulations=5      → 8 (60% increase)
- exploration_constant=1.414 → 1.6 (13% increase)
- max_depth=2             → 3 (50% increase)

# Added hybrid strategies at root:
+ "Induction with extremal principle"
+ "Contradiction with pigeonhole principle"
+ "Construction with algebraic manipulation"
+ "Combinatorial with geometric insight"
```

**Best-of-N Sampling:**
```python
# MCTSExplorer.search() return changed:
- return best_solution  # Dict
+ return best_solution, all_solutions_sorted  # Tuple

# mcts_bfs_search() signature added:
+ best_of_n: int = 0  # New parameter
```

**Impact:** Test 1 showed 373 min runtime vs 31 min baseline (12× regression)

### Critical Change #2: commit 8d84155 (Emergency Fixes)

**Reverted MCTS to Baseline:**
```diff
# agent_gpt_oss.py:
- mcts_simulations=8  → 5 (reverted)
- mcts_exploration=1.6 → 1.414 (reverted)

# mcts_bfs.py call:
- max_depth=3 → 2 (reverted)
```

**Added Verification Safeguards:**
```python
# New global variables:
+ VERIFICATION_TIMEOUT = 600  # 10 minutes
+ VERIFICATION_MAX_ATTEMPTS = 3
+ VERIFICATION_SAFEGUARDS_ENABLED = True

# New function:
+ def verify_solution_safe(problem_statement, solution, verbose=True,
+                          reasoning_effort=None, max_attempts=None,
+                          timeout_seconds=None, fallback_reasoning="medium"):
```

**Proof Sketch Phase (300+ lines added):**
```python
+ def generate_proof_sketch(problem_statement, reasoning_effort="low", verbose=True)
+ def verify_proof_structure(problem_statement, proof_sketch, ...)
+ def fill_in_proof_details(problem_statement, proof_sketch, ...)
+ def verify_complete_proof(problem_statement, complete_proof, ...)
```

### Critical Change #3: Tier 1 Features (commit 2427765)

**Answer Validation:**
```python
+ def extract_answer_from_solution(solution)
+ def validate_answer_format(answer, expected_pattern=None)
+ def compare_answers(answer1, answer2, tolerance=1e-10)
```

**Stuck Detection:**
```python
+ def detect_stuck_pattern(correct_history, error_history, current_iteration, threshold=3)
```

**Score Tracking:**
```python
+ solution_scores = []  # Track score history
+ # Enhanced logging with score progression
```

## Current State Analysis (HEAD @ 6f43597)

### MCTS Code Status: ✅ PRESENT

**File:** `code/agent_gpt_oss.py` (1924 lines - 668 lines added)

**Agent Signature (line 1418):**
```python
def agent(problem_statement, other_prompts=[], memory_file=None, resume_from_memory=False,
          solution_reasoning=None, self_improvement_reasoning=None, verification_reasoning=None,
          num_initial_attempts=1,
          use_mcts=False,           # ✅ PRESENT
          mcts_simulations=5,       # ✅ REVERTED to baseline
          mcts_exploration=1.414,   # ✅ REVERTED to baseline
          best_of_n=0,              # ⚠️ NEW PARAMETER
          use_proof_sketch=False):  # ⚠️ NEW PARAMETER
```

**MCTS Integration (lines 1503-1543):**
```python
elif use_mcts:  # ⚠️ Changed from 'if' to 'elif'
    from mcts_bfs import mcts_bfs_search

    mcts_result = mcts_bfs_search(
        problem_statement=problem_statement,
        num_simulations=mcts_simulations,
        generate_solution_func=init_explorations,
        verify_solution_func=verify_solution,  # ⚠️ NOT verify_solution_safe
        sol_reasoning=sol_reasoning,
        self_imp_reasoning=self_imp_reasoning,
        ver_reasoning=ver_reasoning,
        exploration_constant=mcts_exploration,
        max_depth=2,  # ✅ Baseline restored
        save_tree_path=f"{memory_file.replace('.json', '_mcts_tree.json')}" if memory_file else None,
        best_of_n=best_of_n  # ⚠️ NEW PARAMETER
    )
```

**File:** `code/mcts_bfs.py` (625 lines - 76 lines added)

**Function Signature:**
```python
def mcts_bfs_search(
    problem_statement: str,
    num_simulations: int,
    sol_reasoning: str = "low",
    self_imp_reasoning: str = "high",  # ⚠️ Changed default
    ver_reasoning: str = "high",       # ⚠️ Changed default
    exploration_constant: float = 1.414,  # ✅ Baseline
    max_depth: int = 2,                    # ✅ Baseline
    save_tree_path: Optional[str] = None,
    best_of_n: int = 0                     # ⚠️ NEW PARAMETER
) -> Optional[Dict]:  # ✅ Still returns Dict (not tuple)
```

**Search Return (line 556):**
```python
best_solution, all_solutions = explorer.search(...)  # ⚠️ Unpacks tuple
# ...
return best_solution  # ✅ Still returns Dict
```

## Potential Regressions Identified

### 1. ⚠️ Control Flow Change: `if` → `elif`

**At bfbebaf (line 905):**
```python
if solution is None:
    if use_mcts:  # First priority
        # MCTS code

    if not use_mcts and num_initial_attempts > 1:  # Second priority
        # BFS code
```

**At HEAD (line 1503):**
```python
if solution is None:
    if use_proof_sketch:  # First priority - NEW!
        # Proof sketch pipeline

    elif use_mcts:  # Second priority - CHANGED!
        # MCTS code

    if not use_mcts and num_initial_attempts > 1:  # Third priority
        # BFS code
```

**Impact:** `elif use_mcts` means MCTS will be skipped if `use_proof_sketch=True`!

### 2. ⚠️ Default Reasoning Changes in mcts_bfs_search

**At bfbebaf:**
```python
def mcts_bfs_search(...,
    sol_reasoning: str = "low",
    self_imp_reasoning: str = "high",
    ver_reasoning: str = "high")
```

**Impact:** If called without explicit parameters, defaults changed from what might have been used.

### 3. ⚠️ Best-of-N Re-verification

**New code in mcts_bfs.py (lines 574-618):**
```python
if best_of_n > 0 and len(all_solutions) > 0:
    for idx, solution_dict in enumerate(top_n_solutions, 1):
        verify_result, good_verify = verify_solution_func(
            problem_statement,
            solution_text,
            reasoning_effort=ver_reasoning  # ⚠️ Re-verifies with same reasoning
        )
```

**Issue:** If `best_of_n > 0`, MCTS will re-verify top N solutions. If this hangs or takes too long, it delays return.

### 4. ⚠️ Verification Safeguards Not Used in MCTS Path

**Analysis:**
- `init_explorations()` uses `verify_solution()` (line 1230)
- `mcts_bfs_search()` passes `verify_solution` (not `verify_solution_safe`) to MCTS
- Best-of-N re-verification uses `verify_solution_func` (which is `verify_solution`)

**Impact:** MCTS path does NOT benefit from timeout/retry safeguards! If verification hangs, MCTS will hang.

### 5. ⚠️ Hybrid Strategies at Root Level

**At HEAD:**
```python
hybrid_strategies = [
    "Induction with extremal principle",
    "Contradiction with pigeonhole principle",
    "Construction with algebraic manipulation",
    "Combinatorial with geometric insight"
]
```

**Impact:** Root has 8 + 4 = 12 strategies instead of 8. This affects UCB1 exploration distribution and could slow down convergence to good strategies.

### 6. ⚠️ Increased Content Length Limit

**At bfbebaf:**
```python
MAX_CONTENT_LENGTH = 50000
```

**At HEAD:**
```python
MAX_CONTENT_LENGTH = 50000*2  # 100000
```

**Impact:** Allows 2× longer responses, potentially slowing down generation without adding value.

## Root Cause Hypothesis

### Primary Suspect: Control Flow Bug (`elif use_mcts`)

**Hypothesis:** If the user's command includes any flag that sets `use_proof_sketch=True`, MCTS will be skipped entirely.

**Test:**
```bash
# This would skip MCTS if use_proof_sketch defaults to True or is set:
python code/agent_gpt_oss.py problems/imo01.txt \
  --use-mcts \
  --mcts-simulations 5 \
  --mcts-exploration 1.414 \
  --solution-reasoning low \
  --self-improvement-reasoning low \
  --verification-reasoning low
```

### Secondary Suspect: Best-of-N Verification Overhead

**Hypothesis:** If `best_of_n > 0` (default or user-set), the re-verification loop adds significant overhead and could hang.

**Test:** Check if `best_of_n` is being set to a non-zero value anywhere.

### Tertiary Suspect: Hybrid Strategies Dilution

**Hypothesis:** Adding 4 hybrid strategies at root dilutes UCB1 scores, causing MCTS to waste simulations on suboptimal hybrid combinations instead of focusing on proven base strategies.

## Recommended Fixes

### Fix #1: Revert Control Flow (HIGH PRIORITY)
```python
# Change line 1503 from:
elif use_mcts:

# Back to:
if use_mcts:
```

### Fix #2: Use Verification Safeguards in MCTS Path
```python
# In agent_gpt_oss.py, line 1519:
verify_solution_func=verify_solution_safe,  # Instead of verify_solution
```

### Fix #3: Disable Best-of-N by Default
```python
# Ensure default best_of_n=0 everywhere
# OR remove best-of-N code entirely if not proven beneficial
```

### Fix #4: Remove Hybrid Strategies from Root
```python
# In mcts_bfs.py, line 142-150, comment out:
# hybrid_strategies = [...]
# all_strategies = common_strategies  # Don't add hybrids
```

### Fix #5: Restore Original Content Length
```python
# In agent_gpt_oss.py, line 239:
MAX_CONTENT_LENGTH = 50000  # Revert from 100000
```

## Testing Plan

### Test 1: Exact Baseline Restoration
```bash
# Ensure these parameters match bfbebaf exactly:
python code/agent_gpt_oss.py problems/imo01.txt \
  --use-mcts \
  --mcts-simulations 5 \
  --mcts-exploration 1.414 \
  --solution-reasoning low \
  --self-improvement-reasoning low \
  --verification-reasoning low \
  --log test_exact_baseline.log

# Expected: 50-minute success
```

### Test 2: With Fixes Applied
After applying Fix #1-#5, run same command and compare runtime.

### Test 3: Identify Specific Breaking Change
Apply fixes one at a time:
1. Just Fix #1 (control flow)
2. Fix #1 + Fix #2 (safeguards)
3. Fix #1 + Fix #2 + Fix #3 (best-of-n)
4. All fixes

Compare which fix(es) restore 50-minute performance.

## Summary Table

| Aspect | bfbebaf (Working) | HEAD (Current) | Status |
|--------|-------------------|----------------|--------|
| MCTS Code Present | ✅ Yes | ✅ Yes | OK |
| `use_mcts` parameter | ✅ Yes | ✅ Yes | OK |
| Simulations default | ✅ 5 | ✅ 5 (reverted) | OK |
| Exploration default | ✅ 1.414 | ✅ 1.414 (reverted) | OK |
| Max depth | ✅ 2 | ✅ 2 (reverted) | OK |
| Control flow | ✅ `if` | ⚠️ `elif` | **BUG** |
| Best-of-N | ❌ Not present | ⚠️ Added, default 0 | RISK |
| Root strategies | ✅ 8 base | ⚠️ 12 (8+4 hybrid) | CHANGED |
| Verification | ✅ verify_solution | ⚠️ Still verify_solution (not _safe) | RISK |
| Content limit | ✅ 50000 | ⚠️ 100000 | CHANGED |
| Proof sketch | ❌ Not present | ⚠️ Added, takes priority | **BUG** |

## Conclusion

**The MCTS code is present and structurally correct in the current branch**, but several changes have been introduced that likely interfere with its operation:

1. **CRITICAL BUG:** `elif use_mcts` causes MCTS to be skipped if proof sketch is enabled
2. **RISK:** MCTS doesn't use verification safeguards (could hang)
3. **RISK:** Best-of-N re-verification adds overhead
4. **CHANGE:** Hybrid strategies at root may dilute UCB1 exploration
5. **CHANGE:** 2× content limit may slow generation

**Recommended Action:** Apply Fix #1 immediately (change `elif` back to `if`) and test. This is the most likely cause of regression.

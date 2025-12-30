# P0 Ablation Testing Guide (BFS-based)

**Last Updated:** 2025-12-28
**Strategy:** Best-First Search (BFS) instead of RLAC

## Overview

This guide explains the updated P0 ablation testing framework that uses **BFS (Best-First Search)** instead of RLAC for faster, more cost-effective testing.

## Key Changes from RLAC-based Ablation

| Aspect | RLAC (Old) | BFS (New) |
|--------|-----------|-----------|
| **Strategy** | Adversarial refinement (15+ rounds) | Best-first exploration (3-15 iterations) |
| **Time per run** | 30-60 min | 15-25 min |
| **Cost per run** | $10-15 | $5-7 |
| **Total cost (N=12)** | ~$150-180 | ~$60-84 |
| **Sample size** | N=10 recommended | N=12 recommended |
| **Metric** | ROBUST verdicts | Success rate |

## Statistical Power Analysis

Based on N=30 verification results (87.78% accuracy, 95% CI: [82.2%, 91.8%], ±4.8pp margin):

### Sample Size Recommendations

| N | Margin of Error | Detectable Difference | Use Case |
|---|-----------------|----------------------|----------|
| **N=3** | ±17pp | 35%+ | Quick smoke test |
| **N=10** | ±9-10pp | 15%+ | Initial screening |
| **N=12** | ±8-9pp | 15%+ | **RECOMMENDED** |
| **N=30** | ±4.8pp | 8%+ | Final validation |

### Is N=30 Enough?

**Short answer:** N=30 is IDEAL but potentially OVERKILL for initial screening.

**For P0 ablation with BFS:**
- ✅ **N=12 is RECOMMENDED** for initial ablation (faster iteration, detect major effects)
- ✅ **N=30 for final validation** after identifying critical features
- ✅ **Statistical power:**
  - N=12: Detects 15%+ differences with 80% power
  - N=30: Detects 8%+ differences with 90% power

**Cost comparison:**
- N=12: ~$360-500 total (5 configs × 12 runs × $6/run)
- N=30: ~$900-1050 total (5 configs × 30 runs × $6/run)

**Time comparison:**
- N=12: ~20 hours sequential, ~4-5 hours parallel (6 workers)
- N=30: ~50 hours sequential, ~10-12 hours parallel (6 workers)

**Recommendation:** Start with N=12 for initial ablation, then use N=30 to validate critical features before implementing context extraction.

## Quick Start

```bash
# Quick validation test (N=3, ~1-2 hours)
./test_p0_ablation_quick.sh problems/imo01.txt

# Recommended initial ablation (N=12, ~4-5 hours parallel)
./test_p0_ablation.sh problems/imo01.txt 12

# Final validation (N=30, ~10-12 hours parallel)
./test_p0_ablation.sh problems/imo01.txt 30
```

## Test Configurations

The ablation test runs the following BFS configurations:

1. **baseline**: All P0 features enabled (reference)
2. **no_format_validation**: Format validation disabled
3. **no_near_success_protection**: Near-success protection disabled
4. **no_answer_lock**: Answer lock disabled
5. **all_disabled**: All P0 features disabled

### BFS Parameters (per run)

- **Solution reasoning:** medium
- **Verification reasoning:** high
- **Self-improvement reasoning:** medium
- **Initial attempts:** 3 (BFS exploration)
- **Max iterations:** 15

## P0 Features and Expected Impact on BFS

### 1. Format Validation (`RLAC_DISABLE_P0_FORMAT_VALIDATION`)

**Expected:** HELPFUL (catches extraction bugs early)

**How it works:**
- Validates extracted solution is at least 100 characters
- Returns error if validation fails
- Prevents sending empty/malformed solutions to verifier

**Expected impact on BFS:**
- 10-20% improvement (MODERATE)
- Catches bugs before verification
- Prevents silent failures

### 2. Near-Success Protection (`RLAC_DISABLE_P0_NEAR_SUCCESS_PROTECTION`)

**Expected:** NEUTRAL (RLAC-specific logic)

**How it works:**
- Enhanced grace failure at 2/3 ROBUST
- History-aware protection
- Designed for adversarial rounds

**Expected impact on BFS:**
- <5% difference (MINIMAL)
- BFS doesn't have "near success" concept
- May affect verification feedback loop minimally

### 3. Answer Lock (`RLAC_DISABLE_P0_ANSWER_LOCK`)

**Expected:** POTENTIALLY HARMFUL (prevents exploration)

**How it works:**
- Locks answer after 2 consecutive ROBUST verdicts
- Prevents fundamental answer changes
- Auto-disabled during P5 reconsideration

**Expected impact on BFS:**
- May REDUCE success by 10-15%
- BFS benefits from exploration flexibility
- Lock may prevent finding better solutions

## Interpreting Results

### Success Rate Thresholds

| Success Rate | Symbol | Interpretation |
|--------------|--------|----------------|
| **≥70%** | ✅ | Configuration works well |
| **40-69%** | ⚠️ | Marginal performance |
| **<40%** | ❌ | Poor performance |

### Feature Impact Classification

Compare each ablation to the baseline:

| Success Rate Difference | Classification | Action |
|-------------------------|----------------|--------|
| **≥20%** | MAJOR impact | Feature is CRITICAL, always enable |
| **10-20%** | MODERATE impact | Feature is BENEFICIAL, recommended |
| **<10%** | MINIMAL impact | Feature is NEUTRAL or RLAC-specific |
| **Negative** (ablation > baseline) | HARMFUL | Feature INTERFERES with BFS, disable |

### Example Analysis

```
Baseline (all P0 features):        8/12 (67%)  ← Reference
no_format_validation:              4/12 (33%)  ← 34pp drop = CRITICAL
no_near_success_protection:        7/12 (58%)  ← 9pp drop = MINIMAL
no_answer_lock:                   10/12 (83%)  ← 16pp gain = HARMFUL!
all_disabled:                      2/12 (17%)  ← 50pp drop = Cumulative effect
```

**Conclusions:**
- **Format validation is CRITICAL** (34pp drop when disabled)
- **Near-success protection is MINIMAL** (9pp drop, RLAC-specific)
- **Answer lock is HARMFUL for BFS** (16pp gain when disabled!)
- **Action:** Disable answer lock for BFS, keep format validation

## Running Ablation Tests

### View Results

```bash
# After ablation completes
cat ablation_results_*/ablation_report.md
```

### Compare Success Rates

```bash
# Quick comparison across all configs
for dir in ablation_results_*/*/; do
  config=$(basename $dir)
  successes=$(grep -l 'Correct solution found' $dir/*.log 2>/dev/null | wc -l)
  total=12  # or extract from logs
  echo "$config: $successes/$total ($(($successes * 100 / $total))%)"
done
```

### Analyze Individual Logs

```bash
# Check iteration counts
for dir in ablation_results_*/*/; do
  echo "=== $(basename $dir) ==="
  grep "Iteration [0-9]" $dir/*.log | tail -5
done

# Check success patterns
grep -h "Correct solution found" ablation_results_*/*/*.log | wc -l
```

## Statistical Significance

For N=12, use Wilson score confidence intervals:

| Success Rate | 95% CI | Interpretation |
|--------------|--------|----------------|
| 8/12 (67%) | [38%, 88%] | ±25pp margin, moderate confidence |
| 4/12 (33%) | [12%, 62%] | ±25pp margin, low confidence |
| 10/12 (83%) | [55%, 96%] | ±20pp margin, high confidence |

**Interpretation:**
- If CIs don't overlap, difference is likely real
- If CIs overlap significantly, may need N=30 to confirm
- For production decisions, use N=30 for narrow CIs (±5-8pp)

## Next Steps After Ablation

### If Format Validation is Critical (≥20% impact)

```bash
# Keep enabled (already default)
# Document the benefit
echo "Format validation improves BFS success by 20%+" >> docs/P0_FEATURES.md
```

### If Answer Lock Hurts BFS (negative impact)

```bash
# Add flag to disable for BFS mode
# In agent_gpt_oss.py:
# if args.num_initial_attempts and not args.use_rlac:
#     disable_answer_lock = True
```

### If Near-Success Protection is Neutral (<10% impact)

```bash
# Document as RLAC-specific
echo "Near-success protection: RLAC-specific, no BFS impact" >> docs/P0_FEATURES.md
# No code changes needed
```

### Context Extraction (After Ablation)

Once you identify critical features:

1. **Run ablation on multiple problems:**
   ```bash
   for problem in problems/imo0{1,2,3,4,5}.txt; do
     ./test_p0_ablation.sh $problem 12
   done
   ```

2. **Analyze problem-type patterns:**
   - Do FIND problems benefit more from format validation?
   - Do PROVE problems need answer lock disabled?
   - Are there problem-specific feature interactions?

3. **Implement context extraction:**
   ```python
   def configure_p0_for_bfs(problem_type):
       """Auto-configure P0 features for BFS based on problem type"""
       config = {
           'format_validation': True,  # Always helpful
           'near_success_protection': False,  # RLAC-specific
           'answer_lock': False,  # Hurts BFS exploration
       }

       # Problem-specific overrides
       if problem_type == "FIND":
           config['format_validation'] = True  # Critical for FIND
       elif problem_type == "PROVE":
           pass  # Use defaults

       return config
   ```

## Cost and Time Estimates

### Single Ablation Run (N=12, 5 configs)

**Parallel execution (recommended):**
- Script runs configs sequentially, but each config runs 12 BFS in parallel
- Time: ~4-5 hours (depends on problem difficulty)
- Cost: 5 configs × 12 runs × $6/run = $360

### Multi-Problem Ablation (5 problems, N=12)

- Time: 5 problems × 4-5 hours = 20-25 hours
- Cost: 5 problems × $360 = $1800

### N=30 Final Validation (single problem, 5 configs)

- Time: ~10-12 hours (parallel BFS within each config)
- Cost: 5 configs × 30 runs × $6/run = $900

## Troubleshooting

### High variance in success rates

**Symptom:** Baseline shows 6/12 one run, 10/12 another run

**Solution:**
- Increase N to 20-30 for stable estimates
- Check for API issues or rate limiting
- Verify BFS temperature is default (0.1)

### All configs show similar success rates

**Symptom:** All configs within 5% of each other

**Solution:**
- Problem may be too easy/hard
- Try different problems (imo02-imo05)
- Adjust BFS parameters (NUM_INITIAL_ATTEMPTS)

### Ablation takes too long

**Symptom:** N=12 taking >8 hours

**Solution:**
- Check if runs hit MAX_RUNS=15 limit (unsuccessful)
- Reduce to N=10 for initial screening
- Use `test_p0_ablation_quick.sh` (N=3) for smoke testing

## Summary

✅ **N=30 is IDEAL** for ablation testing before context extraction
✅ **N=12 is RECOMMENDED** for initial screening (faster, cheaper)
✅ **BFS-based ablation is 2-3× faster** than RLAC-based
✅ **Statistical power:**
  - N=12: Detects 15%+ differences
  - N=30: Detects 8%+ differences

**Next steps:**
1. Run `./test_p0_ablation.sh problems/imo01.txt 12` for initial screening
2. Identify critical features (≥20% impact)
3. If features show problem-type patterns, implement context extraction
4. Validate with N=30 before production deployment

## References

- BFS implementation: `code/meta_prompted_bfs.py`
- Main agent: `code/agent_gpt_oss.py`
- Test script: `test_p0_ablation.sh`
- Quick test: `test_p0_ablation_quick.sh`
- CLAUDE.md: BFS configuration and usage

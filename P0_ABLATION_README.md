# P0 Ablation Testing Framework

## Quick Start

```bash
# Run full ablation test (10 rounds)
./test_p0_ablation.sh problems/imo01.txt 10

# Run quick test (3 rounds for validation)
./test_p0_ablation_quick.sh problems/imo01.txt

# Results will be in: ablation_results_TIMESTAMP/
```

## What is P0 Ablation Testing?

P0 Ablation Testing is a systematic framework for evaluating the impact of individual P0 (Priority 0) features in the RLAC system. By running tests with different feature combinations, we can identify:

1. **Critical features** - Features that are necessary for success
2. **Efficiency features** - Features that improve performance but aren't strictly necessary
3. **Neutral features** - Features with minimal impact (may be problem-specific)

## Key Features

### Temperature = 0 (Deterministic)

All ablation tests run with **temperature=0.0** to ensure deterministic, reproducible results. This allows fair comparison between different configurations.

### P0 Features Tested

1. **Format Validation** - Catches extraction bugs before calling verifier
2. **Near-Success Protection** - Prevents progress loss near success threshold
3. **Answer Lock** - Prevents answer oscillation after achieving stability
4. **Adaptive Temperature** - Increases exploration when stuck (disabled for testing)

## Test Configurations

The ablation script runs these configurations:

1. **baseline** - All P0 features enabled (reference)
2. **no_format_validation** - Format validation disabled
3. **no_near_success_protection** - Near-success protection disabled
4. **no_answer_lock** - Answer lock disabled
5. **all_disabled** - All P0 features disabled (worst case)

## Output

Each test produces:

- **Log file** - Full execution log with all P0 feature activations
- **Memory file** - JSON state for resume capability
- **Summary file** - Key metrics and result status
- **Comparison report** - Markdown report comparing all configurations

## Example Usage

### Basic Test

```bash
# Test Problem 1 with 10 rounds
./test_p0_ablation.sh problems/imo01.txt 10

# View results
cat ablation_results_*/ablation_report.md
```

### Multi-Problem Study

```bash
# Test all problems
for problem in problems/imo*.txt; do
    ./test_p0_ablation.sh "${problem}" 10
    sleep 10
done
```

### Custom Configuration

```bash
# Override specific settings
export RLAC_SOL_REASONING=medium
export RLAC_CRITIC_REASONING=high
./test_p0_ablation.sh problems/imo02.txt 15
```

## Environment Variables

### P0 Feature Toggles

```bash
# Disable individual features (for manual testing)
export RLAC_DISABLE_P0_FORMAT_VALIDATION=true
export RLAC_DISABLE_P0_NEAR_SUCCESS_PROTECTION=true
export RLAC_DISABLE_P0_ANSWER_LOCK=true
export RLAC_DISABLE_ADAPTIVE_TEMPERATURE=true
```

### RLAC Configuration

```bash
# Core settings (used by ablation script)
export RLAC_MAX_ROUNDS=10
export RLAC_ROBUST_THRESHOLD=3
export RLAC_SOL_REASONING=low
export RLAC_CRITIC_REASONING=medium
export RLAC_VERIFY_EVERY_N_ROUNDS=2
export RLAC_VERIFY_START_ROUND=0
```

## Interpreting Results

### Success Patterns

| Baseline | Ablation | Interpretation |
|----------|----------|----------------|
| ✅ | ❌ | Feature is **critical** |
| ✅ | ✅ (slower) | Feature improves **efficiency** |
| ✅ | ✅ (same) | Feature has **minimal impact** |
| ❌ | ❌ | Problem **too hard** |
| ❌ | ✅ | **Unexpected** - investigate |

### Example Analysis

```
Baseline (all features):
  - SUCCESS in round 9 (3/3 ROBUST)
  - Duration: 450s

No near-success protection:
  - FAILED (oscillated at 2/3 ROBUST)
  - Duration: 600s (hit max rounds)

Conclusion: Near-success protection is CRITICAL for this problem.
```

## Debugging

### Check P0 Configuration

```bash
# Verify P0 features in log
grep "P0 ABLATION" ablation_results_*/baseline.log
```

### Track Feature Activations

```bash
# See when protection activates
grep "P0-v2" ablation_results_*/baseline.log

# Compare verdict sequences
for log in ablation_results_*/*.log; do
    echo "=== $(basename ${log}) ==="
    grep "verdict: " "${log}" | tail -10
done
```

## Documentation

- **Detailed guide:** `docs/P0_ABLATION_GUIDE.md`
- **Architecture:** `CLAUDE.md` (P0 Ablation Testing section)
- **Implementation:** `code/agent_gpt_oss.py` (search for "P0 ABLATION")

## Files

- `test_p0_ablation.sh` - Main ablation test script
- `test_p0_ablation_quick.sh` - Quick validation test (3 rounds)
- `docs/P0_ABLATION_GUIDE.md` - Comprehensive documentation
- `code/agent_gpt_oss.py` - Implementation with P0 feature toggles

## Next Steps

1. Run baseline ablation on Problem 1 to validate framework
2. Test on multiple problems to identify patterns
3. Analyze which features are critical vs. efficiency improvements
4. Implement context extraction if specific features consistently help specific problem types
5. Update default configuration based on findings

## Support

For issues or questions:
1. Check `docs/P0_ABLATION_GUIDE.md` for detailed troubleshooting
2. Review logs in `ablation_results_*/` directory
3. Check environment variables are set correctly
4. Verify temperature=0.0 is enforced (adaptive temperature disabled)

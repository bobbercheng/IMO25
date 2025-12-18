# A/B Testing Framework: Prescriptive Feedback Impact

**Purpose:** Measure the impact of prescriptive feedback on agent performance
**Date:** 2025-12-18

---

## Quick Start

### Run A/B Test on Single Problem

```bash
# Control Group (No prescriptive feedback)
DISABLE_PRESCRIPTIVE_FEEDBACK=1 \
python code/agent_gpt_oss.py problems/imo01.txt \
  --num-initial-attempts 3 \
  --solution-reasoning low \
  --verification-reasoning medium \
  --log run_log_gpt_oss/ab_control_p1.log \
  --memory run_log_gpt_oss/ab_control_p1.json

# Treatment Group (With prescriptive feedback)
python code/agent_gpt_oss.py problems/imo01.txt \
  --num-initial-attempts 3 \
  --solution-reasoning low \
  --verification-reasoning medium \
  --log run_log_gpt_oss/ab_treatment_p1.log \
  --memory run_log_gpt_oss/ab_treatment_p1.json
```

### Compare Results

```bash
python analyze_ab_test.py \
  --control run_log_gpt_oss/ab_control_p1.log \
  --treatment run_log_gpt_oss/ab_treatment_p1.log
```

---

## Implementation Options

### Option 1: Environment Variable (Recommended)

Add this check to `agent_gpt_oss.py` in the `verify_solution()` function:

```python
# In verify_solution() before prescriptive feedback integration (line ~1249):

# PRESCRIPTIVE FEEDBACK ENHANCEMENT
# Can be disabled for A/B testing via environment variable
disable_prescriptive = os.environ.get('DISABLE_PRESCRIPTIVE_FEEDBACK', '0') == '1'

if not disable_prescriptive:
    try:
        from prescriptive_feedback import enhance_verification_with_prescriptive_feedback

        bug_report, metadata = enhance_verification_with_prescriptive_feedback(
            problem_statement, solution, bug_report, "yes" in o.lower(), verbose
        )

        if verbose and metadata.get('templates_matched'):
            print(f"\n>>>>>>> [PRESCRIPTIVE FEEDBACK] Matched {len(metadata['templates_matched'])} template(s)")
            for match in metadata['templates_matched']:
                print(f">>>>>>>   - {match['template']} (confidence: {match['confidence']:.0%})")

    except ImportError:
        if verbose:
            print(">>>>>>> [PRESCRIPTIVE FEEDBACK] Module not available, skipping enhancement")
    except Exception as e:
        if verbose:
            print(f">>>>>>> [PRESCRIPTIVE FEEDBACK] Enhancement failed: {e}")
else:
    if verbose:
        print(">>>>>>> [PRESCRIPTIVE FEEDBACK] Disabled for A/B testing")
```

**Usage:**
```bash
# Control (no feedback)
DISABLE_PRESCRIPTIVE_FEEDBACK=1 python code/agent_gpt_oss.py ...

# Treatment (with feedback)
python code/agent_gpt_oss.py ...
```

### Option 2: Command-Line Flag

Add this argument to `agent_gpt_oss.py`:

```python
parser.add_argument(
    '--disable-prescriptive-feedback',
    action='store_true',
    help='Disable prescriptive feedback for A/B testing'
)

# Then use: args.disable_prescriptive_feedback
```

**Usage:**
```bash
# Control
python code/agent_gpt_oss.py problems/imo01.txt --disable-prescriptive-feedback ...

# Treatment
python code/agent_gpt_oss.py problems/imo01.txt ...
```

### Option 3: Separate Script (Simplest)

Create a wrapper script `run_ab_test.sh`:

```bash
#!/bin/bash

PROBLEM=$1
OUTPUT_DIR=${2:-"ab_test_results"}
RUNS_PER_GROUP=${3:-5}

mkdir -p "$OUTPUT_DIR/control" "$OUTPUT_DIR/treatment"

echo "Running A/B Test: $RUNS_PER_GROUP runs per group"
echo "Problem: $PROBLEM"
echo "Output: $OUTPUT_DIR"
echo ""

# Control group (no prescriptive feedback)
echo "=== CONTROL GROUP (No Prescriptive Feedback) ==="
for i in $(seq 1 $RUNS_PER_GROUP); do
    echo "  Run $i/$RUNS_PER_GROUP..."
    DISABLE_PRESCRIPTIVE_FEEDBACK=1 \
    python code/agent_gpt_oss.py "$PROBLEM" \
        --num-initial-attempts 3 \
        --solution-reasoning low \
        --verification-reasoning medium \
        --log "$OUTPUT_DIR/control/run_${i}.log" \
        --memory "$OUTPUT_DIR/control/run_${i}.json" \
        > "$OUTPUT_DIR/control/run_${i}_stdout.txt" 2>&1

    # Extract success/failure
    if grep -q "Found a correct solution" "$OUTPUT_DIR/control/run_${i}.log"; then
        echo "    ✅ SUCCESS"
    else
        echo "    ❌ FAILED"
    fi
done

# Treatment group (with prescriptive feedback)
echo ""
echo "=== TREATMENT GROUP (With Prescriptive Feedback) ==="
for i in $(seq 1 $RUNS_PER_GROUP); do
    echo "  Run $i/$RUNS_PER_GROUP..."
    python code/agent_gpt_oss.py "$PROBLEM" \
        --num-initial-attempts 3 \
        --solution-reasoning low \
        --verification-reasoning medium \
        --log "$OUTPUT_DIR/treatment/run_${i}.log" \
        --memory "$OUTPUT_DIR/treatment/run_${i}.json" \
        > "$OUTPUT_DIR/treatment/run_${i}_stdout.txt" 2>&1

    if grep -q "Found a correct solution" "$OUTPUT_DIR/treatment/run_${i}.log"; then
        echo "    ✅ SUCCESS"
    else
        echo "    ❌ FAILED"
    fi
done

echo ""
echo "=== A/B Test Complete ==="
echo "Run analysis: python analyze_ab_test.py $OUTPUT_DIR"
```

**Usage:**
```bash
chmod +x run_ab_test.sh
./run_ab_test.sh problems/imo01.txt ab_test_p1 10
```

---

## Analysis Script

Create `analyze_ab_test.py`:

```python
#!/usr/bin/env python3
"""
Analyze A/B test results for prescriptive feedback impact.

Usage:
    python analyze_ab_test.py ab_test_results/
    python analyze_ab_test.py --control ab_test_results/control --treatment ab_test_results/treatment
"""

import os
import re
import json
import argparse
from pathlib import Path
from typing import Dict, List, Tuple
import statistics

def extract_metrics_from_log(log_file: Path) -> Dict:
    """Extract key metrics from agent log file."""
    with open(log_file, 'r') as f:
        content = f.read()

    metrics = {
        'success': bool(re.search(r'Found a correct solution', content)),
        'iterations': len(re.findall(r'=== Iteration \d+', content)),
        'prescriptive_warnings': content.count('## Automated Checker Warnings'),
        'prescriptive_fixes': content.count('## Prescriptive Feedback'),
        'critical_errors': content.count('Critical Error'),
        'justification_gaps': content.count('Justification Gap'),
        'log_size_kb': log_file.stat().st_size / 1024,
    }

    # Extract final score if available
    score_match = re.search(r'\[SCORE\] Current score: ([-\d.]+)', content)
    if score_match:
        metrics['final_score'] = float(score_match.group(1))

    # Extract iteration count
    iteration_match = re.findall(r'Iteration (\d+):', content)
    if iteration_match:
        metrics['max_iteration'] = max(int(i) for i in iteration_match)

    return metrics

def analyze_group(group_dir: Path, group_name: str) -> Dict:
    """Analyze all runs in a group."""
    log_files = sorted(group_dir.glob('run_*.log'))

    if not log_files:
        raise ValueError(f"No log files found in {group_dir}")

    all_metrics = [extract_metrics_from_log(f) for f in log_files]

    # Aggregate statistics
    success_rate = sum(m['success'] for m in all_metrics) / len(all_metrics)
    avg_iterations = statistics.mean(m.get('max_iteration', m['iterations']) for m in all_metrics)
    avg_critical_errors = statistics.mean(m['critical_errors'] for m in all_metrics)
    avg_warnings = statistics.mean(m['prescriptive_warnings'] for m in all_metrics)
    avg_fixes = statistics.mean(m['prescriptive_fixes'] for m in all_metrics)

    return {
        'group_name': group_name,
        'n_runs': len(all_metrics),
        'success_rate': success_rate,
        'successes': sum(m['success'] for m in all_metrics),
        'avg_iterations': avg_iterations,
        'avg_critical_errors': avg_critical_errors,
        'avg_prescriptive_warnings': avg_warnings,
        'avg_prescriptive_fixes': avg_fixes,
        'all_metrics': all_metrics
    }

def compare_groups(control: Dict, treatment: Dict) -> Dict:
    """Statistical comparison between control and treatment."""

    # Calculate improvements
    success_lift = ((treatment['success_rate'] - control['success_rate']) /
                    max(control['success_rate'], 0.01)) * 100

    iteration_reduction = ((control['avg_iterations'] - treatment['avg_iterations']) /
                           max(control['avg_iterations'], 1)) * 100

    error_reduction = ((control['avg_critical_errors'] - treatment['avg_critical_errors']) /
                       max(control['avg_critical_errors'], 1)) * 100

    return {
        'success_lift_pct': success_lift,
        'iteration_reduction_pct': iteration_reduction,
        'error_reduction_pct': error_reduction,
        'absolute_success_delta': treatment['success_rate'] - control['success_rate'],
        'absolute_iteration_delta': treatment['avg_iterations'] - control['avg_iterations'],
    }

def print_report(control: Dict, treatment: Dict, comparison: Dict):
    """Print formatted A/B test report."""

    print("\n" + "="*80)
    print("A/B TEST RESULTS: Prescriptive Feedback Impact")
    print("="*80)

    print(f"\n📊 Sample Size:")
    print(f"   Control:   {control['n_runs']} runs")
    print(f"   Treatment: {treatment['n_runs']} runs")

    print(f"\n✅ Success Rate:")
    print(f"   Control:   {control['success_rate']:.1%} ({control['successes']}/{control['n_runs']})")
    print(f"   Treatment: {treatment['success_rate']:.1%} ({treatment['successes']}/{treatment['n_runs']})")
    print(f"   Δ:         {comparison['absolute_success_delta']:+.1%} ({comparison['success_lift_pct']:+.1f}% lift)")

    print(f"\n🔁 Average Iterations:")
    print(f"   Control:   {control['avg_iterations']:.1f}")
    print(f"   Treatment: {treatment['avg_iterations']:.1f}")
    print(f"   Δ:         {comparison['absolute_iteration_delta']:+.1f} ({comparison['iteration_reduction_pct']:+.1f}% reduction)")

    print(f"\n❌ Average Critical Errors:")
    print(f"   Control:   {control['avg_critical_errors']:.1f}")
    print(f"   Treatment: {treatment['avg_critical_errors']:.1f}")
    print(f"   Δ:         {comparison['error_reduction_pct']:+.1f}% reduction")

    print(f"\n🔍 Prescriptive Feedback Usage (Treatment Group):")
    print(f"   Avg Warnings: {treatment['avg_prescriptive_warnings']:.1f} per run")
    print(f"   Avg Fixes:    {treatment['avg_prescriptive_fixes']:.1f} per run")

    print(f"\n" + "="*80)
    print("CONCLUSION:")
    print("="*80)

    if comparison['success_lift_pct'] > 10:
        print(f"✅ Prescriptive feedback shows STRONG POSITIVE impact:")
        print(f"   - {comparison['success_lift_pct']:.1f}% improvement in success rate")
        print(f"   - {abs(comparison['iteration_reduction_pct']):.1f}% reduction in iterations")
    elif comparison['success_lift_pct'] > 0:
        print(f"✅ Prescriptive feedback shows POSITIVE impact:")
        print(f"   - {comparison['success_lift_pct']:.1f}% improvement in success rate")
    else:
        print(f"⚠️  Prescriptive feedback shows NO SIGNIFICANT impact:")
        print(f"   - {comparison['success_lift_pct']:.1f}% change in success rate")
        print(f"   - May need tuning or larger sample size")

    print("\n")

def main():
    parser = argparse.ArgumentParser(description='Analyze A/B test results')
    parser.add_argument('test_dir', nargs='?', help='Directory containing control/ and treatment/ subdirectories')
    parser.add_argument('--control', help='Control group directory')
    parser.add_argument('--treatment', help='Treatment group directory')
    parser.add_argument('--output', help='Save results to JSON file')

    args = parser.parse_args()

    # Determine control and treatment directories
    if args.test_dir:
        control_dir = Path(args.test_dir) / 'control'
        treatment_dir = Path(args.test_dir) / 'treatment'
    else:
        control_dir = Path(args.control)
        treatment_dir = Path(args.treatment)

    # Analyze both groups
    control = analyze_group(control_dir, 'Control (No Prescriptive Feedback)')
    treatment = analyze_group(treatment_dir, 'Treatment (With Prescriptive Feedback)')

    # Compare
    comparison = compare_groups(control, treatment)

    # Print report
    print_report(control, treatment, comparison)

    # Save to JSON if requested
    if args.output:
        results = {
            'control': control,
            'treatment': treatment,
            'comparison': comparison
        }
        # Remove raw metrics to keep JSON clean
        results['control'].pop('all_metrics', None)
        results['treatment'].pop('all_metrics', None)

        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"Results saved to {args.output}")

if __name__ == '__main__':
    main()
```

**Make it executable:**
```bash
chmod +x analyze_ab_test.py
```

---

## Recommended Test Plan

### Phase 1: Single Problem, Small Sample (Quick Validation)

```bash
# Test on IMO Problem 1 with 5 runs per group
./run_ab_test.sh problems/imo01.txt ab_test_p1_pilot 5

# Analyze
python analyze_ab_test.py ab_test_p1_pilot/
```

**Expected runtime:** ~2-3 hours (5 control + 5 treatment runs)

### Phase 2: Single Problem, Larger Sample (Statistical Power)

```bash
# Increase to 20 runs per group for 95% confidence
./run_ab_test.sh problems/imo01.txt ab_test_p1_full 20

# Analyze
python analyze_ab_test.py ab_test_p1_full/ --output ab_results_p1.json
```

**Expected runtime:** ~8-12 hours

### Phase 3: Multiple Problems (Generalization)

```bash
# Run on all 5 IMO problems with 10 runs each
for problem in problems/imo0{1..5}.txt; do
    problem_name=$(basename $problem .txt)
    ./run_ab_test.sh $problem "ab_test_${problem_name}" 10
done

# Aggregate analysis
python aggregate_ab_results.py ab_test_imo0*/
```

**Expected runtime:** 2-3 days

---

## Key Metrics to Track

| Metric | Description | Target |
|--------|-------------|--------|
| **Success Rate** | % of runs that find correct solution | >10% lift |
| **Avg Iterations** | Mean iterations to solution | >15% reduction |
| **Critical Errors** | Avg critical errors per run | >20% reduction |
| **Time to Solution** | Wall clock time | <5% increase (overhead) |
| **Total Cost** | API costs (tokens × price) | <10% increase |

---

## Statistical Significance

For **95% confidence** that results aren't due to chance:

- **Small effect (10% lift):** Need 20+ runs per group
- **Medium effect (25% lift):** Need 10+ runs per group
- **Large effect (50% lift):** Need 5+ runs per group

**Use this formula:**
```
n = (Z^2 * p * (1-p)) / E^2

Where:
- Z = 1.96 (for 95% confidence)
- p = baseline success rate (e.g., 0.3 = 30%)
- E = desired precision (e.g., 0.1 = ±10%)
```

---

## Cost Estimation

Assuming:
- 1 run = 30 iterations avg
- 1 iteration = $0.40 (GPT-OSS API call)
- 1 run = $12 total cost

**Test costs:**
| Test | Runs | Cost |
|------|------|------|
| Pilot (5×2) | 10 | $120 |
| Full (20×2) | 40 | $480 |
| Multi-problem (10×2×5) | 100 | $1,200 |

**Budget accordingly!**

---

## Next Steps

1. **Implement Option 1** (environment variable) - easiest and most flexible
2. **Run Phase 1 pilot test** (5 runs per group, ~$120, 2-3 hours)
3. **Analyze results** with `analyze_ab_test.py`
4. **If positive (>10% lift):** Run Phase 2 for statistical significance
5. **If negative:** Investigate and tune system before larger tests

---

## Questions to Answer

The A/B test will definitively answer:

✅ **Does prescriptive feedback improve success rate?**
✅ **Does it reduce iterations to solution?**
✅ **Does it reduce critical errors?**
✅ **What's the cost/benefit trade-off?**
✅ **Which problem types benefit most?**

**After these tests, you'll have data-driven proof of impact!**

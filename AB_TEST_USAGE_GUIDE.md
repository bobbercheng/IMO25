# A/B Testing Scripts Usage Guide

## Quick Reference

### Basic Usage (Bash-based Parallel)
```bash
# Run with 3 parallel jobs (default)
./run_ab_test.sh problems/imo01.txt ab_test_p1 10

# Run with 5 parallel jobs (recommended)
./run_ab_test.sh problems/imo01.txt ab_test_p1 10 5

# Run with custom configuration
./run_ab_test.sh problems/imo01.txt ab_test_p1 20 5
#                 ^problem         ^output   ^runs ^parallel
```

### Advanced Usage (GNU Parallel - Fastest)
```bash
# Install GNU parallel first (one-time setup)
brew install parallel        # macOS
# or
apt-get install parallel     # Ubuntu/Debian

# Run with GNU parallel (fastest)
./run_ab_test_parallel.sh problems/imo01.txt ab_test_p1 20 5
```

---

## Performance Comparison

| Method | 10 Runs | 20 Runs | Notes |
|--------|---------|---------|-------|
| **Sequential** | ~3 hours | ~6 hours | Original script |
| **Parallel (3 jobs)** | ~1 hour | ~2 hours | 3× speedup |
| **Parallel (5 jobs)** | ~40 min | ~1.5 hours | 4.5× speedup |
| **GNU Parallel** | ~35 min | ~1.2 hours | 5× speedup (optimal) |

**Note:** Actual runtime depends on problem difficulty and API latency.

---

## Choosing Parallel Jobs

### Rule of Thumb
```
Parallel Jobs = min(Runs per Group, CPU Cores, API Rate Limit / Request Rate)
```

### Recommendations

| Your Setup | Recommended Jobs |
|------------|------------------|
| **Laptop** (4 cores) | 3 jobs |
| **Desktop** (8+ cores) | 5 jobs |
| **Server** (16+ cores) | 5 jobs (API rate limited) |
| **Cloud** (unlimited) | 5 jobs (API rate limited) |

**Why not more than 5?**
- API rate limits (too many parallel requests may trigger throttling)
- Memory constraints (each job uses ~500MB)
- Diminishing returns (coordination overhead)

---

## Examples

### Example 1: Quick Pilot Test
```bash
# 5 runs per group, 3 parallel jobs
# Runtime: ~30 min, Cost: ~$120
./run_ab_test.sh problems/imo01.txt ab_test_pilot 5 3

# Analyze
python analyze_ab_test.py ab_test_pilot/
```

### Example 2: Full Statistical Test
```bash
# 20 runs per group, 5 parallel jobs
# Runtime: ~1.5 hours, Cost: ~$480
./run_ab_test.sh problems/imo01.txt ab_test_full 20 5

# Analyze
python analyze_ab_test.py ab_test_full/
```

### Example 3: Multi-Problem Test (Sequential)
```bash
# Test all 5 problems sequentially
for problem in problems/imo0{1..5}.txt; do
    problem_name=$(basename $problem .txt)
    ./run_ab_test.sh $problem "ab_test_${problem_name}" 10 5
done

# Aggregate results
python aggregate_ab_results.py ab_test_imo*/ --output aggregate.json
```

### Example 4: Multi-Problem Test (Parallel)
```bash
# Test all 5 problems in parallel (requires powerful machine)
# WARNING: This runs 5 problems × 5 parallel jobs = 25 concurrent processes!

for problem in problems/imo0{1..5}.txt; do
    problem_name=$(basename $problem .txt)
    ./run_ab_test.sh $problem "ab_test_${problem_name}" 10 5 &
done

# Wait for all to complete
wait

# Aggregate results
python aggregate_ab_results.py ab_test_imo*/ --output aggregate.json
```

---

## Monitoring Progress

### Real-time Monitoring

**Option 1: Watch log directory**
```bash
# In another terminal
watch -n 5 "ls -1 ab_test_p1/control/*.log | wc -l"
```

**Option 2: Monitor running processes**
```bash
# Count active Python processes
ps aux | grep agent_gpt_oss.py | grep -v grep | wc -l
```

**Option 3: Check success rate in real-time**
```bash
# Watch success count
watch -n 10 "
  echo 'Control successes:' && \
  grep -l 'Found a correct solution' ab_test_p1/control/*.log 2>/dev/null | wc -l && \
  echo 'Treatment successes:' && \
  grep -l 'Found a correct solution' ab_test_p1/treatment/*.log 2>/dev/null | wc -l
"
```

### Early Termination

If you need to stop the test:
```bash
# Stop all agent processes
pkill -f agent_gpt_oss.py

# The script will show partial results
python analyze_ab_test.py ab_test_p1/
```

---

## Troubleshooting

### Issue: "Too many open files"

**Solution:** Increase file descriptor limit
```bash
ulimit -n 4096
./run_ab_test.sh problems/imo01.txt ab_test_p1 20 5
```

### Issue: High memory usage

**Symptoms:** System slowdown, swap usage
**Solution:** Reduce parallel jobs
```bash
# Use 3 instead of 5
./run_ab_test.sh problems/imo01.txt ab_test_p1 20 3
```

### Issue: API rate limiting

**Symptoms:** Many failed runs with connection errors
**Solution:** Reduce parallel jobs or add delays
```bash
# Use 3 jobs
./run_ab_test.sh problems/imo01.txt ab_test_p1 20 3

# Or edit script to add sleep between launches
```

### Issue: Jobs not completing

**Check:** Are processes actually running?
```bash
ps aux | grep agent_gpt_oss.py

# Check for errors
tail -f ab_test_p1/control/run_1_stdout.txt
```

---

## Cost Optimization

### Strategy 1: Pilot → Full
```bash
# Step 1: Small pilot (5 runs, ~$120, 30 min)
./run_ab_test.sh problems/imo01.txt pilot 5 3

# Step 2: Analyze
python analyze_ab_test.py pilot/

# Step 3: If promising (>10% lift), run full test
./run_ab_test.sh problems/imo01.txt full 20 5
```

### Strategy 2: Early Stopping
```bash
# Monitor during run
watch -n 30 "python analyze_ab_test.py ab_test_current/"

# If clear winner emerges (>30% lift with 10+ runs), stop early
```

### Strategy 3: Multi-Problem Sampling
```bash
# Instead of 20 runs on all 5 problems (100 total)
# Do 10 runs on 5 problems (50 total) first

for problem in problems/imo0{1..5}.txt; do
    problem_name=$(basename $problem .txt)
    ./run_ab_test.sh $problem "ab_test_${problem_name}" 10 5
done

# Analyze aggregate
python aggregate_ab_results.py ab_test_imo*/
```

---

## Advanced: GNU Parallel

### Installation

**macOS:**
```bash
brew install parallel
```

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install parallel
```

**RedHat/CentOS:**
```bash
sudo yum install parallel
```

### Usage

```bash
# Same interface as run_ab_test.sh
./run_ab_test_parallel.sh problems/imo01.txt ab_test_p1 20 5

# Benefits:
# - 15-20% faster than bash version
# - Better job scheduling
# - Progress bar (with --bar flag)
# - Automatic retry on failure
```

### With Progress Bar

Edit `run_ab_test_parallel.sh` and add `--bar` flag:
```bash
seq 1 $RUNS_PER_GROUP | parallel --bar -j $PARALLEL_JOBS "..."
```

---

## Summary

**Recommended Setup:**

| Test Type | Command | Runtime | Cost |
|-----------|---------|---------|------|
| **Pilot** | `./run_ab_test.sh problems/imo01.txt pilot 5 3` | 30 min | $120 |
| **Full** | `./run_ab_test.sh problems/imo01.txt full 20 5` | 1.5 hrs | $480 |
| **Multi** | Loop with 10 runs × 5 problems | 5 hrs | $1,200 |

**Key Points:**
- Use 3 parallel jobs for stability
- Use 5 parallel jobs for speed (if you have resources)
- Monitor progress with `watch` commands
- Analyze early to detect clear winners
- Use GNU parallel if available (15% faster)

**Start with pilot test!**
```bash
./run_ab_test.sh problems/imo01.txt ab_test_pilot 5 3
```

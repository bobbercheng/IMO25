# GPT-OSS Agent Usage Guide

**agent_gpt_oss.py** - Advanced IMO problem solver with asymmetric reasoning, RLAC, and formula derivation

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [CLI Arguments](#cli-arguments)
3. [Environment Variables](#environment-variables)
4. [Common Usage Patterns](#common-usage-patterns)
5. [Advanced Features](#advanced-features)
6. [Examples](#examples)
7. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Basic Usage

```bash
# Solve a problem with default settings
python code/agent_gpt_oss.py problems/imo01.txt --log output.log

# With custom reasoning levels (asymmetric approach)
python code/agent_gpt_oss.py problems/imo01.txt \
  --solution-reasoning low \
  --verification-reasoning high \
  --log output.log
```

### OpenRouter Setup (Recommended)

```bash
# Configure OpenRouter API (faster for testing)
export GPT_OSS_API_URL=https://openrouter.ai/api/v1/chat/completions
export GPT_OSS_MODEL_NAME=openrouter/openai/gpt-oss-120b
export GPT_OSS_API_KEY=sk-or-your-key-here

# Run agent
python code/agent_gpt_oss.py problems/imo01.txt --log output.log
```

### Formula Derivation (10-100x Faster for Formula Problems)

```bash
# Attempt formula derivation before BFS
python code/agent_gpt_oss.py problems/imo06.txt \
  --use-formula-derivation \
  --formula-reasoning high \
  --log output.log
```

---

## CLI Arguments

### Required Arguments

| Argument | Type | Description |
|----------|------|-------------|
| `problem_file` | str | Path to problem statement file (or use `--benchmark`) |

### Optional Arguments

#### Basic Options

| Argument | Short | Type | Default | Description |
|----------|-------|------|---------|-------------|
| `--log` | `-l` | str | None | Path to log file |
| `--other_prompts` | `-o` | str | None | Comma-separated additional prompts |
| `--max_runs` | `-m` | int | 10 | Maximum number of runs (deprecated, now runs once) |

#### Benchmark Loading

| Argument | Short | Type | Default | Description |
|----------|-------|------|---------|-------------|
| `--benchmark` | `-b` | str | None | Load from benchmark: `gradingbench`, `proofbench`, `answerbench` |
| `--level` | | str | None | Filter by level: Basic/Advanced (grading), pre-IMO/IMO-easy/IMO-medium/IMO-hard (proof) |
| `--benchmark-index` | `-i` | int | 0 | Problem index in filtered benchmark |

#### Memory & Resume

| Argument | Short | Type | Default | Description |
|----------|-------|------|---------|-------------|
| `--memory` | `-mem` | str | None | Path to memory file for state persistence |
| `--resume` | `-r` | bool | False | Resume from memory file |

#### Reasoning Effort Control

| Argument | Short | Type | Default | Description |
|----------|-------|------|---------|-------------|
| `--solution-reasoning` | `-sr` | str | medium | Solution generation effort: `low`/`medium`/`high` |
| `--self-improvement-reasoning` | `-sir` | str | high | Self-improvement effort: `low`/`medium`/`high` |
| `--verification-reasoning` | `-vr` | str | medium | Verification effort: `low`/`medium`/`high` |

**Asymmetric Strategy (Recommended):**
- Solution: `low` (fast generation, prevents truncation)
- Self-Improvement: `high` (proactive error detection)
- Verification: `high` (rigorous checking)

#### BFS Exploration

| Argument | Short | Type | Default | Description |
|----------|-------|------|---------|-------------|
| `--num-initial-attempts` | `-nia` | int | 1 | Generate N diverse solutions, pick best (3-5 for BFS) |
| `--ground-truth-answer` | `-gta` | str | None | Provide answer and ask LLM to prove it |

#### MCTS Exploration (Advanced)

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--use-mcts` | bool | False | Use MCTS-guided exploration instead of BFS |
| `--mcts-simulations` | int | 5 | Number of MCTS simulations |
| `--mcts-exploration` | float | 1.414 | MCTS exploration constant (UCB1) |
| `--best-of-n` | int | 0 | Verify top N MCTS solutions, return first verified |

#### Proof Sketch Architecture

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--use-proof-sketch` | bool | False | Use proof sketch: outline → verify → expand → verify |

#### Translation Layer

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--use-translation` | bool | False | Enable translation layer for asymmetric reasoning |

#### Verification Safeguards

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--verification-timeout` | int | 600 | Timeout for verification in seconds (10 min) |
| `--verification-max-attempts` | int | 3 | Max verification attempts with exponential backoff |
| `--disable-verification-safeguards` | bool | False | Disable timeout and retry safeguards (not recommended) |

#### RLAC (Adversarial Critic)

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--use-rlac` | bool | False | Use RLAC mode (Generator-Critic adversarial loop) |
| `--rlac-max-rounds` | int | 12 | Maximum adversarial rounds |
| `--rlac-robust-threshold` | int | 3 | Consecutive ROBUST verdicts needed for success |
| `--rlac-stuck-threshold` | int | 2 | Consecutive failed fixes before declaring stuck |
| `--rlac-defense-first` | bool | True | Enable defense-first mode (generator anticipates attacks) |
| `--no-rlac-defense-first` | bool | False | Disable defense-first mode |
| `--rlac-max-regeneration` | int | 2 | Max regeneration attempts for invalid initial solution |
| `--rlac-constructive-mode` | bool | True | Use constructive critic after repeated failures |
| `--no-rlac-constructive-mode` | bool | False | Disable constructive mode |
| `--rlac-critic-reasoning` | str | medium | Critic reasoning effort: `low`/`medium`/`high` |

**RLAC Reasoning Strategy:**
- Solution: `low` (fast generation)
- Critic: `medium` (balanced attack rigor)
- Rounds 0-2: LOW critic reasoning (efficiency)
- Rounds 3-6: MEDIUM critic reasoning (progressive intensity)

#### Schema Blacklist (Diversity Enhancement)

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--use-schema-blacklist` | bool | False | Use JSON schema for blacklist constraints (100% compliance) |

#### Formula Derivation (Small-Case Validation)

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--use-formula-derivation` | bool | False | Attempt formula derivation before BFS (10-100x speedup) |
| `--formula-min-confidence` | float | 0.8 | Minimum confidence to accept derived formula |
| `--formula-reasoning` | str | adaptive | Formula derivation effort: `low`/`medium`/`high`/`adaptive` |

**Formula Derivation Strategy:**
- `adaptive`: Try low → medium → high (3-5x cost savings)
- `high`: Use high reasoning immediately (recommended with `--formula-reasoning high`)
- Falls back to BFS if derivation fails or confidence < threshold

---

## Environment Variables

### API Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `GPT_OSS_API_URL` | `http://localhost:30000/v1/chat/completions` | API endpoint URL |
| `GPT_OSS_API_KEY` | (none) | API key (optional for local, required for OpenRouter) |
| `OPENROUTER_API_KEY` | (none) | Fallback if `GPT_OSS_API_KEY` not set |
| `GPT_OSS_MODEL_NAME` | `openai/gpt-oss-120b` | Model name |

**Model Name Prefixes:**
- Standard: `openai/gpt-oss-120b` or `gpt-oss-120b`
- OpenRouter: `openrouter/openai/gpt-oss-120b` (auto-detects API spec)

### Reasoning Effort Defaults

| Variable | Default | Description |
|----------|---------|-------------|
| `GPT_OSS_SOLUTION_REASONING` | `medium` | Default solution reasoning effort |
| `GPT_OSS_SELF_IMPROVEMENT_REASONING` | `high` | Default self-improvement reasoning effort |
| `GPT_OSS_VERIFICATION_REASONING` | `medium` | Default verification reasoning effort |
| `GPT_OSS_REASONING_EFFORT` | (solution default) | Global reasoning override |

**Priority:** CLI args > Specific env vars > Global env var > Hardcoded defaults

### Structured Output

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_STRUCTURED_OUTPUT` | `1` | Enable structured JSON output (`1`=enabled, `0`=disabled) |

### TIER 2 Refinement

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_TIER2_REFINEMENT` | `true` | Enable TIER 2 refinement loop |
| `TIER2_MAX_ROUNDS` | `5` | Maximum TIER 2 rounds |
| `TIER2_REFINEMENT_REASONING` | `high` | TIER 2 refinement reasoning effort |
| `TIER2_VERIFICATION_REASONING` | `medium` | TIER 2 verification reasoning effort |
| `TIER2_USE_GRADUATED_VERIFICATION` | `false` | Use graduated verification (disabled per expert analysis) |
| `TIER2_AUTO_DETECT_STRATEGY` | `true` | Auto-detect proof type |

### LLM Verification

| Variable | Default | Description |
|----------|---------|-------------|
| `USE_LLM_VERIFICATION` | `true` | Use LLM-based verification |
| `LLM_VERIFY_TEST_CASES` | `3,4,5,10` | Test case sizes for verification |

### Translation Layer

| Variable | Default | Description |
|----------|---------|-------------|
| `GPT_OSS_USE_TRANSLATION` | `false` | Enable translation layer (set by `--use-translation`) |

### Answer Validation (Debugging Only)

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_ANSWER_VALIDATION` | `0` | Enable answer validation for measurement (`0`=disabled, `1`=enabled) |

**WARNING:** Enable only for testing with known answers. Causes ground truth leakage!

### RLAC Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `RLAC_VERIFY_EVERY_N_ROUNDS` | `4` | Run verification every N rounds during RLAC |
| `RLAC_VERIFY_START_ROUND` | `3` | Start verification from round N |
| `RLAC_DISABLE_INLINE_VERIFICATION` | `false` | Disable in-RLAC verification |
| `RLAC_ACCEPT_SUSPICIOUS_THRESHOLD` | `3` | Accept solution after N consecutive SUSPICIOUS verdicts |
| `RLAC_SUSPICIOUS_LOOKBACK` | `4` | Lookback window for SUSPICIOUS verdict counting |
| `RLAC_ANSWER_STABILITY_WINDOW` | `3` | Window for answer stability detection |

### RLAC P0 Features (Ablation Testing)

| Variable | Default | Description |
|----------|---------|-------------|
| `RLAC_DISABLE_P0_FORMAT_VALIDATION` | `false` | Disable format validation |
| `RLAC_DISABLE_P0_NEAR_SUCCESS_PROTECTION` | `false` | Disable near-success protection |
| `RLAC_DISABLE_P0_ANSWER_LOCK` | `false` | Disable answer lock mechanism |
| `RLAC_DISABLE_ADAPTIVE_TEMPERATURE` | `false` | Disable adaptive temperature |

**Usage:** For P0 ablation testing to identify critical vs. efficiency features.

### Prescriptive Feedback

| Variable | Default | Description |
|----------|---------|-------------|
| `DISABLE_PRESCRIPTIVE_FEEDBACK` | `0` | Disable prescriptive feedback (`0`=enabled, `1`=disabled) |

### BFS Run Identification

| Variable | Default | Description |
|----------|---------|-------------|
| `BFS_RUN_ID` | (none) | 0-indexed run identifier for parallel BFS runs |

---

## Common Usage Patterns

### 1. Basic Problem Solving (Asymmetric Reasoning)

**Fastest, most cost-effective approach:**

```bash
python code/agent_gpt_oss.py problems/imo01.txt \
  --solution-reasoning low \
  --self-improvement-reasoning high \
  --verification-reasoning high \
  --log output.log
```

**Why:**
- Low reasoning for solution: 17x faster, prevents truncation
- High reasoning for verification: Catches subtle errors
- High reasoning for self-improvement: Proactive error detection

**Cost:** ~$12 per problem | **Time:** ~45-90 min

### 2. Formula-Based Problems (10-100x Speedup)

**For problems with mathematical formulas:**

```bash
python code/agent_gpt_oss.py problems/imo06.txt \
  --use-formula-derivation \
  --formula-reasoning high \
  --log output.log
```

**Expected:**
- Time: 2-10 min (vs 45-90 min for BFS)
- Cost: $0.001-$3 (vs $12-75 for BFS)
- Success: 75-85% (vs 30-40% for BFS)

**Adaptive reasoning (cost-optimized):**

```bash
python code/agent_gpt_oss.py problems/imo06.txt \
  --use-formula-derivation \
  --formula-reasoning adaptive \
  --log output.log
```

Tries low → medium → high, saves 3-5x cost.

### 3. BFS Exploration (Escape Local Minima)

**Generate multiple diverse solutions:**

```bash
python code/agent_gpt_oss.py problems/imo01.txt \
  --num-initial-attempts 5 \
  --solution-reasoning low \
  --verification-reasoning high \
  --log output.log
```

**Why:**
- Generates 5 diverse initial solutions
- Picks best based on verification
- Helps escape local minima

**Cost:** ~$15-20 per problem | **Success:** +10-15% improvement

### 4. RLAC Mode (Adversarial Refinement)

**Generator-Critic adversarial loop:**

```bash
python code/agent_gpt_oss.py problems/imo01.txt \
  --use-rlac \
  --rlac-max-rounds 15 \
  --rlac-robust-threshold 3 \
  --solution-reasoning low \
  --rlac-critic-reasoning medium \
  --log output.log
```

**Features:**
- Generator creates solution
- Critic attacks solution
- Generator defends or revises
- Repeats until robust or stuck

**Cost:** ~$20-50 per problem | **Success:** +15-25% improvement

### 5. Ground Truth Answer Mode

**When answer is known but proof is hard:**

```bash
python code/agent_gpt_oss.py problems/imo01.txt \
  --ground-truth-answer 2112 \
  --verification-reasoning high \
  --log output.log
```

**Use case:**
- Answer known (e.g., 2112)
- Need rigorous proof
- LLM focuses on constructing valid proof

### 6. Benchmark Loading

**Load from pre-configured benchmarks:**

```bash
# Load from gradingbench, Advanced level, problem 0
python code/agent_gpt_oss.py \
  --benchmark gradingbench \
  --level Advanced \
  --benchmark-index 0 \
  --log output.log

# Load from proofbench, IMO-hard level, problem 5
python code/agent_gpt_oss.py \
  --benchmark proofbench \
  --level IMO-hard \
  --benchmark-index 5 \
  --log output.log
```

### 7. Memory & Resume

**Save state and resume later:**

```bash
# Initial run with memory
python code/agent_gpt_oss.py problems/imo01.txt \
  --memory state.json \
  --log output.log

# Resume from state
python code/agent_gpt_oss.py problems/imo01.txt \
  --memory state.json \
  --resume \
  --log output_resumed.log
```

**Use case:**
- Long-running problems (hours)
- Checkpoint progress
- Resume after interruption

### 8. OpenRouter Configuration

**Faster inference for medium/high reasoning:**

```bash
# Set environment variables
export GPT_OSS_API_URL=https://openrouter.ai/api/v1/chat/completions
export GPT_OSS_MODEL_NAME=openrouter/openai/gpt-oss-120b
export GPT_OSS_API_KEY=sk-or-your-key-here

# Run with medium reasoning
python code/agent_gpt_oss.py problems/imo01.txt \
  --solution-reasoning medium \
  --verification-reasoning high \
  --log output.log
```

**Benefits:**
- Faster inference for medium/high reasoning
- No local deployment needed
- Automatic failover and load balancing

---

## Advanced Features

### 1. Proof Sketch Architecture

**Structured proof development:**

```bash
python code/agent_gpt_oss.py problems/imo01.txt \
  --use-proof-sketch \
  --log output.log
```

**Workflow:**
1. Create proof outline
2. Verify structure
3. Expand details
4. Verify mathematics

**Use case:** Complex proofs requiring careful structure

### 2. MCTS Exploration

**Tree-based exploration:**

```bash
python code/agent_gpt_oss.py problems/imo01.txt \
  --use-mcts \
  --mcts-simulations 5 \
  --mcts-exploration 1.414 \
  --best-of-n 3 \
  --log output.log
```

**How it works:**
- MCTS simulations: 5 (baseline proven config)
- Exploration constant: 1.414 (sqrt(2), UCB1 default)
- Best-of-N: Verify top 3 solutions, return first verified

**Cost:** ~$25-40 per problem | **Success:** +20-30% improvement

### 3. Schema Blacklist (Diversity)

**Prevent solution repetition:**

```bash
python code/agent_gpt_oss.py problems/imo01.txt \
  --num-initial-attempts 5 \
  --use-schema-blacklist \
  --log output.log
```

**Features:**
- JSON schema enforces blacklist constraints
- 100% compliance via constrained decoding
- 0% waste (no rejected generations)

**Use case:** BFS runs where diversity is critical

### 4. Translation Layer

**Asymmetric reasoning with translation:**

```bash
python code/agent_gpt_oss.py problems/imo01.txt \
  --use-translation \
  --solution-reasoning low \
  --verification-reasoning high \
  --log output.log
```

**How it works:**
- Generate with low reasoning (fast)
- Translate to high reasoning format (quality)
- Verify with high reasoning (rigorous)

**Experimental feature - use with caution**

### 5. P0 Ablation Testing

**Test individual RLAC P0 features:**

```bash
# Disable format validation
RLAC_DISABLE_P0_FORMAT_VALIDATION=true \
python code/agent_gpt_oss.py problems/imo01.txt \
  --use-rlac \
  --log output.log

# Disable near-success protection
RLAC_DISABLE_P0_NEAR_SUCCESS_PROTECTION=true \
python code/agent_gpt_oss.py problems/imo01.txt \
  --use-rlac \
  --log output.log
```

**Use case:** Identify which P0 features are critical vs. efficiency improvements

---

## Examples

### Example 1: Quick Solve with Defaults

```bash
python code/agent_gpt_oss.py problems/imo01.txt --log quick.log
```

**Uses:**
- Solution reasoning: medium
- Self-improvement reasoning: high
- Verification reasoning: medium

### Example 2: Asymmetric Low/High

```bash
python code/agent_gpt_oss.py problems/imo01.txt \
  --solution-reasoning low \
  --verification-reasoning high \
  --log asymmetric.log
```

**Best for:** Cost-efficient solving with rigorous verification

### Example 3: Formula Derivation + BFS Fallback

```bash
python code/agent_gpt_oss.py problems/imo06.txt \
  --use-formula-derivation \
  --formula-reasoning adaptive \
  --num-initial-attempts 5 \
  --log hybrid.log
```

**Strategy:**
1. Try formula derivation (adaptive reasoning)
2. If successful (confidence ≥ 0.8): Use formula answer
3. If failed: Fall back to BFS with 5 diverse attempts

### Example 4: RLAC with In-Round Verification

```bash
python code/agent_gpt_oss.py problems/imo01.txt \
  --use-rlac \
  --rlac-max-rounds 15 \
  --solution-reasoning low \
  --rlac-critic-reasoning medium \
  --log rlac_verified.log
```

**Environment:**
```bash
export RLAC_VERIFY_EVERY_N_ROUNDS=2
export RLAC_VERIFY_START_ROUND=0
```

**Features:**
- Runs cooperative verification every 2 rounds
- Catches critical errors early (e.g., wrong constructions)

### Example 5: Full Power (All Features)

```bash
python code/agent_gpt_oss.py problems/imo06.txt \
  --use-formula-derivation \
  --formula-reasoning adaptive \
  --num-initial-attempts 5 \
  --use-rlac \
  --rlac-max-rounds 15 \
  --solution-reasoning low \
  --verification-reasoning high \
  --rlac-critic-reasoning medium \
  --use-schema-blacklist \
  --log full_power.log
```

**Strategy:**
1. Try formula derivation (adaptive)
2. If failed: BFS with 5 diverse attempts + blacklist
3. For each attempt: RLAC refinement (15 rounds max)
4. Verification: High reasoning rigor

**Cost:** ~$50-100 per problem | **Success:** Maximum (80-90%)

### Example 6: Debug Mode (Answer Validation)

```bash
ENABLE_ANSWER_VALIDATION=1 \
python code/agent_gpt_oss.py problems/imo01.txt \
  --num-initial-attempts 5 \
  --log debug.log
```

**WARNING:** Only use with known answers for testing!

---

## Troubleshooting

### Issue 1: Formula Derivation Fails

**Symptom:**
```
[FORMULA DERIVATION] ✗ Failed to derive formula. Falling back to BFS...
```

**Solutions:**
1. **Increase reasoning:** Use `--formula-reasoning high`
2. **Check confidence:** Lower `--formula-min-confidence` to 0.6
3. **Verify problem type:** Formula derivation only works for formula-based problems

### Issue 2: Verification Timeout

**Symptom:**
```
[WARNING] Verification timed out after 600 seconds
```

**Solutions:**
1. **Increase timeout:** `--verification-timeout 1200` (20 min)
2. **Reduce reasoning:** `--verification-reasoning medium` instead of high
3. **Check network:** Ensure stable API connection

### Issue 3: RLAC Gets Stuck

**Symptom:**
```
[RLAC] STUCK after 12 rounds, no progress
```

**Solutions:**
1. **Increase rounds:** `--rlac-max-rounds 20`
2. **Enable constructive mode:** (enabled by default)
3. **Try defense-first:** `--rlac-defense-first` (default)
4. **Adjust critic reasoning:** `--rlac-critic-reasoning low` (faster iterations)

### Issue 4: High Cost

**Symptom:**
```
Total cost: $150 for single problem
```

**Solutions:**
1. **Use asymmetric reasoning:** `--solution-reasoning low`
2. **Disable RLAC:** Remove `--use-rlac` flag
3. **Use formula derivation:** `--use-formula-derivation` for formula problems
4. **Reduce BFS attempts:** `--num-initial-attempts 3` (from 5)

### Issue 5: JSON Schema Conflict

**Symptom:**
```
[SMALL_CASE_VALIDATOR] Not all cases matched
```

**Fixed in v2.3!** Schema conflict detection now prevents this issue.

**If still occurs:**
1. Update to latest version
2. Set `ENABLE_STRUCTURED_OUTPUT=0` to disable conflicting suffix

### Issue 6: API Connection Failed

**Symptom:**
```
Error during API request: Connection refused
```

**Solutions:**
1. **Check API URL:** Verify `GPT_OSS_API_URL` is correct
2. **Check API key:** Ensure `GPT_OSS_API_KEY` is set (for OpenRouter)
3. **Test connection:** `curl $GPT_OSS_API_URL/models`
4. **Local deployment:** Ensure server is running on specified port

---

## Performance Comparison

| Approach | Time | Cost | Success Rate | Use Case |
|----------|------|------|--------------|----------|
| **Default (medium/high/medium)** | 45-90 min | $12-75 | 30-40% | General problems |
| **Asymmetric (low/high/high)** | 45-90 min | $12-30 | 40-60% | Cost-efficient |
| **Formula Derivation** | 2-10 min | $0.001-$3 | 75-85% | Formula problems |
| **BFS (N=5)** | 50-100 min | $15-40 | 40-55% | Local minima escape |
| **RLAC** | 60-120 min | $20-50 | 45-65% | Adversarial refinement |
| **MCTS** | 70-130 min | $25-60 | 50-70% | Tree exploration |
| **Full Power** | 80-150 min | $50-100 | 80-90% | Maximum success |

---

## Related Documentation

- **CLAUDE.md** - Architecture overview and common commands
- **BFS_INTEGRATION_IMPLEMENTATION.md** - Formula derivation integration guide
- **docs/P0_ABLATION_GUIDE.md** - P0 feature ablation testing
- **docs/RLAC_COMPREHENSIVE_ANALYSIS.md** - RLAC analysis and tuning

---

## Version History

- **v2.3 (2026-01-06)** - Fixed JSON schema conflict in formula derivation
- **v2.2 (2025-12-28)** - Added P0 ablation testing framework
- **v2.1 (2025-12-21)** - Simplified restart loop, integrated RLAC
- **v2.0 (2025-12-07)** - Added in-RLAC verification
- **v1.9 (2025-11-25)** - Fixed counterexample truncation
- **v1.0** - Initial release with asymmetric reasoning

---

**Last Updated:** 2026-01-06
**Maintainer:** IMO25 Team

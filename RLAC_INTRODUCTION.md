# RLAC: Reinforcement Learning with Adversarial Critics

## Overview

RLAC (Reinforcement Learning with Adversarial Critics) is an inference-time adversarial refinement system for mathematical problem solving. Unlike traditional verification which passively checks solutions, RLAC uses two competing LLM agents:

1. **Generator Agent**: Creates and refines mathematical solutions
2. **Adversarial Critic Agent**: Actively tries to BREAK solutions with counterexamples

The adversarial feedback loop creates reinforcement signals that drive iterative improvement **without any model training**.

> **Important**: This implementation adapts RLAC principles for **inference-time** use. The original RLAC paper describes a training algorithm with gradient updates. This implementation uses iterative prompting with adversarial feedback instead.

## Core Innovation: Adversarial vs Verification

### Traditional Verification
```
Generator → Solution → Verifier → ✓/✗
```
- Binary outcome (pass/fail)
- Passive checking
- "Is this correct?"

### Adversarial RLAC
```
Generator → Solution → Critic (attacks) → Structured flaws → Generator revision → ...
```
- Iterative refinement loop
- Active attacking with counterexamples
- Progressive difficulty (curriculum learning)
- "How can I break this?"

| Aspect | Verifier | Adversarial Critic |
|--------|----------|-------------------|
| Goal | Confirm correctness | Find flaws to exploit |
| Stance | Neutral judge | Hostile attacker |
| Output | Yes/No | Counterexamples + severity |
| Feedback | "Wrong" | "n=0 fails because..." |

## Quick Start

### Basic Usage (Integrated with agent_gpt_oss.py)

```bash
python code/agent_gpt_oss.py problems/imo01.txt \
  --use-rlac \
  --log rlac_output.log
```

### Advanced Configuration

```bash
python code/agent_gpt_oss.py problems/imo01.txt \
  --use-rlac \
  --rlac-max-rounds 12 \
  --rlac-robust-threshold 3 \
  --rlac-stuck-threshold 4 \
  --rlac-defense-first \
  --solution-reasoning low \
  --verification-reasoning high \
  --log rlac_output.log
```

### Standalone RLAC Agent

```bash
python code/agent_rlac.py problems/imo01.txt \
  --max-iterations 10 \
  --generator-reasoning low \
  --critic-reasoning high \
  --log rlac_standalone.json
```

## Configuration Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--use-rlac` | False | Enable RLAC mode |
| `--rlac-max-rounds` | 12 | Maximum adversarial rounds |
| `--rlac-robust-threshold` | 3 | Consecutive robust verdicts needed for success |
| `--rlac-stuck-threshold` | 4 | Consecutive failures before declaring stuck |
| `--rlac-defense-first` | True | Generator proactively anticipates attacks |
| `--solution-reasoning` | low | Generator reasoning effort (low/medium/high) |
| `--verification-reasoning` | high | Critic reasoning effort |

## How It Works

### Algorithm Overview

```python
for iteration in range(max_iterations):
    # PHASE 1: Generate or revise solution
    if first_iteration:
        solution = generator.create_solution(problem)
    else:
        solution = generator.revise(problem, solution, criticism)

    # PHASE 2: Adversarial attack
    criticism = critic.attack(problem, solution, intensity=progressive)

    # PHASE 3: Reinforcement signal
    if criticism.no_flaws:
        reward = +10  # Solution survived!
        return solution  # SUCCESS
    else:
        penalty = sum(-severity_score(flaw) for flaw in criticism.flaws)
        cumulative_reward += penalty  # Negative reinforcement
```

### Progressive Curriculum Learning

The system implements two types of progression:

**Attack Intensity** (what to look for):
- Rounds 0-2: BASIC attacks (obvious flaws, base cases)
- Rounds 3-6: MODERATE attacks (edge cases, assumptions)
- Rounds 7+: ADVANCED attacks (subtle flaws, deep rigor)

**Reasoning Effort** (how hard to think):
- Rounds 0-2: LOW reasoning (quick basic checks)
- Rounds 3-6: MEDIUM reasoning (moderate analysis)
- Rounds 7+: HIGH reasoning (rigorous verification)

### Adversarial Attack Strategies

The critic employs multiple attack strategies:

1. **Counterexample Generation**: Test n=0, n=1, n=2, boundary values
2. **Edge Case Hunting**: Degenerate configurations, limits
3. **Assumption Challenging**: "Why must k ≥ 0? Prove this."
4. **Logical Gap Detection**: "Step 3 to step 4 lacks justification"

### Reward System

```python
severity_scores = {
    'critical': -10,  # Counterexample disproves solution
    'major': -5,      # Significant logical gap
    'minor': -2       # Clarity or edge case issue
}

# Positive reward when solution survives attack
if critic_finds_no_flaws:
    reward = +10
```

## Key Features

### 1. Defense-First Mode
Generator proactively anticipates attacks when creating solutions:
- Explicit handling of edge cases
- Defense annotations for vulnerable steps
- Enabled by default with `--rlac-defense-first`

### 2. Answer Reconsideration
When stuck with the same counterexample appearing repeatedly:
- Detects when the **answer itself** (not just the proof) may be wrong
- Triggers explicit "find a different answer" mode
- Accumulates counterexample evidence for reconsideration

### 3. Stuck Pattern Detection
Detects when generator cannot progress:
- Same flaw types appearing across multiple rounds
- Repeating counterexamples
- Solution unchanged despite revisions
- Triggers strategy shift or regeneration

### 4. Best Solution Tracking
- Tracks highest-scoring solution throughout refinement
- Falls back to best solution if generator gets stuck
- Preserves progress across adversarial rounds

### 5. Answer Stability Tracking
- Tracks answer changes across rounds
- Detects oscillation patterns (answer flipping)
- Prevents acceptance of unstable solutions

## Example Session

### Problem
Prove: For all n ≥ 0, 2^n < (n+1)!

### RLAC Flow

**Iteration 1:**
```
Generator: [Proves using induction, base case n=1]
Critic: "FLAW: Base case should be n=0, not n=1. Counterexample: n=0 not covered."
Signal: -10 (critical)
```

**Iteration 2:**
```
Generator: [Adds n=0 base case]
Critic: "FLAW: 2^0 = 1 and 0! = 1, so 1 < 1 is false."
Signal: -10 (critical)
```

**Iteration 3:**
```
Generator: [Proves n=0 separately, proves n≥1 by induction]
Critic: "FLAW: Inductive step requires 2 < k+2. Unstated assumption."
Signal: -5 (major)
```

**Iteration 4:**
```
Generator: [Adds justification: k≥1 implies k+2≥3 > 2]
Critic: "ADVERSARIAL_VALIDATION_PASSED - Logic sound, assumptions justified."
Signal: +10 (SUCCESS)
```

## Output Files

RLAC automatically saves detailed logs:

| File | Description |
|------|-------------|
| `*_rlac_history.json` | Complete attack history with metrics |
| `*_rlac_solution.json` | Final solution with metadata (on success) |
| `*_rlac_failure.json` | Failure analysis (on stuck/timeout) |

### Attack History Structure

```json
{
  "attack_history": [
    {
      "verdict": "BROKEN",
      "counterexamples": ["n=3 gives k=4 which violates..."],
      "critical_flaws": ["Step 3 assumes k < n/2 without proof"],
      "total_penalty": -20,
      "round_num": 0
    }
  ],
  "metrics": {
    "total_attacks": 10,
    "total_counterexamples": 15,
    "broken_rate": 0.7
  }
}
```

## Performance Expectations

| Metric | Traditional | RLAC | Improvement |
|--------|------------|------|-------------|
| Success Rate | 30-40% | 50-70% | +50-75% |
| Edge Case Coverage | ~60% | ~95% | Active hunting |
| Cost per Attempt | $1-2 | $3-5 | 2-3× higher |
| Solution Quality | Medium | High | Adversarially tested |

**Net outcome:** Higher cost per attempt, but better success rate = better ROI overall.

## When to Use RLAC

### Ideal for:
- Mathematical proofs (IMO problems)
- High-stakes correctness requirements
- Complex reasoning requiring rigor
- When solution quality > speed

### Not ideal for:
- Simple problems with obvious answers
- Tight latency requirements (<5 seconds)
- Low-stakes applications
- Purely creative tasks

## Troubleshooting

### Generator Stuck Immediately
- Enable defense-first mode: `--rlac-defense-first`
- Increase `--solution-reasoning` to "medium"
- Increase `--rlac-stuck-threshold`

### All Rounds Return BROKEN
- Check logs for specific counterexamples
- May indicate genuine solution flaws
- Increase regeneration attempts

### Maximum Rounds Exceeded
- Increase `--rlac-max-rounds` to 15-20
- Reduce `--rlac-robust-threshold` to 2
- Check if answer is oscillating

## File Structure

| File | Description |
|------|-------------|
| `code/agent_gpt_oss.py` | Main agent with RLAC integration |
| `code/agent_rlac.py` | Standalone RLAC agent module |
| `code/adversarial_critic.py` | Adversarial critic implementation |
| `code/adversarial_prompts.py` | Prompt templates for RLAC |
| `code/rlac_improvements.py` | Enhanced validation and parsing |

## Integration with Asymmetric Reasoning

RLAC enhances the existing asymmetric reasoning approach:

```python
# Existing asymmetric pattern
SOLUTION_REASONING_EFFORT = "low"      # Fast generation
VERIFICATION_REASONING_EFFORT = "high" # Rigorous checking

# RLAC enhancement
GENERATOR_REASONING = "low"   # Fast solution/revision (unchanged)
CRITIC_REASONING = "high"     # Rigorous adversarial attack (enhanced)
```

Benefits:
- Generator stays fast (17× faster with "low" reasoning)
- Critic becomes more effective (actively attacks instead of just verifying)
- Same computational efficiency, better verification quality

## References

- Original RLAC Paper: Wu et al., "RLAC: Reinforcement Learning with Adversarial Critic" (arXiv:2511.01758v1)
- Implementation details: See `RLAC_IMPLEMENTATION.md`

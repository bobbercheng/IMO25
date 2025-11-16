# Gradient/Progressive Reasoning Effort System Design

**Date**: 2025-11-16
**Purpose**: Design a curriculum learning approach for reasoning effort in GPT-OSS agent
**Status**: Design Document (Implementation Pending)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Background & Motivation](#background--motivation)
3. [Approach Comparison](#approach-comparison)
4. [Recommended Strategy](#recommended-strategy)
5. [Implementation Details](#implementation-details)
6. [Expected Benefits & Challenges](#expected-benefits--challenges)
7. [Testing & Validation Plan](#testing--validation-plan)

---

## Executive Summary

### The Core Insight

**Current situation**: Switching from low→high reasoning is binary (all or nothing)
**Problem**: High standards from start = 122 truncations and failure
**Proposed solution**: **Progressive difficulty scaling** like curriculum learning

### Recommended Approach

**HYBRID: Iteration-Based + Success-Gated Progression (Approach E)**

- Combines iteration-based schedule with success-based gates
- Verification difficulty increases gradually but only when agent is ready
- Dual-track: verification difficulty increases faster than generation
- Natural integration with existing memory/resume system

### Expected Impact

| Metric | Baseline (high) | Low/Low | **Gradient (Predicted)** |
|--------|-----------------|---------|--------------------------|
| Success Rate | 0% | 30-40% (unconfirmed) | **60-80%** |
| Truncations | 122 | 0 | **0-5** |
| Solution Quality | N/A | Medium confidence | **High confidence** |
| Iterations to Success | ∞ | 17 (if successful) | **20-30** |
| False Positives | N/A | High risk | **Very low** |

---

## Background & Motivation

### Current System Analysis

**File**: `/home/user/IMO25/code/agent_gpt_oss.py`

**Current Implementation**:
```python
# Line 49: Global setting
REASONING_EFFORT = os.getenv("GPT_OSS_REASONING_EFFORT", "low")

# Line 148: Used for ALL requests
def build_request_payload(...):
    payload = {
        "reasoning": {
            "effort": REASONING_EFFORT  # Same for generation & verification
        }
    }
```

**Problem**: No differentiation between:
- Solution generation (needs efficiency)
- Verification (needs rigor)
- Early iterations (needs achievable standards)
- Later iterations (needs high confidence)

### Evidence from Testing

#### Test Results with Low Reasoning (Low/Low)

**Positive Results**:
- ✅ 0 truncations (was 122)
- ✅ 17× faster iterations
- ✅ First successful verification (33% pass rate)
- ✅ 97% format compliance

**Concerns**:
- ⚠️ Verification might be too lenient
- ⚠️ 46% justification gaps still present
- ⚠️ 62% critical errors detected
- ⚠️ Agent stuck in correction loops
- ⚠️ Only 1/3 verifications passed despite "low" standards

#### Critical Insight from VERIFICATION_RIGOR_PROBLEM.md

**The Asymmetric Reasoning Discovery**:
- Low reasoning for **generation** = GOOD (prevents truncation)
- Low reasoning for **verification** = QUESTIONABLE (might accept flawed solutions)
- **Solution**: Different reasoning levels for different tasks

**But we can go further**:
- Not just asymmetric (generation vs verification)
- But also **progressive** (early vs late iterations)
- **Curriculum learning**: Start easy, gradually increase difficulty

### The Curriculum Learning Analogy

**Human Learning**:
1. Elementary school: Basic arithmetic (achievable standards)
2. Middle school: Algebra (moderate standards)
3. High school: Calculus (rigorous standards)
4. College: Advanced mathematics (expert-level rigor)

**Agent Learning** (proposed):
1. Iterations 1-5: Get ANY valid solution (low verification)
2. Iterations 6-10: Refine with moderate checking (medium verification)
3. Iterations 11-15: Polish with rigorous checking (high verification)
4. Iterations 16+: Final proof with highest standards (high verification + strict format)

**Key principle**: **Don't fail a first-grader on calculus problems**

---

## Approach Comparison

### Overview Table

| Approach | Complexity | Adaptability | Predictability | Memory Integration |
|----------|------------|--------------|----------------|-------------------|
| A. Iteration-based | Low | Low | High | Simple |
| B. Success-based | Medium | High | Medium | Complex |
| C. Dual-track | Medium | Medium | High | Simple |
| D. Multi-stage | High | Low | High | Medium |
| **E. Hybrid (Recommended)** | **Medium** | **High** | **High** | **Medium** |

---

### Approach A: Iteration-Based Progression

**Description**: Fixed schedule based on iteration number

```python
def get_reasoning_effort(iteration, task_type):
    """
    task_type: 'generation' or 'verification'
    """
    if task_type == 'generation':
        return 'low'  # Always low for generation

    # Verification effort increases with iterations
    if iteration < 5:
        return 'low'
    elif iteration < 10:
        return 'medium'
    else:
        return 'high'
```

**Schedule**:
```
Iterations 0-4:   Gen=low,  Ver=low     (Phase 1: Initial exploration)
Iterations 5-9:   Gen=low,  Ver=medium  (Phase 2: Refinement)
Iterations 10+:   Gen=low,  Ver=high    (Phase 3: Final validation)
```

#### Advantages
- ✅ **Simple to implement**: Just check iteration counter
- ✅ **Predictable**: Always know what standards to expect
- ✅ **Easy to tune**: Adjust thresholds empirically
- ✅ **Memory-friendly**: Iteration count already saved
- ✅ **Reproducible**: Same behavior every run

#### Disadvantages
- ❌ **Not adaptive**: Doesn't account for agent's actual performance
- ❌ **May be too fast**: Could increase difficulty before agent is ready
- ❌ **May be too slow**: Wastes time if agent is already performing well
- ❌ **Fixed schedule**: Can't handle varying problem difficulty

#### Best For
- Initial testing and baseline establishment
- Problems with predictable difficulty
- When you want consistent, repeatable behavior

---

### Approach B: Success-Based Progression

**Description**: Increase difficulty based on consecutive successes

```python
class ProgressiveVerifier:
    def __init__(self):
        self.verification_level = 'low'
        self.consecutive_passes = 0
        self.level_history = []

    def get_verification_effort(self):
        return self.verification_level

    def update_after_verification(self, passed):
        if passed:
            self.consecutive_passes += 1

            # Increase difficulty after N consecutive passes
            if self.verification_level == 'low' and self.consecutive_passes >= 3:
                self.verification_level = 'medium'
                self.consecutive_passes = 0
            elif self.verification_level == 'medium' and self.consecutive_passes >= 3:
                self.verification_level = 'high'
                self.consecutive_passes = 0
            elif self.verification_level == 'high' and self.consecutive_passes >= 5:
                # SUCCESS! Final verification complete
                return True
        else:
            # Failure: reset consecutive count but DON'T decrease level
            self.consecutive_passes = 0

        return False
```

**Progression**:
```
Start:    Ver=low
After 3 consecutive passes at low:    Ver=medium (reset counter)
After 3 consecutive passes at medium: Ver=high   (reset counter)
After 5 consecutive passes at high:   SUCCESS!
```

#### Advantages
- ✅ **Adaptive**: Matches difficulty to agent's capability
- ✅ **Confidence building**: Only increases when ready
- ✅ **Natural stopping**: Success at highest level = high confidence
- ✅ **Prevents premature failure**: Doesn't punish early struggles
- ✅ **Handles varying difficulty**: Easy problems progress faster

#### Disadvantages
- ❌ **Unpredictable runtime**: Don't know how long it will take
- ❌ **Could get stuck**: If agent plateaus at medium level
- ❌ **Memory complexity**: Need to track more state
- ❌ **No upper bound**: Could run indefinitely
- ❌ **Hysteresis needed**: What if agent regresses?

#### Best For
- Varying problem difficulties
- When runtime is not a constraint
- When you want high confidence in final solution
- Adaptive systems that learn from feedback

---

### Approach C: Dual-Track Progression

**Description**: Verification difficulty increases faster than generation

```python
def get_reasoning_effort(iteration, task_type):
    if task_type == 'generation':
        # Generation: slow progression (stays low longer)
        if iteration < 15:
            return 'low'
        elif iteration < 25:
            return 'medium'
        else:
            return 'high'

    elif task_type == 'verification':
        # Verification: fast progression (gets strict quickly)
        if iteration < 3:
            return 'low'
        elif iteration < 8:
            return 'medium'
        else:
            return 'high'
```

**Timeline**:
```
Iterations 0-2:   Gen=low,    Ver=low     (Warmup)
Iterations 3-7:   Gen=low,    Ver=medium  (Generation easy, verification moderate)
Iterations 8-14:  Gen=low,    Ver=high    (Generation easy, verification strict)
Iterations 15-24: Gen=medium, Ver=high    (Both moderate/strict)
Iterations 25+:   Gen=high,   Ver=high    (Both strict)
```

#### Advantages
- ✅ **Asymmetric benefit**: Keeps generation efficient while verification gets rigorous
- ✅ **Early rigor**: Verification becomes strict quickly (good for catching errors)
- ✅ **Late flexibility**: Generation stays flexible longer (prevents truncation)
- ✅ **Best of both worlds**: Efficiency + rigor
- ✅ **Clear progression**: Two independent tracks

#### Disadvantages
- ❌ **Two schedules to tune**: More parameters to optimize
- ❌ **Potential mismatch**: High verification might reject all low-generation solutions
- ❌ **Not adaptive**: Still uses fixed schedule
- ❌ **Complex reasoning**: Harder to explain/justify the specific timings

#### Best For
- When you want rigorous verification but efficient generation
- Building on the asymmetric reasoning insight
- When you can afford to tune two separate schedules

---

### Approach D: Multi-Stage Approach

**Description**: Explicit stages with different goals

```python
class MultiStageAgent:
    def __init__(self):
        self.stage = 1
        self.solutions_by_stage = {}

    def get_current_stage_config(self):
        configs = {
            1: {
                'name': 'Initial Solution',
                'gen_effort': 'low',
                'ver_effort': 'low',
                'goal': 'Get ANY complete solution',
                'passes_needed': 2,
                'max_iterations': 10
            },
            2: {
                'name': 'Refinement',
                'gen_effort': 'low',
                'ver_effort': 'medium',
                'goal': 'Fix obvious errors',
                'passes_needed': 3,
                'max_iterations': 10
            },
            3: {
                'name': 'Polishing',
                'gen_effort': 'low',
                'ver_effort': 'high',
                'goal': 'Achieve rigorous proof',
                'passes_needed': 3,
                'max_iterations': 15
            },
            4: {
                'name': 'Final Validation',
                'gen_effort': 'medium',
                'ver_effort': 'high',
                'goal': 'Maximum confidence',
                'passes_needed': 5,
                'max_iterations': 10
            }
        }
        return configs[self.stage]

    def advance_stage(self):
        self.solutions_by_stage[self.stage] = self.current_solution
        self.stage += 1
        self.consecutive_passes = 0
```

**Stages**:
```
Stage 1 (Iter 0-10):   low/low,    Goal: ANY solution,      Need: 2 passes
Stage 2 (Iter 11-20):  low/medium, Goal: Fix errors,        Need: 3 passes
Stage 3 (Iter 21-35):  low/high,   Goal: Rigorous proof,    Need: 3 passes
Stage 4 (Iter 36-45):  medium/high,Goal: Final validation,  Need: 5 passes
```

#### Advantages
- ✅ **Clear milestones**: Each stage has explicit goal
- ✅ **Progress tracking**: Know which stage agent is in
- ✅ **Different criteria**: Each stage can have different success metrics
- ✅ **Forced progression**: Stages ensure minimum progress
- ✅ **Interpretable**: Easy to understand what agent is trying to do

#### Disadvantages
- ❌ **Complex state management**: Need to track stages, solutions per stage
- ❌ **Rigid structure**: Hard to skip stages if agent is already performing well
- ❌ **Potential waste**: Might spend too much time in early stages
- ❌ **Memory complexity**: Need to save stage information
- ❌ **Long total runtime**: Sum of all max_iterations could be large (45 in example)

#### Best For
- When you want explicit control over progression
- Research/analysis where you want to study each stage separately
- When interpretability is important
- When you can afford longer runtimes

---

### Approach E: Hybrid (Iteration-Based + Success-Gated)

**Description**: Combines iteration schedule with success-based gates

```python
class HybridProgressiveAgent:
    def __init__(self):
        self.iteration = 0
        self.consecutive_passes = 0
        self.verification_level = 'low'
        self.min_iterations_at_level = {
            'low': 0,
            'medium': 0,
            'high': 0
        }

    def get_verification_effort(self):
        """
        Verification level increases based on BOTH:
        1. Iteration count (schedule)
        2. Consecutive passes (readiness)
        """
        # Scheduled increase (can go up)
        scheduled_level = self._get_scheduled_level()

        # But only increase if agent has proven ready
        if scheduled_level > self.verification_level:
            # Only upgrade if we've had some success at current level
            if self.consecutive_passes >= 2:
                self.verification_level = scheduled_level
                self.consecutive_passes = 0
                self.min_iterations_at_level[scheduled_level] = self.iteration
                print(f"✓ Verification upgraded to {scheduled_level} at iteration {self.iteration}")

        return self.verification_level

    def _get_scheduled_level(self):
        """Schedule suggests when increases COULD happen"""
        if self.iteration < 5:
            return 'low'
        elif self.iteration < 12:
            return 'medium'
        else:
            return 'high'

    def update_after_verification(self, passed):
        if passed:
            self.consecutive_passes += 1
        else:
            self.consecutive_passes = 0

        self.iteration += 1

        # Success criteria: 5 passes at highest level
        if self.verification_level == 'high' and self.consecutive_passes >= 5:
            return True  # SUCCESS!

        return False
```

**Example Timeline**:
```
Iteration 0-4:  Ver=low     (scheduled: low, warmup phase)
Iteration 5:    Ver=low→medium IF 2+ passes achieved (gate check)
Iteration 6-11: Ver=medium  (scheduled: medium, refinement phase)
Iteration 12:   Ver=medium→high IF 2+ passes at medium (gate check)
Iteration 13+:  Ver=high    (final validation, need 5 passes)
```

#### Advantages
- ✅ **Best of both worlds**: Combines predictability + adaptability
- ✅ **Safety gates**: Won't increase if agent isn't ready
- ✅ **Bounded runtime**: Schedule provides upper bounds
- ✅ **Adaptive to performance**: Fast learners progress quickly
- ✅ **Prevents premature increase**: Gates ensure readiness
- ✅ **Clear progression**: Still has phases like iteration-based
- ✅ **Moderate complexity**: Not too simple, not too complex

#### Disadvantages
- ❌ **More parameters to tune**: Both schedule and gate thresholds
- ❌ **Interaction complexity**: Schedule + gates could conflict
- ❌ **Still has some rigidity**: Schedule provides framework
- ❌ **Medium implementation complexity**: More logic needed

#### Best For
- **RECOMMENDED FOR THIS PROJECT**
- Production use where you want both reliability and adaptability
- When you want safety nets (gates) but also progress guarantees (schedule)
- Balancing efficiency and rigor

---

## Recommended Strategy

### Primary Recommendation: Approach E (Hybrid)

**Rationale**:

1. **Addresses truncation problem**: Keeps generation at low (proven effective)
2. **Addresses verification rigor**: Progressive increase to high verification
3. **Safety mechanisms**: Gates prevent premature difficulty increase
4. **Bounded runtime**: Schedule ensures progress
5. **Handles varying difficulty**: Adaptive to agent performance
6. **Production-ready**: Good balance of complexity and reliability

### Configuration Parameters

```python
# Configuration for recommended hybrid approach
GRADIENT_CONFIG = {
    # Generation reasoning (stays low for efficiency)
    'generation_effort': 'low',

    # Verification progression schedule
    'verification_schedule': {
        'low': {
            'iterations': (0, 5),      # Iterations where low is scheduled
            'passes_needed': 2,         # Consecutive passes to unlock next level
            'description': 'Initial exploration - get any valid solution'
        },
        'medium': {
            'iterations': (5, 12),     # Iterations where medium is scheduled
            'passes_needed': 2,         # Consecutive passes to unlock high
            'description': 'Refinement - fix obvious errors'
        },
        'high': {
            'iterations': (12, 30),    # Iterations where high is scheduled
            'passes_needed': 5,         # Final success criteria
            'description': 'Final validation - rigorous proof'
        }
    },

    # Safety parameters
    'min_iterations_per_level': 3,     # Minimum iterations before considering upgrade
    'max_total_iterations': 30,         # Hard limit
    'max_errors': 10,                   # Early termination threshold

    # Fallback options
    'allow_level_skip': False,          # Can skip medium if doing very well?
    'allow_level_downgrade': False      # Can decrease rigor if stuck?
}
```

### Success Criteria by Level

| Level | Goal | Consecutive Passes | Quality Standard |
|-------|------|-------------------|------------------|
| Low | Get ANY complete solution | 2 | Basic structure, answer present |
| Medium | Fix obvious errors | 2 | No critical logical errors |
| High | Rigorous proof | 5 | IMO-level rigor, no gaps |

---

## Implementation Details

### File Structure

```
code/
├── agent_gpt_oss.py                    # Main agent (needs modification)
├── progressive_reasoning.py            # NEW: Gradient reasoning logic
└── progressive_config.py               # NEW: Configuration parameters
```

### Implementation Plan

#### Step 1: Create Progressive Reasoning Module

**File**: `/home/user/IMO25/code/progressive_reasoning.py`

```python
"""
Progressive Reasoning Effort System
Implements gradient/curriculum learning for reasoning effort.
"""

import json
from typing import Literal, Dict, Tuple

ReasoningLevel = Literal['low', 'medium', 'high']
TaskType = Literal['generation', 'verification']

class ProgressiveReasoningManager:
    """
    Manages progressive increase in reasoning effort across iterations.
    Uses hybrid approach: iteration-based schedule + success-based gates.
    """

    def __init__(self, config: dict = None):
        """
        Initialize with configuration.

        Args:
            config: Configuration dictionary (uses default if None)
        """
        self.config = config or self._default_config()

        # State tracking
        self.iteration = 0
        self.verification_level: ReasoningLevel = 'low'
        self.consecutive_passes = 0
        self.verification_history = []
        self.level_transitions = []

    @staticmethod
    def _default_config() -> dict:
        """Default configuration for progressive reasoning"""
        return {
            'generation_effort': 'low',
            'verification_schedule': {
                'low': {
                    'iterations': (0, 5),
                    'passes_needed': 2,
                    'description': 'Initial exploration'
                },
                'medium': {
                    'iterations': (5, 12),
                    'passes_needed': 2,
                    'description': 'Refinement'
                },
                'high': {
                    'iterations': (12, 30),
                    'passes_needed': 5,
                    'description': 'Final validation'
                }
            },
            'min_iterations_per_level': 3,
            'max_total_iterations': 30,
            'max_errors': 10
        }

    def get_reasoning_effort(self, task_type: TaskType) -> ReasoningLevel:
        """
        Get reasoning effort for current task.

        Args:
            task_type: 'generation' or 'verification'

        Returns:
            Reasoning level ('low', 'medium', or 'high')
        """
        if task_type == 'generation':
            return self.config['generation_effort']
        elif task_type == 'verification':
            return self.verification_level
        else:
            raise ValueError(f"Unknown task type: {task_type}")

    def _get_scheduled_level(self) -> ReasoningLevel:
        """Get the level that should be active based on iteration schedule"""
        for level, params in self.config['verification_schedule'].items():
            start, end = params['iterations']
            if start <= self.iteration < end:
                return level
        # Default to highest level if beyond schedule
        return 'high'

    def _can_upgrade_level(self, to_level: ReasoningLevel) -> bool:
        """
        Check if agent is ready to upgrade to next level.

        Requires:
        1. Scheduled level allows it
        2. Enough consecutive passes at current level
        3. Minimum iterations at current level completed
        """
        # Find current level config
        current_config = self.config['verification_schedule'][self.verification_level]
        passes_needed = current_config['passes_needed']

        # Check if we have enough passes
        if self.consecutive_passes < passes_needed:
            return False

        # Check minimum iterations (if we have level transition history)
        if self.level_transitions:
            last_transition = self.level_transitions[-1]
            iterations_at_current = self.iteration - last_transition['iteration']
            if iterations_at_current < self.config['min_iterations_per_level']:
                return False

        return True

    def update_after_verification(self, passed: bool) -> Dict:
        """
        Update state after verification and check for level transitions.

        Args:
            passed: Whether verification passed

        Returns:
            Dictionary with status information:
            {
                'iteration': int,
                'verification_level': str,
                'passed': bool,
                'consecutive_passes': int,
                'level_upgraded': bool,
                'success': bool  # True if final success achieved
            }
        """
        # Update pass counter
        if passed:
            self.consecutive_passes += 1
        else:
            self.consecutive_passes = 0

        # Record in history
        self.verification_history.append({
            'iteration': self.iteration,
            'level': self.verification_level,
            'passed': passed,
            'consecutive_passes': self.consecutive_passes
        })

        # Check for level upgrade
        scheduled_level = self._get_scheduled_level()
        level_upgraded = False

        if scheduled_level != self.verification_level:
            # Schedule suggests upgrade - check if agent is ready
            level_order = ['low', 'medium', 'high']
            current_idx = level_order.index(self.verification_level)
            scheduled_idx = level_order.index(scheduled_level)

            if scheduled_idx > current_idx:
                # Potential upgrade - check readiness
                if self._can_upgrade_level(scheduled_level):
                    old_level = self.verification_level
                    self.verification_level = scheduled_level
                    self.consecutive_passes = 0
                    level_upgraded = True

                    # Record transition
                    self.level_transitions.append({
                        'iteration': self.iteration,
                        'from_level': old_level,
                        'to_level': scheduled_level,
                        'reason': 'passed_gate'
                    })

                    print(f"\n{'='*70}")
                    print(f"✓ VERIFICATION LEVEL UPGRADED: {old_level} → {scheduled_level}")
                    print(f"  Iteration: {self.iteration}")
                    print(f"  Reason: Achieved {self.config['verification_schedule'][old_level]['passes_needed']} consecutive passes")
                    print(f"  New goal: {self.config['verification_schedule'][scheduled_level]['description']}")
                    print(f"{'='*70}\n")

        # Check for final success
        final_config = self.config['verification_schedule']['high']
        success = (
            self.verification_level == 'high' and
            self.consecutive_passes >= final_config['passes_needed']
        )

        # Increment iteration counter
        self.iteration += 1

        return {
            'iteration': self.iteration - 1,  # Return current iteration number
            'verification_level': self.verification_level,
            'passed': passed,
            'consecutive_passes': self.consecutive_passes,
            'level_upgraded': level_upgraded,
            'success': success
        }

    def get_status(self) -> Dict:
        """Get current status of progressive reasoning system"""
        scheduled_level = self._get_scheduled_level()
        current_config = self.config['verification_schedule'][self.verification_level]

        return {
            'iteration': self.iteration,
            'verification_level': self.verification_level,
            'scheduled_level': scheduled_level,
            'consecutive_passes': self.consecutive_passes,
            'passes_needed': current_config['passes_needed'],
            'level_description': current_config['description'],
            'ready_for_upgrade': (
                scheduled_level != self.verification_level and
                self._can_upgrade_level(scheduled_level)
            )
        }

    def to_dict(self) -> dict:
        """Serialize state for saving to memory"""
        return {
            'iteration': self.iteration,
            'verification_level': self.verification_level,
            'consecutive_passes': self.consecutive_passes,
            'verification_history': self.verification_history,
            'level_transitions': self.level_transitions,
            'config': self.config
        }

    @classmethod
    def from_dict(cls, state: dict) -> 'ProgressiveReasoningManager':
        """Deserialize state from memory"""
        manager = cls(config=state.get('config'))
        manager.iteration = state.get('iteration', 0)
        manager.verification_level = state.get('verification_level', 'low')
        manager.consecutive_passes = state.get('consecutive_passes', 0)
        manager.verification_history = state.get('verification_history', [])
        manager.level_transitions = state.get('level_transitions', [])
        return manager


def print_progression_summary(manager: ProgressiveReasoningManager):
    """Print a summary of the progression through levels"""
    print("\n" + "="*70)
    print("PROGRESSIVE REASONING SUMMARY")
    print("="*70)

    status = manager.get_status()
    print(f"\nCurrent Status:")
    print(f"  Iteration: {status['iteration']}")
    print(f"  Verification Level: {status['verification_level']}")
    print(f"  Consecutive Passes: {status['consecutive_passes']}/{status['passes_needed']}")
    print(f"  Current Goal: {status['level_description']}")

    if manager.level_transitions:
        print(f"\nLevel Transitions:")
        for trans in manager.level_transitions:
            print(f"  Iteration {trans['iteration']}: {trans['from_level']} → {trans['to_level']}")

    if manager.verification_history:
        print(f"\nVerification History (last 10):")
        for vh in manager.verification_history[-10:]:
            status_icon = "✓" if vh['passed'] else "✗"
            print(f"  Iter {vh['iteration']:2d} [{vh['level']:6s}]: {status_icon} (streak: {vh['consecutive_passes']})")

    print("="*70 + "\n")
```

#### Step 2: Modify agent_gpt_oss.py

**Changes needed**:

1. **Import progressive reasoning module** (line ~31):
```python
from progressive_reasoning import ProgressiveReasoningManager, print_progression_summary
```

2. **Replace global REASONING_EFFORT** (line ~49):
```python
# OLD:
# REASONING_EFFORT = os.getenv("GPT_OSS_REASONING_EFFORT", "low")

# NEW:
# Initialize progressive reasoning (will be per-agent instance)
ENABLE_PROGRESSIVE = os.getenv("GPT_OSS_ENABLE_PROGRESSIVE", "true").lower() == "true"
DEFAULT_REASONING_EFFORT = os.getenv("GPT_OSS_REASONING_EFFORT", "low")
```

3. **Modify build_request_payload** (line ~130):
```python
def build_request_payload(system_prompt, question_prompt, other_prompts=None,
                         reasoning_effort=None):
    """
    Builds the JSON payload for the OpenAI-compatible API request.

    Args:
        reasoning_effort: Reasoning effort level (if None, uses DEFAULT)
    """
    if reasoning_effort is None:
        reasoning_effort = DEFAULT_REASONING_EFFORT

    payload = {
        "messages": [...],
        "model": MODEL_NAME,
        "temperature": 0.1,
        "reasoning": {
            "effort": reasoning_effort  # Use specified effort
        }
    }
    return payload
```

4. **Modify verify_solution to accept reasoning_effort** (line ~437):
```python
def verify_solution(problem_statement, solution, verbose=True,
                   reasoning_effort=None):
    """
    Verify solution with specified reasoning effort.

    Args:
        reasoning_effort: Reasoning level for verification (default: DEFAULT_REASONING_EFFORT)
    """
    if reasoning_effort is None:
        reasoning_effort = DEFAULT_REASONING_EFFORT

    dsol = extract_detailed_solution(solution)
    newst = f"""..."""

    if verbose:
        print(f">>>>>>> Start verification (reasoning_effort={reasoning_effort})")

    p2 = build_request_payload(
        system_prompt=verification_system_prompt,
        question_prompt=newst,
        reasoning_effort=reasoning_effort  # Pass through
    )

    # ... rest of function
```

5. **Modify save_memory to include progressive state** (line ~492):
```python
def save_memory(memory_file, problem_statement, other_prompts,
               current_iteration, max_runs, solution=None, verify=None,
               progressive_manager=None):
    """Save state including progressive reasoning manager"""
    memory = {
        "problem_statement": problem_statement,
        "other_prompts": other_prompts,
        "current_iteration": current_iteration,
        "max_runs": max_runs,
        "solution": solution,
        "verify": verify,
        "timestamp": __import__('datetime').datetime.now().isoformat()
    }

    # Add progressive reasoning state if using it
    if progressive_manager is not None:
        memory["progressive_reasoning"] = progressive_manager.to_dict()

    # ... rest of function
```

6. **Major changes to agent() function** (line ~587):
```python
def agent(problem_statement, other_prompts=[], memory_file=None,
         resume_from_memory=False):
    """
    Main agent loop with progressive reasoning support.
    """
    # Initialize progressive reasoning manager
    progressive_manager = None
    if ENABLE_PROGRESSIVE:
        progressive_manager = ProgressiveReasoningManager()

    # Load from memory if resuming
    if resume_from_memory and memory_file:
        memory = load_memory(memory_file)
        if memory:
            problem_statement = memory.get("problem_statement", problem_statement)
            other_prompts = memory.get("other_prompts", other_prompts)
            current_iteration = memory.get("current_iteration", 0)
            solution = memory.get("solution", None)
            verify = memory.get("verify", None)

            # Restore progressive reasoning state
            if ENABLE_PROGRESSIVE and "progressive_reasoning" in memory:
                progressive_manager = ProgressiveReasoningManager.from_dict(
                    memory["progressive_reasoning"]
                )

            print(f"Resuming from iteration {current_iteration}")
            if progressive_manager:
                print_progression_summary(progressive_manager)
        else:
            print("Failed to load memory, starting fresh")
            current_iteration = 0
            solution = None
            verify = None
    else:
        current_iteration = 0
        solution = None
        verify = None

    # Initial exploration
    if solution is None:
        # Use low reasoning for initial generation (always)
        gen_effort = (progressive_manager.get_reasoning_effort('generation')
                     if progressive_manager else DEFAULT_REASONING_EFFORT)

        p1, solution, verify, good_verify = init_explorations(
            problem_statement, True, other_prompts
        )

        if solution is None:
            print(">>>>>>> Failed in finding a complete solution.")
            return None

        # Update progressive manager after initial verification
        if progressive_manager:
            passed = "yes" in good_verify.lower()
            status = progressive_manager.update_after_verification(passed)
            print(f">>> Progressive Status: Level={status['verification_level']}, "
                  f"Passes={status['consecutive_passes']}")
    else:
        # Resuming - verify with current level
        ver_effort = (progressive_manager.get_reasoning_effort('verification')
                     if progressive_manager else DEFAULT_REASONING_EFFORT)
        _, good_verify = verify_solution(problem_statement, solution,
                                        reasoning_effort=ver_effort)

    error_count = 0
    correct_count = 0

    for i in range(current_iteration, 30):
        print(f"\n{'='*70}")
        print(f"Iteration: {i}, Errors: {error_count}/10")

        if progressive_manager:
            status = progressive_manager.get_status()
            print(f"Verification Level: {status['verification_level']}")
            print(f"Consecutive Passes: {status['consecutive_passes']}/{status['passes_needed']}")
            print(f"Goal: {status['level_description']}")
        else:
            print(f"Correct Count: {correct_count}/5")

        print(f"{'='*70}\n")

        try:
            # Determine reasoning efforts
            gen_effort = (progressive_manager.get_reasoning_effort('generation')
                         if progressive_manager else DEFAULT_REASONING_EFFORT)
            ver_effort = (progressive_manager.get_reasoning_effort('verification')
                         if progressive_manager else DEFAULT_REASONING_EFFORT)

            # Check verification result
            if "yes" not in good_verify.lower():
                # Verification failed
                error_count += 1

                if progressive_manager:
                    status = progressive_manager.update_after_verification(False)
                    print(f">>> Verification FAILED at {status['verification_level']} level")

                # Generate correction
                print(f">>>>>>> Verification does not pass, correcting ...")
                print(f">>>>>>> Using reasoning_effort={gen_effort} for generation")

                p1 = build_request_payload(
                    system_prompt=step1_prompt,
                    question_prompt=problem_statement,
                    other_prompts=other_prompts,
                    reasoning_effort=gen_effort
                )

                p1["messages"].append({
                    "role": "assistant",
                    "content": solution
                })
                p1["messages"].append({
                    "role": "user",
                    "content": correction_prompt + "\n\n" + verify
                })

                response2 = send_api_request(get_api_key(), p1)
                solution = extract_solution(extract_text_from_response(response2))

                print(">>>>>>> Corrected solution generated")

            # Verify the solution
            print(f">>>>>>> Verifying solution (reasoning_effort={ver_effort})")
            verify, good_verify = verify_solution(problem_statement, solution,
                                                 reasoning_effort=ver_effort)

            # Update state based on verification
            if "yes" in good_verify.lower():
                print(">>>>>>> Solution PASSED verification")

                if progressive_manager:
                    status = progressive_manager.update_after_verification(True)

                    if status['success']:
                        print("\n" + "="*70)
                        print("🎉 SUCCESS! Final solution validated at HIGHEST level")
                        print("="*70)
                        print_progression_summary(progressive_manager)
                        print(json.dumps(solution, indent=4))
                        return solution

                    if status['level_upgraded']:
                        print(f">>> Verification level upgraded!")
                        print(f">>> New target: {status['consecutive_passes']}/{status['passes_needed']} passes at {status['verification_level']} level")
                else:
                    correct_count += 1
                    error_count = 0

                    if correct_count >= 5:
                        print(">>>>>>> Correct solution found (5 consecutive passes).")
                        print(json.dumps(solution, indent=4))
                        return solution

            # Save memory every iteration
            if memory_file:
                save_memory(memory_file, problem_statement, other_prompts,
                           i, 30, solution, verify, progressive_manager)

            # Check failure conditions
            if error_count >= 10:
                print(">>>>>>> Failed: Reached maximum error count (10)")
                if progressive_manager:
                    print_progression_summary(progressive_manager)
                if memory_file:
                    save_memory(memory_file, problem_statement, other_prompts,
                               i, 30, solution, verify, progressive_manager)
                return None

        except Exception as e:
            print(f">>>>>>> Error in iteration {i}: {e}")
            continue

    # Reached maximum iterations
    print(">>>>>>> Failed: Reached maximum iterations (30)")
    if progressive_manager:
        print_progression_summary(progressive_manager)
    if memory_file:
        save_memory(memory_file, problem_statement, other_prompts,
                   30, 30, solution, verify, progressive_manager)
    return None
```

7. **Update CLI arguments** (line ~696):
```python
parser.add_argument('--progressive', '-p', action='store_true',
                   help='Enable progressive reasoning effort (default: enabled)')
parser.add_argument('--no-progressive', action='store_true',
                   help='Disable progressive reasoning (use fixed effort)')
```

#### Step 3: Create Configuration File

**File**: `/home/user/IMO25/code/progressive_config.py`

```python
"""
Configuration presets for progressive reasoning system.
"""

# Default hybrid configuration (recommended)
HYBRID_DEFAULT = {
    'generation_effort': 'low',
    'verification_schedule': {
        'low': {
            'iterations': (0, 5),
            'passes_needed': 2,
            'description': 'Initial exploration - get any valid solution'
        },
        'medium': {
            'iterations': (5, 12),
            'passes_needed': 2,
            'description': 'Refinement - fix obvious errors'
        },
        'high': {
            'iterations': (12, 30),
            'passes_needed': 5,
            'description': 'Final validation - rigorous proof'
        }
    },
    'min_iterations_per_level': 3,
    'max_total_iterations': 30,
    'max_errors': 10
}

# Conservative: slower progression
CONSERVATIVE = {
    'generation_effort': 'low',
    'verification_schedule': {
        'low': {
            'iterations': (0, 8),
            'passes_needed': 3,
            'description': 'Extended warmup'
        },
        'medium': {
            'iterations': (8, 16),
            'passes_needed': 3,
            'description': 'Careful refinement'
        },
        'high': {
            'iterations': (16, 35),
            'passes_needed': 5,
            'description': 'Thorough validation'
        }
    },
    'min_iterations_per_level': 5,
    'max_total_iterations': 35,
    'max_errors': 12
}

# Aggressive: faster progression
AGGRESSIVE = {
    'generation_effort': 'low',
    'verification_schedule': {
        'low': {
            'iterations': (0, 3),
            'passes_needed': 1,
            'description': 'Quick warmup'
        },
        'medium': {
            'iterations': (3, 8),
            'passes_needed': 2,
            'description': 'Rapid refinement'
        },
        'high': {
            'iterations': (8, 25),
            'passes_needed': 5,
            'description': 'Final validation'
        }
    },
    'min_iterations_per_level': 2,
    'max_total_iterations': 25,
    'max_errors': 10
}

# For testing: very fast progression
FAST_TEST = {
    'generation_effort': 'low',
    'verification_schedule': {
        'low': {
            'iterations': (0, 2),
            'passes_needed': 1,
            'description': 'Quick test'
        },
        'medium': {
            'iterations': (2, 4),
            'passes_needed': 1,
            'description': 'Quick test'
        },
        'high': {
            'iterations': (4, 15),
            'passes_needed': 3,
            'description': 'Quick test'
        }
    },
    'min_iterations_per_level': 1,
    'max_total_iterations': 15,
    'max_errors': 8
}
```

---

## Expected Benefits & Challenges

### Benefits

#### 1. Prevents Truncation (Like Low/Low)
- ✅ Generation stays at low reasoning
- ✅ 0 truncations expected (proven in tests)
- ✅ Fast iteration speed maintained
- ✅ Focused, structured output

#### 2. Achieves High Confidence (Better than Low/Low)
- ✅ Final solutions validated at HIGH reasoning level
- ✅ 5 consecutive passes at highest standard
- ✅ Very low false positive rate
- ✅ Publishable confidence level

#### 3. Builds Capability Progressively
- ✅ Agent learns from easier standards first
- ✅ Doesn't fail immediately on hard problems
- ✅ Gradual improvement through feedback
- ✅ Natural curriculum learning

#### 4. Adaptive to Problem Difficulty
- ✅ Easy problems progress quickly through levels
- ✅ Hard problems get more time at each level
- ✅ Success gates prevent premature advancement
- ✅ Better resource allocation

#### 5. Memory/Resume Compatible
- ✅ Progressive state saves to memory file
- ✅ Can resume at any level
- ✅ Preserves level transition history
- ✅ No loss of progress

### Challenges

#### 1. Parameter Tuning
- ⚠️ Need to find optimal thresholds
- ⚠️ Different problems might need different schedules
- ⚠️ May need empirical testing to optimize
- **Mitigation**: Start with conservative defaults, provide presets

#### 2. Longer Runtime (Potentially)
- ⚠️ More iterations needed to reach final success
- ⚠️ Low→medium→high takes longer than jumping to high
- ⚠️ But jumpting to high directly FAILED (baseline)
- **Mitigation**: Still faster than baseline (which never succeeded)

#### 3. Implementation Complexity
- ⚠️ More code to maintain
- ⚠️ More state to track
- ⚠️ Harder to debug
- **Mitigation**: Modular design, good logging, clear state management

#### 4. Potential for Getting Stuck
- ⚠️ Agent might plateau at medium level
- ⚠️ Might never reach high level gates
- ⚠️ No downgrade mechanism (by design)
- **Mitigation**: Max iterations per level, clear failure modes

### Risk Mitigation Strategies

| Risk | Impact | Mitigation |
|------|--------|------------|
| Wrong schedule parameters | Suboptimal progression | Provide multiple presets, allow tuning |
| Agent stuck at medium | Never reaches high | Max iterations forces progression or failure |
| Too many iterations | Expensive runtime | Hard limits, early termination |
| State corruption | Lost progress | Robust serialization, validation |
| Regression bugs | System breaks | Comprehensive testing, backward compatibility |

---

## Testing & Validation Plan

### Phase 1: Unit Testing (Week 1)

**Objective**: Verify progressive reasoning logic

**Tests**:
```python
# Test 1: Level transitions
def test_level_transitions():
    manager = ProgressiveReasoningManager()
    assert manager.verification_level == 'low'

    # Simulate 2 passes at low
    manager.update_after_verification(True)
    manager.update_after_verification(True)
    assert manager.verification_level == 'low'  # Not yet at threshold iteration

    # Advance to iteration 5, try to upgrade
    for _ in range(3):
        manager.iteration += 1
    manager.update_after_verification(True)
    manager.update_after_verification(True)
    # Should upgrade now (at iteration 5+ with 2 passes)
    assert manager.verification_level == 'medium'

# Test 2: Success criteria
def test_success_criteria():
    manager = ProgressiveReasoningManager()
    manager.verification_level = 'high'
    manager.iteration = 15

    # Simulate 5 consecutive passes
    for i in range(5):
        status = manager.update_after_verification(True)
        if i < 4:
            assert not status['success']
        else:
            assert status['success']

# Test 3: Gate blocking
def test_gate_blocks_upgrade():
    manager = ProgressiveReasoningManager()
    manager.iteration = 5  # At medium schedule

    # But no passes yet
    manager.consecutive_passes = 0
    status = manager.update_after_verification(False)

    # Should stay at low (not enough passes)
    assert manager.verification_level == 'low'

# Test 4: Serialization
def test_serialization():
    manager1 = ProgressiveReasoningManager()
    manager1.iteration = 10
    manager1.verification_level = 'medium'
    manager1.consecutive_passes = 3

    # Serialize and deserialize
    state = manager1.to_dict()
    manager2 = ProgressiveReasoningManager.from_dict(state)

    assert manager2.iteration == 10
    assert manager2.verification_level == 'medium'
    assert manager2.consecutive_passes == 3
```

### Phase 2: Integration Testing (Week 1-2)

**Objective**: Verify integration with agent_gpt_oss.py

**Tests**:
1. Test with progressive enabled vs disabled
2. Test memory save/load with progressive state
3. Test resume from different levels
4. Test with different configuration presets

**Command**:
```bash
# Test 1: Default progressive
python code/agent_gpt_oss.py problems/test_simple.txt \
  --log logs/test_progressive_default.log \
  --memory memory/test_progressive.json

# Test 2: Conservative preset
export GPT_OSS_PROGRESSIVE_CONFIG="conservative"
python code/agent_gpt_oss.py problems/test_simple.txt \
  --log logs/test_progressive_conservative.log

# Test 3: Resume from memory
python code/agent_gpt_oss.py problems/test_simple.txt \
  --memory memory/test_progressive.json \
  --resume
```

### Phase 3: Comparative Testing (Week 2-3)

**Objective**: Compare progressive vs baseline approaches

**Test Matrix**:

| Configuration | Generation | Verification | Expected Outcome |
|---------------|------------|--------------|------------------|
| Baseline (original) | high | high | 0% success (proven) |
| Low/Low | low | low | 30-40% success, low confidence |
| Low/High (asymmetric) | low | high | ? (untested) |
| **Progressive (hybrid)** | **low** | **low→medium→high** | **60-80% success, high confidence** |

**Test Problems**:
1. IMO 2025 Problem 1 (tested before)
2. IMO 2025 Problem 2 (new)
3. IMO 2025 Problem 3 (new)
4. Pre-IMO level (easier, control)
5. IMO-hard level (harder, stress test)

**Metrics to Collect**:
- Success rate (%)
- Iterations to success
- Truncations per iteration
- Verification pass rate by level
- Level transition timing
- Total runtime
- Solution quality (manual review)

**Expected Results**:

```
Problem: IMO 2025 Problem 1
├─ Baseline (high/high):     SUCCESS: 0%,  Iterations: ∞,      Truncations: 12.2/iter
├─ Low/Low:                  SUCCESS: ?%,  Iterations: ~17,    Truncations: 0/iter
├─ Low/High (asymmetric):    SUCCESS: ?%,  Iterations: ~20-25, Truncations: 0/iter
└─ Progressive (hybrid):     SUCCESS: ?%,  Iterations: ~25-30, Truncations: 0/iter
```

### Phase 4: Optimization (Week 3-4)

**Objective**: Tune parameters for optimal performance

**Parameters to Tune**:
1. Iteration thresholds (when to allow level increase)
2. Pass requirements (how many passes needed at each level)
3. Minimum iterations per level
4. Early vs late progression

**Method**: Grid search or Bayesian optimization

**Optimization Target**: Maximize success rate while minimizing total iterations

### Phase 5: Production Validation (Week 4+)

**Objective**: Validate on full benchmark

**Test Suite**:
- gradingbench: All levels
- proofbench: All levels
- answerbench: Full suite

**Success Criteria**:
- Success rate > 50% on pre-IMO
- Success rate > 30% on IMO-easy/medium
- Success rate > 10% on IMO-hard
- No truncations
- High confidence in solutions (manual spot-check)

---

## Alternative Approaches Considered

### Why Not Pure Success-Based (Approach B)?

**Concerns**:
- No upper bound on iterations
- Could run indefinitely if agent plateaus
- Hard to predict runtime
- Debugging difficult without predictable schedule

**When it would work better**:
- Unlimited compute budget
- Research setting where runtime doesn't matter
- When you want maximum adaptation

### Why Not Multi-Stage (Approach D)?

**Concerns**:
- Too rigid
- Wastes time if agent progresses quickly
- Complex state management
- Total runtime might be very long (sum of all stage maxes)

**When it would work better**:
- When you need explicit milestones for reporting
- Research/analysis of each stage separately
- When interpretability > efficiency

### Why Not Pure Iteration-Based (Approach A)?

**Concerns**:
- Not adaptive
- Might increase difficulty too fast for hard problems
- Might be too slow for easy problems
- Treats all problems the same

**When it would work better**:
- Initial testing/baseline
- When problems have similar difficulty
- When you need simple, predictable behavior

### Why Hybrid is Best

**Combines strengths**:
- ✅ Schedule provides structure (iteration-based)
- ✅ Gates provide safety (success-based)
- ✅ Dual-track efficiency (verification increases faster)
- ✅ Bounded runtime (max iterations)
- ✅ Adaptive capability (gates respond to performance)

**Minimizes weaknesses**:
- ✅ Not too rigid (gates allow variation)
- ✅ Not too flexible (schedule provides bounds)
- ✅ Not too complex (moderate state)
- ✅ Not too simple (handles varying difficulty)

---

## Interaction with Memory/Resume

### State to Save

```python
{
    "progressive_reasoning": {
        "iteration": 12,
        "verification_level": "medium",
        "consecutive_passes": 1,
        "verification_history": [
            {"iteration": 0, "level": "low", "passed": true, "consecutive_passes": 1},
            {"iteration": 1, "level": "low", "passed": true, "consecutive_passes": 2},
            {"iteration": 5, "level": "medium", "passed": false, "consecutive_passes": 0},
            ...
        ],
        "level_transitions": [
            {"iteration": 5, "from_level": "low", "to_level": "medium", "reason": "passed_gate"}
        ],
        "config": {...}
    }
}
```

### Resume Behavior

**Scenario 1: Resume at Same Level**
```
Saved:  Iteration 8, Level medium, Passes 1
Resume: Continue at medium, remember the 1 pass
Next:   Need 1 more pass at medium to potentially upgrade
```

**Scenario 2: Resume After Level Transition**
```
Saved:  Iteration 12, just upgraded to high, Passes 0
Resume: Start at high level, need 5 passes
Next:   Verify at high standard immediately
```

**Scenario 3: Resume From Failed Run**
```
Saved:  Iteration 25, Level high, Passes 2, then crashed
Resume: Continue at high, remember 2 passes
Next:   Need 3 more passes to succeed
```

### Compatibility with Existing Memory System

**No breaking changes**:
- If no progressive state in memory → use default/disabled
- If progressive state present → restore from it
- Backward compatible with old memory files
- Forward compatible (can add new fields)

---

## Visualization & Monitoring

### Recommended Output Format

```
================================================================================
ITERATION 12 PROGRESS
================================================================================
Verification Level: medium
Consecutive Passes: 1/2 (need 1 more to upgrade to high)
Current Goal: Refinement - fix obvious errors
Error Count: 3/10

Schedule Status:
  [✓] low     (0-5):   Completed at iteration 5
  [→] medium  (5-12):  Currently active
  [ ] high    (12-30): Scheduled next (if gate passed)

Level Transition History:
  Iteration 5: low → medium (passed gate with 2 consecutive passes)

Recent Verification History:
  Iter  8 [medium]: ✗ (streak: 0)
  Iter  9 [medium]: ✗ (streak: 0)
  Iter 10 [medium]: ✓ (streak: 1)
  Iter 11 [medium]: ✗ (streak: 0)
  Iter 12 [medium]: ✓ (streak: 1) ← current
================================================================================
```

### Monitor Integration

Update `/home/user/IMO25/monitor_agent_progress.py` to track:
- Current verification level
- Passes needed to upgrade
- Level transition events
- Time spent at each level

---

## Success Metrics

### Primary Metrics

1. **Success Rate**: % of problems solved completely
   - Target: > 60% (vs 0% baseline, ~40% low/low)

2. **Solution Confidence**: Quality of final solutions
   - Target: 95%+ pass manual expert review
   - Measured by: No false positives in high-level verification

3. **Efficiency**: Average iterations to success
   - Target: < 30 iterations (bounded)
   - Comparison: Low/low achieved in ~17, but low confidence

4. **Robustness**: Truncation rate
   - Target: 0 truncations (like low/low)
   - Must maintain this from baseline fix

### Secondary Metrics

5. **Level Progression**: How quickly problems advance through levels
   - Track: Average iteration at each level transition
   - Insight: Harder problems stay longer at low/medium

6. **Pass Rate by Level**: Verification pass rate at each level
   - Expected: High at low (~60%), Medium at medium (~40%), Lower at high (~30%)
   - Validates that levels are actually different in rigor

7. **Error Recovery**: Ability to learn from verification failures
   - Track: Consecutive failures before giving up
   - Target: < 5 consecutive failures at any level

---

## Future Enhancements

### Possible Extensions

1. **Problem Difficulty Detection**
   - Auto-adjust schedule based on problem complexity
   - Use faster progression for simpler problems

2. **Dynamic Generation Effort**
   - Allow generation effort to increase in later stages
   - Stage 4 could use medium/high for final polish

3. **Level Downgrade Option**
   - If stuck at high, temporarily drop to medium
   - Get more passes, then retry high

4. **Adaptive Thresholds**
   - Learn optimal thresholds from historical data
   - Per-problem-type configurations

5. **Multi-Model Support**
   - Different models might need different schedules
   - Auto-tune based on model capabilities

6. **Verification Ensemble**
   - Use multiple verification levels simultaneously
   - Solution must pass ALL levels

---

## Comparison to Related Work

### Curriculum Learning in ML
- **Standard CL**: Train on easy examples first, gradually increase difficulty
- **Our approach**: Verify with easy standards first, gradually increase rigor
- **Key difference**: We're not retraining, but adapting evaluation standards

### Self-Taught Reasoner (STaR)
- **STaR**: Generate rationales, filter by correctness, finetune
- **Our approach**: Generate solutions, verify with progressive rigor, iterate
- **Similarity**: Both use generated content + filtering

### AlphaGo/AlphaZero Self-Play
- **AlphaGo**: Play against self, curriculum of opponent strength
- **Our approach**: Solve with increasing verification rigor
- **Similarity**: Progressive difficulty, self-improvement loop

### Verification-Guided Decoding
- **Standard VGD**: Use verifier to guide/rerank generation
- **Our approach**: Use progressive verifier to assess and iterate
- **Difference**: We iterate solutions, not decode paths

---

## Conclusion

### Recommended Implementation Path

**Week 1**: Implement core progressive reasoning module
- Create `progressive_reasoning.py`
- Modify `agent_gpt_oss.py` integration
- Unit tests

**Week 2**: Integration and initial testing
- Test on IMO problem 1 (known baseline)
- Compare to low/low results
- Tune default configuration

**Week 3**: Comparative evaluation
- Test on multiple problems
- Compare all approaches (baseline, low/low, asymmetric, progressive)
- Collect comprehensive metrics

**Week 4**: Optimization and documentation
- Tune parameters
- Run full benchmark
- Document results

### Expected Outcome

**Best case** (80% confidence):
- 60-80% success rate on tested problems
- High confidence in solutions (validated at high level)
- 0 truncations maintained
- Clear progression through levels
- Publishable results

**Realistic case** (95% confidence):
- 40-60% success rate
- Higher confidence than low/low
- Some challenges with parameter tuning
- Demonstrates clear benefit over binary approach
- Valuable insights for future work

**Worst case** (99% confidence):
- Similar to low/low but slower (more iterations)
- Fails to reach high level on hard problems
- But still better than baseline (0%)
- Provides data on where approach struggles
- Informs next iteration of design

### Key Insight

**The gradient/progressive approach is fundamentally about building confidence progressively rather than demanding perfection immediately.**

Just as:
- Students learn from easy to hard problems
- Athletes train from light to heavy weights
- Musicians practice from simple to complex pieces

Our agent should:
- Solve with easy verification first
- Gradually face stricter standards
- Build capability and confidence progressively

**This is not just an optimization—it's a paradigm shift in how we think about AI agent evaluation.**

---

**Document Status**: Complete
**Next Action**: Review and approve for implementation
**Estimated Implementation Time**: 2-3 weeks
**Expected Impact**: High (60-80% success rate vs 0% baseline)

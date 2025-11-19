# Cross-Validation Architecture Analysis
## Integrating Open Source Models (CodeQwen3-32B) with GPT-OSS Agent

**Date:** 2025-11-19
**Context:** Enhance low-reasoning solution generation with open source cross-validation
**Objective:** Complement asymmetric reasoning architecture with independent validation layer

---

## Executive Summary

The current agent_gpt_oss.py uses asymmetric reasoning where **only low reasoning works for initial solution generation** due to truncation issues with medium/high reasoning. This creates a quality gap that cross-validation with open source models (like CodeQwen3-32B) can address.

**Key Challenge:** Low reasoning generation is fast but may produce lower-quality initial solutions. High reasoning verification catches errors but only after solution generation.

**Proposed Solution:** Integrate open source models as a cross-validation layer to improve solution quality without incurring the cost/truncation penalties of high reasoning generation.

---

## Current Architecture Analysis

### Existing Workflow
```
┌─────────────────────────────────────────────────────────────┐
│ Phase 1: Initial Exploration (init_explorations)            │
│   1. Generate initial solution (low reasoning)              │
│   2. Self-improvement (high reasoning) ←─ proactive errors  │
│   3. Verify solution (high reasoning) ←─ rigorous checking  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 2: Iteration Loop (30 iterations max)                 │
│   1. If verification fails:                                 │
│      - Apply correction_prompt with bug_report              │
│      - (Optional) Use translation layer if asymmetric       │
│      - Generate corrected solution (low reasoning)          │
│   2. Verify corrected solution (high reasoning)             │
│   3. Track scores, detect stuck patterns, validate answers  │
│   4. Exit if: 5 consecutive passes OR 10 consecutive fails  │
└─────────────────────────────────────────────────────────────┘
```

### Key Components
1. **Reasoning Levels:**
   - `SOLUTION_REASONING_EFFORT = "low"` - Fast, prevents truncation
   - `SELF_IMPROVEMENT_REASONING_EFFORT = "high"` - Proactive error detection
   - `VERIFICATION_REASONING_EFFORT = "high"` - Rigorous checking

2. **Translation Layer:** Converts high-reasoning verification feedback to low-reasoning-compatible guidance

3. **Safeguards:**
   - `verify_solution_safe()` - Timeout, retry, fallback mechanisms
   - Stuck pattern detection
   - Answer validation (prevents unjustified narrowing)

4. **Exploration Modes:**
   - BFS: `num_initial_attempts` generates N diverse solutions, picks best
   - MCTS: Tree-based strategy exploration with UCB1 selection
   - Proof Sketch: outline → verify structure → expand → verify math

---

## Architectural Proposals

### Proposal 1: Post-Generation Validation Layer
**Pattern:** Sequential validation after low-reasoning generation, before high-reasoning verification

```
┌──────────────────────────────────────────────────────────────────┐
│ Enhanced Workflow with Cross-Validation                          │
│                                                                   │
│ 1. Generate solution (low reasoning, GPT-OSS)                    │
│                    ↓                                              │
│ 2. Cross-validate (CodeQwen3-32B) ←── NEW LAYER                  │
│    - Check mathematical correctness                              │
│    - Identify potential errors                                   │
│    - Score confidence (0-100)                                    │
│                    ↓                                              │
│ 3. Decision Gate:                                                │
│    - If confidence > threshold (e.g., 70): Proceed to Phase 4    │
│    - If confidence < threshold: Generate alternative OR apply fix│
│                    ↓                                              │
│ 4. Self-improvement (high reasoning, GPT-OSS)                    │
│                    ↓                                              │
│ 5. Final verification (high reasoning, GPT-OSS)                  │
└──────────────────────────────────────────────────────────────────┘
```

#### Integration Points
- **Location:** Between initial generation and self-improvement in `init_explorations()`
- **Function:** `cross_validate_solution(problem_statement, solution, oss_model_config)`

#### Pros
- ✅ Catches errors early, before expensive high-reasoning verification
- ✅ Reduces wasted verification cycles on obviously flawed solutions
- ✅ Maintains existing workflow structure (minimal disruption)
- ✅ Can be toggled on/off via flag
- ✅ Independent model provides unbiased validation

#### Cons
- ❌ Adds latency to each iteration (OSS model inference time)
- ❌ May create conflicting feedback if OSS model disagrees with GPT-OSS
- ❌ Requires careful threshold tuning to avoid false rejections
- ❌ No diversity benefit (single-path validation)

#### Configuration Schema
```python
# Environment variables
OSS_VALIDATOR_API_URL = os.getenv("OSS_VALIDATOR_API_URL", "http://localhost:8000/v1/chat/completions")
OSS_VALIDATOR_MODEL = os.getenv("OSS_VALIDATOR_MODEL", "codeqwen3-32b")
OSS_VALIDATOR_ENABLED = os.getenv("OSS_VALIDATOR_ENABLED", "false").lower() == "true"
OSS_VALIDATOR_CONFIDENCE_THRESHOLD = float(os.getenv("OSS_VALIDATOR_CONFIDENCE_THRESHOLD", "70"))
OSS_VALIDATOR_MAX_RETRIES = int(os.getenv("OSS_VALIDATOR_MAX_RETRIES", "2"))

# CLI arguments
parser.add_argument('--use-oss-validator', action='store_true',
                   help='Enable OSS model cross-validation layer')
parser.add_argument('--oss-validator-threshold', type=float, default=70,
                   help='Confidence threshold for OSS validator (0-100)')
```

#### State Management
```python
# Memory additions
memory = {
    # ... existing fields ...
    "cross_validation_results": [],  # List of {iteration, confidence, feedback}
    "oss_validator_config": {
        "model": OSS_VALIDATOR_MODEL,
        "threshold": OSS_VALIDATOR_CONFIDENCE_THRESHOLD,
        "enabled": OSS_VALIDATOR_ENABLED
    }
}
```

---

### Proposal 2: Parallel Ensemble Validation
**Pattern:** Generate solutions in parallel using both GPT-OSS and OSS models, then ensemble vote

```
┌──────────────────────────────────────────────────────────────────┐
│ Parallel Generation + Ensemble Decision                          │
│                                                                   │
│         ┌─────────────────────┬──────────────────────┐           │
│         │                     │                      │           │
│    GPT-OSS (low)         CodeQwen3-32B        (Optional) Qwen3   │
│         │                     │                      │           │
│    Solution A           Solution B           Solution C          │
│         │                     │                      │           │
│         └─────────────────────┴──────────────────────┘           │
│                              ↓                                    │
│                    Ensemble Voting Layer                          │
│                    - Compare solutions                            │
│                    - Identify consensus                           │
│                    - Merge best elements                          │
│                              ↓                                    │
│                    Best Solution Selected                         │
│                              ↓                                    │
│              Self-improvement + Verification                      │
└──────────────────────────────────────────────────────────────────┘
```

#### Integration Points
- **Location:** Replace `init_explorations()` with `ensemble_explorations()`
- **Functions:**
  - `generate_parallel_solutions(problem, models_config)`
  - `ensemble_vote(solutions, voting_strategy)`
  - `merge_solution_elements(solutions, consensus_map)`

#### Pros
- ✅ Maximum diversity through independent models
- ✅ Cross-validation is implicit (models check each other)
- ✅ Can identify consensus areas vs disagreements
- ✅ Potential for solution merging (take best parts from each)
- ✅ Embarrassingly parallel (minimal latency if concurrent)

#### Cons
- ❌ Significantly more complex implementation
- ❌ Requires sophisticated voting/merging logic
- ❌ Higher computational cost (multiple model inferences)
- ❌ Disagreements may be hard to resolve algorithmically
- ❌ May confuse the agent if merged solution is incoherent

#### Configuration Schema
```python
# Ensemble configuration
ENSEMBLE_MODELS = [
    {
        "name": "gpt_oss",
        "api_url": os.getenv("GPT_OSS_API_URL", "http://localhost:30000/v1/chat/completions"),
        "reasoning_effort": "low",
        "weight": 1.0  # Voting weight
    },
    {
        "name": "codeqwen3_32b",
        "api_url": os.getenv("CODEQWEN_API_URL", "http://localhost:8000/v1/chat/completions"),
        "reasoning_effort": "medium",
        "weight": 0.8
    }
]

ENSEMBLE_VOTING_STRATEGY = os.getenv("ENSEMBLE_VOTING_STRATEGY", "consensus")
# Options: "consensus" (must agree), "weighted" (vote by weight), "best_score" (pick highest)

# CLI
parser.add_argument('--use-ensemble', action='store_true',
                   help='Use ensemble of multiple models for generation')
parser.add_argument('--ensemble-voting', choices=['consensus', 'weighted', 'best_score'],
                   default='best_score',
                   help='Ensemble voting strategy')
```

#### State Management
```python
memory = {
    # ... existing ...
    "ensemble_solutions": [
        {
            "iteration": 0,
            "model": "gpt_oss",
            "solution": "...",
            "score": 45.2,
            "selected": True
        },
        {
            "iteration": 0,
            "model": "codeqwen3_32b",
            "solution": "...",
            "score": 38.1,
            "selected": False
        }
    ]
}
```

---

### Proposal 3: Two-Stage Verification (Light → Heavy)
**Pattern:** OSS model does cheap preliminary verification, GPT-OSS high-reasoning for final check

```
┌──────────────────────────────────────────────────────────────────┐
│ Two-Stage Verification Architecture                              │
│                                                                   │
│ 1. Generate solution (low reasoning, GPT-OSS)                    │
│                    ↓                                              │
│ 2. Light verification (CodeQwen3-32B) ←── Fast preliminary check │
│    - Basic correctness                                           │
│    - Format validation                                           │
│    - Obvious error detection                                     │
│                    ↓                                              │
│ 3. Decision Gate:                                                │
│    - If passes light verification: Proceed to Phase 4            │
│    - If fails: SKIP expensive heavy verification, go to fix      │
│                    ↓                                              │
│ 4. Heavy verification (high reasoning, GPT-OSS) ←── Final check  │
│    - Rigorous mathematical proof checking                        │
│    - Deep logical analysis                                       │
│                    ↓                                              │
│ 5. If fails: Apply correction and loop                           │
└──────────────────────────────────────────────────────────────────┘
```

#### Integration Points
- **Location:** Modify `verify_solution_safe()` to add preliminary stage
- **Function:** `light_verification(problem, solution, oss_config)`

#### Pros
- ✅ Reduces expensive high-reasoning verification calls (cost optimization)
- ✅ Catches obvious errors fast (efficiency)
- ✅ Maintains high-quality final verification
- ✅ Easy to implement (add one function call)
- ✅ Backward compatible (can disable light verification)

#### Cons
- ❌ May miss subtle errors that OSS model doesn't catch
- ❌ Still sequential (adds latency)
- ❌ Threshold tuning required (false positives/negatives)
- ❌ Doesn't improve solution generation quality directly

#### Configuration Schema
```python
# Two-stage verification config
LIGHT_VERIFICATION_ENABLED = os.getenv("LIGHT_VERIFICATION_ENABLED", "false").lower() == "true"
LIGHT_VERIFICATION_MODEL = os.getenv("LIGHT_VERIFICATION_MODEL", "codeqwen3-32b")
LIGHT_VERIFICATION_TIMEOUT = int(os.getenv("LIGHT_VERIFICATION_TIMEOUT", "60"))  # 1 min

# CLI
parser.add_argument('--use-light-verification', action='store_true',
                   help='Enable fast OSS model preliminary verification before heavy verification')
```

#### State Management
```python
memory = {
    # ... existing ...
    "verification_stages": [
        {
            "iteration": 0,
            "light_verification": {"passed": True, "time": 12.3, "issues": []},
            "heavy_verification": {"passed": False, "time": 145.2, "issues": ["..."]}
        }
    ]
}
```

---

### Proposal 4: Guided Generation (OSS Model as Advisor)
**Pattern:** OSS model generates hints/guidance, GPT-OSS uses hints to improve generation

```
┌──────────────────────────────────────────────────────────────────┐
│ Guided Generation with OSS Advisor                               │
│                                                                   │
│ 1. Analyze problem (CodeQwen3-32B)                               │
│    - Identify proof strategy hints                               │
│    - Suggest key lemmas/techniques                               │
│    - Highlight potential pitfalls                                │
│                    ↓                                              │
│ 2. Generate solution with hints (low reasoning, GPT-OSS)         │
│    - Use OSS-generated guidance as additional prompts            │
│    - Incorporate suggested techniques                            │
│                    ↓                                              │
│ 3. Self-improvement (high reasoning, GPT-OSS)                    │
│                    ↓                                              │
│ 4. Verification (high reasoning, GPT-OSS)                        │
└──────────────────────────────────────────────────────────────────┘
```

#### Integration Points
- **Location:** Before `init_explorations()`, generate guidance
- **Function:** `generate_oss_guidance(problem_statement, oss_config)`

#### Pros
- ✅ Improves generation quality without changing reasoning level
- ✅ Leverages OSS model's strengths for strategic thinking
- ✅ Works well with existing prompt architecture
- ✅ Can be combined with other proposals
- ✅ Minimal disruption to workflow

#### Cons
- ❌ OSS model may suggest wrong strategies (misleading guidance)
- ❌ Adds latency at start of each run
- ❌ GPT-OSS may ignore or misinterpret hints
- ❌ Harder to debug when hints lead to failures

#### Configuration Schema
```python
# Guided generation config
OSS_GUIDANCE_ENABLED = os.getenv("OSS_GUIDANCE_ENABLED", "false").lower() == "true"
OSS_GUIDANCE_MODEL = os.getenv("OSS_GUIDANCE_MODEL", "codeqwen3-32b")
OSS_GUIDANCE_DEPTH = os.getenv("OSS_GUIDANCE_DEPTH", "strategy_only")
# Options: "strategy_only", "strategy_and_lemmas", "full_outline"

# CLI
parser.add_argument('--use-oss-guidance', action='store_true',
                   help='Use OSS model to generate strategic guidance before solution generation')
parser.add_argument('--oss-guidance-depth',
                   choices=['strategy_only', 'strategy_and_lemmas', 'full_outline'],
                   default='strategy_only',
                   help='Depth of OSS guidance (more depth = more influence)')
```

#### State Management
```python
memory = {
    # ... existing ...
    "oss_guidance": {
        "generated_at": "2025-11-19T10:30:00",
        "strategy_hints": ["Use strong induction", "Consider extremal principle"],
        "key_lemmas": ["Prove intermediate value theorem first"],
        "pitfalls": ["Watch for boundary cases when n=1"],
        "used_in_generation": True
    }
}
```

---

### Proposal 5: Hybrid MCTS with Cross-Validation Nodes
**Pattern:** Extend MCTS to include OSS model validation at tree nodes

```
┌──────────────────────────────────────────────────────────────────┐
│ MCTS Tree with Cross-Validation Integration                      │
│                                                                   │
│                        Root                                       │
│                         │                                         │
│        ┌────────────────┼────────────────┐                        │
│   Strategy A      Strategy B       Strategy C                    │
│        │               │                 │                        │
│   [Generate]      [Generate]        [Generate]                   │
│        │               │                 │                        │
│   [OSS Validate] [OSS Validate]  [OSS Validate] ←── NEW          │
│        │               │                 │                        │
│   Score: 65        Score: 82        Score: 45                    │
│        │               │                 │                        │
│   (Low UCB1)      (High UCB1) ←─ Selected                        │
│                        │                                          │
│                   [Refine B1]  [Refine B2]                        │
│                        │             │                            │
│                   [Generate]    [Generate]                        │
│                        │             │                            │
│                   [OSS Val]     [OSS Val]                         │
│                        │             │                            │
│                   Score: 88     Score: 75                         │
│                        │                                          │
│                   [GPT-OSS High Verification] ←── Final           │
└──────────────────────────────────────────────────────────────────┘
```

#### Integration Points
- **Location:** Modify `mcts_bfs.py` to add cross-validation in simulation step
- **Function:** Extend `MCTSNode.update()` to include OSS validation scores

#### Pros
- ✅ Combines MCTS strategy exploration with OSS validation
- ✅ OSS scores guide tree search (prune bad strategies early)
- ✅ Reduces wasted GPT-OSS verification on low-score nodes
- ✅ Natural fit for existing MCTS architecture
- ✅ Can validate multiple strategies in parallel

#### Cons
- ❌ Most complex implementation (requires MCTS refactoring)
- ❌ Only applicable when using MCTS mode
- ❌ May over-rely on OSS model's scoring accuracy
- ❌ Debugging is harder (nested tree + cross-validation)

#### Configuration Schema
```python
# MCTS cross-validation config
MCTS_OSS_VALIDATION_ENABLED = os.getenv("MCTS_OSS_VALIDATION_ENABLED", "false").lower() == "true"
MCTS_OSS_VALIDATION_THRESHOLD = float(os.getenv("MCTS_OSS_VALIDATION_THRESHOLD", "60"))
MCTS_OSS_SCORE_WEIGHT = float(os.getenv("MCTS_OSS_SCORE_WEIGHT", "0.5"))
# Combined score = (1 - weight) * mcts_score + weight * oss_score

# CLI
parser.add_argument('--mcts-use-oss-validation', action='store_true',
                   help='Integrate OSS model validation into MCTS tree scoring')
parser.add_argument('--mcts-oss-weight', type=float, default=0.5,
                   help='Weight for OSS validation scores in MCTS (0-1)')
```

#### State Management
```python
# Extend MCTSNode class
class MCTSNode:
    def __init__(self, strategy, parent=None):
        # ... existing ...
        self.oss_validation_scores = []  # Track OSS scores
        self.avg_oss_score = 0.0

    def combined_score(self, oss_weight=0.5):
        """Calculate combined MCTS + OSS score"""
        mcts_score = self.avg_score()
        oss_score = self.avg_oss_score
        return (1 - oss_weight) * mcts_score + oss_weight * oss_score
```

---

## Recommended Approach

### Primary Recommendation: **Proposal 1 (Post-Generation Validation Layer)**

**Rationale:**
1. **Minimal Disruption:** Integrates cleanly into existing workflow
2. **Clear Value Proposition:** Catches errors before expensive verification
3. **Easy to Implement:** Single function addition, ~200 lines of code
4. **Toggleable:** Can be enabled/disabled via flag for A/B testing
5. **Immediate Impact:** Reduces wasted verification cycles

**Implementation Priority:** HIGH
**Estimated Effort:** 2-3 days
**Risk Level:** LOW

### Secondary Recommendation: **Proposal 4 (Guided Generation)**

**Rationale:**
1. **Complementary to Proposal 1:** Can be combined for maximum effect
2. **Improves Root Cause:** Enhances generation quality vs just validation
3. **Leverages OSS Strengths:** Strategic thinking without full solution
4. **Low Risk:** Hints are advisory, not mandatory

**Implementation Priority:** MEDIUM
**Estimated Effort:** 2-3 days
**Risk Level:** LOW-MEDIUM

### Experimental Recommendation: **Proposal 5 (MCTS + Cross-Validation)**

**Rationale:**
1. **Synergistic with MCTS:** Natural fit for tree-based exploration
2. **Advanced Use Case:** For users already using `--use-mcts` flag
3. **Research Value:** Novel architecture for mathematical reasoning

**Implementation Priority:** LOW (after validating Proposal 1)
**Estimated Effort:** 5-7 days
**Risk Level:** MEDIUM-HIGH

---

## Implementation Roadmap

### Phase 1: Post-Generation Validation (Proposal 1)
**Week 1-2**

1. Create `oss_validator.py` module with:
   - `cross_validate_solution()` - Main validation function
   - `build_validation_prompt()` - Construct validation prompts
   - `parse_validation_response()` - Extract confidence + feedback
   - `OSS_API_client()` - Handle OSS model API calls

2. Modify `agent_gpt_oss.py`:
   - Add OSS validation call in `init_explorations()` after line 1204
   - Implement decision gate based on confidence threshold
   - Add CLI arguments and environment variable support
   - Update `save_memory()` to track cross-validation results

3. Testing:
   - Unit tests for validation prompt construction
   - Integration tests with mock OSS API
   - End-to-end tests on IMO benchmark problems
   - Performance benchmarking (latency impact)

### Phase 2: Guided Generation (Proposal 4)
**Week 3-4**

1. Extend `oss_validator.py`:
   - `generate_oss_guidance()` - Generate strategic hints
   - `parse_guidance_response()` - Extract structured hints
   - `integrate_guidance_into_prompts()` - Merge into other_prompts

2. Modify `agent_gpt_oss.py`:
   - Add guidance generation before `init_explorations()`
   - Append guidance to `other_prompts` parameter
   - Track guidance usage in memory

3. Testing:
   - Compare success rates with/without guidance
   - Analyze cases where guidance helped vs hindered
   - Measure iteration count reduction

### Phase 3: MCTS Integration (Proposal 5)
**Week 5-6 (Optional)**

1. Modify `mcts_bfs.py`:
   - Add `oss_validation_score` field to `MCTSNode`
   - Update `simulate()` to call OSS validator
   - Modify `ucb1()` to incorporate OSS scores
   - Add combined scoring function

2. Testing:
   - MCTS tree visualization with OSS scores
   - Compare MCTS performance with/without OSS validation
   - Analyze pruning effectiveness

---

## API Design Specifications

### Core API: `oss_validator.py`

```python
"""
OSS Model Cross-Validation Module for GPT-OSS Agent

Provides validation, scoring, and guidance generation using open source
mathematical reasoning models (e.g., CodeQwen3-32B, Qwen2.5-Math).
"""

import os
import json
import requests
from typing import Dict, Tuple, Optional, List

# Configuration
OSS_VALIDATOR_API_URL = os.getenv(
    "OSS_VALIDATOR_API_URL",
    "http://localhost:8000/v1/chat/completions"
)
OSS_VALIDATOR_MODEL = os.getenv("OSS_VALIDATOR_MODEL", "codeqwen3-32b")
OSS_VALIDATOR_TIMEOUT = int(os.getenv("OSS_VALIDATOR_TIMEOUT", "120"))
OSS_VALIDATOR_MAX_TOKENS = int(os.getenv("OSS_VALIDATOR_MAX_TOKENS", "4096"))

def cross_validate_solution(
    problem_statement: str,
    solution: str,
    verbose: bool = True
) -> Tuple[float, str, Dict]:
    """
    Cross-validate a solution using OSS model.

    Args:
        problem_statement: The original mathematical problem
        solution: The generated solution to validate
        verbose: Print detailed validation logs

    Returns:
        Tuple of (confidence_score, feedback_text, metadata)
        - confidence_score: 0-100 indicating solution quality
        - feedback_text: Detailed validation feedback
        - metadata: {model, tokens, time, detected_errors}
    """
    if verbose:
        print(f"\n{'='*80}")
        print(f">>>>>>> [OSS VALIDATOR] Starting cross-validation")
        print(f">>>>>>> [OSS VALIDATOR] Model: {OSS_VALIDATOR_MODEL}")
        print(f"{'='*80}\n")

    # Build validation prompt
    validation_prompt = build_validation_prompt(problem_statement, solution)

    # Call OSS model API
    payload = {
        "model": OSS_VALIDATOR_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You are a mathematical reasoning validator. Check solutions for correctness, logical soundness, and completeness."
            },
            {
                "role": "user",
                "content": validation_prompt
            }
        ],
        "temperature": 0.1,
        "max_tokens": OSS_VALIDATOR_MAX_TOKENS
    }

    try:
        response = requests.post(
            OSS_VALIDATOR_API_URL,
            json=payload,
            timeout=OSS_VALIDATOR_TIMEOUT
        )
        response.raise_for_status()

        result = response.json()
        validation_text = result['choices'][0]['message']['content']

        # Parse response
        confidence, feedback, errors = parse_validation_response(validation_text)

        metadata = {
            "model": OSS_VALIDATOR_MODEL,
            "tokens": result.get('usage', {}).get('total_tokens', 0),
            "time": response.elapsed.total_seconds(),
            "detected_errors": errors
        }

        if verbose:
            print(f">>>>>>> [OSS VALIDATOR] Confidence: {confidence:.1f}/100")
            print(f">>>>>>> [OSS VALIDATOR] Errors detected: {len(errors)}")
            print(f">>>>>>> [OSS VALIDATOR] Time: {metadata['time']:.2f}s")
            print(f"{'='*80}\n")

        return confidence, feedback, metadata

    except Exception as e:
        if verbose:
            print(f">>>>>>> [OSS VALIDATOR] ERROR: {e}")
        return 0.0, f"Validation failed: {str(e)}", {"error": str(e)}


def build_validation_prompt(problem: str, solution: str) -> str:
    """
    Construct validation prompt for OSS model.

    Returns:
        Formatted prompt string
    """
    return f"""### Task ###
You are validating a mathematical solution for correctness.

### Problem ###
{problem}

### Proposed Solution ###
{solution}

### Your Task ###
Evaluate this solution on the following criteria:

1. **Correctness**: Are all mathematical steps correct?
2. **Completeness**: Does it fully answer the problem?
3. **Logical Soundness**: Is the reasoning valid throughout?
4. **Clarity**: Is the proof clearly explained?

### Output Format ###
CONFIDENCE: [0-100]

ERRORS DETECTED:
- [List each error/gap found, or "None" if solution is correct]

DETAILED FEEDBACK:
[Explain your assessment in 2-3 paragraphs]

RECOMMENDATION: [Accept / Minor Fixes Needed / Major Revision Required / Reject]
"""


def parse_validation_response(text: str) -> Tuple[float, str, List[str]]:
    """
    Parse OSS model validation response.

    Args:
        text: Raw validation response from OSS model

    Returns:
        Tuple of (confidence_score, feedback_text, error_list)
    """
    import re

    # Extract confidence score
    confidence_match = re.search(r'CONFIDENCE:\s*([0-9.]+)', text)
    confidence = float(confidence_match.group(1)) if confidence_match else 50.0

    # Extract errors
    errors = []
    errors_section = re.search(r'ERRORS DETECTED:(.*?)(?:DETAILED FEEDBACK|$)', text, re.DOTALL)
    if errors_section:
        error_text = errors_section.group(1)
        errors = [
            line.strip(' -•*')
            for line in error_text.split('\n')
            if line.strip() and line.strip().lower() not in ['none', 'no errors', '']
        ]

    # Extract detailed feedback
    feedback_match = re.search(r'DETAILED FEEDBACK:(.*?)(?:RECOMMENDATION|$)', text, re.DOTALL)
    feedback = feedback_match.group(1).strip() if feedback_match else text

    return confidence, feedback, errors


def generate_oss_guidance(
    problem_statement: str,
    guidance_depth: str = "strategy_only",
    verbose: bool = True
) -> Dict[str, List[str]]:
    """
    Generate strategic guidance using OSS model.

    Args:
        problem_statement: The mathematical problem
        guidance_depth: "strategy_only", "strategy_and_lemmas", or "full_outline"
        verbose: Print detailed logs

    Returns:
        Dictionary with:
        - strategy_hints: List of suggested proof strategies
        - key_lemmas: List of intermediate results to prove (if depth > strategy_only)
        - pitfalls: List of common mistakes to avoid
    """
    if verbose:
        print(f"\n{'='*80}")
        print(f">>>>>>> [OSS GUIDANCE] Generating strategic guidance")
        print(f">>>>>>> [OSS GUIDANCE] Depth: {guidance_depth}")
        print(f"{'='*80}\n")

    guidance_prompt = build_guidance_prompt(problem_statement, guidance_depth)

    payload = {
        "model": OSS_VALIDATOR_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You are a mathematical strategist providing high-level proof guidance."
            },
            {
                "role": "user",
                "content": guidance_prompt
            }
        ],
        "temperature": 0.3,  # Slightly higher for creativity
        "max_tokens": 2048
    }

    try:
        response = requests.post(
            OSS_VALIDATOR_API_URL,
            json=payload,
            timeout=OSS_VALIDATOR_TIMEOUT
        )
        response.raise_for_status()

        result = response.json()
        guidance_text = result['choices'][0]['message']['content']

        # Parse guidance
        guidance = parse_guidance_response(guidance_text)

        if verbose:
            print(f">>>>>>> [OSS GUIDANCE] Strategies: {len(guidance['strategy_hints'])}")
            print(f">>>>>>> [OSS GUIDANCE] Key lemmas: {len(guidance['key_lemmas'])}")
            print(f">>>>>>> [OSS GUIDANCE] Pitfalls: {len(guidance['pitfalls'])}")
            print(f"{'='*80}\n")

        return guidance

    except Exception as e:
        if verbose:
            print(f">>>>>>> [OSS GUIDANCE] ERROR: {e}")
        return {
            "strategy_hints": [],
            "key_lemmas": [],
            "pitfalls": []
        }


def build_guidance_prompt(problem: str, depth: str) -> str:
    """Construct guidance generation prompt."""

    base_prompt = f"""### Problem ###
{problem}

### Your Task ###
Provide strategic guidance for solving this problem. DO NOT write the full solution.
"""

    if depth == "strategy_only":
        return base_prompt + """
### Output Format ###
SUGGESTED STRATEGIES:
1. [Strategy name]: [One sentence description]
2. [Strategy name]: [One sentence description]
...

PITFALLS TO AVOID:
- [Common mistake 1]
- [Common mistake 2]
"""

    elif depth == "strategy_and_lemmas":
        return base_prompt + """
### Output Format ###
SUGGESTED STRATEGIES:
1. [Strategy name]: [One sentence description]
2. [Strategy name]: [One sentence description]

KEY LEMMAS TO PROVE:
- [Intermediate result 1]
- [Intermediate result 2]

PITFALLS TO AVOID:
- [Common mistake 1]
- [Common mistake 2]
"""

    else:  # full_outline
        return base_prompt + """
### Output Format ###
SUGGESTED STRATEGY: [Main approach]

PROOF OUTLINE:
Step 1: [High-level step]
Step 2: [High-level step]
...

KEY LEMMAS:
- [Lemma 1]
- [Lemma 2]

PITFALLS:
- [Mistake 1]
- [Mistake 2]
"""


def parse_guidance_response(text: str) -> Dict[str, List[str]]:
    """Parse OSS guidance response into structured format."""
    import re

    guidance = {
        "strategy_hints": [],
        "key_lemmas": [],
        "pitfalls": []
    }

    # Extract strategies
    strategies_section = re.search(r'SUGGESTED STRATEG(?:IES|Y):(.*?)(?:KEY LEMMAS|PITFALLS|$)', text, re.DOTALL)
    if strategies_section:
        strategy_text = strategies_section.group(1)
        strategies = [
            line.strip(' -•*0-9.')
            for line in strategy_text.split('\n')
            if line.strip() and len(line.strip()) > 10
        ]
        guidance['strategy_hints'] = strategies[:5]  # Top 5

    # Extract lemmas
    lemmas_section = re.search(r'KEY LEMMAS:(.*?)(?:PITFALLS|$)', text, re.DOTALL)
    if lemmas_section:
        lemma_text = lemmas_section.group(1)
        lemmas = [
            line.strip(' -•*0-9.')
            for line in lemma_text.split('\n')
            if line.strip() and len(line.strip()) > 10
        ]
        guidance['key_lemmas'] = lemmas

    # Extract pitfalls
    pitfalls_section = re.search(r'PITFALLS:(.*?)$', text, re.DOTALL)
    if pitfalls_section:
        pitfall_text = pitfalls_section.group(1)
        pitfalls = [
            line.strip(' -•*0-9.')
            for line in pitfall_text.split('\n')
            if line.strip() and len(line.strip()) > 10
        ]
        guidance['pitfalls'] = pitfalls

    return guidance
```

---

## Fallback Strategies

### When Cross-Validation Disagrees with Primary Solution

**Scenario 1: OSS validator rejects low-confidence solution**
```
GPT-OSS (low): Generates solution
    ↓
OSS Validator: Confidence = 35% (below threshold 70%)
    ↓
Decision: Reject and regenerate
    ↓
Action: Generate alternative solution OR apply OSS feedback as correction
```

**Fallback Logic:**
```python
def handle_low_confidence_validation(
    confidence: float,
    threshold: float,
    oss_feedback: str,
    max_retries: int = 2
) -> str:
    """
    Handle case where OSS validator gives low confidence.

    Strategies:
    1. If retries remaining: Regenerate with OSS feedback as guidance
    2. If no retries: Proceed to GPT-OSS self-improvement anyway
    3. Track pattern: If consistently low confidence, escalate reasoning
    """
    if confidence < threshold:
        if retries_remaining > 0:
            print(f">>>>>>> [OSS VALIDATOR] Low confidence ({confidence:.1f}), regenerating...")
            # Append OSS feedback to prompts
            other_prompts.append(f"Previous attempt had issues: {oss_feedback}")
            return "regenerate"
        else:
            print(f">>>>>>> [OSS VALIDATOR] Max retries reached, proceeding anyway")
            return "proceed"
    else:
        return "proceed"
```

**Scenario 2: OSS validator disagrees with GPT-OSS verification**
```
GPT-OSS Verification: "Yes - solution is correct"
    ↓
OSS Validator: Confidence = 45%, errors detected
    ↓
Decision: CONFLICT - which to trust?
```

**Conflict Resolution:**
```python
def resolve_validation_conflict(
    gpt_oss_result: str,
    oss_confidence: float,
    oss_errors: List[str],
    tie_breaker: str = "gpt_oss_wins"
) -> str:
    """
    Resolve disagreement between validators.

    Tie-breaker strategies:
    - "gpt_oss_wins": Trust GPT-OSS high-reasoning verification (default)
    - "oss_wins": Trust OSS validator
    - "conservative": Reject if either validator rejects
    - "optimistic": Accept if either validator accepts
    """
    gpt_oss_accepts = "yes" in gpt_oss_result.lower()
    oss_accepts = oss_confidence >= 70

    if gpt_oss_accepts == oss_accepts:
        # No conflict
        return "pass" if gpt_oss_accepts else "fail"

    # Conflict - apply tie-breaker
    if tie_breaker == "gpt_oss_wins":
        return "pass" if gpt_oss_accepts else "fail"
    elif tie_breaker == "oss_wins":
        return "pass" if oss_accepts else "fail"
    elif tie_breaker == "conservative":
        return "fail"  # Reject if any doubt
    elif tie_breaker == "optimistic":
        return "pass"  # Accept if any approval
    else:
        # Default to GPT-OSS
        return "pass" if gpt_oss_accepts else "fail"
```

**Scenario 3: OSS validator timeout or error**
```
OSS Validator: Request timeout after 120s
    ↓
Decision: Graceful degradation
    ↓
Action: Log warning and skip OSS validation
```

**Error Handling:**
```python
def safe_cross_validate(
    problem: str,
    solution: str,
    timeout: int = 120,
    fallback_on_error: bool = True
) -> Tuple[float, str, Dict]:
    """
    Safely call OSS validator with error handling.

    Returns:
    - On success: (confidence, feedback, metadata)
    - On error: (50.0, "Validation unavailable", {"error": ...})
    """
    try:
        return cross_validate_solution(problem, solution, verbose=True)
    except requests.Timeout:
        print(f">>>>>>> [OSS VALIDATOR] Timeout after {timeout}s, skipping")
        return 50.0, "Validation timeout", {"error": "timeout"}
    except Exception as e:
        print(f">>>>>>> [OSS VALIDATOR] Error: {e}, skipping")
        if fallback_on_error:
            return 50.0, "Validation unavailable", {"error": str(e)}
        else:
            raise
```

---

## Performance Expectations

### Cost Analysis (per iteration)

**Baseline (no cross-validation):**
- Low reasoning generation: ~$0.50
- High reasoning verification: ~$3.00
- **Total per iteration: ~$3.50**

**With OSS Post-Generation Validation (Proposal 1):**
- Low reasoning generation: ~$0.50
- OSS validation: ~$0.05 (local inference) or ~$0.15 (API)
- High reasoning verification: ~$3.00
- **Total per iteration: ~$3.65**
- **Overhead: +4.3%**

**Potential Savings:**
- If OSS catches error early: Skip wasted high-reasoning verification
- Estimated savings: 1-2 iterations per problem
- **Net savings: ~$3.50 - $7.00 per problem**

### Latency Analysis

**Baseline (no cross-validation):**
- Low reasoning generation: ~20s
- High reasoning verification: ~120s
- **Total: ~140s per iteration**

**With OSS Validation:**
- Low reasoning generation: ~20s
- OSS validation: ~15s (local) or ~30s (API)
- High reasoning verification: ~120s
- **Total: ~155s - ~170s per iteration**
- **Overhead: +10.7% - +21.4%**

**Parallel Optimization:**
If OSS validation runs in parallel with preparation for next step:
- **Effective overhead: ~5s**

### Success Rate Impact (Projected)

**Baseline (low/high asymmetric):**
- Success rate: 40-60% (current)
- Average iterations to success: 8-12
- **Cost per success: ~$28 - $42**

**With OSS Cross-Validation (Proposal 1):**
- Success rate: 50-70% (projected +10-15%)
- Average iterations to success: 6-9 (fewer wasted corrections)
- **Cost per success: ~$22 - $33**
- **ROI: 20-30% cost reduction**

**With OSS Guidance + Validation (Proposals 1 + 4):**
- Success rate: 55-75% (projected +15-20%)
- Average iterations to success: 5-8
- **Cost per success: ~$18 - $29**
- **ROI: 30-40% cost reduction**

---

## Testing Strategy

### Unit Tests
```python
# test_oss_validator.py

def test_validation_prompt_construction():
    """Test that validation prompts are well-formed."""
    problem = "Prove that 2+2=4"
    solution = "By definition of addition..."
    prompt = build_validation_prompt(problem, solution)

    assert "### Problem ###" in prompt
    assert problem in prompt
    assert solution in prompt
    assert "CONFIDENCE:" in prompt

def test_parse_validation_response():
    """Test parsing of OSS model responses."""
    response = """
    CONFIDENCE: 85.5

    ERRORS DETECTED:
    - Minor notation issue in step 3
    - Missing edge case for n=0

    DETAILED FEEDBACK:
    The solution is largely correct...

    RECOMMENDATION: Minor Fixes Needed
    """

    confidence, feedback, errors = parse_validation_response(response)

    assert confidence == 85.5
    assert len(errors) == 2
    assert "notation issue" in errors[0]

def test_guidance_generation():
    """Test strategic guidance generation."""
    problem = "Find all k such that..."
    guidance = generate_oss_guidance(problem, "strategy_only", verbose=False)

    assert "strategy_hints" in guidance
    assert "pitfalls" in guidance
    assert isinstance(guidance["strategy_hints"], list)
```

### Integration Tests
```python
# test_integration.py

def test_validation_in_workflow():
    """Test that validation integrates correctly into agent workflow."""
    problem = read_file_content("problems/imo01.txt")

    # Mock OSS validator to return low confidence
    with mock.patch('oss_validator.cross_validate_solution') as mock_validate:
        mock_validate.return_value = (35.0, "Solution incomplete", {})

        # Run agent with validation enabled
        solution = agent(
            problem,
            use_oss_validator=True,
            oss_validator_threshold=70
        )

        # Should trigger regeneration due to low confidence
        assert mock_validate.call_count >= 2  # Initial + retry

def test_conflict_resolution():
    """Test behavior when GPT-OSS and OSS validator disagree."""
    problem = "..."
    solution = "..."

    # Mock: GPT-OSS says "yes", OSS says low confidence
    with mock.patch('agent_gpt_oss.verify_solution') as mock_gpt:
        with mock.patch('oss_validator.cross_validate_solution') as mock_oss:
            mock_gpt.return_value = ("", "Yes")
            mock_oss.return_value = (45.0, "Issues found", {})

            # Test tie-breaker logic
            result = resolve_validation_conflict(
                "Yes", 45.0, ["error1"],
                tie_breaker="gpt_oss_wins"
            )
            assert result == "pass"

            result = resolve_validation_conflict(
                "Yes", 45.0, ["error1"],
                tie_breaker="conservative"
            )
            assert result == "fail"
```

### End-to-End Tests
```bash
# Run agent with OSS validation on IMO benchmark
python code/agent_gpt_oss.py \
    --benchmark proofbench \
    --level IMO-easy \
    --benchmark-index 0 \
    --use-oss-validator \
    --oss-validator-threshold 70 \
    --log test_oss_validation.log

# Compare success rates
python scripts/compare_success_rates.py \
    baseline_logs/ \
    oss_validation_logs/
```

---

## Monitoring and Metrics

### Key Metrics to Track

1. **Validation Accuracy:**
   - OSS confidence vs GPT-OSS verification agreement rate
   - False positive rate (OSS accepts, GPT-OSS rejects)
   - False negative rate (OSS rejects, GPT-OSS accepts)

2. **Performance Metrics:**
   - Average OSS validation latency
   - Percentage of solutions passing OSS validation
   - Iteration count reduction (with vs without OSS)

3. **Cost Metrics:**
   - OSS validation cost per call
   - Total cost per problem (with vs without OSS)
   - Cost per successful solution

4. **Quality Metrics:**
   - Success rate improvement
   - Average confidence scores for successful solutions
   - Percentage of early error detection (caught by OSS before GPT-OSS)

### Logging Format
```python
# Enhanced logging for cross-validation
print(f">>>>>>> [OSS VALIDATOR] ==========================================")
print(f">>>>>>> [OSS VALIDATOR] Iteration: {iteration}")
print(f">>>>>>> [OSS VALIDATOR] Confidence: {confidence:.1f}/100")
print(f">>>>>>> [OSS VALIDATOR] Errors detected: {len(errors)}")
print(f">>>>>>> [OSS VALIDATOR] Time: {elapsed:.2f}s")
print(f">>>>>>> [OSS VALIDATOR] Passed threshold ({threshold}): {confidence >= threshold}")
print(f">>>>>>> [OSS VALIDATOR] ==========================================")
```

### Memory State Tracking
```python
# Cross-validation history in memory
memory = {
    # ... existing fields ...
    "cross_validation_history": [
        {
            "iteration": 0,
            "oss_confidence": 35.2,
            "oss_errors": ["Missing case n=1", "Unclear induction step"],
            "oss_time": 12.3,
            "gpt_oss_verification": "No",
            "agreement": True,
            "decision": "regenerate"
        },
        {
            "iteration": 1,
            "oss_confidence": 72.8,
            "oss_errors": [],
            "oss_time": 10.1,
            "gpt_oss_verification": "Yes",
            "agreement": True,
            "decision": "accept"
        }
    ],
    "oss_validation_stats": {
        "total_calls": 2,
        "avg_confidence": 54.0,
        "avg_latency": 11.2,
        "agreement_rate": 1.0,
        "threshold_pass_rate": 0.5
    }
}
```

---

## Summary

This architectural analysis presents five distinct approaches for integrating open source cross-validation into the GPT-OSS agent's asymmetric reasoning architecture:

1. **Post-Generation Validation** - Sequential validation layer (RECOMMENDED)
2. **Parallel Ensemble** - Generate with multiple models and vote
3. **Two-Stage Verification** - Light OSS check before heavy GPT-OSS check
4. **Guided Generation** - OSS provides strategic hints (RECOMMENDED)
5. **MCTS Integration** - Validate MCTS tree nodes with OSS scores

The recommended implementation path is:
1. Start with **Proposal 1 (Post-Generation Validation)** for immediate impact
2. Add **Proposal 4 (Guided Generation)** for complementary benefits
3. Experimentally explore **Proposal 5 (MCTS)** for advanced users

This approach balances implementation complexity, risk, and potential value, while maintaining backward compatibility with the existing agent architecture.

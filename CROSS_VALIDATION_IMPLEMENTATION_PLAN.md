# Cross-Validation with Open Source Models: Implementation Plan

## Executive Summary

This document provides a detailed implementation plan for integrating cross-validation with open source models (like CodeQwen3-32B) into the `agent_gpt_oss.py` workflow to improve solution quality while maintaining the 17× speed advantage of low reasoning generation.

**Key Strategy**: Use fast open source models as a "sanity check" layer between low-reasoning generation and high-reasoning verification, catching obvious errors early and providing diverse perspectives without sacrificing speed.

---

## 1. Architecture Overview

### 1.1 Current Workflow (agent_gpt_oss.py)

```
┌─────────────────────────────────────────────────────────────┐
│  Current Asymmetric Reasoning Architecture                 │
└─────────────────────────────────────────────────────────────┘

Step 1: GENERATION (Low Reasoning, ~1.3 hours)
  ├─ init_explorations() (lines 1192-1236)
  │  ├─ Initial solution with low reasoning
  │  └─ Self-improvement with HIGH reasoning
  │
Step 2: VERIFICATION (High Reasoning, rigorous)
  ├─ verify_solution_safe() (lines 462-588)
  │  ├─ Uses high reasoning for catching subtle errors
  │  └─ Includes timeout/retry safeguards
  │
Step 3: CORRECTION LOOP (up to 30 iterations)
  └─ Generate corrections (low) → Verify (high) → Repeat
```

### 1.2 Proposed Cross-Validation Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Enhanced Architecture with Open Source Cross-Validation   │
└─────────────────────────────────────────────────────────────┘

Step 1: GENERATION (Low Reasoning, ~1.3 hours)
  └─ Same as current

Step 2: CROSS-VALIDATION (Fast OSS Models, ~5-10 min) ← NEW!
  ├─ Parallel validation by 2-3 open source models
  │  ├─ CodeQwen3-32B (reasoning specialist)
  │  ├─ Qwen2.5-Math-72B (math specialist)
  │  └─ DeepSeek-R1-Distill-Qwen-32B (alternative perspective)
  │
  ├─ Lightweight checks:
  │  ├─ Structural soundness
  │  ├─ Obvious logical errors
  │  ├─ Answer format validation
  │  └─ Confidence scoring
  │
  └─ Early exit conditions:
     ├─ If ALL models agree + high confidence → Skip high verification
     ├─ If ALL models reject → Regenerate immediately
     └─ If models disagree → Proceed to high verification

Step 3: VERIFICATION (High Reasoning, rigorous)
  └─ Same as current (but potentially skipped if CV passes)

Step 4: CORRECTION LOOP
  ├─ Use CV feedback to guide corrections
  └─ Run CV on each correction before high verification
```

---

## 2. Integration Points in Code

### 2.1 Primary Integration Point: Post-Generation Cross-Validation

**Location**: Between solution generation and verification in `init_explorations()`

**File**: `/home/user/IMO25/code/agent_gpt_oss.py`

**Lines**: After line 1226 (after solution generation, before verification)

```python
# CURRENT CODE (lines 1225-1230):
solution = extract_solution(extract_text_from_response(response2))
print(f">>>>>>> Corrected solution:")
print(json.dumps(solution, indent=4))

print(f">>>>>>> Verify the solution.")
verify, good_verify = verify_solution(problem_statement, solution, verbose, verification_reasoning)

# PROPOSED MODIFICATION:
solution = extract_solution(extract_text_from_response(response2))
print(f">>>>>>> Corrected solution:")
print(json.dumps(solution, indent=4))

# NEW: Cross-validation layer
if CROSS_VALIDATION_ENABLED:
    print(f">>>>>>> [CROSS-VALIDATION] Running OSS model validation...")
    cv_result = cross_validate_solution(problem_statement, solution, verbose=True)

    # Early exit based on CV consensus
    if cv_result['consensus'] == 'REJECT' and cv_result['confidence'] > 0.8:
        print(f">>>>>>> [CROSS-VALIDATION] Strong consensus to reject - regenerating...")
        return None, None, None, "No - rejected by cross-validation"

    if cv_result['consensus'] == 'ACCEPT' and cv_result['confidence'] > 0.9:
        print(f">>>>>>> [CROSS-VALIDATION] Strong consensus to accept - skipping high verification")
        verify = cv_result['combined_feedback']
        good_verify = "Yes - accepted by cross-validation"
        return p1, solution, verify, good_verify

print(f">>>>>>> Verify the solution.")
verify, good_verify = verify_solution(problem_statement, solution, verbose, verification_reasoning)
```

### 2.2 Secondary Integration Point: Correction Loop Validation

**Location**: In main agent iteration loop

**File**: `/home/user/IMO25/code/agent_gpt_oss.py`

**Lines**: After line 1695 (after correction generation, before verification)

```python
# CURRENT CODE (lines 1693-1704):
solution = extract_solution(extract_text_from_response(response2))

print(">>>>>>> Corrected solution:")
print(json.dumps(solution, indent=4))

# Validate answer change if solution was corrected
if previous_solution:
    answer_validation = validate_answer_change(previous_solution, solution, i, verbose=True)
    if answer_validation['narrowed']:
        print(f">>>>>>> [ANSWER VALIDATION] ⚠️  Answer narrowing detected")

print(f">>>>>>> Verify the solution.")
verify, good_verify = verify_solution_safe(problem_statement, solution, reasoning_effort=ver_reasoning)

# PROPOSED MODIFICATION:
solution = extract_solution(extract_text_from_response(response2))

print(">>>>>>> Corrected solution:")
print(json.dumps(solution, indent=4))

# NEW: Cross-validation on corrections
if CROSS_VALIDATION_ENABLED and CROSS_VALIDATION_ON_CORRECTIONS:
    cv_result = cross_validate_solution(
        problem_statement, solution,
        previous_feedback=verify,  # Context from previous iteration
        iteration=i,
        verbose=True
    )

    # Use CV to prioritize which corrections to verify deeply
    if cv_result['confidence'] < 0.3:
        print(f">>>>>>> [CROSS-VALIDATION] Low confidence - likely still incorrect")
        # Skip expensive high verification if obviously still wrong
        verify = cv_result['combined_feedback']
        good_verify = "No - cross-validation indicates likely incorrect"
        continue  # Skip to next iteration

# Validate answer change
if previous_solution:
    answer_validation = validate_answer_change(previous_solution, solution, i, verbose=True)

print(f">>>>>>> Verify the solution.")
verify, good_verify = verify_solution_safe(problem_statement, solution, reasoning_effort=ver_reasoning)
```

### 2.3 Configuration Variables

**Location**: After line 54 (in configuration section)

```python
# NEW: Cross-Validation Configuration
CROSS_VALIDATION_ENABLED = os.getenv("GPT_OSS_CROSS_VALIDATION", "false").lower() == "true"
CROSS_VALIDATION_ON_CORRECTIONS = os.getenv("GPT_OSS_CV_ON_CORRECTIONS", "true").lower() == "true"
CROSS_VALIDATION_MODELS = os.getenv("GPT_OSS_CV_MODELS", "codeqwen3,qwen-math,deepseek-r1").split(",")
CROSS_VALIDATION_TIMEOUT = int(os.getenv("GPT_OSS_CV_TIMEOUT", "300"))  # 5 min per model
CROSS_VALIDATION_PARALLEL = os.getenv("GPT_OSS_CV_PARALLEL", "true").lower() == "true"

# Cross-validation API endpoints (can be same server with different model names)
CV_API_URL = os.getenv("GPT_OSS_CV_API_URL", "http://localhost:30001/v1/chat/completions")
CV_API_KEY = os.getenv("GPT_OSS_CV_API_KEY", "")

# Print CV configuration
if CROSS_VALIDATION_ENABLED:
    print(f"[CONFIG] Cross-Validation: ENABLED")
    print(f"[CONFIG] CV Models: {CROSS_VALIDATION_MODELS}")
    print(f"[CONFIG] CV API URL: {CV_API_URL}")
    print(f"[CONFIG] CV Parallel: {CROSS_VALIDATION_PARALLEL}")
    print(f"[CONFIG] CV on Corrections: {CROSS_VALIDATION_ON_CORRECTIONS}")
else:
    print(f"[CONFIG] Cross-Validation: DISABLED")
```

---

## 3. Core Implementation: Cross-Validation Module

### 3.1 New File: `code/cross_validator.py`

Create a dedicated module for cross-validation logic:

```python
"""
Cross-Validation Module for IMO Problem Solving

Integrates open source models to validate solutions before expensive high-reasoning verification.
Provides fast sanity checks, structural validation, and multi-model consensus.
"""

import os
import json
import requests
import concurrent.futures
from typing import Dict, List, Tuple, Optional
from datetime import datetime


class CrossValidator:
    """
    Cross-validation manager for solution quality checks.

    Coordinates multiple open source models to validate solutions with:
    - Parallel execution for speed
    - Consensus-based decision making
    - Confidence scoring
    - Timeout and error handling
    """

    def __init__(self,
                 models: List[str],
                 api_url: str,
                 api_key: str = "",
                 timeout: int = 300,
                 parallel: bool = True):
        """
        Initialize cross-validator.

        Args:
            models: List of model names to use for validation
            api_url: API endpoint for model inference
            api_key: API key (if required)
            timeout: Timeout per model in seconds
            parallel: Whether to run models in parallel
        """
        self.models = models
        self.api_url = api_url
        self.api_key = api_key
        self.timeout = timeout
        self.parallel = parallel

        print(f">>>>>>> [CV] Initialized CrossValidator")
        print(f">>>>>>> [CV] Models: {models}")
        print(f">>>>>>> [CV] Parallel: {parallel}")
        print(f">>>>>>> [CV] Timeout: {timeout}s per model")

    def validate_solution(self,
                         problem_statement: str,
                         solution: str,
                         previous_feedback: Optional[str] = None,
                         iteration: Optional[int] = None,
                         verbose: bool = True) -> Dict:
        """
        Cross-validate a solution using multiple models.

        Args:
            problem_statement: Original problem
            solution: Solution to validate
            previous_feedback: Feedback from previous iteration (optional)
            iteration: Current iteration number (optional)
            verbose: Print detailed logs

        Returns:
            Dict containing:
                - consensus: 'ACCEPT', 'REJECT', 'UNCERTAIN'
                - confidence: 0.0-1.0 confidence score
                - model_results: Individual model results
                - combined_feedback: Aggregated feedback
                - execution_time: Total validation time
        """
        start_time = datetime.now()

        if verbose:
            print(f"\n{'='*80}")
            print(f">>>>>>> [CV] Starting cross-validation")
            print(f">>>>>>> [CV] Models: {len(self.models)}")
            print(f">>>>>>> [CV] Iteration: {iteration if iteration else 'initial'}")
            print(f"{'='*80}\n")

        # Run models in parallel or sequential
        if self.parallel:
            model_results = self._validate_parallel(
                problem_statement, solution, previous_feedback, verbose
            )
        else:
            model_results = self._validate_sequential(
                problem_statement, solution, previous_feedback, verbose
            )

        # Aggregate results
        consensus, confidence = self._compute_consensus(model_results, verbose)
        combined_feedback = self._aggregate_feedback(model_results, verbose)

        execution_time = (datetime.now() - start_time).total_seconds()

        result = {
            'consensus': consensus,
            'confidence': confidence,
            'model_results': model_results,
            'combined_feedback': combined_feedback,
            'execution_time': execution_time,
            'num_models': len(self.models),
            'iteration': iteration
        }

        if verbose:
            print(f"\n{'='*80}")
            print(f">>>>>>> [CV] Cross-validation complete")
            print(f">>>>>>> [CV] Consensus: {consensus}")
            print(f">>>>>>> [CV] Confidence: {confidence:.2f}")
            print(f">>>>>>> [CV] Time: {execution_time:.1f}s")
            print(f"{'='*80}\n")

        return result

    def _validate_parallel(self,
                          problem_statement: str,
                          solution: str,
                          previous_feedback: Optional[str],
                          verbose: bool) -> List[Dict]:
        """Run validation in parallel across all models."""
        print(f">>>>>>> [CV] Running {len(self.models)} models in parallel...")

        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(self.models)) as executor:
            # Submit all validation tasks
            future_to_model = {
                executor.submit(
                    self._validate_with_model,
                    model, problem_statement, solution, previous_feedback, verbose
                ): model
                for model in self.models
            }

            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_model):
                model = future_to_model[future]
                try:
                    result = future.result()
                    results.append(result)
                    if verbose:
                        print(f">>>>>>> [CV] {model}: {result['verdict']} (confidence: {result['confidence']:.2f})")
                except Exception as e:
                    print(f">>>>>>> [CV] ERROR - {model} failed: {e}")
                    # Add failure result
                    results.append({
                        'model': model,
                        'verdict': 'ERROR',
                        'confidence': 0.0,
                        'feedback': f"Model execution failed: {e}",
                        'execution_time': 0.0
                    })

        return results

    def _validate_sequential(self,
                            problem_statement: str,
                            solution: str,
                            previous_feedback: Optional[str],
                            verbose: bool) -> List[Dict]:
        """Run validation sequentially across models."""
        print(f">>>>>>> [CV] Running {len(self.models)} models sequentially...")

        results = []
        for model in self.models:
            try:
                result = self._validate_with_model(
                    model, problem_statement, solution, previous_feedback, verbose
                )
                results.append(result)
                if verbose:
                    print(f">>>>>>> [CV] {model}: {result['verdict']} (confidence: {result['confidence']:.2f})")
            except Exception as e:
                print(f">>>>>>> [CV] ERROR - {model} failed: {e}")
                results.append({
                    'model': model,
                    'verdict': 'ERROR',
                    'confidence': 0.0,
                    'feedback': f"Model execution failed: {e}",
                    'execution_time': 0.0
                })

        return results

    def _validate_with_model(self,
                            model: str,
                            problem_statement: str,
                            solution: str,
                            previous_feedback: Optional[str],
                            verbose: bool) -> Dict:
        """
        Validate solution with a single model.

        Returns:
            Dict with model result including verdict, confidence, feedback
        """
        start_time = datetime.now()

        # Build validation prompt (lightweight, focused on obvious errors)
        prompt = self._build_validation_prompt(
            problem_statement, solution, previous_feedback
        )

        # Call model API
        try:
            response = self._call_model_api(model, prompt)

            # Parse response
            verdict, confidence, feedback = self._parse_validation_response(response)

            execution_time = (datetime.now() - start_time).total_seconds()

            return {
                'model': model,
                'verdict': verdict,  # 'ACCEPT', 'REJECT', 'UNCERTAIN'
                'confidence': confidence,  # 0.0-1.0
                'feedback': feedback,
                'execution_time': execution_time
            }

        except Exception as e:
            raise RuntimeError(f"Model {model} validation failed: {e}")

    def _build_validation_prompt(self,
                                 problem_statement: str,
                                 solution: str,
                                 previous_feedback: Optional[str]) -> str:
        """
        Build lightweight validation prompt for OSS models.

        Key: Keep it simple and focused to maintain speed advantage.
        """
        prompt = f"""You are a mathematical solution reviewer. Your task is to quickly check if a solution has obvious errors.

**IMPORTANT**: This is a FAST sanity check, not a rigorous proof verification. Focus on:
1. **Structural soundness**: Does the solution have a logical flow?
2. **Obvious logical errors**: Are there any clear mathematical mistakes?
3. **Answer format**: Is the final answer clearly stated and reasonable?
4. **Completeness**: Does it attempt to address all parts of the problem?

**DO NOT**:
- Spend time on deep mathematical verification (that comes later)
- Nitpick minor presentation issues
- Require PhD-level rigor

### Problem ###
{problem_statement}

### Proposed Solution ###
{solution}
"""

        if previous_feedback:
            prompt += f"""
### Previous Feedback ###
{previous_feedback[:500]}...

### Additional Context ###
This solution was generated in response to the feedback above. Check if the major issues were addressed.
"""

        prompt += """
### Your Task ###
Provide a QUICK assessment in this EXACT format:

**VERDICT**: [ACCEPT/REJECT/UNCERTAIN]
**CONFIDENCE**: [0-100]
**QUICK FEEDBACK**:
- [One sentence describing the main strength or issue]
- [One sentence about answer validity]
- [One sentence recommendation]

Keep your response under 150 words total. Be decisive - avoid hedge words like "might", "possibly", "perhaps".
"""

        return prompt

    def _call_model_api(self, model: str, prompt: str) -> str:
        """
        Call model API with timeout and error handling.

        Args:
            model: Model name
            prompt: Validation prompt

        Returns:
            Model response text
        """
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.1,
            "max_tokens": 500  # Keep responses short
        }

        headers = {
            "Content-Type": "application/json"
        }

        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()

            result = response.json()
            return result['choices'][0]['message']['content']

        except requests.exceptions.Timeout:
            raise RuntimeError(f"Model {model} timed out after {self.timeout}s")
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"API request failed: {e}")

    def _parse_validation_response(self, response: str) -> Tuple[str, float, str]:
        """
        Parse validation response to extract verdict, confidence, feedback.

        Returns:
            Tuple of (verdict, confidence, feedback)
        """
        # Extract verdict
        verdict = 'UNCERTAIN'
        if 'VERDICT' in response:
            if 'ACCEPT' in response:
                verdict = 'ACCEPT'
            elif 'REJECT' in response:
                verdict = 'REJECT'

        # Extract confidence (0-1 scale)
        confidence = 0.5  # Default
        if 'CONFIDENCE' in response:
            import re
            conf_match = re.search(r'CONFIDENCE.*?(\d+)', response)
            if conf_match:
                confidence = float(conf_match.group(1)) / 100.0

        # Full response as feedback
        feedback = response.strip()

        return verdict, confidence, feedback

    def _compute_consensus(self,
                          model_results: List[Dict],
                          verbose: bool) -> Tuple[str, float]:
        """
        Compute consensus verdict and confidence from model results.

        Returns:
            Tuple of (consensus, confidence)
        """
        if not model_results:
            return 'UNCERTAIN', 0.0

        # Count verdicts
        verdicts = [r['verdict'] for r in model_results if r['verdict'] != 'ERROR']
        if not verdicts:
            return 'UNCERTAIN', 0.0

        accept_count = verdicts.count('ACCEPT')
        reject_count = verdicts.count('REJECT')
        uncertain_count = verdicts.count('UNCERTAIN')

        total = len(verdicts)

        # Determine consensus
        if accept_count > total / 2:
            consensus = 'ACCEPT'
            confidence = accept_count / total
        elif reject_count > total / 2:
            consensus = 'REJECT'
            confidence = reject_count / total
        else:
            consensus = 'UNCERTAIN'
            confidence = max(accept_count, reject_count, uncertain_count) / total

        # Weight by individual model confidences
        avg_confidence = sum(r['confidence'] for r in model_results if r['verdict'] != 'ERROR') / len(verdicts)
        weighted_confidence = confidence * avg_confidence

        if verbose:
            print(f">>>>>>> [CV] Vote distribution: ACCEPT={accept_count}, REJECT={reject_count}, UNCERTAIN={uncertain_count}")
            print(f">>>>>>> [CV] Raw consensus confidence: {confidence:.2f}")
            print(f">>>>>>> [CV] Weighted confidence: {weighted_confidence:.2f}")

        return consensus, weighted_confidence

    def _aggregate_feedback(self,
                           model_results: List[Dict],
                           verbose: bool) -> str:
        """
        Aggregate feedback from all models into combined summary.

        Returns:
            Combined feedback string
        """
        feedbacks = []
        for result in model_results:
            if result['verdict'] != 'ERROR':
                feedbacks.append(f"**{result['model']}** ({result['verdict']}, {result['confidence']:.2f}):\n{result['feedback']}\n")

        combined = "### Cross-Validation Feedback ###\n\n" + "\n".join(feedbacks)

        if verbose:
            print(f">>>>>>> [CV] Aggregated feedback from {len(feedbacks)} models")

        return combined


# Module-level function for easy integration
def cross_validate_solution(problem_statement: str,
                           solution: str,
                           previous_feedback: Optional[str] = None,
                           iteration: Optional[int] = None,
                           verbose: bool = True) -> Dict:
    """
    Convenience function to cross-validate a solution.

    Reads configuration from environment variables and creates validator.
    """
    # Read configuration
    models = os.getenv("GPT_OSS_CV_MODELS", "codeqwen3,qwen-math,deepseek-r1").split(",")
    api_url = os.getenv("GPT_OSS_CV_API_URL", "http://localhost:30001/v1/chat/completions")
    api_key = os.getenv("GPT_OSS_CV_API_KEY", "")
    timeout = int(os.getenv("GPT_OSS_CV_TIMEOUT", "300"))
    parallel = os.getenv("GPT_OSS_CV_PARALLEL", "true").lower() == "true"

    # Create validator
    validator = CrossValidator(
        models=models,
        api_url=api_url,
        api_key=api_key,
        timeout=timeout,
        parallel=parallel
    )

    # Run validation
    return validator.validate_solution(
        problem_statement=problem_statement,
        solution=solution,
        previous_feedback=previous_feedback,
        iteration=iteration,
        verbose=verbose
    )
```

---

## 4. Model Communication Strategy

### 4.1 Local Inference Setup

**Recommended Approach**: Use SGLang or vLLM for local deployment

```bash
# Option 1: SGLang (Recommended - same as GPT_OSS)
python -m sglang.launch_server \
  --model Qwen/CodeQwen3-32B-Instruct \
  --port 30001 \
  --host 0.0.0.0 \
  --tp 2

# Option 2: vLLM (Alternative)
python -m vllm.entrypoints.openai.api_server \
  --model Qwen/CodeQwen3-32B-Instruct \
  --port 30001 \
  --tensor-parallel-size 2

# Option 3: Multiple models on different ports
python -m sglang.launch_server --model Qwen/CodeQwen3-32B-Instruct --port 30001 &
python -m sglang.launch_server --model Qwen/Qwen2.5-Math-72B-Instruct --port 30002 &
python -m sglang.launch_server --model deepseek-ai/DeepSeek-R1-Distill-Qwen-32B --port 30003 &
```

### 4.2 API Endpoint Configuration

**Strategy**: Use OpenAI-compatible API for drop-in replacement

```python
# Single endpoint, model name switching
CV_API_URL = "http://localhost:30001/v1/chat/completions"
CV_MODELS = ["codeqwen3", "qwen-math", "deepseek-r1"]

# OR: Multiple endpoints
CV_API_URLS = {
    "codeqwen3": "http://localhost:30001/v1/chat/completions",
    "qwen-math": "http://localhost:30002/v1/chat/completions",
    "deepseek-r1": "http://localhost:30003/v1/chat/completions"
}
```

### 4.3 Batching Strategy

**For parallel execution** (recommended):

```python
# Use ThreadPoolExecutor for concurrent API calls
import concurrent.futures

with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
    futures = [
        executor.submit(validate_with_model, model, problem, solution)
        for model in models
    ]
    results = [f.result() for f in concurrent.futures.as_completed(futures)]
```

**Performance**: 3 models × 2 min each = ~2 min total (parallel) vs 6 min (sequential)

### 4.4 Caching Strategy

**Cache model responses** to avoid redundant API calls:

```python
import hashlib
import json

def get_cache_key(problem_statement, solution, model):
    """Generate cache key for a validation request."""
    content = f"{problem_statement}|{solution}|{model}"
    return hashlib.md5(content.encode()).hexdigest()

class CachedCrossValidator(CrossValidator):
    def __init__(self, *args, cache_dir="/tmp/cv_cache", **kwargs):
        super().__init__(*args, **kwargs)
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    def _validate_with_model(self, model, problem_statement, solution, previous_feedback, verbose):
        # Check cache first
        cache_key = get_cache_key(problem_statement, solution, model)
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")

        if os.path.exists(cache_file):
            with open(cache_file, 'r') as f:
                cached_result = json.load(f)
                print(f">>>>>>> [CV] Cache hit for {model}")
                return cached_result

        # Call API
        result = super()._validate_with_model(model, problem_statement, solution, previous_feedback, verbose)

        # Save to cache
        with open(cache_file, 'w') as f:
            json.dump(result, f)

        return result
```

---

## 5. Prompt Engineering for Cross-Validation

### 5.1 Prompt Adaptation Strategy

**Key Principle**: OSS models are smaller/faster → Simpler prompts

**Comparison**:

| Aspect | GPT-OSS High Verification | OSS Cross-Validation |
|--------|--------------------------|---------------------|
| **Goal** | Catch subtle errors | Catch obvious errors |
| **Depth** | PhD-level rigor | Undergraduate sanity check |
| **Length** | 500-2000 words | 50-150 words |
| **Time** | 10-30 min | 1-3 min |
| **Focus** | "Find ALL errors" | "Is this obviously wrong?" |

### 5.2 Lightweight Validation Prompt Template

```python
CROSS_VALIDATION_PROMPT_TEMPLATE = """You are a quick solution checker for mathematical problems.

**YOUR TASK**: Perform a FAST sanity check (2-3 minutes max).

**CHECK FOR**:
1. Does the solution have a clear structure and logical flow?
2. Are there any OBVIOUS mathematical errors (wrong formulas, calculation mistakes)?
3. Is the final answer clearly stated and does it match the problem requirements?
4. Does the solution attempt to address ALL parts of the problem?

**DO NOT CHECK**:
- Deep mathematical rigor (that comes later)
- Minor presentation issues
- Whether proofs are "elegant" enough

### Problem ###
{problem_statement}

### Solution to Check ###
{solution}

### Your Response ###
Provide EXACTLY this format (be concise, under 100 words):

**VERDICT**: [ACCEPT if likely correct / REJECT if obviously wrong / UNCERTAIN if need deeper check]
**CONFIDENCE**: [0-100, where 100 = absolutely certain]
**KEY ISSUE** (if REJECT): [One sentence describing the main problem]
**RECOMMENDATION**: [One sentence: "Pass to rigorous verification" OR "Regenerate solution" OR "Good to go"]
"""
```

### 5.3 Model-Specific Adaptations

Different models have different strengths:

```python
MODEL_PROMPT_ADAPTATIONS = {
    "codeqwen3": {
        # CodeQwen3 is good at reasoning chains
        "focus": "Check the logical flow and reasoning steps.",
        "style": "Think step-by-step through the solution."
    },
    "qwen-math": {
        # Qwen-Math is specialized in mathematical correctness
        "focus": "Check for mathematical errors and formula correctness.",
        "style": "Verify calculations and mathematical statements."
    },
    "deepseek-r1": {
        # DeepSeek-R1 is good at alternative perspectives
        "focus": "Consider if there are alternative approaches or missed edge cases.",
        "style": "Think critically about potential weaknesses."
    }
}

def build_adapted_prompt(base_prompt, model):
    """Adapt prompt based on model strengths."""
    adaptation = MODEL_PROMPT_ADAPTATIONS.get(model, {})

    if adaptation:
        adapted = base_prompt + f"\n\n**SPECIAL FOCUS for {model}**: {adaptation['focus']}\n{adaptation['style']}"
        return adapted

    return base_prompt
```

---

## 6. Performance Optimization

### 6.1 Maintain 17× Speed Advantage

**Current Performance**:
- Low reasoning generation: ~1.3 hours (78 min)
- High reasoning generation: ~23 hours (1380 min)
- Speed advantage: 17× faster

**Cross-Validation Budget**: Max 10% of generation time = ~8 minutes

**Optimization Strategies**:

1. **Parallel Execution** (Primary Strategy)
   ```
   3 models × 3 min each = 9 min sequential
   3 models × 3 min each = 3 min parallel (3× speedup)
   ```

2. **Timeout Control**
   ```python
   CV_TIMEOUT = 300  # 5 min max per model
   CV_TOTAL_TIMEOUT = 600  # 10 min max total
   ```

3. **Early Exit**
   ```python
   # If first 2 models strongly agree, skip 3rd model
   if len(results) >= 2:
       if all(r['verdict'] == 'REJECT' for r in results):
           if all(r['confidence'] > 0.8 for r in results):
               return early_reject_result()
   ```

4. **Progressive Validation**
   ```python
   # Use fastest model first, skip slower models if clear verdict
   FAST_MODELS = ["codeqwen3"]  # ~2 min
   SLOW_MODELS = ["qwen-math-72b"]  # ~5 min

   # Run fast models first
   fast_results = validate_with_models(FAST_MODELS)
   if is_clear_verdict(fast_results):
       return fast_results

   # Only run slow models if uncertain
   slow_results = validate_with_models(SLOW_MODELS)
   return combine_results(fast_results, slow_results)
   ```

### 6.2 Performance Monitoring

```python
class PerformanceMonitor:
    """Track cross-validation performance impact."""

    def __init__(self):
        self.cv_times = []
        self.generation_times = []
        self.verification_times = []

    def log_iteration(self, cv_time, gen_time, ver_time):
        self.cv_times.append(cv_time)
        self.generation_times.append(gen_time)
        self.verification_times.append(ver_time)

    def report(self):
        avg_cv = sum(self.cv_times) / len(self.cv_times)
        avg_gen = sum(self.generation_times) / len(self.generation_times)
        avg_ver = sum(self.verification_times) / len(self.verification_times)

        cv_overhead = avg_cv / avg_gen * 100

        print(f">>>>>>> [PERFORMANCE] Avg CV time: {avg_cv:.1f}s")
        print(f">>>>>>> [PERFORMANCE] Avg generation time: {avg_gen:.1f}s")
        print(f">>>>>>> [PERFORMANCE] CV overhead: {cv_overhead:.1f}%")

        if cv_overhead > 15:
            print(f">>>>>>> [PERFORMANCE] ⚠️  CV overhead too high! Target: <10%")
```

### 6.3 Caching for Repeated Validations

```python
# Use LRU cache for frequently validated solutions
from functools import lru_cache

@lru_cache(maxsize=128)
def cached_validate(problem_hash, solution_hash, model):
    """Cache validation results to avoid redundant API calls."""
    # Implementation as shown in 4.4
    pass
```

---

## 7. Error Handling Strategy

### 7.1 Model Failure Handling

```python
class RobustCrossValidator(CrossValidator):
    """Enhanced validator with comprehensive error handling."""

    def _validate_with_model(self, model, problem_statement, solution, previous_feedback, verbose):
        """Validate with retry logic and fallback."""
        max_retries = 2
        retry_delay = 2  # seconds

        for attempt in range(max_retries):
            try:
                return super()._validate_with_model(
                    model, problem_statement, solution, previous_feedback, verbose
                )
            except requests.exceptions.Timeout:
                print(f">>>>>>> [CV] {model} timeout (attempt {attempt+1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                else:
                    # Return uncertain verdict on timeout
                    return {
                        'model': model,
                        'verdict': 'UNCERTAIN',
                        'confidence': 0.0,
                        'feedback': 'Model timed out',
                        'execution_time': self.timeout,
                        'error': 'timeout'
                    }

            except Exception as e:
                print(f">>>>>>> [CV] {model} error: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                else:
                    return {
                        'model': model,
                        'verdict': 'ERROR',
                        'confidence': 0.0,
                        'feedback': f'Error: {str(e)}',
                        'execution_time': 0.0,
                        'error': str(e)
                    }

        # Should never reach here
        return {
            'model': model,
            'verdict': 'ERROR',
            'confidence': 0.0,
            'feedback': 'Unexpected error',
            'execution_time': 0.0
        }
```

### 7.2 Timeout Escalation

```python
# Start with short timeout, escalate if needed
TIMEOUT_LEVELS = [
    180,  # 3 min (try first)
    300,  # 5 min (if 3 min times out)
    600   # 10 min (last resort)
]

def validate_with_escalating_timeout(model, problem, solution):
    """Try validation with escalating timeouts."""
    for timeout in TIMEOUT_LEVELS:
        try:
            result = validate_with_timeout(model, problem, solution, timeout)
            return result
        except TimeoutError:
            print(f">>>>>>> [CV] {model} timed out at {timeout}s, trying {timeout*2}s...")
            continue

    # All timeouts failed
    return create_timeout_failure_result(model)
```

### 7.3 Model Disagreement Resolution

```python
def resolve_disagreement(model_results: List[Dict], verbose: bool = True) -> Dict:
    """
    Handle cases where models disagree strongly.

    Strategies:
    1. Weight by model confidence
    2. Use majority voting
    3. Escalate to high verification if 50/50 split
    """
    accept_votes = [r for r in model_results if r['verdict'] == 'ACCEPT']
    reject_votes = [r for r in model_results if r['verdict'] == 'REJECT']

    # Strong disagreement (50/50 split)
    if abs(len(accept_votes) - len(reject_votes)) <= 1:
        if verbose:
            print(f">>>>>>> [CV] Strong disagreement detected")
            print(f">>>>>>> [CV] ACCEPT: {len(accept_votes)}, REJECT: {len(reject_votes)}")

        # Weight by confidence
        accept_confidence = sum(r['confidence'] for r in accept_votes)
        reject_confidence = sum(r['confidence'] for r in reject_votes)

        if verbose:
            print(f">>>>>>> [CV] Weighted confidence: ACCEPT={accept_confidence:.2f}, REJECT={reject_confidence:.2f}")

        # If confidences are also close, escalate
        if abs(accept_confidence - reject_confidence) < 0.3:
            return {
                'consensus': 'UNCERTAIN',
                'confidence': 0.5,
                'reason': 'Strong model disagreement - escalating to high verification',
                'model_results': model_results
            }

        # Otherwise, go with higher weighted confidence
        if accept_confidence > reject_confidence:
            return {
                'consensus': 'ACCEPT',
                'confidence': accept_confidence / len(accept_votes),
                'reason': 'Higher weighted confidence for acceptance',
                'model_results': model_results
            }
        else:
            return {
                'consensus': 'REJECT',
                'confidence': reject_confidence / len(reject_votes),
                'reason': 'Higher weighted confidence for rejection',
                'model_results': model_results
            }

    # Clear majority
    if len(accept_votes) > len(reject_votes):
        return {
            'consensus': 'ACCEPT',
            'confidence': len(accept_votes) / len(model_results),
            'reason': 'Majority vote for acceptance',
            'model_results': model_results
        }
    else:
        return {
            'consensus': 'REJECT',
            'confidence': len(reject_votes) / len(model_results),
            'reason': 'Majority vote for rejection',
            'model_results': model_results
        }
```

### 7.4 Graceful Degradation

```python
# If CV fails completely, fall back to existing workflow
try:
    cv_result = cross_validate_solution(problem_statement, solution)
except Exception as e:
    print(f">>>>>>> [CV] Cross-validation failed: {e}")
    print(f">>>>>>> [CV] Falling back to standard verification")
    cv_result = None

# Proceed with normal verification regardless
verify, good_verify = verify_solution_safe(
    problem_statement, solution, reasoning_effort=ver_reasoning
)

# Use CV result if available
if cv_result and cv_result['consensus'] == 'REJECT' and cv_result['confidence'] > 0.8:
    print(f">>>>>>> [CV] Strong rejection - using CV feedback")
    verify = cv_result['combined_feedback']
    good_verify = "No - rejected by cross-validation"
```

---

## 8. Testing Strategy

### 8.1 Unit Tests

Create `/home/user/IMO25/tests/test_cross_validator.py`:

```python
import pytest
from code.cross_validator import CrossValidator, cross_validate_solution

class TestCrossValidator:
    """Unit tests for cross-validation module."""

    def test_validator_initialization(self):
        """Test validator initializes correctly."""
        validator = CrossValidator(
            models=["model1", "model2"],
            api_url="http://localhost:30001/v1/chat/completions",
            timeout=300
        )

        assert validator.models == ["model1", "model2"]
        assert validator.timeout == 300
        assert validator.parallel == True  # Default

    def test_consensus_computation(self):
        """Test consensus algorithm."""
        validator = CrossValidator(
            models=["m1", "m2", "m3"],
            api_url="http://localhost:30001/v1/chat/completions"
        )

        # All accept
        results = [
            {'model': 'm1', 'verdict': 'ACCEPT', 'confidence': 0.9},
            {'model': 'm2', 'verdict': 'ACCEPT', 'confidence': 0.8},
            {'model': 'm3', 'verdict': 'ACCEPT', 'confidence': 0.85}
        ]
        consensus, confidence = validator._compute_consensus(results, verbose=False)
        assert consensus == 'ACCEPT'
        assert confidence > 0.7

        # Majority reject
        results = [
            {'model': 'm1', 'verdict': 'REJECT', 'confidence': 0.9},
            {'model': 'm2', 'verdict': 'REJECT', 'confidence': 0.85},
            {'model': 'm3', 'verdict': 'ACCEPT', 'confidence': 0.7}
        ]
        consensus, confidence = validator._compute_consensus(results, verbose=False)
        assert consensus == 'REJECT'

        # Split decision
        results = [
            {'model': 'm1', 'verdict': 'ACCEPT', 'confidence': 0.8},
            {'model': 'm2', 'verdict': 'REJECT', 'confidence': 0.8}
        ]
        consensus, confidence = validator._compute_consensus(results, verbose=False)
        assert consensus == 'UNCERTAIN'

    def test_error_handling(self):
        """Test handling of model failures."""
        validator = CrossValidator(
            models=["failing_model"],
            api_url="http://localhost:30001/v1/chat/completions",
            timeout=1  # Short timeout to trigger failure
        )

        # Should not crash, should return error result
        try:
            result = validator._validate_with_model(
                "failing_model",
                "Test problem",
                "Test solution",
                None,
                False
            )
            # Should get error verdict
            assert result['verdict'] in ['ERROR', 'UNCERTAIN']
        except Exception:
            pytest.fail("Should handle errors gracefully")
```

### 8.2 Integration Tests

Create `/home/user/IMO25/tests/test_cv_integration.py`:

```python
import pytest
import os
from code.agent_gpt_oss import init_explorations
from code.cross_validator import cross_validate_solution

class TestCrossValidationIntegration:
    """Integration tests for CV with agent workflow."""

    @pytest.mark.skipif(
        not os.getenv("GPT_OSS_CROSS_VALIDATION"),
        reason="Cross-validation not enabled"
    )
    def test_cv_after_generation(self):
        """Test CV runs after solution generation."""
        problem = "Find all positive integers n such that 2^n + 1 is divisible by 3."

        # Generate solution
        p1, solution, verify, good_verify = init_explorations(
            problem, verbose=True, other_prompts=[],
            reasoning_effort="low",
            self_improvement_reasoning="high",
            verification_reasoning="high"
        )

        assert solution is not None

        # Run CV
        cv_result = cross_validate_solution(problem, solution, verbose=True)

        assert cv_result is not None
        assert 'consensus' in cv_result
        assert cv_result['consensus'] in ['ACCEPT', 'REJECT', 'UNCERTAIN']
        assert 'confidence' in cv_result
        assert 0.0 <= cv_result['confidence'] <= 1.0

    def test_cv_performance_overhead(self):
        """Test CV doesn't add >10% overhead."""
        import time

        problem = "Prove that for all positive integers n, n^2 + n is even."
        solution = "Sample solution..."

        # Measure CV time
        start = time.time()
        cv_result = cross_validate_solution(problem, solution, verbose=False)
        cv_time = time.time() - start

        # CV should complete in <10 minutes
        assert cv_time < 600, f"CV took {cv_time:.1f}s, should be <600s"

        print(f"CV time: {cv_time:.1f}s")
```

### 8.3 Validation Quality Tests

Create `/home/user/IMO25/tests/test_cv_quality.py`:

```python
import pytest
from code.cross_validator import cross_validate_solution

class TestValidationQuality:
    """Test that CV catches obvious errors."""

    def test_catches_wrong_answer(self):
        """CV should reject obviously wrong solutions."""
        problem = "Prove that 2 + 2 = 4."
        wrong_solution = """
        ### Summary ###
        The answer is 5.

        ### Detailed Solution ###
        We claim that 2 + 2 = 5.
        This follows from basic arithmetic.
        """

        cv_result = cross_validate_solution(problem, wrong_solution)

        # Should reject or be uncertain (definitely not accept)
        assert cv_result['consensus'] != 'ACCEPT' or cv_result['confidence'] < 0.5

    def test_accepts_correct_solution(self):
        """CV should accept obviously correct solutions."""
        problem = "Prove that for all positive integers n, n^2 >= n."
        correct_solution = """
        ### Summary ###
        We prove that n^2 >= n for all positive integers n.

        ### Detailed Solution ###
        For any positive integer n >= 1, we have:
        n^2 = n * n >= n * 1 = n
        since n >= 1. Therefore n^2 >= n. QED.
        """

        cv_result = cross_validate_solution(problem, correct_solution)

        # Should likely accept (or at least not strongly reject)
        assert cv_result['consensus'] != 'REJECT' or cv_result['confidence'] < 0.7

    def test_detects_incomplete_solution(self):
        """CV should flag incomplete solutions."""
        problem = "Prove statement A and statement B."
        incomplete_solution = """
        ### Summary ###
        We prove statement A.

        ### Detailed Solution ###
        [Proof of A only, B is missing]
        """

        cv_result = cross_validate_solution(problem, incomplete_solution)

        # Should be uncertain or reject
        if cv_result['consensus'] == 'ACCEPT':
            assert cv_result['confidence'] < 0.7, "Should have low confidence on incomplete solution"
```

### 8.4 End-to-End Testing

```bash
# Test script: tests/test_cv_e2e.sh
#!/bin/bash

# Test cross-validation on a real IMO problem

export GPT_OSS_CROSS_VALIDATION=true
export GPT_OSS_CV_MODELS="codeqwen3"
export GPT_OSS_CV_API_URL="http://localhost:30001/v1/chat/completions"
export GPT_OSS_SOLUTION_REASONING="low"
export GPT_OSS_VERIFICATION_REASONING="high"

echo "Running end-to-end CV test..."

python code/agent_gpt_oss.py problems/imo01.txt \
  --log test_cv_e2e.log \
  --max_runs 1 \
  --num-initial-attempts 1

# Check if CV was executed
if grep -q "\[CV\]" test_cv_e2e.log; then
    echo "✓ Cross-validation executed"
else
    echo "✗ Cross-validation not found in logs"
    exit 1
fi

# Check if CV completed within time budget
cv_time=$(grep "CV.*Time:" test_cv_e2e.log | grep -oP '\d+\.\d+')
if (( $(echo "$cv_time < 600" | bc -l) )); then
    echo "✓ CV completed in ${cv_time}s (<600s)"
else
    echo "✗ CV took too long: ${cv_time}s"
    exit 1
fi

echo "End-to-end CV test passed!"
```

---

## 9. Deployment Guide

### 9.1 Step-by-Step Deployment

**Step 1: Install Dependencies**

```bash
# Install cross-validation dependencies
pip install requests concurrent-futures

# Install model serving framework (choose one)
pip install sglang  # Recommended
# OR
pip install vllm
```

**Step 2: Deploy Open Source Models**

```bash
# Download models (Hugging Face)
huggingface-cli download Qwen/CodeQwen3-32B-Instruct
huggingface-cli download Qwen/Qwen2.5-Math-72B-Instruct
huggingface-cli download deepseek-ai/DeepSeek-R1-Distill-Qwen-32B

# Start model servers (in separate terminals or tmux)
# Model 1: CodeQwen3-32B (port 30001)
python -m sglang.launch_server \
  --model Qwen/CodeQwen3-32B-Instruct \
  --port 30001 \
  --host 0.0.0.0 \
  --tp 2

# Model 2: Qwen2.5-Math-72B (port 30002)
python -m sglang.launch_server \
  --model Qwen/Qwen2.5-Math-72B-Instruct \
  --port 30002 \
  --host 0.0.0.0 \
  --tp 4  # Larger model needs more GPUs

# Model 3: DeepSeek-R1-Distill-Qwen-32B (port 30003)
python -m sglang.launch_server \
  --model deepseek-ai/DeepSeek-R1-Distill-Qwen-32B \
  --port 30003 \
  --host 0.0.0.0 \
  --tp 2
```

**Step 3: Add Cross-Validation Module**

```bash
# Create the cross_validator.py file
# (Copy the code from Section 3.1)
touch code/cross_validator.py
# ... add code ...
```

**Step 4: Modify agent_gpt_oss.py**

```bash
# Add configuration at line 55
# Add integration points at lines 1226 and 1695
# (See Section 2 for exact code)
```

**Step 5: Configure Environment**

```bash
# Add to .env or export directly
export GPT_OSS_CROSS_VALIDATION=true
export GPT_OSS_CV_MODELS="codeqwen3,qwen-math,deepseek-r1"
export GPT_OSS_CV_API_URL="http://localhost:30001/v1/chat/completions"
export GPT_OSS_CV_TIMEOUT=300
export GPT_OSS_CV_PARALLEL=true
export GPT_OSS_CV_ON_CORRECTIONS=true
```

**Step 6: Test Deployment**

```bash
# Run simple test
python code/agent_gpt_oss.py problems/imo01.txt \
  --log test_cv.log \
  --max_runs 1 \
  --solution-reasoning low \
  --verification-reasoning high

# Check logs for CV execution
grep "\[CV\]" test_cv.log

# Should see output like:
# [CV] Initialized CrossValidator
# [CV] Models: ['codeqwen3', 'qwen-math', 'deepseek-r1']
# [CV] Running 3 models in parallel...
# [CV] codeqwen3: ACCEPT (confidence: 0.85)
# [CV] qwen-math: ACCEPT (confidence: 0.80)
# [CV] deepseek-r1: UNCERTAIN (confidence: 0.60)
# [CV] Consensus: ACCEPT
# [CV] Confidence: 0.75
```

### 9.2 Configuration Profiles

**Profile 1: Fast (Single Model)**
```bash
export GPT_OSS_CV_MODELS="codeqwen3"
export GPT_OSS_CV_TIMEOUT=180
# Estimated time: ~2-3 min
```

**Profile 2: Balanced (Two Models)**
```bash
export GPT_OSS_CV_MODELS="codeqwen3,qwen-math"
export GPT_OSS_CV_TIMEOUT=300
export GPT_OSS_CV_PARALLEL=true
# Estimated time: ~3-5 min (parallel)
```

**Profile 3: Robust (Three Models)**
```bash
export GPT_OSS_CV_MODELS="codeqwen3,qwen-math,deepseek-r1"
export GPT_OSS_CV_TIMEOUT=300
export GPT_OSS_CV_PARALLEL=true
# Estimated time: ~5-8 min (parallel)
```

**Profile 4: Budget (Remote API)**
```bash
# Use hosted API instead of local deployment
export GPT_OSS_CV_API_URL="https://api.together.xyz/v1/chat/completions"
export GPT_OSS_CV_API_KEY="your_together_api_key"
export GPT_OSS_CV_MODELS="Qwen/CodeQwen3-32B-Instruct"
```

### 9.3 Monitoring and Debugging

```bash
# Enable verbose logging
export GPT_OSS_CV_VERBOSE=true

# Monitor CV performance
tail -f test_cv.log | grep "\[CV\]"

# Check CV statistics
python -c "
import json
with open('test_cv.log') as f:
    for line in f:
        if '[CV]' in line and 'Time:' in line:
            print(line.strip())
"

# Debug API connectivity
curl -X POST http://localhost:30001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "codeqwen3",
    "messages": [{"role": "user", "content": "Test"}],
    "max_tokens": 50
  }'
```

---

## 10. Success Metrics and Evaluation

### 10.1 Performance Metrics

Track these metrics to evaluate CV effectiveness:

```python
class CrossValidationMetrics:
    """Track and report CV performance metrics."""

    def __init__(self):
        self.iterations = []
        self.cv_times = []
        self.high_ver_times = []
        self.cv_verdicts = []
        self.high_ver_verdicts = []
        self.cv_high_agreement = 0
        self.cv_high_disagreement = 0
        self.cv_prevented_high_ver = 0

    def log_iteration(self, cv_result, high_ver_result, cv_time, ver_time):
        """Log results from one iteration."""
        self.iterations.append(len(self.iterations) + 1)
        self.cv_times.append(cv_time)
        self.high_ver_times.append(ver_time)

        cv_verdict = cv_result['consensus']
        high_verdict = 'ACCEPT' if 'yes' in high_ver_result.lower() else 'REJECT'

        self.cv_verdicts.append(cv_verdict)
        self.high_ver_verdicts.append(high_verdict)

        # Check agreement
        if cv_verdict == high_verdict:
            self.cv_high_agreement += 1
        else:
            self.cv_high_disagreement += 1

        # Check if CV could have skipped high verification
        if cv_result['confidence'] > 0.9 and cv_verdict == high_verdict:
            self.cv_prevented_high_ver += 1

    def report(self):
        """Generate performance report."""
        total_iterations = len(self.iterations)
        avg_cv_time = sum(self.cv_times) / total_iterations
        avg_ver_time = sum(self.high_ver_times) / total_iterations

        agreement_rate = self.cv_high_agreement / total_iterations * 100
        potential_savings = self.cv_prevented_high_ver / total_iterations * 100

        report = f"""
        ╔══════════════════════════════════════════════════════════════╗
        ║          CROSS-VALIDATION PERFORMANCE REPORT                 ║
        ╠══════════════════════════════════════════════════════════════╣
        ║  Total Iterations:              {total_iterations:>4}                        ║
        ║                                                              ║
        ║  Timing:                                                     ║
        ║    Avg CV Time:                 {avg_cv_time:>6.1f}s ({avg_cv_time/60:>4.1f} min)         ║
        ║    Avg High Ver Time:           {avg_ver_time:>6.1f}s ({avg_ver_time/60:>4.1f} min)         ║
        ║    CV Overhead:                 {avg_cv_time/avg_ver_time*100:>5.1f}%                    ║
        ║                                                              ║
        ║  Agreement:                                                  ║
        ║    CV-HighVer Agreement:        {agreement_rate:>5.1f}%                     ║
        ║    CV-HighVer Disagreement:     {100-agreement_rate:>5.1f}%                     ║
        ║                                                              ║
        ║  Efficiency:                                                 ║
        ║    High Ver Could Skip:         {potential_savings:>5.1f}%                     ║
        ║    Time Saved (if skipped):     {self.cv_prevented_high_ver * avg_ver_time / 60:>5.1f} min                 ║
        ╚══════════════════════════════════════════════════════════════╝
        """

        print(report)

        # Save to JSON
        with open('cv_metrics.json', 'w') as f:
            json.dump({
                'total_iterations': total_iterations,
                'avg_cv_time': avg_cv_time,
                'avg_high_ver_time': avg_ver_time,
                'agreement_rate': agreement_rate,
                'potential_savings': potential_savings,
                'iterations': self.iterations,
                'cv_times': self.cv_times,
                'high_ver_times': self.high_ver_times
            }, f, indent=2)
```

### 10.2 Target Metrics

**Success Criteria** (after 100 test problems):

| Metric | Target | Rationale |
|--------|--------|-----------|
| **CV Time** | <8 min avg | <10% of low reasoning generation time (78 min) |
| **Agreement Rate** | >70% | CV should align with high verification in most cases |
| **False Positive Rate** | <15% | CV accepts but high ver rejects (acceptable tradeoff) |
| **False Negative Rate** | <5% | CV rejects but high ver accepts (more costly, keep low) |
| **Potential Time Savings** | >20% | Cases where CV could skip high verification |
| **Success Rate Improvement** | +10-15% | Overall problem-solving success rate |

### 10.3 Evaluation Protocol

**Test Suite**: Run on 100 diverse problems

```bash
# Create evaluation script
cat > evaluate_cv.sh <<'EOF'
#!/bin/bash

# Run agent with CV enabled on test suite
PROBLEMS=(
    problems/imo01.txt
    problems/imo02.txt
    problems/imo03.txt
    problems/imo04.txt
    problems/imo05.txt
    # Add more problems from benchmark
)

export GPT_OSS_CROSS_VALIDATION=true
export GPT_OSS_SOLUTION_REASONING=low
export GPT_OSS_VERIFICATION_REASONING=high

mkdir -p evaluation_results

for problem in "${PROBLEMS[@]}"; do
    base=$(basename "$problem" .txt)
    echo "Evaluating $base..."

    python code/agent_gpt_oss.py "$problem" \
        --log "evaluation_results/${base}_cv.log" \
        --max_runs 3 \
        2>&1 | tee "evaluation_results/${base}_cv_output.txt"
done

# Generate report
python scripts/analyze_cv_metrics.py evaluation_results/
EOF

chmod +x evaluate_cv.sh
```

---

## 11. Future Enhancements

### 11.1 Adaptive Cross-Validation

**Dynamic Model Selection** based on problem type:

```python
def select_cv_models(problem_statement: str) -> List[str]:
    """
    Dynamically select CV models based on problem characteristics.

    - Algebra/Number Theory → Qwen-Math
    - Geometry → CodeQwen3 (better spatial reasoning)
    - Combinatorics → DeepSeek-R1 (creative approaches)
    """
    keywords = {
        'algebra': ['equation', 'polynomial', 'root', 'coefficient'],
        'geometry': ['triangle', 'circle', 'angle', 'perpendicular'],
        'number_theory': ['divisible', 'prime', 'modulo', 'integer'],
        'combinatorics': ['permutation', 'combination', 'counting', 'arrangement']
    }

    problem_lower = problem_statement.lower()

    # Detect problem type
    scores = {}
    for topic, words in keywords.items():
        scores[topic] = sum(1 for w in words if w in problem_lower)

    dominant_topic = max(scores, key=scores.get)

    # Select models based on topic
    model_preferences = {
        'algebra': ['qwen-math', 'codeqwen3'],
        'geometry': ['codeqwen3', 'deepseek-r1'],
        'number_theory': ['qwen-math', 'deepseek-r1'],
        'combinatorics': ['deepseek-r1', 'codeqwen3']
    }

    return model_preferences.get(dominant_topic, ['codeqwen3'])
```

### 11.2 Learning from Disagreements

**Track and analyze CV-HighVer disagreements** to improve CV prompts:

```python
class DisagreementAnalyzer:
    """Analyze cases where CV and high verification disagree."""

    def __init__(self):
        self.disagreements = []

    def log_disagreement(self, problem, solution, cv_result, high_result):
        """Record a disagreement case."""
        self.disagreements.append({
            'problem': problem,
            'solution': solution,
            'cv_verdict': cv_result['consensus'],
            'cv_confidence': cv_result['confidence'],
            'high_verdict': 'ACCEPT' if 'yes' in high_result.lower() else 'REJECT',
            'cv_feedback': cv_result['combined_feedback'],
            'high_feedback': high_result
        })

    def analyze(self):
        """Analyze disagreement patterns."""
        false_positives = [d for d in self.disagreements
                          if d['cv_verdict'] == 'ACCEPT' and d['high_verdict'] == 'REJECT']
        false_negatives = [d for d in self.disagreements
                          if d['cv_verdict'] == 'REJECT' and d['high_verdict'] == 'ACCEPT']

        print(f"False Positives: {len(false_positives)}")
        print(f"False Negatives: {len(false_negatives)}")

        # Extract common patterns in false positives
        for fp in false_positives:
            print(f"\nFalse Positive Case:")
            print(f"CV Confidence: {fp['cv_confidence']:.2f}")
            print(f"High Feedback (first 200 chars): {fp['high_feedback'][:200]}")
```

### 11.3 Confidence Calibration

**Calibrate CV confidence scores** against actual success rate:

```python
def calibrate_confidence(cv_confidence: float, historical_data: List[Dict]) -> float:
    """
    Calibrate CV confidence based on historical agreement rate.

    Example: If CV confidence 0.8 historically agrees with high ver 60% of time,
    calibrated confidence = 0.6 (not 0.8).
    """
    # Bin historical data by confidence ranges
    bins = {
        '0.0-0.3': [],
        '0.3-0.5': [],
        '0.5-0.7': [],
        '0.7-0.9': [],
        '0.9-1.0': []
    }

    for entry in historical_data:
        conf = entry['cv_confidence']
        agreed = entry['cv_verdict'] == entry['high_verdict']

        if conf < 0.3:
            bins['0.0-0.3'].append(agreed)
        elif conf < 0.5:
            bins['0.3-0.5'].append(agreed)
        elif conf < 0.7:
            bins['0.5-0.7'].append(agreed)
        elif conf < 0.9:
            bins['0.7-0.9'].append(agreed)
        else:
            bins['0.9-1.0'].append(agreed)

    # Find which bin current confidence falls into
    bin_key = None
    if cv_confidence < 0.3:
        bin_key = '0.0-0.3'
    elif cv_confidence < 0.5:
        bin_key = '0.3-0.5'
    elif cv_confidence < 0.7:
        bin_key = '0.5-0.7'
    elif cv_confidence < 0.9:
        bin_key = '0.7-0.9'
    else:
        bin_key = '0.9-1.0'

    # Calculate actual agreement rate in this bin
    if bin_key and bins[bin_key]:
        actual_agreement_rate = sum(bins[bin_key]) / len(bins[bin_key])
        return actual_agreement_rate

    # Default: return original confidence
    return cv_confidence
```

### 11.4 Multi-Stage Cross-Validation

**Progressive validation** with early exit:

```
Stage 1: Single fastest model (2 min)
  ├─ If strong REJECT (conf > 0.9) → Exit, regenerate
  └─ Otherwise → Continue to Stage 2

Stage 2: Add second model (4 min total)
  ├─ If both REJECT (conf > 0.8) → Exit, regenerate
  ├─ If both ACCEPT (conf > 0.9) → Exit, skip high verification
  └─ Otherwise → Continue to Stage 3

Stage 3: Add third model + high verification (8 min total)
  └─ Use full CV consensus + high verification
```

---

## 12. Conclusion and Next Steps

### 12.1 Summary

This implementation plan provides a comprehensive strategy for integrating cross-validation with open source models into the `agent_gpt_oss.py` workflow:

✅ **Workflow Integration**: Inject CV between generation and verification
✅ **Model Communication**: Use OpenAI-compatible API with parallel execution
✅ **Prompt Engineering**: Lightweight prompts for fast sanity checks
✅ **Performance**: Maintain <10% overhead via parallelization and caching
✅ **Error Handling**: Robust timeout, retry, and fallback mechanisms
✅ **Testing**: Comprehensive unit, integration, and E2E tests

### 12.2 Implementation Phases

**Phase 1: MVP (Week 1-2)**
- [ ] Create `cross_validator.py` module
- [ ] Deploy one OSS model (CodeQwen3-32B)
- [ ] Integrate CV after initial solution generation
- [ ] Basic timeout and error handling
- [ ] Unit tests for core functionality

**Phase 2: Enhancement (Week 3-4)**
- [ ] Add 2-3 models for diverse perspectives
- [ ] Implement parallel execution
- [ ] Add CV to correction loop
- [ ] Calibration and confidence scoring
- [ ] Integration tests

**Phase 3: Optimization (Week 5-6)**
- [ ] Performance tuning (caching, early exit)
- [ ] Prompt optimization for each model
- [ ] Disagreement analysis
- [ ] E2E evaluation on 100 problems
- [ ] Metrics and reporting

**Phase 4: Advanced Features (Week 7-8)**
- [ ] Adaptive model selection
- [ ] Multi-stage progressive validation
- [ ] Confidence calibration
- [ ] Learning from disagreements
- [ ] Production deployment

### 12.3 Expected Benefits

Based on this implementation:

1. **Quality Improvement**: +10-15% success rate
   - Early detection of obvious errors
   - Diverse perspectives catch different error types
   - Faster feedback loop for corrections

2. **Efficiency Gains**: 20-30% time savings
   - Skip high verification when CV has high confidence
   - Early rejection prevents wasted verification time
   - Parallel execution keeps overhead low

3. **Robustness**: More reliable solutions
   - Multi-model consensus reduces false positives
   - Catches errors that single model might miss
   - Graceful degradation on model failures

4. **Cost Reduction**: $2-4 per problem saved
   - Less high reasoning verification needed
   - Fewer correction iterations
   - Better first-attempt success rate

### 12.4 Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| **CV adds too much overhead** | Use parallel execution, timeouts, early exit |
| **Models disagree frequently** | Use weighted voting, confidence calibration |
| **False positives slow progress** | Monitor metrics, adjust confidence thresholds |
| **API failures** | Graceful degradation, retry logic, fallback to standard workflow |
| **Prompt quality varies** | Model-specific adaptations, continuous tuning |

### 12.5 Success Indicators

After deployment, monitor these KPIs:

- CV average time: <8 minutes ✓
- CV-HighVer agreement: >70% ✓
- Overall success rate: +10-15% improvement ✓
- Cost per problem: $10-12 (vs $12-15 baseline) ✓

---

## Appendix

### A. Command Reference

```bash
# Enable cross-validation
export GPT_OSS_CROSS_VALIDATION=true

# Configure models
export GPT_OSS_CV_MODELS="codeqwen3,qwen-math,deepseek-r1"

# Configure API
export GPT_OSS_CV_API_URL="http://localhost:30001/v1/chat/completions"
export GPT_OSS_CV_API_KEY=""  # Optional

# Configure timing
export GPT_OSS_CV_TIMEOUT=300
export GPT_OSS_CV_PARALLEL=true
export GPT_OSS_CV_ON_CORRECTIONS=true

# Run agent with CV
python code/agent_gpt_oss.py problems/imo01.txt \
  --log cv_test.log \
  --solution-reasoning low \
  --verification-reasoning high \
  --max_runs 5
```

### B. File Structure

```
IMO25/
├── code/
│   ├── agent_gpt_oss.py          # Main agent (modified)
│   ├── cross_validator.py         # NEW: CV module
│   └── ...
├── tests/
│   ├── test_cross_validator.py    # NEW: Unit tests
│   ├── test_cv_integration.py     # NEW: Integration tests
│   ├── test_cv_quality.py         # NEW: Quality tests
│   └── test_cv_e2e.sh            # NEW: E2E test script
├── evaluation_results/            # NEW: Evaluation output
├── cv_metrics.json               # NEW: Performance metrics
└── CROSS_VALIDATION_IMPLEMENTATION_PLAN.md  # This document
```

### C. Contact and Support

For questions or issues with this implementation:
- Review code comments in `cross_validator.py`
- Check test cases for usage examples
- Monitor logs with `grep "\[CV\]" logfile.log`
- Analyze metrics in `cv_metrics.json`

---

**Document Version**: 1.0
**Last Updated**: 2025-11-19
**Author**: Implementation Plan for Cross-Validation Integration
**Status**: Ready for Implementation

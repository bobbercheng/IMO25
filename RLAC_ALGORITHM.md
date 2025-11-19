# Agentic RLAC Algorithm Specification

## Algorithm: Adversarial Critic Reinforcement Learning (Inference-Time)

```python
def agentic_rlac_solve(problem_statement, max_iterations=10):
    """
    Solve a mathematical problem using adversarial critic reinforcement learning.

    This implements RLAC at inference time using two competing agents:
    - Generator: Creates and refines solutions
    - Critic: Adversarially attacks solutions to find flaws

    The "reinforcement" comes from iterative improvement based on adversarial feedback.
    """

    # Initialize state
    solution = None
    criticism_history = []
    cumulative_reward = 0
    best_solution = None
    best_reward = -float('inf')

    for iteration in range(1, max_iterations + 1):
        print(f"\n{'='*80}")
        print(f"RLAC ITERATION {iteration}/{max_iterations}")
        print(f"{'='*80}\n")

        # ============================================================
        # PHASE 1: GENERATION
        # ============================================================
        print("PHASE 1: Solution Generation")

        if iteration == 1:
            # Initial solution generation
            solution = generator_agent.generate_initial_solution(
                problem=problem_statement,
                reasoning_effort="high"  # Be thorough from the start
            )
        else:
            # Revise solution based on adversarial criticism
            solution = generator_agent.revise_solution(
                problem=problem_statement,
                previous_solution=solution,
                latest_criticism=criticism_history[-1],
                full_criticism_history=criticism_history,
                reasoning_effort="high"
            )

        print(f"Solution generated (iteration {iteration})")
        print(f"Length: {len(solution.content)} chars\n")

        # ============================================================
        # PHASE 2: ADVERSARIAL CRITICISM
        # ============================================================
        print("PHASE 2: Adversarial Attack")

        # Critic attempts to break the solution
        criticism = critic_agent.adversarial_attack(
            problem=problem_statement,
            proposed_solution=solution,
            previous_attacks=criticism_history,
            attack_intensity=get_attack_intensity(iteration),
            reasoning_effort="high"  # Critic must be thorough
        )

        print(f"Criticism complete")
        print(f"Flaws found: {len(criticism.flaws)}\n")

        # ============================================================
        # PHASE 3: REINFORCEMENT SIGNAL CALCULATION
        # ============================================================
        print("PHASE 3: Reinforcement Signal")

        if criticism.no_flaws_found:
            # POSITIVE REINFORCEMENT: Solution survived adversarial attack
            reward = +10
            cumulative_reward += reward

            print(f"✓ SOLUTION SURVIVED ADVERSARIAL ATTACK")
            print(f"Reward: +{reward}")
            print(f"Cumulative Reward: {cumulative_reward}")

            # Solution passed adversarial validation
            return {
                'success': True,
                'solution': solution,
                'iterations': iteration,
                'total_reward': cumulative_reward,
                'criticism_history': criticism_history
            }

        else:
            # NEGATIVE REINFORCEMENT: Critic found flaws
            # Severity determines magnitude of negative reward
            severity_penalties = {
                'critical': -10,  # Counterexample that disproves solution
                'major': -5,      # Significant logical gap or missing case
                'minor': -2       # Edge case or clarity issue
            }

            # Calculate total penalty for this iteration
            iteration_penalty = sum(
                severity_penalties.get(flaw.severity, -5)
                for flaw in criticism.flaws
            )

            cumulative_reward += iteration_penalty

            print(f"✗ CRITIC FOUND {len(criticism.flaws)} FLAW(S)")
            for i, flaw in enumerate(criticism.flaws, 1):
                print(f"  {i}. [{flaw.severity.upper()}] {flaw.description}")
                if flaw.counterexample:
                    print(f"     Counterexample: {flaw.counterexample}")

            print(f"Penalty: {iteration_penalty}")
            print(f"Cumulative Reward: {cumulative_reward}")

            # Store criticism for next iteration
            criticism_history.append({
                'iteration': iteration,
                'flaws': criticism.flaws,
                'counterexamples': criticism.counterexamples,
                'reward': iteration_penalty,
                'solution_snapshot': solution.content[:500]  # Store snippet
            })

        # ============================================================
        # PHASE 4: TRACK BEST SOLUTION
        # ============================================================
        # Even if current solution has flaws, it might be better than previous
        if cumulative_reward > best_reward:
            best_reward = cumulative_reward
            best_solution = solution
            print(f"\n→ New best solution (reward: {best_reward})")

        # ============================================================
        # PHASE 5: EARLY STOPPING CONDITIONS
        # ============================================================
        # If we're stuck (same criticism multiple times), try different approach
        if is_stuck(criticism_history):
            print("\n⚠ STUCK PATTERN DETECTED - Requesting strategy shift")
            generator_agent.request_strategy_shift()

        # If criticism becomes too minor, consider accepting solution
        if all(f.severity == 'minor' for f in criticism.flaws) and iteration >= 5:
            print("\n→ Only minor flaws remaining after 5 iterations")
            print("→ Consider accepting solution with minor improvements")

    # ============================================================
    # MAX ITERATIONS REACHED
    # ============================================================
    print(f"\n{'='*80}")
    print(f"MAX ITERATIONS REACHED ({max_iterations})")
    print(f"{'='*80}\n")

    return {
        'success': False,
        'solution': best_solution,
        'iterations': max_iterations,
        'total_reward': best_reward,
        'criticism_history': criticism_history,
        'status': 'partial_solution'
    }


def get_attack_intensity(iteration):
    """
    Progressive difficulty: Critic attacks get more sophisticated over time.

    This creates a curriculum of adversarial challenges:
    - Early: Find obvious flaws
    - Middle: Generate counterexamples
    - Late: Find subtle logical gaps
    """
    if iteration <= 2:
        return "basic"      # Obvious logical flaws, simple counterexamples
    elif iteration <= 5:
        return "moderate"   # Edge cases, missing cases, assumption validation
    else:
        return "advanced"   # Subtle gaps, advanced mathematical rigor


def is_stuck(criticism_history, window=3):
    """
    Detect if we're stuck in a loop (same criticism repeating).
    """
    if len(criticism_history) < window:
        return False

    recent_criticisms = criticism_history[-window:]

    # Check if the same flaw keeps appearing
    recent_flaw_types = [
        {flaw.type for flaw in crit['flaws']}
        for crit in recent_criticisms
    ]

    # If same flaw types in all recent iterations, we're stuck
    if len(recent_flaw_types) >= 2:
        intersection = set.intersection(*recent_flaw_types)
        if len(intersection) > 0:
            return True

    return False
```

## Key Components Explained

### 1. Generator Agent Interface

```python
class GeneratorAgent:
    def generate_initial_solution(self, problem, reasoning_effort="high"):
        """Generate first solution attempt."""
        prompt = f"""
        Solve the following mathematical problem with rigorous justification:

        {problem}

        Provide a complete solution with:
        1. Clear statement of approach
        2. Step-by-step logical reasoning
        3. Explicit handling of edge cases
        4. Rigorous mathematical justification
        """

        return self.llm_call(prompt, reasoning_effort=reasoning_effort)

    def revise_solution(self, problem, previous_solution, latest_criticism,
                       full_criticism_history, reasoning_effort="high"):
        """Revise solution based on adversarial feedback."""

        # Build criticism context
        criticism_summary = self._format_criticism_history(full_criticism_history)

        prompt = f"""
        Your previous solution was attacked by an adversarial critic who found flaws.

        PROBLEM:
        {problem}

        PREVIOUS SOLUTION:
        {previous_solution.content}

        ADVERSARIAL CRITICISM (Latest):
        {self._format_criticism(latest_criticism)}

        FULL CRITICISM HISTORY:
        {criticism_summary}

        Your task: Create a STRONGER solution that addresses ALL criticism.

        Requirements:
        1. Fix each identified flaw explicitly
        2. Address counterexamples directly
        3. Strengthen logical rigor where gaps were found
        4. Add edge case handling where missing
        5. Anticipate potential future attacks

        DO NOT just patch the solution. If the criticism reveals fundamental
        issues, consider a completely different approach.
        """

        return self.llm_call(prompt, reasoning_effort=reasoning_effort)

    def request_strategy_shift(self):
        """Request generator try a completely different approach."""
        self.strategy_shift_requested = True
```

### 2. Adversarial Critic Agent Interface

```python
class AdversarialCriticAgent:
    def adversarial_attack(self, problem, proposed_solution, previous_attacks,
                          attack_intensity="moderate", reasoning_effort="high"):
        """
        Adversarially attack the proposed solution.

        The critic's goal is to BREAK the solution, not just check it.
        """

        # Build attack history to avoid repeating same attacks
        attack_history = self._format_attack_history(previous_attacks)

        prompt = f"""
        You are an adversarial mathematical critic. Your goal is to BREAK this solution.

        PROBLEM:
        {problem}

        PROPOSED SOLUTION:
        {proposed_solution.content}

        PREVIOUS ATTACKS:
        {attack_history}

        Your mission: Find ANY flaw, no matter how subtle. Be aggressive and skeptical.

        Attack strategies (intensity: {attack_intensity}):
        1. COUNTEREXAMPLE GENERATION: Find specific values that break the solution
        2. EDGE CASE HUNTING: Test n=0, n=1, negative, infinity, etc.
        3. ASSUMPTION CHALLENGING: What assumptions are unstated/unjustified?
        4. LOGICAL GAP DETECTION: Where do steps not follow rigorously?
        5. COMPLETENESS CHECK: Are all cases covered in case-by-case proofs?
        6. CONSISTENCY TESTING: Any internal contradictions?

        {self._get_intensity_specific_instructions(attack_intensity)}

        For EACH flaw you find, provide:
        - Type: [counterexample|logical_gap|missing_case|assumption|edge_case|contradiction]
        - Severity: [critical|major|minor]
        - Description: Precise explanation of the flaw
        - Counterexample: Specific example that breaks it (if applicable)
        - Location: Where in the solution this flaw occurs

        CRITICAL: If after exhaustive adversarial testing you find NO flaws,
        you MUST explicitly state:
        "ADVERSARIAL VALIDATION PASSED - After rigorous adversarial testing across
        all attack vectors, no flaws were found. Solution appears sound."

        Do NOT give the solution the benefit of the doubt. Attack relentlessly.
        """

        response = self.llm_call(prompt, reasoning_effort=reasoning_effort)

        return self._parse_criticism(response)

    def _get_intensity_specific_instructions(self, intensity):
        """Get attack instructions based on intensity level."""

        if intensity == "basic":
            return """
            Focus on:
            - Obvious logical errors
            - Simple counterexamples (small integers)
            - Missing basic cases
            """

        elif intensity == "moderate":
            return """
            Focus on:
            - Edge cases (0, 1, negative, large values)
            - Unstated assumptions
            - Gaps in case-by-case reasoning
            - Simple consistency checks
            """

        else:  # advanced
            return """
            Focus on:
            - Subtle logical gaps in complex reasoning
            - Advanced counterexamples requiring mathematical insight
            - Deep consistency across entire proof
            - Mathematical rigor at the highest level
            - Implicit assumptions that require proof themselves
            """

    def _parse_criticism(self, response):
        """Parse LLM response into structured criticism."""

        # Check for validation pass
        if "ADVERSARIAL VALIDATION PASSED" in response.content:
            return Criticism(no_flaws_found=True, flaws=[])

        # Parse individual flaws
        flaws = self._extract_flaws_from_response(response.content)

        return Criticism(
            no_flaws_found=False,
            flaws=flaws,
            counterexamples=[f.counterexample for f in flaws if f.counterexample],
            raw_response=response.content
        )
```

### 3. Data Structures

```python
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Flaw:
    type: str  # counterexample|logical_gap|missing_case|assumption|edge_case|contradiction
    severity: str  # critical|major|minor
    description: str
    counterexample: Optional[str]
    location: str

@dataclass
class Criticism:
    no_flaws_found: bool
    flaws: List[Flaw]
    counterexamples: List[str]
    raw_response: str

@dataclass
class Solution:
    content: str
    iteration: int
    timestamp: str
```

## Example Interaction Flow

### Iteration 1:
**Generator:** Proposes solution using induction
**Critic:** "Your base case only checks n=1, but the problem states n≥0. Counterexample: n=0 fails."
**Signal:** -10 (critical flaw)

### Iteration 2:
**Generator:** Adds n=0 case, fixes induction base
**Critic:** "Your inductive step assumes k≥1, but this contradicts your new n=0 base case."
**Signal:** -5 (major logical gap)

### Iteration 3:
**Generator:** Restructures proof to handle n=0 separately, then prove for n≥1
**Critic:** "The inequality in step 5 is not justified. How do you know 2^k < k! for k≥4?"
**Signal:** -5 (major gap)

### Iteration 4:
**Generator:** Adds lemma proving 2^k < k! for k≥4
**Critic:** "ADVERSARIAL VALIDATION PASSED - After testing counterexamples, edge cases, and logical rigor, no flaws found."
**Signal:** +10 (SUCCESS)

## Advantages of Agentic RLAC

1. **No training required** - Pure inference-time improvement
2. **Interpretable feedback** - Concrete counterexamples and flaws
3. **Curriculum learning** - Progressive difficulty creates robust solutions
4. **Adversarial robustness** - Solutions must survive active attacks
5. **Iterative refinement** - Each round strengthens the solution
6. **Cost-effective** - Only run on inference, no expensive training

## When to Use Agentic RLAC

✓ Complex problems requiring rigor (proofs, mathematics)
✓ When correctness is critical (adversarial testing ensures robustness)
✓ When you have compute budget for multiple iterations
✓ When you want interpretable improvement (explicit flaw identification)

✗ Simple problems with obvious answers
✗ Extremely tight latency requirements
✗ When verification is impossible (purely creative tasks)

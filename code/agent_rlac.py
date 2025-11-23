"""
Agentic RLAC (Reinforcement Learning with Adversarial Critics) Agent

This implements RLAC at inference time using adversarial agent interactions.
Unlike traditional verification, the critic actively tries to BREAK solutions.

Key Innovation: Adversarial feedback loop creates reinforcement signals without training.
"""

import json
import os
import sys
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any
from datetime import datetime

# Placeholder for LLM interface - adapt to your API
# from llm_interface import LLMClient


@dataclass
class Flaw:
    """Represents a flaw found by the adversarial critic."""
    type: str  # counterexample|logical_gap|missing_case|assumption|edge_case|contradiction
    severity: str  # critical|major|minor
    description: str
    counterexample: Optional[str]
    location: str

    def to_dict(self):
        return asdict(self)


@dataclass
class Criticism:
    """Structured criticism from adversarial critic."""
    no_flaws_found: bool
    flaws: List[Flaw]
    raw_response: str
    iteration: int

    @property
    def counterexamples(self):
        return [f.counterexample for f in self.flaws if f.counterexample]

    def to_dict(self):
        return {
            'no_flaws_found': self.no_flaws_found,
            'flaws': [f.to_dict() for f in self.flaws],
            'counterexamples': self.counterexamples,
            'raw_response': self.raw_response,
            'iteration': self.iteration
        }


@dataclass
class Solution:
    """A solution attempt with metadata."""
    content: str
    iteration: int
    timestamp: str
    reward: float

    def to_dict(self):
        return asdict(self)


class GeneratorAgent:
    """
    Generator Agent: Creates and refines mathematical solutions.

    In RLAC, the generator receives negative reinforcement (penalties) when
    the critic finds flaws, and positive reinforcement when solutions survive
    adversarial attacks.
    """

    def __init__(self, llm_client, reasoning_effort="high"):
        self.llm = llm_client
        self.reasoning_effort = reasoning_effort
        self.strategy_shift_requested = False
        self.answer_reconsideration_requested = False
        self.accumulated_counterexamples = []
        self.last_answer = None

    def generate_initial_solution(self, problem: str) -> Solution:
        """Generate the first solution attempt."""

        prompt = f"""You are solving a mathematical problem. Provide a rigorous, complete solution.

PROBLEM:
{problem}

Requirements:
1. State your approach clearly
2. Provide step-by-step logical reasoning
3. Explicitly handle edge cases (n=0, n=1, etc.)
4. Justify each mathematical step
5. Consider potential counterexamples

Your solution will be tested by an adversarial critic who will try to break it.
Make it as robust as possible.

Provide your solution in clear mathematical language.
"""

        response = self.llm.generate(
            prompt=prompt,
            reasoning_effort=self.reasoning_effort
        )

        return Solution(
            content=response,
            iteration=1,
            timestamp=datetime.now().isoformat(),
            reward=0.0
        )

    def revise_solution(self, problem: str, previous_solution: Solution,
                       latest_criticism: Criticism,
                       criticism_history: List[Criticism]) -> Solution:
        """
        Revise solution based on adversarial criticism.

        This is where the 'reinforcement' happens - the generator learns from
        negative feedback (flaws found) and tries to improve.
        """

        # Format criticism for context
        criticism_summary = self._format_criticism_history(criticism_history)
        latest_flaws = self._format_latest_criticism(latest_criticism)

        # Answer reconsideration takes priority over strategy shift
        strategy_instruction = ""
        if self.answer_reconsideration_requested:
            # Accumulate counterexamples for evidence
            counterexample_evidence = "\n".join([
                f"- {ce}" for ce in self.accumulated_counterexamples[-5:]  # Last 5
            ])
            strategy_instruction = f"""
### ANSWER RECONSIDERATION MODE - YOUR ANSWER MAY BE WRONG ###

**CRITICAL**: The critic has provided VALID counterexamples across multiple rounds.
This suggests your ANSWER (not just your proof) may be fundamentally incorrect.

**Evidence Summary**:
{counterexample_evidence}

**BEFORE continuing, answer these questions:**

1. **Are these counterexamples mathematically valid?**
   Verify by direct calculation. If they ARE valid:

2. **What do they prove about the correct answer?**
   - If counterexample shows k=1 works → k=1 MUST be in the correct answer
   - List what the evidence PROVES

3. **Is your current answer compatible with this evidence?**
   If your answer EXCLUDES something the counterexamples PROVE is possible,
   YOUR ANSWER IS WRONG and must change.

4. **Your REVISED answer (if needed):**
   State what the correct answer should be based on the evidence.

**DO NOT** defend an answer that contradicts valid counterexamples.
**DO** revise your answer if the evidence proves it wrong.
            """
            self.answer_reconsideration_requested = False
        elif self.strategy_shift_requested:
            strategy_instruction = """
            IMPORTANT: Your previous approaches have been repeatedly criticized.
            Consider a FUNDAMENTALLY DIFFERENT approach to the problem.
            Don't just patch - rethink the entire strategy.
            """
            self.strategy_shift_requested = False

        prompt = f"""Your solution was attacked by an adversarial critic who found flaws.

PROBLEM:
{problem}

YOUR PREVIOUS SOLUTION (Iteration {previous_solution.iteration}):
{previous_solution.content}

ADVERSARIAL CRITICISM (Latest):
{latest_flaws}

CRITICISM HISTORY SUMMARY:
{criticism_summary}

{strategy_instruction}

Your task: Create a STRONGER solution that addresses ALL identified flaws.

For each flaw:
1. Understand the counterexample or gap
2. Fix the underlying issue (not just the symptom)
3. Verify your fix handles the edge case
4. Anticipate similar potential attacks

Requirements:
- Address each flaw explicitly
- Fix counterexamples with concrete reasoning
- Fill logical gaps with rigorous justification
- Add missing cases
- Strengthen assumptions with proofs

Be thorough - the critic will attack again even more aggressively.
"""

        response = self.llm.generate(
            prompt=prompt,
            reasoning_effort=self.reasoning_effort
        )

        return Solution(
            content=response,
            iteration=previous_solution.iteration + 1,
            timestamp=datetime.now().isoformat(),
            reward=0.0  # Will be calculated after criticism
        )

    def request_strategy_shift(self):
        """Signal that generator should try a completely different approach."""
        self.strategy_shift_requested = True

    def request_answer_reconsideration(self, counterexamples: List[str]):
        """
        Signal that the generator's ANSWER may be wrong.

        This is different from strategy_shift which just changes proof approach.
        Answer reconsideration explicitly tells the generator that their claimed
        answer (e.g., "k ∈ {0, n}") may be fundamentally incorrect based on
        counterexample evidence.

        Args:
            counterexamples: List of counterexample strings from the critic
        """
        self.answer_reconsideration_requested = True
        self.accumulated_counterexamples.extend(counterexamples)
        # Keep only the most recent counterexamples to avoid prompt explosion
        self.accumulated_counterexamples = self.accumulated_counterexamples[-10:]

    def _format_criticism_history(self, history: List[Criticism]) -> str:
        """Format criticism history for context."""
        if not history:
            return "No previous criticism."

        summary = []
        for i, crit in enumerate(history, 1):
            flaw_count = len(crit.flaws)
            summary.append(f"Iteration {i}: {flaw_count} flaw(s) found")
            for flaw in crit.flaws[:2]:  # Show first 2 flaws
                summary.append(f"  - [{flaw.severity}] {flaw.type}: {flaw.description[:100]}")

        return "\n".join(summary)

    def _format_latest_criticism(self, criticism: Criticism) -> str:
        """Format the latest criticism in detail."""
        if criticism.no_flaws_found:
            return "No flaws found - solution passed adversarial validation!"

        formatted = []
        for i, flaw in enumerate(criticism.flaws, 1):
            formatted.append(f"\nFLAW {i}: [{flaw.severity.upper()}] {flaw.type}")
            formatted.append(f"Description: {flaw.description}")
            if flaw.counterexample:
                formatted.append(f"Counterexample: {flaw.counterexample}")
            formatted.append(f"Location: {flaw.location}")

        return "\n".join(formatted)


class AdversarialCriticAgent:
    """
    Adversarial Critic Agent: Attacks solutions to find flaws.

    Unlike a traditional verifier that checks correctness, this agent is
    ADVERSARIAL - it actively tries to break the solution using:
    - Counterexample generation
    - Edge case hunting
    - Logical gap detection
    - Assumption challenging
    """

    def __init__(self, llm_client, reasoning_effort="high"):
        self.llm = llm_client
        self.reasoning_effort = reasoning_effort

    def adversarial_attack(self, problem: str, solution: Solution,
                          attack_intensity: str = "moderate") -> Criticism:
        """
        Perform adversarial attack on the solution.

        The critic's goal is to BREAK the solution, not just check it.
        This adversarial pressure creates the reinforcement signal.
        """

        intensity_instructions = self._get_intensity_instructions(attack_intensity)

        prompt = f"""You are an adversarial mathematical critic. Your goal is to BREAK this solution.

PROBLEM:
{problem}

PROPOSED SOLUTION (Iteration {solution.iteration}):
{solution.content}

YOUR MISSION: Find ANY flaw, no matter how subtle. Be aggressive and skeptical.
ASSUME THE SOLUTION IS WRONG until proven otherwise through exhaustive testing.

ATTACK STRATEGIES ({attack_intensity} intensity):
{intensity_instructions}

1. COUNTEREXAMPLE GENERATION
   - Try small values (n=0, 1, 2, 3)
   - Try edge cases (negative, infinity, boundary conditions)
   - Try special cases mentioned in the problem
   - Construct specific examples that would break the claimed result

2. LOGICAL GAP DETECTION
   - Where are steps not rigorously justified?
   - Where does the solver make logical jumps?
   - Are there implicit assumptions that need proof?

3. COMPLETENESS CHECKING
   - If proof by cases, are all cases covered?
   - Are there scenarios not considered?
   - What about degenerate cases?

4. ASSUMPTION CHALLENGING
   - What assumptions are made without justification?
   - Are there unstated prerequisites?
   - Do claimed inequalities actually hold?

5. CONSISTENCY TESTING
   - Are there internal contradictions?
   - Do different parts of the solution conflict?
   - Does the conclusion match the problem statement?

For EACH flaw you find, provide in this EXACT format:

FLAW_START
Type: [counterexample|logical_gap|missing_case|assumption|edge_case|contradiction]
Severity: [critical|major|minor]
Description: [Precise explanation of the flaw]
Counterexample: [Specific example that breaks it, or "N/A"]
Location: [Where in the solution this occurs]
FLAW_END

CRITICAL RULE: If after exhaustive adversarial testing you find NO flaws,
you MUST state exactly:
"ADVERSARIAL_VALIDATION_PASSED"

Do NOT give the benefit of the doubt. Attack relentlessly. Your job is to BREAK this.
"""

        response = self.llm.generate(
            prompt=prompt,
            reasoning_effort=self.reasoning_effort
        )

        return self._parse_criticism(response, solution.iteration)

    def _get_intensity_instructions(self, intensity: str) -> str:
        """Get attack instructions based on intensity level."""

        if intensity == "basic":
            return """
BASIC INTENSITY - Focus on obvious flaws:
- Simple logical errors
- Basic counterexamples (small integers: 0, 1, 2)
- Missing trivial cases
"""
        elif intensity == "moderate":
            return """
MODERATE INTENSITY - Dig deeper:
- Edge cases (0, 1, negative, large values)
- Unstated assumptions that need justification
- Gaps in case-by-case reasoning
- Simple consistency checks across solution
"""
        else:  # advanced
            return """
ADVANCED INTENSITY - Maximum rigor:
- Subtle logical gaps in complex reasoning chains
- Advanced counterexamples requiring mathematical insight
- Deep consistency checking across entire proof
- Mathematical rigor at research-level standards
- Implicit assumptions that themselves require proof
- Boundary cases and limiting behaviors
"""

    def _parse_criticism(self, response: str, iteration: int) -> Criticism:
        """Parse LLM response into structured Criticism object."""

        # Check for validation pass
        if "ADVERSARIAL_VALIDATION_PASSED" in response:
            return Criticism(
                no_flaws_found=True,
                flaws=[],
                raw_response=response,
                iteration=iteration
            )

        # Extract flaws using simple parsing
        flaws = []
        flaw_blocks = response.split("FLAW_START")

        for block in flaw_blocks[1:]:  # Skip first split (before any FLAW_START)
            if "FLAW_END" not in block:
                continue

            flaw_text = block.split("FLAW_END")[0].strip()

            # Parse fields
            flaw_dict = {}
            for line in flaw_text.split("\n"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    flaw_dict[key.strip().lower()] = value.strip()

            if flaw_dict:
                flaws.append(Flaw(
                    type=flaw_dict.get('type', 'unknown'),
                    severity=flaw_dict.get('severity', 'major'),
                    description=flaw_dict.get('description', ''),
                    counterexample=flaw_dict.get('counterexample') if flaw_dict.get('counterexample', 'N/A') != 'N/A' else None,
                    location=flaw_dict.get('location', 'unspecified')
                ))

        # If no structured flaws found but response contains criticism, mark as unparsed
        if not flaws and "ADVERSARIAL_VALIDATION_PASSED" not in response:
            # Fallback: create generic flaw
            flaws.append(Flaw(
                type='unparsed',
                severity='major',
                description='Critic found issues but response not in expected format',
                counterexample=None,
                location='See raw response'
            ))

        return Criticism(
            no_flaws_found=len(flaws) == 0,
            flaws=flaws,
            raw_response=response,
            iteration=iteration
        )


class RLACAgent:
    """
    Main RLAC Agent orchestrating the adversarial reinforcement learning loop.
    """

    def __init__(self, generator_llm, critic_llm,
                 max_iterations=10,
                 generator_reasoning="high",
                 critic_reasoning="high"):
        """
        Initialize RLAC agent with generator and critic.

        Args:
            generator_llm: LLM client for generator
            critic_llm: LLM client for critic (can be same as generator)
            max_iterations: Maximum RLAC iterations
            generator_reasoning: Reasoning effort for generator
            critic_reasoning: Reasoning effort for critic
        """
        self.generator = GeneratorAgent(generator_llm, generator_reasoning)
        self.critic = AdversarialCriticAgent(critic_llm, critic_reasoning)
        self.max_iterations = max_iterations

    def solve(self, problem: str, log_file: Optional[str] = None):
        """
        Solve problem using adversarial critic reinforcement learning.

        Returns:
            dict with solution, success status, reward, and history
        """

        print("="*80)
        print("AGENTIC RLAC SOLVER")
        print("="*80)
        print(f"Max iterations: {self.max_iterations}")
        print(f"Generator reasoning: {self.generator.reasoning_effort}")
        print(f"Critic reasoning: {self.critic.reasoning_effort}")
        print()

        # Initialize state
        solution = None
        criticism_history = []
        cumulative_reward = 0.0
        best_solution = None
        best_reward = -float('inf')

        for iteration in range(1, self.max_iterations + 1):
            print(f"\n{'='*80}")
            print(f"RLAC ITERATION {iteration}/{self.max_iterations}")
            print(f"{'='*80}\n")

            # PHASE 1: GENERATION
            print("PHASE 1: Solution Generation")
            if iteration == 1:
                solution = self.generator.generate_initial_solution(problem)
            else:
                solution = self.generator.revise_solution(
                    problem=problem,
                    previous_solution=solution,
                    latest_criticism=criticism_history[-1],
                    criticism_history=criticism_history
                )

            print(f"✓ Solution generated (iteration {iteration})")
            print(f"  Length: {len(solution.content)} characters")

            # PHASE 2: ADVERSARIAL CRITICISM
            print("\nPHASE 2: Adversarial Attack")
            attack_intensity = self._get_attack_intensity(iteration)
            print(f"  Attack intensity: {attack_intensity}")

            criticism = self.critic.adversarial_attack(
                problem=problem,
                solution=solution,
                attack_intensity=attack_intensity
            )

            print(f"✓ Adversarial attack complete")

            # PHASE 3: REINFORCEMENT SIGNAL
            print("\nPHASE 3: Reinforcement Signal")

            if criticism.no_flaws_found:
                # POSITIVE REINFORCEMENT
                reward = 10.0
                cumulative_reward += reward

                print(f"✓✓✓ SOLUTION SURVIVED ADVERSARIAL ATTACK ✓✓✓")
                print(f"  Reward: +{reward}")
                print(f"  Cumulative Reward: {cumulative_reward}")

                solution.reward = cumulative_reward

                # Log and return success
                result = {
                    'success': True,
                    'solution': solution.to_dict(),
                    'iterations': iteration,
                    'total_reward': cumulative_reward,
                    'criticism_history': [c.to_dict() for c in criticism_history]
                }

                if log_file:
                    self._save_result(result, log_file)

                return result

            else:
                # NEGATIVE REINFORCEMENT
                severity_penalties = {
                    'critical': -10.0,
                    'major': -5.0,
                    'minor': -2.0
                }

                iteration_penalty = sum(
                    severity_penalties.get(flaw.severity, -5.0)
                    for flaw in criticism.flaws
                )

                cumulative_reward += iteration_penalty

                print(f"✗ CRITIC FOUND {len(criticism.flaws)} FLAW(S)")
                for i, flaw in enumerate(criticism.flaws, 1):
                    print(f"  {i}. [{flaw.severity.upper()}] {flaw.type}")
                    print(f"     {flaw.description}")
                    if flaw.counterexample:
                        print(f"     Counterexample: {flaw.counterexample}")

                print(f"  Penalty: {iteration_penalty}")
                print(f"  Cumulative Reward: {cumulative_reward}")

                criticism_history.append(criticism)

            # PHASE 4: TRACK BEST
            if cumulative_reward > best_reward:
                best_reward = cumulative_reward
                best_solution = solution
                print(f"\n→ New best solution (reward: {best_reward})")

            # PHASE 5: STUCK DETECTION & ANSWER RECONSIDERATION
            stuck_info = self._analyze_stuck_pattern(criticism_history)
            if stuck_info['is_stuck']:
                if stuck_info['has_counterexamples']:
                    print("\n⚠ STUCK WITH VALID COUNTEREXAMPLES - Requesting answer reconsideration")
                    print("  Counterexamples suggest the ANSWER (not just proof) may be wrong")
                    self.generator.request_answer_reconsideration(
                        stuck_info['counterexamples']
                    )
                else:
                    print("\n⚠ STUCK PATTERN DETECTED - Requesting strategy shift")
                    self.generator.request_strategy_shift()

            # Accept if only minor flaws after several iterations
            if (all(f.severity == 'minor' for f in criticism.flaws) and
                iteration >= 5):
                print("\n→ Only minor flaws remaining after 5 iterations")
                print("→ Accepting solution as good enough")

                result = {
                    'success': True,
                    'solution': best_solution.to_dict(),
                    'iterations': iteration,
                    'total_reward': best_reward,
                    'criticism_history': [c.to_dict() for c in criticism_history],
                    'status': 'accepted_with_minor_flaws'
                }

                if log_file:
                    self._save_result(result, log_file)

                return result

        # MAX ITERATIONS REACHED
        print(f"\n{'='*80}")
        print(f"MAX ITERATIONS REACHED ({self.max_iterations})")
        print(f"Returning best solution found (reward: {best_reward})")
        print(f"{'='*80}\n")

        result = {
            'success': False,
            'solution': best_solution.to_dict() if best_solution else None,
            'iterations': self.max_iterations,
            'total_reward': best_reward,
            'criticism_history': [c.to_dict() for c in criticism_history],
            'status': 'max_iterations_reached'
        }

        if log_file:
            self._save_result(result, log_file)

        return result

    def _get_attack_intensity(self, iteration: int) -> str:
        """Progressive difficulty curriculum."""
        if iteration <= 2:
            return "basic"
        elif iteration <= 5:
            return "moderate"
        else:
            return "advanced"

    def _is_stuck(self, criticism_history: List[Criticism], window: int = 3) -> bool:
        """Detect stuck patterns (same criticism repeating)."""
        return self._analyze_stuck_pattern(criticism_history, window)['is_stuck']

    def _analyze_stuck_pattern(self, criticism_history: List[Criticism], window: int = 3) -> dict:
        """
        Analyze stuck patterns with detailed information.

        Returns dict with:
            - is_stuck: bool
            - has_counterexamples: bool (if stuck with counterexamples, answer may be wrong)
            - counterexamples: List[str] of recent counterexamples
            - reason: str explaining why stuck
        """
        result = {
            'is_stuck': False,
            'has_counterexamples': False,
            'counterexamples': [],
            'reason': ''
        }

        if len(criticism_history) < window:
            return result

        recent = criticism_history[-window:]

        # Collect all counterexamples from recent rounds
        all_counterexamples = []
        for crit in recent:
            for flaw in crit.flaws:
                if flaw.counterexample:
                    all_counterexamples.append(flaw.counterexample)

        # Check if same flaw types keep appearing
        recent_flaw_types = [
            {flaw.type for flaw in crit.flaws}
            for crit in recent
        ]

        if len(recent_flaw_types) >= 2:
            intersection = set.intersection(*recent_flaw_types)
            if len(intersection) > 0:
                result['is_stuck'] = True
                result['reason'] = f"Same flaw types repeating: {intersection}"

                # KEY INSIGHT: If stuck with counterexamples, the ANSWER may be wrong
                if all_counterexamples:
                    result['has_counterexamples'] = True
                    result['counterexamples'] = all_counterexamples
                    result['reason'] += " (with counterexamples - answer may be wrong)"

        # Also check if all recent rounds have 'broken' verdicts with counterexamples
        all_have_flaws = all(len(crit.flaws) > 0 for crit in recent)
        if all_have_flaws and all_counterexamples:
            result['is_stuck'] = True
            result['has_counterexamples'] = True
            result['counterexamples'] = all_counterexamples
            result['reason'] = "All recent rounds have flaws with counterexamples"

        return result

    def _save_result(self, result: dict, log_file: str):
        """Save result to log file."""
        with open(log_file, 'w') as f:
            json.dump(result, f, indent=2)


# =============================================================================
# TIER 5: LLM CLIENT WRAPPER - Integration with GPT-OSS API
# =============================================================================

class GPTOSSClient:
    """
    LLM Client wrapper for GPT-OSS API integration.
    (Tier 5: RLAC Full Integration)

    This provides the LLM interface required by GeneratorAgent and AdversarialCriticAgent,
    connecting them to the GPT-OSS API backend used by agent_gpt_oss.py.
    """

    def __init__(self, api_url: str = None, api_key: str = None):
        """
        Initialize GPT-OSS client.

        Args:
            api_url: API endpoint (defaults to GPT_OSS_API_URL env var)
            api_key: API key (defaults to GPT_OSS_API_KEY env var)
        """
        self.api_url = api_url or os.environ.get('GPT_OSS_API_URL', 'http://localhost:30000/v1/chat/completions')
        self.api_key = api_key or os.environ.get('GPT_OSS_API_KEY', '')

    def generate(self, prompt: str, reasoning_effort: str = "high",
                system_prompt: str = None, timeout: int = 600) -> str:
        """
        Generate text using GPT-OSS API.

        Args:
            prompt: User prompt
            reasoning_effort: Reasoning level ("low", "medium", "high")
            system_prompt: Optional system prompt
            timeout: Request timeout in seconds

        Returns:
            Generated text response
        """
        import requests

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": "gpt",  # Model name for GPT-OSS
            "messages": messages,
            "temperature": 1.0,
            "stream": False
        }

        # Add reasoning effort if supported
        if reasoning_effort:
            payload["reasoning_effort"] = reasoning_effort

        headers = {
            "Content-Type": "application/json"
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            response = requests.post(
                self.api_url,
                json=payload,
                headers=headers,
                timeout=timeout
            )
            response.raise_for_status()

            result = response.json()

            # Extract text from response
            if 'choices' in result and len(result['choices']) > 0:
                return result['choices'][0].get('message', {}).get('content', '')

            return ""

        except Exception as e:
            print(f"[GPTOSSClient] API request failed: {e}")
            return ""


def create_rlac_agent_with_gpt_oss(api_url: str = None, api_key: str = None,
                                   max_iterations: int = 10,
                                   generator_reasoning: str = "low",
                                   critic_reasoning: str = "high") -> RLACAgent:
    """
    Factory function to create an RLACAgent with GPT-OSS backend.
    (Tier 5: RLAC Full Integration)

    This provides an easy way to instantiate the full RLAC pipeline
    connected to the GPT-OSS API.

    Args:
        api_url: GPT-OSS API URL (defaults to env var)
        api_key: GPT-OSS API key (defaults to env var)
        max_iterations: Maximum RLAC iterations
        generator_reasoning: Reasoning effort for generator
        critic_reasoning: Reasoning effort for critic

    Returns:
        Configured RLACAgent ready to solve problems
    """
    client = GPTOSSClient(api_url=api_url, api_key=api_key)

    return RLACAgent(
        generator_llm=client,
        critic_llm=client,  # Can use same client for both
        max_iterations=max_iterations,
        generator_reasoning=generator_reasoning,
        critic_reasoning=critic_reasoning
    )


# Example usage
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="RLAC Agent - Adversarial Reinforcement Learning")
    parser.add_argument("problem_file", nargs="?", help="Path to problem file")
    parser.add_argument("--max-iterations", type=int, default=10, help="Maximum RLAC iterations")
    parser.add_argument("--generator-reasoning", default="low", choices=["low", "medium", "high"])
    parser.add_argument("--critic-reasoning", default="high", choices=["low", "medium", "high"])
    parser.add_argument("--log", help="Log file path")
    parser.add_argument("--api-url", help="GPT-OSS API URL")
    parser.add_argument("--api-key", help="GPT-OSS API key")

    args = parser.parse_args()

    if args.problem_file:
        # Run with actual problem
        with open(args.problem_file, 'r') as f:
            problem = f.read()

        agent = create_rlac_agent_with_gpt_oss(
            api_url=args.api_url,
            api_key=args.api_key,
            max_iterations=args.max_iterations,
            generator_reasoning=args.generator_reasoning,
            critic_reasoning=args.critic_reasoning
        )

        result = agent.solve(problem, log_file=args.log)

        print("\n" + "="*80)
        print("RLAC RESULT")
        print("="*80)
        print(f"Success: {result.get('success', False)}")
        print(f"Iterations: {result.get('iterations', 0)}")
        print(f"Total Reward: {result.get('total_reward', 0)}")

    else:
        # Show help
        print("RLAC Agent Implementation (Tier 5: Full Integration)")
        print("="*60)
        print()
        print("Key components:")
        print("- GeneratorAgent: Creates and refines solutions")
        print("- AdversarialCriticAgent: Attacks solutions to find flaws")
        print("- RLACAgent: Orchestrates adversarial reinforcement learning loop")
        print("- GPTOSSClient: LLM client wrapper for GPT-OSS API")
        print()
        print("Usage:")
        print("  python agent_rlac.py problem.txt --log output.json")
        print()
        print("The adversarial feedback loop creates reinforcement signals:")
        print("- Negative: Critic finds flaw → penalty → generator improves")
        print("- Positive: Solution survives attack → reward → success")

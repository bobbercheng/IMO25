"""
Adversarial Critic Module for RLAC

This module implements an adversarial critic that actively tries to break mathematical
solutions through counterexample generation, edge case testing, and assumption challenging.

Key Features:
- Adversarial attack generation with progressive difficulty
- Structured feedback parsing (counterexamples, flaws, severity scores)
- Comprehensive logging for troubleshooting and data collection
- Attack history tracking for curriculum learning
"""

import json
import re
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any

from adversarial_prompts import (
    adversarial_critic_system_prompt,
    get_attack_intensity_prompt,
    build_rlac_control_prompt,
    adversarial_defense_prompt,
    counterexample_generation_prompt
)


class AdversarialCritic:
    """
    Adversarial critic that actively tries to break mathematical solutions.

    Unlike cooperative verification which grades solutions, this critic:
    - Assumes solutions are wrong until proven robust
    - Generates concrete counterexamples
    - Tests boundary cases systematically
    - Challenges implicit assumptions
    - Provides structured feedback with severity scores
    """

    def __init__(self, reasoning_effort="high", verbose=True, log_file=None):
        """
        Initialize the adversarial critic.

        Args:
            reasoning_effort: Reasoning level for attacks ("low", "medium", "high")
                             Recommended: "high" for rigorous adversarial attacks
            verbose: Enable detailed logging
            log_file: Optional file handle for logging (uses agent's log_file if None)
        """
        self.reasoning_effort = reasoning_effort
        self.verbose = verbose
        self.log_file = log_file

        # Attack history for tracking progress
        self.attack_history = []

        # Metrics for data collection
        self.total_attacks = 0
        self.total_counterexamples = 0
        self.total_broken_solutions = 0
        self.total_robust_solutions = 0

        if self.verbose:
            self._log(f"[ADVERSARIAL CRITIC] Initialized with reasoning_effort={reasoning_effort}")

    def _log(self, message):
        """Log message with timestamp."""
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_msg = f"[{timestamp}] {message}"
        print(log_msg)

    def attack_solution(self, problem_statement, solution, round_num=0, max_rounds=10,
                       api_request_func=None, api_key=None) -> Dict[str, Any]:
        """
        Attack a solution with adversarial testing.

        Args:
            problem_statement: Original problem text
            solution: Solution to attack
            round_num: Current RLAC round number (0-indexed)
            max_rounds: Maximum RLAC rounds
            api_request_func: Function to send API requests (from agent_gpt_oss)
            api_key: API key for requests

        Returns:
            Dict containing:
                - verdict: "BROKEN" / "SUSPICIOUS" / "ROBUST"
                - counterexamples: List of counterexample strings
                - critical_flaws: List of critical flaw strings
                - major_issues: List of major issue strings
                - minor_issues: List of minor issue strings
                - total_penalty: Total penalty score
                - full_attack: Complete attack text
                - round_num: Round number for tracking
                - timestamp: Attack timestamp
        """
        if self.verbose:
            self._log(f"\n{'='*80}")
            self._log(f"[ADVERSARIAL CRITIC] Round {round_num + 1}/{max_rounds}")
            self._log(f"{'='*80}\n")

        # Get attack intensity based on round (curriculum learning)
        intensity_name, intensity_prompt = get_attack_intensity_prompt(round_num, max_rounds)

        # PROGRESSIVE REASONING EFFORT: Start low, increase to high
        # Rounds 0-2: LOW reasoning (quick basic attacks)
        # Rounds 3-6: MEDIUM reasoning (moderate attacks)
        # Rounds 7+: HIGH reasoning (advanced rigorous attacks)
        progressive_reasoning = self._get_progressive_reasoning_effort(round_num, max_rounds)

        if self.verbose:
            self._log(f"[ADVERSARIAL CRITIC] Attack intensity: {intensity_name}")
            self._log(f"[ADVERSARIAL CRITIC] Base reasoning effort: {self.reasoning_effort}")
            self._log(f"[ADVERSARIAL CRITIC] Progressive reasoning effort: {progressive_reasoning}")
            if progressive_reasoning != self.reasoning_effort:
                self._log(f"[ADVERSARIAL CRITIC] Using progressive reasoning (overriding base)")


        # Build RLAC control prompt with history
        control_prompt = build_rlac_control_prompt(
            round_num, max_rounds, intensity_name, self.attack_history
        )

        # Build complete attack prompt
        attack_prompt = f"""
{control_prompt}

{intensity_prompt}

### Problem ###
{problem_statement}

### Solution to Attack ###
{solution}

### Your Attack ###
Try HARD to break this solution. Generate counterexamples, test boundaries, challenge assumptions.
Remember: You are rewarded for finding flaws, not for accepting solutions.

Follow the output format specified in your system prompt.
"""

        if self.verbose:
            self._log(f"[ADVERSARIAL CRITIC] Attack prompt constructed ({len(attack_prompt)} chars)")

        # Send attack request
        if api_request_func is None:
            # Import from agent_gpt_oss if not provided
            from agent_gpt_oss import build_request_payload, send_api_request, extract_text_from_response, get_api_key
            api_request_func = send_api_request
            api_key = get_api_key()

            payload = build_request_payload(
                system_prompt=adversarial_critic_system_prompt,
                question_prompt=attack_prompt,
                reasoning_effort=progressive_reasoning  # Use progressive reasoning
            )
        else:
            # Use provided function
            from agent_gpt_oss import build_request_payload, extract_text_from_response
            payload = build_request_payload(
                system_prompt=adversarial_critic_system_prompt,
                question_prompt=attack_prompt,
                reasoning_effort=progressive_reasoning  # Use progressive reasoning
            )

        if self.verbose:
            self._log(f"[ADVERSARIAL CRITIC] Sending attack request...")

        start_time = datetime.now()
        response = api_request_func(api_key, payload)
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        attack_result = extract_text_from_response(response)

        if self.verbose:
            self._log(f"[ADVERSARIAL CRITIC] Attack completed in {duration:.1f}s")
            self._log(f"[ADVERSARIAL CRITIC] Response length: {len(attack_result)} chars")

        # Parse attack result
        parsed_result = self._parse_attack_result(attack_result, round_num)

        # Update metrics
        self.total_attacks += 1
        self.total_counterexamples += len(parsed_result['counterexamples'])
        if parsed_result['verdict'] == 'BROKEN':
            self.total_broken_solutions += 1
        elif parsed_result['verdict'] == 'ROBUST':
            self.total_robust_solutions += 1

        # Add to history
        self.attack_history.append(parsed_result)

        # Log summary
        if self.verbose:
            self._log_attack_summary(parsed_result)

        return parsed_result

    def _get_progressive_reasoning_effort(self, round_num: int, max_rounds: int) -> str:
        """
        Get progressive reasoning effort based on round number.

        Implements curriculum learning for critic:
        - Early rounds (0-2): LOW reasoning for quick basic attacks
        - Middle rounds (3-6): MEDIUM reasoning for moderate attacks
        - Late rounds (7+): HIGH reasoning for advanced rigorous attacks

        Args:
            round_num: Current round (0-indexed)
            max_rounds: Maximum rounds

        Returns:
            Reasoning effort string: "low", "medium", or "high"
        """
        if round_num < 3:
            return "low"
        elif round_num < 7:
            return "medium"
        else:
            return "high"

    def _parse_attack_result(self, attack_text: str, round_num: int) -> Dict[str, Any]:
        """
        Parse adversarial attack result into structured format.

        Args:
            attack_text: Raw attack output from critic
            round_num: Current round number

        Returns:
            Structured attack result dictionary
        """
        result = {
            'verdict': 'UNKNOWN',
            'counterexamples': [],
            'critical_flaws': [],
            'major_issues': [],
            'minor_issues': [],
            'boundary_cases': [],
            'assumption_challenges': [],
            'total_penalty': 0,
            'full_attack': attack_text,
            'round_num': round_num,
            'timestamp': datetime.now().isoformat()
        }

        # Extract verdict
        result['verdict'] = self._extract_verdict(attack_text)

        # Extract counterexamples
        result['counterexamples'] = self._extract_counterexamples(attack_text)

        # Extract critical flaws
        result['critical_flaws'] = self._extract_section(attack_text, 'CRITICAL FLAWS')

        # Extract boundary cases
        result['boundary_cases'] = self._extract_section(attack_text, 'BOUNDARY CASES')

        # Extract assumption challenges
        result['assumption_challenges'] = self._extract_section(attack_text, 'ASSUMPTION CHALLENGES')

        # Calculate penalty score
        result['total_penalty'] = self._calculate_penalty(result)

        # Extract counts from severity scores if present
        severity_match = re.search(r'Critical flaws:\s*(\d+)', attack_text)
        if severity_match:
            result['critical_count'] = int(severity_match.group(1))
        else:
            result['critical_count'] = len(result['critical_flaws'])

        major_match = re.search(r'Major issues:\s*(\d+)', attack_text)
        if major_match:
            result['major_count'] = int(major_match.group(1))
        else:
            result['major_count'] = len(result['boundary_cases']) + len(result['assumption_challenges'])

        minor_match = re.search(r'Minor issues:\s*(\d+)', attack_text)
        if minor_match:
            result['minor_count'] = int(minor_match.group(1))
        else:
            result['minor_count'] = 0

        return result

    def _extract_verdict(self, attack_text: str) -> str:
        """Extract verdict from attack result."""
        text_upper = attack_text.upper()

        # Look for explicit verdict
        verdict_patterns = [
            r'ADVERSARIAL VERDICT[:\s]+(\w+)',
            r'VERDICT[:\s]+(\w+)',
            r'\*\*VERDICT\*\*[:\s]+(\w+)'
        ]

        for pattern in verdict_patterns:
            match = re.search(pattern, text_upper)
            if match:
                verdict = match.group(1)
                if 'BROKEN' in verdict:
                    return 'BROKEN'
                elif 'ROBUST' in verdict:
                    return 'ROBUST'
                elif 'SUSPICIOUS' in verdict:
                    return 'SUSPICIOUS'

        # Fallback: infer from content
        if 'BROKEN' in text_upper or 'COUNTEREXAMPLE' in text_upper:
            return 'BROKEN'
        elif 'ROBUST' in text_upper or 'NO FLAWS' in text_upper:
            return 'ROBUST'
        elif 'SUSPICIOUS' in text_upper:
            return 'SUSPICIOUS'

        return 'UNKNOWN'

    def _extract_counterexamples(self, attack_text: str) -> List[str]:
        """Extract counterexamples from attack result."""
        counterexamples = []

        # Pattern 1: Numbered counterexamples
        pattern1 = r'(?:Counterexample|Counter-example)\s+\d+[:\s]+(.+?)(?=(?:Counterexample|Counter-example)\s+\d+|BOUNDARY|ASSUMPTION|CRITICAL|$)'
        matches = re.findall(pattern1, attack_text, re.DOTALL | re.IGNORECASE)
        counterexamples.extend([m.strip() for m in matches if m.strip()])

        # Pattern 2: Bulleted counterexamples
        pattern2 = r'-\s+(?:Counterexample|Counter-example)[:\s]+(.+?)(?=\n-|\n\n|$)'
        matches = re.findall(pattern2, attack_text, re.DOTALL | re.IGNORECASE)
        counterexamples.extend([m.strip() for m in matches if m.strip()])

        # Pattern 3: Section-based extraction
        ce_section = self._extract_section(attack_text, 'COUNTEREXAMPLES FOUND')
        counterexamples.extend(ce_section)

        # Remove duplicates while preserving order
        seen = set()
        unique_counterexamples = []
        for ce in counterexamples:
            if ce and ce not in seen:
                seen.add(ce)
                unique_counterexamples.append(ce)

        return unique_counterexamples

    def _extract_section(self, text: str, section_name: str) -> List[str]:
        """Extract items from a named section."""
        items = []

        # Find section header
        section_pattern = rf'\*\*{section_name}\*\*:?\s*\n(.*?)(?=\n\*\*|\n\n[A-Z]|$)'
        match = re.search(section_pattern, text, re.DOTALL | re.IGNORECASE)

        if match:
            section_content = match.group(1)

            # Extract numbered items
            numbered_items = re.findall(r'(?:^|\n)\s*[\d\-\*]+\.?\s+(.+?)(?=\n[\d\-\*]|\n\n|$)', section_content, re.DOTALL)
            items.extend([item.strip() for item in numbered_items if item.strip()])

        return items

    def _calculate_penalty(self, result: Dict[str, Any]) -> int:
        """
        Calculate total penalty score based on severity.

        Scoring:
        - Critical flaw (counterexample): -10 points
        - Major issue (boundary/assumption): -5 points
        - Minor issue: -2 points
        """
        penalty = 0
        penalty += len(result['counterexamples']) * 10  # Critical
        penalty += len(result['critical_flaws']) * 10    # Critical
        penalty += len(result['boundary_cases']) * 5     # Major
        penalty += len(result['assumption_challenges']) * 5  # Major
        penalty += result.get('minor_count', 0) * 2      # Minor

        return penalty

    def _log_attack_summary(self, result: Dict[str, Any]):
        """Log a summary of the attack results."""
        self._log(f"\n{'='*80}")
        self._log(f"[ADVERSARIAL CRITIC] Attack Summary - Round {result['round_num'] + 1}")
        self._log(f"{'='*80}")
        self._log(f"[ADVERSARIAL CRITIC] Verdict: {result['verdict']}")
        self._log(f"[ADVERSARIAL CRITIC] Counterexamples: {len(result['counterexamples'])}")
        self._log(f"[ADVERSARIAL CRITIC] Critical flaws: {len(result['critical_flaws'])}")
        self._log(f"[ADVERSARIAL CRITIC] Boundary cases: {len(result['boundary_cases'])}")
        self._log(f"[ADVERSARIAL CRITIC] Assumption challenges: {len(result['assumption_challenges'])}")
        self._log(f"[ADVERSARIAL CRITIC] Total penalty: -{result['total_penalty']} points")

        # Log specific counterexamples
        if result['counterexamples']:
            self._log(f"\n[ADVERSARIAL CRITIC] Counterexamples found:")
            for i, ce in enumerate(result['counterexamples'][:3], 1):  # Show first 3
                self._log(f"[ADVERSARIAL CRITIC]   {i}. {ce[:100]}{'...' if len(ce) > 100 else ''}")

        # Log critical flaws
        if result['critical_flaws']:
            self._log(f"\n[ADVERSARIAL CRITIC] Critical flaws:")
            for i, flaw in enumerate(result['critical_flaws'][:3], 1):
                self._log(f"[ADVERSARIAL CRITIC]   {i}. {flaw[:100]}{'...' if len(flaw) > 100 else ''}")

        self._log(f"{'='*80}\n")

    def get_defense_prompt(self, attack_result: Dict[str, Any]) -> str:
        """
        Generate defense prompt for the generator based on attack results.

        Args:
            attack_result: Parsed attack result dictionary

        Returns:
            Formatted defense prompt string
        """
        return adversarial_defense_prompt.format(
            adversarial_feedback=attack_result['full_attack']
        )

    def get_metrics_summary(self) -> Dict[str, Any]:
        """
        Get overall metrics summary for the critic.

        Returns:
            Dictionary with overall performance metrics
        """
        return {
            'total_attacks': self.total_attacks,
            'total_counterexamples': self.total_counterexamples,
            'total_broken_solutions': self.total_broken_solutions,
            'total_robust_solutions': self.total_robust_solutions,
            'total_suspicious': self.total_attacks - self.total_broken_solutions - self.total_robust_solutions,
            'broken_rate': self.total_broken_solutions / self.total_attacks if self.total_attacks > 0 else 0,
            'robust_rate': self.total_robust_solutions / self.total_attacks if self.total_attacks > 0 else 0,
            'avg_counterexamples_per_attack': self.total_counterexamples / self.total_attacks if self.total_attacks > 0 else 0
        }

    def save_attack_history(self, filepath: str):
        """
        Save attack history to JSON file for analysis.

        Args:
            filepath: Path to save attack history
        """
        history_data = {
            'attack_history': self.attack_history,
            'metrics': self.get_metrics_summary(),
            'timestamp': datetime.now().isoformat()
        }

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(history_data, f, indent=2, ensure_ascii=False)

            if self.verbose:
                self._log(f"[ADVERSARIAL CRITIC] Attack history saved to {filepath}")
            return True
        except Exception as e:
            if self.verbose:
                self._log(f"[ADVERSARIAL CRITIC] Error saving attack history: {e}")
            return False

    def detect_stuck_pattern(self, recent_rounds: int = 3) -> bool:
        """
        Detect if the generator is stuck (not addressing attacks).

        Args:
            recent_rounds: Number of recent rounds to check

        Returns:
            True if stuck pattern detected
        """
        if len(self.attack_history) < recent_rounds:
            return False

        recent_attacks = self.attack_history[-recent_rounds:]

        # Stuck if all recent attacks found issues but verdict didn't improve
        all_broken = all(a['verdict'] == 'BROKEN' for a in recent_attacks)
        all_have_counterexamples = all(len(a['counterexamples']) > 0 for a in recent_attacks)

        if all_broken and all_have_counterexamples:
            if self.verbose:
                self._log(f"\n{'='*80}")
                self._log(f"[ADVERSARIAL CRITIC] STUCK PATTERN DETECTED")
                self._log(f"[ADVERSARIAL CRITIC] Last {recent_rounds} rounds all BROKEN with counterexamples")
                self._log(f"[ADVERSARIAL CRITIC] Generator may be unable to address attacks")
                self._log(f"{'='*80}\n")
            return True

        return False

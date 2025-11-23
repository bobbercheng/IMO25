"""
Adversarial Critic Module for RLAC

This module implements an adversarial critic that actively tries to break mathematical
solutions through counterexample generation, edge case testing, and assumption challenging.

Key Features:
- Adversarial attack generation with progressive difficulty
- Structured feedback parsing (counterexamples, flaws, severity scores)
- Comprehensive logging for troubleshooting and data collection
- Attack history tracking for curriculum learning

Enhanced Features (Counter-Proposals):
1. Validation Pipeline with fail-fast + retry strategy (vs format enforcement)
2. Proper brace-matching LaTeX parser + semantic normalization (vs fallback)
3. Explicit state machine + confidence scoring + history tracking (vs simple states)
"""

import json
import re
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any

# Import enhanced components
from rlac_improvements import (
    SolutionValidationPipeline,
    LaTeXBraceParser,
    VerdictStateMachine,
    VerdictState,
    VerdictConfidence,
    PipelineResult,
    LaTeXParseResult,
    run_enhanced_rlac_round,
    create_enhanced_critic_wrapper
)

from adversarial_prompts import (
    adversarial_critic_system_prompt,
    get_attack_intensity_prompt,
    build_rlac_control_prompt,
    adversarial_defense_prompt,
    counterexample_generation_prompt,
    defense_first_generator_prompt,
    defense_first_revision_prompt,
    answer_reconsideration_prompt,  # NEW: For when answer is fundamentally wrong
    small_case_verification_prompt,
    small_case_verification_instruction,
    error_severity_classification,
    classify_error_severity,
    calculate_verdict_from_errors
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

        # Build complete attack prompt with small-case verification
        attack_prompt = f"""
{control_prompt}

{intensity_prompt}

{small_case_verification_instruction}

### Problem ###
{problem_statement}

### Solution to Attack ###
{solution}

### Your Attack ###
Try HARD to break this solution. Generate counterexamples, test boundaries, challenge assumptions.
Remember: You are rewarded for finding flaws, not for accepting solutions.

**MANDATORY**: Before giving your verdict, perform small-case verification:
1. Pick 3-5 small concrete values (n=1, 2, 3, 4, 5 or appropriate)
2. Compute what the solution claims for each case
3. Verify by direct calculation
4. Report any mismatch as a COUNTEREXAMPLE

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
            'answer_implications': [],  # NEW: What counterexamples prove about correct answer
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

        # Extract counterexamples FIRST (needed for verdict validation)
        result['counterexamples'] = self._extract_counterexamples(attack_text)

        # NEW: Extract answer implications - what counterexamples prove about correct answer
        result['answer_implications'] = self._extract_answer_implications(attack_text, result['counterexamples'])

        # Extract verdict with counterexample validation
        # This fixes the bug where "Round 1 BROKEN with 0 counterexamples" could occur
        result['verdict'] = self._extract_verdict(attack_text, result['counterexamples'])

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

    def _extract_verdict(self, attack_text: str, counterexamples: List[str] = None) -> str:
        """
        Extract verdict from attack result using unified format.

        Expects unified format: ADVERSARIAL_VERDICT: [BROKEN / SUSPICIOUS / ROBUST]

        Args:
            attack_text: Raw attack output from critic
            counterexamples: Optional list of parsed counterexamples for validation

        Returns:
            Verdict string: "BROKEN" / "SUSPICIOUS" / "ROBUST" / "UNKNOWN"
        """
        # FIX: Handle None or empty attack_text to prevent crash
        if not attack_text:
            if self.verbose:
                self._log("[ADVERSARIAL CRITIC] Warning: Empty attack_text received")
            return 'UNKNOWN'

        text_upper = attack_text.upper()

        # Primary patterns: Unified format (highest priority)
        unified_patterns = [
            r'ADVERSARIAL_VERDICT\s*:\s*(\w+)',      # ADVERSARIAL_VERDICT: BROKEN (unified)
            r'###\s*VERDICT\s*###\s*\n*\s*ADVERSARIAL_VERDICT\s*:\s*(\w+)',  # Section header version
        ]

        for pattern in unified_patterns:
            match = re.search(pattern, text_upper)
            if match:
                verdict = match.group(1)
                if 'BROKEN' in verdict:
                    return 'BROKEN'
                elif 'ROBUST' in verdict:
                    return 'ROBUST'
                elif 'SUSPICIOUS' in verdict:
                    return 'SUSPICIOUS'

        # Fallback patterns (backward compatibility with old format)
        fallback_patterns = [
            r'ADVERSARIAL\s+VERDICT[:\s]+(\w+)',     # ADVERSARIAL VERDICT: BROKEN
            r'\*\*ADVERSARIAL\s+VERDICT\*\*[:\s]+(\w+)',  # **ADVERSARIAL VERDICT**: BROKEN
            r'\*\*VERDICT\*\*[:\s]+(\w+)',           # **VERDICT**: BROKEN
            r'VERDICT[:\s]+(\w+)',                    # VERDICT: BROKEN
        ]

        for pattern in fallback_patterns:
            match = re.search(pattern, text_upper)
            if match:
                verdict = match.group(1)
                if 'BROKEN' in verdict:
                    return 'BROKEN'
                elif 'ROBUST' in verdict:
                    return 'ROBUST'
                elif 'SUSPICIOUS' in verdict:
                    return 'SUSPICIOUS'

        # Content-based inference (last resort)
        # FIX: Only mark as BROKEN if there are ACTUAL counterexamples found,
        # not just because the word "counterexample" or "BROKEN" appears in the text
        has_actual_counterexamples = counterexamples and len(counterexamples) > 0

        # FIX: Check for ROBUST/pass indicators FIRST (they're more reliable)
        if 'ADVERSARIAL_VALIDATION_PASSED' in text_upper or 'NO FLAWS' in text_upper.replace('_', ' '):
            return 'ROBUST'
        elif 'ROBUST' in text_upper and 'NOT ROBUST' not in text_upper:
            return 'ROBUST'

        # FIX: Only mark as BROKEN if we have actual counterexamples
        # The word "BROKEN" alone doesn't mean the solution is broken
        # (e.g., "This is NOT BROKEN" or "what a BROKEN solution looks like")
        if has_actual_counterexamples:
            return 'BROKEN'
        elif 'BROKEN' in text_upper and has_actual_counterexamples:
            # Word BROKEN + actual counterexamples = definitely broken
            return 'BROKEN'
        elif 'COUNTEREXAMPLE' in text_upper and not has_actual_counterexamples:
            # Mentions counterexamples but none parsed - suspicious, not broken
            return 'SUSPICIOUS'
        elif 'BROKEN' in text_upper and not has_actual_counterexamples:
            # Word BROKEN but no actual counterexamples - suspicious
            # FIX: Changed from returning 'BROKEN' to 'SUSPICIOUS'
            return 'SUSPICIOUS'
        elif 'SUSPICIOUS' in text_upper:
            return 'SUSPICIOUS'

        return 'UNKNOWN'

    def _extract_counterexamples(self, attack_text: str) -> List[str]:
        """
        Extract counterexamples from attack result using unified format.

        Expects unified format:
        COUNTEREXAMPLE_1: [example]
        COUNTEREXAMPLE_2: [example]
        ...

        Returns:
            List of counterexample strings
        """
        counterexamples = []

        # Primary pattern: Unified format (COUNTEREXAMPLE_N: ...)
        unified_pattern = r'COUNTEREXAMPLE_(\d+)\s*:\s*(.+?)(?=COUNTEREXAMPLE_\d+|###|BOUNDARY|IMPLICATION|FLAW|CHALLENGE|SEVERITY|NO_COUNTEREXAMPLES|$)'
        matches = re.findall(unified_pattern, attack_text, re.DOTALL | re.IGNORECASE)
        for num, content in matches:
            content = content.strip()
            if content and content.upper() != 'NO_COUNTEREXAMPLES_FOUND':
                counterexamples.append(content)

        # Fallback pattern 1: Numbered counterexamples (Counterexample 1:)
        if not counterexamples:
            pattern1 = r'(?:Counterexample|Counter-example)\s+\d+[:\s]+(.+?)(?=(?:Counterexample|Counter-example)\s+\d+|BOUNDARY|ASSUMPTION|CRITICAL|###|$)'
            matches = re.findall(pattern1, attack_text, re.DOTALL | re.IGNORECASE)
            counterexamples.extend([m.strip() for m in matches if m.strip()])

        # Fallback pattern 2: Bulleted counterexamples (- Counterexample:)
        if not counterexamples:
            pattern2 = r'-\s+(?:Counterexample|Counter-example)[:\s]+(.+?)(?=\n-|\n\n|###|$)'
            matches = re.findall(pattern2, attack_text, re.DOTALL | re.IGNORECASE)
            counterexamples.extend([m.strip() for m in matches if m.strip()])

        # Fallback pattern 3: Section-based extraction (old format)
        if not counterexamples:
            ce_section = self._extract_section(attack_text, 'COUNTEREXAMPLES FOUND')
            counterexamples.extend(ce_section)
            # Also try new section name
            ce_section2 = self._extract_section(attack_text, 'COUNTEREXAMPLES')
            counterexamples.extend(ce_section2)

        # Remove duplicates while preserving order
        seen = set()
        unique_counterexamples = []
        for ce in counterexamples:
            if ce and ce not in seen:
                seen.add(ce)
                unique_counterexamples.append(ce)

        return unique_counterexamples

    def _extract_answer_implications(self, attack_text: str, counterexamples: List[str]) -> List[str]:
        """
        Extract answer implications - what counterexamples prove about the correct answer.

        Expects unified format:
        ### ANSWER_IMPLICATIONS ###
        IMPLICATION: [What the counterexamples prove about the correct answer]

        This is CRITICAL for closing the feedback loop. Without explicit implications,
        the generator may acknowledge counterexamples but not understand how they
        affect the answer.

        Args:
            attack_text: Raw attack output from critic
            counterexamples: List of extracted counterexamples

        Returns:
            List of answer implication strings
        """
        implications = []

        # Primary pattern: Unified format (IMPLICATION: ...)
        unified_pattern = r'IMPLICATION\s*:\s*(.+?)(?=IMPLICATION|###|BOUNDARY|FLAW|CHALLENGE|SEVERITY|$)'
        matches = re.findall(unified_pattern, attack_text, re.DOTALL | re.IGNORECASE)
        for m in matches:
            m = m.strip()
            if m and m.upper() not in ('N/A', 'NA', 'NONE', ''):
                implications.append(m)

        # Also try ### ANSWER_IMPLICATIONS ### section
        answer_impl_section = self._extract_section(attack_text, 'ANSWER_IMPLICATIONS')
        implications.extend(answer_impl_section)

        # Fallback pattern 1: "WHAT THE ANSWER SHOULD BE" section (old format)
        if not implications:
            answer_section = self._extract_section(attack_text, 'WHAT THE ANSWER SHOULD BE')
            implications.extend(answer_section)

        # Fallback pattern 2: Answer_Implication field from FLAW_START blocks
        if not implications:
            impl_pattern = r'Answer[_\s]?Implication[:\s]+(.+?)(?=\n[A-Z]|FLAW_END|$)'
            matches = re.findall(impl_pattern, attack_text, re.DOTALL | re.IGNORECASE)
            for m in matches:
                m = m.strip()
                if m and m.upper() not in ('N/A', 'NA', 'NONE', ''):
                    implications.append(m)

        # Fallback pattern 3: "This proves..." statements
        proves_pattern = r'(?:This|The counterexample|This counterexample)\s+proves\s+(.+?)(?=\.|$)'
        matches = re.findall(proves_pattern, attack_text, re.IGNORECASE)
        implications.extend([m.strip() for m in matches if m.strip()])

        # Fallback pattern 4: "The correct answer should..." statements
        correct_pattern = r'(?:The )?correct answer should\s+(.+?)(?=\.|$)'
        matches = re.findall(correct_pattern, attack_text, re.IGNORECASE)
        implications.extend([f"Correct answer should {m.strip()}" for m in matches if m.strip()])

        # Fallback pattern 5: "must include" / "must exclude" / "cannot include"
        must_pattern = r'(?:answer|solution)\s+(must\s+(?:include|exclude|be)|cannot\s+include)\s+(.+?)(?=\.|,|$)'
        matches = re.findall(must_pattern, attack_text, re.IGNORECASE)
        implications.extend([f"Answer {m[0]} {m[1].strip()}" for m in matches if m[1].strip()])

        # Auto-generate implications from counterexamples if none found
        if not implications and counterexamples:
            for ce in counterexamples[:3]:  # Limit to first 3
                implications.append(f"Counterexample '{ce[:100]}' suggests answer may need revision")

        # Remove duplicates while preserving order
        seen = set()
        unique_implications = []
        for impl in implications:
            if impl and impl not in seen:
                seen.add(impl)
                unique_implications.append(impl)

        return unique_implications

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
        self._log(f"[ADVERSARIAL CRITIC] Answer implications: {len(result.get('answer_implications', []))}")
        self._log(f"[ADVERSARIAL CRITIC] Critical flaws: {len(result['critical_flaws'])}")
        self._log(f"[ADVERSARIAL CRITIC] Boundary cases: {len(result['boundary_cases'])}")
        self._log(f"[ADVERSARIAL CRITIC] Assumption challenges: {len(result['assumption_challenges'])}")
        self._log(f"[ADVERSARIAL CRITIC] Total penalty: -{result['total_penalty']} points")

        # Log specific counterexamples
        if result['counterexamples']:
            self._log(f"\n[ADVERSARIAL CRITIC] Counterexamples found:")
            for i, ce in enumerate(result['counterexamples'][:3], 1):  # Show first 3
                self._log(f"[ADVERSARIAL CRITIC]   {i}. {ce[:100]}{'...' if len(ce) > 100 else ''}")

        # NEW: Log answer implications - critical for feedback loop
        if result.get('answer_implications'):
            self._log(f"\n[ADVERSARIAL CRITIC] Answer implications (what this proves about correct answer):")
            for i, impl in enumerate(result['answer_implications'][:5], 1):  # Show first 5
                self._log(f"[ADVERSARIAL CRITIC]   {i}. {impl[:150]}{'...' if len(impl) > 150 else ''}")

        # Log critical flaws
        if result['critical_flaws']:
            self._log(f"\n[ADVERSARIAL CRITIC] Critical flaws:")
            for i, flaw in enumerate(result['critical_flaws'][:3], 1):
                self._log(f"[ADVERSARIAL CRITIC]   {i}. {flaw[:100]}{'...' if len(flaw) > 100 else ''}")

        self._log(f"{'='*80}\n")

    def get_defense_prompt(self, attack_result: Dict[str, Any], defense_first: bool = False) -> str:
        """
        Generate defense prompt for the generator based on attack results.

        Args:
            attack_result: Parsed attack result dictionary
            defense_first: If True, use defense-first mode for more proactive defense

        Returns:
            Formatted defense prompt string
        """
        if defense_first:
            return defense_first_revision_prompt.format(
                adversarial_feedback=attack_result['full_attack']
            )
        return adversarial_defense_prompt.format(
            adversarial_feedback=attack_result['full_attack']
        )

    def get_defense_first_prompt(self) -> str:
        """
        Get the defense-first generator prompt for initial solution generation.

        Use this prompt to make the generator proactively anticipate attacks
        when generating the initial solution.

        Returns:
            Defense-first generator prompt string
        """
        return defense_first_generator_prompt

    def get_answer_reconsideration_prompt(self, counterexamples: List[str],
                                          previous_answer: str = "unknown") -> str:
        """
        Get the answer reconsideration prompt for when the answer may be fundamentally wrong.

        Use this prompt when stuck detection triggers with counterexamples,
        indicating the ANSWER (not just the proof) may need to change.

        Args:
            counterexamples: List of counterexample strings from recent attacks
            previous_answer: The answer the generator has been defending

        Returns:
            Formatted answer reconsideration prompt
        """
        counterexample_evidence = "\n".join([
            f"- {ce[:200]}..." if len(ce) > 200 else f"- {ce}"
            for ce in counterexamples[-5:]  # Last 5 counterexamples
        ])

        return answer_reconsideration_prompt.format(
            counterexample_evidence=counterexample_evidence,
            previous_answer=previous_answer
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

    def detect_stuck_pattern(self, recent_rounds: int = 4) -> bool:
        """
        Detect if the generator is stuck (not addressing attacks).

        This is the UNIFIED stuck detection mechanism that combines:
        1. Solution unchanged detection (tracked by caller via stuck_count)
        2. Attack pattern analysis (same flaws repeating)

        Args:
            recent_rounds: Number of recent rounds to check (default: 4)

        Returns:
            True if stuck pattern detected
        """
        if len(self.attack_history) < recent_rounds:
            return False

        recent_attacks = self.attack_history[-recent_rounds:]

        # Pattern 1: All recent attacks found issues but verdict didn't improve
        all_broken = all(a['verdict'] == 'BROKEN' for a in recent_attacks)
        all_have_counterexamples = all(len(a['counterexamples']) > 0 for a in recent_attacks)

        # Pattern 2: Same counterexamples appearing repeatedly
        if len(recent_attacks) >= 2:
            first_ces = set(recent_attacks[0].get('counterexamples', [])[:3])
            last_ces = set(recent_attacks[-1].get('counterexamples', [])[:3])
            overlapping_ces = len(first_ces & last_ces) > 0 if first_ces and last_ces else False
        else:
            overlapping_ces = False

        is_stuck = all_broken and (all_have_counterexamples or overlapping_ces)

        if is_stuck:
            if self.verbose:
                self._log(f"\n{'='*80}")
                self._log(f"[ADVERSARIAL CRITIC] STUCK PATTERN DETECTED")
                self._log(f"[ADVERSARIAL CRITIC] Last {recent_rounds} rounds all BROKEN")
                if all_have_counterexamples:
                    self._log(f"[ADVERSARIAL CRITIC] All rounds had counterexamples")
                if overlapping_ces:
                    self._log(f"[ADVERSARIAL CRITIC] Same counterexamples repeating")
                self._log(f"[ADVERSARIAL CRITIC] Generator may be unable to address attacks")
                self._log(f"{'='*80}\n")
            return True

        return False

    # =========================================================================
    # TIER 5: RLAC FULL INTEGRATION - Defense/Concession Parsing
    # =========================================================================

    def parse_defense_response(self, defense_text: str, attack_result: Dict) -> Dict[str, Any]:
        """
        Parse generator's defense response to detect defense vs concession patterns.
        (Tier 5: RLAC Full Integration)

        This enables more intelligent RLAC loop control by understanding HOW the
        generator responds to attacks - whether it successfully defends, concedes,
        or fails to address the attack.

        Args:
            defense_text: Generator's response after receiving attack
            attack_result: The attack that was responded to

        Returns:
            Dict containing:
                - response_type: "defense" / "concession" / "partial_defense" / "unclear"
                - defended_attacks: List of attacks successfully defended against
                - conceded_attacks: List of attacks conceded to
                - unaddressed_attacks: List of attacks not addressed
                - new_approach: Whether generator tried fundamentally new approach
                - confidence: Confidence in parsing result (0.0-1.0)
        """
        result = {
            'response_type': 'unclear',
            'defended_attacks': [],
            'conceded_attacks': [],
            'unaddressed_attacks': [],
            'new_approach': False,
            'confidence': 0.5,
            'raw_defense': defense_text[:500] if defense_text else ''
        }

        if not defense_text:
            return result

        text_lower = defense_text.lower()

        # === Detect defense patterns ===
        defense_patterns = [
            r'this\s+is\s+actually\s+correct\s+because',
            r'the\s+counterexample\s+is\s+invalid',
            r'counterexample\s+does\s+not\s+apply',
            r'this\s+case\s+is\s+already\s+covered',
            r'I\s+defend\s+my\s+solution',
            r'the\s+attack\s+misinterprets',
            r'the\s+criticism\s+is\s+incorrect',
            r'this\s+is\s+not\s+a\s+valid\s+counterexample',
            r'the\s+proof\s+already\s+handles',
            r'this\s+case\s+falls\s+under'
        ]

        defense_count = sum(1 for p in defense_patterns if re.search(p, text_lower))

        # === Detect concession patterns ===
        concession_patterns = [
            r'you\s+are\s+(?:correct|right)',
            r'I\s+acknowledge\s+(?:this|the)\s+(?:flaw|error|gap)',
            r'I\s+concede',
            r'this\s+is\s+a\s+valid\s+counterexample',
            r'I\s+will\s+fix\s+this',
            r'I\s+need\s+to\s+revise',
            r'the\s+(?:flaw|error|gap)\s+is\s+valid',
            r'I\s+(?:made|found)\s+(?:a|an)\s+(?:error|mistake)',
            r'thank\s+you\s+for\s+(?:finding|pointing)',
            r'I\s+will\s+address\s+this'
        ]

        concession_count = sum(1 for p in concession_patterns if re.search(p, text_lower))

        # === Detect new approach patterns ===
        new_approach_patterns = [
            r'(?:completely|fundamentally)\s+(?:new|different)\s+approach',
            r'(?:let|trying)\s+(?:me|a)\s+(?:try|use)\s+(?:a\s+)?different\s+(?:strategy|approach|method)',
            r'I\s+will\s+(?:now\s+)?(?:try|use)\s+(?:a\s+)?(?:completely\s+)?(?:new|different)',
            r'switching\s+to\s+(?:a\s+)?(?:new|different)',
            r'abandoning\s+(?:the\s+)?previous\s+approach',
            r'instead\s+of\s+(?:my\s+)?previous'
        ]

        result['new_approach'] = any(re.search(p, text_lower) for p in new_approach_patterns)

        # === Determine response type ===
        if defense_count > concession_count and defense_count >= 2:
            result['response_type'] = 'defense'
            result['confidence'] = min(0.9, 0.5 + 0.1 * defense_count)
        elif concession_count > defense_count and concession_count >= 2:
            result['response_type'] = 'concession'
            result['confidence'] = min(0.9, 0.5 + 0.1 * concession_count)
        elif defense_count > 0 and concession_count > 0:
            result['response_type'] = 'partial_defense'
            result['confidence'] = 0.6
        else:
            result['response_type'] = 'unclear'
            result['confidence'] = 0.3

        # === Map attacks to defense status ===
        counterexamples = attack_result.get('counterexamples', [])

        for ce in counterexamples:
            ce_lower = ce.lower()[:100]  # First 100 chars of counterexample

            # Check if counterexample is mentioned and defended against
            if ce_lower[:30] in text_lower or any(word in text_lower for word in ce_lower.split()[:5] if len(word) > 3):
                if result['response_type'] in ['defense', 'partial_defense']:
                    result['defended_attacks'].append(ce)
                else:
                    result['conceded_attacks'].append(ce)
            else:
                result['unaddressed_attacks'].append(ce)

        if self.verbose:
            self._log(f"[DEFENSE PARSER] Response type: {result['response_type']} (confidence: {result['confidence']:.2f})")
            self._log(f"[DEFENSE PARSER] Defended: {len(result['defended_attacks'])}, Conceded: {len(result['conceded_attacks'])}, Unaddressed: {len(result['unaddressed_attacks'])}")
            if result['new_approach']:
                self._log(f"[DEFENSE PARSER] Generator trying new approach")

        return result

    # =========================================================================
    # TIER 5: Domain-Specific Attack Patterns
    # =========================================================================

    def get_domain_specific_attacks(self, problem_type: str) -> List[str]:
        """
        Get domain-specific attack strategies based on problem type.
        (Tier 5: RLAC Full Integration)

        Args:
            problem_type: Type of problem (number_theory, geometry, combinatorics, etc.)

        Returns:
            List of domain-specific attack strategies
        """
        domain_attacks = {
            'number_theory': [
                "Test edge cases: n=0, n=1, n=2, n=prime, n=composite",
                "Check divisibility claims with actual computations",
                "Verify modular arithmetic with specific values",
                "Test large primes and prime powers",
                "Check gcd/lcm properties with examples",
                "Verify floor/ceiling function edge cases",
                "Test claims about digit sums with specific numbers"
            ],
            'geometry': [
                "Test degenerate configurations (collinear points, coincident vertices)",
                "Verify angle calculations with specific coordinates",
                "Check if solution holds for both convex and concave cases",
                "Test boundary cases (right angles, parallel lines)",
                "Verify coordinate geometry claims numerically",
                "Check if transformations preserve claimed properties",
                "Test with specific triangle types (isoceles, right, equilateral)"
            ],
            'combinatorics': [
                "Test small values (n=1,2,3,4,5) with explicit enumeration",
                "Verify counting arguments with double counting",
                "Check pigeonhole applications with exact values",
                "Test inclusion-exclusion claims",
                "Verify bijection claims with explicit mapping",
                "Check generating function coefficients",
                "Test recursion base cases and induction steps"
            ],
            'algebra': [
                "Verify polynomial identities with specific values",
                "Test inequality claims at boundary values",
                "Check symmetry arguments with permutations",
                "Verify algebraic manipulations step by step",
                "Test claims about roots with specific polynomials",
                "Check AM-GM, Cauchy-Schwarz applications",
                "Verify functional equation solutions with substitutions"
            ],
            'inequality': [
                "Test at equality conditions",
                "Check boundary values where inequality becomes tight",
                "Verify AM-GM applications with specific values",
                "Test Cauchy-Schwarz setup correctness",
                "Check if constraints are satisfied at claimed optimum",
                "Verify homogenization is valid",
                "Test with extreme values (0, 1, infinity limits)"
            ]
        }

        # Default general attacks
        general_attacks = [
            "Test with small specific values",
            "Verify logical chains step by step",
            "Check if all cases are covered",
            "Look for unstated assumptions",
            "Test boundary conditions"
        ]

        return domain_attacks.get(problem_type.lower(), general_attacks)

    def enhanced_attack(self, problem_statement: str, solution: str, round_num: int,
                       max_rounds: int, problem_type: str = None,
                       api_request_func=None, api_key=None) -> Dict[str, Any]:
        """
        Enhanced attack with domain-specific strategies.
        (Tier 5: RLAC Full Integration)

        Args:
            problem_statement: Original problem
            solution: Solution to attack
            round_num: Current round number
            max_rounds: Maximum rounds
            problem_type: Optional problem type hint for domain-specific attacks
            api_request_func: Function to send API requests
            api_key: API key

        Returns:
            Enhanced attack result with domain-specific findings
        """
        # Get base attack result
        base_result = self.attack_solution(
            problem_statement=problem_statement,
            solution=solution,
            round_num=round_num,
            max_rounds=max_rounds,
            api_request_func=api_request_func,
            api_key=api_key
        )

        # Add domain-specific context
        if problem_type:
            domain_attacks = self.get_domain_specific_attacks(problem_type)
            base_result['domain_attacks_suggested'] = domain_attacks
            base_result['problem_type'] = problem_type

            if self.verbose:
                self._log(f"[ENHANCED ATTACK] Problem type: {problem_type}")
                self._log(f"[ENHANCED ATTACK] Domain-specific attacks available: {len(domain_attacks)}")

        return base_result

    # =========================================================================
    # COUNTER-PROPOSAL IMPLEMENTATIONS
    # =========================================================================

    def create_enhanced_session(self) -> 'EnhancedAdversarialSession':
        """
        Create an enhanced RLAC session with all counter-proposal improvements.

        Returns:
            EnhancedAdversarialSession with validation pipeline, LaTeX parser, and state machine
        """
        return EnhancedAdversarialSession(
            critic=self,
            verbose=self.verbose
        )


class EnhancedAdversarialSession:
    """
    Enhanced RLAC session implementing counter-proposal improvements:

    1. Empty Solution: Validation pipeline with fail-fast + retry strategy
    2. Nested LaTeX: Proper brace-matching parser + semantic normalization
    3. Verdict States: Explicit state machine + confidence scoring + history tracking
    """

    def __init__(self, critic: AdversarialCritic, verbose: bool = True,
                 consecutive_robust_threshold: int = 3):
        """
        Initialize enhanced session.

        Args:
            critic: Base AdversarialCritic instance
            verbose: Enable logging
            consecutive_robust_threshold: Consecutive ROBUST for VERIFIED state
        """
        self.critic = critic
        self.verbose = verbose

        # Counter-proposal 1: Validation pipeline
        self.validation_pipeline = SolutionValidationPipeline(
            fail_fast=True,
            verbose=verbose
        )

        # Counter-proposal 2: LaTeX parser
        self.latex_parser = LaTeXBraceParser(verbose=verbose)

        # Counter-proposal 3: State machine
        self.state_machine = VerdictStateMachine(
            consecutive_robust_for_verified=consecutive_robust_threshold,
            verbose=verbose
        )

        # Session state
        self.round_num = 0
        self.max_retries = 3
        self.answer_history: List[LaTeXParseResult] = []

        if verbose:
            self._log("Enhanced RLAC session initialized with counter-proposal improvements")
            self._log("  - Validation Pipeline: fail-fast + retry strategy")
            self._log("  - LaTeX Parser: proper brace-matching + semantic normalization")
            self._log("  - State Machine: explicit states + confidence scoring + history")

    def _log(self, message: str):
        """Log with timestamp."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] [ENHANCED SESSION] {message}")

    def validate_solution(self, solution: str, context: Dict[str, Any] = None) -> Tuple[bool, PipelineResult]:
        """
        Validate solution using fail-fast pipeline.

        Counter-Proposal 1: Instead of format enforcement in prompt,
        use validation pipeline with fail-fast + retry strategy.

        Args:
            solution: Solution to validate
            context: Optional validation context

        Returns:
            Tuple of (is_valid, detailed_result)
        """
        result = self.validation_pipeline.validate(solution, context)

        if self.verbose:
            status = "PASSED" if result.is_valid else "FAILED"
            self._log(f"Validation {status}: {result.pass_rate:.0%} ({len(result.passed_checks)}/{result.total_checks})")
            if not result.is_valid:
                self._log(f"  Failed checks: {', '.join(result.failed_checks)}")
                if result.should_retry:
                    self._log(f"  Retry hints: {result.retry_hints[:2]}")

        return result.is_valid, result

    def get_retry_prompt(self, validation_result: PipelineResult) -> str:
        """
        Get retry prompt based on validation failures.

        Part of Counter-Proposal 1: Actionable feedback for retry.
        """
        return self.validation_pipeline.get_retry_prompt(validation_result)

    def extract_answer(self, solution: str) -> LaTeXParseResult:
        """
        Extract answer using proper brace-matching parser.

        Counter-Proposal 2: Instead of fallback to full solution,
        use proper brace-matching parser + semantic normalization.

        Args:
            solution: Solution text

        Returns:
            LaTeXParseResult with properly parsed answer
        """
        result = self.latex_parser.extract_boxed(solution)

        if result and result.success:
            if self.verbose:
                self._log(f"Answer extracted (depth {result.parse_depth}): {result.normalized[:50]}...")
            self.answer_history.append(result)
            return result

        # Try alternative extraction
        parsed = self.latex_parser.parse_answer_expression(solution)
        if parsed['value']:
            alt_result = LaTeXParseResult(
                success=True,
                content=str(parsed['value']),
                raw_match=str(parsed['raw'])[:100],
                parse_depth=0,
                normalized=str(parsed['normalized']) if parsed['normalized'] else ""
            )
            self.answer_history.append(alt_result)
            return alt_result

        # Return empty result
        return LaTeXParseResult(
            success=False,
            content="",
            raw_match="",
            parse_depth=0,
            normalized="",
            parse_errors=["Could not extract answer from solution"]
        )

    def check_answer_stability(self, current_answer: LaTeXParseResult) -> Dict[str, Any]:
        """
        Check answer stability using semantic comparison.

        Part of Counter-Proposal 2: Semantic normalization for comparison.
        """
        if len(self.answer_history) < 2:
            return {'stable': True, 'changes': 0, 'oscillating': False}

        changes = 0
        oscillations = 0

        for i in range(1, len(self.answer_history)):
            prev = self.answer_history[i - 1]
            curr = self.answer_history[i]

            is_equiv, confidence = self.latex_parser.answers_equivalent(
                prev.normalized, curr.normalized
            )

            if not is_equiv:
                changes += 1
                # Check for oscillation (A -> B -> A pattern)
                if i >= 2:
                    prev_prev = self.answer_history[i - 2]
                    is_back, _ = self.latex_parser.answers_equivalent(
                        prev_prev.normalized, curr.normalized
                    )
                    if is_back:
                        oscillations += 1

        return {
            'stable': changes == 0,
            'changes': changes,
            'oscillating': oscillations > 0,
            'oscillation_count': oscillations
        }

    def evaluate_attack(self, attack_text: str, counterexamples: List[str],
                       solution: str) -> VerdictConfidence:
        """
        Evaluate attack with state machine and confidence scoring.

        Counter-Proposal 3: Instead of simple intermediate states,
        use explicit state machine + confidence scoring + history tracking.

        Args:
            attack_text: Full attack text from critic
            counterexamples: Extracted counterexamples
            solution: Current solution

        Returns:
            VerdictConfidence with state, confidence, and evidence
        """
        verdict = self.state_machine.evaluate_attack(
            attack_text=attack_text,
            counterexamples=counterexamples,
            solution=solution,
            round_num=self.round_num
        )

        if self.verbose:
            self._log(f"Verdict: {verdict.state.name} (confidence: {verdict.confidence:.2f})")
            self._log(f"  Evidence: {verdict.evidence_count} items ({', '.join(verdict.evidence_types)})")
            self._log(f"  Reasoning: {verdict.reasoning}")

        return verdict

    def get_state_summary(self) -> Dict[str, Any]:
        """Get comprehensive state machine summary."""
        return self.state_machine.get_state_summary()

    def should_terminate(self) -> Tuple[bool, str]:
        """Check if session should terminate."""
        return self.state_machine.should_terminate()

    def run_round(self, problem_statement: str, solution: str,
                  max_rounds: int, api_request_func, api_key: str) -> Dict[str, Any]:
        """
        Run a complete RLAC round with all improvements.

        Combines all three counter-proposals:
        1. Validates solution first (fail-fast)
        2. Extracts answer with proper parsing
        3. Evaluates with state machine

        Args:
            problem_statement: The problem
            solution: Current solution
            max_rounds: Maximum rounds
            api_request_func: API request function
            api_key: API key

        Returns:
            Comprehensive round result
        """
        result = {
            'round_num': self.round_num,
            'validation': None,
            'answer': None,
            'attack': None,
            'verdict': None,
            'state_summary': None,
            'should_continue': True,
            'termination_reason': None,
            'retry_needed': False,
            'retry_prompt': None
        }

        # Step 1: Validate solution (Counter-Proposal 1)
        is_valid, validation_result = self.validate_solution(solution)
        result['validation'] = {
            'is_valid': is_valid,
            'pass_rate': validation_result.pass_rate,
            'failed_checks': validation_result.failed_checks
        }

        if not is_valid:
            if validation_result.should_retry:
                result['retry_needed'] = True
                result['retry_prompt'] = self.get_retry_prompt(validation_result)
                return result
            else:
                result['should_continue'] = False
                result['termination_reason'] = "Solution failed validation (not recoverable)"
                return result

        # Step 2: Extract answer (Counter-Proposal 2)
        answer = self.extract_answer(solution)
        result['answer'] = {
            'success': answer.success,
            'content': answer.content[:100] if answer.content else "",
            'normalized': answer.normalized[:100] if answer.normalized else "",
            'parse_depth': answer.parse_depth
        }

        # Check answer stability
        stability = self.check_answer_stability(answer)
        result['answer']['stability'] = stability

        # Step 3: Run attack
        attack_result = self.critic.attack_solution(
            problem_statement=problem_statement,
            solution=solution,
            round_num=self.round_num,
            max_rounds=max_rounds,
            api_request_func=api_request_func,
            api_key=api_key
        )

        result['attack'] = {
            'verdict': attack_result['verdict'],
            'counterexamples': len(attack_result['counterexamples']),
            'penalty': attack_result['total_penalty']
        }

        # Step 4: Evaluate with state machine (Counter-Proposal 3)
        verdict = self.evaluate_attack(
            attack_text=attack_result['full_attack'],
            counterexamples=attack_result['counterexamples'],
            solution=solution
        )

        result['verdict'] = {
            'state': verdict.state.name,
            'confidence': verdict.confidence,
            'evidence_count': verdict.evidence_count,
            'evidence_types': verdict.evidence_types,
            'reasoning': verdict.reasoning
        }

        # Step 5: Check termination
        should_terminate, reason = self.should_terminate()
        result['should_continue'] = not should_terminate
        result['termination_reason'] = reason if should_terminate else None
        result['state_summary'] = self.get_state_summary()

        # Increment round counter
        self.round_num += 1

        return result

    def get_defense_prompt(self, attack_result: Dict[str, Any]) -> str:
        """Get defense prompt from base critic."""
        return self.critic.get_defense_prompt(attack_result)

    def save_session(self, filepath: str) -> bool:
        """
        Save session state to file.

        Args:
            filepath: Path to save state

        Returns:
            True if successful
        """
        try:
            session_data = {
                'round_num': self.round_num,
                'state_machine': self.state_machine.to_dict(),
                'answer_history': [
                    {
                        'content': a.content[:200],
                        'normalized': a.normalized[:200],
                        'parse_depth': a.parse_depth
                    }
                    for a in self.answer_history
                ],
                'validation_history_count': len(self.validation_pipeline.validation_history),
                'timestamp': datetime.now().isoformat()
            }

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, indent=2)

            if self.verbose:
                self._log(f"Session saved to {filepath}")
            return True

        except Exception as e:
            if self.verbose:
                self._log(f"Error saving session: {e}")
            return False


# ==============================================================================
# SYMBOLIC VERIFIER
# ==============================================================================

class SymbolicVerifier:
    """
    Symbolic verification system for mathematical solutions.

    This verifier performs symbolic computation to validate claims in solutions,
    catching errors that pure reasoning might miss. It integrates with the
    small-case verification system.

    Key capabilities:
    1. Algebraic expression verification
    2. Numerical computation checks
    3. Symbolic equivalence testing
    4. Small-case enumeration
    5. Formula verification
    """

    def __init__(self, verbose: bool = True):
        """
        Initialize the symbolic verifier.

        Args:
            verbose: Enable detailed logging
        """
        self.verbose = verbose
        self.verification_history: List[Dict[str, Any]] = []

        if verbose:
            self._log("SymbolicVerifier initialized")

    def _log(self, message: str):
        """Log with timestamp."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] [SYMBOLIC VERIFIER] {message}")

    def verify_formula(self, formula: str, test_values: List[Dict[str, Any]],
                       expected_fn=None) -> Dict[str, Any]:
        """
        Verify a mathematical formula against test values.

        Args:
            formula: Mathematical formula as string (e.g., "n*(n+1)//2")
            test_values: List of dicts with variable values (e.g., [{'n': 1}, {'n': 2}])
            expected_fn: Optional function to compute expected values

        Returns:
            Dict with verification results:
                - passed: True if all tests passed
                - results: List of individual test results
                - first_failure: Details of first failing case (if any)
        """
        results = []
        first_failure = None

        for test in test_values:
            try:
                # Safe evaluation of formula with given values
                computed = self._safe_eval(formula, test)

                # Compare with expected if provided
                if expected_fn:
                    expected = expected_fn(**test)
                    passed = computed == expected
                    result = {
                        'test': test,
                        'computed': computed,
                        'expected': expected,
                        'passed': passed
                    }
                else:
                    result = {
                        'test': test,
                        'computed': computed,
                        'passed': True  # No expected value to compare
                    }

                results.append(result)

                if not result['passed'] and first_failure is None:
                    first_failure = result

            except Exception as e:
                result = {
                    'test': test,
                    'error': str(e),
                    'passed': False
                }
                results.append(result)
                if first_failure is None:
                    first_failure = result

        all_passed = all(r.get('passed', False) for r in results)

        verification_result = {
            'passed': all_passed,
            'results': results,
            'first_failure': first_failure,
            'total_tests': len(results),
            'passed_tests': sum(1 for r in results if r.get('passed', False))
        }

        self.verification_history.append(verification_result)

        if self.verbose:
            status = "PASS" if all_passed else "FAIL"
            self._log(f"Formula verification: {status} ({verification_result['passed_tests']}/{len(results)})")
            if first_failure:
                self._log(f"  First failure: {first_failure}")

        return verification_result

    def _safe_eval(self, formula: str, variables: Dict[str, Any]) -> Any:
        """
        Safely evaluate a mathematical formula.

        Only allows safe mathematical operations, no arbitrary code execution.

        Args:
            formula: Formula string
            variables: Variable values dict

        Returns:
            Computed result
        """
        # Allowed names for safe evaluation
        safe_names = {
            'abs': abs,
            'min': min,
            'max': max,
            'sum': sum,
            'len': len,
            'range': range,
            'int': int,
            'float': float,
            'pow': pow,
            'round': round,
            # Add variable values
            **variables
        }

        # Restrict to safe operations
        return eval(formula, {"__builtins__": {}}, safe_names)

    def verify_small_cases(self, claim_checker, n_values: List[int] = None,
                          problem_type: str = 'general') -> Dict[str, Any]:
        """
        Verify a claim for small cases.

        Args:
            claim_checker: Function that takes n and returns (passed: bool, details: str)
            n_values: List of n values to test (auto-generated if None)
            problem_type: Type of problem for generating appropriate test cases

        Returns:
            Dict with small-case verification results
        """
        if n_values is None:
            n_values = self._get_test_values_for_type(problem_type)

        results = []
        all_passed = True
        first_failure = None

        for n in n_values:
            try:
                passed, details = claim_checker(n)
                result = {
                    'n': n,
                    'passed': passed,
                    'details': details
                }
            except Exception as e:
                passed = False
                result = {
                    'n': n,
                    'passed': False,
                    'error': str(e)
                }

            results.append(result)

            if not passed:
                all_passed = False
                if first_failure is None:
                    first_failure = result

        verification_result = {
            'verdict': 'ALL_PASS' if all_passed else 'SOME_FAIL',
            'passed': all_passed,
            'results': results,
            'first_failure': first_failure,
            'cases_tested': len(results),
            'cases_passed': sum(1 for r in results if r.get('passed', False))
        }

        self.verification_history.append(verification_result)

        if self.verbose:
            self._log(f"Small-case verification: {verification_result['verdict']}")
            self._log(f"  Cases: {verification_result['cases_passed']}/{verification_result['cases_tested']} passed")
            if first_failure:
                self._log(f"  First failure at n={first_failure['n']}: {first_failure.get('details', first_failure.get('error', 'unknown'))}")

        return verification_result

    def _get_test_values_for_type(self, problem_type: str) -> List[int]:
        """Get appropriate test values based on problem type."""
        test_cases = {
            'number_theory': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 16, 25, 100],
            'combinatorics': [1, 2, 3, 4, 5, 6, 7, 8],
            'geometry': [3, 4, 5, 6, 7, 8],
            'algebra': [0, 1, 2, 3, 4, 5, -1, -2],
            'inequality': [1, 2, 3, 4, 5, 10, 100],
            'general': [1, 2, 3, 4, 5]
        }
        return test_cases.get(problem_type.lower(), test_cases['general'])

    def verify_divisibility(self, value: int, divisor: int) -> Dict[str, Any]:
        """
        Verify divisibility claim.

        Args:
            value: Number to check
            divisor: Divisor to check against

        Returns:
            Dict with verification result
        """
        result = {
            'value': value,
            'divisor': divisor,
            'remainder': value % divisor,
            'is_divisible': value % divisor == 0
        }

        if self.verbose:
            status = "YES" if result['is_divisible'] else "NO"
            self._log(f"Divisibility check: {value} % {divisor} = {result['remainder']} -> {status}")

        return result

    def verify_modular_claim(self, expression: str, modulus: int,
                            expected_residue: int, variables: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verify a modular arithmetic claim.

        Args:
            expression: Expression to evaluate (e.g., "n**2 + n")
            modulus: Modulus value
            expected_residue: Expected residue
            variables: Variable values

        Returns:
            Dict with verification result
        """
        try:
            computed = self._safe_eval(expression, variables)
            actual_residue = computed % modulus

            result = {
                'expression': expression,
                'variables': variables,
                'computed_value': computed,
                'modulus': modulus,
                'actual_residue': actual_residue,
                'expected_residue': expected_residue,
                'passed': actual_residue == expected_residue
            }
        except Exception as e:
            result = {
                'expression': expression,
                'variables': variables,
                'error': str(e),
                'passed': False
            }

        if self.verbose:
            status = "PASS" if result.get('passed', False) else "FAIL"
            self._log(f"Modular claim verification: {status}")

        return result

    def verify_inequality(self, lhs_expr: str, rhs_expr: str, relation: str,
                         test_values: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Verify an inequality claim.

        Args:
            lhs_expr: Left-hand side expression
            rhs_expr: Right-hand side expression
            relation: Comparison operator ('>', '<', '>=', '<=', '==')
            test_values: List of variable value dicts to test

        Returns:
            Dict with verification results
        """
        compare_ops = {
            '>': lambda a, b: a > b,
            '<': lambda a, b: a < b,
            '>=': lambda a, b: a >= b,
            '<=': lambda a, b: a <= b,
            '==': lambda a, b: a == b,
            '!=': lambda a, b: a != b
        }

        compare_fn = compare_ops.get(relation)
        if not compare_fn:
            return {'error': f'Unknown relation: {relation}', 'passed': False}

        results = []
        first_failure = None

        for test in test_values:
            try:
                lhs_value = self._safe_eval(lhs_expr, test)
                rhs_value = self._safe_eval(rhs_expr, test)
                passed = compare_fn(lhs_value, rhs_value)

                result = {
                    'test': test,
                    'lhs': lhs_value,
                    'rhs': rhs_value,
                    'relation': relation,
                    'passed': passed
                }
            except Exception as e:
                result = {
                    'test': test,
                    'error': str(e),
                    'passed': False
                }

            results.append(result)
            if not result['passed'] and first_failure is None:
                first_failure = result

        all_passed = all(r.get('passed', False) for r in results)

        return {
            'passed': all_passed,
            'results': results,
            'first_failure': first_failure,
            'total_tests': len(results),
            'passed_tests': sum(1 for r in results if r.get('passed', False))
        }

    def classify_errors(self, errors: List[str]) -> Dict[str, Any]:
        """
        Classify a list of errors by severity.

        Args:
            errors: List of error description strings

        Returns:
            Dict with classified errors and verdict
        """
        classified = [classify_error_severity(e) for e in errors]
        return calculate_verdict_from_errors(classified)

    def get_small_case_prompt(self) -> str:
        """Get the small-case verification prompt."""
        return small_case_verification_prompt

    def get_small_case_instruction(self) -> str:
        """Get the mandatory small-case check instruction."""
        return small_case_verification_instruction

    def get_metrics(self) -> Dict[str, Any]:
        """Get verification metrics summary."""
        if not self.verification_history:
            return {'total_verifications': 0, 'pass_rate': 0.0}

        passed = sum(1 for v in self.verification_history if v.get('passed', False))
        total = len(self.verification_history)

        return {
            'total_verifications': total,
            'passed': passed,
            'failed': total - passed,
            'pass_rate': passed / total if total > 0 else 0.0
        }

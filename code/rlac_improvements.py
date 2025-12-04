"""
RLAC Improvements Module

Implements three key improvements to the RLAC system:
1. Empty Solution: Validation pipeline with fail-fast + retry strategy
2. Nested LaTeX: Proper brace-matching parser + semantic normalization
3. Verdict States: Explicit state machine + confidence scoring + history tracking

Author: Claude Code
"""

import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import json


# =============================================================================
# IMPROVEMENT 1: Validation Pipeline with Fail-Fast + Retry Strategy
# =============================================================================

class ValidationFailure(Exception):
    """Exception raised when solution validation fails."""
    def __init__(self, reason: str, severity: str = "error", recoverable: bool = True):
        self.reason = reason
        self.severity = severity  # "error", "warning", "critical"
        self.recoverable = recoverable
        super().__init__(reason)


@dataclass
class ValidationResult:
    """Result of a validation check."""
    passed: bool
    check_name: str
    reason: str
    severity: str = "info"  # "info", "warning", "error", "critical"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineResult:
    """Aggregate result from validation pipeline."""
    is_valid: bool
    results: List[ValidationResult]
    failed_checks: List[str]
    passed_checks: List[str]
    should_retry: bool
    retry_hints: List[str]
    total_checks: int
    pass_rate: float


class SolutionValidationPipeline:
    """
    Validation pipeline with fail-fast + retry strategy.

    Implements ordered validation checks that can fail-fast on critical errors
    while providing actionable feedback for retry attempts.
    """

    def __init__(self, fail_fast: bool = True, verbose: bool = True):
        """
        Initialize validation pipeline.

        Args:
            fail_fast: Stop on first critical failure
            verbose: Enable logging
        """
        self.fail_fast = fail_fast
        self.verbose = verbose
        self.validation_history: List[PipelineResult] = []

    def validate(self, solution: str, context: Dict[str, Any] = None) -> PipelineResult:
        """
        Run full validation pipeline on solution.

        Pipeline order (fail-fast on critical):
        1. Null check (critical)
        2. Empty check (critical)
        3. Minimum length check (error)
        4. Structure markers check (error)
        5. Mathematical content check (warning)
        6. Answer presence check (warning)
        7. Proof substance check (warning)

        Args:
            solution: Solution text to validate
            context: Optional context dict with problem info

        Returns:
            PipelineResult with all validation results
        """
        context = context or {}
        results: List[ValidationResult] = []

        # Check 1: Null check (critical - fail fast)
        null_result = self._check_null(solution)
        results.append(null_result)
        if not null_result.passed and self.fail_fast:
            return self._build_result(results)

        # Check 2: Empty check (critical - fail fast)
        empty_result = self._check_empty(solution)
        results.append(empty_result)
        if not empty_result.passed and self.fail_fast:
            return self._build_result(results)

        # Check 3: Minimum length (error)
        min_length = context.get('min_length', 500)
        length_result = self._check_min_length(solution, min_length)
        results.append(length_result)
        if not length_result.passed and length_result.severity == "critical" and self.fail_fast:
            return self._build_result(results)

        # Check 4: Structure markers (error)
        structure_result = self._check_structure_markers(solution)
        results.append(structure_result)

        # Check 5: Mathematical content (warning)
        math_result = self._check_mathematical_content(solution)
        results.append(math_result)

        # Check 6: Answer presence (warning)
        answer_result = self._check_answer_presence(solution)
        results.append(answer_result)

        # Check 7: Proof substance (warning)
        proof_result = self._check_proof_substance(solution)
        results.append(proof_result)

        return self._build_result(results)

    def _check_null(self, solution: str) -> ValidationResult:
        """Check if solution is None."""
        if solution is None:
            return ValidationResult(
                passed=False,
                check_name="null_check",
                reason="Solution is None",
                severity="critical",
                metadata={"recoverable": True, "retry_hint": "Regenerate solution from scratch"}
            )
        return ValidationResult(
            passed=True,
            check_name="null_check",
            reason="Solution is not None",
            severity="info"
        )

    def _check_empty(self, solution: str) -> ValidationResult:
        """Check if solution is empty or whitespace only."""
        if not solution or not solution.strip():
            return ValidationResult(
                passed=False,
                check_name="empty_check",
                reason="Solution is empty or whitespace only",
                severity="critical",
                metadata={"recoverable": True, "retry_hint": "Ensure generator produces substantive content"}
            )
        return ValidationResult(
            passed=True,
            check_name="empty_check",
            reason=f"Solution has content ({len(solution)} chars)",
            severity="info",
            metadata={"length": len(solution)}
        )

    def _check_min_length(self, solution: str, min_length: int) -> ValidationResult:
        """Check minimum length requirement."""
        actual_length = len(solution) if solution else 0

        if actual_length < min_length:
            # Determine severity based on how short
            if actual_length < min_length * 0.2:
                severity = "critical"
            elif actual_length < min_length * 0.5:
                severity = "error"
            else:
                severity = "warning"

            return ValidationResult(
                passed=False,
                check_name="min_length_check",
                reason=f"Solution too short ({actual_length} < {min_length} chars)",
                severity=severity,
                metadata={
                    "actual_length": actual_length,
                    "min_length": min_length,
                    "ratio": actual_length / min_length if min_length > 0 else 0,
                    "retry_hint": "Request more detailed solution with complete proof"
                }
            )

        return ValidationResult(
            passed=True,
            check_name="min_length_check",
            reason=f"Solution meets length requirement ({actual_length} >= {min_length})",
            severity="info",
            metadata={"actual_length": actual_length, "min_length": min_length}
        )

    def _check_structure_markers(self, solution: str) -> ValidationResult:
        """Check for required structure markers."""
        required_markers = ['summary', 'solution', 'proof', 'answer', 'conclusion']
        found_markers = []

        solution_lower = solution.lower() if solution else ""

        for marker in required_markers:
            if marker in solution_lower:
                found_markers.append(marker)

        if len(found_markers) == 0:
            return ValidationResult(
                passed=False,
                check_name="structure_check",
                reason="Solution missing all structure markers",
                severity="error",
                metadata={
                    "expected_markers": required_markers,
                    "found_markers": found_markers,
                    "retry_hint": "Include clear sections: Summary, Solution, Proof, Answer"
                }
            )

        return ValidationResult(
            passed=True,
            check_name="structure_check",
            reason=f"Found {len(found_markers)} structure markers",
            severity="info",
            metadata={"found_markers": found_markers}
        )

    def _check_mathematical_content(self, solution: str) -> ValidationResult:
        """Check for mathematical content indicators."""
        math_indicators = [
            ('$', 'inline_math'),
            ('\\', 'latex_commands'),
            ('proof', 'proof_keyword'),
            ('therefore', 'logical_connector'),
            ('hence', 'logical_connector'),
            ('thus', 'logical_connector'),
            ('let', 'definition'),
            ('assume', 'assumption'),
            ('suppose', 'assumption'),
            ('if and only if', 'biconditional'),
            ('implies', 'implication'),
            ('\\boxed', 'boxed_answer'),
            ('qed', 'proof_end'),
        ]

        solution_lower = solution.lower() if solution else ""
        found_indicators = []

        for indicator, category in math_indicators:
            if indicator.lower() in solution_lower:
                found_indicators.append((indicator, category))

        if len(found_indicators) < 3:
            return ValidationResult(
                passed=False,
                check_name="math_content_check",
                reason=f"Insufficient mathematical content ({len(found_indicators)} indicators)",
                severity="warning",
                metadata={
                    "found_indicators": found_indicators,
                    "retry_hint": "Include mathematical notation, proofs, and logical reasoning"
                }
            )

        return ValidationResult(
            passed=True,
            check_name="math_content_check",
            reason=f"Sufficient mathematical content ({len(found_indicators)} indicators)",
            severity="info",
            metadata={"found_indicators": found_indicators}
        )

    def _check_answer_presence(self, solution: str) -> ValidationResult:
        """Check if solution contains an identifiable answer."""
        answer_patterns = [
            r'\\boxed\{',
            r'(?:the\s+)?answer\s+is',
            r'(?:we\s+)?conclude\s+that',
            r'(?:the\s+)?result\s+is',
            r'(?:we\s+)?find\s+that',
            r'(?:this\s+)?gives\s+us',
        ]

        solution_text = solution if solution else ""

        for pattern in answer_patterns:
            if re.search(pattern, solution_text, re.IGNORECASE):
                return ValidationResult(
                    passed=True,
                    check_name="answer_presence_check",
                    reason="Solution contains identifiable answer",
                    severity="info",
                    metadata={"matched_pattern": pattern}
                )

        return ValidationResult(
            passed=False,
            check_name="answer_presence_check",
            reason="No clear answer identified in solution",
            severity="warning",
            metadata={"retry_hint": "Include explicit answer using \\boxed{} or 'The answer is...'"}
        )

    def _check_proof_substance(self, solution: str) -> ValidationResult:
        """Check if solution has proof substance (not just answer)."""
        if not solution:
            return ValidationResult(
                passed=False,
                check_name="proof_substance_check",
                reason="Empty solution has no proof",
                severity="error"
            )

        # Check for answer-only solutions
        has_boxed = '\\boxed' in solution.lower()
        has_proof_keywords = any(kw in solution.lower() for kw in ['proof', 'because', 'since', 'therefore'])

        # Short solution with boxed but no proof = answer-only
        if len(solution) < 1000 and has_boxed and not has_proof_keywords:
            return ValidationResult(
                passed=False,
                check_name="proof_substance_check",
                reason="Solution appears to be answer-only without proof",
                severity="warning",
                metadata={"retry_hint": "Provide complete proof, not just final answer"}
            )

        return ValidationResult(
            passed=True,
            check_name="proof_substance_check",
            reason="Solution contains proof substance",
            severity="info"
        )

    def _build_result(self, results: List[ValidationResult]) -> PipelineResult:
        """Build aggregate pipeline result."""
        failed_checks = [r.check_name for r in results if not r.passed]
        passed_checks = [r.check_name for r in results if r.passed]

        # Determine if retry is viable
        critical_failures = [r for r in results if not r.passed and r.severity == "critical"]
        error_failures = [r for r in results if not r.passed and r.severity == "error"]

        # Can retry if not too many critical failures
        should_retry = len(critical_failures) <= 1 and len(error_failures) <= 2

        # Gather retry hints
        retry_hints = []
        for r in results:
            if not r.passed and 'retry_hint' in r.metadata:
                retry_hints.append(r.metadata['retry_hint'])

        is_valid = len(failed_checks) == 0 or all(
            r.severity in ("info", "warning") for r in results if not r.passed
        )

        result = PipelineResult(
            is_valid=is_valid,
            results=results,
            failed_checks=failed_checks,
            passed_checks=passed_checks,
            should_retry=should_retry,
            retry_hints=retry_hints,
            total_checks=len(results),
            pass_rate=len(passed_checks) / len(results) if results else 0
        )

        self.validation_history.append(result)
        return result

    def get_retry_prompt(self, result: PipelineResult) -> str:
        """Generate a retry prompt based on validation failures."""
        if result.is_valid:
            return ""

        prompt_parts = ["Your previous solution had the following issues:"]

        for r in result.results:
            if not r.passed:
                prompt_parts.append(f"- {r.reason}")

        if result.retry_hints:
            prompt_parts.append("\nTo fix these issues:")
            for hint in result.retry_hints:
                prompt_parts.append(f"- {hint}")

        prompt_parts.append("\nPlease regenerate a complete solution addressing these issues.")

        return "\n".join(prompt_parts)


# =============================================================================
# IMPROVEMENT 2: Proper Brace-Matching LaTeX Parser + Semantic Normalization
# =============================================================================

@dataclass
class LaTeXParseResult:
    """Result of LaTeX parsing."""
    success: bool
    content: str
    raw_match: str
    parse_depth: int
    normalized: str
    parse_errors: List[str] = field(default_factory=list)


class LaTeXBraceParser:
    """
    Proper brace-matching parser for LaTeX expressions.

    Handles nested braces correctly, unlike simple regex which fails on:
    - \\boxed{\\frac{1}{2}}
    - \\boxed{x^{2} + y^{2}}
    - \\boxed{\\{1, 2, 3\\}}
    """

    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    def extract_boxed(self, text: str) -> Optional[LaTeXParseResult]:
        """
        Extract content from \\boxed{...} with proper brace matching.

        Args:
            text: Text containing \\boxed{...}

        Returns:
            LaTeXParseResult or None if not found
        """
        # Find \boxed{ pattern
        pattern = r'\\boxed\s*\{'
        match = re.search(pattern, text)

        if not match:
            return None

        start_pos = match.end() - 1  # Position of opening brace
        content, end_pos, depth = self._match_braces(text, start_pos)

        if content is None:
            return LaTeXParseResult(
                success=False,
                content="",
                raw_match=text[match.start():min(len(text), match.start() + 50)],
                parse_depth=depth,
                normalized="",
                parse_errors=["Unbalanced braces in \\boxed expression"]
            )

        raw_match = text[match.start():end_pos + 1]
        normalized = self._normalize_latex(content)

        return LaTeXParseResult(
            success=True,
            content=content,
            raw_match=raw_match,
            parse_depth=depth,
            normalized=normalized
        )

    def extract_all_boxed(self, text: str) -> List[LaTeXParseResult]:
        """Extract all \\boxed{...} expressions from text."""
        results = []
        remaining_text = text
        offset = 0

        while True:
            result = self.extract_boxed(remaining_text)
            if result is None or not result.success:
                break

            results.append(result)

            # Find position after this match and continue
            match = re.search(r'\\boxed\s*\{', remaining_text)
            if match:
                # Skip past this match
                end_pos = remaining_text.find(result.raw_match) + len(result.raw_match)
                remaining_text = remaining_text[end_pos:]
                offset += end_pos
            else:
                break

        return results

    def _match_braces(self, text: str, start_pos: int) -> Tuple[Optional[str], int, int]:
        """
        Match braces starting from position, handling nesting.

        Args:
            text: Full text
            start_pos: Position of opening brace

        Returns:
            Tuple of (content, end_position, max_depth) or (None, -1, depth) on failure
        """
        if start_pos >= len(text) or text[start_pos] != '{':
            return None, -1, 0

        depth = 1
        max_depth = 1
        pos = start_pos + 1
        escape_next = False

        while pos < len(text) and depth > 0:
            char = text[pos]

            # Handle escape sequences
            if escape_next:
                escape_next = False
                pos += 1
                continue

            if char == '\\':
                # Check for \{ or \}
                if pos + 1 < len(text) and text[pos + 1] in '{}':
                    escape_next = True
                    pos += 1
                    continue
                pos += 1
                continue

            if char == '{':
                depth += 1
                max_depth = max(max_depth, depth)
            elif char == '}':
                depth -= 1

            pos += 1

        if depth != 0:
            return None, -1, max_depth

        # Extract content (excluding outer braces)
        content = text[start_pos + 1:pos - 1]
        return content, pos - 1, max_depth

    def _normalize_latex(self, latex: str) -> str:
        """
        Normalize LaTeX for semantic comparison.

        Normalizations:
        - Remove extra whitespace
        - Standardize common equivalents
        - Remove cosmetic commands
        """
        if not latex:
            return ""

        normalized = latex

        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized).strip()

        # Normalize common equivalents
        equivalents = [
            (r'\\cdot', '*'),
            (r'\\times', '*'),
            (r'\\div', '/'),
            (r'\\frac\s*{([^}]*)}\s*{([^}]*)}', r'(\1)/(\2)'),
            (r'\\left\s*\(', '('),
            (r'\\right\s*\)', ')'),
            (r'\\left\s*\[', '['),
            (r'\\right\s*\]', ']'),
            (r'\\{', '{'),
            (r'\\}', '}'),
            (r'\\,', ''),
            (r'\\;', ''),
            (r'\\!', ''),
            (r'\\quad', ' '),
            (r'\\qquad', ' '),
        ]

        for pattern, replacement in equivalents:
            normalized = re.sub(pattern, replacement, normalized)

        # Final whitespace cleanup
        normalized = re.sub(r'\s+', ' ', normalized).strip()

        return normalized

    def parse_answer_expression(self, text: str) -> Dict[str, Any]:
        """
        Parse various answer formats and normalize them.

        Handles:
        - \\boxed{...}
        - "The answer is ..."
        - Set notation: {1, 2, 3}
        - Ranges: [0, n]
        - Expressions: n^2 + 1
        """
        result = {
            'raw': text,
            'type': 'unknown',
            'value': None,
            'normalized': None,
            'confidence': 0.0
        }

        # Try boxed first
        boxed = self.extract_boxed(text)
        if boxed and boxed.success:
            result['type'] = 'boxed'
            result['value'] = boxed.content
            result['normalized'] = boxed.normalized
            result['confidence'] = 0.95
            return result

        # Try "answer is" pattern
        answer_match = re.search(
            r'(?:the\s+)?answer\s+is[:\s]+(.+?)(?:\.|$)',
            text, re.IGNORECASE
        )
        if answer_match:
            value = answer_match.group(1).strip()
            result['type'] = 'text_answer'
            result['value'] = value
            result['normalized'] = self._normalize_latex(value)
            result['confidence'] = 0.8
            return result

        # Try set notation
        set_match = re.search(r'\{([^{}]+)\}', text)
        if set_match:
            value = set_match.group(1)
            result['type'] = 'set'
            result['value'] = value
            result['normalized'] = ','.join(sorted(v.strip() for v in value.split(',')))
            result['confidence'] = 0.7
            return result

        return result

    def answers_equivalent(self, answer1: str, answer2: str) -> Tuple[bool, float]:
        """
        Check if two answers are semantically equivalent.

        Returns:
            Tuple of (is_equivalent, confidence)
        """
        parsed1 = self.parse_answer_expression(answer1)
        parsed2 = self.parse_answer_expression(answer2)

        # Direct match
        if parsed1['normalized'] and parsed2['normalized']:
            if parsed1['normalized'] == parsed2['normalized']:
                return True, 0.95

        # Raw value match
        if parsed1['value'] and parsed2['value']:
            v1 = str(parsed1['value']).strip().lower()
            v2 = str(parsed2['value']).strip().lower()
            if v1 == v2:
                return True, 0.9

        # Numeric comparison for simple numbers
        try:
            n1 = float(parsed1['value']) if parsed1['value'] else None
            n2 = float(parsed2['value']) if parsed2['value'] else None
            if n1 is not None and n2 is not None and abs(n1 - n2) < 1e-9:
                return True, 0.99
        except (ValueError, TypeError):
            pass

        return False, 0.0


# =============================================================================
# IMPROVEMENT 3: Explicit State Machine + Confidence Scoring + History Tracking
# =============================================================================

class VerdictState(Enum):
    """Explicit verdict states with clear semantics."""
    UNKNOWN = auto()      # Initial state, not yet evaluated
    BROKEN = auto()       # Definite failure with counterexamples
    SUSPICIOUS = auto()   # Potential issues but not confirmed
    WEAK = auto()         # Solution has gaps but may be salvageable
    ROBUST = auto()       # Solution survived attacks
    VERIFIED = auto()     # Multiple consecutive robust verdicts


@dataclass
class VerdictConfidence:
    """Confidence scoring for verdict."""
    state: VerdictState
    confidence: float  # 0.0 to 1.0
    evidence_count: int
    evidence_types: List[str]
    reasoning: str


@dataclass
class VerdictHistoryEntry:
    """Single entry in verdict history."""
    round_num: int
    timestamp: datetime
    state: VerdictState
    confidence: VerdictConfidence
    counterexamples: List[str]
    attack_text: str
    solution_hash: str  # Track which solution version
    transition_from: Optional[VerdictState]


class VerdictStateMachine:
    """
    Explicit state machine for verdict tracking.

    State Transitions:
    - UNKNOWN -> BROKEN (counterexamples found)
    - UNKNOWN -> SUSPICIOUS (issues detected)
    - UNKNOWN -> WEAK (gaps found)
    - UNKNOWN -> ROBUST (no issues found)
    - BROKEN -> SUSPICIOUS (counterexamples addressed but issues remain)
    - BROKEN -> WEAK (partial fix)
    - BROKEN -> ROBUST (complete fix)
    - SUSPICIOUS -> BROKEN (confirmed issues)
    - SUSPICIOUS -> ROBUST (issues resolved)
    - WEAK -> BROKEN (new counterexamples)
    - WEAK -> ROBUST (gaps filled)
    - ROBUST -> VERIFIED (consecutive robust)
    - ROBUST -> BROKEN (new attack succeeds)
    - VERIFIED -> BROKEN (late-stage failure)

    Disallowed Transitions:
    - VERIFIED -> UNKNOWN (can't go back to initial)
    - BROKEN -> VERIFIED (must go through ROBUST first)
    """

    VALID_TRANSITIONS = {
        VerdictState.UNKNOWN: {VerdictState.BROKEN, VerdictState.SUSPICIOUS, VerdictState.WEAK, VerdictState.ROBUST},
        VerdictState.BROKEN: {VerdictState.SUSPICIOUS, VerdictState.WEAK, VerdictState.ROBUST, VerdictState.BROKEN},
        VerdictState.SUSPICIOUS: {VerdictState.BROKEN, VerdictState.WEAK, VerdictState.ROBUST, VerdictState.SUSPICIOUS},
        VerdictState.WEAK: {VerdictState.BROKEN, VerdictState.SUSPICIOUS, VerdictState.ROBUST, VerdictState.WEAK},
        VerdictState.ROBUST: {VerdictState.BROKEN, VerdictState.SUSPICIOUS, VerdictState.VERIFIED, VerdictState.ROBUST},
        VerdictState.VERIFIED: {VerdictState.BROKEN, VerdictState.SUSPICIOUS, VerdictState.VERIFIED},
    }

    def __init__(self, consecutive_robust_for_verified: int = 3, verbose: bool = True):
        """
        Initialize state machine.

        Args:
            consecutive_robust_for_verified: Number of consecutive ROBUST verdicts needed for VERIFIED
            verbose: Enable logging
        """
        self.current_state = VerdictState.UNKNOWN
        self.consecutive_robust_for_verified = consecutive_robust_for_verified
        self.verbose = verbose

        # History tracking
        self.history: List[VerdictHistoryEntry] = []

        # Confidence tracking
        self.cumulative_confidence = 0.0
        self.consecutive_robust_count = 0
        self.consecutive_broken_count = 0

        # Pattern tracking
        self.state_transition_count: Dict[str, int] = {}
        self.oscillation_count = 0

    def _log(self, message: str):
        """Log message with timestamp."""
        if self.verbose:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            print(f"[{timestamp}] [STATE MACHINE] {message}")

    def evaluate_attack(self, attack_text: str, counterexamples: List[str],
                       solution: str, round_num: int) -> VerdictConfidence:
        """
        Evaluate attack result and determine verdict with confidence.

        Args:
            attack_text: Full attack text from critic
            counterexamples: List of counterexamples found
            solution: Current solution (for hashing)
            round_num: Current round number

        Returns:
            VerdictConfidence with state and confidence score
        """
        text_upper = attack_text.upper() if attack_text else ""
        evidence_types = []
        evidence_count = 0

        # Evidence collection
        has_counterexamples = len(counterexamples) > 0
        has_explicit_broken = 'BROKEN' in text_upper
        has_explicit_robust = 'ROBUST' in text_upper
        has_explicit_suspicious = 'SUSPICIOUS' in text_upper
        has_contradiction = 'CONTRADICTION' in text_upper or 'INVALID' in text_upper
        has_no_flaws = 'NO FLAWS' in text_upper or 'NO ISSUES' in text_upper

        # Count evidence
        if has_counterexamples:
            evidence_types.append('counterexamples')
            evidence_count += len(counterexamples)
        if has_explicit_broken:
            evidence_types.append('explicit_broken_verdict')
            evidence_count += 1
        if has_explicit_robust:
            evidence_types.append('explicit_robust_verdict')
            evidence_count += 1
        if has_contradiction:
            evidence_types.append('contradiction_detected')
            evidence_count += 1
        if has_no_flaws:
            evidence_types.append('no_flaws_found')
            evidence_count += 1

        # Determine state and confidence
        if has_counterexamples:
            # BROKEN with high confidence if counterexamples exist
            state = VerdictState.BROKEN
            confidence = min(0.95, 0.7 + 0.1 * len(counterexamples))
            reasoning = f"Found {len(counterexamples)} counterexample(s)"
        elif has_explicit_broken and has_contradiction:
            # BROKEN but lower confidence without concrete counterexamples
            state = VerdictState.BROKEN
            confidence = 0.75
            reasoning = "Explicit BROKEN verdict with contradiction detected"
        elif has_explicit_broken:
            # Could be BROKEN or SUSPICIOUS depending on evidence
            state = VerdictState.SUSPICIOUS
            confidence = 0.6
            reasoning = "Explicit BROKEN verdict but no concrete counterexamples"
        elif has_explicit_suspicious:
            state = VerdictState.SUSPICIOUS
            confidence = 0.7
            reasoning = "Explicit SUSPICIOUS verdict"
        elif has_explicit_robust or has_no_flaws:
            state = VerdictState.ROBUST
            confidence = 0.8 if has_explicit_robust else 0.7
            reasoning = "No flaws found in attack"
        else:
            # Default to WEAK if we can't determine
            state = VerdictState.WEAK
            confidence = 0.5
            reasoning = "Unable to determine verdict from attack text"

        verdict_confidence = VerdictConfidence(
            state=state,
            confidence=confidence,
            evidence_count=evidence_count,
            evidence_types=evidence_types,
            reasoning=reasoning
        )

        # Transition to new state
        self._transition(verdict_confidence, counterexamples, attack_text, solution, round_num)

        return verdict_confidence

    def _transition(self, verdict: VerdictConfidence, counterexamples: List[str],
                   attack_text: str, solution: str, round_num: int):
        """
        Perform state transition with validation.
        """
        old_state = self.current_state
        new_state = verdict.state

        # Check for oscillation (BROKEN -> ROBUST -> BROKEN pattern)
        if len(self.history) >= 2:
            prev_states = [h.state for h in self.history[-2:]]
            if (old_state == VerdictState.ROBUST and new_state == VerdictState.BROKEN and
                prev_states[0] == VerdictState.BROKEN):
                self.oscillation_count += 1
                self._log(f"OSCILLATION DETECTED (count: {self.oscillation_count})")

        # Check if transition is valid
        if new_state not in self.VALID_TRANSITIONS.get(old_state, set()):
            self._log(f"WARNING: Invalid transition {old_state.name} -> {new_state.name}")
            # Allow anyway but log warning

        # Handle special transitions
        if new_state == VerdictState.ROBUST:
            self.consecutive_robust_count += 1
            self.consecutive_broken_count = 0

            # Check for VERIFIED promotion
            if self.consecutive_robust_count >= self.consecutive_robust_for_verified:
                new_state = VerdictState.VERIFIED
                verdict.state = new_state
                self._log(f"PROMOTED to VERIFIED after {self.consecutive_robust_count} consecutive ROBUST")
        elif new_state == VerdictState.BROKEN:
            self.consecutive_broken_count += 1
            self.consecutive_robust_count = 0
        else:
            self.consecutive_robust_count = 0
            self.consecutive_broken_count = 0

        # Record transition
        transition_key = f"{old_state.name}->{new_state.name}"
        self.state_transition_count[transition_key] = self.state_transition_count.get(transition_key, 0) + 1

        # Create history entry
        entry = VerdictHistoryEntry(
            round_num=round_num,
            timestamp=datetime.now(),
            state=new_state,
            confidence=verdict,
            counterexamples=counterexamples,
            attack_text=attack_text[:500] if attack_text else "",  # Truncate for storage
            solution_hash=str(hash(solution))[:12] if solution else "",
            transition_from=old_state
        )
        self.history.append(entry)

        # Update state
        self.current_state = new_state

        self._log(f"Transition: {old_state.name} -> {new_state.name} (confidence: {verdict.confidence:.2f})")

    def get_state_summary(self) -> Dict[str, Any]:
        """Get summary of current state and history."""
        state_counts = {}
        for entry in self.history:
            state_name = entry.state.name
            state_counts[state_name] = state_counts.get(state_name, 0) + 1

        return {
            'current_state': self.current_state.name,
            'total_rounds': len(self.history),
            'consecutive_robust': self.consecutive_robust_count,
            'consecutive_broken': self.consecutive_broken_count,
            'oscillation_count': self.oscillation_count,
            'state_counts': state_counts,
            'transition_counts': self.state_transition_count,
            'is_verified': self.current_state == VerdictState.VERIFIED,
            'is_stuck': self.consecutive_broken_count >= 4 or self.oscillation_count >= 3
        }

    def get_confidence_trend(self) -> List[float]:
        """Get confidence trend over rounds."""
        return [entry.confidence.confidence for entry in self.history]

    def should_terminate(self) -> Tuple[bool, str]:
        """
        Determine if RLAC loop should terminate.

        Returns:
            Tuple of (should_terminate, reason)
        """
        summary = self.get_state_summary()

        if summary['is_verified']:
            return True, f"Solution VERIFIED after {summary['consecutive_robust']} consecutive ROBUST verdicts"

        if summary['oscillation_count'] >= 3:
            return True, f"Excessive oscillation detected ({summary['oscillation_count']} times)"

        if summary['consecutive_broken'] >= 5:
            return True, f"Stuck in BROKEN state ({summary['consecutive_broken']} consecutive)"

        return False, ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize state machine to dict for persistence."""
        return {
            'current_state': self.current_state.name,
            'consecutive_robust_count': self.consecutive_robust_count,
            'consecutive_broken_count': self.consecutive_broken_count,
            'oscillation_count': self.oscillation_count,
            'state_transition_count': self.state_transition_count,
            'history': [
                {
                    'round_num': h.round_num,
                    'timestamp': h.timestamp.isoformat(),
                    'state': h.state.name,
                    'confidence': h.confidence.confidence,
                    'evidence_types': h.confidence.evidence_types,
                    'counterexample_count': len(h.counterexamples),
                    'solution_hash': h.solution_hash,
                    'transition_from': h.transition_from.name if h.transition_from else None
                }
                for h in self.history
            ]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VerdictStateMachine':
        """Restore state machine from dict."""
        machine = cls(verbose=False)
        machine.current_state = VerdictState[data['current_state']]
        machine.consecutive_robust_count = data.get('consecutive_robust_count', 0)
        machine.consecutive_broken_count = data.get('consecutive_broken_count', 0)
        machine.oscillation_count = data.get('oscillation_count', 0)
        machine.state_transition_count = data.get('state_transition_count', {})
        # Note: Full history restoration would need more data
        return machine


# =============================================================================
# INTEGRATION HELPERS
# =============================================================================

def create_enhanced_critic_wrapper(critic_instance, verbose: bool = True):
    """
    Create an enhanced wrapper around AdversarialCritic with improvements.

    Args:
        critic_instance: Original AdversarialCritic instance
        verbose: Enable logging

    Returns:
        Enhanced critic with validation pipeline, LaTeX parser, and state machine
    """
    # Create improvement components
    validation_pipeline = SolutionValidationPipeline(fail_fast=True, verbose=verbose)
    latex_parser = LaTeXBraceParser(verbose=verbose)
    state_machine = VerdictStateMachine(verbose=verbose)

    return {
        'critic': critic_instance,
        'validation_pipeline': validation_pipeline,
        'latex_parser': latex_parser,
        'state_machine': state_machine
    }


def run_enhanced_rlac_round(
    enhanced_critic: Dict,
    problem_statement: str,
    solution: str,
    round_num: int,
    max_rounds: int,
    api_request_func,
    api_key: str
) -> Dict[str, Any]:
    """
    Run a single RLAC round with all improvements.

    Returns enhanced result with:
    - Validation status
    - Parsed LaTeX answers
    - State machine verdict with confidence
    """
    critic = enhanced_critic['critic']
    validation = enhanced_critic['validation_pipeline']
    latex = enhanced_critic['latex_parser']
    state_machine = enhanced_critic['state_machine']

    result = {
        'round_num': round_num,
        'validation_result': None,
        'attack_result': None,
        'verdict_confidence': None,
        'parsed_answer': None,
        'state_summary': None,
        'should_terminate': False,
        'termination_reason': None
    }

    # Step 1: Validate solution before attacking
    validation_result = validation.validate(solution)
    result['validation_result'] = {
        'is_valid': validation_result.is_valid,
        'pass_rate': validation_result.pass_rate,
        'failed_checks': validation_result.failed_checks,
        'should_retry': validation_result.should_retry
    }

    if not validation_result.is_valid and not validation_result.should_retry:
        result['should_terminate'] = True
        result['termination_reason'] = "Solution failed validation and is not recoverable"
        return result

    # Step 2: Parse answer from solution
    parsed_answer = latex.parse_answer_expression(solution)
    result['parsed_answer'] = parsed_answer

    # Step 3: Run attack
    attack_result = critic.attack_solution(
        problem_statement=problem_statement,
        solution=solution,
        round_num=round_num,
        max_rounds=max_rounds,
        api_request_func=api_request_func,
        api_key=api_key
    )
    result['attack_result'] = {
        'verdict': attack_result['verdict'],
        'counterexamples': attack_result['counterexamples'],
        'total_penalty': attack_result['total_penalty']
    }

    # Step 4: Evaluate with state machine
    verdict_confidence = state_machine.evaluate_attack(
        attack_text=attack_result['full_attack'],
        counterexamples=attack_result['counterexamples'],
        solution=solution,
        round_num=round_num
    )
    result['verdict_confidence'] = {
        'state': verdict_confidence.state.name,
        'confidence': verdict_confidence.confidence,
        'evidence_count': verdict_confidence.evidence_count,
        'evidence_types': verdict_confidence.evidence_types,
        'reasoning': verdict_confidence.reasoning
    }

    # Step 5: Check termination
    should_terminate, reason = state_machine.should_terminate()
    result['should_terminate'] = should_terminate
    result['termination_reason'] = reason
    result['state_summary'] = state_machine.get_state_summary()

    return result

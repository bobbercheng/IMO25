# Detailed Proposal: Multi-Level Convergence Detection System

**Author:** AI Systems Analysis
**Date:** 2025-12-07
**Context:** Problem 1 RLAC test showed 82% wasted API calls due to lack of convergence detection

---

## Executive Summary

The current system lacks mechanisms to detect when it's stuck in unproductive loops. Analysis of problem 1 logs reveals:
- **RLAC:** 8 consecutive SUSPICIOUS/BROKEN verdicts on same construction error
- **TIER 2:** 5 consecutive refinement attempts with identical mathematical errors
- **Total waste:** ~14 out of 17 rounds (82%) were unproductive

This proposal introduces a **4-level convergence detection framework** that operates at different time scales and abstraction levels to catch stuck patterns early and trigger appropriate interventions.

---

## 1. DETECTION LEVEL 1: Error Signature Matching (TIER 2)

### Problem Identified

From logs (TIER 2 rounds 1-5):
```
Round 1: "Critical Error – the three listed lines do not cover all six points
          of S_3 (e.g. (1,3) and (2,1) are uncovered)"

Round 3: "Critical Error – a direct check shows that the point (1,3)∈S_3 is
          not on any of the three listed lines"

Round 5: "Critical Error – a direct check shows that the point (1,3)∈S_3 is
          not on any of the three listed lines"
```

**Identical error** repeated 5 times with **no progress**.

### Proposed Solution: Error Fingerprinting

**Algorithm:**
```python
class ErrorFingerprint:
    """
    Creates stable signature of verification errors for convergence detection.
    """
    def __init__(self, error_data):
        """
        Args:
            error_data: Verification result with critical_errors, major_issues, etc.
        """
        self.type = error_data.get('type')  # "Critical Error", "Justification Gap"
        self.location_hash = self._hash_location(error_data.get('location'))
        self.issue_hash = self._hash_issue(error_data.get('issue'))

    def _hash_location(self, location):
        """
        Extract structural location (e.g., "Section 2c", "Construction k=3").
        Ignore exact wording, focus on proof section.
        """
        if not location:
            return None

        # Extract section markers
        import re
        section_match = re.search(r'§(\d+[a-z]?)|Section\s+(\d+[a-z]?)|k\s*=\s*(\d+)', location)
        if section_match:
            return section_match.group(0)

        # Hash first 50 chars for specificity
        return hash(location[:50])

    def _hash_issue(self, issue):
        """
        Extract core issue without specific values.

        Examples:
          "point (1,3) not covered" → "point_not_covered"
          "line L_1 incorrect" → "line_incorrect"
        """
        if not issue:
            return None

        # Normalize to canonical form
        issue_lower = issue.lower()

        # Pattern matching for common error types
        if 'not covered' in issue_lower or 'uncovered' in issue_lower:
            return 'point_not_covered'
        elif 'not on' in issue_lower and 'line' in issue_lower:
            return 'point_not_on_line'
        elif 'construction' in issue_lower and ('fail' in issue_lower or 'incorrect' in issue_lower):
            return 'construction_invalid'
        elif 'argument' in issue_lower and ('flaw' in issue_lower or 'gap' in issue_lower):
            return 'argument_flawed'
        elif 'inductive' in issue_lower and 'step' in issue_lower:
            return 'induction_fails'

        # Fallback: hash core keywords
        keywords = re.findall(r'\b(?:point|line|construction|argument|proof|claim)\b', issue_lower)
        return hash(tuple(keywords))

    def __eq__(self, other):
        return (self.type == other.type and
                self.location_hash == other.location_hash and
                self.issue_hash == other.issue_hash)

    def __hash__(self):
        return hash((self.type, self.location_hash, self.issue_hash))


class ConvergenceDetectorL1:
    """
    Level 1: Detects identical error signatures in TIER 2 refinement.
    """
    def __init__(self, max_repeat=2, verbose=True):
        self.error_history = []
        self.max_repeat = max_repeat
        self.verbose = verbose

    def check_stuck(self, current_errors):
        """
        Check if current errors match recent history.

        Returns:
            (is_stuck: bool, repeat_count: int, recommendation: str)
        """
        # Create fingerprints for current errors
        current_fps = [ErrorFingerprint(e) for e in current_errors]

        if not current_fps:
            return False, 0, None

        # Check if this fingerprint set appeared before
        current_sig = frozenset(current_fps)

        # Count consecutive repeats
        repeat_count = 0
        for historical_errors in reversed(self.error_history):
            historical_fps = [ErrorFingerprint(e) for e in historical_errors]
            historical_sig = frozenset(historical_fps)

            if current_sig == historical_sig:
                repeat_count += 1
            else:
                break  # Consecutive streak broken

        # Add to history
        self.error_history.append(current_errors)

        # Determine if stuck
        is_stuck = repeat_count >= self.max_repeat

        if is_stuck:
            recommendation = self._get_recommendation(repeat_count, current_fps)
            return True, repeat_count, recommendation

        return False, repeat_count, None

    def _get_recommendation(self, repeat_count, error_fps):
        """Generate intervention recommendation based on error pattern."""
        # Identify error type
        error_types = [fp.issue_hash for fp in error_fps]

        if 'point_not_covered' in error_types or 'point_not_on_line' in error_types:
            return "CONSTRUCTION_SEARCH"  # Need different construction approach
        elif 'argument_flawed' in error_types or 'induction_fails' in error_types:
            return "PROOF_STRATEGY_CHANGE"  # Need different proof technique
        elif 'construction_invalid' in error_types:
            return "ESCALATE_REASONING"  # Use high reasoning for breakthrough
        else:
            return "ABORT_TIER2"  # Unknown pattern, accept TIER_1_ONLY
```

**Integration Point:** `code/tier2_refinement.py:tier2_refine_solution()`

**Usage:**
```python
# In TIER 2 refinement loop
detector = ConvergenceDetectorL1(max_repeat=2)

for round_num in range(max_refinement_rounds):
    verification = verify_proof(current_solution)

    if verification['status'] == 'VALID':
        return {'success': True, 'solution': current_solution}

    # Check for stuck pattern
    is_stuck, repeat_count, recommendation = detector.check_stuck(
        verification.get('critical_errors', [])
    )

    if is_stuck:
        print(f"[TIER 2 STUCK] Same errors repeated {repeat_count} times")
        print(f"[TIER 2 STUCK] Recommendation: {recommendation}")

        if recommendation == "CONSTRUCTION_SEARCH":
            # Trigger construction search mode (see Level 4)
            solution = search_alternative_constructions(current_solution, verification)
        elif recommendation == "ESCALATE_REASONING":
            # One final attempt with high reasoning
            if round_num < max_refinement_rounds - 1:
                solution = refine_with_high_reasoning(current_solution, verification)
            else:
                print(f"[TIER 2 ABORT] Accepting TIER_1_ONLY")
                return {'success': False, 'reason': 'stuck_on_errors', 'tier': 'TIER_1_ONLY'}
        else:
            print(f"[TIER 2 ABORT] Accepting TIER_1_ONLY")
            return {'success': False, 'reason': 'stuck_on_errors', 'tier': 'TIER_1_ONLY'}
```

**Expected Impact:**
- Detect stuck pattern after 2 identical errors (instead of 5+)
- Save 3-4 high-reasoning API calls (~$12-16)
- Reduce TIER 2 runtime by 60% (abort early when stuck)

---

## 2. DETECTION LEVEL 2: Verdict Pattern Analysis (RLAC)

### Problem Identified

From RLAC history:
```
Round 0: SUSPICIOUS (k=n construction fails)
Round 1: SUSPICIOUS (k=n construction fails)
Round 2: SUSPICIOUS (k=1 missing from answer)
Round 3: SUSPICIOUS (k=1 construction)
Round 4: SUSPICIOUS (inductive step fails)
Round 5: SUSPICIOUS (inductive step fails)
Round 6: SUSPICIOUS (k=2 construction fails)
Round 7: BROKEN (inductive step - upgraded to P1)
Round 8: UNKNOWN (empty response)
Round 9-11: ROBUST (finally converged)
```

**8 consecutive non-ROBUST verdicts** before breakthrough.

### Proposed Solution: Verdict Pattern Detector

**Algorithm:**
```python
class VerdictPattern:
    """Encodes a sequence of RLAC verdicts for pattern matching."""
    def __init__(self, verdicts, window=3):
        """
        Args:
            verdicts: List of verdict strings (ROBUST, BROKEN, SUSPICIOUS, UNKNOWN)
            window: Number of recent verdicts to consider
        """
        self.pattern = tuple(verdicts[-window:])
        self.window = window

    def is_stuck_pattern(self):
        """
        Detect known stuck patterns.

        Returns:
            (is_stuck: bool, pattern_name: str, confidence: float)
        """
        # Pattern 1: All non-ROBUST for long stretch
        if all(v in ['BROKEN', 'SUSPICIOUS'] for v in self.pattern):
            confidence = len(self.pattern) / 5.0  # Confidence increases with length
            return True, 'PERSISTENT_BROKEN', min(confidence, 1.0)

        # Pattern 2: Oscillating between BROKEN and SUSPICIOUS
        if len(set(self.pattern)) == 2 and 'ROBUST' not in self.pattern:
            return True, 'OSCILLATING', 0.7

        # Pattern 3: UNKNOWN after consecutive failures (model giving up)
        if self.pattern[-1] == 'UNKNOWN' and len([v for v in self.pattern[:-1] if v != 'ROBUST']) >= 2:
            return True, 'MODEL_EXHAUSTION', 0.9

        # Pattern 4: Repeated SUSPICIOUS on same issue
        if self.pattern.count('SUSPICIOUS') >= 3:
            return True, 'STUCK_ON_SUSPICIOUS', 0.8

        return False, None, 0.0


class ConvergenceDetectorL2:
    """
    Level 2: Detects verdict patterns in RLAC adversarial testing.
    """
    def __init__(self, intervention_threshold=4, verbose=True):
        self.verdict_history = []
        self.intervention_threshold = intervention_threshold
        self.verbose = verbose

    def add_verdict(self, verdict):
        """Add new verdict to history."""
        self.verdict_history.append(verdict)

    def check_convergence(self):
        """
        Analyze verdict history for convergence or stuck patterns.

        Returns:
            {
                'converged': bool,
                'stuck': bool,
                'pattern': str or None,
                'recommendation': str or None,
                'consecutive_robust': int
            }
        """
        if len(self.verdict_history) < 3:
            return {'converged': False, 'stuck': False}

        # Check for convergence (3 consecutive ROBUST)
        recent = self.verdict_history[-3:]
        if all(v == 'ROBUST' for v in recent):
            return {
                'converged': True,
                'stuck': False,
                'pattern': 'CONVERGED',
                'recommendation': None,
                'consecutive_robust': 3
            }

        # Check for stuck patterns
        pattern = VerdictPattern(self.verdict_history, window=5)
        is_stuck, pattern_name, confidence = pattern.is_stuck_pattern()

        if is_stuck:
            recommendation = self._get_intervention(pattern_name, confidence)
            return {
                'converged': False,
                'stuck': True,
                'pattern': pattern_name,
                'confidence': confidence,
                'recommendation': recommendation,
                'consecutive_robust': 0
            }

        return {'converged': False, 'stuck': False}

    def _get_intervention(self, pattern_name, confidence):
        """Recommend intervention based on stuck pattern."""
        if pattern_name == 'PERSISTENT_BROKEN':
            if confidence > 0.8:
                return 'ABANDON_CONSTRUCTION'  # Try completely different approach
            else:
                return 'ESCALATE_REASONING'  # Switch to high reasoning

        elif pattern_name == 'OSCILLATING':
            return 'STABILIZE_ANSWER'  # Lock answer, focus on proof quality

        elif pattern_name == 'MODEL_EXHAUSTION':
            return 'FRESH_START'  # Emergency fresh start with different prompt

        elif pattern_name == 'STUCK_ON_SUSPICIOUS':
            return 'ESCALATE_CRITIC'  # Use high reasoning for critic

        return 'CONTINUE'
```

**Integration Point:** `code/agent_gpt_oss.py:rlac_agent()`

**Usage:**
```python
# In RLAC loop
detector_l2 = ConvergenceDetectorL2(intervention_threshold=4)

for round_num in range(max_rlac_rounds):
    # ... get critic verdict ...

    detector_l2.add_verdict(verdict)

    convergence_status = detector_l2.check_convergence()

    if convergence_status['converged']:
        print(f"[RLAC SUCCESS] Converged after {round_num+1} rounds")
        break

    if convergence_status['stuck']:
        pattern = convergence_status['pattern']
        recommendation = convergence_status['recommendation']
        confidence = convergence_status['confidence']

        print(f"[RLAC STUCK] Pattern: {pattern} (confidence: {confidence:.2f})")
        print(f"[RLAC INTERVENTION] {recommendation}")

        if recommendation == 'ABANDON_CONSTRUCTION':
            print(f"[RLAC STRATEGY SHIFT] Current construction failing repeatedly")
            print(f"[RLAC STRATEGY SHIFT] Requesting fresh start with different approach")
            # Trigger fresh start with explicit instruction to try different construction
            solution = generate_fresh_with_hint(
                problem=problem,
                failed_approach="construction using formula L_t",
                hint="Try using different slopes or mixed vertical/sunny lines"
            )

        elif recommendation == 'ESCALATE_REASONING':
            print(f"[RLAC ESCALATION] Switching generator to high reasoning")
            current_sol_reasoning = "high"

        elif recommendation == 'FRESH_START':
            print(f"[RLAC EMERGENCY] Model exhausted - fresh start")
            solution = emergency_fresh_start(problem, round_num)
```

**Expected Impact:**
- Detect stuck pattern after 4-5 rounds (instead of 8+)
- Trigger intervention before model exhaustion
- Reduce RLAC rounds by 30-40%

---

## 3. DETECTION LEVEL 3: Answer Stability Tracking

### Problem Identified

From logs:
```
Iteration 4: Answer changed (1st change)
Iteration 7: Answer changed (2nd change)
[RLAC STABILITY] Answer changed (2 total changes)
```

Answer changed **twice** before stabilizing, despite "answer lock" mechanism.

### Proposed Solution: Answer Trajectory Analysis

**Algorithm:**
```python
class AnswerTrajectory:
    """Tracks answer evolution and detects instability patterns."""
    def __init__(self, initial_answer):
        self.history = [initial_answer]
        self.change_points = []
        self.semantic_distances = []

    def add_answer(self, new_answer, round_num):
        """
        Add new answer and compute semantic distance from previous.

        Returns:
            (changed: bool, distance: float, change_type: str)
        """
        prev_answer = self.history[-1]

        # Compute semantic distance
        distance = self._semantic_distance(prev_answer, new_answer)
        self.semantic_distances.append(distance)

        # Determine change type
        if distance < 0.1:
            change_type = 'STABLE'
        elif distance < 0.3:
            change_type = 'MINOR_REFINEMENT'
        elif distance < 0.7:
            change_type = 'MODERATE_CHANGE'
        else:
            change_type = 'MAJOR_CHANGE'

        if change_type in ['MODERATE_CHANGE', 'MAJOR_CHANGE']:
            self.change_points.append(round_num)

        self.history.append(new_answer)

        return distance > 0.1, distance, change_type

    def _semantic_distance(self, ans1, ans2):
        """
        Compute semantic distance between two answers.

        Uses:
        1. String edit distance (normalized)
        2. Set notation comparison (k values)
        3. Structural similarity

        Returns: float in [0, 1] where 0=identical, 1=completely different
        """
        if ans1 == ans2:
            return 0.0

        # Normalize both answers
        ans1_norm = self._normalize_answer(ans1)
        ans2_norm = self._normalize_answer(ans2)

        # Extract k-values if present
        k1_set = self._extract_k_values(ans1_norm)
        k2_set = self._extract_k_values(ans2_norm)

        if k1_set and k2_set:
            # Use Jaccard distance for set comparison
            intersection = len(k1_set & k2_set)
            union = len(k1_set | k2_set)
            return 1.0 - (intersection / union if union > 0 else 0)

        # Fallback: edit distance
        from difflib import SequenceMatcher
        matcher = SequenceMatcher(None, ans1_norm, ans2_norm)
        return 1.0 - matcher.ratio()

    def _normalize_answer(self, ans):
        """Normalize answer for comparison."""
        import re
        # Remove LaTeX commands
        ans = re.sub(r'\\[a-z]+\s*', '', ans)
        # Remove whitespace
        ans = ''.join(ans.split())
        # Lowercase
        return ans.lower()

    def _extract_k_values(self, ans):
        """Extract set of k values from answer."""
        import re
        # Look for patterns like {0,1}, {0,1,3}, etc.
        set_match = re.search(r'\{([\d,\s]+)\}', ans)
        if set_match:
            values = set_match.group(1)
            return set([int(x.strip()) for x in values.split(',') if x.strip().isdigit()])

        # Look for single values
        val_matches = re.findall(r'k\s*=\s*(\d+)', ans)
        if val_matches:
            return set([int(v) for v in val_matches])

        return None

    def is_converging(self, window=3):
        """
        Check if answer is converging (distances decreasing).

        Returns: (converging: bool, trend: str, confidence: float)
        """
        if len(self.semantic_distances) < window:
            return False, 'INSUFFICIENT_DATA', 0.0

        recent = self.semantic_distances[-window:]

        # Check if distances are decreasing
        is_decreasing = all(recent[i] >= recent[i+1] for i in range(len(recent)-1))

        if is_decreasing:
            return True, 'CONVERGING', 0.9

        # Check if oscillating
        changes_direction = sum(1 for i in range(len(recent)-1)
                               if (recent[i] < recent[i+1]) != (recent[0] < recent[1]))
        if changes_direction >= 2:
            return False, 'OSCILLATING', 0.8

        # Check if stable
        if all(d < 0.1 for d in recent):
            return True, 'STABLE', 1.0

        return False, 'DIVERGING', 0.6


class ConvergenceDetectorL3:
    """
    Level 3: Tracks answer trajectory and stability.
    """
    def __init__(self, max_changes=2, verbose=True):
        self.trajectory = None
        self.max_changes = max_changes
        self.verbose = verbose
        self.lock_eligible = False

    def initialize(self, initial_answer):
        """Initialize with first answer."""
        self.trajectory = AnswerTrajectory(initial_answer)

    def update(self, new_answer, round_num):
        """
        Update with new answer.

        Returns:
            {
                'changed': bool,
                'distance': float,
                'change_type': str,
                'total_changes': int,
                'should_lock': bool,
                'converging': bool
            }
        """
        changed, distance, change_type = self.trajectory.add_answer(new_answer, round_num)

        total_changes = len(self.trajectory.change_points)

        # Check convergence
        converging, trend, confidence = self.trajectory.is_converging()

        # Determine if should lock answer
        should_lock = (total_changes >= self.max_changes or
                      (converging and trend == 'STABLE'))

        if self.verbose and changed:
            print(f"[ANSWER STABILITY] Answer changed ({change_type})")
            print(f"[ANSWER STABILITY] Semantic distance: {distance:.3f}")
            print(f"[ANSWER STABILITY] Total changes: {total_changes}")
            print(f"[ANSWER STABILITY] Trend: {trend} (confidence: {confidence:.2f})")

        return {
            'changed': changed,
            'distance': distance,
            'change_type': change_type,
            'total_changes': total_changes,
            'should_lock': should_lock,
            'converging': converging,
            'trend': trend,
            'confidence': confidence
        }
```

**Integration Point:** `code/agent_gpt_oss.py:rlac_agent()` (answer comparison)

**Usage:**
```python
# In RLAC loop
detector_l3 = ConvergenceDetectorL3(max_changes=2)
detector_l3.initialize(initial_answer)

for round_num in range(max_rlac_rounds):
    # ... generate revised solution ...
    new_answer = extract_answer(revised_solution)

    stability = detector_l3.update(new_answer, round_num)

    if stability['changed']:
        if stability['total_changes'] > 2:
            print(f"[ANSWER WARNING] Excessive changes ({stability['total_changes']})")
            print(f"[ANSWER WARNING] Answer may be unstable - consider aborting")

        if stability['change_type'] == 'MAJOR_CHANGE':
            print(f"[ANSWER ALERT] Major semantic change detected!")
            print(f"[ANSWER ALERT] Resetting robust counter")
            consecutive_robust = 0

    if stability['should_lock']:
        if not answer_locked:
            print(f"[ANSWER LOCK] Enabling answer lock (stability achieved)")
            answer_locked = True
            locked_answer = new_answer
```

**Expected Impact:**
- Early detection of answer instability
- Prevent excessive answer changes (>2)
- Better lock timing based on convergence

---

## 4. DETECTION LEVEL 4: Construction Search Exhaustion

### Problem Identified

From RLAC history rounds 0-6:
- All attempts used same construction formula: `L_t: y = t/(t+1) * x + 1/(t+1)`
- **6 rounds** wasted before abandoning this approach
- No mechanism to detect "construction search space exhausted"

### Proposed Solution: Construction Attempt Tracker

**Algorithm:**
```python
class ConstructionAttempt:
    """Represents a single construction attempt with signature."""
    def __init__(self, lines, k_target, n_value):
        """
        Args:
            lines: List of line equations as strings
            k_target: Target number of sunny lines
            n_value: Problem parameter n
        """
        self.lines = lines
        self.k_target = k_target
        self.n_value = n_value
        self.signature = self._compute_signature()

    def _compute_signature(self):
        """
        Compute structural signature of construction.

        Captures:
        - Number of vertical lines
        - Number of horizontal lines
        - Slope pattern of sunny lines
        - Formula pattern (if detectable)
        """
        vertical_count = sum(1 for line in self.lines if self._is_vertical(line))
        horizontal_count = sum(1 for line in self.lines if self._is_horizontal(line))

        slopes = [self._extract_slope(line) for line in self.lines
                 if not self._is_vertical(line) and not self._is_horizontal(line)]

        # Check for formula pattern
        formula_type = self._detect_formula_pattern(slopes)

        return {
            'vertical': vertical_count,
            'horizontal': horizontal_count,
            'slope_pattern': tuple(sorted([abs(s) for s in slopes if s is not None])),
            'formula_type': formula_type
        }

    def _is_vertical(self, line):
        """Check if line is vertical (x = const)."""
        import re
        return bool(re.match(r'x\s*=\s*\d+', line))

    def _is_horizontal(self, line):
        """Check if line is horizontal (y = const)."""
        import re
        return bool(re.match(r'y\s*=\s*\d+', line))

    def _extract_slope(self, line):
        """Extract slope from line equation y = mx + b."""
        import re
        # Pattern: y = (fraction)x + ...
        match = re.search(r'y\s*=\s*([-+]?\d+/\d+|[-+]?\d+\.?\d*)\s*\*?\s*x', line)
        if match:
            slope_str = match.group(1)
            if '/' in slope_str:
                num, denom = slope_str.split('/')
                return float(num) / float(denom)
            return float(slope_str)
        return None

    def _detect_formula_pattern(self, slopes):
        """
        Detect if slopes follow a formula pattern.

        Common patterns:
        - t/(t+1) for t=1,2,3...
        - Arithmetic progression
        - Geometric progression
        """
        if not slopes or len(slopes) < 2:
            return None

        # Check t/(t+1) pattern
        expected_t_over_t_plus_1 = [t/(t+1) for t in range(1, len(slopes)+1)]
        if all(abs(slopes[i] - expected_t_over_t_plus_1[i]) < 0.01
              for i in range(len(slopes))):
            return 't/(t+1)'

        # Check arithmetic progression
        diffs = [slopes[i+1] - slopes[i] for i in range(len(slopes)-1)]
        if all(abs(diffs[i] - diffs[0]) < 0.01 for i in range(len(diffs))):
            return 'arithmetic'

        # Check geometric progression
        if all(slopes[i] != 0 for i in range(len(slopes))):
            ratios = [slopes[i+1] / slopes[i] for i in range(len(slopes)-1)]
            if all(abs(ratios[i] - ratios[0]) < 0.01 for i in range(len(ratios))):
                return 'geometric'

        return 'custom'

    def is_similar_to(self, other):
        """Check if two constructions are structurally similar."""
        if self.signature['formula_type'] == other.signature['formula_type']:
            if self.signature['formula_type'] in ['t/(t+1)', 'arithmetic', 'geometric']:
                return True  # Same formula family

        # Check structural similarity
        return (self.signature['vertical'] == other.signature['vertical'] and
                self.signature['horizontal'] == other.signature['horizontal'] and
                self.signature['slope_pattern'] == other.signature['slope_pattern'])


class ConvergenceDetectorL4:
    """
    Level 4: Tracks construction attempts and detects exhaustion.
    """
    def __init__(self, max_similar_attempts=3, verbose=True):
        self.attempt_history = []
        self.max_similar_attempts = max_similar_attempts
        self.verbose = verbose

    def add_attempt(self, construction_data, verdict):
        """
        Add construction attempt to history.

        Args:
            construction_data: Dict with 'lines', 'k_target', 'n_value'
            verdict: RLAC verdict (ROBUST, BROKEN, SUSPICIOUS)
        """
        attempt = ConstructionAttempt(
            lines=construction_data['lines'],
            k_target=construction_data['k_target'],
            n_value=construction_data['n_value']
        )

        self.attempt_history.append({
            'attempt': attempt,
            'verdict': verdict,
            'round': len(self.attempt_history)
        })

    def check_exhaustion(self):
        """
        Check if construction search space is exhausted.

        Returns:
            {
                'exhausted': bool,
                'similar_count': int,
                'formula_stuck': bool,
                'recommendation': str
            }
        """
        if len(self.attempt_history) < self.max_similar_attempts:
            return {'exhausted': False}

        # Get recent attempts
        recent = self.attempt_history[-self.max_similar_attempts:]

        # Check if all failed
        all_failed = all(a['verdict'] in ['BROKEN', 'SUSPICIOUS'] for a in recent)

        if not all_failed:
            return {'exhausted': False}

        # Check if all attempts are similar
        attempts = [a['attempt'] for a in recent]
        reference = attempts[0]

        similar_count = sum(1 for a in attempts if reference.is_similar_to(a))

        # Check if stuck on same formula
        formula_types = [a.signature['formula_type'] for a in attempts]
        formula_stuck = (len(set(formula_types)) == 1 and
                        formula_types[0] in ['t/(t+1)', 'arithmetic', 'geometric'])

        exhausted = similar_count >= self.max_similar_attempts - 1

        if exhausted:
            recommendation = self._get_recommendation(formula_stuck, reference)
            return {
                'exhausted': True,
                'similar_count': similar_count,
                'formula_stuck': formula_stuck,
                'stuck_formula': formula_types[0] if formula_stuck else None,
                'recommendation': recommendation
            }

        return {'exhausted': False}

    def _get_recommendation(self, formula_stuck, reference_attempt):
        """Generate recommendation for escaping construction trap."""
        if formula_stuck:
            formula_type = reference_attempt.signature['formula_type']
            return {
                'action': 'ABANDON_FORMULA',
                'reason': f"Stuck on {formula_type} formula pattern for {self.max_similar_attempts} rounds",
                'suggestion': "Try mixed construction (vertical + sunny lines) or different slope selection"
            }
        else:
            return {
                'action': 'TRY_DIFFERENT_STRUCTURE',
                'reason': f"Similar construction structure failed {self.max_similar_attempts} times",
                'suggestion': "Consider different k-value or completely different line configuration"
            }
```

**Integration Point:** `code/adversarial_critic.py` (after each attack)

**Usage:**
```python
# In RLAC loop after each verdict
detector_l4 = ConvergenceDetectorL4(max_similar_attempts=3)

for round_num in range(max_rlac_rounds):
    # ... get critic verdict and counterexamples ...

    # Extract construction from solution
    construction_data = parse_construction_from_solution(current_solution)

    if construction_data:
        detector_l4.add_attempt(construction_data, verdict)

        exhaustion = detector_l4.check_exhaustion()

        if exhaustion.get('exhausted'):
            print(f"[CONSTRUCTION SEARCH] Exhausted after {exhaustion['similar_count']} similar attempts")

            if exhaustion['formula_stuck']:
                print(f"[CONSTRUCTION SEARCH] Stuck on formula: {exhaustion['stuck_formula']}")

            recommendation = exhaustion['recommendation']
            print(f"[CONSTRUCTION SEARCH] Recommendation: {recommendation['action']}")
            print(f"[CONSTRUCTION SEARCH] Reason: {recommendation['reason']}")
            print(f"[CONSTRUCTION SEARCH] Suggestion: {recommendation['suggestion']}")

            # Trigger fresh start with explicit hint
            solution = generate_fresh_with_construction_hint(
                problem=problem,
                avoid_formula=exhaustion.get('stuck_formula'),
                suggestion=recommendation['suggestion']
            )
```

**Expected Impact:**
- Detect construction exhaustion after 3 similar attempts (instead of 6+)
- Save 3+ rounds of wasted API calls
- Trigger proactive strategy shift

---

## 5. Integration: Multi-Level Orchestration

### Orchestrator Design

```python
class ConvergenceOrchestrator:
    """
    Orchestrates all 4 levels of convergence detection.

    Hierarchy:
    L1: Error signatures (TIER 2 specific)
    L2: Verdict patterns (RLAC specific)
    L3: Answer stability (cross-cutting)
    L4: Construction exhaustion (RLAC specific)
    """
    def __init__(self, config):
        self.l1 = ConvergenceDetectorL1(max_repeat=config.get('l1_max_repeat', 2))
        self.l2 = ConvergenceDetectorL2(intervention_threshold=config.get('l2_threshold', 4))
        self.l3 = ConvergenceDetectorL3(max_changes=config.get('l3_max_changes', 2))
        self.l4 = ConvergenceDetectorL4(max_similar_attempts=config.get('l4_max_attempts', 3))

        self.current_phase = None  # 'RLAC' or 'TIER2'

    def set_phase(self, phase):
        """Set current phase (RLAC or TIER2)."""
        self.current_phase = phase

    def check_all(self, context):
        """
        Check all applicable detectors based on current phase.

        Args:
            context: Dict with phase-specific data

        Returns:
            {
                'should_abort': bool,
                'should_intervene': bool,
                'intervention': str,
                'reason': str,
                'detections': dict
            }
        """
        detections = {}

        if self.current_phase == 'RLAC':
            # L2: Verdict patterns
            self.l2.add_verdict(context['verdict'])
            convergence = self.l2.check_convergence()
            detections['l2_verdict_pattern'] = convergence

            # L3: Answer stability
            if 'answer' in context:
                stability = self.l3.update(context['answer'], context['round'])
                detections['l3_answer_stability'] = stability

            # L4: Construction exhaustion
            if 'construction' in context:
                self.l4.add_attempt(context['construction'], context['verdict'])
                exhaustion = self.l4.check_exhaustion()
                detections['l4_construction'] = exhaustion

            # Decision logic
            if convergence.get('converged'):
                return {
                    'should_abort': False,
                    'should_intervene': False,
                    'reason': 'CONVERGED',
                    'detections': detections
                }

            # Priority: Construction exhaustion > Verdict pattern > Answer instability
            if exhaustion.get('exhausted'):
                return {
                    'should_abort': False,
                    'should_intervene': True,
                    'intervention': exhaustion['recommendation']['action'],
                    'reason': exhaustion['recommendation']['reason'],
                    'detections': detections
                }

            if convergence.get('stuck'):
                return {
                    'should_abort': convergence['recommendation'] == 'ABORT',
                    'should_intervene': True,
                    'intervention': convergence['recommendation'],
                    'reason': f"Verdict pattern: {convergence['pattern']}",
                    'detections': detections
                }

        elif self.current_phase == 'TIER2':
            # L1: Error signatures
            if 'verification_errors' in context:
                is_stuck, repeat_count, recommendation = self.l1.check_stuck(
                    context['verification_errors']
                )
                detections['l1_error_signature'] = {
                    'stuck': is_stuck,
                    'repeat_count': repeat_count,
                    'recommendation': recommendation
                }

                if is_stuck:
                    return {
                        'should_abort': recommendation in ['ABORT_TIER2'],
                        'should_intervene': True,
                        'intervention': recommendation,
                        'reason': f"Error repeated {repeat_count} times",
                        'detections': detections
                    }

        return {
            'should_abort': False,
            'should_intervene': False,
            'reason': 'CONTINUE',
            'detections': detections
        }
```

---

## 6. Configuration and Tuning

**Recommended Default Configuration:**

```python
convergence_config = {
    # Level 1: Error signatures (TIER 2)
    'l1_max_repeat': 2,  # Abort after 2 identical errors
    'l1_verbose': True,

    # Level 2: Verdict patterns (RLAC)
    'l2_threshold': 4,  # Intervene after 4 non-ROBUST verdicts
    'l2_window': 5,  # Look at last 5 verdicts
    'l2_verbose': True,

    # Level 3: Answer stability
    'l3_max_changes': 2,  # Lock after 2 changes
    'l3_window': 3,  # Convergence window
    'l3_verbose': True,

    # Level 4: Construction exhaustion
    'l4_max_attempts': 3,  # Abandon after 3 similar attempts
    'l4_verbose': True
}
```

**Performance Tuning Guide:**

| Scenario | Adjustment | Impact |
|----------|-----------|--------|
| **Aggressive early stopping** | l1_max_repeat=1, l2_threshold=3, l4_max_attempts=2 | Faster but may miss breakthroughs |
| **Conservative (more exploration)** | l1_max_repeat=3, l2_threshold=6, l4_max_attempts=4 | Slower but more thorough |
| **Production (balanced)** | Default config | Good efficiency/quality tradeoff |

---

## 7. Expected Results (Problem 1 Scenario)

### Before Convergence Detection:
- **RLAC:** 12 rounds (8 wasted)
- **TIER 2:** 5 rounds (all wasted, identical errors)
- **Runtime:** 51 minutes
- **Cost:** ~$44
- **Outcome:** TIER_1_ONLY

### After Convergence Detection:
- **RLAC:** 7-8 rounds (intervention at round 6, fresh start)
  - Round 6: L4 detects construction exhaustion
  - Round 7: Fresh start with different construction
  - Rounds 7-9: Converge to correct answer
- **TIER 2:** 2-3 rounds (early abort after L1 detects stuck)
  - Round 2: L1 detects identical k=3 construction error
  - Abort with TIER_1_ONLY instead of wasting 3 more rounds
- **Runtime:** 18-22 minutes (60% reduction)
- **Cost:** ~$18-22 (50% reduction)
- **Outcome:** TIER_1_ONLY (same, but faster)

---

## 8. Implementation Roadmap

**Phase 1 (Week 1):** Level 1 - Error Signature Matching
- Implement ErrorFingerprint class
- Integrate into TIER 2 refinement loop
- Test on problem 1 logs (should abort at round 2)

**Phase 2 (Week 1-2):** Level 2 - Verdict Pattern Analysis
- Implement VerdictPattern detector
- Integrate into RLAC loop
- Test intervention triggers

**Phase 3 (Week 2):** Level 3 - Answer Stability
- Implement AnswerTrajectory tracking
- Integrate answer lock logic
- Test convergence detection

**Phase 4 (Week 2-3):** Level 4 - Construction Exhaustion
- Implement ConstructionAttempt parser
- Integrate fresh start triggers
- Test on construction-heavy problems

**Phase 5 (Week 3):** Integration & Tuning
- Implement ConvergenceOrchestrator
- Run integration tests
- Tune thresholds based on test results

---

## Summary

This multi-level convergence detection system provides:

1. **Early Detection:** Catch stuck patterns after 2-4 rounds (vs 5-8 currently)
2. **Targeted Interventions:** Different strategies for different stuck patterns
3. **Cost Efficiency:** 40-60% reduction in wasted API calls
4. **Quality Preservation:** Maintain success rate while improving speed

**Key Innovation:** Hierarchical detection at multiple abstraction levels (errors, verdicts, answers, constructions) provides robust coverage of all stuck scenarios.

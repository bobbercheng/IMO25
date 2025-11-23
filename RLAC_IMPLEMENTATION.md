# RLAC Implementation Details

This document covers the technical implementation of the RLAC (Reinforcement Learning with Adversarial Critics) system.

## Architecture Overview

### Core Components

```
┌─────────────────────────────────────────────────────────────┐
│                      RLACAgent                               │
│                                                              │
│  ┌─────────────────┐     ┌─────────────────────────────┐    │
│  │  GeneratorAgent │────▶│   AdversarialCriticAgent    │    │
│  │                 │◀────│                             │    │
│  │  - Initial gen  │     │  - Attack solution          │    │
│  │  - Revise       │     │  - Generate counterexamples │    │
│  │  - Answer recon │     │  - Progressive intensity    │    │
│  └─────────────────┘     └─────────────────────────────┘    │
│           │                          │                       │
│           ▼                          ▼                       │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Reinforcement Signal                    │    │
│  │  ROBUST (+10) | BROKEN (-10/-5/-2) | SUSPICIOUS     │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### File Structure

| File | Purpose |
|------|---------|
| `code/adversarial_critic.py` | AdversarialCritic class with attack methods |
| `code/adversarial_prompts.py` | All prompt templates |
| `code/rlac_improvements.py` | Enhanced validation pipeline and state machine |
| `code/agent_rlac.py` | Standalone RLAC agent |
| `code/agent_gpt_oss.py` | Integrated RLAC mode |

## Key Classes

### AdversarialCritic

```python
class AdversarialCritic:
    """
    Adversarial critic that actively tries to break mathematical solutions.

    Key Methods:
    - attack_solution(): Main attack method with progressive intensity
    - detect_stuck_pattern(): Detect when generator is stuck
    - create_enhanced_session(): Create session with validation pipeline
    """

    def __init__(self, reasoning_effort="high", verbose=True, log_file=None):
        self.reasoning_effort = reasoning_effort
        self.attack_history = []
        self.total_attacks = 0
        self.total_counterexamples = 0
```

### EnhancedAdversarialSession

```python
class EnhancedAdversarialSession:
    """
    Enhanced session with three key improvements:
    1. Validation Pipeline (fail-fast + retry)
    2. LaTeX Brace-Matching Parser
    3. Verdict State Machine with confidence scoring
    """
```

## Prompt System

### Adversarial Critic System Prompt

Located in `adversarial_prompts.py`:

```python
adversarial_critic_system_prompt = """
You are an ADVERSARIAL CRITIC for mathematical proofs.
Your goal is to BREAK solutions, not grade them cooperatively.

### Your Mission ###
Your ONLY job is to find counterexamples, edge cases, or logical flaws.
You are REWARDED for breaking solutions, NOT for accepting them.

### Adversarial Mindset ###
1. Assume the solution is wrong until proven otherwise
2. Generate concrete counterexamples to test claims
3. Find boundary cases where logic might fail
4. Challenge implicit assumptions
5. Be maximally skeptical

### Attack Strategies ###
- Counterexample Generation: Find X that doesn't satisfy Y
- Boundary Testing: n=0, n=1, negative, infinity
- Assumption Challenge: "Does this work if [condition] doesn't hold?"
- Construction Attack: "Can I build a configuration that breaks this?"

### Output Format ###
ADVERSARIAL_VERDICT: [BROKEN / SUSPICIOUS / ROBUST]

COUNTEREXAMPLE_1: [Concrete example with specific values]
COUNTEREXAMPLE_2: ...

CRITICAL_FLAWS:
FLAW_1: [Logical error that invalidates the proof]

SEVERITY:
CRITICAL_COUNT: [number]
MAJOR_COUNT: [number]
MINOR_COUNT: [number]
"""
```

### Progressive Attack Intensity

```python
def get_attack_intensity_prompt(round_num, max_rounds):
    """Curriculum learning for attack intensity."""
    if round_num < 3:
        return "BASIC", adversarial_attack_basic
    elif round_num < 7:
        return "MODERATE", adversarial_attack_moderate
    else:
        return "ADVANCED", adversarial_attack_advanced
```

**Basic Attacks** (Rounds 0-2):
- Check base case handling
- Test with small values (n=0, 1, 2)
- Look for simple algebraic errors

**Moderate Attacks** (Rounds 3-6):
- Boundary conditions (n=0, negative, infinity)
- Challenge implicit assumptions
- Check logical flow gaps

**Advanced Attacks** (Rounds 7+):
- Construct adversarial configurations
- Check for circular reasoning
- Verify quantifier ordering
- Look for measure-zero exceptions

### Answer Reconsideration Prompt

Triggered when the same counterexample appears repeatedly:

```python
answer_reconsideration_prompt = """
### ANSWER RECONSIDERATION MODE ###

Your previous answer has NOT IMPROVED despite multiple proof revisions.
This suggests the ANSWER ITSELF is wrong, not just the proof.

**Evidence of Wrong Answer**:
{evidence_summary}

**What You Must Do Now**:
1. ACCEPT: Your previous answer is incorrect
2. RE-READ: Carefully read the problem statement again
3. SEARCH: Look for DIFFERENT possible answers
4. TEST: Check each candidate against known counterexamples
5. PROPOSE: A completely different answer

**Critical Rules**:
- Do NOT try to defend the previous answer
- Do NOT propose a minor variation
- Do PROPOSE a fundamentally different answer if you find one
"""
```

## Validation Pipeline

### Solution Validation (Counter-Proposal 1)

The validation pipeline performs ordered checks before attacking:

```python
class SolutionValidationPipeline:
    """Fail-fast validation with actionable retry prompts."""

    def validate(self, solution: str) -> PipelineResult:
        checks = [
            ("null_check", self._check_null, "critical"),
            ("empty_check", self._check_empty, "critical"),
            ("min_length", self._check_min_length, "error"),
            ("structure_markers", self._check_structure, "error"),
            ("mathematical_content", self._check_math_content, "warning"),
            ("answer_presence", self._check_answer, "warning"),
            ("proof_substance", self._check_substance, "warning"),
        ]

        for name, check_func, severity in checks:
            passed, message = check_func(solution)
            if not passed:
                if severity == "critical":
                    return PipelineResult(valid=False, should_retry=True)
```

### LaTeX Parser (Counter-Proposal 2)

Proper brace-matching for nested LaTeX:

```python
class LaTeXBraceParser:
    """Handle nested braces like \boxed{\frac{a}{b}}."""

    def extract_boxed(self, text: str) -> LaTeXParseResult:
        # Find \boxed{ and track brace depth
        start = text.find(r'\boxed{')
        if start == -1:
            return LaTeXParseResult(found=False)

        depth = 1
        pos = start + 7  # After '\boxed{'

        while pos < len(text) and depth > 0:
            if text[pos] == '{':
                depth += 1
            elif text[pos] == '}':
                depth -= 1
            pos += 1

        content = text[start + 7:pos - 1]
        return LaTeXParseResult(
            found=True,
            content=content,
            normalized=self._normalize(content)
        )
```

### Verdict State Machine (Counter-Proposal 3)

```python
class VerdictStateMachine:
    """Track verdict history with confidence scoring."""

    class VerdictState(Enum):
        UNKNOWN = "unknown"
        BROKEN = "broken"
        SUSPICIOUS = "suspicious"
        WEAK = "weak"
        ROBUST = "robust"
        VERIFIED = "verified"

    def evaluate_attack(self, attack_text, counterexamples, solution):
        # Calculate confidence based on evidence
        confidence = 0.0
        evidence_types = []

        if "ADVERSARIAL_VALIDATION_PASSED" in attack_text:
            confidence = 0.9
            state = VerdictState.ROBUST
        elif counterexamples:
            confidence = 0.8
            state = VerdictState.BROKEN
            evidence_types.append("counterexample")

        return VerdictConfidence(state, confidence, evidence_types)
```

## Main RLAC Loop

### Solve Method (agent_rlac.py)

```python
def solve(self, problem: str, log_file: Optional[str] = None):
    """Main RLAC solving loop."""

    # Initialize
    solution = None
    criticism_history = []
    cumulative_reward = 0.0
    consecutive_robust = 0

    for iteration in range(1, self.max_iterations + 1):

        # PHASE 1: GENERATION
        if iteration == 1:
            solution = self.generator.generate_initial_solution(problem)
        else:
            # Check for answer reconsideration trigger
            should_reconsider = self._should_reconsider_answer(
                criticism_history, solution
            )
            solution = self.generator.revise_solution(
                problem, solution, criticism_history[-1],
                criticism_history, should_reconsider
            )

        # PHASE 2: ADVERSARIAL ATTACK
        attack_intensity = self._get_attack_intensity(iteration)
        criticism = self.critic.adversarial_attack(
            problem, solution, attack_intensity
        )

        # PHASE 3: REINFORCEMENT SIGNAL
        if criticism.no_flaws_found:
            reward = 10.0
            cumulative_reward += reward
            consecutive_robust += 1

            if consecutive_robust >= self.robust_threshold:
                return {'success': True, 'solution': solution}
        else:
            penalty = self._calculate_penalty(criticism.flaws)
            cumulative_reward += penalty
            consecutive_robust = 0
            criticism_history.append(criticism)

        # PHASE 4: STUCK DETECTION
        if self._is_stuck(criticism_history):
            self._handle_stuck(criticism_history)
```

### Answer Reconsideration Detection

```python
def _should_reconsider_answer(self, criticism_history, solution, min_rounds=3):
    """Detect when answer itself (not proof) is the problem."""

    if len(criticism_history) < min_rounds:
        return False

    recent = criticism_history[-min_rounds:]

    # Extract counterexamples from recent rounds
    all_counterexamples = []
    for crit in recent:
        all_counterexamples.extend(crit.counterexamples)

    # Check for repeating counterexamples
    ce_counts = {}
    for ce in all_counterexamples:
        normalized = self._normalize_counterexample(ce)
        ce_counts[normalized] = ce_counts.get(normalized, 0) + 1

    # If any counterexample repeated N-1 times, answer is likely wrong
    for ce, count in ce_counts.items():
        if count >= min_rounds - 1:
            return True

    return False
```

### Stuck Pattern Detection

```python
def detect_stuck_pattern(self, recent_rounds=4):
    """Detect if generator is stuck."""

    recent_attacks = self.attack_history[-recent_rounds:]

    # Pattern 1: All recent attacks found issues
    all_broken = all(a['verdict'] == 'BROKEN' for a in recent_attacks)

    # Pattern 2: Same counterexamples appearing repeatedly
    first_ces = set(recent_attacks[0].get('counterexamples', [])[:3])
    last_ces = set(recent_attacks[-1].get('counterexamples', [])[:3])
    overlapping_ces = len(first_ces & last_ces) > 0

    # Pattern 3: Same flaw types repeating
    flaw_types = [set(a.get('flaw_types', [])) for a in recent_attacks]
    repeating_flaws = len(set.intersection(*flaw_types)) > 0 if flaw_types else False

    return {
        'is_stuck': all_broken and (overlapping_ces or repeating_flaws),
        'has_counterexamples': overlapping_ces,
        'counterexamples': list(first_ces & last_ces) if overlapping_ces else []
    }
```

## Data Structures

### Criticism

```python
@dataclass
class Criticism:
    no_flaws_found: bool
    flaws: List[Flaw]
    raw_response: str
    iteration: int
    counterexamples: List[str] = field(default_factory=list)
```

### Flaw

```python
@dataclass
class Flaw:
    type: str  # counterexample, logical_gap, missing_case, etc.
    severity: str  # critical, major, minor
    description: str
    counterexample: Optional[str]
    location: str
```

### Solution

```python
@dataclass
class Solution:
    content: str
    iteration: int
    timestamp: str
    reward: float
```

## Parsing Attack Responses

```python
def _parse_attack_response(self, response: str) -> Dict[str, Any]:
    """Parse critic response into structured format."""

    result = {
        'verdict': 'UNKNOWN',
        'counterexamples': [],
        'critical_flaws': [],
        'major_issues': [],
        'minor_issues': [],
        'total_penalty': 0
    }

    # Check for validation pass
    if "ADVERSARIAL_VALIDATION_PASSED" in response:
        result['verdict'] = 'ROBUST'
        return result

    # Parse verdict
    verdict_match = re.search(r'ADVERSARIAL_VERDICT:\s*(\w+)', response)
    if verdict_match:
        result['verdict'] = verdict_match.group(1).upper()

    # Parse counterexamples
    ce_pattern = r'COUNTEREXAMPLE_\d+:\s*(.+?)(?=COUNTEREXAMPLE_|\n###|$)'
    for match in re.finditer(ce_pattern, response, re.DOTALL):
        result['counterexamples'].append(match.group(1).strip())

    # Parse flaws
    flaw_pattern = r'FLAW_\d+:\s*(.+?)(?=FLAW_|\n###|$)'
    for match in re.finditer(flaw_pattern, response, re.DOTALL):
        result['critical_flaws'].append(match.group(1).strip())

    # Calculate penalty
    result['total_penalty'] = (
        len(result['counterexamples']) * -10 +
        len(result['critical_flaws']) * -10 +
        len(result['major_issues']) * -5 +
        len(result['minor_issues']) * -2
    )

    return result
```

## Integration Points

### With agent_gpt_oss.py

The RLAC mode is integrated via the `rlac_agent()` function:

```python
def rlac_agent(problem_statement, log_file, memory_file, args):
    """Run RLAC adversarial refinement loop."""

    # Create enhanced session
    critic = AdversarialCritic(
        reasoning_effort=args.verification_reasoning,
        verbose=True,
        log_file=log_file
    )
    session = critic.create_enhanced_session()

    # Main loop
    for round_num in range(args.rlac_max_rounds):
        # Generate/revise solution
        if round_num == 0:
            solution = generate_initial_solution(problem_statement, args)
        else:
            solution = revise_solution(solution, attack_result, args)

        # Validate solution
        is_valid, validation_result = session.validate_solution(solution)
        if not is_valid:
            # Handle invalid solution
            continue

        # Attack solution
        attack_result = critic.attack_solution(
            problem_statement, solution, round_num, args.rlac_max_rounds
        )

        # Check termination
        if attack_result['verdict'] == 'ROBUST':
            consecutive_robust += 1
            if consecutive_robust >= args.rlac_robust_threshold:
                return {'success': True, 'solution': solution}
```

### API Request Integration

```python
def attack_solution(self, problem_statement, solution, round_num, max_rounds,
                   api_request_func=None, api_key=None):
    """Attack with API integration."""

    # Get progressive reasoning effort
    progressive_reasoning = self._get_progressive_reasoning_effort(
        round_num, max_rounds
    )

    # Build payload
    from agent_gpt_oss import build_request_payload, send_api_request

    payload = build_request_payload(
        system_prompt=adversarial_critic_system_prompt,
        question_prompt=attack_prompt,
        reasoning_effort=progressive_reasoning
    )

    # Send request
    response = send_api_request(payload, api_key)

    return self._parse_attack_response(response)
```

## Performance Considerations

### Progressive Reasoning Cost Savings

Without progressive reasoning (all HIGH):
- 12 rounds × HIGH reasoning = 12× cost

With progressive reasoning (LOW → MEDIUM → HIGH):
- 3 rounds LOW + 4 rounds MEDIUM + 5 rounds HIGH ≈ 7× cost equivalent
- **40-50% cost savings** while maintaining quality

### Asymmetric Efficiency

```python
# Generator: LOW reasoning (fast, efficient)
# Critic: Progressive reasoning (starts cheap, scales up)

# Cost comparison:
# - LOW reasoning: ~$0.05 per call
# - MEDIUM reasoning: ~$0.20 per call
# - HIGH reasoning: ~$1.00 per call

# 12-round RLAC with progression:
# Generator: 12 × $0.05 = $0.60
# Critic: 3×$0.05 + 4×$0.20 + 5×$1.00 = $6.05
# Total: ~$6.65 per problem

# vs Symmetric HIGH/HIGH:
# Generator: 12 × $1.00 = $12.00
# Critic: 12 × $1.00 = $12.00
# Total: ~$24.00 per problem
```

## Known Limitations

### Paper vs Implementation Differences

| Aspect | Paper's RLAC | This Implementation |
|--------|-------------|---------------------|
| Type | Training algorithm | Inference-time |
| Gradient Updates | Yes (DPO) | No |
| Critic Learning | Updated via RL | Static/frozen |
| Generator Learning | Fine-tuned | Prompted only |

### Current Limitations

1. **No Training**: Models don't improve over time
2. **Static Critic**: Relies on prompt quality, not learned behavior
3. **Reward Unused**: Cumulative reward tracked but not used for updates
4. **Parsing Fragility**: Depends on LLM following output format

## Future Improvements

1. **Critic Training Loop**: Collect successful/failed criticisms for fine-tuning
2. **Adaptive Thresholds**: Adjust based on problem difficulty
3. **Multi-Agent Critic**: Ensemble of critics for higher confidence
4. **Transfer Learning**: Use attack history across problems
5. **Dynamic Reasoning**: Scale reasoning based on attack success rate

## References

- Original Paper: Wu et al., "RLAC: Reinforcement Learning with Adversarial Critic" (arXiv:2511.01758v1)
- Usage Guide: See `RLAC_INTRODUCTION.md`

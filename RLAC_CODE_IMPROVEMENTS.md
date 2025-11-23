# Specific Code Improvements for RLAC Implementation

## Fix #1: Update Class Docstring (CRITICAL - 5 min)

**File:** `code/agent_rlac.py` lines 1-8

**BEFORE:**
```python
"""
Agentic RLAC (Reinforcement Learning with Adversarial Critics) Agent

This implements RLAC at inference time using adversarial agent interactions.
Unlike traditional verification, the critic actively tries to BREAK solutions.

Key Innovation: Adversarial feedback loop creates reinforcement signals without training.
"""
```

**AFTER:**
```python
"""
Agentic RLAC (Reinforcement Learning with Adversarial Critics) Agent
Inference-Time Implementation

IMPORTANT: This implements RLAC PRINCIPLES at INFERENCE TIME, not the training
algorithm described in the paper. Key differences:

PAPER'S RLAC (Training-Time):
- Uses RL with DPO to jointly train both generator and critic
- Critic learns to identify genuine failure modes via gradient updates
- Generator learns robust outputs via policy optimization
- Both models improve together during training

THIS IMPLEMENTATION (Inference-Time):
- Does NOT train or update either model via gradients
- Uses iterative prompting with adversarial feedback (in-context learning)
- Critic is static/frozen (from base LLM, not fine-tuned)
- Generator is prompted to improve based on criticism
- Improves solution through multiple rounds of criticism without training

CORE INSIGHT (Preserved):
Adversarial feedback loop creates reinforcement signals and prevents reward
hacking, even without explicit RL training.

NOVEL EXTENSIONS (Not in Paper):
- Answer Reconsideration: Distinguishes proof flaws from answer flaws
- Attack Intensity Curriculum: Progressive difficulty escalation
- Stuck Pattern Detection: Multi-round consistency checking
- Strategy Shift: Request different approach when stuck

Use case: Inference-time solution refinement without training.
"""
```

**Why:** Prevents confusion about whether this is training-time or inference-time

---

## Fix #2: Improve Critic Prompt Format (MEDIUM PRIORITY - 15 min)

**File:** `code/agent_rlac.py` lines 289-363

**BEFORE:**
```python
def adversarial_attack(self, problem: str, solution: Solution,
                      attack_intensity: str = "moderate") -> Criticism:
    """
    Perform adversarial attack on the solution.
    """
    
    intensity_instructions = self._get_intensity_instructions(attack_intensity)

    prompt = f"""You are an adversarial mathematical critic. Your goal is to BREAK this solution.

PROBLEM:
{problem}

PROPOSED SOLUTION (Iteration {solution.iteration}):
{solution.content}

YOUR MISSION: Find ANY flaw, no matter how subtle...

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
"""
```

**AFTER:**
```python
def adversarial_attack(self, problem: str, solution: Solution,
                      attack_intensity: str = "moderate") -> Criticism:
    """
    Perform adversarial attack on the solution.
    
    Note: Differs from paper's RLAC which samples ONE specific test case.
    This samples a natural language response and parses multiple flaws from it.
    """
    
    intensity_instructions = self._get_intensity_instructions(attack_intensity)

    prompt = f"""You are an adversarial mathematical critic. Your task is to identify
THE MOST CRITICAL FLAW in this solution, if one exists.

{intensity_instructions}

PROBLEM:
{problem}

SOLUTION (Iteration {solution.iteration}):
{solution.content}

===== ANALYSIS =====

Examine this solution for:
1. Counterexamples that break the main claim
2. Logical gaps in the reasoning chain
3. Missing edge cases or special cases
4. Unjustified assumptions
5. Internal contradictions or inconsistencies

===== OUTPUT FORMAT =====

Output EXACTLY ONE flaw in this format:

FLAW_TYPE: [counterexample|logical_gap|missing_case|assumption|edge_case|contradiction]
SEVERITY: [critical|major|minor]
DESCRIPTION: Brief, clear explanation of what is wrong
COUNTEREXAMPLE: Specific example or case (if applicable)
LOCATION: Exactly where in the solution this occurs

===== OR IF NO FLAWS =====

If you have thoroughly analyzed the solution and found no flaws, output:
VALIDATION_PASSED

===== INSTRUCTIONS =====

- DO NOT hedge with "might be", "could be", or "possibly"
- Find ONE clear, verifiable flaw OR confirm the solution is sound
- For counterexamples: provide specific values and show why they fail
- For logical gaps: identify exactly which step lacks justification
- Attack aggressively - your job is to break this solution
"""
```

**Key Changes:**
- ONE flaw per call (aligns with paper)
- Clearer structure with sections
- More specific format (no FLAW_START/FLAW_END tags)
- Emphasis on finding THE MOST CRITICAL (not listing all)

---

## Fix #3: Add Critic Effectiveness Tracking (MEDIUM PRIORITY - 20 min)

**File:** `code/agent_rlac.py` (add to RLACAgent class)

**ADD AFTER __init__:**
```python
class RLACAgent:
    def __init__(self, generator_llm, critic_llm,
                 max_iterations=10,
                 generator_reasoning="high",
                 critic_reasoning="high"):
        self.generator = GeneratorAgent(generator_llm, generator_reasoning)
        self.critic = AdversarialCriticAgent(critic_llm, critic_reasoning)
        self.max_iterations = max_iterations
        
        # NEW: Track critic effectiveness
        self.critic_metrics = {
            'total_flaws_proposed': 0,
            'flaws_by_type': defaultdict(int),
            'flaws_by_severity': defaultdict(int),
            'rounds_with_flaws': 0,
            'rounds_without_flaws': 0,
        }
```

**ADD IN SOLVE METHOD (after line 527, after criticism object created):**
```python
        # Track critic metrics
        if criticism.no_flaws_found:
            self.critic_metrics['rounds_without_flaws'] += 1
        else:
            self.critic_metrics['rounds_with_flaws'] += 1
            self.critic_metrics['total_flaws_proposed'] += len(criticism.flaws)
            for flaw in criticism.flaws:
                self.critic_metrics['flaws_by_type'][flaw.type] += 1
                self.critic_metrics['flaws_by_severity'][flaw.severity] += 1
```

**ADD HELPER METHOD:**
```python
    def get_critic_detection_rate(self, window: int = 3) -> float:
        """
        Estimate critic detection rate from recent rounds.
        Higher is better (finding more flaws) but should not be 100%
        (generator still improving).
        
        Paper shows effective critics maintain 39-60% detection rate.
        """
        total_rounds = self.critic_metrics['rounds_with_flaws'] + \
                      self.critic_metrics['rounds_without_flaws']
        
        if total_rounds == 0:
            return 0.0
        
        return self.critic_metrics['rounds_with_flaws'] / total_rounds
```

**ADD TO RESULT DICT (before returning):**
```python
        result = {
            'success': True/False,
            'solution': solution.to_dict(),
            'iterations': iteration,
            'total_reward': cumulative_reward,
            'criticism_history': [...],
            'critic_metrics': self.critic_metrics,  # NEW
        }
```

---

## Fix #4: Better Answer Reconsideration (MEDIUM PRIORITY - 15 min)

**File:** `code/agent_rlac.py` lines 134-167

**BEFORE:**
```python
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
```

**AFTER (simpler, more focused):**
```python
if self.answer_reconsideration_requested:
    evidence_list = "\n".join([
        f"  - {ce}" for ce in self.accumulated_counterexamples[-5:]
    ])
    
    strategy_instruction = f"""
### CRITICAL: Your ANSWER May Be Wrong

Evidence of counterexamples appearing repeatedly:
{evidence_list}

BEFORE revising the proof, answer:
1. Are these counterexamples mathematically valid? (Verify by hand)
2. If YES, what must the CORRECT ANSWER include based on this evidence?
3. Is your current answer compatible with item #2?

If your answer contradicts the valid counterexamples, you MUST change it.
State the revised answer, then provide the corrected proof.
    """
```

---

## Fix #5: Add Validation Framework Skeleton (LOWER PRIORITY - 30 min)

**File:** `code/agent_rlac.py` (add new class)

**ADD (for future use):**
```python
class Validator:
    """
    External validator for RLAC.
    
    Implements paper's Appendix B validator designs.
    To be implemented for specific domains.
    """
    
    def verify_rubric(self, rubric_type: str, rubric_content: str,
                     solution: str, problem: str) -> bool:
        """
        Verify whether solution satisfies the proposed rubric.
        
        Args:
            rubric_type: Type of rubric (e.g., 'counterexample', 'test_case')
            rubric_content: The specific rubric/test case
            solution: The proposed solution
            problem: Original problem statement
            
        Returns:
            True if solution satisfies rubric, False otherwise
        """
        raise NotImplementedError("Implement for your domain")


class FactualValidator(Validator):
    """Validator for factual text generation (Paper Appendix B.1)"""
    
    def verify_rubric(self, rubric_type: str, rubric_content: str,
                     solution: str, problem: str) -> bool:
        """
        Verify factual claim appears in solution and is correct.
        
        Two-stage validation:
        1. Textual entailment: claim appears in the specified location
        2. Knowledge base check: claim is correct per Wikipedia/KB
        """
        # TODO: Implement with FactScore or similar
        pass


class CodeValidator(Validator):
    """Validator for code generation (Paper Appendix B.2)"""
    
    def verify_rubric(self, rubric_type: str, rubric_content: str,
                     solution: str, problem: str) -> bool:
        """
        Verify code passes test case.
        
        Process:
        1. Run test_case on reference solution → expected output
        2. Run test_case on generated code → actual output
        3. Compare outputs
        """
        # TODO: Implement with code execution
        pass
```

---

## Fix #6: Add Documentation Comment to Algorithm (LOW PRIORITY - 10 min)

**File:** `code/agent_rlac.py` (add above `def solve`)

**ADD:**
```python
def solve(self, problem: str, log_file: Optional[str] = None):
    """
    Solve problem using adversarial critic reinforcement learning.
    
    Algorithm (Inference-Time Variant):
    
    1. GENERATION: Generate initial solution
    2. CRITICISM: Adversarial critic proposes flaw
    3. FEEDBACK: Check if flaw passes validation
    4. LEARNING: Update solution based on feedback (via prompting)
    5. STUCK DETECTION: Identify patterns (same flaws, counterexamples)
    6. STRATEGY ADJUSTMENT: Request strategy shift or answer reconsideration
    7. CONVERGENCE: Stop if validation passes OR only minor flaws remain
    
    Key Differences from Paper:
    - No gradient updates (inference-time only)
    - No explicit critic training
    - Critic is frozen, generator is prompted
    - Effectiveness through iterative refinement, not learned robustness
    
    Returns:
        dict with solution, success status, iterations, reward, and metrics
    """
```

---

## Priority Implementation Order

| Priority | Fix | Time | Impact |
|----------|-----|------|--------|
| HIGH | Fix #1: Update docstring | 5 min | Prevents confusion |
| HIGH | Fix #2: Improve prompt | 15 min | Better alignment with paper |
| MEDIUM | Fix #3: Track metrics | 20 min | Measure effectiveness |
| MEDIUM | Fix #4: Simpler reconsideration | 15 min | Clearer prompting |
| LOW | Fix #5: Validator skeleton | 30 min | Future extensibility |
| LOW | Fix #6: Algorithm docs | 10 min | Code clarity |

**Total Time: ~95 minutes for all fixes**
**Recommended Start: Fix #1, #2, #3 (50 minutes, high impact)**


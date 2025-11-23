# RLAC Paper vs Implementation: Comprehensive Gap Analysis

## SECTION 1: CORE RLAC METHODOLOGY FROM PAPER

### 1.1 Mathematical Foundation

**Paper's Min-Max Objective (Eq. 4):**
```
π^g = arg max_π min_πc E_{s∼S} E_{a∼π(·|s)} E_{c∼πc(·|s,a)} [R(s, a, c)]
```

**Key Insight:** The problem reformulates rubric satisfaction as a min-max game:
- GENERATOR maximizes: probability of producing outputs that satisfy all rubrics
- CRITIC minimizes: by proposing the worst-case rubric (failure mode) for current generator
- EXTERNAL VALIDATOR: provides ground truth R(s,a,c) ∈ {0,1}

**Why this works:** Searches over C(s) (unbounded criteria) → searches over critic proposals (one per generation)

---

### 1.2 Algorithm 1: RLAC Training Loop

**Paper's Algorithm (Section 3.2 & Appendix):**

```
for each iteration do
  ## POLICY EVALUATION FOR GENERATOR
  for each instruction s:
    Generate K generations a₁, ..., aₖ ∼ π^g(·|s)
    Sample ONE criterion from critic: cᵢ ∼ π^c(·|s, aᵢ)
    Construct dataset: D^g_s = {(s, aᵢ, R(s, aᵢ, cᵢ))}

  ## POLICY EVALUATION FOR CRITIC (Optional)
  for each instruction s, output a:
    Generate N criteria: c₁, ..., cₙ ∼ π^c(·|s, a)
    Construct dataset: D^c_(s,a) = {(s, a, R(s, a, cⱼ))}

  ## POLICY IMPROVEMENT FOR GENERATOR
  L(π^g; π^g_ref) = DPO loss (Eq. 5) on binary signals:
    - R(s, aᵢ, cᵢ) = 1 → positive (a⁺)
    - R(s, aᵢ, cᵢ) = 0 → negative (a⁻)

  ## POLICY IMPROVEMENT FOR CRITIC (Optional)
  L(π^c; π^c_ref) = DPO loss (Eq. 6) on binary signals:
    - Invalid/satisfied criteria → negative (c⁻)
    - Valid, unsatisfied criteria → positive (c⁺)
```

**Critical Points:**
1. K generations, but only ONE criterion per generation (not N)
2. Critic evaluation is OPTIONAL in paper
3. DPO is chosen for "simplicity and stability"
4. Binary rewards ONLY - no scaling needed

---

### 1.3 Three Core Components

#### GENERATOR (π^g)
- **Role:** Produce output a for instruction s
- **Training:** Maximize probability of outputs satisfying critic's proposed rubrics
- **Feedback:** Binary reward (did the proposed criterion pass?)
- **Update:** DPO with K samples per instruction

#### CRITIC (π^c)
- **Role:** Propose ONE rubric c that generator likely violates
- **Key Property:** LEARNED and ADAPTIVE - evolves with generator
- **Training:** Learn to identify genuine failure modes (not obvious/already-fixed ones)
- **Update:** DPO on N criteria samples (optional in paper)

#### VALIDATOR
- **Role:** External truth - verifies if output satisfies proposed rubric
- **Implementation varies:** 
  - Factual: FactScore (Wikipedia verification)
  - Code: Test execution (generated reference solutions)
- **Constraint:** Must be reliable (paper shows noisy validation hurts both methods)

---

### 1.4 Why Attacks Are "Effective" (Paper's Definition)

From paper's ablations and discussions:

1. **Dynamic vs Static:** Adversarial critic (learns from generator) beats static critic
   - Static critic's detection accuracy drops from 42.3% → 33.9% (generator exploits patterns)
   - Adversarial critic maintains 39%+ detection rate

2. **Reliable Validation Required:** Table 2 shows noisy validator destabilizes training

3. **On-Policy Learning:** Critics propose rubrics based on CURRENT generator output
   - This is prompt-specific and adaptive
   - Prevents reward hacking (unlike fixed reward models)

4. **Progressive Difficulty Not Explicitly Formalized:**
   - Paper doesn't mention attack intensity progression
   - Implementation adds this as curriculum learning

---

## SECTION 2: ACTUAL IMPLEMENTATION IN agent_rlac.py

### 2.1 What's Implemented Correctly

**Positive aspects:**
1. Three-component architecture (Generator, Critic, Validator) ✓
2. Binary reward signals ✓
3. Adversarial loop structure ✓
4. DPO-style updates (conceptually) ✓
5. Stuck pattern detection (NEW - not in paper)
6. Answer reconsideration mechanism (NEW - not in paper)

### 2.2 Critical Differences from Paper

#### DIFFERENCE 1: Training Approach

**Paper:** 
- Uses RL training with DPO objectives
- Gradient-based policy optimization
- Shared reference policies (π^g_ref, π^c_ref)

**Implementation:**
- NO GRADIENT UPDATES AT ALL
- Generates solutions, gets feedback, moves to next iteration
- No actual learning - just iterative generation with feedback
- This is "agentic RLAC" at INFERENCE TIME (as stated in docstring)

**IMPACT:** This is the fundamental issue. The paper's power comes from joint training via RL. The implementation is using RLAC as an inference-time adversarial criticism pattern, not as a training algorithm.

---

#### DIFFERENCE 2: Critic Sampling Strategy

**Paper Algorithm 1:**
```
Sample a criterion from the adversarial critic for each generation
Sample ONE criterion per generation (K generations = K criteria checks)
```

**Implementation (lines 521-525):**
```python
criticism = self.critic.adversarial_attack(
    problem=problem,
    solution=solution,
    attack_intensity=attack_intensity
)
```

- Calls adversarial_attack() which samples ONE response from critic
- Parses ALL flaws found in that single response
- No explicit sampling of N criteria per generation

**Key Issue:** The paper's critic is trained to propose specific test cases; the implementation's critic returns a long natural language response with many flaws parsed out.

---

#### DIFFERENCE 3: Reward Structure

**Paper:**
- Binary: R(s,a,c) ∈ {0,1}
- DPO creates preference signal from binary rewards
- Both generator and critic updated equally

**Implementation (lines 559-580):**
```python
severity_penalties = {
    'critical': -10.0,
    'major': -5.0,
    'minor': -2.0
}
cumulative_reward += iteration_penalty
```

- Weighted penalties based on flaw severity
- Cumulative reward tracking (not used for updates)
- Reward is informational only (no policy gradient)

---

#### DIFFERENCE 4: Attack Intensity Curriculum

**Paper:** No explicit attack intensity progression mentioned

**Implementation (lines 643-650):**
```python
def _get_attack_intensity(self, iteration: int) -> str:
    if iteration <= 2:
        return "basic"
    elif iteration <= 5:
        return "moderate"
    else:
        return "advanced"
```

- Adds curriculum learning (basic → moderate → advanced)
- Moderate: "dig deeper, edge cases, unstated assumptions"
- Advanced: "subtle logical gaps, boundary cases, research-level rigor"

**GOOD addition not in paper**, but creates different failure mode detection over time.

---

#### DIFFERENCE 5: Answer Reconsideration (NEW MECHANISM)

**Paper:** Critic finds flaws via adversarial attack. Generator improves proof.

**Implementation (lines 226-241, 590-601):**
```python
def request_answer_reconsideration(self, counterexamples: List[str]):
    """Signal that the generator's ANSWER may be wrong (not just proof)"""
    self.answer_reconsideration_requested = True
    self.accumulated_counterexamples.extend(counterexamples)
```

**Trigger:** When stuck pattern detected WITH counterexamples:
```python
if stuck_info['has_counterexamples']:
    print("⚠ STUCK WITH VALID COUNTEREXAMPLES - Requesting answer reconsideration")
    self.generator.request_answer_reconsideration(stuck_info['counterexamples'])
```

**NOT IN PAPER** - This is a domain-specific extension for math problems where the FINAL ANSWER (not just the proof) might be wrong.

---

## SECTION 3: MISSING MECHANISMS FROM PAPER

### 3.1 CRITICAL MISSING: Joint Training with Gradient Updates

**What Paper Does:**
- Fine-tune both π^g and π^c jointly using DPO
- Critic learns to identify actual failure modes (not obvious ones)
- Generator learns robust solutions (not just pattern matching)

**What Implementation Does:**
- Generates solutions with adversarial feedback
- Uses feedback to guide next solution attempt (via prompting)
- NO parameter updates to either model

**Impact:** 
- Paper's effectiveness comes from TRAINING critic to be better at finding real flaws
- Implementation's effectiveness comes from clever prompting and self-reflection
- These are fundamentally different approaches

---

### 3.2 MISSING: Structured Critic Proposal Format

**Paper's Critic Prompt (Appendix A.2):**

For code generation:
```
Output exactly ONE failing test case inside <testcase> tags:
Option A (CALL format): <testcase> CALL: func_name(arg1, arg2) </testcase>
Option B (STDIN format): <testcase> STDIN: <raw input> </testcase>
```

For factual text:
```
Return answer in **exactly three lines**:
reason: < explaining what is wrong >
sentence: N
error_fact: < brief clause (max 8 words) >
```

**Implementation's Critic (lines 300-355):**
```python
# Freeform prompt asking for FLAW_START/FLAW_END blocks with:
# Type: [counterexample|logical_gap|missing_case|assumption|edge_case|contradiction]
# Severity: [critical|major|minor]
# Description: ...
# Counterexample: ...
# Location: ...
```

**Difference:**
- Paper forces critic to output ONE structured test case
- Implementation asks for multiple flaws in unstructured format
- Parsing is more fragile in implementation

---

### 3.3 MISSING: Optional Critic Training

**Paper Algorithm 1 Line 8:** "Optional" - you can train critic separately

**Implementation:**
- Critic is never trained
- Always uses same pre-trained critic (or frozen critic from LLM)
- No mechanism to update critic's parameters

---

### 3.4 MISSING: Reference Policy Management

**Paper:**
```
Initialize: π^g, π^c, π^g_ref, π^c_ref
DPO updates generator relative to π^g_ref (which tracks moving average)
DPO updates critic relative to π^c_ref
```

**Implementation:**
- No reference policies
- No mechanism to track which responses were "good" vs "bad"
- Critic prompts are static (defined in class constructor)

---

## SECTION 4: IMPLEMENTATION-SPECIFIC ADDITIONS

### 4.1 Stuck Pattern Detection (NEW)

**Lines 656-717: `_analyze_stuck_pattern()`**

Detects when:
1. Same flaw types appear in multiple rounds
2. Counterexamples appear in 2+ of last 3 rounds

**Logic:**
```python
# Check intersection of flaw types across rounds
intersection = set.intersection(*recent_flaw_types)
if len(intersection) > 0:
    result['is_stuck'] = True

# If counterexamples present in majority rounds → answer may be wrong
if rounds_with_counterexamples >= (window // 2 + 1):
    result['has_counterexamples'] = True
```

**NOT IN PAPER** - Domain-specific optimization for mathematical problems

---

### 4.2 Strategy Shift vs Answer Reconsideration (NEW)

**Two-level stuck detection:**
1. **Strategy Shift (line 600):** Generic "try different approach"
   - Triggered by stuck pattern WITHOUT counterexamples

2. **Answer Reconsideration (line 594):** "Your ANSWER may be wrong"
   - Triggered by stuck pattern WITH counterexamples
   - Accumulates evidence of what's possible/impossible

**This is clever** but not formalized in paper.

---

### 4.3 Early Success Criteria (lines 604-621)

```python
# Accept if only minor flaws after 5+ iterations
if (all(f.severity == 'minor' for f in criticism.flaws) and
    iteration >= 5):
    print("Accepting solution as good enough")
    return {'success': True, 'status': 'accepted_with_minor_flaws'}
```

**NOT IN PAPER** - Paper focuses on zero-error solutions or training convergence

---

## SECTION 5: GAP ANALYSIS SUMMARY TABLE

| Aspect | Paper | Implementation | Gap | Severity |
|--------|-------|-----------------|-----|----------|
| **Training** | Joint RL with DPO | Inference-only | Fundamental difference | CRITICAL |
| **Critic Updates** | Trained via DPO | Static/frozen | No learning | CRITICAL |
| **Reward Signal** | Binary only | Weighted by severity | Implementation-specific | MEDIUM |
| **Critic Output** | 1 structured test case | Multiple flaw descriptions | Different parsing | MEDIUM |
| **Attack Curriculum** | Not mentioned | basic→moderate→advanced | Addition | LOW |
| **Reference Policies** | π^g_ref, π^c_ref | None | Simplified | MEDIUM |
| **Stuck Detection** | Not formalized | Implemented with logic | Addition | LOW |
| **Answer Reconsideration** | Implicit in criticism | Explicit mechanism | Enhancement | LOW |
| **Early Exit** | Train to convergence | Accept minor flaws @iter 5 | Different success criteria | MEDIUM |

---

## SECTION 6: SPECIFIC RECOMMENDATIONS

### RECOMMENDATION 1: CLARIFY THE USE CASE

**Current Status:** Docstring says "Agentic RLAC at inference time"

**Issue:** Paper's RLAC is a TRAINING algorithm; this is an INFERENCE-TIME algorithm

**Action:**
```python
"""
Agentic RLAC Agent - Inference-Time Adversarial Critic Loop

NOTE: This implements RLAC principles at INFERENCE TIME using adversarial
agent interactions. Unlike the paper's RLAC (which trains generator + critic
jointly via RL), this version:

1. Does NOT train/update the generator model
2. Does NOT train/update the critic model  
3. Uses iterative prompting with adversarial feedback (in-context learning)
4. Adds practical mechanisms (answer reconsideration, stuck detection)
   not formalized in the paper

The core insight from RLAC is preserved: adversarial feedback loop creates
reinforcement signals without explicit RL training.
"""
```

---

### RECOMMENDATION 2: ALIGN CRITIC PROPOSAL WITH PAPER

**Current (lines 300-355):**
```
Freeform prompt → multiple flaws parsed from response
```

**Better (aligns with paper Appendix A.2):**

For mathematical problems:
```python
CRITIC_PROMPT_MATH = """
You are an adversarial mathematical critic. Find THE MOST CRITICAL FLAW
in this solution.

Output EXACTLY ONE flaw in this format:

FLAW_TYPE: [counterexample|logical_gap|missing_case|assumption|edge_case]
SEVERITY: [critical|major|minor]
DESCRIPTION: Brief explanation of the flaw
COUNTEREXAMPLE: Specific example that breaks the claim
LOCATION: Where in solution this occurs

If the solution is correct, output:
RESULT: SOLUTION_PASSED
"""
```

**Benefit:** 
- One flaw per critic call (matching paper)
- Clearer parsing
- Critic can't "hedge bets" with multiple flaws

---

### RECOMMENDATION 3: IMPLEMENT SIMPLE CRITIC TRAINING LOOP

**Current:** Critic never updates

**Proposed Addition:**
```python
class RLACAgent:
    def solve_with_critic_training(self, problem: str, 
                                   train_iterations: int = 3):
        """
        Extended RLAC with critic fine-tuning (matches paper better).
        
        After each generate-criticize cycle, collect examples of:
        - Successful criticisms (critic found real flaw → verified as real)
        - Failed criticisms (critic proposed flaw → not actually a flaw)
        
        Use these to fine-tune critic to improve detection accuracy.
        """
        critic_training_data = []
        
        for main_iteration in range(1, self.max_iterations + 1):
            # Standard RLAC loop
            solution = self.generate_or_revise(...)
            criticism = self.critic.adversarial_attack(...)
            
            # Collect examples for critic training
            if criticism.no_flaws_found:
                # This is a "missed opportunity" for the critic
                # (if we had more sophisticated validation)
                pass
            else:
                # Critic correctly identified flaws
                for flaw in criticism.flaws:
                    critic_training_data.append({
                        'problem': problem,
                        'solution': solution.content,
                        'flaw_type': flaw.type,
                        'description': flaw.description,
                        'was_correct': True  # validator confirmed it
                    })
            
            # After N main iterations, fine-tune critic
            if main_iteration % 3 == 0 and critic_training_data:
                self._train_critic_on_batch(critic_training_data[-20:])
```

---

### RECOMMENDATION 4: TRACK REWARDS PROPERLY FOR LEARNING SIGNALS

**Current (lines 559-580):**
```python
iteration_penalty = sum(severity_penalties.get(flaw.severity, -5.0)
                       for flaw in criticism.flaws)
cumulative_reward += iteration_penalty
# Reward is tracked but never used for anything
```

**Better:**
```python
@dataclass
class GenerationRecord:
    solution: Solution
    criticism: Criticism
    reward: float
    iteration: int
    is_accepted: bool

class RLACAgent:
    def __init__(self, ...):
        self.generation_history: List[GenerationRecord] = []
    
    def solve(self, problem: str):
        # ... existing code ...
        
        for iteration in range(1, self.max_iterations + 1):
            # ... generate and criticize ...
            
            record = GenerationRecord(
                solution=solution,
                criticism=criticism,
                reward=cumulative_reward,
                iteration=iteration,
                is_accepted=(criticism.no_flaws_found or 
                           only_minor_flaws_after_5_iters)
            )
            self.generation_history.append(record)
        
        # Return history so caller can analyze learning trajectory
        return result, self.generation_history
```

---

### RECOMMENDATION 5: IMPROVE CRITIC PROMPT FOR MATH PROBLEMS

**Current generator receives (lines 176-208):**
```
Latest flaws + history summary + strategy instruction

But doesn't explicitly reason about WHAT THE ANSWER SHOULD BE
```

**Better (especially for answer reconsideration):**

```python
def revise_solution(self, problem, previous_solution, 
                   latest_criticism, criticism_history):
    
    # NEW: Extract answer claim if possible
    answer_extraction_prompt = f"""
    Look at this solution: {previous_solution.content}
    
    What is the CLAIMED ANSWER? (e.g., "n ∈ {{0, 1}}", "minimum is 5", etc.)
    State it clearly.
    """
    
    claimed_answer = self.llm.generate(answer_extraction_prompt)
    
    if self.answer_reconsideration_requested:
        # Provide evidence that current answer is wrong
        prompt = f"""
PROBLEM: {problem}

CURRENT CLAIMED ANSWER: {claimed_answer}

COUNTEREXAMPLE EVIDENCE FROM CRITIC:
{self.accumulated_counterexamples}

QUESTION: Do these counterexamples prove your answer is WRONG?

If yes, what MUST the correct answer include based on this evidence?
(e.g., if counterexample shows k=2 works, then 2 MUST be in the answer)

THEN provide a corrected solution with the right answer.
"""
    # ... rest of revision ...
```

---

### RECOMMENDATION 6: FORMALIZE "EFFECTIVE ATTACK" METRICS

**Paper's Findings (Table 2, Figure 3, Figure 4):**
- Effective critic maintains ~40-60% detection rate as generator improves
- Static critic drops to 33%
- Adversarial critic stays stable

**Implementation should measure:**
```python
class CriticMetrics:
    def __init__(self):
        self.proposals_per_round = []
        self.valid_proposals = []  # Had to exist in solution
        self.verified_failures = []  # Were actually wrong
        self.false_positives = []  # Weren't actually wrong
    
    def calculate_detection_rate(self, window=3):
        """
        What % of critic's proposals correctly identified real flaws?
        Should be high (critic is good) but not 100% (generator still improving)
        """
        recent = self.verified_failures[-window:]
        if not recent:
            return 0.0
        return len(recent) / len(self.proposals_per_round[-window:])
    
    def is_critic_degrading(self, window=3):
        """Detect if critic's detection rate is dropping (generator exploiting patterns)"""
        rates = [self.calculate_detection_rate(window) 
                for _ in range(len(self.verified_failures) - window)]
        if len(rates) < 2:
            return False
        return rates[-1] < rates[0] * 0.8  # 20% drop = degrading
```

---

### RECOMMENDATION 7: IMPLEMENT PAPER'S VALIDATION PROCESS

**Paper Appendix B details:**

For factual text:
1. Check textual entailment (fact actually appears in sentence)
2. Query Wikipedia knowledge base
3. Return binary result

For code:
1. Generate reference solutions from Qwen-Instruct
2. Filter to 99.7% accuracy ones
3. Run critic's test case on reference → expected output
4. Run on generated code → actual output
5. Compare

**Current Implementation:**
```python
class GPTOSSClient:
    def generate(self, prompt, reasoning_effort="high"):
        # Calls API, returns text
        # No validator - just the raw critic response
```

**Better:**
```python
class Validator:
    """External validator - domain-specific correctness checking"""
    
    def validate_factual_claim(self, claim: str, source: str) -> bool:
        """Verify claim against knowledge base"""
        # Factual: query Wikipedia, domain DB, etc.
        pass
    
    def validate_code_test_case(self, code: str, test_case: str) -> bool:
        """Run test case on code, verify output"""
        # Code: execute, compare against reference
        pass

# Use validator in critic feedback:
criticism = self.critic.adversarial_attack(problem, solution)
for flaw in criticism.flaws:
    if flaw.counterexample:
        is_valid = self.validator.verify(flaw.counterexample, solution)
        # Store validation result with flaw
        flaw.validator_confirmed = is_valid
```

---

### RECOMMENDATION 8: DOCUMENT INFERENCE-TIME vs TRAINING-TIME RLAC

**Create comparison document:**

```markdown
# Two Versions of RLAC

## Paper's RLAC (Training-Time)
- **When:** During post-training
- **What:** Fine-tunes both generator and critic jointly with RL
- **How:** Uses DPO to update policies based on validator feedback
- **Outcome:** Critic learns to identify real flaws; generator learns robust generation
- **Training Cost:** High (requires gradient updates, validator calls)
- **Inference:** Fast (just single generator forward pass)

## Agentic RLAC (Inference-Time, this implementation)
- **When:** At inference time (no training)
- **What:** Iteratively refines solution using adversarial feedback
- **How:** Prompts generator to improve based on critic's identified flaws
- **Outcome:** Better solution through self-reflection and iteration
- **Inference Cost:** High (multiple generator calls, multiple critic calls)
- **Training:** None required

## Which to use?
- **Paper's RLAC:** If you can afford training time and validator calls upfront
- **Agentic RLAC:** If you want better inference-time solutions without training
```

---

## SECTION 7: CONCRETE CODE FIXES

### FIX 1: Better Critic Prompt Structure

**File:** `/home/user/IMO25/code/agent_rlac.py` lines 300-355

Replace:
```python
prompt = f"""You are an adversarial mathematical critic. Your goal is to BREAK this solution.
...
For EACH flaw you find, provide in this EXACT format:

FLAW_START
Type: ...
Severity: ...
Description: ...
Counterexample: ...
Location: ...
FLAW_END
"""
```

With:
```python
prompt = f"""You are an adversarial mathematical critic. Your goal is to find THE MOST CRITICAL FLAW.

Analyze this solution for:
1. Counterexamples that invalidate claims
2. Logical gaps in reasoning
3. Missing cases or edge cases
4. Unjustified assumptions
5. Internal contradictions

Output EXACTLY ONE flaw in this format:

TYPE: [counterexample|logical_gap|missing_case|assumption|edge_case|contradiction]
SEVERITY: [critical|major|minor]
DESCRIPTION: Brief explanation of the flaw
COUNTEREXAMPLE: Specific example (if applicable)
LOCATION: Where in the solution

If no flaws exist after thorough analysis, output:
RESULT: PASSED_VALIDATION

Do not provide benefits of the doubt. Attack relentlessly until you find
the worst flaw or confirm correctness.
"""
```

---

### FIX 2: Track Critic Effectiveness

**Add to RLACAgent:**
```python
def __init__(self, ...):
    # ... existing ...
    self.critic_metrics = {
        'proposals': [],
        'valid_flaws': [],
        'false_positives': [],
    }

def solve(self, problem: str, log_file: Optional[str] = None):
    # ... in criticism phase ...
    
    self.critic_metrics['proposals'].append(len(criticism.flaws))
    
    # Track if flaws were addressed (perfect metric requires next iteration)
    # For now, just track detection
    if not criticism.no_flaws_found:
        self.critic_metrics['valid_flaws'].append(len(criticism.flaws))
    
    # ... existing code ...
    
    # In results:
    result['critic_metrics'] = self.critic_metrics
```

---

### FIX 3: Make Answer Reconsideration More Principled

**Current (line 134-167): too verbose**

Improve:
```python
def revise_solution(self, problem: str, previous_solution: Solution,
                   latest_criticism: Criticism,
                   criticism_history: List[Criticism]) -> Solution:
    
    strategy_instruction = ""
    
    if self.answer_reconsideration_requested:
        # Evidence-based answer challenge
        evidence = "\n".join([
            f"- {ce}" for ce in self.accumulated_counterexamples[-5:]
        ])
        
        strategy_instruction = f"""
### CRITICAL: Answer Reconsideration Required

These counterexamples appear REPEATEDLY in recent rounds:
{evidence}

Before revising the proof, answer:
1. Are these counterexamples mathematically valid? (Verify by hand)
2. If valid, what do they prove MUST be in the correct answer?
3. Is your current answer compatible with this evidence?
4. If no, state the CORRECTED answer.

DO NOT defend an answer contradicted by valid counterexamples.
        """
        self.answer_reconsideration_requested = False
    
    elif self.strategy_shift_requested:
        strategy_instruction = """
### Strategy Shift Required

Your approach has been criticized repeatedly without improvement.
Try a FUNDAMENTALLY DIFFERENT method - don't patch the existing approach.
        """
        self.strategy_shift_requested = False
    
    # ... rest unchanged ...
```

---

## SUMMARY TABLE: Recommendations Priority

| # | Recommendation | Priority | Effort | Impact |
|---|---|---|---|---|
| 1 | Clarify use case (Inference vs Training) | HIGH | LOW | Prevents confusion |
| 2 | Align critic proposal format with paper | HIGH | MEDIUM | Better reproducibility |
| 3 | Implement optional critic training | MEDIUM | HIGH | Closer to paper's intent |
| 4 | Track rewards for analysis | MEDIUM | LOW | Better debugging |
| 5 | Improve critic prompt for math | MEDIUM | MEDIUM | Better answers |
| 6 | Formalize "effective attack" metrics | LOW | MEDIUM | Research insights |
| 7 | Implement paper's validation process | MEDIUM | MEDIUM | Proper grounding |
| 8 | Document Inference vs Training RLAC | HIGH | LOW | Clarity for users |


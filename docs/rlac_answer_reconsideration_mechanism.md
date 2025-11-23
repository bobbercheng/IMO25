# RLAC Answer Reconsideration Mechanism

## Overview

This document defines the specific mechanism that must be added to RLAC to handle the "wrong answer" scenario that the current architecture cannot address.

---

## 1. DETECTION PHASE: When to Trigger Answer Reconsideration

### Detection Logic

```python
def should_trigger_answer_reconsideration(
    criticism_history: List[Criticism],
    current_solution: Solution,
    min_rounds: int = 3,
    ce_repetition_threshold: int = 2
) -> Tuple[bool, str]:
    """
    Determine if answer reconsideration should be triggered.
    
    Returns:
        (should_reconsider, reason_for_decision)
    """
    
    if len(criticism_history) < min_rounds:
        return False, "Not enough rounds to determine pattern"
    
    recent_criticism = criticism_history[-min_rounds:]
    
    # Signal 1: Same counterexample appearing repeatedly
    ce_counter = {}
    for crit in recent_criticism:
        for ce in crit.counterexamples:
            # Normalize counterexample for comparison
            normalized_ce = normalize_counterexample(ce)
            ce_counter[normalized_ce] = ce_counter.get(normalized_ce, 0) + 1
    
    repeating_ces = {ce: count for ce, count in ce_counter.items() 
                     if count >= ce_repetition_threshold}
    
    if repeating_ces:
        return True, f"Repeating counterexamples: {list(repeating_ces.keys())}"
    
    # Signal 2: Answer unchanged while verdict stays BROKEN
    verdicts = [crit.no_flaws_found for crit in recent_criticism]
    all_broken = not any(verdicts)  # All rounds = BROKEN
    
    if all_broken:
        current_answer = extract_answer(current_solution.content)
        prev_answers = [extract_answer(sol) for sol in get_previous_solutions(criticism_history)]
        
        # Check if answer hasn't changed
        answer_stable = all(ans == current_answer for ans in prev_answers[-min_rounds:])
        
        if answer_stable:
            return True, f"Answer unchanged for {min_rounds} rounds, all verdicts BROKEN"
    
    # Signal 3: Counterexample directly contradicts answer
    for crit in recent_criticism:
        for ce in crit.counterexamples:
            if directly_contradicts_answer(ce, extract_answer(current_solution)):
                return True, f"Counterexample directly contradicts answer"
    
    return False, "No reconsideration trigger detected"


def directly_contradicts_answer(counterexample: str, answer: str) -> bool:
    """
    Check if counterexample directly proves answer is wrong.
    
    Looks for patterns like:
    - "For n=2, formula gives X but actual is Y" (where X != Y)
    - "This contradicts your claim that..."
    - "You said X but the correct answer is Y"
    """
    
    ce_lower = counterexample.lower()
    
    # Pattern: "formula gives X" / "actual is Y"
    formula_pattern = r'formula gives\s+(\d+|[\w\s]+?)\s+(?:but|however)\s+(?:actual|correct|true)\s+(?:is|should be)\s+(\d+|[\w\s]+)'
    match = re.search(formula_pattern, ce_lower)
    
    if match:
        claimed = match.group(1).strip()
        actual = match.group(2).strip()
        return claimed != actual and answer.strip() in claimed
    
    # Pattern: "contradicts", "doesn't match", "is wrong"
    contradiction_keywords = ['contradicts', 'doesn\'t match', 'doesn\'t work', 'is wrong', 
                              'fails for', 'incorrect for', 'gives wrong answer for']
    
    if any(keyword in ce_lower for keyword in contradiction_keywords):
        # And the counterexample mentions a specific value
        if re.search(r'n\s*=\s*\d+|n\s*=\s*\w+', ce_lower):
            return True
    
    return False


def normalize_counterexample(ce: str) -> str:
    """
    Normalize counterexample for comparison across rounds.
    
    Removes specific details that might change wording but are same flaw:
    - "For n=2: formula gives 4, actual is 3"
    - "When n=2: my approach gives 4, but correct answer is 3"
    Both normalize to the same core flaw
    """
    
    # Extract core: "n=X, claimed=Y, actual=Z"
    pattern = r'n\s*=\s*(\d+)[^:].*?(?:gives|claims|shows)\s+(\d+|[\w]+).*?(?:actual|correct|true)\s+(?:is|=)\s+(\d+|[\w]+)'
    match = re.search(pattern, ce, re.IGNORECASE)
    
    if match:
        n, claimed, actual = match.groups()
        return f"n={n}: claimed={claimed}, actual={actual}"
    
    # If pattern doesn't match, return hash of first 50 chars
    return hashlib.md5(ce[:50].encode()).hexdigest()
```

### Integration into Main Loop

```python
# In RLACAgent.solve(), after attack phase:

if not criticism.no_flaws_found:
    # NEW: Check if answer reconsideration needed
    should_reconsider, reason = should_trigger_answer_reconsideration(
        criticism_history,
        solution,
        min_rounds=3
    )
    
    if should_reconsider:
        print(f"\n⚠⚠⚠ ANSWER RECONSIDERATION TRIGGERED ⚠⚠⚠")
        print(f"Reason: {reason}")
        print(f"The current answer may be fundamentally wrong.")
        print(f"Requesting generator to explore alternative answers...\n")
```

---

## 2. EXECUTION PHASE: Answer Reconsideration Prompt

### The Prompt Template

```python
answer_reconsideration_prompt = """
### ANSWER RECONSIDERATION MODE ###

Your previous answer has NOT IMPROVED despite multiple attempted proof revisions.
This suggests the ANSWER ITSELF is wrong, not just the proof.

**Evidence of Wrong Answer**:
{evidence_summary}

**What Happened**:
- You proposed answer: {previous_answer}
- Critic found: {counterexample_details}
- You attempted to fix the proof {attempt_count} times
- Each time, the same counterexample broke your answer
- This means the answer itself is wrong, no matter how perfect the proof

**What You Must Do Now**:

1. **ACCEPT**: Your previous answer {previous_answer} is incorrect
2. **RE-READ**: Carefully read the problem statement again
3. **SEARCH**: Look for DIFFERENT possible answers
4. **TEST**: For each candidate answer, check against:
   - The given counterexamples
   - Small test cases (n=1, n=2, n=3)
   - Edge cases
5. **PROPOSE**: A completely different answer that handles all cases

**Critical Rules**:
- Do NOT try to defend {previous_answer}
- Do NOT propose a minor variation of {previous_answer}
- Do PROPOSE a fundamentally different answer if you find one
- Do TEST your new answer before including it

**Example of What NOT to Do**:
Wrong Answer: f(n) = n²
Bad attempt: "Actually, f(n) = n² + 0" (same answer)
Bad attempt: "The proof should be: f(n) = (n²)*(n+1)/n" (tries to justify same answer)

**Example of What to DO**:
Wrong Answer: f(n) = n²
Correct new answer: f(n) = n(n+1)/2
Justification: "For n=2, this gives 2*3/2 = 3, which matches the counterexample"

**Your Response Must Include**:
1. Acknowledgment that previous answer was wrong
2. Analysis of why the counterexample proves it wrong
3. New candidate answer(s)
4. Verification that new answer handles known counterexamples
5. Complete new solution with the new answer

**IMPORTANT**: If you cannot find a valid alternative answer,
be honest and state that. Don't defend the wrong answer.
"""

def format_answer_reconsideration_prompt(
    previous_solution: Solution,
    criticism_history: List[Criticism],
    current_answer: str
) -> str:
    """Format the answer reconsideration prompt with actual evidence."""
    
    # Extract evidence
    repeating_ces = find_repeating_counterexamples(criticism_history)
    ce_details = "\n".join([
        f"- Round {crit.iteration}: {ce}"
        for crit in criticism_history[-3:]
        for ce in crit.counterexamples[:1]  # Just show first one
    ])
    
    attempt_count = len(criticism_history)
    
    return answer_reconsideration_prompt.format(
        evidence_summary=ce_details,
        previous_answer=current_answer,
        counterexample_details=repeating_ces[0] if repeating_ces else "See above",
        attempt_count=attempt_count
    )
```

### Integration into Revision Loop

```python
def revise_solution(self, problem: str, previous_solution: Solution,
                   latest_criticism: Criticism,
                   criticism_history: List[Criticism],
                   should_reconsider_answer: bool = False) -> Solution:
    """
    Revise solution, with option to reconsider the answer.
    """
    
    if should_reconsider_answer:
        current_answer = extract_answer(previous_solution.content)
        prompt = format_answer_reconsideration_prompt(
            previous_solution=previous_solution,
            criticism_history=criticism_history,
            current_answer=current_answer
        )
    else:
        # Normal revision: improve proof of same answer
        prompt = adversarial_defense_prompt.format(
            adversarial_feedback=latest_criticism.raw_response
        )
    
    response = self.llm.generate(prompt=prompt, reasoning_effort=self.reasoning_effort)
    
    return Solution(
        content=response,
        iteration=previous_solution.iteration + 1,
        timestamp=datetime.now().isoformat(),
        reward=0.0
    )
```

---

## 3. ANSWER TRACKING

### Answer Extractor

```python
def extract_answer(solution_text: str) -> Optional[str]:
    """
    Extract the mathematical answer from a solution.
    
    Strategies in order:
    1. Look for \boxed{...}
    2. Look for "answer is:" or "the answer is:"
    3. Look for final expression before conclusion
    """
    
    # Strategy 1: Boxed answer (most reliable)
    boxed_match = re.search(r'\\boxed\{(.+?)\}', solution_text)
    if boxed_match:
        return boxed_match.group(1).strip()
    
    # Strategy 2: Explicit "answer is" statement
    answer_pattern = r'(?:the\s+)?answer\s+(?:is|:)\s*(.+?)(?:\n|$)'
    match = re.search(answer_pattern, solution_text, re.IGNORECASE)
    if match:
        answer_str = match.group(1).strip()
        # Take until period or newline
        answer_str = re.split(r'[.\n]', answer_str)[0].strip()
        return answer_str
    
    # Strategy 3: "Therefore" or "Thus" before final expression
    conclusion_pattern = r'(?:therefore|thus|hence)\s*[:=]\s*(.+?)(?:\n|$)'
    match = re.search(conclusion_pattern, solution_text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    
    return None


class AnswerTracker:
    """Track answers across iterations to detect stability."""
    
    def __init__(self):
        self.answer_history = []  # List of (iteration, answer_str)
        
    def add_solution(self, iteration: int, solution_text: str) -> Optional[str]:
        """Add a solution and extract its answer."""
        answer = extract_answer(solution_text)
        if answer:
            self.answer_history.append((iteration, answer))
        return answer
    
    def get_answer_stability(self, window: int = 4) -> dict:
        """Get statistics about answer changes."""
        if len(self.answer_history) < window:
            return {
                'has_history': False,
                'changes': 0,
                'stable': True
            }
        
        recent = [ans for _, ans in self.answer_history[-window:]]
        changes = sum(1 for i in range(1, len(recent)) if recent[i] != recent[i-1])
        
        return {
            'has_history': True,
            'total_iterations': len(self.answer_history),
            'recent_window': window,
            'changes_in_window': changes,
            'stable': changes == 0,
            'first_answer': self.answer_history[0][1] if self.answer_history else None,
            'current_answer': self.answer_history[-1][1] if self.answer_history else None
        }
    
    def answers_equivalent(self, ans1: str, ans2: str) -> bool:
        """Check if two answers are mathematically equivalent."""
        # Simple check: normalized string comparison
        norm1 = re.sub(r'\s+', '', ans1.lower())
        norm2 = re.sub(r'\s+', '', ans2.lower())
        return norm1 == norm2
```

---

## 4. STATE MACHINE TRANSITIONS

### New States

```
┌──────────────────────────────────────────────────────────┐
│             RLAC State Machine with Answer Reconsideration │
└──────────────────────────────────────────────────────────┘

                    INITIAL
                       │
                       ↓
                   ATTACKING
                       │
                    ┌──┴──┐
                    ↓     ↓
              [ROBUST]  [BROKEN]
                    │     │
             [SUCCESS]    └──→ [PROOF_IMPROVEMENT]
                               │
                      ┌────────┴────────┐
                      ↓                 ↓
                  [IMPROVING]       [STUCK_PROOF]
                      │                 │
                   [ROBUST]         [ANSWER_RECONSIDERATION]
                      │                 │
                 [SUCCESS]              └────┐
                                            │
                                    ┌───────┴────────┐
                                    ↓                ↓
                              [ANSWER_CHANGED]  [NO_VALID_ANSWER]
                                    │                │
                                [ATTACKING]      [FAILURE]
                                    │
                               [ROBUST/BROKEN]


State Descriptions:
───────────────────

INITIAL:
  - Starting state
  - Solution just generated
  - Next: ATTACKING

ATTACKING:
  - Critic attacking current solution
  - Next: ROBUST or BROKEN

ROBUST:
  - Critic found no flaws
  - Verdict: PASSED ATTACK
  - Next: SUCCESS or continue

BROKEN:
  - Critic found flaws
  - Next: PROOF_IMPROVEMENT or ANSWER_RECONSIDERATION

PROOF_IMPROVEMENT:
  - Trying to improve proof of same answer
  - Using normal revision prompt
  - Next: ATTACKING

STUCK_PROOF:
  - Same flaws repeating despite proof improvements
  - Answer hasn't changed for 3+ rounds
  - Next: ANSWER_RECONSIDERATION

ANSWER_RECONSIDERATION:
  - Asking generator to find different answer
  - Using answer reconsideration prompt
  - Next: ANSWER_CHANGED or NO_VALID_ANSWER

ANSWER_CHANGED:
  - Generator proposed different answer
  - Next: ATTACKING (test new answer)

NO_VALID_ANSWER:
  - Generator couldn't find valid alternative answer
  - Next: FAILURE

SUCCESS:
  - Solution passed all attacks
  - Can terminate with success

FAILURE:
  - Max iterations reached or no valid answer found
  - Terminate with failure
```

### Transition Rules

```python
class AnswerReconsiderationStateMachine:
    """State machine for RLAC with answer reconsideration."""
    
    def __init__(self):
        self.current_state = 'INITIAL'
        self.state_history = []
        
    def transition(self, event: str, data: dict) -> str:
        """Process event and transition to new state."""
        
        transitions = {
            ('INITIAL', 'solution_generated'): 'ATTACKING',
            
            ('ATTACKING', 'no_flaws'): 'ROBUST',
            ('ATTACKING', 'flaws_found'): 'BROKEN',
            
            ('ROBUST', 'accept'): 'SUCCESS',
            ('ROBUST', 'continue'): 'ATTACKING',
            
            ('BROKEN', 'should_reconsider_answer'): 'ANSWER_RECONSIDERATION',
            ('BROKEN', 'attempt_proof_improvement'): 'PROOF_IMPROVEMENT',
            
            ('PROOF_IMPROVEMENT', 'improved'): 'ATTACKING',
            
            ('STUCK_PROOF', 'time_to_reconsider'): 'ANSWER_RECONSIDERATION',
            
            ('ANSWER_RECONSIDERATION', 'answer_changed'): 'ANSWER_CHANGED',
            ('ANSWER_RECONSIDERATION', 'no_valid_answer'): 'NO_VALID_ANSWER',
            
            ('ANSWER_CHANGED', 'revised'): 'ATTACKING',
            
            ('NO_VALID_ANSWER', 'max_attempts'): 'FAILURE',
            ('FAILURE', 'exit'): 'FAILURE',
            ('SUCCESS', 'exit'): 'SUCCESS',
        }
        
        transition_key = (self.current_state, event)
        new_state = transitions.get(transition_key)
        
        if new_state:
            self.state_history.append({
                'from': self.current_state,
                'to': new_state,
                'event': event,
                'data': data
            })
            self.current_state = new_state
            return new_state
        else:
            raise ValueError(f"Invalid transition: {transition_key}")
    
    def is_terminal(self) -> bool:
        """Check if in terminal state."""
        return self.current_state in ['SUCCESS', 'FAILURE']
```

---

## 5. COMPLETE REVISED RLACAgent.solve() Loop

```python
def solve(self, problem: str, log_file: Optional[str] = None):
    """
    Solve problem with answer reconsideration capability.
    """
    
    print("="*80)
    print("AGENTIC RLAC SOLVER WITH ANSWER RECONSIDERATION")
    print("="*80)
    
    # Initialize
    solution = None
    criticism_history = []
    answer_tracker = AnswerTracker()
    state_machine = AnswerReconsiderationStateMachine()
    cumulative_reward = 0.0
    best_solution = None
    best_reward = -float('inf')
    
    for iteration in range(1, self.max_iterations + 1):
        print(f"\n{'='*80}")
        print(f"ITERATION {iteration}/{self.max_iterations} [State: {state_machine.current_state}]")
        print(f"{'='*80}\n")
        
        # PHASE 1: GENERATION
        print("PHASE 1: Solution Generation")
        if iteration == 1:
            solution = self.generator.generate_initial_solution(problem)
            state_machine.transition('solution_generated', {})
        else:
            # NEW: Check if answer reconsideration is needed
            should_reconsider, reason = should_trigger_answer_reconsideration(
                criticism_history, solution
            )
            
            if should_reconsider:
                print(f"\n⚠⚠⚠ ANSWER RECONSIDERATION TRIGGERED ⚠⚠⚠")
                print(f"Reason: {reason}\n")
                state_machine.transition('time_to_reconsider', {'reason': reason})
            
            solution = self.generator.revise_solution(
                problem=problem,
                previous_solution=solution,
                latest_criticism=criticism_history[-1],
                criticism_history=criticism_history,
                should_reconsider_answer=should_reconsider
            )
        
        # Track answer
        current_answer = answer_tracker.add_solution(iteration, solution.content)
        print(f"✓ Solution generated (iteration {iteration})")
        print(f"  Answer: {current_answer}")
        
        # PHASE 2: ADVERSARIAL ATTACK
        print("\nPHASE 2: Adversarial Attack")
        attack_intensity = self._get_attack_intensity(iteration)
        
        criticism = self.critic.adversarial_attack(
            problem=problem,
            solution=solution,
            attack_intensity=attack_intensity
        )
        
        print(f"✓ Attack complete: {criticism.no_flaws_found}")
        
        # PHASE 3: REINFORCEMENT SIGNAL
        print("\nPHASE 3: Reinforcement Signal")
        
        if criticism.no_flaws_found:
            reward = 10.0
            cumulative_reward += reward
            solution.reward = cumulative_reward
            
            print(f"✓✓✓ SOLUTION SURVIVED ATTACK ✓✓✓")
            print(f"  Reward: +{reward}")
            
            state_machine.transition('no_flaws', {})
            state_machine.transition('accept', {})
            
            result = {
                'success': True,
                'solution': solution.to_dict(),
                'iterations': iteration,
                'total_reward': cumulative_reward,
                'criticism_history': [c.to_dict() for c in criticism_history],
                'answer_tracker': answer_tracker.answer_history
            }
            
            if log_file:
                self._save_result(result, log_file)
            
            return result
        else:
            # Flaws found
            penalty = sum(-severity_penalties.get(flaw.severity, -5.0) 
                         for flaw in criticism.flaws)
            cumulative_reward += penalty
            
            print(f"✗ Critic found {len(criticism.flaws)} flaw(s)")
            
            state_machine.transition('flaws_found', {'count': len(criticism.flaws)})
            
            # Determine next action: proof improvement or answer reconsideration
            should_reconsider, reason = should_trigger_answer_reconsideration(
                criticism_history + [criticism], solution
            )
            
            if should_reconsider:
                print(f"  → Answer reconsideration triggered: {reason}")
                state_machine.transition('should_reconsider_answer', {'reason': reason})
            else:
                print(f"  → Will attempt proof improvement")
                state_machine.transition('attempt_proof_improvement', {})
            
            criticism_history.append(criticism)
        
        # PHASE 4: CHECK TERMINATION
        print("\nPHASE 4: Termination Check")
        
        if state_machine.is_terminal():
            print(f"  → Terminal state reached: {state_machine.current_state}")
            break
        
        print(f"  → Continuing (state: {state_machine.current_state})")
    
    # MAX ITERATIONS REACHED
    print(f"\nMax iterations reached")
    state_machine.transition('max_attempts', {})
    
    result = {
        'success': False,
        'solution': best_solution.to_dict() if best_solution else None,
        'iterations': self.max_iterations,
        'final_state': state_machine.current_state,
        'answer_tracker': answer_tracker.answer_history
    }
    
    if log_file:
        self._save_result(result, log_file)
    
    return result
```

---

## 6. Summary

The answer reconsideration mechanism:

1. **Detects** when answer is the problem (repeating counterexamples, stable answer, all verdicts broken)
2. **Triggers** explicit "answer reconsideration" mode
3. **Prompts** generator to find a DIFFERENT answer (not just fix the proof)
4. **Tracks** answers across iterations to distinguish between:
   - Proof improvement (same answer, stronger proof)
   - Answer change (different answer, possibly from different insight)
5. **Manages** transitions through state machine with distinct states for each phase

This solves the fundamental architectural flaw where RLAC cannot handle "wrong answer" scenarios.


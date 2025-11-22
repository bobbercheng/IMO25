# RLAC Enhancement Analysis for IMO Problem-Solving Gap

## Executive Summary

The IMO25 system demonstrates a critical gap between **solution generation confidence** and **verification rigor**. Solutions generated with low reasoning effort (fast, intuitive) consistently fail high-reasoning verification (rigorous, checking). This research proposes specific RLAC (Reinforcement Learning with Adversarial Critics) enhancements to bridge this gap through adversarial feedback during generation, not just after-the-fact verification.

**Core Finding:** The current pipeline is sequential (generate → verify). We propose inserting an **adversarial critic** during generation that acts as a "proof saboteur" rather than a "proof checker."

---

## Problem Analysis: The Generator-Verifier Gap

### Observed Pattern (from agent_gpt_oss_2_mcts_low_bfs.log and verification)

**Iteration 1:** Solution appears complete with clear structure
- Defines key concepts (circumcenter, angle bisector)
- Provides lemmas and main proof steps
- Uses appropriate mathematical language
- **Generator confidence:** "This is a rigorous solution"
- **Verification result:** INVALID - Multiple critical errors

**Critical Errors Found:**
1. **Theorem Misapplication:** Claims angle-bisector theorem applies when points don't lie on the relevant sides
2. **Chord Confusion:** Claims CE = AE (different chords from same point)
3. **Unjustified Perpendicularity:** Asserts AP ⊥ PM without proof
4. **Missing Steps:** Claims about angles without justifying the geometric configuration
5. **Incomplete:** Proof stops before addressing the main tangency claim

### Why Does This Happen?

**With low reasoning effort:**
- Model generates plausible-sounding mathematical arguments
- Follows rhetorical structure of valid proofs
- Makes intuitive leaps that seem reasonable
- Doesn't verify each step exhaustively
- Cannot distinguish between "sounds right" and "is right"

**With high reasoning effort (verification):**
- Model tests each claim against definitions
- Identifies when theorems don't apply
- Finds counterexamples to false statements
- Detects logical gaps
- But this feedback arrives too late—after an invalid solution is already generated

### The Root Cause: Confidence Calibration Gap

The model's confidence in solution correctness is poorly calibrated:
- **Internal confidence (generation):** "This proof looks complete and follows valid reasoning patterns"
- **External confidence (verification):** "Wait, this actually has critical errors"
- **Gap:** No mechanism during generation to challenge weak assumptions

---

## RLAC Enhancement Strategy

Rather than traditional verification (cooperative grading), we propose adversarial criticism during generation that:

1. **Actively tries to break solutions** (not evaluate them)
2. **Provides specific counterexamples** to weak claims
3. **Generates during generation** (not just after)
4. **Uses progressive difficulty** to escalate challenges
5. **Tracks what generators defend/concede** to measure learning

### Key Principle: Adversarial Mindset Change

**Traditional Verification:** "Does this proof work?"
- Binary outcome: yes/no
- Feedback is often too late
- Model learns from rejection, not challenge

**Adversarial Criticism:** "How can I break this proof?"
- Generative outcome: specific flaws
- Feedback shapes generation directly
- Model learns what NOT to claim

---

## Proposed RLAC Enhancements

### 1. Critic-Assisted Solution Generation (CASG)

**Implementation:**
- After initial solution outline, insert adversarial critic Round 0
- Critic attempts basic attacks (boundary cases, definition checks)
- Generator reads criticisms and revises before full writeup
- Reduces commitment to flawed approaches early

**Specific Attack Categories for Geometry Problems:**

```
GEOMETRIC MISCONCEPTION ATTACKS:
- Point Collocation: "You claim X lies on line L. Verify that X, Y, Z are collinear."
- Theorem Application: "You apply [THEOREM]. Verify its preconditions hold."
- Circle Properties: "You claim point P has property Q. Check all instances."
- Angle Relationships: "You claim ∠ABC = ∠DEF. Justify via the circle/configuration."

DEFINITION ATTACKS:
- "You define/use the circumcenter. Does it satisfy all properties you assume?"
- "You claim perpendicularity. Prove both directions of the perpendicularity."
- "Orthocenter appears in your solution. Does it have the properties you use?"

COMPLETENESS ATTACKS:
- "How do you handle the degenerate case where X = Y?"
- "Does your argument work when the configuration is reflected?"
- "You use property P implicitly. Where is it proven?"
```

**Timing:**
- Critic runs DURING solution generation, after outline
- Not a post-hoc verification
- Interrupts the generation before investing heavily in a flawed approach

### 2. Structured Flaw Reporting with Severity & Location

**Current System:** Returns verdict (BROKEN/SUSPICIOUS/ROBUST)

**Proposed Enhancement:** Structured criticisms with:

```json
{
  "flaw": {
    "type": "theorem_misapplication|unjustified_claim|missing_case|circular_reasoning|definition_violation",
    "severity": "critical|major|minor",
    "location": "lemma_name:line_number:step_description",
    "specific_claim": "The exact statement being attacked",
    "why_wrong": "Concrete reason this claim fails",
    "counterexample_or_missing_condition": "E.g., 'Points C,E,A are not collinear, so CE ≠ AE'",
    "suggested_correction": "What the solution needs to address this",
    "confidence": 0.95
  }
}
```

**Benefit:** Generators can precisely target which parts to fix, not just "redo the whole thing"

### 3. Progressive Difficulty with Math-Specific Curriculum

**Current System:** 
- Rounds 0-2: BASIC attacks (obvious flaws)
- Rounds 3-6: MODERATE attacks (edge cases, assumptions)
- Rounds 7+: ADVANCED attacks (subtle gaps, rigor)

**Proposed Enhancement:** Geometry-specific progression

```
GEOMETRY ATTACK CURRICULUM:

Round 0-1 (Definition Check):
- Does every term used have been defined?
- Do all points exist in the configuration?
- Can you verify basic incidence (is X on line L)?

Round 2-3 (Theorem Preconditions):
- For each theorem applied: are preconditions satisfied?
- Angle-bisector theorem: Does it bisect the angle at the right vertex?
- Power of a point: Are the secants/chords actually chords/secants?
- Similarity: Do the angles/sides actually match as claimed?

Round 4-6 (Configuration Verification):
- Is the configuration non-degenerate?
- Can you construct it explicitly with coordinates?
- What if the configuration is slightly perturbed?

Round 7-8 (Logical Closure):
- Are all cases covered (collinear, intersection, parallel)?
- Is any assumption circular (proving using itself)?
- Does the final claim actually follow from the lemmas?

Round 9+ (Rigorous Reconstruction):
- Rewrite the proof formally step-by-step
- Identify any hand-waving or "clearly implies"
- Fill every logical gap explicitly
```

### 4. Counterexample Generation for Geometric Claims

**Current System:** Attacks list issues, sometimes with counterexamples

**Proposed Enhancement:** Systematic counterexample generation

For claims like "∠CEA = ∠DFA":
- Critic constructs explicit configuration where claim is false
- Provides concrete angle measurements
- Uses coordinates or specific geometric properties
- Verifies the counterexample actually violates the claim

Example format:
```
CLAIM: "Since E lies on Ω and F lies on Γ, the similarity triangle AEC ~ triangle AFD"

COUNTEREXAMPLE ATTEMPT 1:
  Let Ω have center M=(0,0), radius 1
  Let Γ have center N=(2,0), radius 2
  Then A=(1/2, √3/2), C=(-1,0)
  [Construct E and F]
  Compute actual angles:
  ∠EAC = [computation] ≠ [claimed angle]
  
VERDICT: This configuration violates the similarity claim

LOCATION OF ERROR: The angle equality assumes concurrent behavior that 
                   doesn't hold in this construction
```

### 5. Defense and Concession Tracking

**New Mechanic:** Track whether generator **defends** or **concedes** to each attack

```
ATTACK: "You claim AP ⊥ PM. Where is this justified?"

GENERATOR RESPONSE TYPE A (Defense):
"AP is perpendicular to MN (proven via circumcenter property).
 Since PM is part of MN's configuration, AP ⊥ PM follows from [specific reason]"
 → ANALYZER: Is defense valid? If yes, critic failed to break it.

GENERATOR RESPONSE TYPE B (Concession):
"You're right, I haven't proven AP ⊥ PM. Let me revise..."
 → ANALYZER: Generator learned to not make unjustified claims

GENERATOR RESPONSE TYPE C (Deflection):
"This is a minor point, the main argument still holds..."
 → ANALYZER: Red flag—generator avoiding the issue
```

**Learning Signal:** Track which types of flaws generators concede to vs. defend against
- Helps identify which attacks are actually breaking, vs. spurious

### 6. Confidence Calibration through Adversarial Feedback

**Problem:** Generators are overconfident in solutions

**Solution:** Force explicit confidence statements with adversarial feedback

```
GENERATOR: "I claim [STATEMENT] with confidence 0.95"

CRITIC: "Test this claim with [SPECIFIC COUNTEREXAMPLE/PRECONDITION CHECK]"
        
OUTCOME A: Confidence justified → "Robust" 
          (Generator correctly identified strength)

OUTCOME B: Confidence unjustified → "Broken" 
          (Confidence calibration failure—PENALIZE)
          
OUTCOME C: Partially justified → "Suspicious"
          (Some parts hold, others fail—PARTIAL PENALTY)
```

**Training Signal:** When generator overconfidently claims something that fails,
the penalty is larger (miscalibration cost).

---

## Specific Enhancements for This Problem (IMO-02)

### The Specific Failure Pattern

Verified solutions failed because:
1. **Angle-bisector misapplication:** Points E, F not on the expected sides
2. **Chords misconstrued:** Claims CE = AE without collinearity
3. **Perpendicularity unproven:** AP ⊥ PM asserted without derivation
4. **Completeness gap:** Stops after lemma, doesn't complete main proof

### Tailored Critic Prompts

**For theorem application verification:**
```
ADVERSARIAL THEOREM CHECKER:

When you apply Angle-Bisector Theorem:
1. Name the triangle explicitly (e.g., "triangle CAD")
2. Name the bisector explicitly (e.g., "line AP")
3. Identify which vertex is being bisected (e.g., "angle at A")
4. Identify the opposite side (e.g., "side CD")
5. Verify the bisector meets the opposite SIDE (not just the extended line)
6. If not, your application is INVALID

Apply this checklist to every theorem invocation.
```

**For geometric configuration verification:**
```
CONFIGURATION SKEPTIC:

Before using points E, F, B in any property:
1. Verify E is on Ω: Is E the second intersection of line AP with Ω?
2. Verify F is on Γ: Is F the second intersection of line AP with Γ?  
3. Verify B is the intersection point: B is where? (second intersection of Ω and Γ)
4. Now: Do these points have the relationship you claim?
   - Example: You claim "B, E, F concyclic"—why? Show the calculation.
```

**For perpendicularity claims:**
```
PERPENDICULARITY VERIFIER:

Every time you claim line X ⊥ line Y:
1. Prove it from first principles
2. Do NOT assume perpendicularity; derive it
3. Show the calculation (dot product = 0, or angle = 90°, etc.)
4. If you say "Since P is the circumcenter, AP ⊥ MN":
   - Circumcenter property: PA = PC = PD
   - Does this imply perpendicularity? JUSTIFY
   - (Hint: It doesn't automatically—you need the additional fact 
     that C and D are symmetric about AP)
```

---

## Multi-Stage Verification Pipeline

Rather than single binary verification, propose tiered approach:

**Stage 1 - Outline Verification (After draft outline, before full writeup):**
- Critic attacks: Is the strategic approach sound?
- Are the lemmas correctly stated?
- Does the flow make logical sense?
- Early kill of doomed approaches

**Stage 2 - Lemma Verification (Each lemma independently):**
- Critic attacks each lemma as standalone theorem
- Are preconditions stated?
- Is proof complete?
- Can you construct a counterexample if claim is false?

**Stage 3 - Integration Verification (After full writeup):**
- Do the lemmas actually connect?
- Does final statement follow?
- Are there any circular dependencies?

**Stage 4 - Robustness Verification (Final check):**
- What if one assumption is removed?
- What about boundary/degenerate cases?
- Can you rewrite it more formally?

Each stage outputs specific criticisms that feed back to the generator.

---

## Implementation Roadmap (Research Conceptual)

### Phase 1: Enhanced Critic Module
- Implement math-specific attack patterns (theorem application, configuration, definitions)
- Structured flaw reporting with location and suggested fixes
- Confidence scoring for attacks

### Phase 2: Integrated Generation-Criticism
- Insert critic calls during solution generation (not just after)
- Add "outline → critic → full writeup" workflow
- Track generator responses to attacks

### Phase 3: Confidence Calibration
- Require generators to report confidence levels
- Track which confidence statements are justified/unjustified
- Use miscalibration as training signal

### Phase 4: Curriculum Learning
- Implement geometry-specific attack progression
- Difficulty scaling based on solution type
- Track which attacks types are effective

### Phase 5: Analytics & Feedback
- Track success rates by attack type
- Identify systematic weakness patterns
- Generate attack histories for analysis

---

## Expected Outcomes

### Success Metrics

1. **Verification pass rate increases** from 0% → target 40-60%
   - Measured by: high-reasoning verification accepting solutions as correct

2. **False confidence decreases**
   - Generators stop overconfidently asserting unproven claims
   - Solutions marked as "partial" rather than claiming completeness

3. **Concession rate improves**
   - When attacked, generators fix flaws rather than defend them
   - Measured by: % of attacks leading to solution improvements

4. **Error detection early**
   - Critic catches issues before full writeup
   - Reduces wasted computation on doomed approaches

### Confidence Calibration Improvement

**Current state:**
- Generator confidence in solution: "This is rigorous and complete" (99%)
- Verification finding: "This has critical errors" (failure)
- Calibration error: Huge (100%)

**Target state:**
- Generator confidence in solution: "This looks good but I'm uncertain about the perpendicularity claim" (70%)
- Verification finding: "The perpendicularity is unjustified, fix it" (specific feedback)
- Calibration error: Small (5-10%)

---

## Theoretical Justification

### Why RLAC Helps

**Standard verification:** Binary signal (correct/incorrect) at the very end
- Generator sees only the final verdict
- Cannot calibrate confidence during generation
- Makes same mistakes repeatedly

**RLAC adversarial feedback:** Continuous signal during generation
- Generator sees specific flaws as they're identified
- Can adjust confidence and reasoning in real time
- Learns which types of claims need more rigor

**Adversarial approach advantage:**
- Doesn't just grade ("this is wrong")
- Actively attacks ("here's why it's wrong, here's a counterexample")
- Forces generator to defend assumptions (or concede)
- Creates a feedback loop that improves reasoning

### Connection to Human Mathematical Practice

Professional mathematicians use adversarial criticism:
- Seminar: "Does your theorem work in this case?" → Defense or revision
- Peer review: "You assume X. Prove it." → Defense or concession
- Self-review: "Can I break my own proof?" → Strengthening or fixing

RLAC formalizes this process for AI models.

---

## Example Scenario: IMO-02 with RLAC

### Without RLAC (Current):
1. Agent generates solution with angle-bisector argument
2. Agent runs verification
3. Verification (high reasoning) finds: "E, F not on sides—theorem misapplied"
4. Agent sees: "Invalid solution"
5. Tries again (no specific guidance on what to fix)

### With RLAC:
1. Agent generates solution outline: "Use angle-bisector theorem on triangle CAD"
2. Critic attacks: "You claim angle-bisector applies. But E is on Ω, not on line CD. Verify preconditions."
3. Agent reads criticism: "Hmm, let me check... E is the SECOND intersection with Ω, not on CD."
4. Agent revises: "I need a different approach. Not angle-bisector directly."
5. Agent regenerates solution using power-of-a-point instead
6. Critic attacks: "You claim A, P, M, N concyclic. Prove this."
7. Agent provides proof (or fails, and tries different approach)
8. ... continues until passes multiple rounds of adversarial testing
9. Solution is verified—much higher confidence

**Key difference:** Feedback shaped the generation process, not just judged the result.

---

## Risks and Mitigations

### Risk 1: Critic Makes Spurious Attacks
**Mitigation:** Track accuracy of critic's attacks
- If generator validly defends against an attack, it wasn't a real flaw
- Use this to calibrate critic confidence scores
- Focus on attacks that actually identify errors

### Risk 2: Adversarial Loop Becomes Nonproductive
**Mitigation:** 
- Set max iteration limits
- Track convergence (is each round producing improvements?)
- Implement "stuck detection" and strategy shift

### Risk 3: Computational Cost
**Mitigation:**
- Run critic at lower reasoning effort than generator during generation
- Only run full high-effort critic on final solution
- Progressive difficulty means early rounds are cheap

### Risk 4: Over-Specialization to Critic
**Mitigation:**
- Rotate critic attack styles
- Don't let generator just "placate" critic with minimal changes
- Require structural improvements, not just wording changes

---

## Summary: Key Proposals

| Enhancement | Current Gap | Proposed Fix | Expected Impact |
|-------------|------------|-------------|-----------------|
| **Timing** | Verification after full solution | Critic during generation outline | Early detection of doomed approaches |
| **Specificity** | Binary verdict (correct/wrong) | Structured flaws with location | Generator can target fixes precisely |
| **Attacktype** | Generic attacks | Geometry-specific (theorem, config, definition) | Higher quality criticisms |
| **Curriculum** | Fixed progression | Math-domain progression | Attacks match problem complexity |
| **Counterexamples** | Sometimes vague | Explicit constructions | Generator sees exactly why claim fails |
| **Defense Tracking** | No feedback on why generator fails | Track concessions vs. defenses | Identify systematic weak reasoning |
| **Confidence** | Overconfident claims | Required confidence scores + penalties for miscalibration | Better calibrated solutions |

---

## Conclusion

The IMO-02 test case reveals a fundamental gap: **fast generation (low reasoning) produces solutions that sound good but are actually invalid**. This gap isn't fixed by better verification—it's fixed by **better generation**, which requires adversarial feedback during the generation process itself.

RLAC provides the framework: An adversarial critic that acts as a "proof saboteur" rather than a "proof grader" can identify flaws while there's still time to fix them, not after the solution is already committed. By incorporating specific geometric attack patterns, structured feedback with locations, and confidence calibration, we can shift the system from generating overconfident invalid solutions to generating calibrated, verification-resistant solutions.

The proposed enhancements are not just about better criticism—they're about **changing when and how criticism is applied**, making it part of the generation process rather than a post-hoc judgment.


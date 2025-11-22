# RLAC Architecture: Current vs Proposed

## Current Architecture (Sequential Pipeline)

```
┌─────────────────────────────────────────────────────────────────┐
│                      CURRENT SYSTEM                             │
└─────────────────────────────────────────────────────────────────┘

        Problem Statement
               ↓
        ┌──────────────┐
        │              │
        │  GENERATOR   │  ← Low reasoning effort
        │  (Agent)     │  ✓ Fast (1-3 hours)
        │              │  ✓ Creative exploration
        │              │  ✗ Overconfident claims
        └──────────────┘
               ↓
        Full Solution (Complete)
        (1000+ tokens, heavy commitment)
               ↓
        ┌──────────────┐
        │              │
        │  VERIFIER    │  ← High reasoning effort
        │  (Critic)    │  ✓ Catches errors
        │              │  ✓ Rigorous checking
        │              │  ✗ Feedback arrives too late
        └──────────────┘
               ↓
        Verdict: INVALID
        (Multiple critical errors found)
               ↓
        ┌──────────────┐
        │ Back to      │
        │ Generator    │  ← No specific guidance
        │ Retry...     │     on what to fix
        └──────────────┘


CHARACTERISTICS:
• Binary feedback (correct/incorrect)
• Post-hoc judgment
• Generator already committed to flawed approach
• No intermediate checkpoints
• No structured error location information
• No tracking of what generator learned

PROBLEM: Critic feedback shapes verification, not generation
```

---

## Proposed Architecture (Integrated Pipeline with RLAC)

```
┌─────────────────────────────────────────────────────────────────┐
│                    PROPOSED SYSTEM                              │
└─────────────────────────────────────────────────────────────────┘

        Problem Statement
               ↓
        ┌──────────────┐
        │              │
        │  GENERATOR   │  ← Low reasoning effort
        │  OUTLINE     │  ✓ Fast outline generation
        │              │  ✓ Flexible (not committed yet)
        └──────────────┘
               ↓
        Solution Outline (Brief)
        "Use power-of-a-point and Simson line"
               ↓
        ┌──────────────────────────┐
        │  CRITIC ROUND 0          │  ← EARLY ATTACK
        │  (Definition Check)      │  ✓ Attack outline only
        │                          │  ✓ Cheap (outline length)
        │  - Is approach sound?    │  ✓ Catches doomed paths early
        │  - Are lemmas correct?   │  ✗ generator can still pivot
        │  - Does flow make sense? │
        └──────────────────────────┘
               ↓
        Attack Feedback (Structured)
        {
          "type": "missing_precondition",
          "location": "Step 3: Power-of-a-point",
          "claim": "A,P,M,N concyclic",
          "why_wrong": "[specific reason]",
          "suggested_fix": "[how to address]"
        }
               ↓
        ┌─────────────────────────┐
        │  GENERATOR RESPONDS      │  ← DEFENSE/CONCESSION
        │  To Early Criticism      │  ✓ Opportunity to revise
        │                          │  ✓ Can try different approach
        │ Defends claim OR         │  ✓ No heavy sunk cost
        │ Revises outline OR       │
        │ Concedes and pivots      │
        └─────────────────────────┘
               ↓
        Revised Solution Outline
        "Use configuration property: A on circumcircle of PMN"
               ↓
        ┌──────────────┐
        │              │
        │  GENERATOR   │  ← Medium reasoning effort
        │  FULL PROOF  │  ✓ Informed by early feedback
        │              │  ✓ Avoiding known pitfalls
        └──────────────┘
               ↓
        Full Solution (Complete)
        (Shaped by adversarial feedback)
               ↓
        ┌─────────────────────────┐
        │  CRITIC ROUND 1-3       │  ← ITERATIVE ATTACKS
        │  (Lemma Verification)   │  ✓ Each lemma tested
        │                         │  ✓ Checks preconditions
        │  - Lemma 1: [attack]    │  ✓ Structured verdicts
        │  - Lemma 2: [attack]    │
        │  - Lemma 3: [attack]    │
        └─────────────────────────┘
               ↓
        Lemma Feedback + Generator Refinements
               ↓
        ┌─────────────────────────┐
        │  CRITIC ROUND 4-6       │  ← INTEGRATION ATTACKS
        │  (Integration & Closure)│  ✓ Checks logical flow
        │                         │  ✓ Looks for circular deps
        │  - Lemmas connect? ✓    │
        │  - Final follows? [?]   │  
        │  - All cases covered?   │
        └─────────────────────────┘
               ↓
        Final Verdict + Confidence Score
        ✓ ROBUST (Passed multiple attack rounds)
        ✓ Confidence: 0.92


CHARACTERISTICS:
• Continuous feedback (specific structured flaws)
• During-generation shaping
• Generator can pivot early (before heavy investment)
• Multiple checkpoints (outline → lemma → integration)
• Structured error location and suggested fixes
• Defense/concession tracking (learning signal)
• Confidence calibration (overconfidence penalty)

ADVANTAGE: Critic feedback shapes generation, not just judges it
```

---

## Side-by-Side Comparison

| Aspect | Current | Proposed |
|--------|---------|----------|
| **Timing** | Post-generation | During generation |
| **Checkpoints** | Single (final) | Multiple (outline → lemma → integration → robustness) |
| **Feedback** | Binary (correct/wrong) | Structured (type/severity/location/fix) |
| **Generator Input** | Verdict only | Specific flaw descriptions |
| **Early Pivot?** | No (solution already committed) | Yes (outline only) |
| **Attack Type** | Generic | Domain-specific (theorem, config, definition) |
| **Response Tracking** | No | Yes (defense vs. concession) |
| **Confidence** | No tracking | Required with calibration penalties |
| **Cost** | All cost in verification | Distributed (cheap early, full late) |
| **Learning Signal** | Rejection | Specific guidance |

---

## Detailed Comparison: Example from IMO-02

### Current Approach

```
ITERATION 1:
  Generator: "I'll use angle-bisector theorem on triangle CAD"
             (Low reasoning, fast generation)
  
  Generator produces: 5-minute full proof using this strategy
  
  Verifier: "ERROR - Angle-bisector preconditions violated.
             Points E, F not on side CD."
  
  Generator: "I failed. Let me try again..."
             (No specific guidance on what to fix)


ITERATION 2:
  Generator: "I'll use direct construction approach"
             (Different strategy, also fast generation)
  
  Generator produces: Another 5-minute full proof
  
  Verifier: "ERROR - Perpendicularity claim AP⊥PM unjustified"
  
  Generator: "I failed again. Let me try again..."


PATTERN: Binary feedback, trial-and-error approach, no progress indication
```

### Proposed Approach with RLAC

```
ITERATION 1 - OUTLINE PHASE:
  Generator: "Strategy: Use angle-bisector theorem on triangle CAD,
              then show BE, CF are feet of perpendiculars"
             (30 seconds, lightweight outline)
  
  Critic Round 0 (Definition Check):
    Attack: "You claim angle-bisector applies. Verify that E, F
             lie on side CD where the bisector meets it."
    
  Generator Response:
    "Wait, E is the SECOND intersection of line AP with Ω,
     not on line CD itself. My strategy is flawed!"
    
  Generator Revision:
    "New strategy: Use power-of-a-point property to establish
     relationships, then show A,P,M,N concyclic"


ITERATION 1 - FULL PROOF PHASE:
  Generator: "I'll prove A,P,M,N concyclic using symmetric
              properties of the circumcenter..."
             (5-minute full proof, informed by early feedback)
  
  Critic Round 1 (Lemma Verification):
    Attack on Key Lemma: "You claim circumcenter P satisfies
                         PA = PC = PD. Are C and D actually
                         symmetric with respect to point O (midpoint of MN)?"
    
  Generator Response:
    "Yes, because P is equidistant from C and D, and they're
     both on line MN through O, so O is their midpoint."
    
  Critic Round 2 (Logical Closure):
    Attack: "You claim this implies A,P,M,N concyclic.
             Show the actual circle and why these 4 points are on it."
    
  Generator Refinement:
    "By construction, O is equidistant from all four points A,P,M,N.
     Proof: [detailed calculation showing OA=OP=OM=ON]"
    
  Critic Round 3 (Final Robustness):
    Attack: "Assume one point is removed. Is configuration still valid?"
    
  Generator: "Yes, configuration holds with or without..."
  
  Final Verdict: ✓ ROBUST
                 Passed 3+ rounds of adversarial testing


PATTERN: Specific feedback, early course correction, structured progress
```

---

## Attack Intensity Progression

### Current (Generic)

```
Round 0-2: BASIC
  Generic obvious flaw checking
  
Round 3-6: MODERATE  
  Generic edge case testing
  
Round 7+: ADVANCED
  Generic subtle gap checking
```

### Proposed (Domain-Specific for Geometry)

```
Round 0-1: DEFINITION CHECK
  • Does every term exist? (points, lines, circles)
  • Are points where you claim they are?
  • Do all objects in config actually exist?
  Attack: "Is point E actually on circle Ω as you claimed?"

Round 2-3: THEOREM PRECONDITIONS
  • For angle-bisector: does it bisect? (right vertex, right angle)
  • For power-of-a-point: are lines actually secants/chords?
  • For similarity: do angle/side ratios actually match?
  Attack: "Angle-bisector theorem requires bisecting the angle
           at vertex A in triangle CAD. Does AP actually bisect ∠CAD?"

Round 4-6: CONFIGURATION VERIFICATION
  • Can you construct this with coordinates?
  • Is config non-degenerate? (points not collinear when shouldn't be)
  • What if config is slightly perturbed?
  Attack: "Construct this configuration explicitly with Ω centered
           at origin, radius 1, and Γ centered at (2,0), radius 2.
           Do your claimed properties hold?"

Round 7-8: LOGICAL CLOSURE
  • Are all cases covered? (collinear, tangent, intersecting)
  • Is anything circular? (proving using what you're trying to prove)
  • Does final claim actually follow from lemmas?
  Attack: "You proved A,P,M,N concyclic. Does the final tangency
           claim actually follow? Show the logical chain."

Round 9+: RIGOROUS RECONSTRUCTION
  • Rewrite proof formally, every step justified
  • Identify hand-waving ("clearly implies", "obviously", etc.)
  • Fill every logical gap explicitly
  Attack: "Take your step 3: 'Hence the line through H parallel to AP
           is the Simson line of A'. This requires A on circumcircle
           of PMN AND a classical theorem. Make this explicit."
```

---

## Confidence Calibration Mechanism

### Current (No Calibration)

```
Generator outputs solution without confidence levels
Verifier outputs binary verdict
Generator confidence never evaluated
→ Generator remains overconfident on repeated failures
```

### Proposed (With Calibration)

```
GENERATOR STATEMENT:
  "I claim [STATEMENT] with confidence 0.95"
  Example: "A, P, M, N lie on a circle" with confidence 0.95

ADVERSARIAL TEST:
  Critic: "Test this claim by constructing explicit coordinates
           showing whether it's true or false"

OUTCOME A - JUSTIFIED:
  Coordinates confirm: A, P, M, N are concyclic
  → Confidence was correct
  → Reward for calibration (+1 point)
  → Confidence score improves

OUTCOME B - UNJUSTIFIED (Overconfident):
  Coordinates show: A, P, M, N are NOT concyclic
  → Confidence was wrong
  → MISCALIBRATION PENALTY (-5 points)
  → Much larger than normal error penalty (-2 points)
  → Generator learns: Don't overconfidently claim things

OUTCOME C - PARTIALLY JUSTIFIED:
  Coordinates show: Only A, P, M are on circle (not N)
  → Confidence was partially wrong
  → PARTIAL PENALTY (-3 points)
  → Generator learns: Be more careful about "all 4 points"

LEARNING: Overconfidence is actively discouraged
           Careful reasoning with lower confidence is rewarded
```

---

## Implementation Roadmap (Research Phases)

### Phase 1: Enhanced Critic Module
**Duration:** Research & Development  
**Input:** Current adversarial_critic.py  
**Enhancements:**
- Structured flaw reporting (JSON with location, type, why_wrong, fix)
- Geometry-specific attack patterns library
- Counterexample generation for geometric claims
- Confidence scoring for attacks

**Output:** Enhanced adversarial_critic.py  
**Complexity:** Medium (existing critic infrastructure to build upon)

### Phase 2: Integrated Generation-Criticism
**Duration:** Research & Development  
**Prerequisites:** Phase 1 complete  
**Changes:**
- New "outline generation" step before full proof
- Insert critic after outline (Round 0)
- Generator reads feedback and revises outline
- Then proceed to full proof generation

**Output:** Modified agent_rlac.py with outline → critique → full proof workflow  
**Complexity:** Medium (orchestration logic)

### Phase 3: Confidence Calibration
**Duration:** Research & Development  
**Prerequisites:** Phase 2 complete  
**Changes:**
- Generator required to report confidence for key claims
- Critic tests claims explicitly
- Confidence calibration penalty/reward system
- Tracking of calibration accuracy over time

**Output:** Extended adversarial_critic.py with confidence testing  
**Complexity:** Medium (new penalty calculation, claim extraction)

### Phase 4: Curriculum Learning
**Duration:** Research & Development  
**Prerequisites:** Phase 1 complete  
**Changes:**
- Implement geometry-specific attack progression
- Progressive difficulty scaling
- Track which attack types are most effective
- Adapt difficulty based on solution type

**Output:** adversarial_prompts.py with domain curriculum  
**Complexity:** Medium (prompt engineering + metric tracking)

### Phase 5: Analytics & Feedback System
**Duration:** Ongoing  
**Prerequisites:** Phases 1-4 complete  
**Changes:**
- Track success rates by attack type
- Identify systematic weakness patterns
- Generate attack effectiveness reports
- Feedback for prompt optimization

**Output:** analysis/metrics scripts + reports  
**Complexity:** Low (analytics layer)

---

## Key Architectural Principles

### 1. **Timing Over Perfection**
A good critic running during generation (outline phase) beats an excellent critic running after completion.

### 2. **Specificity Over Generality**
Structured flaws with locations and suggested fixes beat binary verdicts.

### 3. **Domain-Specific Over Generic**
Attacks optimized for geometry (theorem preconditions, configurations) beat generic reasoning checks.

### 4. **Response Tracking Over Just Grading**
Knowing whether generator defends or concedes to attacks provides learning signals.

### 5. **Calibration Over Accuracy**
Penalizing overconfidence is more important than being right about everything.

---

## Success Criteria for RLAC Enhancement

### Primary Metrics
1. **Verification pass rate:** 0% → 40-60%
   - Measured by: solutions passing high-reasoning verification
   
2. **Confidence calibration:** Large gap → Small gap
   - Measured by: difference between generator confidence and actual correctness
   
3. **Early detection rate:** 0% → 50%+
   - Measured by: percentage of errors caught in Round 0 (outline phase)

### Secondary Metrics
4. **Concession rate:** 0% → 70%+
   - Measured by: generator fixing flaws when adversarially challenged
   
5. **Attack effectiveness:** Track which attack types break the most solutions
   - Measured by: attack type → success rate correlation

6. **Computational efficiency:** Early pivots save computation
   - Measured by: average time per iteration (should drop with early feedback)

---

## Research Contribution

This RLAC enhancement addresses a fundamental gap in AI mathematical reasoning:

**Current State:** Models can generate plausible-sounding arguments quickly, but lack mechanisms to verify them during generation.

**Proposed Solution:** Insert adversarial critics during generation to shape reasoning in real-time, not just judge it after completion.

**Impact:** Shift from binary success/failure outcomes to calibrated, verification-resistant solutions through continuous adversarial feedback.


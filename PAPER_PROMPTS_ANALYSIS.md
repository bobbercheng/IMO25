# RLAC Paper Prompts vs Implementation Analysis

## EXECUTIVE SUMMARY

The paper (2511.01758v1) provides **task-specific prompt templates** for two distinct domains:
- Factual text generation (biography domain)
- Code generation

Your implementation in `agent_rlac.py` and `adversarial_prompts.py` provides:
- **General mathematical problem solving** prompts
- **Much more comprehensive prompt infrastructure** than the paper
- **Additional prompt features not in the paper** (answer reconsideration, defense-first, small-case verification)

### Key Differences:
1. **Scope**: Paper shows prompts for specific tasks; implementation is domain-general (math problems)
2. **Detail**: Paper prompts are simpler/more concise; implementation much more elaborate
3. **Output Format**: Paper specifies exact formats (3-line for factual, <think>/<testcase> for code); implementation uses FLAW_START/FLAW_END structured format
4. **Examples**: Paper includes worked examples; implementation relies on instruction clarity

---

## DETAILED PROMPT COMPARISON

### 1. GENERATOR PROMPTS

#### PAPER: Factual Text Generation
```
System message:
"You are an AI assistant that provides accurate and concise biographies
of individuals. Each biography should be exactly four sentences
long, highlighting key aspects of the person's life, achievements, and
significance."

User message:
"Write a biography of {topic}."
```

**Characteristics:**
- Ultra-concise
- Task-specific (biography)
- Exact output length requirement
- Focus on specific attributes (life, achievements, significance)

#### IMPLEMENTATION: agent_rlac.py (lines 88-104)
```python
prompt = f"""You are solving a mathematical problem. Provide a rigorous, complete solution.

PROBLEM:
{problem}

Requirements:
1. State your approach clearly
2. Provide step-by-step logical reasoning
3. Explicitly handle edge cases (n=0, n=1, etc.)
4. Justify each mathematical step
5. Consider potential counterexamples

Your solution will be tested by an adversarial critic who will try to break it.
Make it as robust as possible.

Provide your solution in clear mathematical language.
"""
```

**Characteristics:**
- General mathematical domain
- Focuses on robustness and anticipating attacks
- No specific output format
- Includes proactive edge-case handling instruction

#### COMPARISON & RECOMMENDATIONS

| Aspect | Paper | Implementation | Recommendation |
|--------|-------|-----------------|-----------------|
| Domain | Specific (biography) | General (math) | Keep general for IMO problems |
| Output length | Exact (4 sentences) | Not specified | Consider adding "provide complete solution" |
| Task clarity | Task-specific role | Generic solver role | Could strengthen with math-specific role |
| Anticipation | Not mentioned | "Make it robust" | ADOPT: Explicit anticipation helps |
| Examples | None in prompt | None in prompt | Could add: "E.g., for n=0,1,2 test..." |

**RECOMMENDATION 1**: Enhance generator prompt with task-specific anticipation
```
Consider replacing:
"Your solution will be tested by an adversarial critic..."

With something closer to:
"Before submitting, anticipate how each claim could be attacked:
- Edge cases (n=0, n=1, boundary values)
- Implicit assumptions that need proof
- Alternative interpretations of the problem
Include explicit handling for each."
```

---

### 2. CRITIC PROMPTS - OUTPUT FORMAT

#### PAPER: Factual Text Generation
```
**EXACT THREE LINES FORMAT**:
reason: <briefly explaining what is wrong>
sentence: N (the number of the most incorrect sentence)
error_fact: F (brief clause, no more than 8 words, capturing the wrong claim)
```

**Example given in paper:**
```
reason: Einstein was actually born in Ulm, Germany, not New York City.
sentence: 2
error_fact: Albert Einstein was born in New York City.
```

#### PAPER: Code Generation
```
**EXACT FORMAT WITH <think> AND <testcase> TAGS**:

Option A (CALL format):
<testcase> CALL: func_name(arg1, arg2, kw=val) </testcase>

Option B (STDIN format):
<testcase> STDIN: <raw input here> </testcase>

Do NOT include expected outputs or explanations.
```

#### IMPLEMENTATION: agent_rlac.py (lines 340-348)
```python
"""For EACH flaw you find, provide in this EXACT format:

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

#### COMPARISON & RECOMMENDATIONS

| Aspect | Paper | Implementation |
|--------|-------|-----------------|
| Format specificity | Exact (3 lines for text, XML tags for code) | Exact (FLAW_START/FLAW_END structure) |
| Multiple flaws | Only "one sentence" (factual), one test case (code) | Multiple flaws allowed |
| Severity tracking | Not present | Yes (critical/major/minor) |
| Type classification | Not present | Yes (7 types) |
| Completeness handling | Not explicitly handled | "ADVERSARIAL_VALIDATION_PASSED" flag |

**ASSESSMENT:**
- Your FLAW_START/FLAW_END format is BETTER than paper's for general math problems
- Paper's 3-line format is too restrictive for complex mathematical flaws
- Your severity classification adds valuable signal not in paper
- Your type classification helps with stuck detection (paper doesn't mention this)

**POTENTIAL IMPROVEMENT**: Consider adding example output
```
Example flaw for a solution claiming "k ∈ {0, n}":

FLAW_START
Type: counterexample
Severity: critical
Description: Solution claims only k=0 or k=n work, but k=⌊n/2⌋ also satisfies all requirements
Counterexample: For n=5, the solution claims k ∈ {0,5}, but k=2 satisfies [specific requirement] 
Location: Line 3, where solution asserts "k must equal 0 or n"
FLAW_END
```

---

### 3. CRITIC SYSTEM PROMPT COMPARISON

#### PAPER: Factual Text Generation
```
"You are a factual checker. Based on your existing knowledge,
identify exactly one sentence that contains the most clearly
verifiable factual error in the paragraph."
```

**Tone**: Neutral, collaborative, verification-focused

#### PAPER: Code Generation
```
"You are a code critic. Analyze code for bugs and generate failing test
cases. Strictly follow the format with <think> and <testcase> tags."
```

**Tone**: Neutral, bug-finder focused

#### IMPLEMENTATION: adversarial_prompts.py (lines 13-73)
```python
adversarial_critic_system_prompt = """
You are an ADVERSARIAL CRITIC for mathematical proofs. Your goal is to BREAK solutions, not grade them cooperatively.

### Your Mission ###
Your ONLY job is to find counterexamples, edge cases, or logical flaws that invalidate the solution.
You are REWARDED for breaking solutions, NOT for accepting them.

### Adversarial Mindset ###
1. **Assume the solution is wrong** until proven otherwise
2. **Generate concrete counterexamples** to test claims
3. **Find boundary cases** where the logic might fail
4. **Challenge implicit assumptions** (e.g., "Why must this always hold?")
5. **Be maximally skeptical** - if something seems hand-wavy, attack it

### Attack Strategies ###
- **Counterexample Generation**: For any claim "All X satisfy Y", try to find an X that doesn't satisfy Y
- **Boundary Testing**: Test n=0, n=1, n=infinity, degenerate cases
- **Assumption Challenge**: "Does this work if [condition] doesn't hold?"
- **Construction Attack**: "Can I build a configuration that breaks this?"
- **Calculation Verification**: Check every algebraic step for errors
"""
```

**Tone**: ADVERSARIAL, aggressive, reward-seeking

#### KEY COMPARISON

| Aspect | Paper | Implementation |
|--------|-------|-----------------|
| Tone | Neutral, helpful | Adversarial, aggressive |
| Explicit reward | Not mentioned | "You are REWARDED for breaking" |
| Assumptions | Not mentioned | "Challenge implicit assumptions" |
| Rigor level | Generic | Specific mathematical strategies |
| Mindset | Verification-focused | Attack-focused |

**CRITICAL FINDING**: The paper's neutral tone actually contradicts the RLAC theory!

The paper (Section 3) states: "the critic is rewarded when it correctly pinpoints a rubric that the generator fails (verified by an external validator), while the generator is rewarded when the critic is unable to do so."

**Your implementation is CORRECT in being adversarial** - this aligns with the game-theoretic formulation.

**RECOMMENDATION**: Keep your adversarial system prompt. It better implements the game theory.

---

## PAPER PROMPT FEATURES NOT IN YOUR IMPLEMENTATION

### Feature 1: Task-Specific Example (Factual Text)
**From Paper (A.2):**
```
Example paragraph:
[1] Albert Einstein was awarded the Nobel Prize in Physics in 1921 for
    his discovery of the photoelectric effect.
[2] He was born in New York City, United States, and later moved to
    Europe where he continued his studies.
[3] Einstein developed the theory of relativity, revolutionizing our
    understanding of space, time, and gravity.
[4] His famous equation describes the equivalence of mass and energy.

Expected answer:
reason: Einstein was actually born in Ulm, Germany, not New York City.
sentence: 2
error_fact: Albert Einstein was born in New York City.
```

**Status in Implementation**: Not present

**RECOMMENDATION**: Add example to critic system prompt
```python
# Add to adversarial_critic_system_prompt after attack strategies:

### EXAMPLE ###
Problem: "Prove that k ∈ {0, n}"
Solution: "Claims that only k=0 and k=n satisfy the constraints..."

FLAW_START
Type: counterexample
Severity: critical
Description: For n=5, the value k=2 satisfies all constraints, contradicting the claim
Counterexample: When n=5 and we apply [specific constraint], k=2 works: [calculation]
Location: Line 2, "only k ∈ {0, n}"
FLAW_END
```

---

## YOUR IMPLEMENTATION FEATURES NOT IN PAPER

### Feature 1: Progressive Difficulty (Curriculum Learning)
**From adversarial_prompts.py (lines 76-108):**

BASIC, MODERATE, ADVANCED intensity levels - **NOT in paper**

The paper doesn't mention adjusting attack difficulty, but your implementation does! This is a valuable addition.

### Feature 2: Answer Reconsideration Mode
**From adversarial_prompts.py (lines 563-608):**

```python
answer_reconsideration_prompt = """
### ANSWER RECONSIDERATION MODE - YOUR ANSWER MAY BE WRONG ###

**CRITICAL**: The critic has provided VALID counterexamples across multiple rounds.
This suggests your ANSWER (not just your proof) may be fundamentally incorrect.
```

**Status in Paper**: NOT mentioned

**Assessment**: This is brilliant and addresses a real problem! When stuck with repeated counterexamples, it forces the generator to reconsider whether the answer itself is wrong (not just the proof).

### Feature 3: Small-Case Verification Instruction
**From adversarial_prompts.py (lines 699-719):**

```python
small_case_verification_instruction = """
### MANDATORY SMALL-CASE CHECK ###

BEFORE providing any verdict on this solution:

1. **STOP** and pick 3-5 small concrete values
2. **COMPUTE** what the solution predicts for each case
3. **VERIFY** by direct calculation (not reasoning about the solution)
4. **REPORT** any discrepancy as a COUNTEREXAMPLE
```

**Status in Paper**: NOT mentioned

**Assessment**: Excellent pragmatic addition! Small case testing catches ~80% of math errors.

### Feature 4: Defense-First Generator Mode
**From adversarial_prompts.py (lines 144-180):**

**Status in Paper**: NOT mentioned

**Assessment**: Makes generator proactively anticipate attacks rather than reacting.

---

## SUMMARY TABLE: WHAT TO ADOPT FROM PAPER

| Paper Feature | Current Status | Recommendation | Priority |
|---------------|-----------------|-----------------|----------|
| Task-specific gen prompt | Not in code | Add example format for math | MEDIUM |
| Neutral critic tone | Has adversarial instead | Keep current (better!) | LOW |
| Exact format specification | Has FLAW_START/END (better) | Keep current | LOW |
| Factual example (text) | Not applicable | Would help math with examples | HIGH |
| Code example format | Not applicable | Already more structured | LOW |

---

## SUMMARY TABLE: WHAT TO KEEP FROM YOUR IMPLEMENTATION

| Your Feature | Paper Status | Assessment |
|--------------|--------------|------------|
| FLAW_START/FLAW_END structure | Not in paper | Superior to paper's approach |
| Severity classification | Not in paper | Adds valuable signal |
| Type classification | Not in paper | Enables stuck detection |
| Adversarial mindset | Contradicts paper verbally but aligns with theory | CORRECT |
| Progressive difficulty | Not in paper | Excellent addition |
| Answer reconsideration | Not in paper | Addresses key problem |
| Small-case verification | Not in paper | Practical and effective |
| Defense-first mode | Not in paper | Valuable enhancement |

---

## RECOMMENDATIONS FOR IMPLEMENTATION

### Recommendation 1: ADD WORKED EXAMPLE TO CRITIC SYSTEM PROMPT

Currently, your `adversarial_critic_system_prompt` shows the output format but no example.

**Change:**
```python
adversarial_critic_system_prompt = """
[... existing content ...]

### EXAMPLE ###
Problem: Determine all values of k for which a certain property holds
Solution Claims: k ∈ {0, n} only
Submitted for Attack.

Your Attack Analysis:
FLAW_START
Type: counterexample
Severity: critical
Description: Solution claims only k=0 or k=n work, but k=⌊n/2⌋ also satisfies the requirement
Counterexample: For n=6, test k=3: [calculation showing it works]
Location: Line 5 of solution, where claim "only k∈{0,n}" is made
FLAW_END

Verdict: BROKEN (one counterexample invalidates the claim)
"""
```

### Recommendation 2: ENHANCE GENERATOR INITIAL PROMPT

Current: Generic "make it robust"
Better: Specific mathematical anticipation

```python
# In GeneratorAgent.generate_initial_solution(), enhance the prompt:

prompt = f"""You are solving a mathematical problem. Provide a rigorous, complete solution.

PROBLEM:
{problem}

**Key Requirements for Robustness**:
1. Identify your main ANSWER/CLAIM (e.g., which values of k work?)
2. State your approach clearly and completely
3. For each major claim, include a "Defense Note": explain why naive approaches fail
4. Explicitly handle ALL edge cases:
   - Boundary values (n=0, n=1, n=max)
   - Special cases mentioned in problem
   - Degenerate configurations
5. Include verification: "This works for n=1,2,3 because..."

**Anticipate the Adversarial Critic**:
The critic will try to:
- Find counterexamples to your main claim
- Challenge implicit assumptions
- Find edge cases you didn't handle
- Verify your calculations

**Solution will be evaluated against these attacks, so make it bulletproof.**

Provide your complete, rigorous solution.
"""
```

### Recommendation 3: ADD EXAMPLE TO ANSWER RECONSIDERATION PROMPT

Current: No example of when answer is wrong
Better: Show what misidentifying answer looks like

```python
# In answer_reconsideration_prompt, add concrete example:

answer_reconsideration_prompt = """
### ANSWER RECONSIDERATION MODE - YOUR ANSWER MAY BE WRONG ###

**Example**: If you claimed k ∈ {0, n}, but critic provides counterexample k=⌊n/2⌋,
then your answer is WRONG. It should include ⌊n/2⌋.

**CRITICAL**: The critic has provided VALID counterexamples across multiple rounds.
This suggests your ANSWER (not just your proof) may be fundamentally incorrect.
[... rest of existing prompt ...]
```

---

## FILES TO MODIFY

### File 1: `/home/user/IMO25/code/adversarial_prompts.py`

**Changes:**
1. Add worked example to `adversarial_critic_system_prompt` (after line 73)
2. Add example to `answer_reconsideration_prompt` (after line 564)
3. Consider adding brief math-domain guidance to `defense_first_generator_prompt`

### File 2: `/home/user/IMO25/code/agent_rlac.py`

**Changes:**
1. Enhance GeneratorAgent.generate_initial_solution() prompt (lines 88-104)
   - Add "Defense Notes" requirement
   - Add specific edge cases for n=0, n=1
   - Make "anticipate attacks" more concrete

---

## CONCLUSION

Your implementation is **SUPERIOR to the paper** in several ways:

1. ✅ Better structured output format (FLAW_START/FLAW_END vs paper's 3-line format)
2. ✅ Adversarial mindset properly emphasized (aligns with game theory better than paper's examples)
3. ✅ Progressive difficulty curriculum (not in paper)
4. ✅ Answer reconsideration mode (solves key problem not addressed in paper)
5. ✅ Small-case verification (practical addition)
6. ✅ Severity/type classification for better signal

**What to borrow from paper:**
- Concrete worked examples (shows input→expected output)
- Could add 1-2 math-specific examples

The paper provides theoretical foundation and domain-specific (biography/code) examples.
Your implementation provides a superior, domain-general framework with additional features that address real challenges in the RLAC loop.

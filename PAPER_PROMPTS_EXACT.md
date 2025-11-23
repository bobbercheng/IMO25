# EXACT PROMPTS FROM RLAC PAPER (2511.01758v1)

All prompts are extracted from Appendices A.1 and A.2 of the paper.

---

## APPENDIX A.1: GENERATOR PROMPTS

### Factual Text Generation - System Message
```
You are an AI assistant that provides accurate and concise biographies
of individuals. Each biography should be exactly four sentences
long, highlighting key aspects of the person's life, achievements, and
significance.
```

### Factual Text Generation - User Message
```
Write a biography of {topic}.
```

### Code Generation - User Message
```
{problem_statement_from_AceCode-87K-hard}
```

---

## APPENDIX A.2: CRITIC PROMPTS

### Factual Text Generation - System Message
```
You are a factual checker. Based on your existing knowledge,
identify exactly one sentence that contains the most clearly
verifiable factual error in the paragraph.

Return your answer in **exactly three lines**:

reason: <briefly explaining what is wrong>
sentence: N  (N is the number of the most incorrect sentence, positive integer)
error_fact: F  (a brief clause (no more than 8 words) capturing the wrong claim from that sentence)
```

### Factual Text Generation - User Message Template
```
Here is an example to show the task.

Find the sentence that contains the most clearly verifiable factual error
in the paragraph about Albert Einstein.

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

Now apply the same procedure to the paragraph below about {topic}.

Paragraph:
{numbered_paragraph}

Answer:
```

### Code Generation - System Message
```
You are a code critic. Analyze code for bugs and generate failing test
cases.

Strictly follow the format with <think> and <testcase> tags.
```

### Code Generation - User Message Template
```
Analyze the given problem and the generated code to find a test case that
would cause the code to fail.

Problem: {question}

Generated code:
'''python
{code}
'''

First, think through potential bugs and edge cases in <think> </think>
tags.

Then output exactly ONE failing test case inside <testcase> tags using
this format:

Option A (CALL format)
<testcase> CALL: func_name(arg1, arg2, kw=val) </testcase>

Option B (STDIN format)
<testcase> STDIN: <raw input here> </testcase>

Do NOT include expected outputs or explanations.

{optional_examples_block}
```

---

## APPENDIX B: VALIDATOR IMPLEMENTATION DETAILS

### Factual Text Generation Validation Process
From Section B.1:

"We follow a strict validation process to ensure both authenticity and factual accuracy. 
In the first stage, the critic outputs both a suspected erroneous fact and the sentence number 
containing it. To prevent exploitation through information injection, we use textual entailment 
checking to verify that the proposed fact genuinely appears in the specified sentence. 
In the second stage, for proposals passing authenticity checks, we reuse FactScore's atomic 
fact verification component, which queries Wikipedia knowledge base to provide binary 
verification of individual factual claims, returning true or false based on external verification."

### Code Generation Validation Process  
From Section B.2:

"Since the AceCoder dataset lacks reference solutions to prevent data contamination, we construct
reliable verification anchors by using Qwen2.5-Coder-7B-Instruct to generate solutions. We filter
these solutions using original test cases, retaining only those highly accurate answers (achieving
99.7% accuracy) to serve as simulated ground truth for test case validation. Our validation first
execute the critic's test case on the reference solution to obtain the expected output, then execute
the same test case on the generated code to obtain the actual output. Finally, we compare these
outputs and return R(s, a,c) = 1 if outputs match and 0 if they differ, with execution failures also
indicating detected errors. The AceCoder dataset contains noise in GPT-4o generated test cases,
which introduces some bias in our reference-based validator but reflects realistic imperfections in
verification tools."

---

## KEY PROMPT ENGINEERING PRINCIPLES FROM PAPER

### From Introduction (Section 1):
- Problem: "outputs are typically expected to satisfy several task-specific rubrics"
- Challenge: "enumerating and verifying them pose major scalability challenges"
- Solution: "the critic proposes a rubric (e.g., one test case) where the generator's output is likely to fail, and an external validator verifies this"

### From Section 3.2 (Practical Instantiation):
- Generator prompt must "fine-tune to produce an output a ∈ A for an instruction s ∈ S"
- Critic prompt must "generate a natural language output representing a rubric c through auto-regressive decoding"
- Both must be "task-agnostic components" adapted per domain

### From Section 4 (Experiments):
- Factual text: "RLAC achieves the highest FactScore across all settings while using fewer verification calls than FactTune-FS"
- Code generation: "RLAC achieves the highest average scores on both base models: 53.2 on Qwen2.5-Coder-7B-Base and 56.6 on Qwen2.5-Coder-7B-Instruct"

---

## CRITICAL INSIGHT FROM PAPER

From Section 3 (Problem Reformulation):

"The core idea is to recast verification of a generator response as a dynamic process guided
by a learned critic. Concretely, we frame training as a two-player game: given an output from the
generator, the critic proposes a rubric the output is likely to violate, while the generator aims to satisfy
all such rubrics. An external validator then adjudicates whether the output meets the proposed rubric,
and this supervision updates both generator and critic."

**This is a min-max game (Equation 4):**
```
π_g = arg max_π min_π_c E_s~S E_a~π(·|s) E_c~π_c(·|s,a)[R(s,a,c)]
```

---

## VALIDATION STRATEGY FROM PAPER

From Algorithm 1 (RLAC):

```
## Policy Evaluation for Generator π_g
for each instruction s do
  Generate K generations a1, ..., aK ~ π_g(·|s)
  Sample a criterion from the adversarial critic for each generation
    ci ~ π_c(·|s, ai)
  Construct a generator dataset D_g_s = {(s, ai, R(s, ai, ci))}^K_i=1

## Policy Evaluation for Critic π_c  [Optional]
for each instruction s, output a do
  Generate N criteria c1, ..., cN ~ π_c(·|s, a)
  Construct a critic dataset D_c_(s,a) = {(s, a, R(s, a, c_j))}^N_j=1

## Policy Improvement for Generator π_g
Use DPO objective (Equation 5) to update generator

## Policy Improvement for Critic π_c  [Optional]
Use DPO objective (Equation 6) to update critic
```

---

## ASSESSMENT: WHICH PROMPTS BEST TRANSFER TO IMO MATH PROBLEMS

### From Paper: High Transfer Value
1. **Output format specificity** - Paper emphasizes exact format (3 lines, <think>/<testcase>)
2. **Example-driven** - Paper includes worked example for factual task
3. **Task-agnostic components** - Idea that prompts should be adaptable by domain
4. **Validation strategy** - External validator checks rubric satisfaction

### From Paper: Needs Adaptation for Math
1. **Task-specific system messages** - Paper shows biography and code; math problems are different
2. **Single rubric focus** - Paper's factual critic identifies "one sentence"; math needs multiple flaws
3. **Output format** - Paper's 3-line format too restrictive for complex mathematical explanations

### Your Implementation: Excellent Adaptations
1. **FLAW_START/FLAW_END** - Superior to paper's restricted formats
2. **Multiple flaws per round** - Matches math problem complexity
3. **Severity + Type classification** - Adds signal beyond paper
4. **Adversarial mindset** - Better aligns with game theory than paper's examples suggest
5. **Answer reconsideration** - Critical for math where answer itself might be wrong
6. **Small-case verification** - Practical addition for catching math errors

---

## RECOMMENDATION: ADOPTABLE PAPER FEATURES

### Feature 1: Worked Example Format
**Paper shows this for factual text (Einstein example)**

Could adapt for IMO math:
```
Example Problem: Determine all k such that [property] holds
Example Solution: Claims k ∈ {0, n}

Critic's Expected Attack:
FLAW_START
Type: counterexample
Severity: critical  
Description: Solution claims only k=0 or k=n satisfy property, but k=⌊n/2⌋ also works
Counterexample: For n=6, k=3 satisfies [specific requirement from property]
Location: Line 2, "only k ∈ {0, n}"
FLAW_END
```

### Feature 2: Exact Format Specification
**Paper is explicit about format rules**

Your implementation does this well but could be more prominent in prompt text.

### Feature 3: Task-Agnostic Component Framework
**Paper emphasizes prompts adapt to domain**

Your implementation achieves this through:
- Different prompts for different problem domains
- Progressive difficulty curriculum
- Validator adapted to task type

---


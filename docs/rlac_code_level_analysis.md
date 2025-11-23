# RLAC Agent - Detailed Code-Level Issue Report

## Issue #1: Criticism History Truncation (CRITICAL FLOW BUG)

### Location
File: `/home/user/IMO25/code/agent_rlac.py`
Lines: 243-255

### Current Code
```python
243 |    def _format_criticism_history(self, history: List[Criticism]) -> str:
244 |        """Format criticism history for context."""
245 |        if not history:
246 |            return "No previous criticism."
247 |
248 |        summary = []
249 |        for i, crit in enumerate(history, 1):
250 |            flaw_count = len(crit.flaws)
251 |            summary.append(f"Iteration {i}: {flaw_count} flaw(s) found")
252 |            for flaw in crit.flaws[:2]:  # ← ISSUE: Only shows first 2 flaws
253 |                summary.append(f"  - [{flaw.severity}] {flaw.type}: {flaw.description[:100]}")
254 |                # ↑ ISSUE: Description truncated to 100 chars, NO COUNTEREXAMPLE
255 |
256 |        return "\n".join(summary)
```

### What Gets Lost
1. **Flaws 3+**: If an iteration found 5 flaws, only 2 appear in generator's context
2. **Full descriptions**: 100-char limit cuts off nuanced flaw descriptions
3. **All counterexamples**: The generator NEVER sees what counterexamples were found

### Flow Impact
When generator revises on iteration 2:
```python
# Line 129-130
criticism_summary = self._format_criticism_history(criticism_history)
latest_flaws = self._format_latest_criticism(latest_criticism)

# Passed to generator at line 188
prompt = f"""...
CRITICISM HISTORY SUMMARY:
{criticism_summary}
...
"""
```

Generator receives truncated history, missing crucial context.

### Proposed Fix
```python
def _format_criticism_history(self, history: List[Criticism]) -> str:
    """Format full criticism history for context."""
    if not history:
        return "No previous criticism."

    summary = []
    for i, crit in enumerate(history, 1):
        flaw_count = len(crit.flaws)
        summary.append(f"Iteration {i}: {flaw_count} flaw(s) found")
        for j, flaw in enumerate(crit.flaws, 1):  # ← Remove [:2] limit
            summary.append(f"  Flaw {j}. [{flaw.severity.upper()}] {flaw.type}")
            summary.append(f"     {flaw.description}")  # ← Full description
            if flaw.counterexample:
                summary.append(f"     Example: {flaw.counterexample}")  # ← Add this!
            summary.append(f"     At: {flaw.location}")

    return "\n".join(summary)
```

---

## Issue #2: Answer Reconsideration Evidence Limitation (CRITICAL)

### Location
File: `/home/user/IMO25/code/agent_rlac.py`
Lines: 135-138, 226-241

### Current Code (Issue)
```python
226 |    def request_answer_reconsideration(self, counterexamples: List[str]):
227 |        """
228 |        Signal that the generator's ANSWER may be wrong.
...
236 |        """
237 |        self.answer_reconsideration_requested = True
238 |        self.accumulated_counterexamples.extend(counterexamples)
239 |        # Keep only the most recent counterexamples to avoid prompt explosion
240 |        self.accumulated_counterexamples = self.accumulated_counterexamples[-10:]  # ← Keeps 10
241 |
```

### Current Code (Usage)
```python
135 |        if self.answer_reconsideration_requested:
136 |            # Accumulate counterexamples for evidence
137 |            counterexample_evidence = "\n".join([
138 |                f"- {ce}" for ce in self.accumulated_counterexamples[-5:]  # ← ISSUE: Only uses last 5!
139 |            ])
```

### The Problem
- Line 240 keeps 10 counterexamples
- Line 138 uses only the last 5 of those 10
- **Generator makes answer reconsideration with only 50% of accumulated evidence**

### Example Failure Scenario
```
Round 1: Counterexample shows k=1 doesn't work
Round 2: Counterexample shows k=1 actually does work (contradiction!)
Round 3: Multiple examples show k=0 doesn't work
...
Round 6: Gets stuck, triggers answer reconsideration

accumulated_counterexamples = [ce1, ce2, ce3, ce4, ce5, ce6, ce7, ce8, ce9, ce10]

Evidence shown to generator = [ce6, ce7, ce8, ce9, ce10]  ← Missing the PATTERN!
Generator can't see that ce1 (k=1 doesn't work) was later contradicted by ce2
```

### Proposed Fix
```python
def revise_solution(self, problem: str, previous_solution: Solution, ...):
    ...
    if self.answer_reconsideration_requested:
        # Show ALL accumulated counterexample evidence
        counterexample_evidence = "\n".join([
            f"- {ce}" for ce in self.accumulated_counterexamples  # ← Use ALL
        ])
        
        # But add token management warning
        if len(self.accumulated_counterexamples) > 10:
            counterexample_evidence = (
                f"[Showing {len(self.accumulated_counterexamples)} counterexamples "
                f"across {len(set(self.accumulated_counterexamples))} distinct examples]\n"
                + counterexample_evidence
            )
```

---

## Issue #4: Fragile Flaw Parsing (MEDIUM)

### Location
File: `/home/user/IMO25/code/agent_rlac.py`
Lines: 405-429

### Current Code
```python
405 |        # Extract flaws using simple parsing
406 |        flaws = []
407 |        flaw_blocks = response.split("FLAW_START")
408 |
409 |        for block in flaw_blocks[1:]:  # Skip first split (before any FLAW_START)
410 |            if "FLAW_END" not in block:
411 |                continue
412 |
413 |            flaw_text = block.split("FLAW_END")[0].strip()
414 |
415 |            # Parse fields
416 |            flaw_dict = {}
417 |            for line in flaw_text.split("\n"):
418 |                if ":" in line:
419 |                    key, value = line.split(":", 1)
420 |                    flaw_dict[key.strip().lower()] = value.strip()  # ← Converts to lowercase
421 |
422 |            if flaw_dict:
423 |                flaws.append(Flaw(
424 |                    type=flaw_dict.get('type', 'unknown'),
425 |                    severity=flaw_dict.get('severity', 'major'),
426 |                    description=flaw_dict.get('description', ''),
427 |                    counterexample=flaw_dict.get('counterexample') if flaw_dict.get('counterexample', 'N/A') != 'N/A' else None,
428 |                    location=flaw_dict.get('location', 'unspecified')
429 |                ))
```

### Parsing Fragility Examples

**Scenario 1: Missing space after colon (LLM variation)**
```
Input from LLM:
Type:counterexample
Severity: critical

Parser creates:
flaw_dict = {'type:counterexample': ''}  ← Wrong key!

Result:
flaw.type = 'unknown'  ← Falls back to default!
```

**Scenario 2: Extra whitespace**
```
Input:
Type  :  counterexample
Description:  The n=0 case fails

Parser creates:
flaw_dict = {'type  ': 'counterexample'}  ← Extra spaces in key!

Result:
flaw.type = 'unknown'  ← Fails to match 'type' key!
```

**Scenario 3: Different field order**
```
Input:
Type: counterexample
Counterexample: n=0 breaks
Severity: critical
Description: Missing handling of n=0

Parser: Works OK (order doesn't matter)
But if LLM invents a new field...

Input:
Type: counterexample
Severity: critical
Subcategory: algebraic
Description: ...

Parser:
flaw_dict = {..., 'subcategory': 'algebraic'}
Result: Silently ignores unknown fields
```

### Proposed Robust Fix
```python
def _parse_criticism(self, response: str, iteration: int) -> Criticism:
    """Parse LLM response into structured Criticism object with validation."""
    
    if "ADVERSARIAL_VALIDATION_PASSED" in response:
        return Criticism(
            no_flaws_found=True,
            flaws=[],
            raw_response=response,
            iteration=iteration
        )
    
    flaws = []
    flaw_blocks = response.split("FLAW_START")
    
    for block in flaw_blocks[1:]:
        if "FLAW_END" not in block:
            continue
        
        flaw_text = block.split("FLAW_END")[0].strip()
        
        # Parse fields with normalization
        flaw_dict = {}
        for line in flaw_text.split("\n"):
            line = line.strip()
            if not line or ":" not in line:
                continue
            
            key, value = line.split(":", 1)
            key = key.strip().lower().replace(" ", "_")  # Normalize whitespace
            value = value.strip()
            
            if key and value:  # Only store non-empty fields
                flaw_dict[key] = value
        
        if not flaw_dict:
            continue
        
        # Validate required fields
        required_fields = ['type', 'severity', 'description', 'location']
        missing = [f for f in required_fields if f not in flaw_dict]
        
        if missing:
            print(f"[PARSE WARNING] Missing fields in flaw: {missing}")
            continue  # Skip malformed flaws instead of using defaults
        
        flaws.append(Flaw(
            type=flaw_dict.get('type', 'unknown'),
            severity=flaw_dict.get('severity', 'major'),
            description=flaw_dict.get('description', ''),
            counterexample=flaw_dict.get('counterexample') if flaw_dict.get('counterexample', 'N/A') != 'N/A' else None,
            location=flaw_dict.get('location', 'unspecified')
        ))
    
    # If no flaws parsed, add placeholder
    if not flaws and "ADVERSARIAL_VALIDATION_PASSED" not in response:
        flaws.append(Flaw(
            type='unparsed',
            severity='major',
            description='Critic response not in expected format',
            counterexample=None,
            location='See raw response'
        ))
    
    return Criticism(
        no_flaws_found=len(flaws) == 0,
        flaws=flaws,
        raw_response=response,
        iteration=iteration
    )
```

---

## Issue #10: Missing Solution Validation

### Location
File: `/home/user/IMO25/code/agent_rlac.py`
Lines: 210-220

### Current Code
```python
210 |        response = self.llm.generate(
211 |            prompt=prompt,
212 |            reasoning_effort=self.reasoning_effort
213 |        )
214 |
215 |        return Solution(
216 |            content=response,  # ← No validation!
217 |            iteration=previous_solution.iteration + 1,
218 |            timestamp=datetime.now().isoformat(),
219 |            reward=0.0
220 |        )
```

### Failure Cases
1. **Empty response**: LLM returns "" due to timeout/error
2. **None response**: API error returns None
3. **Truncated response**: Response cut off mid-proof
4. **Garbage response**: API returns malformed JSON

All proceed to line 521 adversarial attack, wasting tokens.

### Proposed Fix
```python
def revise_solution(self, problem: str, previous_solution: Solution,
                   latest_criticism: Criticism,
                   criticism_history: List[Criticism]) -> Solution:
    ...
    response = self.llm.generate(
        prompt=prompt,
        reasoning_effort=self.reasoning_effort
    )
    
    # VALIDATION CHECK
    if not response or not response.strip():
        raise ValueError(
            f"Generator produced empty response at iteration {previous_solution.iteration + 1}"
        )
    
    if len(response) < 100:  # Minimum reasonable solution length
        print(f"[WARNING] Solution suspiciously short ({len(response)} chars). "
              f"Response: {response[:50]}...")
    
    return Solution(
        content=response,
        iteration=previous_solution.iteration + 1,
        timestamp=datetime.now().isoformat(),
        reward=0.0
    )
```

---

## Issue #3: F-String Brace Escaping Risk

### Location
File: `/home/user/IMO25/code/agent_rlac.py`
Lines: 139-166

### Current Code
```python
139 |            strategy_instruction = f"""
140 |### ANSWER RECONSIDERATION MODE - YOUR ANSWER MAY BE WRONG ###
141 |
142 |**CRITICAL**: The critic has provided VALID counterexamples across multiple rounds.
143 |This suggests your ANSWER (not just your proof) may be fundamentally incorrect.
144 |
145 |**Evidence Summary**:
146 |{counterexample_evidence}
...
```

### Risk Scenario
If counterexample contains mathematical set notation:
```python
counterexample = "The set k ∈ {1, 2, 3} is not covered"
# or
counterexample = "For k={1,2}, the formula breaks"

# In f-string:
strategy_instruction = f"""...Evidence: {counterexample}..."""

# Python tries to interpret {1, 2, 3} as f-string expression!
# Results in: SyntaxError or unexpected behavior
```

### Proposed Fix
```python
# Option 1: Use format() instead of f-string
strategy_instruction = """
### ANSWER RECONSIDERATION MODE - YOUR ANSWER MAY BE WRONG ###

**CRITICAL**: The critic has provided VALID counterexamples across multiple rounds.
This suggests your ANSWER (not just your proof) may be fundamentally incorrect.

**Evidence Summary**:
{evidence}

**BEFORE continuing, answer these questions:**
...
""".format(evidence=counterexample_evidence)

# Option 2: Escape braces
strategy_instruction = f"""
...Evidence Summary:
{counterexample_evidence}
...
""".replace("{", "{{").replace("}", "}}")  # Escape for safety

# Option 3: Build string without f-string
parts = [
    "### ANSWER RECONSIDERATION MODE ###",
    "",
    "**Evidence Summary**:",
    counterexample_evidence,
]
strategy_instruction = "\n".join(parts)
```

---

## Issue #6: Missing System Prompt

### Location
File: `/home/user/IMO25/code/agent_rlac.py`
Lines: 210-213 (generate calls)
Vs.
Lines: 749-768 (GPTOSSClient signature)

### Gap Analysis
```python
# Lines 106-109 (initial generation - also missing system prompt)
response = self.llm.generate(
    prompt=prompt,
    reasoning_effort=self.reasoning_effort
)

# Lines 210-213 (revision - also missing)
response = self.llm.generate(
    prompt=prompt,
    reasoning_effort=self.reasoning_effort
)

# But GPTOSSClient supports it!
# Lines 749-768
def generate(self, prompt: str, reasoning_effort: str = "high",
            system_prompt: str = None, timeout: int = 600) -> str:
    ...
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
```

### Proposed Fix
```python
class GeneratorAgent:
    def __init__(self, llm_client, reasoning_effort="high"):
        self.llm = llm_client
        self.reasoning_effort = reasoning_effort
        self.strategy_shift_requested = False
        self.answer_reconsideration_requested = False
        self.accumulated_counterexamples = []
        self.last_answer = None
        
        # Add system prompt
        self.system_prompt = """You are an expert mathematical problem solver.
Your task is to provide rigorous, complete, and correct solutions to mathematical problems.
Focus on clarity, correctness, and handling all edge cases."""

    def generate_initial_solution(self, problem: str) -> Solution:
        ...
        response = self.llm.generate(
            prompt=prompt,
            reasoning_effort=self.reasoning_effort,
            system_prompt=self.system_prompt  # ← Add this
        )
        ...

    def revise_solution(self, ...):
        ...
        response = self.llm.generate(
            prompt=prompt,
            reasoning_effort=self.reasoning_effort,
            system_prompt=self.system_prompt  # ← Add this
        )
        ...
```

---

## Summary: Message Flow Path

### Current Flow (with bugs)
```
Iteration 1:
  generate_initial_solution(problem)
    ↓ LLM returns solution
  adversarial_attack(solution)
    ↓ Parses flaws (fragile #4)
  criticism_history.append(criticism)

Iteration 2:
  revise_solution(
    latest_criticism=criticism_history[-1],    # ✓ OK
    criticism_history=criticism_history         # ✓ OK (has iteration 1)
  )
    → _format_criticism_history(history)       # ✗ TRUNCATES #1
    → _format_latest_criticism(criticism)      # ✓ Full detail
    → request_answer_reconsideration()         # ✗ Limits to 5 #2
  ↓
  adversarial_attack(solution)                 # ✗ No validation on input #10
    ↓ Parses (fragile #4)
  criticism_history.append(criticism)

Iteration 3+: Repeats with accumulating truncation
```

### Fixed Flow (proposed)
```
1. Add robust validation of LLM responses #10
2. Pass full flaw history without truncation #1
3. Pass all counterexamples to answer reconsideration #2
4. Improve parsing robustness #4
5. Add system prompts to generator #6
6. Escape braces in f-strings #3
```

# RLAC Message Construction & Flow - Bug Analysis Report

## Critical Issues Found

### 1. INFORMATION LOSS: Criticism History Truncation (Lines 243-255)

**File:** `/home/user/IMO25/code/agent_rlac.py`
**Lines:** 243-255
**Severity:** HIGH

#### Issue
The `_format_criticism_history()` method **intentionally truncates** detailed criticism information:

```python
def _format_criticism_history(self, history: List[Criticism]) -> str:
    """Format criticism history for context."""
    if not history:
        return "No previous criticism."

    summary = []
    for i, crit in enumerate(history, 1):
        flaw_count = len(crit.flaws)
        summary.append(f"Iteration {i}: {flaw_count} flaw(s) found")
        for flaw in crit.flaws[:2]:  # ← BUG: Only shows FIRST 2 flaws
            summary.append(f"  - [{flaw.severity}] {flaw.type}: {flaw.description[:100]}")
            # ↑ BUG: Descriptions truncated to 100 chars, counterexamples OMITTED

    return "\n".join(summary)
```

**Problems:**
- Only shows first 2 flaws per iteration, hiding 3rd+ flaws completely
- Description truncated to 100 characters, cutting off crucial details
- **Counterexamples are completely omitted** - the generator never sees what counterexamples were found in previous rounds
- This causes the generator to miss the same flaw multiple times

**Impact:** When multiple rounds fail with same flaw type, the generator sees only:
```
Iteration 1: 3 flaw(s) found
  - [critical] counterexample: When n=0, the base...
  - [major] logical_gap: The induction step ass...
```
Instead of the 3rd flaw (which may also be critical). Generator has incomplete history.

---

### 2. COUNTEREXAMPLE LOSS: Answer Reconsideration Evidence Limitation (Lines 135-138)

**File:** `/home/user/IMO25/code/agent_rlac.py`
**Lines:** 135-138
**Severity:** HIGH

#### Issue
The ANSWER RECONSIDERATION prompt only uses **last 5 counterexamples**, not all accumulated ones:

```python
def revise_solution(self, problem: str, previous_solution: Solution,
                   latest_criticism: Criticism,
                   criticism_history: List[Criticism]) -> Solution:
    ...
    if self.answer_reconsideration_requested:
        # Accumulate counterexamples for evidence
        counterexample_evidence = "\n".join([
            f"- {ce}" for ce in self.accumulated_counterexamples[-5:]  # ← BUG: [-5:] limits to last 5
        ])
```

**Problems:**
- If generator has received 15 counterexamples across rounds, only 5 are shown
- Evidence is **incomplete and potentially unrepresentative**
- Generator makes answer reconsideration decision with partial evidence
- After 5+ counterexamples, loses visibility into the first counterexamples which established the pattern

**Impact:** Generator reconstructing answer with only recent counterexample evidence, missing the breadth of evidence needed for truly informed reconsideration.

---

### 3. STRING FORMATTING: Unescaped Braces in f-strings (Lines 139-166)

**File:** `/home/user/IMO25/code/agent_rlac.py`
**Lines:** 139-166
**Severity:** MEDIUM (potential formatting corruption)

#### Issue
The ANSWER RECONSIDERATION prompt uses f-string with markdown bold syntax containing literal braces:

```python
strategy_instruction = f"""
### ANSWER RECONSIDERATION MODE - YOUR ANSWER MAY BE WRONG ###

**CRITICAL**: The critic has provided VALID counterexamples across multiple rounds.
This suggests your ANSWER (not just your proof) may be fundamentally incorrect.

**Evidence Summary**:
{counterexample_evidence}

**BEFORE continuing, answer these questions:**

1. **Are these counterexamples mathematically valid?**
```

**Potential Issue:** 
- While the code above looks OK, be careful with markdown/latex in f-strings
- If prompt construction adds curly braces for set notation, they can be misinterpreted
- Example: If counterexample is "Set k={1,2,3}", the brace `{` could cause issues

**Recommendation:** Use raw strings or escape braces carefully.

---

### 4. PARSING BUG: Flaw Dictionary Key Mismatch (Lines 417-429)

**File:** `/home/user/IMO25/code/agent_rlac.py`
**Lines:** 417-429
**Severity:** MEDIUM

#### Issue
The flaw parsing converts keys to lowercase but the parsing format expects specific casing:

```python
def _parse_criticism(self, response: str, iteration: int) -> Criticism:
    ...
    for line in flaw_text.split("\n"):
        if ":" in line:
            key, value = line.split(":", 1)
            flaw_dict[key.strip().lower()] = value.strip()  # ← Converts to lowercase

    if flaw_dict:
        flaws.append(Flaw(
            type=flaw_dict.get('type', 'unknown'),           # ← Expects lowercase 'type'
            severity=flaw_dict.get('severity', 'major'),     # ← Expects lowercase 'severity'
            description=flaw_dict.get('description', ''),    # ← Expects lowercase 'description'
            counterexample=flaw_dict.get('counterexample') if flaw_dict.get('counterexample', 'N/A') != 'N/A' else None,
            location=flaw_dict.get('location', 'unspecified')
        ))
```

**Problems:**
- The prompt specifies: `Type: `, `Severity: `, `Description: `, `Counterexample: `, `Location: ` (capitalized)
- Parser converts these to lowercase for dictionary keys
- But what if the LLM outputs slightly different format? Extra spaces, different casing?
- **No validation that all required keys were found** - silently uses defaults

**Example failure:**
```
FLAW_START
Type:counterexample       # Missing space after colon
Severity: critical
Description: ...
```
Would create empty dictionary for 'type:counterexample' (with colon), then fall back to 'unknown'

---

### 5. CONTEXT LOSS: Limited Latest Criticism Formatting (Lines 257-270)

**File:** `/home/user/IMO25/code/agent_rlac.py`
**Lines:** 257-270
**Severity:** MEDIUM

#### Issue
While `_format_latest_criticism()` shows more detail than history, it's still limited:

```python
def _format_latest_criticism(self, criticism: Criticism) -> str:
    """Format the latest criticism in detail."""
    if criticism.no_flaws_found:
        return "No flaws found - solution passed adversarial validation!"

    formatted = []
    for i, flaw in enumerate(criticism.flaws, 1):
        formatted.append(f"\nFLAW {i}: [{flaw.severity.upper()}] {flaw.type}")
        formatted.append(f"Description: {flaw.description}")
        if flaw.counterexample:
            formatted.append(f"Counterexample: {flaw.counterexample}")
        formatted.append(f"Location: {flaw.location}")

    return "\n".join(formatted)
```

**Problems:**
- Shows ALL latest flaws (good)
- But if counterexample is very long, it could exceed token limits
- No truncation protection for large counterexamples
- Description can be arbitrarily long, potentially bloating the revision prompt

**Impact:** For complex problems, the latest criticism could dominate the revision prompt, leaving little space for problem context or previous solution.

---

### 6. MESSAGE ASSEMBLY: No System Prompt in Generator (Lines 210-213)

**File:** `/home/user/IMO25/code/agent_rlac.py`
**Lines:** 210-213
**Severity:** LOW (design choice)

#### Issue
The generator never passes a system prompt to the LLM:

```python
response = self.llm.generate(
    prompt=prompt,
    reasoning_effort=self.reasoning_effort
    # ← No system_prompt parameter passed
)
```

**Context from GPTOSSClient.generate():**
```python
def generate(self, prompt: str, reasoning_effort: str = "high",
            system_prompt: str = None, timeout: int = 600) -> str:
    """
    Generate text using GPT-OSS API.
    
    Args:
        prompt: User prompt
        reasoning_effort: Reasoning level ("low", "medium", "high")
        system_prompt: Optional system prompt  # ← Available but not used
    ...
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
```

**Problem:**
- The GPTOSSClient supports system prompts but the generator doesn't use them
- Could improve response quality by setting system context (e.g., "You are an expert mathematician")
- Minor impact but inconsistent with best practices

---

### 7. FLOW BUG: Criticism Appended AFTER Check (Line 582)

**File:** `/home/user/IMO25/code/agent_rlac.py`
**Lines:** 506-511, 521-582
**Severity:** MEDIUM

#### Issue
Criticism is only appended to history AFTER being processed, not when first created:

```python
# Line 506-511: Call revise_solution with PREVIOUS criticism
solution = self.generator.revise_solution(
    problem=problem,
    previous_solution=solution,
    latest_criticism=criticism_history[-1],  # ← Uses LAST element
    criticism_history=criticism_history      # ← Passes full history
)

# Line 521: Attack the NEW solution
criticism = self.critic.adversarial_attack(
    problem=problem,
    solution=solution,
    attack_intensity=attack_intensity
)

# Line 557-582: Only AFTER checking do we append
else:  # criticism has flaws
    ...
    print(f"✗ CRITIC FOUND {len(criticism.flaws)} FLAW(S)")
    ...
    criticism_history.append(criticism)  # ← Appended HERE
```

**Flow Problem:**
When revise_solution is called on iteration 2:
- It receives `criticism_history[-1]` from iteration 0 (first attack)
- Iteration 1's criticism is NOT yet added to history when revise_solution constructs the prompt
- This means the revision prompt SKIPS iteration 1's feedback!

**Example Timeline:**
```
Iteration 1:
  - Generate solution 1
  - Attack produces criticism 1
  - criticism_history = [] → append criticism 1 → criticism_history = [crit1]

Iteration 2:
  - revise_solution(criticism_history=[], latest_criticism=None)  ← PROBLEM!
  - Actually receives: revise_solution(criticism_history=[crit1], latest_criticism=crit1) 
  
Wait, looking at line 509: latest_criticism=criticism_history[-1]
If criticism_history is empty on first iteration, this would IndexError!
```

Actually, let me recheck the flow...

---

### 8. CRITICAL FLOW BUG: Missing Criticism from First Attack (Lines 509-510, 582)

**File:** `/home/user/IMO25/code/agent_rlac.py`
**Severity:** CRITICAL

#### Analysis of Actual Flow:

**Iteration 1:**
- Line 504: `generate_initial_solution()` created
- Line 521-525: `adversarial_attack()` produces `criticism` object
- Line 532-555: Check if passed (no_flaws_found)
- Line 582: `criticism_history.append(criticism)` ← Criticism stored
- At end: `criticism_history = [Criticism_from_iteration_1]`

**Iteration 2:**
- Line 506-511: Call `revise_solution()` with:
  ```python
  latest_criticism=criticism_history[-1]  # ← Gets Criticism_1
  criticism_history=criticism_history      # ← Gets [Criticism_1]
  ```
- Generator formats and passes to generator
- Line 521: New attack produces `criticism` (Criticism_2)
- Line 582: `criticism_history.append(criticism)` ← Now: [Crit_1, Crit_2]

**This seems to work correctly** - but there's still the TRUNCATION BUG #1 that prevents full history from being visible.

---

### 9. INCONSISTENCY: Raw Response Storage vs. Parsing (Lines 401, 445)

**File:** `/home/user/IMO25/code/agent_rlac.py`
**Lines:** 393-447
**Severity:** MEDIUM (debugging/auditability issue)

#### Issue
The raw_response is stored but truncated in state machine:

From `_parse_criticism()`:
```python
return Criticism(
    no_flaws_found=len(flaws) == 0,
    flaws=flaws,
    raw_response=response,  # ← Full response stored
    iteration=iteration
)
```

But in `rlac_improvements.py`, the state machine truncates it:
```python
entry = VerdictHistoryEntry(
    ...
    attack_text=attack_result['full_attack'][:500] if attack_result else "",  # ← Truncated to 500 chars!
    ...
)
```

**Problem:**
- Full response stored in Criticism but truncated to 500 chars in VerdictHistoryEntry
- This mismatch makes debugging difficult
- If you need to re-parse a response later, the truncated version loses information

---

### 10. SOLUTION CONTENT NOT VALIDATED (No check in revise_solution)

**File:** `/home/user/IMO25/code/agent_rlac.py`
**Lines:** 210-220
**Severity:** MEDIUM

#### Issue
Generator response is directly wrapped in Solution without validation:

```python
response = self.llm.generate(
    prompt=prompt,
    reasoning_effort=self.reasoning_effort
)

return Solution(
    content=response,  # ← No validation! Could be empty, None, or garbage
    iteration=previous_solution.iteration + 1,
    timestamp=datetime.now().isoformat(),
    reward=0.0
)
```

**Problems:**
- If LLM returns empty string, None, or truncated response, it's still accepted
- Invalid solutions proceed to adversarial attack phase wasting compute
- No early detection of content generation failures
- rlac_improvements.py has validation pipeline but it's not integrated into agent_rlac.py

---

## Summary Table

| Issue # | Location | Line(s) | Type | Severity | Impact |
|---------|----------|---------|------|----------|--------|
| 1 | agent_rlac.py | 243-255 | Truncation | HIGH | Generator loses 3+ flaws and full counterexamples in history |
| 2 | agent_rlac.py | 135-138 | Truncation | HIGH | Answer reconsideration uses only last 5 counterexamples |
| 3 | agent_rlac.py | 139-166 | Format Risk | MEDIUM | Unescaped braces in f-strings could corrupt message |
| 4 | agent_rlac.py | 417-429 | Parsing | MEDIUM | Flaw parsing fragile to format variations |
| 5 | agent_rlac.py | 257-270 | Limits | MEDIUM | Latest criticism could bloat prompt without truncation |
| 6 | agent_rlac.py | 210-213 | Missing | LOW | No system prompt passed to generator |
| 7 | agent_rlac.py | 582 | Flow | MEDIUM | Criticism appended after use, skips iteration 1 details |
| 8 | agent_rlac.py | 509-510 | VERIFIED | N/A | Actually works, but #1 truncation still causes loss |
| 9 | agent_rlac.py vs rlac_improvements.py | 401, 445 vs 914 | Inconsistency | MEDIUM | Response truncated inconsistently |
| 10 | agent_rlac.py | 210-220 | Validation | MEDIUM | No validation of LLM response before use |

## Recommendations

**PRIORITY 1 (Fix immediately):**
- Issue #1: Pass full flaw details with counterexamples to generator
- Issue #2: Pass all accumulated counterexamples to answer reconsideration

**PRIORITY 2 (Important for robustness):**
- Issue #4: Add robust flaw parsing with format validation
- Issue #10: Validate solution content before proceeding

**PRIORITY 3 (Code quality):**
- Issue #3: Use raw strings or properly escape braces
- Issue #6: Add system prompt for generator

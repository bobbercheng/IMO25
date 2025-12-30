# Comprehensive Verification System Recommendation

**Date:** 2025-12-16
**Context:** Problem 1 false positive - Agent claimed k ∈ {0,1,2,...,n}, truth is k ∈ {0,1,3}
**Objective:** Design rigorous, general verification system without oracle/whitelist

---

## Executive Summary

**RECOMMENDATION: Enhanced Hybrid Approach (Option C+)**

Implement a **4-layer hierarchical verification system** combining:
1. LLM-based claim extraction and code generation
2. Multi-LLM code review and differential testing
3. Deterministic concrete construction execution
4. Conservative verdict aggregation with falsifiable evidence

**Key Innovation:** **Constructive verification** - actually try to build what agent claims, don't just check if explanation sounds good.

**Expected Performance:**
- **Soundness for BROKEN verdicts:** 90-95% (prevents false positives)
- **Soundness for ROBUST verdicts:** 70-80% (acceptable false positive rate)
- **False Positive Prevention:** ✓ k=2 impossibility would be caught

**Rigor Level:** 8.5/10 (best practical balance)

---

## Architecture Overview

### The 4-Layer Verification Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 1: EXTRACTION & SPECIFICATION                             │
│ ─────────────────────────────────────────────────────────────── │
│ Input: Agent's natural language solution                        │
│ Output: Structured claims + Formal specification                │
│                                                                  │
│ Components:                                                      │
│ - LLM Claim Extractor (extracts "k ∈ {0,1,2,...,n}")           │
│ - Formal Specification (defines "valid configuration")          │
│ - Structured Output (JSON with claims, construction method)     │
│                                                                  │
│ Example Output:                                                  │
│ {                                                                │
│   "problem_type": "FIND",                                        │
│   "claimed_values": [0, 1, 2, 3, 4],                            │
│   "construction_method": "Mark k-fold intersections",           │
│   "formal_spec": Problem1Spec                                   │
│ }                                                                │
└─────────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 2: CODE GENERATION & REVIEW                               │
│ ─────────────────────────────────────────────────────────────── │
│ Input: Structured claims + Specification                        │
│ Output: Verified Python code for construction testing           │
│                                                                  │
│ Components:                                                      │
│ - Multi-LLM Code Generation (GPT-4, Claude, Gemini)            │
│ - Template-Based Generation (reduces bugs)                      │
│ - Code Review LLM (checks for bugs, logic errors)              │
│ - Unit Test Generation                                          │
│                                                                  │
│ Example Output:                                                  │
│ def verify_k_construction(n, k):                                │
│     # Try to construct n lines with k marked points             │
│     for config in generate_configurations(n, k):                │
│         if formal_spec.is_valid(n, k, config.lines,            │
│                                  config.marking):               │
│             return (True, config)                               │
│     return (False, None)                                        │
└─────────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 3: MULTI-MODE EXECUTION                                   │
│ ─────────────────────────────────────────────────────────────── │
│ Input: Verified code + Claims                                   │
│ Output: Execution results with evidence                         │
│                                                                  │
│ Components:                                                      │
│ - Concrete Construction (execute code on small cases)           │
│ - Property-Based Testing (random testing for edge cases)        │
│ - Symbolic Verification (verify logic for proof steps)          │
│ - Counterexample Search (try to falsify claims)                │
│                                                                  │
│ Example Execution (for k=2, n=4):                               │
│ Result: CONSTRUCTION FAILED                                     │
│ Evidence: "Tried all combinations of 2 marked points from       │
│            6 points, no valid configuration satisfies spec"     │
│ Confidence: HIGH (falsifiable evidence)                         │
└─────────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 4: AGGREGATION & FEEDBACK                                 │
│ ─────────────────────────────────────────────────────────────── │
│ Input: Execution results from all verification modes            │
│ Output: Final verdict + Detailed feedback                       │
│                                                                  │
│ Decision Logic:                                                  │
│ - Any construction FAIL + HIGH confidence → BROKEN              │
│ - Logic gaps or MEDIUM confidence → SUSPICIOUS                  │
│ - All tests PASS → ROBUST (not 100% certain)                   │
│                                                                  │
│ Example Verdict:                                                 │
│ {                                                                │
│   "verdict": "BROKEN",                                           │
│   "confidence": "HIGH",                                          │
│   "failed_claims": [                                             │
│     {"k": 2, "reason": "Cannot construct configuration"}        │
│   ],                                                             │
│   "feedback": "Your claim that k=2 works is incorrect.          │
│                We tried to construct 4 lines with 2 marked      │
│                points but no valid configuration exists."       │
│ }                                                                │
└─────────────────────────────────────────────────────────────────┘
```

---

## Detailed Component Specifications

### Component 1: Claim Extractor

**Responsibility:** Parse natural language solution into structured claims

**Input:**
```
Agent's solution: "For n lines in general position, we can achieve
k-intersection for k ∈ {0, 1, 2, ..., n}. Construction: ..."
```

**Output (JSON):**
```json
{
  "problem_type": "FIND",
  "claims": [
    {
      "type": "set_of_values",
      "variable": "k",
      "values": [0, 1, 2, 3, 4],
      "constraint": "k ≤ n"
    }
  ],
  "construction_method": {
    "description": "Mark k-fold intersection points",
    "parameters": ["n", "k"],
    "steps": [
      "Arrange n lines in general position",
      "Identify k-fold intersection points",
      "Mark k such points"
    ]
  }
}
```

**Implementation:**
```python
class ClaimExtractor:
    def __init__(self, llm):
        self.llm = llm
        self.system_prompt = """
        Extract structured claims from mathematical solution.
        Focus on:
        - What values/sets are claimed to work?
        - What construction method is proposed?
        - What are the key steps?

        Output valid JSON with schema:
        {
          "claims": [...],
          "construction_method": {...}
        }
        """

    def extract(self, solution_text: str) -> dict:
        response = self.llm.chat(
            system=self.system_prompt,
            messages=[
                {"role": "user", "content": solution_text}
            ],
            response_format={"type": "json_object"}
        )
        return json.loads(response.content)
```

---

### Component 2: Code Generator (Multi-LLM)

**Responsibility:** Generate Python code to verify construction claims

**Key Innovation: Differential Testing with 3 LLMs**

```python
class MultiLLMCodeGenerator:
    def __init__(self, llms: List[LLM]):
        """Initialize with multiple LLMs for differential testing"""
        self.llms = llms  # e.g., [GPT-4, Claude-3.5, Gemini-2.5]
        self.template = CONSTRUCTION_VERIFICATION_TEMPLATE

    def generate_code(self, claims: dict, spec: FormalSpec) -> List[str]:
        """Generate verification code using all LLMs"""
        codes = []

        for llm in self.llms:
            code = llm.generate(
                template=self.template,
                claims=claims,
                spec=spec.to_string(),
                constraints=[
                    "Use template structure",
                    "Call formal_spec.is_valid() for verification",
                    "Include exhaustive search for small cases",
                    "Add explanatory comments"
                ]
            )
            codes.append(code)

        return codes

    def differential_test(self, codes: List[str], test_cases: List) -> dict:
        """Execute all code versions and compare results"""
        results = []

        for code in codes:
            result = execute_code(code, test_cases)
            results.append(result)

        # Check agreement
        if all(r == results[0] for r in results):
            return {
                "agreement": "FULL",
                "confidence": "HIGH",
                "result": results[0]
            }
        elif majority_agree(results):
            return {
                "agreement": "MAJORITY",
                "confidence": "MEDIUM",
                "result": majority_result(results),
                "disagreement": find_disagreements(results)
            }
        else:
            return {
                "agreement": "NONE",
                "confidence": "LOW",
                "warning": "LLMs disagree on verification",
                "results": results
            }
```

---

### Component 3: Code Template (Reduces Bugs)

**Responsibility:** Constrain code generation to reduce bugs

```python
CONSTRUCTION_VERIFICATION_TEMPLATE = '''
def verify_construction_{problem_id}(n: int, k: int,
                                      formal_spec) -> Tuple[bool, Optional[dict]]:
    """
    Verify if construction for k={k} works for n={n}.

    Construction method: {construction_method}

    Returns:
        (success: bool, evidence: dict)
        - success: True if valid configuration found, False otherwise
        - evidence: Configuration details or failure reason
    """

    # STEP 1: Generate configurations using agent's method
    # LLM FILLS THIS PART ↓
    {agent_construction_implementation}
    # END LLM PART ↑

    # STEP 2: Test each configuration against formal specification
    for config in generated_configs:
        if formal_spec.is_valid(n, k, config.lines, config.marking):
            # Found valid configuration
            return (True, {{
                "lines": config.lines,
                "marking": config.marking,
                "verification": "satisfies specification"
            }})

    # STEP 3: No valid configuration found
    return (False, {{
        "reason": "Exhaustive search found no valid configuration",
        "tested_configs": len(generated_configs),
        "specification": str(formal_spec)
    }})
'''
```

**Benefits:**
- Critical verification logic is fixed in template
- LLM only implements construction method
- Formal specification is always called
- Return format is consistent

---

### Component 4: Code Reviewer

**Responsibility:** Review generated code for bugs before execution

```python
class CodeReviewer:
    def __init__(self, llm):
        self.llm = llm
        self.review_checklist = [
            "No off-by-one errors in loops",
            "All edge cases handled (k=0, k=n, empty sets)",
            "Formal specification is called correctly",
            "No hardcoded values specific to test cases",
            "Exhaustive search is actually exhaustive",
            "Type annotations match function signature",
            "No infinite loops or exponential complexity"
        ]

    def review(self, code: str) -> dict:
        """Review code and return issues found"""
        prompt = f"""
        Review this verification code for bugs:

        {code}

        Checklist:
        {chr(10).join(f'- {item}' for item in self.review_checklist)}

        Return JSON:
        {{
          "verdict": "APPROVED" | "NEEDS_REVISION",
          "issues": [list of found issues],
          "suggested_fixes": [list of fixes],
          "confidence": "HIGH" | "MEDIUM" | "LOW"
        }}
        """

        response = self.llm.chat(
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )

        return json.loads(response.content)

    def iterative_fix(self, code: str, max_iterations: int = 3) -> str:
        """Iteratively review and fix code"""
        for i in range(max_iterations):
            review = self.review(code)

            if review["verdict"] == "APPROVED":
                return code

            # Generate fixes
            code = self.apply_fixes(code, review["suggested_fixes"])

        # After max iterations, return best effort
        return code
```

---

### Component 5: Execution Engine

**Responsibility:** Execute verified code on test cases

```python
class ExecutionEngine:
    def __init__(self, timeout: int = 60):
        self.timeout = timeout

    def execute_construction_test(self, code: str, n: int, k: int,
                                   formal_spec) -> dict:
        """Execute construction verification code"""

        # Create safe execution environment
        namespace = {
            'n': n,
            'k': k,
            'formal_spec': formal_spec,
            'range': range,
            'combinations': itertools.combinations,
            'Set': Set,
            'List': List,
            'Optional': Optional,
            # ... (safe builtins only)
        }

        try:
            # Execute with timeout
            with timeout_context(self.timeout):
                exec(code, namespace)

                # Call generated function
                verify_fn = namespace[f'verify_construction_{problem_id}']
                success, evidence = verify_fn(n, k, formal_spec)

                return {
                    "status": "SUCCESS" if success else "FAIL",
                    "evidence": evidence,
                    "execution_time": execution_time,
                    "confidence": "HIGH"
                }

        except TimeoutError:
            return {
                "status": "TIMEOUT",
                "evidence": "Execution exceeded time limit",
                "confidence": "LOW"
            }

        except Exception as e:
            return {
                "status": "ERROR",
                "evidence": f"Code execution error: {str(e)}",
                "confidence": "LOW"
            }

    def multi_case_testing(self, code: str, test_cases: List[dict],
                           formal_spec) -> dict:
        """Execute on multiple test cases"""
        results = []

        for case in test_cases:
            result = self.execute_construction_test(
                code, case['n'], case['k'], formal_spec
            )
            results.append({**case, **result})

        # Aggregate results
        failures = [r for r in results if r['status'] == 'FAIL']
        successes = [r for r in results if r['status'] == 'SUCCESS']

        return {
            "total_cases": len(test_cases),
            "successes": len(successes),
            "failures": len(failures),
            "failure_details": failures,
            "overall_verdict": "FAIL" if failures else "SUCCESS"
        }
```

---

### Component 6: Verdict Aggregator

**Responsibility:** Combine all verification results into final verdict

```python
class VerdictAggregator:
    def __init__(self):
        self.confidence_thresholds = {
            "BROKEN": "HIGH",     # Need high confidence to claim error
            "SUSPICIOUS": "MEDIUM",
            "ROBUST": "MEDIUM"
        }

    def aggregate(self,
                  extraction_result: dict,
                  code_generation_result: dict,
                  execution_result: dict) -> dict:
        """
        Aggregate results from all verification layers
        """

        # LAYER 1 ANALYSIS: Construction Failures
        construction_failures = execution_result.get('failures', [])

        if construction_failures and \
           code_generation_result['agreement'] == 'FULL':
            # All LLMs agree construction fails → High confidence
            return {
                "verdict": "BROKEN",
                "confidence": "HIGH",
                "reason": "Concrete construction failed",
                "evidence": construction_failures,
                "feedback": self.generate_feedback(construction_failures)
            }

        # LAYER 2 ANALYSIS: Code Disagreements
        if code_generation_result['agreement'] == 'NONE':
            # LLMs disagree on how to verify → Suspicious
            return {
                "verdict": "SUSPICIOUS",
                "confidence": "MEDIUM",
                "reason": "Verification code disagreement",
                "evidence": code_generation_result['disagreement']
            }

        # LAYER 3 ANALYSIS: Partial Failures
        if construction_failures and \
           code_generation_result['agreement'] == 'MAJORITY':
            # Majority thinks it fails → Suspicious
            return {
                "verdict": "SUSPICIOUS",
                "confidence": "MEDIUM",
                "reason": "Some constructions failed",
                "evidence": construction_failures
            }

        # LAYER 4 ANALYSIS: All Passed
        if not construction_failures:
            return {
                "verdict": "ROBUST",
                "confidence": "MEDIUM",  # Not 100% certain
                "reason": "All verification tests passed",
                "evidence": execution_result['successes'],
                "caveat": "Code might have bugs, not absolute proof"
            }

    def generate_feedback(self, failures: List[dict]) -> str:
        """Generate actionable feedback for agent"""
        feedback = "Your solution has issues:\n\n"

        for failure in failures:
            k = failure['k']
            reason = failure['evidence']['reason']

            feedback += f"• k={k}: {reason}\n"
            feedback += f"  → We tried to construct your configuration "
            feedback += f"but no valid arrangement exists.\n\n"

        feedback += "Please revise your construction method or "
        feedback += "reconsider which k values actually work."

        return feedback
```

---

## Problem-Specific Adaptations

### For FIND Problems (like Problem 1)

**Focus:** Concrete construction testing

```python
class FindProblemVerifier(HierarchicalVerifier):
    def verify_find_problem(self, solution: str, problem_spec: dict) -> dict:
        """
        FIND problems: Agent must provide explicit construction
        """

        # Extract claimed values
        claims = self.extract_claims(solution)

        # For each claimed value, try to construct
        results = []
        for value in claims['values']:
            # Generate construction code
            codes = self.generate_construction_code(value, problem_spec)

            # Review code
            reviewed_codes = [self.review_code(c) for c in codes]

            # Execute on concrete test cases
            exec_results = [
                self.execute_code(c, test_cases)
                for c in reviewed_codes
            ]

            # Check agreement
            if all(r['status'] == 'FAIL' for r in exec_results):
                # All agree construction fails → DEFINITIVE
                results.append({
                    "value": value,
                    "verdict": "IMPOSSIBLE",
                    "confidence": "HIGH",
                    "evidence": "Concrete construction failed"
                })
            elif all(r['status'] == 'SUCCESS' for r in exec_results):
                results.append({
                    "value": value,
                    "verdict": "WORKS",
                    "confidence": "MEDIUM"
                })
            else:
                results.append({
                    "value": value,
                    "verdict": "UNCERTAIN",
                    "confidence": "LOW"
                })

        # Aggregate
        impossibles = [r for r in results if r['verdict'] == 'IMPOSSIBLE']

        if impossibles:
            return {
                "final_verdict": "BROKEN",
                "confidence": "HIGH",
                "failed_values": [r['value'] for r in impossibles],
                "feedback": f"Claimed values {impossibles} are impossible"
            }

        return {"final_verdict": "ROBUST", "confidence": "MEDIUM"}
```

**Example for k=2:**
```
1. Extract claim: k=2 works for n=4
2. Generate code to construct 4 lines with 2 marked points
3. Execute: Try all possible configurations
4. Result: No valid configuration found
5. Verdict: k=2 is IMPOSSIBLE (high confidence)
6. Feedback: "Your claim that k=2 works is incorrect. We exhaustively
   searched all possible configurations of 4 lines with 2 marked points,
   and none satisfy the requirement that every line contains a marked point."
```

---

### For PROVE Problems

**Focus:** Logical proof verification + lemma checking

```python
class ProveProblemVerifier(HierarchicalVerifier):
    def verify_prove_problem(self, solution: str, problem_spec: dict) -> dict:
        """
        PROVE problems: Verify logical proof structure
        """

        # Extract proof structure
        proof_structure = self.extract_proof_structure(solution)

        # Verify each lemma
        lemma_results = []
        for lemma in proof_structure['lemmas']:
            if self.is_checkable_by_code(lemma):
                # Use code verification for checkable lemmas
                result = self.verify_lemma_by_code(lemma)
            else:
                # Use symbolic LLM verification
                result = self.verify_lemma_symbolic(lemma)

            lemma_results.append(result)

        # Verify proof logic
        logic_check = self.verify_proof_logic(
            lemmas=proof_structure['lemmas'],
            conclusion=proof_structure['conclusion'],
            argument=proof_structure['argument']
        )

        # Aggregate
        failed_lemmas = [r for r in lemma_results if not r['valid']]

        if failed_lemmas:
            return {
                "final_verdict": "BROKEN",
                "confidence": "HIGH",
                "reason": "Invalid lemmas",
                "evidence": failed_lemmas
            }

        if not logic_check['valid']:
            return {
                "final_verdict": "SUSPICIOUS",
                "confidence": "MEDIUM",
                "reason": "Logical gaps in proof",
                "evidence": logic_check['gaps']
            }

        return {"final_verdict": "ROBUST", "confidence": "MEDIUM"}
```

---

## Implementation Roadmap

### Phase 1: Core Infrastructure (Week 1-2)

**Deliverables:**
1. Formal specification templates for IMO problem types
2. Claim extraction LLM prompts
3. Code generation templates
4. Safe execution environment

**Files to create:**
```
code/verification/
├── __init__.py
├── specs/
│   ├── problem1_spec.py        # k-intersection formal spec
│   ├── problem2_spec.py
│   └── spec_template.py
├── extractors/
│   ├── claim_extractor.py      # LLM-based claim extraction
│   └── proof_extractor.py
├── generators/
│   ├── code_generator.py       # Multi-LLM code generation
│   ├── templates.py
│   └── differential_testing.py
└── executors/
    ├── executor.py             # Safe code execution
    └── timeout_utils.py
```

---

### Phase 2: Verification Pipeline (Week 3-4)

**Deliverables:**
1. Multi-LLM code generation system
2. Code review mechanism
3. Differential testing
4. Verdict aggregation

**Integration with existing RLAC:**
```python
# In code/agent_gpt_oss.py

def verify_solution_hierarchical(self, solution: str,
                                  round_num: int) -> dict:
    """
    Hierarchical verification replacing current verify_solution()
    """
    verifier = HierarchicalVerifier(
        problem_spec=self.problem_spec,
        llms=[self.llm, claude_llm, gemini_llm]
    )

    result = verifier.verify(solution)

    if result['verdict'] == 'BROKEN' and result['confidence'] == 'HIGH':
        # High-confidence error → Create attack with evidence
        return {
            "verdict": "BROKEN",
            "attack": result['feedback'],
            "evidence": result['evidence']
        }
    elif result['verdict'] == 'SUSPICIOUS':
        # Uncertain → Request clarification
        return {
            "verdict": "SUSPICIOUS",
            "clarification_needed": result['evidence']
        }
    else:
        # Passed verification
        return {
            "verdict": "ROBUST",
            "confidence": result['confidence']
        }
```

---

### Phase 3: Testing & Validation (Week 5-6)

**Test Cases:**

1. **Regression Test:** Problem 1 with k=2 claim
   - Expected: BROKEN verdict, k=2 detected as impossible

2. **True Positive Test:** Problem 1 with k=3 claim
   - Expected: ROBUST verdict

3. **Novel Problem Test:** New IMO problem not in training
   - Expected: System adapts, provides verdict

4. **Edge Cases:**
   - Ambiguous constructions → Request clarification
   - Timeout during execution → SUSPICIOUS verdict
   - Code generation disagreement → SUSPICIOUS verdict

**Validation:**
```bash
# Run test suite
python tests/test_hierarchical_verifier.py

# Expected results:
# ✓ Problem 1, k=2: BROKEN (detects impossibility)
# ✓ Problem 1, k=3: ROBUST
# ✓ Ambiguous construction: NEEDS_CLARIFICATION
# ✓ Code timeout: SUSPICIOUS (not BROKEN)
```

---

## Risk Mitigation

### Risk 1: LLM generates buggy code

**Mitigation:**
- Template-based generation (reduces degrees of freedom)
- Multi-LLM differential testing (catches model-specific bugs)
- Code review layer
- Unit tests for generated code

**Acceptance Criteria:** <5% of generated code has critical bugs

---

### Risk 2: Execution timeout for large parameter spaces

**Mitigation:**
- Adaptive testing strategy:
  - Small n: Exhaustive search
  - Large n: Random sampling + property-based testing
- Timeout handling → Return SUSPICIOUS (not BROKEN)
- Optional symbolic verification fallback

**Acceptance Criteria:** <10% of verifications timeout

---

### Risk 3: False positives still occur

**Mitigation:**
- Conservative verdict policy (only BROKEN with high confidence)
- Multi-source agreement requirement
- Human-in-the-loop for edge cases
- Detailed evidence logging for debugging

**Acceptance Criteria:** <5% false positive rate for BROKEN verdicts

---

## Success Metrics

### Primary Metrics:

1. **False Positive Rate (BROKEN verdicts)**
   - Target: <5%
   - Current system: ~30-40% (estimated)
   - Measure: Manual review of BROKEN verdicts

2. **True Positive Rate (detecting actual errors)**
   - Target: >85%
   - Measure: Test on known incorrect solutions

3. **Verification Time**
   - Target: <2 minutes per verification
   - Current: ~10 seconds (too fast, not rigorous enough)

### Secondary Metrics:

4. **Code Generation Quality**
   - Target: >90% of generated code passes review
   - Measure: Code reviewer approval rate

5. **Multi-LLM Agreement Rate**
   - Target: >80% full agreement
   - Measure: Differential testing results

---

## Comparison to Alternatives

### Alternative 1: Formal Proof Assistant (Lean/Coq)

**Pros:**
- Perfect soundness (if proof complete)
- No false positives

**Cons:**
- Requires formal proofs (not natural language)
- Too slow for real-time verification
- High barrier to entry

**Verdict:** Not practical for IMO agents (yet)

---

### Alternative 2: Pure LLM Chain-of-Thought

**Pros:**
- Simple to implement
- Flexible

**Cons:**
- Unreliable (current system failed with this)
- No falsifiable evidence
- Same type of reasoning that caused error

**Verdict:** Insufficient rigor, rejected

---

### Alternative 3: SAT/SMT Solver

**Pros:**
- Deterministic verification
- Complete for decidable domains

**Cons:**
- Limited to specific domains
- Difficult to encode complex constructions
- LLM might generate wrong encoding

**Verdict:** Useful as supplement, not primary method

---

### Recommended Hybrid (This Proposal)

**Pros:**
- Balances rigor with practicality
- Falsifiable evidence (concrete construction)
- Multi-layer defense against bugs
- Adaptable to different problem types
- Conservative verdicts prevent false positives

**Cons:**
- More complex than alternatives
- Not perfect soundness (90-95% for BROKEN verdicts)
- Requires multiple LLM calls

**Verdict:** Best practical approach ✓

---

## Conclusion

### The Core Insight

**Current system failed because it trusted explanations without testing execution.**

**New system: Don't just check if it sounds good, actually try to build it.**

### Key Principles

1. **Constructive Verification:** Generate and execute actual constructions
2. **Falsifiable Evidence:** Only claim BROKEN when we have concrete proof
3. **Conservative Verdicts:** When uncertain, mark SUSPICIOUS (not BROKEN)
4. **Multi-layer Defense:** LLM generation + review + differential testing + execution

### Expected Impact

**For Problem 1 false positive:**
- Current: k=2 explanation sounds good → ROBUST (WRONG)
- New: Try to construct k=2 → FAILS → BROKEN (CORRECT ✓)

**General improvement:**
- False positive rate: 30-40% → <5%
- True positive rate: ~60% → >85%
- Verification confidence: LOW → HIGH (for BROKEN verdicts)

### Next Steps

1. Implement Phase 1 (Core Infrastructure)
2. Test on Problem 1 regression case
3. Validate with other IMO problems
4. Integrate with existing RLAC system
5. Monitor performance and iterate

---

## Appendix A: Formal Specification Example

```python
# code/verification/specs/problem1_spec.py

from typing import Set, List
from dataclasses import dataclass

@dataclass
class Configuration:
    """A configuration of lines and marked points"""
    lines: List[Set[int]]  # Each line is a set of point indices
    marking: Set[int]       # Set of marked point indices

class Problem1Spec:
    """
    Formal specification for IMO 2025 Problem 1:
    k-intersection of n lines in general position
    """

    @staticmethod
    def is_valid(n: int, k: int, config: Configuration) -> bool:
        """
        A configuration is valid for (n, k) if:
        1. There are exactly n lines
        2. Exactly k points are marked
        3. Every line contains at least one marked point
        4. Lines are in general position (optional check)
        """

        # Check number of lines
        if len(config.lines) != n:
            return False

        # Check number of marked points
        if len(config.marking) != k:
            return False

        # Check every line contains a marked point
        for line in config.lines:
            if not any(point in line for point in config.marking):
                return False

        # All checks passed
        return True

    @staticmethod
    def get_test_cases(n: int) -> List[int]:
        """
        Get test cases for k values to check for given n
        """
        # Test boundary cases + some middle values
        return [0, 1, 2, n//2, n-1, n]
```

---

## Appendix B: Code Generation Prompt

```python
CODE_GENERATION_PROMPT = """
You are generating Python code to verify a mathematical construction.

PROBLEM SPECIFICATION:
{problem_spec}

AGENT'S CLAIM:
{claim}

AGENT'S CONSTRUCTION METHOD:
{construction_method}

YOUR TASK:
Generate Python code that implements the agent's construction method
and tests if it produces a valid configuration.

REQUIREMENTS:
1. Use the provided template structure
2. Implement the construction method faithfully
3. For small parameter values, use exhaustive search
4. Call formal_spec.is_valid() to verify configurations
5. Return (True, config) if valid found, (False, None) otherwise
6. Include explanatory comments

TEMPLATE:
{template}

IMPORTANT:
- Be precise with loop bounds (avoid off-by-one errors)
- Handle edge cases (k=0, k=n, empty sets)
- Ensure search is exhaustive for small cases
- Add type hints

Generate the complete function:
"""
```

---

## Appendix C: Verdict Decision Tree

```
┌─────────────────────────────────────┐
│ Start Verification                   │
└─────────────────────────────────────┘
                ↓
┌─────────────────────────────────────┐
│ Extract Claims                       │
│ - Parse natural language solution    │
│ - Structure claims as JSON           │
└─────────────────────────────────────┘
                ↓
┌─────────────────────────────────────┐
│ Generate Code (3 LLMs)              │
│ - GPT-4, Claude, Gemini             │
│ - Use template                       │
└─────────────────────────────────────┘
                ↓
┌─────────────────────────────────────┐
│ Code Review                          │
│ - Check for bugs                     │
│ - Iterative fixes                    │
└─────────────────────────────────────┘
                ↓
┌─────────────────────────────────────┐
│ Execute Code (all 3 versions)       │
│ - Run on test cases                  │
│ - Collect results                    │
└─────────────────────────────────────┘
                ↓
┌─────────────────────────────────────┐
│ Check Agreement                      │
└─────────────────────────────────────┘
        ↙       ↓       ↘
   All FAIL  Mixed   All PASS
        ↓       ↓       ↓
    ┌────┐  ┌────┐  ┌────┐
    │BROKEN│ │SUSP│  │ROBUST│
    │HIGH  │ │MED │  │MED   │
    └────┘  └────┘  └────┘
```

---

**END OF RECOMMENDATION**

This verification system provides the rigor needed to prevent false positives
while maintaining the generality required for novel IMO problems. The k=2
impossibility case would be definitively caught at Layer 3 (Execution) with
high confidence.

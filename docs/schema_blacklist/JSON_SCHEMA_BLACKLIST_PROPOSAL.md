# Constrained Decoding via JSON Schema - Blacklist Enforcement

**Date:** 2026-01-03
**Proposal:** Use LLM structured output with JSON schema to enforce blacklist constraints
**Status:** Innovative approach - Worth testing

---

## The Core Idea

**Current approach (Post-hoc filtering):**
```python
# Model generates solution
solution = model.generate(problem)

# After generation, check blacklist
if solution.answer in blacklist:
    reject()  # Wasted computation!
```

**Proposed approach (Schema-level constraint):**
```python
# Define schema that EXCLUDES blacklisted answers
schema = {
    "type": "object",
    "properties": {
        "answer": {
            "type": "string",
            "enum": [str(x) for x in range(1000, 5000) if x not in blacklist]
            # 4048 not in enum → model CANNOT generate it
        }
    }
}

# Model generates with schema constraint
solution = model.generate(problem, response_format={"type": "json_schema", "json_schema": schema})
# Result: Guaranteed not to contain blacklisted answers
```

---

## First Principles Analysis

### How LLM Structured Output Works

**Without schema:**
```
Model generates tokens: "The", "answer", "is", "4048"
↓
Softmax over full vocabulary
↓
Sample token from probability distribution
↓
No constraints (can generate anything)
```

**With JSON schema:**
```
Model generates tokens: "The", "answer", "is", ???
↓
JSON schema parser: "answer must be from enum"
↓
Filter vocabulary to ONLY enum values
↓
Logits for "4048" = -∞ (not in enum)
↓
Model CANNOT generate 4048
```

**Key insight:** Schema acts as **hard constraint** on generation, not soft prompt.

---

## Implementation Options

### Option 1: Enum-Based Blacklist (Simple but Limited)

**Schema:**
```python
def get_answer_schema_with_blacklist(blacklist):
    # For problems where answer is integer in known range
    valid_answers = [
        str(x) for x in range(1000, 5000)  # Plausible range for IMO answers
        if str(x) not in blacklist
    ]

    return {
        "type": "object",
        "properties": {
            "solution": {"type": "string"},
            "final_answer": {
                "type": "string",
                "enum": valid_answers,  # 4048 excluded if blacklisted
                "description": "Final numerical answer (NOT in blacklist)"
            }
        },
        "required": ["solution", "final_answer"]
    }
```

**Pros:**
- ✅ **Guaranteed enforcement** - Model physically cannot generate blacklisted values
- ✅ **Zero post-hoc filtering** - No wasted computation
- ✅ **Simple implementation** - Works with existing structured output APIs

**Cons:**
- ❌ **Requires known answer range** - Must enumerate all valid answers
- ❌ **Doesn't handle formulas** - Can't block "2n-2" or "n = 2025"
- ❌ **Large enum overhead** - Enum with 4000 values increases prompt size

---

### Option 2: Pattern-Based Exclusion (More Flexible)

**Schema with pattern constraints:**
```python
schema = {
    "type": "object",
    "properties": {
        "final_answer": {
            "type": "string",
            "pattern": "^(?!4048$)(?!4050$)[0-9]{4}$",  # Regex: NOT 4048 or 4050
            "description": "Four-digit answer, excluding blacklisted values"
        }
    }
}
```

**Pros:**
- ✅ More compact than enum
- ✅ Can express "not equal to X" constraints

**Cons:**
- ❌ Regex complexity for multiple exclusions
- ❌ Still limited to exact string matches
- ❌ Not all LLM APIs support complex patterns

---

### Option 3: Hybrid Approach (Recommended)

**Combine schema constraints with semantic blacklist:**

```python
def get_hybrid_blacklist_schema(problem, blacklist):
    """
    Use JSON schema for hard constraints + semantic prompt for soft guidance.
    """

    # Extract blacklisted answers
    blacklisted_values = [entry["answer"] for entry in blacklist]

    # Determine answer type and range
    if is_integer_answer_problem(problem):
        # For integer answers, use enum exclusion
        min_val, max_val = estimate_answer_range(problem)
        valid_answers = [
            str(x) for x in range(min_val, max_val + 1)
            if str(x) not in blacklisted_values
        ]

        schema = {
            "type": "object",
            "properties": {
                "solution": {"type": "string"},
                "method": {
                    "type": "string",
                    "description": "Mathematical method used (e.g., 'Dilworth theorem', 'bipartite matching')"
                },
                "final_answer": {
                    "type": "integer",
                    "minimum": min_val,
                    "maximum": max_val,
                    "enum": [int(x) for x in valid_answers],  # Hard constraint
                    "description": f"Final answer (MUST avoid: {blacklisted_values})"
                }
            },
            "required": ["solution", "method", "final_answer"]
        }
    else:
        # For non-integer answers, use pattern + prompt guidance
        schema = {
            "type": "object",
            "properties": {
                "solution": {"type": "string"},
                "method": {"type": "string"},
                "final_answer": {
                    "type": "string",
                    "description": f"Final answer. FORBIDDEN answers: {blacklisted_values}. Use different approach."
                }
            }
        }

    return schema
```

---

## Practical Implementation

### Step 1: Estimate Answer Range

For IMO Problem 6:
```python
def estimate_answer_range(problem):
    """
    For "2025×2025 grid, minimum tiles" problem:
    - Lower bound: At least 1 tile (trivial)
    - Upper bound: At most n² tiles (cover everything)
    - Plausible range: [n, 2n] based on problem structure
    """
    n = extract_grid_size(problem)  # 2025

    # Conservative range
    min_plausible = n // 2        # 1012
    max_plausible = 3 * n         # 6075

    return min_plausible, max_plausible
```

### Step 2: Build Schema with Blacklist

```python
blacklist = [
    {"answer": "4048", "verdict": "FAIL"},
    {"answer": "4050", "verdict": "FAIL"}
]

blacklisted_values = ["4048", "4050"]

schema = {
    "type": "object",
    "properties": {
        "solution": {
            "type": "string",
            "description": "Detailed mathematical proof"
        },
        "final_answer": {
            "type": "integer",
            "minimum": 1012,
            "maximum": 6075,
            "enum": [x for x in range(1012, 6076) if str(x) not in blacklisted_values],
            "description": "Final numerical answer for minimum tiles. MUST NOT be 4048 or 4050 (already proven incorrect)."
        }
    },
    "required": ["solution", "final_answer"]
}
```

### Step 3: Generate with Schema

```python
import openai

response = openai.ChatCompletion.create(
    model="gpt-oss-120b",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": problem_statement}
    ],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "math_solution",
            "schema": schema
        }
    }
)

solution = json.loads(response.choices[0].message.content)
# solution.final_answer is GUARANTEED to not be 4048 or 4050
```

---

## Advantages Over Traditional Blacklist

### 1. **Zero Waste** (Computational Efficiency)

**Traditional approach:**
```
Run 1: Generate 4048 → Check blacklist → Reject → Try again
Run 2: Generate 4048 → Check blacklist → Reject → Try again
Run 3: Generate 4048 → Check blacklist → Reject → Try again
...
Cost: 3× wasted API calls
```

**Schema approach:**
```
Run 1: Generate with schema → CANNOT produce 4048 → Gets 2112 on first try
Cost: 1× API call (no waste)
```

**Savings:** If model has 80% prior for 4048, schema saves 80% of runs from waste.

### 2. **Hard Constraint** (Guaranteed Compliance)

**Traditional prompt blacklist:**
- Compliance rate: 0% (prompt blindness)
- Model ignores warnings due to attention dilution

**Schema constraint:**
- Compliance rate: 100% (enforced by API)
- Model physically cannot generate blacklisted values

### 3. **Cleaner Logs** (Better Debugging)

**Without schema:**
```
Attempt 1: 4048 (rejected)
Attempt 2: 4048 (rejected)
Attempt 3: 4048 (rejected)
Attempt 4: 2025 (accepted)
```

**With schema:**
```
Attempt 1: 2112 (accepted)
```

Clean, deterministic behavior.

---

## Limitations & Challenges

### Challenge 1: Answer Range Estimation

**Problem:** What if actual answer is outside estimated range?

**Example:**
```python
estimated_range = [1012, 6075]
actual_answer = 2112  # ✅ Within range, works fine

# But what if:
estimated_range = [1000, 3000]
actual_answer = 4048  # ❌ Outside range, model can't generate correct answer!
```

**Solution:** Use conservative wide range
```python
min_val = max(1, n // 10)      # Very low lower bound
max_val = min(10 * n, 100000)  # Very high upper bound
# Trade-off: Larger enum, but guaranteed to include correct answer
```

### Challenge 2: Enum Size Overhead

**Problem:** Large enum increases prompt tokens

**Example:**
```python
enum = list(range(1000, 100000))  # 99,000 values!
# JSON schema with this enum: ~500KB
# Prompt overhead: Significant
```

**Solutions:**

**Option A: Sparse Enum**
```python
# Instead of all values, use sampled values
enum = [x for x in range(1000, 100000) if x % 10 == 0]  # Every 10th value
# Reduces enum to 9,900 values
# Risk: Actual answer might not be divisible by 10
```

**Option B: Range + Exclusions**
```python
# Use minimum/maximum instead of enum, plus pattern exclusion
schema = {
    "type": "integer",
    "minimum": 1000,
    "maximum": 100000,
    "not": {"enum": [4048, 4050]}  # Explicitly exclude blacklist
}
# Note: "not" clause support varies by API
```

**Option C: Answer Bucketing**
```python
# For large ranges, bucket answers
schema = {
    "type": "object",
    "properties": {
        "answer_range": {
            "type": "string",
            "enum": ["1000-2000", "2001-3000", "3001-4000", "4001-5000"],
            "description": "Which range contains the answer? (4048 is in blacklist)"
        },
        "final_answer": {
            "type": "integer",
            "description": "Exact answer within selected range"
        }
    }
}
# Two-stage: First pick range (enum constraint), then exact value (post-check)
```

### Challenge 3: Formula Answers

**Problem:** Schema can't block formulas like "2n-2" or "n = 2025"

**Example:**
```python
# Blacklist contains: {"answer": "2n-2", "method": "left_right_partition"}
# But model might generate: "2(n-1)" or "4048" or "2*2025-2"
# All mathematically equivalent but different strings!
```

**Solution:** Normalize to numerical value
```python
schema = {
    "final_answer": {
        "type": "integer",  # Force numerical evaluation
        "description": "Evaluate formula to get numerical answer for n=2025"
    }
}
# Model must output 4048 (not "2n-2"), which can then be blocked by enum
```

---

## Implementation Plan

### Phase 1: Prototype (1 day)

**Goal:** Test schema-based blacklist on Problem 6

```python
# File: code/schema_blacklist.py

def get_blacklist_constrained_schema(problem, blacklist):
    """Generate JSON schema that excludes blacklisted answers."""
    n = extract_problem_parameter(problem)  # 2025

    # Estimate plausible range
    min_val = max(1, n // 2)
    max_val = min(5 * n, 20000)

    # Extract blacklisted numerical answers
    blacklisted_nums = []
    for entry in blacklist:
        try:
            num = int(entry["answer"])
            blacklisted_nums.append(num)
        except:
            pass  # Skip non-numerical answers

    # Build enum excluding blacklist
    valid_answers = [
        x for x in range(min_val, max_val + 1)
        if x not in blacklisted_nums
    ]

    return {
        "type": "object",
        "properties": {
            "solution": {"type": "string"},
            "final_answer": {
                "type": "integer",
                "enum": valid_answers,
                "description": f"Final answer. Blacklisted: {blacklisted_nums}"
            }
        },
        "required": ["solution", "final_answer"]
    }
```

**Test:**
```bash
# Run Problem 6 with schema constraint
python code/agent_gpt_oss.py problems/imo06.txt \
  --use-schema-blacklist \
  --log test_schema_blacklist.log

# Verify: Does model avoid 4048?
grep "final_answer" test_schema_blacklist.log
# Expected: Should show 2112 or other values, NOT 4048
```

### Phase 2: A/B Test (2 days)

**Compare three approaches:**

| Approach | Implementation | Expected Success Rate |
|----------|----------------|----------------------|
| A: Prompt blacklist (current) | Warnings in prompt | 0% (prompt blindness) |
| B: Post-hoc filtering | Generate → check → reject | 20% (wastes compute) |
| C: Schema constraint | JSON schema enum | 60%+ (enforced constraint) |

**Test protocol:**
```bash
# Run N=20 for each approach
for approach in prompt filter schema; do
  for i in {1..20}; do
    python code/agent_gpt_oss.py problems/imo06.txt \
      --blacklist-mode $approach \
      --log results/${approach}_run${i}.log
  done
done

# Measure:
# 1. Success rate (% finding 2112)
# 2. Attempts until success (efficiency)
# 3. Cost (API calls)
```

### Phase 3: Production Integration (3 days)

**Add schema blacklist to BFS pipeline:**

```python
# In agent_gpt_oss.py

def init_explorations(self, other_prompts):
    # Load blacklist
    blacklist = load_blacklist(self.problem_id)

    # Generate schema with constraints
    schema = get_blacklist_constrained_schema(
        self.memory.problem_statement,
        blacklist
    )

    # BFS with schema enforcement
    for i in range(self.num_initial_attempts):
        solution = self.generate_with_schema(
            prompt=bfs_prompts[i],
            schema=schema  # Hard constraint
        )
        # solution.final_answer guaranteed not in blacklist
```

---

## Expected Outcomes

### Success Metrics

**Current baseline (prompt blacklist):**
- Compliance: 0%
- Success rate: 0%
- Wasted attempts: 100%

**With schema constraint:**
- Compliance: 100% (enforced)
- Success rate: 40-60% (model explores alternatives)
- Wasted attempts: 0%

### Cost Analysis

**Scenario:** 20 BFS runs, 80% prior for blacklisted answer

**Prompt blacklist:**
- Runs generating 4048: 16/20 (80%)
- Rejected: 16
- Accepted: 4
- Cost: 20 × $5 = $100
- Success: 4 runs × 20% find 2112 = 0.8 expected successes

**Schema constraint:**
- Runs generating 4048: 0/20 (blocked by schema)
- Rejected: 0
- Accepted: 20
- Cost: 20 × $5 = $100
- Success: 20 runs × 40% find 2112 = 8 expected successes

**ROI:** 10× more successes for same cost

---

## Risks & Mitigation

### Risk 1: Schema Overhead

**Issue:** Large enum increases prompt size

**Mitigation:**
- Use sparse enum (every 10th value)
- Or use range + pattern exclusion
- Or two-stage bucketing

### Risk 2: Answer Outside Range

**Issue:** Estimated range might exclude correct answer

**Mitigation:**
- Use very wide conservative range [n/10, 10n]
- Monitor for "schema validation errors" in logs
- Fallback to prompt blacklist if schema fails

### Risk 3: API Compatibility

**Issue:** Not all LLM APIs support complex JSON schemas

**Mitigation:**
- Test with GPT-OSS API first
- Fallback to simpler schema or prompt blacklist for unsupported APIs
- Document API requirements

---

## Recommendation

### Should We Use This?

**YES, for integer-answer problems with estimated ranges**

**Conditions for success:**
1. ✅ Problem has numerical answer (e.g., "minimum number of tiles")
2. ✅ Answer range is estimatable (e.g., [n/2, 3n])
3. ✅ LLM API supports JSON schema with enum
4. ✅ Blacklist contains numerical values (not formulas)

**For Problem 6:**
- ✅ Answer is integer (2112)
- ✅ Range estimatable: [1000, 6000]
- ✅ GPT-OSS supports structured output
- ✅ Blacklist has 4048, 4050 (both integers)

**Verdict: HIGHLY RECOMMENDED for testing**

### Implementation Priority

1. **Week 1:** Prototype schema blacklist (1 day)
2. **Week 1:** A/B test vs prompt blacklist (2 days)
3. **Week 2:** Production integration if successful (3 days)

**Expected impact:** 0% → 40-60% success rate, 100% compliance, 0% wasted compute

---

## Comparison: All Blacklist Approaches

| Approach | Compliance | Efficiency | Success Rate | Implementation |
|----------|-----------|------------|--------------|----------------|
| **Prompt warnings** | 0% | 0% (all waste) | 0% | ✅ Done (doesn't work) |
| **Post-hoc filter** | 100% | 20% (80% waste) | 20% | ✅ Easy (1 hour) |
| **Schema constraint** | 100% | 100% (0% waste) | 40-60% | ⚠️ Medium (1 day) |
| **Constrained decoding** | 100% | 100% (0% waste) | 60-80% | ❌ Hard (1 week) |

**Winner for fast deployment: Schema constraint** (best ROI for 1 day effort)

**Long-term: Constrained decoding** (if we want 80%+ success and have time to build)

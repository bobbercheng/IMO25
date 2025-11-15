# Remaining Root Causes and Additional Indicators

## Summary of Current State

### ✅ Applied to code/agent_gpt_oss.py
1. reasoning_effort: "high" → "low"
2. repetition_penalty: REMOVED

### ❌ NOT YET Applied to code/agent_gpt_oss.py
The following improvements from the "new version" (shared code) are NOT in current code/agent_gpt_oss.py:
- Self-improvement step
- Multi-stage verification (5 consecutive successes)
- 10-error early termination
- Memory/resume capability

---

## Root Causes - Detailed Status

### ROOT CAUSE #1: Reasoning Efficiency ⚠️  PARTIALLY ADDRESSED

**Original Problem:**
- 122 content truncations in 10 iterations (12+ per iteration)
- Excessive exploratory reasoning
- Output frequently exceeded max length

**What We Fixed:**
✅ reasoning_effort: "high" → "low"

**What Remains Unfixed:**
❌ No explicit output length monitoring
❌ No progressive summarization
❌ No automatic content pruning

**Additional Indicators Needed:**
```python
# In monitor_agent_progress.py - ADD:

1. Output Length Tracking
   - Track solution length over time
   - Detect if solutions are growing unbounded
   - Alert if average length > 10KB

2. Truncation Pattern Analysis
   - Track WHERE truncations happen (reasoning vs final output)
   - Detect if truncations are in same section repeatedly
   - Alert if truncations increasing over iterations

3. Content Density Metrics
   - Track ratio of math symbols to total text
   - Low ratio = too much exploration, not enough content
   - Alert if ratio < 20%
```

**Suggested Monitoring:**
```python
# Add to AgentProgressMonitor class
def track_output_length(self, content):
    """Track solution length patterns."""
    for match in re.finditer(r'Corrected solution:.*?"([^"]*)"', content, re.DOTALL):
        solution = match.group(1)
        if solution:
            length = len(solution)
            self.metrics['solution_lengths'].append(length)

            # Alert if growing unbounded
            if len(self.metrics['solution_lengths']) >= 3:
                recent = self.metrics['solution_lengths'][-3:]
                if all(recent[i] < recent[i+1] for i in range(2)):
                    # 3 consecutive increases
                    growth_rate = (recent[-1] - recent[0]) / recent[0]
                    if growth_rate > 0.5:  # 50% growth
                        return "⚠️  Solution length growing rapidly"
```

**Early Warning Signs:**
- Solution length doubling each iteration
- Truncations still > 3 per iteration
- Content density < 20% (too much text, not enough math)

---

### ROOT CAUSE #2: Output Formatting ❌ NOT ADDRESSED

**Original Problem:**
- 52 empty solutions (empty string "")
- Inconsistent formatting
- Missing required sections (Summary, Detailed Solution)

**What We Fixed:**
❌ NOTHING - Same prompts, no validation

**What Remains Unfixed:**
❌ No format validation before sending to verifier
❌ No template enforcement
❌ No empty output prevention
❌ No structured output parser

**Additional Indicators Needed:**
```python
# In monitor_agent_progress.py - ADD:

1. Format Compliance Score
   - Check for required sections
   - Count missing sections
   - Alert if < 80% compliance

2. Empty Solution Detection
   - Track consecutive empty solutions
   - Alert if > 2 consecutive empties
   - Suggest format validation fix

3. Structure Quality Metrics
   - Check if has "### Summary ###"
   - Check if has "### Detailed Solution ###"
   - Check if has TeX math ($ symbols)
   - Check if has verdict statement
```

**Suggested Monitoring:**
```python
def validate_solution_format(self, solution):
    """Validate solution has required structure."""
    issues = []

    # Required sections
    required = [
        "### Summary ###",
        "Verdict",
        "Method Sketch",
        "### Detailed Solution ###"
    ]

    missing = [sec for sec in required if sec not in solution]
    if missing:
        issues.append(f"Missing sections: {', '.join(missing)}")

    # Should have TeX math
    if "$" not in solution:
        issues.append("No TeX mathematics found")

    # Should have reasonable length
    if len(solution) < 200:
        issues.append(f"Too short: {len(solution)} chars")

    # Calculate compliance score
    compliance = (len(required) - len(missing)) / len(required)

    return compliance, issues
```

**Early Warning Signs:**
- Empty solution rate > 20%
- Format compliance < 60%
- Missing required sections in >50% of solutions
- No TeX math in solutions

**Suggested Fix (to add later):**
```python
# Add to agent before verification
def enforce_format(solution):
    """Enforce proper format before verification."""
    # Check format
    is_valid, errors = validate_format(solution)

    if not is_valid:
        # Regenerate with format instructions
        format_prompt = f"""
        Your solution has format errors:
        {chr(10).join(f'- {e}' for e in errors)}

        Please regenerate following this template:

        ### Summary ###
        **a. Verdict:** [Complete/Partial solution statement]
        **b. Method Sketch:** [High-level approach]

        ### Detailed Solution ###
        [Step-by-step proof with TeX math]
        """
        # Regenerate...

    return solution
```

---

### ROOT CAUSE #3: Proof Rigor ❌ NOT ADDRESSED

**Original Problem:**
- Informal reasoning
- Justification gaps
- Failed IMO verification standards
- 112 verification failures

**What We Fixed:**
❌ NOTHING - Identical prompts

**What Remains Unfixed:**
❌ No rigor enhancement prompts
❌ No proof structure templates
❌ No formal verification checklist
❌ No lemma/theorem enforcement

**Additional Indicators Needed:**
```python
# In monitor_agent_progress.py - ADD:

1. Rigor Indicators from Bug Reports
   - Count "Justification Gap" mentions
   - Count "Critical Error" mentions
   - Track if same gaps repeat

2. Proof Structure Metrics
   - Count number of lemmas defined
   - Count number of cases analyzed
   - Check if has "proof by induction/contradiction"
   - Check if conclusions are stated clearly

3. Verification Failure Patterns
   - Track most common failure reasons
   - Detect if stuck in same error loop
   - Alert if same bug report for 3+ iterations
```

**Suggested Monitoring:**
```python
def analyze_bug_reports(self):
    """Analyze verification bug reports for patterns."""
    gap_count = 0
    error_count = 0
    repeated_issues = defaultdict(int)

    for bug in self.metrics['bug_reports']:
        # Count types
        if "Justification Gap" in bug:
            gap_count += 1
        if "Critical Error" in bug:
            error_count += 1

        # Extract specific issues
        for line in bug.split('\n'):
            if "Location:" in line or "Issue:" in line:
                repeated_issues[line] += 1

    # Find repeated issues (appearing 3+ times)
    stuck_on = [issue for issue, count in repeated_issues.items() if count >= 3]

    return {
        'justification_gaps': gap_count,
        'critical_errors': error_count,
        'stuck_on_issues': stuck_on
    }
```

**Early Warning Signs:**
- Justification gaps > 70% of verification failures
- Same issue reported 3+ times (stuck in loop)
- No formal proof structures (lemmas, cases)
- Verification always fails for same reason

**Suggested Fix (to add later):**
```python
# Add rigor enhancement to prompts
rigor_prompt = """
Before finalizing, include a "Proof Checklist":

**Proof Checklist:**
□ All definitions stated clearly
□ All assumptions explicitly listed
□ Each lemma proven before use
□ All cases enumerated and covered
□ Each step follows logically from previous
□ Final answer clearly stated
□ All TeX math properly formatted

Confirm each item is satisfied in your proof.
"""

# Add to system prompt or as follow-up
```

---

### ROOT CAUSE #4: Error Recovery ❌ NOT IN code/agent_gpt_oss.py

**Original Problem:**
- 112 verification failures
- No learning between iterations
- Infinite correction loops
- No effective recovery strategy

**What We Fixed:**
❌ NOT in code/agent_gpt_oss.py (but exists in the new version shared)

**What Remains Unfixed in current code:**
❌ No self-improvement step
❌ No multi-stage verification
❌ No 5-consecutive-success requirement
❌ No 10-error early termination
❌ No memory/resume capability

**These ARE in the new version but NOT in code/agent_gpt_oss.py**

**Additional Indicators Needed:**
```python
# In monitor_agent_progress.py - ADD:

1. Learning Progress Detection
   - Track if bug reports are getting shorter (improving)
   - Track if correct count is increasing
   - Detect if same mistakes repeating

2. Recovery Effectiveness
   - Track time to first verification pass
   - Track time between consecutive passes
   - Alert if no improvement for 5+ iterations

3. Stuck Detection
   - Detect if error count not decreasing
   - Detect if same verification failure 5+ times
   - Alert "stuck in loop" with specific issue
```

**Suggested Monitoring:**
```python
def detect_stuck_pattern(self):
    """Detect if agent is stuck making same mistake."""
    if len(self.metrics['bug_reports']) < 5:
        return None

    recent_bugs = self.metrics['bug_reports'][-5:]

    # Check if all recent bugs are very similar
    # (using simple substring matching)
    common_phrases = set()
    for bug in recent_bugs:
        # Extract key phrases
        phrases = re.findall(r'(Missing|Invalid|Error in|Gap in) \w+', bug)
        common_phrases.update(phrases)

    # If same phrases appear in all 5 bugs
    stuck_indicators = []
    for phrase in common_phrases:
        if sum(1 for bug in recent_bugs if phrase in bug) >= 4:
            stuck_indicators.append(phrase)

    if stuck_indicators:
        return f"⚠️  STUCK: Repeating same errors: {', '.join(stuck_indicators)}"

    return None
```

**Early Warning Signs:**
- No verification passes after 10 iterations
- Error count not decreasing
- Same bug report for 5+ consecutive iterations
- No improvement in correct count

---

## Recommended Enhancements to monitor_agent_progress.py

### 1. Format Validation Indicators

Add to `update_metrics()`:
```python
# Track format compliance
for match in re.finditer(r'Corrected solution:.*?"([^"]*)"', content, re.DOTALL):
    solution = match.group(1)
    if solution:
        compliance, issues = validate_solution_format(solution)
        self.metrics['format_compliance_scores'].append(compliance)
        if issues:
            self.metrics['format_issues'].extend(issues)
```

Add to `calculate_health_score()`:
```python
# Penalty for poor format compliance
if len(self.metrics['format_compliance_scores']) > 0:
    avg_compliance = sum(self.metrics['format_compliance_scores']) / len(self.metrics['format_compliance_scores'])

    if avg_compliance < 0.5:  # <50% compliance
        score -= 20
        reasons.append(f"❌ Low format compliance: {avg_compliance:.0%}")
    elif avg_compliance < 0.8:  # <80% compliance
        score -= 10
        reasons.append(f"⚠️ Moderate format compliance: {avg_compliance:.0%}")
    else:
        reasons.append(f"✅ Good format compliance: {avg_compliance:.0%}")
```

---

### 2. Rigor Indicators

Add to `update_metrics()`:
```python
# Track verification failure reasons
for match in re.finditer(r'Bug report:(.*?)(?:>>>|$)', content, re.DOTALL):
    bug = match.group(1).strip()
    if bug:
        self.metrics['bug_reports'].append(bug)

        # Count types
        if "Justification Gap" in bug:
            self.metrics['justification_gaps'] += 1
        if "Critical Error" in bug:
            self.metrics['critical_errors'] += 1
```

Add to dashboard:
```python
# Rigor Metrics
if self.metrics['bug_reports']:
    total_bugs = len(self.metrics['bug_reports'])
    gap_rate = self.metrics['justification_gaps'] / max(total_bugs, 1)
    error_rate = self.metrics['critical_errors'] / max(total_bugs, 1)

    print(f"{'RIGOR METRICS:':<20}")
    print(f"  Justification Gaps: {self.metrics['justification_gaps']} ({gap_rate:.0%})")
    print(f"  Critical Errors: {self.metrics['critical_errors']} ({error_rate:.0%})")

    # Check if stuck
    stuck = detect_stuck_pattern()
    if stuck:
        print(f"  {stuck}")
```

---

### 3. Recovery Progress Indicators

Add to `update_metrics()`:
```python
# Track bug report lengths (shorter = improving)
for match in re.finditer(r'Bug report:(.*?)(?:>>>|$)', content, re.DOTALL):
    bug = match.group(1).strip()
    self.metrics['bug_report_lengths'].append(len(bug))
```

Add to `calculate_health_score()`:
```python
# Green flag: Bug reports getting shorter (improving)
if len(self.metrics['bug_report_lengths']) >= 3:
    recent_lengths = self.metrics['bug_report_lengths'][-3:]
    if all(recent_lengths[i] > recent_lengths[i+1] for i in range(2)):
        # 3 consecutive decreases
        score += 10
        reasons.append("✅ Bug reports getting shorter (improving)")
```

---

## Priority for Adding Indicators

### 🔴 HIGH PRIORITY (Add Immediately)

1. **Format Compliance Tracking**
   - Most likely to provide early warning
   - Easy to detect and measure
   - Direct correlation with empty solution problem

2. **Bug Report Pattern Analysis**
   - Detects if stuck in loop
   - Identifies specific issues blocking progress
   - Can suggest targeted fixes

3. **Solution Length Monitoring**
   - Detects runaway generation early
   - Complements truncation tracking
   - Easy to implement

### 🟡 MEDIUM PRIORITY (Add Soon)

4. **Rigor Metrics (Gap vs Error ratio)**
   - Helps diagnose proof quality issues
   - Indicates if problem is rigor vs logic
   - Guides improvement strategy

5. **Learning Progress Indicators**
   - Shows if corrections are helping
   - Detects improvement trends
   - Motivates continuing vs stopping

### 🟢 LOW PRIORITY (Nice to Have)

6. **Content Density Metrics**
   - Interesting but less actionable
   - Requires more complex parsing
   - Lower correlation with success

---

## Implementation Plan

### Phase 1: Update monitor_agent_progress.py (Now)
```bash
# Add high-priority indicators:
1. Format compliance tracking
2. Bug report pattern analysis
3. Solution length monitoring
4. Enhanced dashboard display
```

### Phase 2: Test with Current Code (Next)
```bash
# Run test with enhanced monitoring:
python agent_gpt_oss.py problems/imo01.txt --log test.log &
python monitor_agent_progress.py test.log --interval 60

# Look for new indicators after 3 hours
```

### Phase 3: Add Fixes Based on Indicators (Later)
```bash
# Based on what indicators show:
- If format compliance <60% → Add format validation
- If rigor gaps >70% → Add rigor enhancement prompts
- If stuck on same issue → Add targeted correction
```

---

## Expected Impact

With enhanced monitoring:

**Before:**
- Can only see: truncations, empty solutions, pass rate
- Limited ability to diagnose WHY it's failing

**After:**
- Can see: format compliance, rigor metrics, stuck patterns
- Can diagnose SPECIFIC issues:
  - "Stuck on justification gaps" → Need rigor prompts
  - "Format compliance 40%" → Need format validation
  - "Bug reports not improving" → Need better correction

**Result:**
- More actionable insights within 3 hours
- Can identify specific fixes needed
- Better prediction of what will help

---

## Summary Table

| Root Cause | Status in Code | Indicators Available | Indicators Needed | Priority |
|------------|----------------|---------------------|-------------------|----------|
| **#1 Efficiency** | ⚠️ Partial | Truncations | Length growth, density | 🔴 High |
| **#2 Formatting** | ❌ None | Empty count | Compliance score, validation | 🔴 High |
| **#3 Rigor** | ❌ None | Pass rate | Gap/error ratio, patterns | 🟡 Medium |
| **#4 Recovery** | ❌ None | Iterations | Learning progress, stuck detection | 🟡 Medium |

---

## Next Steps

1. ✅ Update monitor_agent_progress.py with high-priority indicators
2. ⏳ Test enhanced monitoring on current code
3. ⏳ Document what new indicators reveal
4. ⏳ Add targeted fixes based on indicator insights
5. ⏳ Iterate until success rate reaches 50-70%

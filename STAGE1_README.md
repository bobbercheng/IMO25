# Stage 1: Automated Error Categorization & Template Generation

**Purpose**: Validate that prescriptive feedback improves proof quality before investing 2 days in Phase 2 implementation.

**Approach**: Use GPT-OSS-120B to automatically analyze Phase A validation errors, create error taxonomy, and generate fix templates.

---

## Quick Start

```bash
# Run Stage 1 analysis on Phase A validation logs
python stage1_error_analysis.py \
  --logs run_log_gpt_oss/memory_phase1_validation_p1.log \
         run_log_gpt_oss/mcts_phase1_validation_p1.log \
  --output stage1_results.json
```

**Expected Runtime**: 20-40 minutes (depends on GPT-OSS API speed)
**Expected Cost**: $2-5 (3-5 GPT-OSS calls with HIGH reasoning)

---

## What It Does

### Step 1: Extract Errors (2-3 minutes)
- Reads Phase A validation log files
- Extracts all verification errors:
  - Critical Errors (breaks logical chain)
  - Justification Gaps (missing rigor)
  - Construction Failures (coverage issues)
  - Other Errors
- Deduplicates and counts

**Expected Output**:
```
[SUMMARY] Total unique errors extracted:
  Critical Errors: 15-25
  Justification Gaps: 10-20
  Construction Failures: 5-10
  Other Errors: 3-8
  TOTAL: 35-60
```

### Step 2: Categorize Errors (10-15 minutes)
- Feeds all errors to GPT-OSS-120B with HIGH reasoning
- LLM analyzes patterns and creates taxonomy
- Returns 5-10 error categories ranked by frequency

**Expected Output**:
```json
{
  "categories": [
    {
      "name": "Slope Constraint Violation",
      "description": "Lines claimed as 'sunny' have prohibited slopes (0, -1, or ∞)",
      "frequency": 8,
      "root_cause": "Construction doesn't verify slope constraints"
    },
    {
      "name": "Incomplete Coverage Proof",
      "description": "Construction doesn't prove all points are covered",
      "frequency": 6,
      "root_cause": "Missing case analysis for edge points"
    }
  ]
}
```

### Step 3: Generate Fix Templates (5-10 minutes)
- For each error category, GPT-OSS generates prescriptive template
- Templates convert errors into TODO-style repair plans
- Format: Context + Required Actions + Verification Checklist

**Example Template**:
```
PRESCRIPTIVE REPAIR PLAN for Slope Constraint Violation:

**Context**: Your construction claims line ℓ_c is sunny, but for c=3
the slope equals -1 (prohibited).

**Required Actions**:
- [ ] CRITICAL: In Section 2.2, replace ℓ_c definition for c≥3
- [ ] CRITICAL: Choose slope formula ensuring -(c-2) ≠ {0, -1, ∞}
- [ ] CRITICAL: Add explicit slope verification: "For c≥3, -(c-2) < -1"
- [ ] POLISH: Add table showing slopes for c=3,4,5 as examples

**Verification Checklist**:
- [ ] Verify slope formula: -(c-2) ≠ -1 for all c≥3
- [ ] Verify line equation passes through required points
- [ ] Re-run coverage proof with new line definition
```

### Step 4: Test Top 3 Templates (5-10 minutes)
- Applies each template to sample errors
- GPT-OSS evaluates:
  - **Applicability**: Does template fit the error?
  - **Specificity**: Are actions concrete enough? (1-10)
  - **Actionability**: Can an LLM follow them? (1-10)
  - **Completeness**: Covers all aspects? (1-10)

**Success Criteria**:
- ≥2/3 templates tested
- Avg Specificity ≥ 6.0
- Avg Actionability ≥ 6.0
- Avg Completeness ≥ 6.0

---

## Output File Structure

The script saves `stage1_results.json` with:

```json
{
  "error_extraction": {
    "log_files": ["..."],
    "total_errors": 45,
    "by_type": {
      "critical_errors": 18,
      "justification_gaps": 15,
      "construction_failures": 8,
      "other_errors": 4
    }
  },
  "taxonomy": {
    "categories": [...],
    "error_mapping": {...}
  },
  "templates": {
    "Category Name": "PRESCRIPTIVE REPAIR PLAN...",
    ...
  },
  "test_results": {
    "templates_tested": 3,
    "results": [
      {
        "category": "Slope Constraint Violation",
        "evaluation": {
          "applicability": "Yes",
          "specificity_score": 8,
          "actionability_score": 9,
          "completeness_score": 7,
          "overall_assessment": "Template is highly actionable..."
        }
      }
    ]
  },
  "success_criteria": {
    "templates_tested": 3,
    "avg_specificity": 7.3,
    "avg_actionability": 8.0,
    "avg_completeness": 6.7
  }
}
```

---

## Interpreting Results

### ✅ STAGE 1 PASSED (Proceed to Stage 2)
```
Templates Tested: 3/3
Avg Specificity: 7.3/10
Avg Actionability: 8.0/10
Avg Completeness: 6.7/10

✅ STAGE 1 PASSED: Prescriptive feedback templates are viable
   Recommendation: Proceed to Stage 2 (n=10 statistical validation)
```

**Next Step**: Run Stage 2 n=10 validation to test if Phase 1 doesn't degrade answer quality

---

### ❌ STAGE 1 FAILED (Refine or Pivot)
```
Templates Tested: 2/3
Avg Specificity: 4.5/10
Avg Actionability: 5.2/10
Avg Completeness: 4.8/10

❌ STAGE 1 FAILED: Prescriptive feedback templates need improvement
   Recommendation: Refine template generation or pivot to Phase 3
```

**Next Step**: Either:
1. Adjust template generation prompts and re-run
2. Pivot to Phase 3 (compositional verification)
3. Manual template creation by human expert

---

## Troubleshooting

### Error: "No errors extracted"
**Cause**: Log files don't contain verification errors
**Fix**: Check that log files are from Phase A validation (should have verification output)

### Error: "GPT-OSS API timeout" (FIXED 2025-12-18)
**Cause**: Too many errors (526) creating 20K+ char prompts that timeout with HIGH reasoning
**Fix Applied**: Three optimizations to reduce prompt size by 70%:
1. **Random sampling**: 10 errors per type instead of 20 (50% reduction)
2. **Truncation**: 300 chars per error instead of 500 (40% reduction)
3. **Medium reasoning**: Changed categorization from HIGH to MEDIUM (saves HIGH for templates)

**Result**: Prompt size reduced from ~20K to ~7K chars, expected completion in <300s instead of timeout

### Error: "Failed to parse JSON"
**Cause**: LLM response not in valid JSON format
**Fix**: Check API response, adjust temperature (lower = more structured)

### Low scores (<6.0) on all metrics
**Cause**: Error corpus too small or not diverse enough
**Fix**:
- Add more log files from different test runs
- Manually curate error examples
- Adjust categorization prompt to request more specific categories

---

## Configuration Options

### Change LLM Reasoning Levels

Edit `stage1_error_analysis.py`:

```python
# For categorization (default: high)
taxonomy = categorize_errors(all_errors)
# Change to:
response = call_gpt_oss(categorization_prompt, reasoning_effort="medium")

# For template generation (default: high)
templates = generate_fix_templates(taxonomy)
# Change to:
response = call_gpt_oss(template_prompt, reasoning_effort="medium")

# For testing (default: medium)
test_results = test_top_templates(templates, all_errors)
# Change to:
response = call_gpt_oss(test_prompt, reasoning_effort="low")
```

**Trade-off**: Lower reasoning = faster + cheaper, but less accurate templates

### Change Number of Categories

Edit categorization prompt:

```python
# Default: "5-10 distinct categories"
# Change to: "3-5 distinct categories" (broader)
# Or: "10-15 distinct categories" (more fine-grained)
```

### Change Number of Templates Tested

Edit `generate_fix_templates()`:

```python
# Default: top 10 categories
for category in taxonomy['categories'][:10]:
# Change to: top 5
for category in taxonomy['categories'][:5]:
```

And in `test_top_templates()`:

```python
# Default: top 3 templates
top_templates = list(templates.items())[:3]
# Change to: top 5
top_templates = list(templates.items())[:5]
```

---

## Advanced Usage

### Extract Errors Only (No LLM Calls)

```bash
python -c "
from stage1_error_analysis import extract_errors_from_log
import json

errors = extract_errors_from_log('run_log_gpt_oss/memory_phase1_validation_p1.log')
print(json.dumps({k: len(v) for k, v in errors.items()}, indent=2))
"
```

### Generate Templates for Specific Category

```bash
python -c "
from stage1_error_analysis import call_gpt_oss

template = call_gpt_oss('''
Create prescriptive fix template for:
Category: Slope Constraint Violation
Description: Lines claimed sunny have prohibited slopes
Root Cause: Construction doesn't verify slope constraints
''', reasoning_effort='high')

print(template)
"
```

### Test Custom Template

```bash
python -c "
from stage1_error_analysis import call_gpt_oss

evaluation = call_gpt_oss('''
Test this template:
[Your custom template here]

On this error:
[Your error example here]

Rate specificity, actionability, completeness (1-10)
''', reasoning_effort='medium')

print(evaluation)
"
```

---

## What Happens After Stage 1

### If PASSED → Stage 2: Statistical Validation

Run n=10 tests to validate:
- Phase 1 doesn't degrade answer quality
- Phase 1 improves success rate
- Deduplication doesn't interfere

Cost: $120, Time: overnight

### If FAILED → Iterate or Pivot

**Option A**: Refine templates
- Adjust prompts
- Add human expert review
- Increase specificity requirements
- Re-run Stage 1

**Option B**: Pivot to Phase 3
- Compositional verification
- Proof decomposition
- Independent component validation

---

## Success Metrics

Stage 1 validates that prescriptive feedback **concept** works. Key metrics:

1. **Template Quality**:
   - Specificity ≥6.0: Actions are concrete, not abstract
   - Actionability ≥6.0: LLM can execute them
   - Completeness ≥6.0: Covers all repair aspects

2. **Error Coverage**:
   - ≥3 error categories identified
   - ≥80% of errors mapped to categories
   - Categories are mutually exclusive

3. **Applicability**:
   - ≥2/3 templates applicable to sample errors
   - Templates generalize across error instances

If all metrics met → HIGH confidence Phase 2 will work

If metrics borderline → MEDIUM confidence, proceed with caution

If metrics fail → LOW confidence, pivot or iterate

---

## Comparison: Manual vs Automated Stage 1

### Original Plan (Manual)
- Human expert selects 3 errors
- Human creates prescriptive feedback
- Human evaluates if agent improves
- Time: 4 hours, Cost: $0, Coverage: 3 errors

### This Script (Automated)
- LLM analyzes all errors (35-60)
- LLM creates error taxonomy (5-10 categories)
- LLM generates templates for each category
- LLM tests templates on samples
- Time: 30 minutes, Cost: $3, Coverage: all errors

**Advantage**: Data-driven, comprehensive, reproducible, scalable

**Trade-off**: Requires LLM API access, slightly higher cost

---

## Example Session

```bash
$ python stage1_error_analysis.py --logs run_log_gpt_oss/*.log

================================================================================
STAGE 1: AUTOMATED ERROR ANALYSIS AND TEMPLATE GENERATION
================================================================================

[EXTRACT] Reading log file: run_log_gpt_oss/memory_phase1_validation_p1.log
[EXTRACT] Found 18 Critical Errors
[EXTRACT] Found 15 Justification Gaps
[EXTRACT] Found 8 Construction Failures
[EXTRACT] Found 4 Other Errors

[SUMMARY] Total unique errors extracted:
  Critical Errors: 18
  Justification Gaps: 15
  Construction Failures: 8
  Other Errors: 4
  TOTAL: 45

================================================================================
[CATEGORIZE] Using GPT-OSS-120B to create error taxonomy
================================================================================

[GPT-OSS] Calling API with reasoning=high, temp=0.1
[GPT-OSS] Prompt length: 12450 chars
[GPT-OSS] Response length: 3218 chars
[CATEGORIZE] Created 7 error categories
  - Slope Constraint Violation: 8 errors
  - Incomplete Coverage Proof: 6 errors
  - Bound Derivation Error: 5 errors
  - Missing Case Analysis: 4 errors
  - False Claim About Points: 3 errors
  - Unjustified Equality: 2 errors
  - Circular Reasoning: 1 errors

================================================================================
[TEMPLATES] Generating prescriptive fix templates for each category
================================================================================

[TEMPLATES] Generating template for: Slope Constraint Violation
[GPT-OSS] Calling API with reasoning=high, temp=0.2
[GPT-OSS] Response length: 1842 chars
[TEMPLATES] Generated 1842 char template

[TEMPLATES] Generating template for: Incomplete Coverage Proof
[GPT-OSS] Response length: 1654 chars
...

================================================================================
[TEST] Testing top 3 category templates
================================================================================

[TEST] Testing template: Slope Constraint Violation
[TEST] Slope Constraint Violation:
  Applicability: Yes
  Specificity: 8/10
  Actionability: 9/10
  Completeness: 7/10

[TEST] Testing template: Incomplete Coverage Proof
...

[SAVED] Results written to stage1_results.json

================================================================================
STAGE 1 SUCCESS CRITERIA EVALUATION
================================================================================

Templates Tested: 3/3
Avg Specificity: 7.3/10
Avg Actionability: 8.0/10
Avg Completeness: 6.7/10

✅ STAGE 1 PASSED: Prescriptive feedback templates are viable
   Recommendation: Proceed to Stage 2 (n=10 statistical validation)
```

---

**Ready to run?** Execute the command at the top of this file! 🚀

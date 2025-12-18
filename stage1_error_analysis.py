#!/usr/bin/env python3
"""
Stage 1: Automated Error Categorization and Template Generation

This script implements the refined Stage 1 validation:
1. Extract all errors from Phase A validation logs
2. Use GPT-OSS-120B to categorize errors into taxonomy
3. Generate fix templates for each error category
4. Test top 3 category templates to validate prescriptive feedback concept

Usage:
    python stage1_error_analysis.py --logs run_log_gpt_oss/memory_phase1_validation_p1.log run_log_gpt_oss/mcts_phase1_validation_p1.log
"""

import os
import sys
import json
import re
import argparse
import random
from collections import defaultdict
from typing import List, Dict, Tuple
import requests

# Import GPT-OSS API configuration from agent
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'code'))
from agent_gpt_oss import API_URL, MODEL_NAME, get_api_key


def extract_errors_from_log(log_file: str) -> Dict[str, List[str]]:
    """
    Extract all verification errors from a log file.
    Extracts from ALL iterations, not just the final one.

    Returns:
        Dict with error types as keys and list of error instances as values
    """
    errors = {
        'critical_errors': [],
        'justification_gaps': [],
        'construction_failures': [],
        'other_errors': []
    }

    print(f"[EXTRACT] Reading log file: {log_file}")

    with open(log_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Extract verification blocks from log entries
    # Pattern: >>>>>>> Verification results: followed by the verification text
    verify_pattern = r'>>>>>>> Verification results:\s*"(.+?)"(?=\n\[|\n>>>>>>> |$)'
    verify_blocks = re.findall(verify_pattern, content, re.DOTALL)

    print(f"[EXTRACT] Found {len(verify_blocks)} verification blocks in log")

    for i, block in enumerate(verify_blocks, 1):
        # Unescape the JSON string (it's stored as escaped JSON in the log)
        # Replace common escape sequences
        unescaped = block.replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\')
        errors = parse_verification_text(unescaped, errors)

    # Also extract from JSON memory file if it exists (for final verification)
    json_file = log_file.replace('.log', '.json')
    if os.path.exists(json_file):
        with open(json_file, 'r', encoding='utf-8') as f:
            memory = json.load(f)
            verify_text = memory.get('verify', '')
            if verify_text:
                errors = parse_verification_text(verify_text, errors)

    # Deduplicate errors (same error text might appear multiple times)
    for key in errors:
        errors[key] = list(set(errors[key]))

    print(f"[EXTRACT] Found {len(errors['critical_errors'])} unique Critical Errors")
    print(f"[EXTRACT] Found {len(errors['justification_gaps'])} unique Justification Gaps")
    print(f"[EXTRACT] Found {len(errors['construction_failures'])} unique Construction Failures")
    print(f"[EXTRACT] Found {len(errors['other_errors'])} unique Other Errors")

    return errors


def parse_verification_text(text: str, errors: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """Parse verification text and extract categorized errors."""

    # Pattern for "Critical Error" findings
    critical_pattern = r'\*\*Critical Error\*\*[:\-–—]\s*(.+?)(?=\n\*\*|###|\Z)'
    for match in re.finditer(critical_pattern, text, re.DOTALL | re.IGNORECASE):
        error_text = match.group(1).strip()
        if error_text and len(error_text) > 20:  # Filter out too-short extracts
            errors['critical_errors'].append(error_text)

    # Pattern for "Justification Gap" findings
    gap_pattern = r'\*\*Justification Gap\*\*[:\-–—]\s*(.+?)(?=\n\*\*|###|\Z)'
    for match in re.finditer(gap_pattern, text, re.DOTALL | re.IGNORECASE):
        error_text = match.group(1).strip()
        if error_text and len(error_text) > 20:
            errors['justification_gaps'].append(error_text)

    # Pattern for construction/coverage failures
    construction_keywords = [
        'construction fail', 'does not cover', 'not all points',
        'coverage fail', 'does not satisfy', 'counterexample'
    ]
    for keyword in construction_keywords:
        pattern = rf'(.{{0,200}}{keyword}.{{0,200}})'
        for match in re.finditer(pattern, text, re.IGNORECASE):
            error_text = match.group(1).strip()
            if error_text and len(error_text) > 30:
                errors['construction_failures'].append(error_text)

    # Extract from structured "Issue:" format
    issue_pattern = r'\*\s+\*\*Issue:\*\*\s+(.+?)(?=\n\*|\Z)'
    for match in re.finditer(issue_pattern, text, re.DOTALL):
        error_text = match.group(1).strip()
        if error_text and len(error_text) > 20:
            # Categorize based on content
            if 'critical' in error_text.lower():
                errors['critical_errors'].append(error_text)
            elif 'justification' in error_text.lower() or 'gap' in error_text.lower():
                errors['justification_gaps'].append(error_text)
            else:
                errors['other_errors'].append(error_text)

    return errors


def call_gpt_oss(prompt: str, reasoning_effort: str = "high", temperature: float = 0.3) -> str:
    """
    Call GPT-OSS-120B API to process a prompt.

    Args:
        prompt: The prompt to send
        reasoning_effort: "low", "medium", or "high"
        temperature: Sampling temperature

    Returns:
        The response text
    """
    api_key = get_api_key()

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": temperature
    }

    # Add reasoning effort (check if model name has provider prefix for extra_body)
    if '/' in MODEL_NAME and not MODEL_NAME.startswith('openai/'):
        # Provider-prefixed model (e.g., openrouter/...) - use extra_body
        payload["extra_body"] = {
            "reasoning": {"effort": reasoning_effort}
        }
    else:
        # Standard model - reasoning at top level
        payload["reasoning"] = {"effort": reasoning_effort}

    headers = {
        "Content-Type": "application/json"
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    print(f"[GPT-OSS] Calling API with reasoning={reasoning_effort}, temp={temperature}")
    print(f"[GPT-OSS] Prompt length: {len(prompt)} chars")

    try:
        response = requests.post(API_URL, json=payload, headers=headers, timeout=600)
        response.raise_for_status()

        result = response.json()
        content = result['choices'][0]['message']['content']

        print(f"[GPT-OSS] Response length: {len(content)} chars")
        return content

    except Exception as e:
        print(f"[GPT-OSS ERROR] {e}")
        return ""


def categorize_errors(all_errors: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """
    Use GPT-OSS-120B to analyze errors and create a taxonomy.

    Returns:
        Dict mapping category names to lists of error instances
    """
    print("\n" + "="*80)
    print("[CATEGORIZE] Using GPT-OSS-120B to create error taxonomy")
    print("="*80 + "\n")

    # Prepare error corpus for analysis
    # Use stratified random sampling for diversity and reduced input size
    error_corpus = []
    for error_type, errors in all_errors.items():
        # Sample 10 diverse errors instead of first 20 (reduces input by 50%)
        sample_size = min(10, len(errors))
        sampled = random.sample(errors, sample_size) if len(errors) > sample_size else errors
        for i, error in enumerate(sampled):
            # Truncate to 300 chars instead of 500 (reduces input by another 40%)
            error_corpus.append(f"[{error_type}#{i+1}] {error[:300]}")
        print(f"[CATEGORIZE] Sampled {len(sampled)} errors from {len(errors)} {error_type}")

    print(f"[CATEGORIZE] Total sampled errors: {len(error_corpus)}")
    print(f"[CATEGORIZE] Estimated reduction: 50% sample size + 40% truncation = 70% smaller prompt")

    categorization_prompt = f"""You are a mathematical proof verification expert analyzing common error patterns.

TASK: Analyze the following verification errors from an IMO problem-solving agent and create a comprehensive error taxonomy.

ERROR CORPUS ({len(error_corpus)} errors from Phase A validation logs):

{chr(10).join(error_corpus)}

INSTRUCTIONS:

1. **Identify error categories**: Group similar errors into 5-10 distinct categories
2. **Name each category**: Use clear, actionable names (e.g., "Slope Constraint Violation", "Incomplete Case Analysis")
3. **Describe each category**: Explain what type of error it represents and why it occurs
4. **Rank by frequency**: Order categories from most to least common
5. **Map errors to categories**: Assign each error instance to its category

OUTPUT FORMAT (JSON):

{{
  "categories": [
    {{
      "name": "Category Name",
      "description": "Clear explanation of error type",
      "frequency": <number of errors in this category>,
      "example_errors": ["error_id_1", "error_id_2"],
      "root_cause": "Why this error occurs"
    }}
  ],
  "error_mapping": {{
    "error_id": "category_name"
  }}
}}

Focus on creating categories that:
- Are mutually exclusive (each error fits in one category)
- Are collectively exhaustive (cover all error types)
- Enable targeted fix templates (each category should have a clear repair strategy)
"""

    # Use medium reasoning for categorization (high reserved for template generation)
    # This reduces timeout risk while maintaining quality
    response = call_gpt_oss(categorization_prompt, reasoning_effort="medium", temperature=0.1)

    # Parse JSON from response
    try:
        # Extract JSON from markdown code blocks if present
        json_match = re.search(r'```(?:json)?\s*(\{.+\})\s*```', response, re.DOTALL)
        if json_match:
            taxonomy = json.loads(json_match.group(1))
        else:
            taxonomy = json.loads(response)

        print(f"[CATEGORIZE] Created {len(taxonomy['categories'])} error categories")
        for cat in taxonomy['categories']:
            print(f"  - {cat['name']}: {cat['frequency']} errors")

        return taxonomy

    except json.JSONDecodeError as e:
        print(f"[CATEGORIZE ERROR] Failed to parse JSON: {e}")
        print(f"[CATEGORIZE ERROR] Response was: {response[:500]}...")
        return {"categories": [], "error_mapping": {}}


def generate_fix_templates(taxonomy: Dict) -> Dict[str, str]:
    """
    Use GPT-OSS-120B to generate prescriptive fix templates for each error category.

    Returns:
        Dict mapping category names to fix template strings
    """
    print("\n" + "="*80)
    print("[TEMPLATES] Generating prescriptive fix templates for each category")
    print("="*80 + "\n")

    templates = {}

    for category in taxonomy['categories'][:10]:  # Process top 10 categories
        category_name = category['name']
        category_desc = category['description']
        root_cause = category.get('root_cause', 'Unknown')

        print(f"[TEMPLATES] Generating template for: {category_name}")

        template_prompt = f"""You are a mathematical proof repair expert creating prescriptive fix templates.

ERROR CATEGORY: {category_name}

DESCRIPTION: {category_desc}

ROOT CAUSE: {root_cause}

TASK: Create a prescriptive fix template that converts this error into actionable repair instructions.

REQUIREMENTS:

1. **Be specific**: Reference exact proof sections, variable names, theorem numbers
2. **Be actionable**: Use TODO format with concrete steps (not abstract advice)
3. **Prioritize**: Mark items as CRITICAL (blocks correctness) or POLISH (improves clarity)
4. **Be complete**: Cover all aspects needed to fix this error category

TEMPLATE FORMAT:

```
PRESCRIPTIVE REPAIR PLAN for {category_name}:

**Context**: [1-2 sentence explanation of what went wrong]

**Required Actions**:
- [ ] CRITICAL: [Specific action with location, e.g., "In Section 2.1, replace line ℓ_c definition..."]
- [ ] CRITICAL: [Another specific action]
- [ ] POLISH: [Nice-to-have improvement]

**Verification Checklist**:
- [ ] [Specific check to confirm fix worked, e.g., "Verify all lines have slope ≠ {{0, -1, ∞}}"]
- [ ] [Another verification step]

**Example Fix** (if applicable):
[Show concrete example of applying this template]
```

Generate the complete template now:
"""

        response = call_gpt_oss(template_prompt, reasoning_effort="high", temperature=0.2)
        templates[category_name] = response

        print(f"[TEMPLATES] Generated {len(response)} char template for {category_name}")

    return templates


def test_top_templates(templates: Dict[str, str], all_errors: Dict[str, List[str]]) -> Dict:
    """
    Test top 3 category templates by applying them to sample errors.

    Returns:
        Test results with success metrics
    """
    print("\n" + "="*80)
    print("[TEST] Testing top 3 category templates")
    print("="*80 + "\n")

    # Select top 3 templates (assume they're ordered by frequency)
    top_templates = list(templates.items())[:3]

    test_results = {
        "templates_tested": len(top_templates),
        "results": []
    }

    for category_name, template in top_templates:
        print(f"\n[TEST] Testing template: {category_name}")

        # Find sample errors for this category
        # For now, use first error from each type as a test case
        sample_errors = []
        for error_type, errors in all_errors.items():
            if errors:
                sample_errors.append(errors[0][:1000])  # Limit length

        if not sample_errors:
            print(f"[TEST] No sample errors found for {category_name}")
            continue

        # Test template application
        test_prompt = f"""You are testing a prescriptive feedback template for mathematical proof repair.

TEMPLATE TO TEST:
{template}

SAMPLE ERROR:
{sample_errors[0]}

TASK: Apply this template to the sample error and generate the prescriptive repair plan.

Evaluate:
1. **Applicability**: Does the template fit this error? (Yes/No/Partial)
2. **Specificity**: Are the actions specific enough? (1-10 scale)
3. **Actionability**: Can an LLM follow these instructions? (1-10 scale)
4. **Completeness**: Does it cover all aspects? (1-10 scale)

OUTPUT FORMAT:
```json
{{
  "applicability": "Yes/No/Partial",
  "specificity_score": <1-10>,
  "actionability_score": <1-10>,
  "completeness_score": <1-10>,
  "overall_assessment": "<brief evaluation>",
  "applied_template": "<the filled-in template with specifics from sample error>"
}}
```
"""

        response = call_gpt_oss(test_prompt, reasoning_effort="medium", temperature=0.3)

        # Parse evaluation
        try:
            json_match = re.search(r'```(?:json)?\s*(\{.+\})\s*```', response, re.DOTALL)
            if json_match:
                evaluation = json.loads(json_match.group(1))
            else:
                evaluation = json.loads(response)

            test_results["results"].append({
                "category": category_name,
                "evaluation": evaluation
            })

            print(f"[TEST] {category_name}:")
            print(f"  Applicability: {evaluation.get('applicability', 'Unknown')}")
            print(f"  Specificity: {evaluation.get('specificity_score', 0)}/10")
            print(f"  Actionability: {evaluation.get('actionability_score', 0)}/10")
            print(f"  Completeness: {evaluation.get('completeness_score', 0)}/10")

        except Exception as e:
            print(f"[TEST ERROR] Failed to parse evaluation: {e}")

    return test_results


def main():
    parser = argparse.ArgumentParser(description='Stage 1: Automated Error Categorization and Template Generation')
    parser.add_argument('--logs', nargs='+', required=True,
                       help='Path(s) to Phase A validation log files')
    parser.add_argument('--output', default='stage1_results.json',
                       help='Output file for results (default: stage1_results.json)')

    args = parser.parse_args()

    print("\n" + "="*80)
    print("STAGE 1: AUTOMATED ERROR ANALYSIS AND TEMPLATE GENERATION")
    print("="*80 + "\n")

    # Step 1: Extract errors from all log files
    all_errors = {
        'critical_errors': [],
        'justification_gaps': [],
        'construction_failures': [],
        'other_errors': []
    }

    for log_file in args.logs:
        errors = extract_errors_from_log(log_file)
        for key in all_errors:
            all_errors[key].extend(errors[key])

    # Deduplicate across all logs
    for key in all_errors:
        all_errors[key] = list(set(all_errors[key]))

    print(f"\n[SUMMARY] Total unique errors extracted:")
    print(f"  Critical Errors: {len(all_errors['critical_errors'])}")
    print(f"  Justification Gaps: {len(all_errors['justification_gaps'])}")
    print(f"  Construction Failures: {len(all_errors['construction_failures'])}")
    print(f"  Other Errors: {len(all_errors['other_errors'])}")
    print(f"  TOTAL: {sum(len(v) for v in all_errors.values())}")

    # Step 2: Use GPT-OSS-120B to categorize errors
    taxonomy = categorize_errors(all_errors)

    if not taxonomy.get('categories'):
        print("[ERROR] Failed to create taxonomy. Exiting.")
        return 1

    # Step 3: Generate fix templates for each category
    templates = generate_fix_templates(taxonomy)

    # Step 4: Test top 3 templates
    test_results = test_top_templates(templates, all_errors)

    # Save results
    output = {
        "error_extraction": {
            "log_files": args.logs,
            "total_errors": sum(len(v) for v in all_errors.values()),
            "by_type": {k: len(v) for k, v in all_errors.items()}
        },
        "taxonomy": taxonomy,
        "templates": templates,
        "test_results": test_results,
        "success_criteria": {
            "templates_tested": test_results["templates_tested"],
            "avg_specificity": sum(r["evaluation"].get("specificity_score", 0)
                                  for r in test_results["results"]) / max(len(test_results["results"]), 1),
            "avg_actionability": sum(r["evaluation"].get("actionability_score", 0)
                                    for r in test_results["results"]) / max(len(test_results["results"]), 1),
            "avg_completeness": sum(r["evaluation"].get("completeness_score", 0)
                                   for r in test_results["results"]) / max(len(test_results["results"]), 1),
        }
    }

    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n[SAVED] Results written to {args.output}")

    # Print final assessment
    criteria = output["success_criteria"]
    print("\n" + "="*80)
    print("STAGE 1 SUCCESS CRITERIA EVALUATION")
    print("="*80 + "\n")
    print(f"Templates Tested: {criteria['templates_tested']}/3")
    print(f"Avg Specificity: {criteria['avg_specificity']:.1f}/10")
    print(f"Avg Actionability: {criteria['avg_actionability']:.1f}/10")
    print(f"Avg Completeness: {criteria['avg_completeness']:.1f}/10")

    # Decision gate
    if (criteria['templates_tested'] >= 2 and
        criteria['avg_specificity'] >= 6.0 and
        criteria['avg_actionability'] >= 6.0 and
        criteria['avg_completeness'] >= 6.0):
        print("\n✅ STAGE 1 PASSED: Prescriptive feedback templates are viable")
        print("   Recommendation: Proceed to Stage 2 (n=10 statistical validation)")
        return 0
    else:
        print("\n❌ STAGE 1 FAILED: Prescriptive feedback templates need improvement")
        print("   Recommendation: Refine template generation or pivot to Phase 3")
        return 1


if __name__ == "__main__":
    sys.exit(main())

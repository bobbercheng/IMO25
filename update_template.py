#!/usr/bin/env python3
"""Update stage1_results.json with corrected Integer/Denominator template"""

import json

# Read the fixed template
with open('template_integer_denominator_FIXED.md', 'r') as f:
    fixed_template = f.read()

# Remove the title and keep just the template content
# Start from "**PRESCRIPTIVE REPAIR PLAN..."
fixed_template = fixed_template.split('\n', 2)[2]  # Skip first 2 lines

# Load stage1_results.json
with open('stage1_results.json', 'r') as f:
    results = json.load(f)

# Replace the Integer/Denominator template
results['templates']['Integer/Denominator Reasoning Errors'] = fixed_template

# Save back
with open('stage1_results.json', 'w') as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print("✅ Successfully updated Integer/Denominator template in stage1_results.json")
print(f"   New template length: {len(fixed_template)} chars")

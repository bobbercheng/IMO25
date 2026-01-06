#!/usr/bin/env python3
"""
Add a test entry to blacklist for validation testing.
This seeds the blacklist with an answer before running sequential tests.
"""

import json
import time
from pathlib import Path

# Blacklist file path
blacklist_file = Path("blacklists/imo06_blacklist.json")

# Ensure directory exists
blacklist_file.parent.mkdir(parents=True, exist_ok=True)

# Load existing blacklist or create new one
if blacklist_file.exists():
    with open(blacklist_file, 'r') as f:
        data = json.load(f)
    print(f"Loaded existing blacklist with {len(data.get('solutions', []))} entries")
else:
    data = {
        "problem_id": "imo06",
        "solutions": [],
        "last_updated": 0,
        "count": 0
    }
    print("Creating new blacklist")

# Add test entry with answer 4048 (Ferrers diagram approach - wrong answer)
test_entry = {
    "answer": "4048",
    "method": "ferrers_diagram",
    "run_id": "manual_test",
    "verdict": "FAIL",  # Mark as FAIL since 4048 is wrong (correct is 2112)
    "iterations": 0,
    "timestamp": time.time()
}

# Check if this answer already exists
existing_answers = [s['answer'] for s in data['solutions']]
if "4048" in existing_answers:
    print("⚠ Answer '4048' already exists in blacklist")
    print(f"Current entries: {existing_answers}")
    print("\nRemoving existing '4048' entries before adding new one...")
    data['solutions'] = [s for s in data['solutions'] if s['answer'] != '4048']

# Add the new entry
data['solutions'].append(test_entry)
data['last_updated'] = time.time()
data['count'] = len(data['solutions'])

# Save back to file
with open(blacklist_file, 'w') as f:
    json.dump(data, f, indent=2)

print(f"\n✓ Added test entry to {blacklist_file}")
print(f"\nBlacklist now contains {data['count']} entries:")
for i, sol in enumerate(data['solutions'], 1):
    print(f"  {i}. Answer: {sol['answer']}, Method: {sol['method']}, Verdict: {sol['verdict']}, Run: {sol['run_id']}")

print("\n" + "="*70)
print("NEXT STEP: Run sequential test to verify blacklist prompt injection")
print("="*70)
print("\nCommand:")
print("  ./test_blacklist_sequential.sh")
print("\nExpected behavior:")
print("  - Run 1 should see the '4048' entry in blacklist")
print("  - Run 1 logs should contain 'FORBIDDEN APPROACHES' with '4048'")
print("  - Run 1 should try a DIFFERENT approach (not Ferrers)")
print("\nIf blacklist prompts appear → Integration works!")
print("If NO blacklist prompts → Need to debug prompt injection")

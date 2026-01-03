#!/usr/bin/env python3
"""
Fix IMO06 blacklist data corruption.

Issue: Blacklist contains {"answer": "4048", "verdict": "FAIL"}
Reality: 4048 is the CORRECT answer (2n-2 via left/right partition)

This script removes incorrect entries and keeps only actual failures.
"""

import json
from pathlib import Path

def fix_blacklist():
    blacklist_path = Path("blacklists/imo06_blacklist.json")

    if not blacklist_path.exists():
        print("❌ Blacklist file not found!")
        return

    # Load current blacklist
    with open(blacklist_path) as f:
        data = json.load(f)

    print("=" * 70)
    print("BLACKLIST DATA CORRUPTION FIX")
    print("=" * 70)

    print(f"\nCurrent entries: {data['count']}")
    print("\nBEFORE:")
    for i, sol in enumerate(data["solutions"], 1):
        verdict_icon = "✅" if sol["verdict"] == "PASS" else "❌"
        print(f"  {i}. {verdict_icon} {sol['answer']} ({sol['method']}) - {sol['verdict']}")

    # Filter out incorrect entries
    # Keep only entries that are:
    # 1. Actual failures (verdict=FAIL and answer != 4048)
    # 2. Successful explorations (verdict=PASS) for reference

    original_count = len(data["solutions"])

    cleaned_solutions = []
    removed_entries = []

    for sol in data["solutions"]:
        # Remove if: answer=4048 AND verdict=FAIL (this is wrong - 4048 is correct)
        if sol["answer"] == "4048" and sol["verdict"] == "FAIL":
            removed_entries.append(sol)
            print(f"\n⚠️  REMOVING INCORRECT ENTRY:")
            print(f"    Answer: {sol['answer']}")
            print(f"    Method: {sol['method']}")
            print(f"    Verdict: {sol['verdict']} ← WRONG (4048 is actually correct)")
        else:
            cleaned_solutions.append(sol)

    # Update data
    data["solutions"] = cleaned_solutions
    data["count"] = len(cleaned_solutions)

    print("\n" + "=" * 70)
    print("AFTER CLEANING:")
    for i, sol in enumerate(data["solutions"], 1):
        verdict_icon = "✅" if sol["verdict"] == "PASS" else "❌"
        print(f"  {i}. {verdict_icon} {sol['answer']} ({sol['method']}) - {sol['verdict']}")

    print(f"\nRemoved: {original_count - data['count']} incorrect entries")
    print(f"Remaining: {data['count']} entries")

    # Save cleaned blacklist
    backup_path = blacklist_path.with_suffix(".json.backup")
    print(f"\n📁 Backing up original to: {backup_path}")
    with open(backup_path, 'w') as f:
        json.dump({"before_fix": data, "removed": removed_entries}, f, indent=2)

    print(f"💾 Saving cleaned blacklist to: {blacklist_path}")
    with open(blacklist_path, 'w') as f:
        json.dump(data, f, indent=2)

    print("\n" + "=" * 70)
    print("✅ BLACKLIST FIXED")
    print("=" * 70)
    print("\nNext steps:")
    print("1. Re-run BFS tests to see if behavior changes")
    print("2. Expect: Model may still converge to 4048 (it's correct!)")
    print("3. Diversity should come from DIFFERENT METHODS, not different answers")
    print()

if __name__ == "__main__":
    fix_blacklist()

#!/usr/bin/env python3
"""
Restore the 4048 FAIL entry to blacklist.

ERROR: I incorrectly removed this entry thinking 4048 was correct.
TRUTH: Correct answer is 2112, so 4048 FAIL should stay.
"""

import json
from pathlib import Path

def restore_blacklist():
    blacklist_path = Path("blacklists/imo06_blacklist.json")

    # Load current blacklist
    with open(blacklist_path) as f:
        data = json.load(f)

    print("=" * 70)
    print("RESTORING 4048 FAIL ENTRY (I was wrong to remove it)")
    print("=" * 70)

    # Check if we need to restore from backup
    backup_path = blacklist_path.with_suffix(".json.backup")
    if backup_path.exists():
        with open(backup_path) as f:
            backup = json.load(f)
            if "removed" in backup:
                removed_entries = backup["removed"]
                print(f"\nFound {len(removed_entries)} removed entries in backup")

                # Restore the 4048 FAIL entry
                for entry in removed_entries:
                    if entry["answer"] == "4048" and entry["verdict"] == "FAIL":
                        print(f"\n✅ Restoring: {entry['answer']} ({entry['method']}) - {entry['verdict']}")
                        data["solutions"].append(entry)
                        data["count"] += 1

    # Sort by timestamp
    data["solutions"].sort(key=lambda x: x["timestamp"])

    # Save restored blacklist
    print(f"\n💾 Saving restored blacklist")
    with open(blacklist_path, 'w') as f:
        json.dump(data, f, indent=2)

    print("\n" + "=" * 70)
    print("CURRENT BLACKLIST:")
    print("=" * 70)
    for i, sol in enumerate(data["solutions"], 1):
        verdict_icon = "✅" if sol["verdict"] == "PASS" else "❌"
        print(f"  {i}. {verdict_icon} {sol['answer']} ({sol['method']}) - {sol['verdict']}")

    print(f"\nTotal entries: {data['count']}")
    print("\n" + "=" * 70)
    print("ANALYSIS")
    print("=" * 70)
    print("\nGround truth: 2112 (correct)")
    print("\nBlacklisted wrong answers:")
    print("  - 4048 (FAIL) ← Model converged here 3/3 times")
    print("  - 4050 (FAIL)")
    print("\nExplored alternatives:")
    print("  - 2025 (PASS) ← Also wrong, but different approach")
    print("\nNOT found: 2112 (the correct answer)")
    print("\n⚠️  This confirms BFS diversity failure:")
    print("    - 0% success rate (0/3 found 2112)")
    print("    - 100% convergence to wrong answer (4048)")
    print("    - Blacklist ineffective at preventing wrong convergence")

if __name__ == "__main__":
    restore_blacklist()

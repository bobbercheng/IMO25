# Structured Output Test Results Summary (5 Runs)

## Overall Results

| Run | Tests Passed | Accuracy | Test1 | Test2 | Test3 | Test4 | Test5 | Test6 |
|-----|-------------|----------|-------|-------|-------|-------|-------|-------|
| 1   | 2/6        | 33.3%    | FAIL  | FAIL  | PASS✓ | FAIL  | PASS✓ | FAIL  |
| 2   | 1/6        | 16.7%    | ?     | FAIL  | FAIL  | FAIL  | PASS✓ | FAIL  |
| 3   | 1/6        | 16.7%    | ?     | FAIL  | FAIL  | FAIL  | PASS✓ | FAIL  |
| 4   | 1/6        | 16.7%    | ?     | FAIL  | FAIL  | FAIL  | PASS✓ | FAIL  |
| 5   | 1/6        | 16.7%    | ?     | FAIL  | FAIL  | FAIL  | PASS✓ | FAIL  |

**Average Accuracy: 20.0%**

## Test Expectations vs Results

| Test | Description | Expected | Pass Rate |
|------|-------------|----------|-----------|
| 1 | Complete Proof (bfs_run2) | PASS | 0/5 (0%) ❌ |
| 2 | Complete Proof (bfs_run8) | PASS | 0/5 (0%) ❌ |
| 3 | Trial-and-error (k=2) | FAIL | 1/5 (20%) ⚠️ |
| 4 | Missing constructions | FAIL | 0/5 (0%) ❌ |
| 5 | Wrong answer (k=2 included) | FAIL | 5/5 (100%) ✅ |
| 6 | Justification gaps | PASS | 0/5 (0%) ❌ |

## Issues Identified

1. **Test 1 & 2 (Complete Proofs)**: Should PASS but all FAILing → Verification too strict
2. **Test 3 (Trial-and-error)**: Should FAIL consistently but only 20% → Inconsistent detection  
3. **Test 4 (Missing constructions)**: Should FAIL but getting unexpected result
4. **Test 5 (Wrong answer)**: ✅ Working perfectly (100% correct detection)
5. **Test 6 (Justification gaps)**: Should PASS but all FAILing → Too strict on gaps

## Comparison to Baseline (Pre-Fixes)

Previous baseline: 26.7% accuracy (8/30 tests passed across 5 runs)
Current results: 20.0% accuracy (6/30 tests passed across 5 runs)

**REGRESSION: -6.7 percentage points**

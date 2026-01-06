#!/usr/bin/env python3
"""Test n=9 with EXHAUSTIVE search"""

import sys
sys.path.insert(0, 'code')

import itertools
import time
import math
from brute_force_tiling_solver import GridTilingSolver

# Monkey-patch to force exhaustive for n=9
original_generate = GridTilingSolver._generate_config_iterator

def patched_generate(self):
    """Force exhaustive search for n=9"""
    num_perms = math.factorial(self.n)

    # Force exhaustive for n <= 9 instead of n <= 8
    if num_perms <= self.max_iters and self.n <= 9:
        print(f"Small n ({self.n}), using exhaustive search ({num_perms} configs)")
        for perm in itertools.permutations(range(self.n)):
            yield {(row, col) for row, col in enumerate(perm)}
    else:
        # Fall back to heuristic
        print(f"Large n ({self.n}), using structured + sampling search")
        yield from original_generate(self)

GridTilingSolver._generate_config_iterator = patched_generate

# Now run the solver
n = 9
k = 3

print(f"Solving for n={n}, k={k} with EXHAUSTIVE search")
print(f"Expected by formula n+2k-3: {n + 2*k - 3}")
print(f"Total permutations to check: {math.factorial(n):,}")
print()

solver = GridTilingSolver(n, max_iters=500000)
start = time.time()
min_tiles, _ = solver.solve()
elapsed = time.time() - start

print(f"\n{'='*80}")
print(f"RESULT: n={n}, k={k} → {min_tiles} tiles (exhaustive search)")
print(f"Elapsed time: {elapsed:.1f}s")
print(f"\nFormula validation:")
print(f"  n+2k-3 = {n + 2*k - 3} {'✓' if min_tiles == n + 2*k - 3 else '✗'}")
print(f"  n+2k-2 = {n + 2*k - 2} {'✓' if min_tiles == n + 2*k - 2 else '✗'}")
print(f"  n+2k-1 = {n + 2*k - 1} {'✓' if min_tiles == n + 2*k - 1 else '✗'}")
print(f"  2n-2   = {2*n - 2} {'✓' if min_tiles == 2*n - 2 else '✗'}")
print(f"{'='*80}")

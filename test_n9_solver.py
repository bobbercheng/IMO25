#!/usr/bin/env python3
"""Quick test to solve n=9 case"""

import sys
sys.path.insert(0, 'code')

from brute_force_tiling_solver import GridTilingSolver
import math

n = 9
k = int(math.sqrt(n))  # k=3 for n=9

print(f"Solving for n={n}, k={k}")
print(f"Expected by formula n+2k-3: {n + 2*k - 3}")
print()

solver = GridTilingSolver(n, max_iters=500000)
min_tiles, _ = solver.solve()

print(f"\n{'='*80}")
print(f"RESULT: n={n}, k={k} → {min_tiles} tiles")
print(f"Formula n+2k-3 = {n + 2*k - 3}")
print(f"Match: {'✓' if min_tiles == n + 2*k - 3 else '✗'}")
print(f"{'='*80}")

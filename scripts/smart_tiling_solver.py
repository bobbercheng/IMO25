#!/usr/bin/env python3
"""
SMART Grid Tiling Solver - Tests only STRUCTURED configurations

Strategy: For perfect squares n=k², the optimal configuration likely has structure.
We'll test only:
1. Diagonal patterns
2. Block-based patterns
3. Affine/modular patterns

This dramatically reduces search space while likely finding optimal.
"""

import time
from typing import Tuple, FrozenSet


def solve_smart(n: int):
    """Test only structured configurations."""
    print(f"Smart solver for n={n}")
    print(f"Testing only structured patterns (not all {factorial_str(n)} permutations)\n")

    configurations = generate_structured_configs(n)

    best_tiles = float('inf')
    best_config = None
    best_name = None

    for name, config in configurations:
        print(f"Testing: {name}...")
        tiles = count_tiles_greedy_improved(n, config)
        print(f"  → {tiles} tiles")

        if tiles < best_tiles:
            best_tiles = tiles
            best_config = config
            best_name = name
            print(f"  ★ NEW BEST!")

    print(f"\n{'='*80}")
    print(f"RESULT: {best_tiles} tiles (using {best_name})")
    print(f"{'='*80}")

    return best_tiles, best_config, best_name


def generate_structured_configs(n: int):
    """Generate structured permutation patterns."""
    configs = []

    # 1. Identity (diagonal)
    configs.append(("Diagonal (i,i)", frozenset((i, i) for i in range(n))))

    # 2. Reverse diagonal
    configs.append(("Reverse diagonal", frozenset((i, n-1-i) for i in range(n))))

    # 3. For perfect squares: block patterns
    if is_perfect_square(n):
        k = int(n ** 0.5)

        # Block diagonal: each k×k block has its own diagonal
        block_diag = []
        for block in range(k):
            for local in range(k):
                row = block * k + local
                col = block * k + local
                block_diag.append((row, col))
        configs.append((f"Block diagonal (k={k})", frozenset(block_diag)))

        # Staircase: (i, (i + k) mod n)
        staircase = []
        for i in range(n):
            j = (i + k) % n
            staircase.append((i, j))
        configs.append((f"Staircase shift by k={k}", frozenset(staircase)))

        # Block permutation: swap blocks
        if k >= 2:
            block_perm = []
            for i in range(n):
                block_i = i // k
                local_i = i % k
                # Swap blocks 0 and 1
                if block_i == 0:
                    block_j = 1
                elif block_i == 1:
                    block_j = 0
                else:
                    block_j = block_i
                j = block_j * k + local_i
                block_perm.append((i, j))
            configs.append(("Block swap pattern", frozenset(block_perm)))

    # 4. Affine patterns
    for shift in [1, 2, n//2]:
        affine = []
        for i in range(n):
            j = (i + shift) % n
            affine.append((i, j))
        configs.append((f"Affine shift by {shift}", frozenset(affine)))

    return configs


def count_tiles_greedy_improved(n: int, uncovered: FrozenSet) -> int:
    """
    IMPROVED greedy tiling - uses better heuristics.

    Instead of maximal rectangle, use:
    1. Largest rectangle that creates good remaining structure
    2. Prefer rectangles that don't fragment remaining cells
    """
    remaining = set((i, j) for i in range(n) for j in range(n) if (i, j) not in uncovered)
    tiles = 0

    while remaining:
        # Find best rectangle to place
        best_rect = find_best_rectangle(remaining, uncovered, n)

        if not best_rect:
            # Fallback: single cell (shouldn't happen)
            cell = min(remaining)
            remaining.remove(cell)
            tiles += 1
        else:
            # Place rectangle
            for cell in best_rect:
                remaining.remove(cell)
            tiles += 1

    return tiles


def find_best_rectangle(remaining: set, uncovered: FrozenSet, n: int) -> frozenset:
    """
    Find best rectangle to place.

    Heuristic: Prefer rectangles that:
    1. Are large (cover many cells)
    2. Don't fragment remaining cells badly
    3. Align with grid structure
    """
    best_rect = None
    best_score = -1

    # Pick a cell to cover
    if not remaining:
        return None

    target = min(remaining)

    # Try all rectangles containing target
    for r_min in range(target[0] + 1):
        for r_max in range(target[0], n):
            for c_min in range(target[1] + 1):
                for c_max in range(target[1], n):
                    # Build rectangle
                    rect = set()
                    valid = True

                    for r in range(r_min, r_max + 1):
                        for c in range(c_min, c_max + 1):
                            if (r, c) in uncovered:
                                valid = False
                                break
                            if (r, c) not in remaining:
                                valid = False
                                break
                            rect.add((r, c))
                        if not valid:
                            break

                    if valid and rect:
                        # Score rectangle
                        size = len(rect)
                        # Bonus for squares
                        width = c_max - c_min + 1
                        height = r_max - r_min + 1
                        square_bonus = 2 if width == height else 0

                        score = size + square_bonus

                        if score > best_score:
                            best_score = score
                            best_rect = frozenset(rect)

    return best_rect


def is_perfect_square(n: int) -> bool:
    """Check if n is a perfect square."""
    k = int(n ** 0.5)
    return k * k == n


def factorial_str(n: int) -> str:
    """Human-readable factorial."""
    import math
    f = math.factorial(n)
    if f < 1000:
        return str(f)
    elif f < 1_000_000:
        return f"{f/1000:.0f}K"
    elif f < 1_000_000_000:
        return f"{f/1_000_000:.0f}M"
    else:
        return f"{f/1_000_000_000:.0f}B"


def main():
    print("="*80)
    print("SMART STRUCTURED CONFIGURATION TILING SOLVER")
    print("="*80)
    print("Strategy: Test only structured patterns (not exhaustive)")
    print("Rationale: Optimal configs for perfect squares likely have structure")
    print("="*80)
    print()

    # Test n=4
    print("TEST 1: n=4 (k=2)")
    print("-"*80)
    tiles_4, config_4, name_4 = solve_smart(4)
    print()

    # Test n=9
    print("\nTEST 2: n=9 (k=3)")
    print("-"*80)
    tiles_9, config_9, name_9 = solve_smart(9)
    print()

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"n=4: {tiles_4} tiles (pattern: {name_4})")
    print(f"n=9: {tiles_9} tiles (pattern: {name_9})")
    print()
    print("Note: These use IMPROVED greedy heuristic on structured configs")
    print("May not be optimal, but likely close for structured patterns")
    print("="*80)


if __name__ == "__main__":
    main()

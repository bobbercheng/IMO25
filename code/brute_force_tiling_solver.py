#!/usr/bin/env python3
"""
Brute-Force / Heuristic Tiling Solver for IMO 2025 Problem 6

Problem: Given an n×n grid, place rectangular tiles such that:
- Each row has exactly 1 uncovered square
- Each column has exactly 1 uncovered square
- Minimize the number of tiles

This solver uses exhaustive search for small n (n≤8) and 
randomized search + heuristics for larger n.
"""

import itertools
import random
import time
import math
from typing import List, Tuple, Set, Optional


class GridTilingSolver:
    """Solver for grid tiling problem"""

    def __init__(self, n: int, max_iters: int = 10000):
        self.n = n
        self.grid_size = n * n
        self.best_tiling = None
        self.min_tiles = float('inf')
        self.max_iters = max_iters
        self.best_config = None

    def solve(self) -> Tuple[int, List[Tuple[int, int, int, int]]]:
        """
        Find minimum tiling for n×n grid.

        Returns:
            (min_tiles, best_tiling_config)
        """
        print(f"Solving {self.n}×{self.n} grid tiling problem...")
        print(f"Total squares: {self.grid_size}")
        print(f"Covered squares: {self.grid_size - self.n}")

        start_time = time.time()

        # Step 1: Generate configurations (iteratively)
        config_generator = self._generate_config_iterator()
        
        count = 0
        for uncovered_squares in config_generator:
            count += 1
            if count > self.max_iters:
                break
                
            if count % 1000 == 0:
                elapsed = time.time() - start_time
                print(f"Progress: {count} configs checked, {elapsed:.1f}s elapsed. Best so far: {self.min_tiles}")

            min_tiles_for_config = self._find_min_tiling(uncovered_squares)

            if min_tiles_for_config < self.min_tiles:
                self.min_tiles = min_tiles_for_config
                # We don't store the full tiling for speed, unless needed
                self.best_config = sorted(list(uncovered_squares))
                print(f"  → New best: {self.min_tiles} tiles (config {count})")

        elapsed = time.time() - start_time
        print(f"\nSolved in {elapsed:.2f}s")
        print(f"Minimum tiles found: {self.min_tiles}")
        print(f"Total configurations tested: {count}")
        if self.best_config:
            # Print the first few elements of the best config to identify it
            print(f"Best config sample: {self.best_config[:5]}...")

        return self.min_tiles, self.best_tiling

    def _generate_config_iterator(self):
        """
        Generator that yields sets of uncovered squares.
        For small n, yields all permutations.
        For large n, yields structured + random permutations.
        """
        # Calculate number of permutations
        num_perms = math.factorial(self.n)
        
        # If tractable, do exhaustive
        if num_perms <= self.max_iters and self.n <= 8:
            print(f"Small n ({self.n}), using exhaustive search ({num_perms} configs)")
            for perm in itertools.permutations(range(self.n)):
                uncovered = set()
                for row, col in enumerate(perm):
                    uncovered.add((row, col))
                yield uncovered
        else:
            print(f"Large n ({self.n}), using structured + sampling search")
            
            # 1. Deterministic / Structured Patterns
            
            # Diagonal
            yield {(i, i) for i in range(self.n)}
            
            # Anti-diagonal
            yield {(i, self.n - 1 - i) for i in range(self.n)}
            
            # Shifted diagonals
            for k in range(1, self.n):
                yield {(i, (i + k) % self.n) for i in range(self.n)}
            
            # Affine Permutations: p[i] = (a*i + b) % n
            # Must have gcd(a, n) == 1
            coprimes = [a for a in range(1, self.n) if math.gcd(a, self.n) == 1]
            print(f"Checking affine permutations with slopes: {coprimes}")
            for a in coprimes:
                for b in range(self.n):
                    yield {(i, (a * i + b) % self.n) for i in range(self.n)}

            # Block Transpose (if n is perfect square)
            k_sqrt = int(math.isqrt(self.n))
            if k_sqrt * k_sqrt == self.n:
                print(f"Checking block transpose patterns for k={k_sqrt}")
                # Transpose: i = q*k + r -> p[i] = r*k + q
                base_perm = [(i, (i % k_sqrt) * k_sqrt + (i // k_sqrt)) for i in range(self.n)]
                
                # Yield base transpose
                yield {x for x in base_perm}
                
                # Transpose with shifts
                # p[i] = (base_perm[i] + shift) % n
                for shift in range(1, self.n):
                     yield {(r, (c + shift) % self.n) for r, c in base_perm}

            # 2. Random Permutations
            print(f"Starting random sampling (limit {self.max_iters})...")
            rng = list(range(self.n))
            while True:
                random.shuffle(rng)
                uncovered = set()
                for row, col in enumerate(rng):
                    uncovered.add((row, col))
                yield uncovered

    def _find_min_tiling(self, uncovered_squares: Set[Tuple[int, int]]) -> int:
        """
        Find minimum number of rectangular tiles to cover all valid squares.
        Uses greedy heuristic with optimized maximal rectangle finding.
        """
        # Convert set to grid for O(1) access
        # 1 = covered (needs tile), 0 = uncovered (hole)
        grid = [[1] * self.n for _ in range(self.n)]
        for r, c in uncovered_squares:
            grid[r][c] = 0
            
        tiles_used = 0
        remaining_squares = (self.n * self.n) - self.n
        
        while remaining_squares > 0:
            # Find largest rectangle of 1s
            rect = self._find_largest_rectangle_fast(grid)
            
            if rect is None:
                # Should not happen if remaining_squares > 0
                return float('inf')
                
            r1, c1, r2, c2 = rect
            
            # "Remove" the rectangle (set to 0)
            count_removed = 0
            for r in range(r1, r2 + 1):
                for c in range(c1, c2 + 1):
                    if grid[r][c] == 1:
                        grid[r][c] = 0
                        count_removed += 1
            
            remaining_squares -= count_removed
            tiles_used += 1
            
        return tiles_used

    def _find_largest_rectangle_fast(self, grid: List[List[int]]) -> Optional[Tuple[int, int, int, int]]:
        """
        Find largest rectangle of 1s in binary grid using histogram algorithm.
        O(N^2) complexity.
        Returns (r1, c1, r2, c2).
        """
        best_area = 0
        best_rect = None
        
        # Heights array for histogram
        heights = [0] * self.n
        
        for r in range(self.n):
            # Update heights
            for c in range(self.n):
                if grid[r][c] == 1:
                    heights[c] += 1
                else:
                    heights[c] = 0
            
            # Largest rectangle in histogram
            stack = [] # stores indices
            
            # We iterate to n to handle the flushing of the stack
            for i in range(self.n + 1):
                h = heights[i] if i < self.n else 0
                
                while stack and heights[stack[-1]] >= h:
                    height = heights[stack.pop()]
                    width = i if not stack else i - stack[-1] - 1
                    area = height * width
                    
                    if area > best_area:
                        best_area = area
                        # Calculate coordinates
                        # The rectangle ends at column i-1 (inclusive)
                        # It spans 'width' columns, so starts at i - width
                        # It spans 'height' rows, ending at current row r
                        c2 = i - 1
                        c1 = i - width
                        r2 = r
                        r1 = r - height + 1
                        best_rect = (r1, c1, r2, c2)
                
                stack.append(i)
                
        return best_rect


def verify_formula(n: int, k: int, actual_answer: int, formula_name: str, formula_func):
    """Test if a formula matches the actual answer"""
    predicted = formula_func(n, k)
    match = "✓" if predicted == actual_answer else "✗"
    print(f"  {formula_name}: {predicted} {match}")
    return predicted == actual_answer


def main():
    """Test the solver on small and medium cases"""

    print("="*80)
    print("OPTIMIZED TILING SOLVER TEST")
    print("="*80)
    print()

    # Test cases: (n, k)
    test_cases = [
        (4, 2),   # Small, exhaustive
        (5, 0),   # Just to test n=5
        (25, 5),  # Large, heuristic + structured
    ]

    results = {}

    for n, k in test_cases:
        if k == 0 and n == 5: k = 2 # Approx
        
        print(f"\n{'='*80}")
        print(f"TEST CASE: n={n} (k={k})")
        print(f"{'='*80}\n")

        # Use more iterations for larger n
        iters = 50000 if n > 10 else 1000
        solver = GridTilingSolver(n, max_iters=iters)
        min_tiles, _ = solver.solve()

        results[(n, k)] = min_tiles

        # Verify against known formulas
        print(f"\nFormula Validation:")
        print(f"Actual answer (heuristic min): {min_tiles}")

        verify_formula(n, k, min_tiles, "n+2k-3", lambda n,k: n + 2*k - 3)
        verify_formula(n, k, min_tiles, "n+2k-2", lambda n,k: n + 2*k - 2)
        verify_formula(n, k, min_tiles, "2n-2  ", lambda n,k: 2*n - 2)

        print()

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)

    for (n, k), answer in results.items():
        formula_n_2k_3 = n + 2*k - 3
        match = "✓" if formula_n_2k_3 == answer else "✗"
        print(f"n={n} (k={k}): {answer} tiles  |  Formula n+2k-3 = {formula_n_2k_3} {match}")

    return results


if __name__ == "__main__":
    results = main()

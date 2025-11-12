#!/usr/bin/env python3

"""
MIT License

Copyright (c) 2025 Lin Yang, Yichen Huang

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import csv
import os
from typing import List, Dict, Optional

class BenchmarkLoader:
    """
    Utility class for loading and filtering IMO benchmark datasets.
    Supports loading from gradingbench, proofbench, and answerbench CSV files
    with optional level filtering.
    """

    def __init__(self, benchmark_dir: str = None):
        """
        Initialize the benchmark loader.

        Args:
            benchmark_dir: Path to the directory containing benchmark CSV files.
                          Defaults to ../imobench relative to this script.
        """
        if benchmark_dir is None:
            # Default to imobench directory relative to this script
            script_dir = os.path.dirname(os.path.abspath(__file__))
            benchmark_dir = os.path.join(os.path.dirname(script_dir), 'imobench')

        self.benchmark_dir = benchmark_dir
        self.gradingbench_path = os.path.join(benchmark_dir, 'gradingbench.csv')
        self.proofbench_path = os.path.join(benchmark_dir, 'proofbench.csv')
        self.answerbench_path = os.path.join(benchmark_dir, 'answerbench.csv')

    def load_gradingbench(self, level: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, str]]:
        """
        Load grading benchmark data with optional level filtering.

        Args:
            level: Level to filter by ('Basic', 'Advanced', or None for all).
                  Case-insensitive. If None, returns all entries.
            limit: Maximum number of entries to return. If None, returns all.

        Returns:
            List of dictionaries containing the benchmark entries.
            Each dictionary has keys: Grading ID, Problem ID, Problem, Solution,
            Grading guidelines, Response, Points, Reward, Problem Source
        """
        return self._load_benchmark_csv(self.gradingbench_path, 'Problem ID', level, limit)

    def load_proofbench(self, level: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, str]]:
        """
        Load proof benchmark data with optional level filtering.

        Args:
            level: Level to filter by ('Basic', 'Advanced', or None for all).
                  Case-insensitive. If None, returns all entries.
            limit: Maximum number of entries to return. If None, returns all.

        Returns:
            List of dictionaries containing the benchmark entries.
            Each dictionary has keys: Problem ID, Problem, Solution, Grading guidelines,
            Category, Level, Short Answer, Source
        """
        return self._load_benchmark_csv(self.proofbench_path, 'Problem ID', level, limit)

    def load_answerbench(self, limit: Optional[int] = None) -> List[Dict[str, str]]:
        """
        Load answer benchmark data (no level filtering available).

        Args:
            limit: Maximum number of entries to return. If None, returns all.

        Returns:
            List of dictionaries containing the benchmark entries.
            Each dictionary has keys: Problem ID, Problem, Short Answer,
            Category, Subcategory, Source
        """
        return self._load_benchmark_csv(self.answerbench_path, None, None, limit)

    def _load_benchmark_csv(
        self,
        csv_path: str,
        id_column: Optional[str],
        level: Optional[str],
        limit: Optional[int]
    ) -> List[Dict[str, str]]:
        """
        Internal method to load and filter a benchmark CSV file.

        Args:
            csv_path: Path to the CSV file
            id_column: Column name containing the problem ID (for level extraction)
            level: Level to filter by ('Basic', 'Advanced', or None)
            limit: Maximum number of entries to return

        Returns:
            List of dictionaries containing the filtered entries
        """
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"Benchmark file not found: {csv_path}")

        entries = []
        count = 0

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row in reader:
                # Apply level filter if specified
                if level is not None and id_column is not None:
                    problem_id = row.get(id_column, '')
                    entry_level = self._extract_level_from_id(problem_id)

                    # Skip if level doesn't match (case-insensitive comparison)
                    if entry_level.lower() != level.lower():
                        continue

                entries.append(row)
                count += 1

                # Apply limit if specified
                if limit is not None and count >= limit:
                    break

        return entries

    def _extract_level_from_id(self, problem_id: str) -> str:
        """
        Extract the level from a problem ID.

        Args:
            problem_id: Problem ID in format like 'PB-Basic-001' or 'PB-Advanced-001'

        Returns:
            The level string ('Basic', 'Advanced', or empty string if not found)
        """
        if not problem_id:
            return ''

        # Split by '-' and get the second part (assuming format like 'PB-Basic-001')
        parts = problem_id.split('-')
        if len(parts) >= 2:
            return parts[1]

        return ''

    def get_available_levels(self, benchmark_type: str = 'proofbench') -> List[str]:
        """
        Get list of available levels in a benchmark.

        Args:
            benchmark_type: Type of benchmark ('gradingbench' or 'proofbench')

        Returns:
            List of available level names
        """
        if benchmark_type == 'gradingbench':
            csv_path = self.gradingbench_path
            id_column = 'Problem ID'
        elif benchmark_type == 'proofbench':
            csv_path = self.proofbench_path
            id_column = 'Problem ID'
        else:
            raise ValueError(f"Unsupported benchmark type: {benchmark_type}")

        levels = set()

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                problem_id = row.get(id_column, '')
                level = self._extract_level_from_id(problem_id)
                if level:
                    levels.add(level)

        return sorted(list(levels))


def main():
    """
    Command-line interface for the benchmark loader.
    Allows listing and filtering benchmark entries.
    """
    import argparse

    parser = argparse.ArgumentParser(description='Load and filter IMO benchmark datasets')
    parser.add_argument('benchmark', choices=['gradingbench', 'proofbench', 'answerbench'],
                       help='Type of benchmark to load')
    parser.add_argument('--level', '-l', type=str, default=None,
                       help='Level to filter by (Basic, Advanced). Case-insensitive.')
    parser.add_argument('--limit', '-n', type=int, default=None,
                       help='Maximum number of entries to display')
    parser.add_argument('--list-levels', action='store_true',
                       help='List available levels in the benchmark')
    parser.add_argument('--benchmark-dir', type=str, default=None,
                       help='Path to benchmark directory (default: ../imobench)')

    args = parser.parse_args()

    loader = BenchmarkLoader(args.benchmark_dir)

    # List available levels if requested
    if args.list_levels:
        if args.benchmark in ['gradingbench', 'proofbench']:
            levels = loader.get_available_levels(args.benchmark)
            print(f"Available levels in {args.benchmark}: {', '.join(levels)}")
        else:
            print(f"{args.benchmark} does not support level filtering")
        return

    # Load the requested benchmark
    print(f"Loading {args.benchmark}...")
    if args.level:
        print(f"Filtering by level: {args.level}")
    if args.limit:
        print(f"Limit: {args.limit} entries")
    print()

    try:
        if args.benchmark == 'gradingbench':
            entries = loader.load_gradingbench(level=args.level, limit=args.limit)
        elif args.benchmark == 'proofbench':
            entries = loader.load_proofbench(level=args.level, limit=args.limit)
        else:  # answerbench
            entries = loader.load_answerbench(limit=args.limit)

        print(f"Loaded {len(entries)} entries")

        # Display a sample of the first entry if available
        if entries:
            print("\nSample entry (first):")
            print("-" * 80)
            for key, value in entries[0].items():
                # Truncate long values for display
                display_value = value[:200] + '...' if len(value) > 200 else value
                print(f"{key}: {display_value}")

    except FileNotFoundError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"Error loading benchmark: {e}")


if __name__ == "__main__":
    main()

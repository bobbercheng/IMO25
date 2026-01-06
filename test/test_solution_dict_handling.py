#!/usr/bin/env python3
"""
Unit tests for solution dict/string handling and anyOf schema generation.

Tests cover:
1. TypeError when passing dict solution to regex operations
2. anyOf range generation for blacklist
3. Schema validation
"""

import unittest
import json
import sys
import os

# Add code directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'code'))

from schema_blacklist import get_blacklist_constrained_schema


class TestSolutionDictHandling(unittest.TestCase):
    """Test that all code handles both dict and string solutions."""

    def test_get_solution_text_with_dict(self):
        """Test get_solution_text helper function."""
        from agent_gpt_oss import get_solution_text

        # Test with dict (structured output)
        solution_dict = {
            "solution": "Test solution text",
            "method": "test_method",
            "final_answer": 42
        }
        result = get_solution_text(solution_dict)
        self.assertEqual(result, "Test solution text")

        # Test with string (legacy output)
        solution_str = "Legacy solution text"
        result = get_solution_text(solution_str)
        self.assertEqual(result, "Legacy solution text")

        # Test with None
        result = get_solution_text(None)
        self.assertEqual(result, "")

    def test_extract_answer_simple_with_integer(self):
        """Test extract_answer_simple with integer final_answer (from schema type: integer)."""
        from agent_gpt_oss import extract_answer_simple

        # Test with integer final_answer (schema type: integer)
        solution_dict = {
            "solution": "Test solution text",
            "method": "test_method",
            "final_answer": 4048
        }
        result = extract_answer_simple(solution_dict)
        self.assertEqual(result, "4048")
        self.assertIsInstance(result, str)  # Should return string, not int

        # Test with string final_answer (legacy)
        solution_dict_str = {
            "solution": "Test solution text",
            "method": "test_method",
            "final_answer": "2025"
        }
        result = extract_answer_simple(solution_dict_str)
        self.assertEqual(result, "2025")
        self.assertIsInstance(result, str)




class TestSchemaGeneration(unittest.TestCase):
    """Test schema generation with anyOf constraints."""

    def test_schema_has_final_answer_field(self):
        """Test that schema includes final_answer field with anyOf ranges."""
        # Create a temporary blacklist file with correct format
        import tempfile
        blacklist = {
            "problem_id": "test",
            "solutions": [
                {"answer": 2025, "method": "test1"},
                {"answer": 4048, "method": "test2"},
                {"answer": 4050, "method": "test3"}
            ]
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(blacklist, f)
            blacklist_file = f.name
        # File is now closed and flushed

        try:
            # Generate schema (pass blacklist directly, not via file)
            problem_statement = "Test problem for n=2025"
            schema = get_blacklist_constrained_schema(
                blacklist_file,  # This won't be used since we pass blacklist
                problem_statement,
                blacklist=blacklist["solutions"]  # Pass blacklist directly
            )

            # Verify schema structure
            self.assertIn('properties', schema)
            self.assertIn('final_answer', schema['properties'])

            # Verify anyOf ranges
            final_answer = schema['properties']['final_answer']
            self.assertEqual(final_answer['type'], 'integer')
            self.assertIn('anyOf', final_answer)

            anyof_ranges = final_answer['anyOf']
            self.assertEqual(len(anyof_ranges), 4)

            # Verify ranges exclude blacklisted values
            # Should have: [1012-2024], [2026-4047], [4049], [4051-6075]
            self.assertEqual(anyof_ranges[0]['maximum'], 2024)  # Before 2025
            self.assertEqual(anyof_ranges[1]['minimum'], 2026)  # After 2025
            self.assertEqual(anyof_ranges[1]['maximum'], 4047)  # Before 4048
            self.assertEqual(anyof_ranges[2]['enum'], [4049])   # Between 4048-4050
            self.assertEqual(anyof_ranges[3]['minimum'], 4051)  # After 4050

        finally:
            os.unlink(blacklist_file)

    def test_schema_has_required_fields(self):
        """Test that schema marks all fields as required."""
        # Create empty blacklist file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"problem_id": "test", "solutions": []}, f)
            blacklist_file = f.name

        try:
            problem_statement = "Test problem for n=2025"
            schema = get_blacklist_constrained_schema(blacklist_file, problem_statement)

            # Verify required fields
            self.assertIn('required', schema)
            required_fields = schema['required']

            # Should require solution, method, and final_answer
            self.assertIn('solution', required_fields)
            self.assertIn('method', required_fields)
            self.assertIn('final_answer', required_fields)

        finally:
            os.unlink(blacklist_file)

    def test_schema_description_has_guidance(self):
        """Test that schema descriptions include proper guidance."""
        import tempfile
        blacklist = {"problem_id": "test", "solutions": [{"answer": 4048, "method": "test"}]}

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(blacklist, f)
            blacklist_file = f.name

        try:
            problem_statement = "Test problem"
            schema = get_blacklist_constrained_schema(blacklist_file, problem_statement, blacklist=blacklist["solutions"])

            # Check solution field description
            solution_desc = schema['properties']['solution']['description']
            self.assertIn('CRITICAL', solution_desc)
            self.assertIn('\\boxed', solution_desc)
            self.assertIn('final_answer', solution_desc)

            # Check final_answer field description
            final_answer_desc = schema['properties']['final_answer']['description']
            self.assertIn('MUST match', final_answer_desc)
            self.assertIn('\\boxed', final_answer_desc)
            self.assertIn('FORBIDDEN', final_answer_desc)

        finally:
            os.unlink(blacklist_file)


class TestSchemaBlacklistEnforcement(unittest.TestCase):
    """Test that anyOf ranges actually prevent blacklisted values."""

    def test_anyof_excludes_blacklisted_values(self):
        """Verify that anyOf ranges don't include blacklisted values."""
        import tempfile

        blacklisted = [2025, 4048, 4050]
        blacklist_data = {
            "problem_id": "test",
            "solutions": [{"answer": val, "method": "test"} for val in blacklisted]
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(blacklist_data, f)
            blacklist_file = f.name

        try:
            problem_statement = "Test problem for n=2025"
            schema = get_blacklist_constrained_schema(blacklist_file, problem_statement, blacklist=blacklist_data["solutions"])
            ranges = schema['properties']['final_answer']['anyOf']

            # Check that no range includes blacklisted values
            for blacklisted_val in blacklisted:
                for range_spec in ranges:
                    if 'enum' in range_spec:
                        self.assertNotIn(blacklisted_val, range_spec['enum'])
                    elif 'minimum' in range_spec and 'maximum' in range_spec:
                        # Value should be outside the range
                        is_outside = (blacklisted_val < range_spec['minimum'] or
                                     blacklisted_val > range_spec['maximum'])
                        self.assertTrue(is_outside,
                            f"{blacklisted_val} is inside range [{range_spec['minimum']}, {range_spec['maximum']}]")
        finally:
            os.unlink(blacklist_file)

    def test_anyof_includes_valid_values(self):
        """Verify that anyOf ranges include valid (non-blacklisted) values."""
        import tempfile

        blacklisted = [2025, 4048, 4050]
        blacklist_data = {
            "problem_id": "test",
            "solutions": [{"answer": val, "method": "test"} for val in blacklisted]
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(blacklist_data, f)
            blacklist_file = f.name

        try:
            problem_statement = "Test problem for n=2025"
            schema = get_blacklist_constrained_schema(blacklist_file, problem_statement, blacklist=blacklist_data["solutions"])
            ranges = schema['properties']['final_answer']['anyOf']

            # Test valid values that should be included
            valid_values = [1012, 2024, 2026, 4047, 4049, 4051, 6075]

            for valid_val in valid_values:
                found = False
                for range_spec in ranges:
                    if 'enum' in range_spec and valid_val in range_spec['enum']:
                        found = True
                        break
                    elif 'minimum' in range_spec and 'maximum' in range_spec:
                        if range_spec['minimum'] <= valid_val <= range_spec['maximum']:
                            found = True
                            break

                self.assertTrue(found, f"Valid value {valid_val} not found in any anyOf range")
        finally:
            os.unlink(blacklist_file)


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)

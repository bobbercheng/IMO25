#!/usr/bin/env python3
"""
Unit Test for API Retry Logic (2025-12-09)

Tests the send_api_request_with_retry() function to ensure it properly
handles transient errors with exponential backoff.

Run with: python code/test_retry_logic.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import unittest
from unittest.mock import patch, MagicMock, call
import requests


class TestAPIRetryLogic(unittest.TestCase):
    """Test API retry logic for transient errors"""

    def setUp(self):
        """Import agent_gpt_oss module"""
        import agent_gpt_oss
        self.module = agent_gpt_oss

    @patch('agent_gpt_oss.send_api_request')
    @patch('time.sleep')  # Mock sleep to speed up tests
    def test_retry_on_500_error(self, mock_sleep, mock_api_request):
        """Test that 500 errors trigger retry with exponential backoff"""
        # Simulate: fail twice with 500, then succeed
        mock_response = MagicMock()
        mock_response.status_code = 500

        error_500 = requests.exceptions.HTTPError()
        error_500.response = mock_response

        mock_api_request.side_effect = [
            error_500,  # First attempt: 500 error
            error_500,  # Second attempt: 500 error
            {'success': True}  # Third attempt: success
        ]

        # Call the retry wrapper
        result = self.module.send_api_request_with_retry(
            api_key="test_key",
            payload={"test": "data"},
            stream=False,
            request_label="Test"
        )

        # Verify result
        self.assertEqual(result, {'success': True})

        # Verify 3 attempts were made
        self.assertEqual(mock_api_request.call_count, 3)

        # Verify exponential backoff: sleep(2.0), sleep(4.0)
        self.assertEqual(mock_sleep.call_count, 2)
        mock_sleep.assert_any_call(2.0)
        mock_sleep.assert_any_call(4.0)

    @patch('agent_gpt_oss.send_api_request')
    @patch('time.sleep')
    def test_no_retry_on_400_error(self, mock_sleep, mock_api_request):
        """Test that 400 errors do NOT trigger retry (client error)"""
        mock_response = MagicMock()
        mock_response.status_code = 400

        error_400 = requests.exceptions.HTTPError()
        error_400.response = mock_response

        mock_api_request.side_effect = error_400

        # Call should raise immediately without retrying
        with self.assertRaises(requests.exceptions.HTTPError):
            self.module.send_api_request_with_retry(
                api_key="test_key",
                payload={"test": "data"},
                stream=False,
                request_label="Test"
            )

        # Verify only 1 attempt was made (no retries)
        self.assertEqual(mock_api_request.call_count, 1)

        # Verify no sleep calls (no retries)
        self.assertEqual(mock_sleep.call_count, 0)

    @patch('agent_gpt_oss.send_api_request')
    @patch('time.sleep')
    def test_retry_on_connection_error(self, mock_sleep, mock_api_request):
        """Test that connection errors trigger retry"""
        connection_error = requests.exceptions.ConnectionError("Connection refused")

        mock_api_request.side_effect = [
            connection_error,  # First attempt: connection error
            {'success': True}  # Second attempt: success
        ]

        result = self.module.send_api_request_with_retry(
            api_key="test_key",
            payload={"test": "data"},
            stream=False,
            request_label="Test"
        )

        self.assertEqual(result, {'success': True})
        self.assertEqual(mock_api_request.call_count, 2)
        self.assertEqual(mock_sleep.call_count, 1)

    @patch('agent_gpt_oss.send_api_request')
    @patch('time.sleep')
    def test_max_retries_exhausted(self, mock_sleep, mock_api_request):
        """Test that max retries is respected"""
        mock_response = MagicMock()
        mock_response.status_code = 500

        error_500 = requests.exceptions.HTTPError()
        error_500.response = mock_response

        # Always fail with 500
        mock_api_request.side_effect = error_500

        # Should retry 4 times (total 5 attempts) then raise
        with self.assertRaises(requests.exceptions.HTTPError):
            self.module.send_api_request_with_retry(
                api_key="test_key",
                payload={"test": "data"},
                stream=False,
                request_label="Test",
                max_retries=4
            )

        # Verify 5 total attempts (1 initial + 4 retries)
        self.assertEqual(mock_api_request.call_count, 5)

        # Verify 4 sleep calls (exponential: 2, 4, 8, 16)
        self.assertEqual(mock_sleep.call_count, 4)

    @patch('agent_gpt_oss.send_api_request')
    def test_success_on_first_try(self, mock_api_request):
        """Test that successful first attempt doesn't trigger retries"""
        mock_api_request.return_value = {'success': True}

        result = self.module.send_api_request_with_retry(
            api_key="test_key",
            payload={"test": "data"},
            stream=False,
            request_label="Test"
        )

        self.assertEqual(result, {'success': True})
        self.assertEqual(mock_api_request.call_count, 1)


def run_tests():
    """Run all tests and print summary"""
    print("=" * 80)
    print("API RETRY LOGIC UNIT TESTS")
    print("=" * 80)
    print()

    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestAPIRetryLogic)

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print()
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")

    if result.wasSuccessful():
        print()
        print("✅ ALL TESTS PASSED!")
        return 0
    else:
        print()
        print("❌ SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(run_tests())

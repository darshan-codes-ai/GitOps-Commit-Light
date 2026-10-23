"""
GitOps Commit Light — Asynchronous Lambda Failure Handling Automated Tests

These tests verify:
1. Production asynchronous invocation semantics: retryable transient failures
   propagate as unhandled invocation failures to trigger Lambda async retries and DLQ routing.
2. Permanent validation errors ('poison pills') are acknowledged cleanly (400)
   without raising, preventing wasteful and endless retry loops.
3. Offline handler compatibility is fully preserved.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LAMBDA_DIR = PROJECT_ROOT / "backend" / "lambda"
for path in [PROJECT_ROOT, LAMBDA_DIR]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from lambda_function import (
    CommitMessageError,
    CommitMessageProvider,
    EventValidationError,
    MockMQTTPublisher,
    MQTTPublishError,
    PermanentCommitMessageError,
    PermanentMQTTPublishError,
    StaticCommitMessageProvider,
    TransientCommitRetrievalError,
    TransientMQTTPublishError,
    UnsupportedEventError,
    is_retryable_error,
    lambda_handler,
    production_lambda_handler,
)

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def load_fixture(filename: str) -> dict:
    """Helper to load a JSON fixture file from tests/fixtures."""
    fixture_path = FIXTURES_DIR / filename
    with open(fixture_path, "r", encoding="utf-8") as f:
        return json.load(f)


# ==============================================================================
# 1. Error Classification Unit Tests
# ==============================================================================

class TestErrorClassification(unittest.TestCase):
    """Direct unit tests for the error classification strategy."""

    def test_permanent_errors_classified_as_non_retryable(self):
        """Verify that permanent event defects are classified as non-retryable."""
        permanent_errors = [
            EventValidationError("Missing required field repositoryName"),
            UnsupportedEventError("Unsupported event action referenceDeleted"),
            PermanentCommitMessageError("No message provider configured"),
            PermanentMQTTPublishError("Cannot publish to wildcard topic"),
        ]
        for err in permanent_errors:
            with self.subTest(error_type=type(err).__name__):
                self.assertFalse(
                    is_retryable_error(err),
                    f"{type(err).__name__} should be classified as permanent (non-retryable).",
                )

    def test_transient_infrastructure_errors_classified_as_retryable(self):
        """Verify that infrastructure errors are classified as transient/retryable."""
        retryable_errors = [
            TransientCommitRetrievalError("CodeCommit ThrottlingException"),
            TransientMQTTPublishError("AWS IoT Core endpoint timeout"),
            MQTTPublishError("General network disconnect"),
            ConnectionResetError("Socket reset by peer"),
            TimeoutError("TCP connection timed out"),
            OSError("Network unreachable"),
            RuntimeError("Unexpected unhandled exception"),
        ]
        for err in retryable_errors:
            with self.subTest(error_type=type(err).__name__):
                self.assertTrue(
                    is_retryable_error(err),
                    f"{type(err).__name__} should be classified as retryable.",
                )


# ==============================================================================
# 2. Production Lambda Entry Point Tests
# ==============================================================================

class TestProductionLambdaHandler(unittest.TestCase):
    """
    Tests verifying production_lambda_handler asynchronous EventBridge semantics.
    """

    def setUp(self):
        self.publisher = MockMQTTPublisher()
        self.provider = StaticCommitMessageProvider(default_message="feat: production ready")

    # --------------------------------------------------------------------------
    # Successful Processing
    # --------------------------------------------------------------------------

    def test_production_handler_successful_processing(self):
        """Verify successful end-to-end processing returns statusCode 200 with published confirmation."""
        event = load_fixture("event_valid_commit.json")
        response = production_lambda_handler(
            event,
            message_provider=self.provider,
            publisher=self.publisher,
        )

        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(response["status"], "success")
        self.assertTrue(response["published"])
        self.assertEqual(response["topic"], "gitops/commits")
        self.assertEqual(len(self.publisher.published_messages), 1)

    # --------------------------------------------------------------------------
    # Permanent Errors: Must NOT Raise (Clean Acknowledgment, No Retries)
    # --------------------------------------------------------------------------

    def test_permanent_validation_error_does_not_raise(self):
        """
        Verify that malformed events (missing fields) exit cleanly with code 400.
        EventBridge considers this acknowledged so it does NOT trigger infinite retries.
        """
        event = load_fixture("event_missing_required_fields.json")
        response = production_lambda_handler(
            event,
            message_provider=self.provider,
            publisher=self.publisher,
        )

        self.assertEqual(response["statusCode"], 400)
        self.assertEqual(response["status"], "error")
        self.assertEqual(response["errorType"], "EventValidationError")
        self.assertFalse(response["retryable"])
        self.assertEqual(len(self.publisher.published_messages), 0)

    def test_permanent_unsupported_action_does_not_raise(self):
        """
        Verify that unsupported actions (e.g. branch deleted) exit cleanly with code 400.
        Branch deletions do not trigger commit lights and must never be retried.
        """
        event = load_fixture("event_unsupported_action_deleted.json")
        response = production_lambda_handler(
            event,
            message_provider=self.provider,
            publisher=self.publisher,
        )

        self.assertEqual(response["statusCode"], 400)
        self.assertEqual(response["errorType"], "UnsupportedEventError")
        self.assertFalse(response["retryable"])
        self.assertEqual(len(self.publisher.published_messages), 0)

    def test_permanent_unsupported_source_does_not_raise(self):
        """
        Verify that non-CodeCommit sources exit cleanly with code 400 without retrying.
        """
        event = load_fixture("event_unsupported_source.json")
        response = production_lambda_handler(
            event,
            message_provider=self.provider,
            publisher=self.publisher,
        )

        self.assertEqual(response["statusCode"], 400)
        self.assertEqual(response["errorType"], "UnsupportedEventError")
        self.assertFalse(response["retryable"])
        self.assertEqual(len(self.publisher.published_messages), 0)

    def test_permanent_missing_commit_message_does_not_raise(self):
        """
        Verify that when a message is permanently unavailable without a provider,
        the handler acknowledges with 400 without triggering an endless retry loop.
        """
        event = load_fixture("event_valid_commit.json")
        response = production_lambda_handler(
            event,
            message_provider=None,  # No provider and event has no embedded message
            publisher=self.publisher,
        )

        self.assertEqual(response["statusCode"], 400)
        self.assertEqual(response["errorType"], "CommitMessageError")
        self.assertFalse(response["retryable"])
        self.assertEqual(len(self.publisher.published_messages), 0)

    # --------------------------------------------------------------------------
    # Transient Errors: MUST Raise (Trigger EventBridge Retries & DLQ)
    # --------------------------------------------------------------------------

    def test_transient_commit_retrieval_error_propagates_as_invocation_failure(self):
        """
        Verify that transient CodeCommit errors (e.g. throttling) are raised out
        of production_lambda_handler so AWS Lambda marks the invocation as failed.
        """
        event = load_fixture("event_valid_commit.json")

        class ThrottledCodeCommitProvider(CommitMessageProvider):
            def get_commit_message(self, repository: str, commit_id: str) -> str:
                raise TransientCommitRetrievalError("AWS CodeCommit API rate limit exceeded")

        with self.assertRaises(TransientCommitRetrievalError) as ctx:
            production_lambda_handler(
                event,
                message_provider=ThrottledCodeCommitProvider(),
                publisher=self.publisher,
            )

        self.assertIn("rate limit exceeded", str(ctx.exception))
        self.assertEqual(len(self.publisher.published_messages), 0)

    def test_transient_network_timeout_in_commit_retrieval_propagates(self):
        """
        Verify that raw network timeouts during commit retrieval wrap into
        TransientCommitRetrievalError and propagate out as an invocation failure.
        """
        event = load_fixture("event_valid_commit.json")

        class TimingOutProvider(CommitMessageProvider):
            def get_commit_message(self, repository: str, commit_id: str) -> str:
                raise TimeoutError("CodeCommit HTTPS connect timed out")

        with self.assertRaises(TransientCommitRetrievalError) as ctx:
            production_lambda_handler(
                event,
                message_provider=TimingOutProvider(),
                publisher=self.publisher,
            )

        self.assertIn("connect timed out", str(ctx.exception))
        self.assertEqual(len(self.publisher.published_messages), 0)

    def test_transient_mqtt_publish_error_propagates_as_invocation_failure(self):
        """
        Verify that transient IoT Core publish errors are raised out of
        production_lambda_handler to trigger EventBridge retries.
        """
        event = load_fixture("event_valid_commit.json")
        failing_publisher = MockMQTTPublisher(
            should_fail=True, fail_message="AWS IoT Core connection timeout"
        )

        with self.assertRaises(MQTTPublishError) as ctx:
            production_lambda_handler(
                event,
                message_provider=self.provider,
                publisher=failing_publisher,
            )

        self.assertIn("AWS IoT Core connection timeout", str(ctx.exception))
        self.assertEqual(len(failing_publisher.published_messages), 0)

    def test_publisher_returning_false_propagates_as_invocation_failure(self):
        """
        Verify that a publisher rejecting delivery (returning False) is raised as
        an invocation failure in production.
        """
        event = load_fixture("event_valid_commit.json")
        rejecting_publisher = MockMQTTPublisher(return_value=False)

        with self.assertRaises(MQTTPublishError) as ctx:
            production_lambda_handler(
                event,
                message_provider=self.provider,
                publisher=rejecting_publisher,
            )

        self.assertIn("returned False", str(ctx.exception))
        self.assertEqual(len(rejecting_publisher.published_messages), 0)

    def test_unexpected_runtime_exception_propagates_as_invocation_failure(self):
        """
        Verify that unforeseen exceptions propagate to avoid silent loss of events.
        """
        event = load_fixture("event_valid_commit.json")

        class CrashingProvider(CommitMessageProvider):
            def get_commit_message(self, repository: str, commit_id: str) -> str:
                raise RuntimeError("Internal unexpected crash")

        with self.assertRaises(Exception):
            production_lambda_handler(
                event,
                message_provider=CrashingProvider(),
                publisher=self.publisher,
            )

    # --------------------------------------------------------------------------
    # Offline Handler Backward Compatibility & Contract Preservation
    # --------------------------------------------------------------------------

    def test_offline_lambda_handler_retains_dictionary_response_for_transient_errors(self):
        """
        Verify that lambda_handler(raise_on_retryable=False) preserves the structured
        dictionary response with retryable=True for offline test runners.
        """
        event = load_fixture("event_valid_commit.json")

        class ThrottledProvider(CommitMessageProvider):
            def get_commit_message(self, repository: str, commit_id: str) -> str:
                raise TransientCommitRetrievalError("Rate limit exceeded")

        response = lambda_handler(
            event,
            message_provider=ThrottledProvider(),
            publisher=self.publisher,
            raise_on_retryable=False,
        )

        # Must return dict, not raise
        self.assertEqual(response["statusCode"], 500)
        self.assertEqual(response["status"], "error")
        self.assertTrue(response["retryable"])
        self.assertIn("Rate limit", response["message"])


if __name__ == "__main__":
    unittest.main()


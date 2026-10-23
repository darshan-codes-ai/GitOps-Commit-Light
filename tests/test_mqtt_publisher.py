"""
GitOps Commit Light — MQTT Publisher Automated Tests

These tests verify the MQTT publisher abstraction, MockMQTTPublisher behavior,
and integration with the lambda_handler entry point without connecting to AWS IoT Core.
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
    DEFAULT_MQTT_TOPIC,
    MockMQTTPublisher,
    MQTTPublishError,
    MQTTPublisher,
    PublishedMessage,
    StaticCommitMessageProvider,
    lambda_handler,
)

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def load_fixture(filename: str) -> dict:
    """Helper to load a JSON fixture file from tests/fixtures."""
    fixture_path = FIXTURES_DIR / filename
    with open(fixture_path, "r", encoding="utf-8") as f:
        return json.load(f)


# ==============================================================================
# 1. MockMQTTPublisher Unit Tests
# ==============================================================================

class TestMockMQTTPublisher(unittest.TestCase):
    """Direct unit tests for the MockMQTTPublisher class."""

    def setUp(self):
        self.publisher = MockMQTTPublisher()

    def test_successful_publish_records_message(self):
        """Verify that publish returns True and accurately records topic and payload."""
        payload = {"schemaVersion": 1, "message": "test commit"}
        result = self.publisher.publish("gitops/commits", payload)

        self.assertTrue(result)
        self.assertEqual(len(self.publisher.published_messages), 1)

        recorded = self.publisher.published_messages[0]
        self.assertIsInstance(recorded, PublishedMessage)
        self.assertEqual(recorded.topic, "gitops/commits")
        self.assertEqual(recorded.payload, payload)
        self.assertEqual(self.publisher.last_message(), recorded)

    def test_publisher_records_multiple_messages_in_order(self):
        """Verify recording of sequential publications."""
        self.publisher.publish("topic/1", {"msg": "first"})
        self.publisher.publish("topic/2", {"msg": "second"})

        self.assertEqual(len(self.publisher.published_messages), 2)
        self.assertEqual(self.publisher.published_messages[0].topic, "topic/1")
        self.assertEqual(self.publisher.published_messages[1].topic, "topic/2")
        self.assertEqual(self.publisher.last_message().topic, "topic/2")

    def test_publisher_clear(self):
        """Verify that clear() empties the recorded message history."""
        self.publisher.publish("gitops/commits", {"msg": "test"})
        self.assertEqual(len(self.publisher.published_messages), 1)

        self.publisher.clear()
        self.assertEqual(len(self.publisher.published_messages), 0)
        self.assertIsNone(self.publisher.last_message())

    def test_published_messages_returns_defensive_copy(self):
        """Verify that modifying the returned list does not mutate internal publisher state."""
        self.publisher.publish("gitops/commits", {"msg": "test"})
        messages = self.publisher.published_messages
        messages.clear()

        self.assertEqual(len(self.publisher.published_messages), 1)

    def test_invalid_topic_empty_string(self):
        """Verify that empty or whitespace topic strings raise MQTTPublishError."""
        for empty_topic in ["", "   "]:
            with self.subTest(topic=repr(empty_topic)):
                with self.assertRaises(MQTTPublishError) as ctx:
                    self.publisher.publish(empty_topic, {"msg": "test"})
                self.assertIn("non-empty string", str(ctx.exception))

    def test_invalid_topic_non_string(self):
        """Verify that non-string topic values raise MQTTPublishError."""
        for invalid_topic in [None, 123, ["topic"]]:
            with self.subTest(topic=invalid_topic):
                with self.assertRaises(MQTTPublishError) as ctx:
                    self.publisher.publish(invalid_topic, {"msg": "test"})
                self.assertIn("non-empty string", str(ctx.exception))

    def test_invalid_topic_wildcards(self):
        """Verify that topics with wildcard characters ('+' or '#') are rejected."""
        for wildcard_topic in ["gitops/+", "gitops/#", "+/commits", "gitops/commits/#"]:
            with self.subTest(topic=wildcard_topic):
                with self.assertRaises(MQTTPublishError) as ctx:
                    self.publisher.publish(wildcard_topic, {"msg": "test"})
                self.assertIn("wildcard", str(ctx.exception).lower())

    def test_invalid_payload_non_dict(self):
        """Verify that non-dict payloads raise MQTTPublishError."""
        for invalid_payload in ["string", [1, 2, 3], None, 42]:
            with self.subTest(payload=type(invalid_payload).__name__):
                with self.assertRaises(MQTTPublishError) as ctx:
                    self.publisher.publish("gitops/commits", invalid_payload)
                self.assertIn("dictionary", str(ctx.exception).lower())

    def test_invalid_payload_non_serializable(self):
        """Verify that payloads containing non-JSON-serializable objects raise MQTTPublishError."""
        unserializable_payload = {
            "key": "value",
            "invalid_set": {1, 2, 3},  # sets cannot be serialized by standard json.dumps
        }
        with self.assertRaises(MQTTPublishError) as ctx:
            self.publisher.publish("gitops/commits", unserializable_payload)
        self.assertIn("not JSON-serializable", str(ctx.exception))

    def test_simulated_publish_failure(self):
        """Verify that publisher configured with should_fail=True raises MQTTPublishError."""
        failing_publisher = MockMQTTPublisher(
            should_fail=True, fail_message="Broker connection lost"
        )
        with self.assertRaises(MQTTPublishError) as ctx:
            failing_publisher.publish("gitops/commits", {"msg": "test"})

        self.assertIn("Broker connection lost", str(ctx.exception))
        self.assertEqual(len(failing_publisher.published_messages), 0)

    def test_mock_publisher_return_value_false_records_nothing(self):
        """Verify that MockMQTTPublisher(return_value=False) returns False without error and records no message."""
        rejecting_publisher = MockMQTTPublisher(return_value=False)
        result = rejecting_publisher.publish("gitops/commits", {"msg": "test"})

        self.assertFalse(result)
        self.assertEqual(len(rejecting_publisher.published_messages), 0)
        self.assertIsNone(rejecting_publisher.last_message())


# ==============================================================================
# 2. Handler + Publisher Integration Tests
# ==============================================================================

class TestHandlerPublisherIntegration(unittest.TestCase):
    """Tests verifying lambda_handler coordination with MQTTPublisher."""

    def setUp(self):
        self.publisher = MockMQTTPublisher()
        self.provider = StaticCommitMessageProvider(default_message="feat: OLED commit light")

    def test_successful_publish_to_default_topic(self):
        """Verify end-to-end publishing to the default 'gitops/commits' topic."""
        event = load_fixture("event_valid_commit.json")
        response = lambda_handler(
            event,
            message_provider=self.provider,
            publisher=self.publisher,
        )

        # 1. Verify structured success response
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(response["status"], "success")
        self.assertTrue(response.get("published"))
        self.assertEqual(response.get("topic"), "gitops/commits")

        # 2. Verify exact topic recorded
        self.assertEqual(len(self.publisher.published_messages), 1)
        recorded = self.publisher.last_message()
        self.assertEqual(recorded.topic, "gitops/commits")

        # 3. Verify exact payload fields
        payload = recorded.payload
        self.assertEqual(payload["schemaVersion"], 1)
        self.assertEqual(payload["eventId"], "synthetic-event-id-001")
        self.assertEqual(payload["repository"], "gitops-commit-light")
        self.assertEqual(payload["branch"], "main")
        self.assertEqual(payload["commitId"], "0123456789abcdef0123456789abcdef01234567")
        self.assertEqual(payload["message"], "feat: OLED commit light")
        self.assertEqual(payload["timestamp"], "2026-10-23T11:00:00Z")

    def test_publish_to_custom_topic(self):
        """Verify publishing to an explicitly specified custom valid topic."""
        event = load_fixture("event_valid_commit.json")
        custom_topic = "gitops/custom-branch"

        response = lambda_handler(
            event,
            message_provider=self.provider,
            publisher=self.publisher,
            mqtt_topic=custom_topic,
        )

        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(response["topic"], custom_topic)
        self.assertEqual(self.publisher.last_message().topic, custom_topic)

    def test_no_publish_when_event_validation_fails(self):
        """Verify that malformed events are rejected without publishing any message."""
        event = load_fixture("event_missing_required_fields.json")
        response = lambda_handler(
            event,
            message_provider=self.provider,
            publisher=self.publisher,
        )

        self.assertEqual(response["statusCode"], 400)
        self.assertEqual(response["status"], "error")
        self.assertEqual(response["errorType"], "EventValidationError")

        # CRITICAL: Verify zero messages were published
        self.assertEqual(len(self.publisher.published_messages), 0)

    def test_no_publish_when_event_unsupported(self):
        """Verify that unsupported events (e.g. branch deleted) do not trigger publication."""
        event = load_fixture("event_unsupported_action_deleted.json")
        response = lambda_handler(
            event,
            message_provider=self.provider,
            publisher=self.publisher,
        )

        self.assertEqual(response["statusCode"], 400)
        self.assertEqual(response["errorType"], "UnsupportedEventError")
        self.assertEqual(len(self.publisher.published_messages), 0)

    def test_no_publish_when_commit_message_unavailable(self):
        """Verify that missing commit messages abort execution before publishing."""
        event = load_fixture("event_valid_commit.json")  # has no embedded message
        response = lambda_handler(
            event,
            message_provider=None,  # No provider supplied
            publisher=self.publisher,
        )

        self.assertEqual(response["statusCode"], 400)
        self.assertEqual(response["errorType"], "CommitMessageError")

        # CRITICAL: Verify zero messages were published
        self.assertEqual(len(self.publisher.published_messages), 0)

    def test_publisher_failure_handled_cleanly(self):
        """Verify that publisher failures return a 500 status without crashing the handler."""
        event = load_fixture("event_valid_commit.json")
        failing_publisher = MockMQTTPublisher(
            should_fail=True, fail_message="AWS IoT Core connection timeout"
        )

        response = lambda_handler(
            event,
            message_provider=self.provider,
            publisher=failing_publisher,
        )

        self.assertEqual(response["statusCode"], 500)
        self.assertEqual(response["status"], "error")
        self.assertEqual(response["errorType"], "MQTTPublishError")
        self.assertIn("AWS IoT Core connection timeout", response["message"])
        self.assertEqual(len(failing_publisher.published_messages), 0)

    def test_invalid_topic_rejected_by_handler(self):
        """Verify that passing an invalid topic returns a structured 500 error."""
        event = load_fixture("event_valid_commit.json")
        response = lambda_handler(
            event,
            message_provider=self.provider,
            publisher=self.publisher,
            mqtt_topic="gitops/+",  # Invalid wildcard topic
        )

        self.assertEqual(response["statusCode"], 500)
        self.assertEqual(response["errorType"], "MQTTPublishError")
        self.assertIn("wildcard", response["message"].lower())
        self.assertEqual(len(self.publisher.published_messages), 0)

    def test_publisher_returning_false_aborts_success_report(self):
        """Regression test: verify that a publisher returning False is never reported as successful."""
        event = load_fixture("event_valid_commit.json")
        rejecting_publisher = MockMQTTPublisher(return_value=False)

        response = lambda_handler(
            event,
            message_provider=self.provider,
            publisher=rejecting_publisher,
        )

        # Must return error, never success
        self.assertEqual(response["statusCode"], 500)
        self.assertEqual(response["status"], "error")
        self.assertEqual(response["errorType"], "MQTTPublishError")
        self.assertIn("returned False", response["message"])
        self.assertFalse(response.get("published", False))
        self.assertEqual(len(rejecting_publisher.published_messages), 0)

    def test_custom_publisher_stub_returning_false(self):
        """Regression test: verify an external publisher stub returning False fails safely."""
        event = load_fixture("event_valid_commit.json")

        class StubRejectingPublisher(MQTTPublisher):
            def publish(self, topic: str, payload: dict) -> bool:
                return False

        response = lambda_handler(
            event,
            message_provider=self.provider,
            publisher=StubRejectingPublisher(),
        )

        self.assertEqual(response["statusCode"], 500)
        self.assertEqual(response["status"], "error")
        self.assertEqual(response["errorType"], "MQTTPublishError")
        self.assertFalse(response.get("published", False))

    def test_publisher_returning_non_boolean_truthy_is_rejected(self):
        """Verify that returning non-boolean truthy values (e.g. 1 or 'OK') is rejected as invalid."""
        event = load_fixture("event_valid_commit.json")

        class NonBoolPublisher(MQTTPublisher):
            def publish(self, topic: str, payload: dict) -> bool:
                return 1  # Truthy integer, but not boolean True

        response = lambda_handler(
            event,
            message_provider=self.provider,
            publisher=NonBoolPublisher(),
        )

        self.assertEqual(response["statusCode"], 500)
        self.assertEqual(response["errorType"], "MQTTPublishError")
        self.assertFalse(response.get("published", False))

    def test_validation_failure_prevents_publishing_even_with_failing_publisher(self):
        """Verify that malformed events abort with 400 before the publisher is ever invoked."""
        event = load_fixture("event_missing_required_fields.json")
        failing_publisher = MockMQTTPublisher(
            should_fail=True, fail_message="Should never be reached"
        )

        response = lambda_handler(
            event,
            message_provider=self.provider,
            publisher=failing_publisher,
        )

        # Must be EventValidationError (400), not MQTTPublishError (500)
        self.assertEqual(response["statusCode"], 400)
        self.assertEqual(response["errorType"], "EventValidationError")
        self.assertEqual(len(failing_publisher.published_messages), 0)


if __name__ == "__main__":
    unittest.main()


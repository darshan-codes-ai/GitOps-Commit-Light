"""
GitOps Commit Light — Offline Event Processing Automated Tests

These tests use Python's built-in unittest framework and run entirely offline
without requiring internet access, AWS credentials, or physical hardware.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

# Ensure both project root and backend/lambda are in sys.path.
# (Note: 'lambda' is a reserved Python keyword, so we add the backend/lambda
# directory to sys.path directly to mirror the AWS Lambda runtime environment).
PROJECT_ROOT = Path(__file__).resolve().parent.parent
LAMBDA_DIR = PROJECT_ROOT / "backend" / "lambda"
for path in [PROJECT_ROOT, LAMBDA_DIR]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from lambda_function import (
    CommitMessageError,
    CommitMessageProvider,
    EventValidationError,
    ParsedCommitEvent,
    StaticCommitMessageProvider,
    UnsupportedEventError,
    build_notification_payload,
    lambda_handler,
    parse_event,
)

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def load_fixture(filename: str) -> dict:
    """Helper to load a JSON fixture file from tests/fixtures."""
    fixture_path = FIXTURES_DIR / filename
    with open(fixture_path, "r", encoding="utf-8") as f:
        return json.load(f)


# ==============================================================================
# 1. Event Parsing Tests
# ==============================================================================

class TestEventParsing(unittest.TestCase):
    """Tests for validating and parsing EventBridge CodeCommit events."""

    def test_parse_valid_commit_fixture(self):
        """Verify successful extraction of all fields from a valid referenceUpdated event."""
        event = load_fixture("event_valid_commit.json")
        parsed = parse_event(event)

        self.assertIsInstance(parsed, ParsedCommitEvent)
        self.assertEqual(parsed.event_id, "synthetic-event-id-001")
        self.assertEqual(parsed.timestamp, "2026-10-23T11:00:00Z")
        self.assertEqual(parsed.repository, "gitops-commit-light")
        self.assertEqual(parsed.branch, "main")
        self.assertEqual(parsed.commit_id, "0123456789abcdef0123456789abcdef01234567")

    def test_parse_valid_reference_created(self):
        """Verify that branch creation (referenceCreated) is recognized as a valid event action."""
        event = load_fixture("event_valid_commit.json")
        event["detail"]["event"] = "referenceCreated"
        parsed = parse_event(event)

        self.assertEqual(parsed.repository, "gitops-commit-light")
        self.assertEqual(parsed.commit_id, "0123456789abcdef0123456789abcdef01234567")

    def test_fallback_when_event_id_missing(self):
        """Verify that a missing top-level event ID triggers the documented fallback."""
        event = load_fixture("event_valid_commit.json")
        del event["id"]

        parsed = parse_event(event)
        self.assertTrue(parsed.event_id.startswith("fallback-"))
        self.assertGreater(len(parsed.event_id), len("fallback-"))

    def test_fallback_when_event_id_empty_string(self):
        """Verify that an empty top-level event ID triggers the fallback."""
        event = load_fixture("event_valid_commit.json")
        event["id"] = "   "

        parsed = parse_event(event)
        self.assertTrue(parsed.event_id.startswith("fallback-"))

    def test_fallback_when_timestamp_missing(self):
        """Verify that a missing event timestamp triggers the UTC ISO8601 fallback."""
        event = load_fixture("event_valid_commit.json")
        del event["time"]

        parsed = parse_event(event)
        self.assertTrue(parsed.timestamp.endswith("Z"))
        self.assertIn("T", parsed.timestamp)

    def test_malformed_event_non_dict(self):
        """Verify that passing non-dictionary payloads raises EventValidationError."""
        for invalid_input in [None, "invalid-string", [1, 2, 3], 42]:
            with self.subTest(invalid_input=invalid_input):
                with self.assertRaises(EventValidationError) as ctx:
                    parse_event(invalid_input)
                self.assertIn("JSON object", str(ctx.exception))

    def test_missing_detail_container(self):
        """Verify that an event without a 'detail' object raises EventValidationError."""
        event = load_fixture("event_valid_commit.json")
        del event["detail"]

        with self.assertRaises(EventValidationError) as ctx:
            parse_event(event)
        self.assertIn("detail", str(ctx.exception))

    def test_missing_repository_name(self):
        """Verify missing repositoryName raises EventValidationError."""
        event = load_fixture("event_valid_commit.json")
        del event["detail"]["repositoryName"]

        with self.assertRaises(EventValidationError) as ctx:
            parse_event(event)
        self.assertIn("repositoryName", str(ctx.exception))

    def test_missing_branch_name(self):
        """Verify missing referenceName raises EventValidationError."""
        event = load_fixture("event_valid_commit.json")
        del event["detail"]["referenceName"]

        with self.assertRaises(EventValidationError) as ctx:
            parse_event(event)
        self.assertIn("referenceName", str(ctx.exception))

    def test_missing_commit_id(self):
        """Verify missing commitId raises EventValidationError."""
        event = load_fixture("event_valid_commit.json")
        del event["detail"]["commitId"]

        with self.assertRaises(EventValidationError) as ctx:
            parse_event(event)
        self.assertIn("commitId", str(ctx.exception))

    def test_fixture_missing_required_fields(self):
        """Verify that the synthetic missing fields fixture is rejected."""
        event = load_fixture("event_missing_required_fields.json")
        with self.assertRaises(EventValidationError):
            parse_event(event)

    def test_unsupported_event_source(self):
        """Verify that non-CodeCommit sources raise UnsupportedEventError."""
        event = load_fixture("event_unsupported_source.json")
        with self.assertRaises(UnsupportedEventError) as ctx:
            parse_event(event)
        self.assertIn("source", str(ctx.exception))

    def test_unsupported_detail_type(self):
        """Verify that non-CodeCommit detail-type raises UnsupportedEventError."""
        event = load_fixture("event_valid_commit.json")
        event["detail-type"] = "Some Other State Change"

        with self.assertRaises(UnsupportedEventError) as ctx:
            parse_event(event)
        self.assertIn("detail-type", str(ctx.exception))

    def test_unsupported_action_deleted(self):
        """Verify that branch deletion (referenceDeleted) raises UnsupportedEventError."""
        event = load_fixture("event_unsupported_action_deleted.json")
        with self.assertRaises(UnsupportedEventError) as ctx:
            parse_event(event)
        self.assertIn("referenceDeleted", str(ctx.exception))

    def test_unsupported_reference_type_tag(self):
        """Verify that tag updates (referenceType != branch) raise UnsupportedEventError."""
        event = load_fixture("event_valid_commit.json")
        event["detail"]["referenceType"] = "tag"

        with self.assertRaises(UnsupportedEventError) as ctx:
            parse_event(event)
        self.assertIn("referenceType", str(ctx.exception))


# ==============================================================================
# 2. Payload Construction Tests
# ==============================================================================

class TestPayloadConstruction(unittest.TestCase):
    """Tests for target notification payload generation and schema validation."""

    def test_payload_schema_and_field_types_with_provider_object(self):
        """Verify exact schema version, field names, and data types with provider object."""
        event = load_fixture("event_valid_commit.json")
        provider = StaticCommitMessageProvider(default_message="docs: add architecture specs")

        payload = build_notification_payload(event, message_provider=provider)

        expected_keys = {
            "schemaVersion",
            "eventId",
            "repository",
            "branch",
            "commitId",
            "message",
            "timestamp",
        }
        self.assertEqual(set(payload.keys()), expected_keys)

        # Field types
        self.assertIsInstance(payload["schemaVersion"], int)
        self.assertEqual(payload["schemaVersion"], 1)
        self.assertIsInstance(payload["eventId"], str)
        self.assertIsInstance(payload["repository"], str)
        self.assertIsInstance(payload["branch"], str)
        self.assertIsInstance(payload["commitId"], str)
        self.assertIsInstance(payload["message"], str)
        self.assertIsInstance(payload["timestamp"], str)

        # Values
        self.assertEqual(payload["eventId"], "synthetic-event-id-001")
        self.assertEqual(payload["repository"], "gitops-commit-light")
        self.assertEqual(payload["branch"], "main")
        self.assertEqual(payload["commitId"], "0123456789abcdef0123456789abcdef01234567")
        self.assertEqual(payload["message"], "docs: add architecture specs")
        self.assertEqual(payload["timestamp"], "2026-10-23T11:00:00Z")

    def test_payload_construction_with_callable_provider(self):
        """Verify that a simple Python callable function can serve as the provider."""
        event = load_fixture("event_valid_commit.json")

        def mock_provider(repo: str, commit_id: str) -> str:
            return f"feat: automated commit for {repo} ({commit_id[:7]})"

        payload = build_notification_payload(event, message_provider=mock_provider)
        self.assertEqual(
            payload["message"],
            "feat: automated commit for gitops-commit-light (0123456)",
        )

    def test_payload_construction_with_embedded_fixture_message(self):
        """Verify that synthetic fixture messages are used when no provider is given."""
        event = load_fixture("event_valid_with_fixture_message.json")
        payload = build_notification_payload(event, message_provider=None)

        self.assertEqual(payload["message"], "feat: update offline test fixtures")
        self.assertEqual(payload["eventId"], "synthetic-event-id-002")

    def test_missing_commit_message_raises_error(self):
        """Verify CommitMessageError when no provider is supplied and no fixture message exists."""
        event = load_fixture("event_valid_commit.json")  # Does not contain commitMessage

        with self.assertRaises(CommitMessageError) as ctx:
            build_notification_payload(event, message_provider=None)
        self.assertIn("Commit message could not be obtained", str(ctx.exception))

    def test_provider_raises_error_handled(self):
        """Verify that an exception inside the provider is converted to CommitMessageError."""
        event = load_fixture("event_valid_commit.json")

        class FailingProvider(CommitMessageProvider):
            def get_commit_message(self, repository: str, commit_id: str) -> str:
                raise ConnectionResetError("Simulated provider failure")

        with self.assertRaises(CommitMessageError) as ctx:
            build_notification_payload(event, message_provider=FailingProvider())
        self.assertIn("Simulated provider failure", str(ctx.exception))

    def test_empty_commit_message_rejected(self):
        """Verify that empty or whitespace-only commit messages are rejected."""
        event = load_fixture("event_valid_commit.json")
        provider = StaticCommitMessageProvider(default_message="   ")

        with self.assertRaises(CommitMessageError) as ctx:
            build_notification_payload(event, message_provider=provider)
        self.assertIn("empty", str(ctx.exception))


# ==============================================================================
# 3. AWS Lambda Handler Tests
# ==============================================================================

class TestLambdaHandler(unittest.TestCase):
    """Tests for the top-level lambda_handler entry point."""

    def test_handler_success(self):
        """Verify lambda_handler returns 200 with structured payload on success."""
        event = load_fixture("event_valid_commit.json")
        provider = StaticCommitMessageProvider(default_message="fix: OLED display refresh")

        response = lambda_handler(event, message_provider=provider)

        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(response["status"], "success")
        self.assertIn("payload", response)
        self.assertEqual(response["payload"]["schemaVersion"], 1)
        self.assertEqual(response["payload"]["message"], "fix: OLED display refresh")

    def test_handler_returns_400_on_validation_error(self):
        """Verify lambda_handler returns 400 on malformed events."""
        event = load_fixture("event_missing_required_fields.json")
        response = lambda_handler(event)

        self.assertEqual(response["statusCode"], 400)
        self.assertEqual(response["status"], "error")
        self.assertEqual(response["errorType"], "EventValidationError")
        self.assertIn("repositoryName", response["message"])

    def test_handler_returns_400_on_unsupported_event(self):
        """Verify lambda_handler returns 400 on unsupported events."""
        event = load_fixture("event_unsupported_action_deleted.json")
        response = lambda_handler(event)

        self.assertEqual(response["statusCode"], 400)
        self.assertEqual(response["status"], "error")
        self.assertEqual(response["errorType"], "UnsupportedEventError")
        self.assertIn("referenceDeleted", response["message"])

    def test_handler_returns_400_on_missing_message(self):
        """Verify lambda_handler returns 400 when commit message cannot be retrieved."""
        event = load_fixture("event_valid_commit.json")
        response = lambda_handler(event, message_provider=None)

        self.assertEqual(response["statusCode"], 400)
        self.assertEqual(response["status"], "error")
        self.assertEqual(response["errorType"], "CommitMessageError")


if __name__ == "__main__":
    unittest.main()

"""
Offline automated tests for production AWS CodeCommit provider and AWS IoT Core publisher.

Verifies:
1. Boto3CodeCommitProvider:
   - Calling get_commit with correct repositoryName and commitId arguments.
   - Extracting and trimming commit message strings.
   - Raising PermanentCommitMessageError on missing or empty commit messages.
   - Error classification: permanent (CommitDoesNotExist, RepositoryDoesNotExist, ValidationException)
     vs transient (Throttling, 5xx server error, network timeout).
   - Safe execution when boto3 is not installed.
2. Boto3IotDataPublisher:
   - Calling publish with topic, qos, and payload bytes.
   - Validating topic (rejecting wildcards) and payload (JSON-serializable).
   - Endpoint URL resolution from environment variable or parameter with https:// enforcement.
   - Error classification: permanent (Unauthorized, InvalidRequest) vs transient (Throttling, 5xx, network timeout).
   - Strict boolean confirmation of HTTP 200 response.
3. Production Handler Wiring:
   - End-to-end processing with injected Boto3CodeCommitProvider and Boto3IotDataPublisher.
   - Transient failure propagation as unhandled exceptions (triggering Lambda async retries).
   - Permanent failure acknowledgment with code 400 without raising.
   - Verification that production_lambda_handler constructs production adapters when unsupplied.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import unittest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LAMBDA_DIR = PROJECT_ROOT / "backend" / "lambda"
for path in [PROJECT_ROOT, LAMBDA_DIR]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from lambda_function import (
    Boto3CodeCommitProvider,
    CommitMessageError,
    EventValidationError,
    PermanentCommitMessageError,
    TransientCommitRetrievalError,
    production_lambda_handler,
)
from publisher import (
    DEFAULT_MQTT_TOPIC,
    Boto3IotDataPublisher,
    MQTTPublishError,
    PermanentMQTTPublishError,
    TransientMQTTPublishError,
)

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def load_fixture(filename: str) -> dict:
    """Helper to load a JSON fixture file from tests/fixtures."""
    fixture_path = FIXTURES_DIR / filename
    with open(fixture_path, "r", encoding="utf-8") as f:
        return json.load(f)


class FakeClientError(Exception):
    """Simulates botocore.exceptions.ClientError for offline testing without boto3."""

    def __init__(
        self,
        code: str,
        message: str = "",
        status_code: int = 400,
        operation_name: str = "operation",
    ):
        self.response = {
            "Error": {
                "Code": code,
                "Message": message or f"Simulated error: {code}",
            },
            "ResponseMetadata": {
                "HTTPStatusCode": status_code,
            },
        }
        self.operation_name = operation_name
        super().__init__(
            f"An error occurred ({code}) when calling the {operation_name} operation: {message}"
        )


class StubCodeCommitClient:
    """Stub CodeCommit client for offline testing."""

    def __init__(self, return_value=None, side_effect=None):
        self.return_value = return_value
        self.side_effect = side_effect
        self.calls = []

    def get_commit(self, **kwargs):
        self.calls.append(kwargs)
        if self.side_effect:
            if isinstance(self.side_effect, Exception):
                raise self.side_effect
            return self.side_effect(**kwargs)
        return self.return_value


class StubIotDataClient:
    """Stub IoT Data Plane client for offline testing."""

    def __init__(self, return_value=None, side_effect=None):
        self.return_value = return_value or {
            "ResponseMetadata": {"HTTPStatusCode": 200}
        }
        self.side_effect = side_effect
        self.calls = []

    def publish(self, **kwargs):
        self.calls.append(kwargs)
        if self.side_effect:
            if isinstance(self.side_effect, Exception):
                raise self.side_effect
            return self.side_effect(**kwargs)
        return self.return_value


# ==============================================================================
# Phase 2 Tests: Boto3CodeCommitProvider
# ==============================================================================

class TestBoto3CodeCommitProvider(unittest.TestCase):
    """Offline unit tests for Boto3CodeCommitProvider."""

    def test_get_commit_message_request_arguments(self):
        """Verify get_commit is called with expected repositoryName and commitId."""
        stub_client = StubCodeCommitClient(
            return_value={
                "commit": {
                    "commitId": "317f2652b047545934fbcd810",
                    "message": "feat: initialize commit light\n",
                }
            }
        )
        provider = Boto3CodeCommitProvider(client=stub_client)
        msg = provider.get_commit_message("my-gitops-repo", "317f2652b047545934fbcd810")

        self.assertEqual(len(stub_client.calls), 1)
        self.assertEqual(
            stub_client.calls[0],
            {
                "repositoryName": "my-gitops-repo",
                "commitId": "317f2652b047545934fbcd810",
            },
        )
        self.assertEqual(msg, "feat: initialize commit light")

    def test_get_commit_message_empty_string_raises_permanent_error(self):
        """Verify that an empty or whitespace commit message raises PermanentCommitMessageError."""
        stub_client = StubCodeCommitClient(
            return_value={"commit": {"message": "   \n\t  "}}
        )
        provider = Boto3CodeCommitProvider(client=stub_client)

        with self.assertRaises(PermanentCommitMessageError) as ctx:
            provider.get_commit_message("my-repo", "commit123")
        self.assertIn("empty commit message", str(ctx.exception))

    def test_get_commit_missing_commit_dict_raises_permanent_error(self):
        """Verify that malformed CodeCommit responses missing 'commit' raise permanent error."""
        stub_client = StubCodeCommitClient(return_value={"unexpected": "data"})
        provider = Boto3CodeCommitProvider(client=stub_client)

        with self.assertRaises(PermanentCommitMessageError):
            provider.get_commit_message("my-repo", "commit123")

    def test_get_commit_missing_message_field_raises_permanent_error(self):
        """Verify that response missing 'message' inside 'commit' raises permanent error."""
        stub_client = StubCodeCommitClient(return_value={"commit": {"author": "dev"}})
        provider = Boto3CodeCommitProvider(client=stub_client)

        with self.assertRaises(PermanentCommitMessageError):
            provider.get_commit_message("my-repo", "commit123")

    def test_get_commit_invalid_input_parameters(self):
        """Verify that empty repository or commitId parameters are rejected immediately."""
        provider = Boto3CodeCommitProvider(client=StubCodeCommitClient())

        with self.assertRaises(PermanentCommitMessageError):
            provider.get_commit_message("", "commit123")
        with self.assertRaises(PermanentCommitMessageError):
            provider.get_commit_message("my-repo", "   ")

    def test_codecommit_permanent_errors(self):
        """Verify that CodeCommit non-existent resource errors are classified as permanent."""
        permanent_codes = [
            "CommitDoesNotExistException",
            "CommitIdDoesNotExistException",
            "RepositoryDoesNotExistException",
            "InvalidCommitIdException",
            "InvalidRepositoryNameException",
            "ValidationException",
        ]
        for code in permanent_codes:
            stub = StubCodeCommitClient(
                side_effect=FakeClientError(code, "Resource not found", status_code=400)
            )
            provider = Boto3CodeCommitProvider(client=stub)
            with self.assertRaises(PermanentCommitMessageError, msg=f"Expected permanent for {code}"):
                provider.get_commit_message("my-repo", "commit123")

    def test_codecommit_transient_throttling(self):
        """Verify that ThrottlingException is classified as a transient retryable error."""
        stub = StubCodeCommitClient(
            side_effect=FakeClientError("ThrottlingException", "Rate exceeded", status_code=429)
        )
        provider = Boto3CodeCommitProvider(client=stub)
        with self.assertRaises(TransientCommitRetrievalError) as ctx:
            provider.get_commit_message("my-repo", "commit123")
        self.assertIn("ThrottlingException", str(ctx.exception))

    def test_codecommit_transient_500_error(self):
        """Verify that HTTP 500 server errors are classified as transient."""
        stub = StubCodeCommitClient(
            side_effect=FakeClientError("InternalServerError", "Server error", status_code=500)
        )
        provider = Boto3CodeCommitProvider(client=stub)
        with self.assertRaises(TransientCommitRetrievalError):
            provider.get_commit_message("my-repo", "commit123")

    def test_codecommit_transient_network_timeout(self):
        """Verify that network timeout and connection errors are classified as transient."""
        stub = StubCodeCommitClient(side_effect=TimeoutError("Connection timed out"))
        provider = Boto3CodeCommitProvider(client=stub)
        with self.assertRaises(TransientCommitRetrievalError) as ctx:
            provider.get_commit_message("my-repo", "commit123")
        self.assertIn("timed out", str(ctx.exception))

    def test_boto3_missing_lazy_instantiation(self):
        """Verify that attempting to get a client when boto3 is missing raises Transient error."""
        provider = Boto3CodeCommitProvider(client=None)
        # In this offline environment, boto3 is not installed
        with self.assertRaises(TransientCommitRetrievalError) as ctx:
            provider._get_client()
        self.assertIn("boto3", str(ctx.exception).lower())


# ==============================================================================
# Phase 3 Tests: Boto3IotDataPublisher
# ==============================================================================

class TestBoto3IotDataPublisher(unittest.TestCase):
    """Offline unit tests for Boto3IotDataPublisher."""

    def setUp(self):
        self.valid_payload = {
            "schemaVersion": 1,
            "eventId": "evt-123",
            "repository": "my-repo",
            "branch": "main",
            "commitId": "317f265",
            "message": "fix: update led flash timing",
            "timestamp": "2026-10-23T12:00:00Z",
        }

    def test_publish_request_arguments(self):
        """Verify publish calls boto3 iot-data client with topic, qos, and valid UTF-8 payload bytes."""
        stub_client = StubIotDataClient()
        publisher = Boto3IotDataPublisher(
            client=stub_client,
            endpoint_url="https://fake-ats.iot.us-east-1.amazonaws.com",
            qos=0,
        )

        result = publisher.publish(DEFAULT_MQTT_TOPIC, self.valid_payload)
        self.assertTrue(result)
        self.assertEqual(len(stub_client.calls), 1)

        call = stub_client.calls[0]
        self.assertEqual(call["topic"], "gitops/commits")
        self.assertEqual(call["qos"], 0)
        self.assertIsInstance(call["payload"], bytes)

        # Confirm payload bytes decode to the exact original dictionary
        decoded = json.loads(call["payload"].decode("utf-8"))
        self.assertEqual(decoded, self.valid_payload)

    def test_publish_missing_endpoint_url_raises_permanent_error(self):
        """Verify that instantiating client without an endpoint URL raises PermanentMQTTPublishError."""
        # Ensure environment variables are not set
        orig_endpoint = os.environ.pop("IOT_DATA_ENDPOINT", None)
        orig_aws_endpoint = os.environ.pop("AWS_IOT_DATA_ENDPOINT", None)
        try:
            publisher = Boto3IotDataPublisher(client=None, endpoint_url=None)
            with self.assertRaises(PermanentMQTTPublishError) as ctx:
                publisher.publish("gitops/commits", self.valid_payload)
            self.assertIn("endpoint URL is not configured", str(ctx.exception))
        finally:
            if orig_endpoint:
                os.environ["IOT_DATA_ENDPOINT"] = orig_endpoint
            if orig_aws_endpoint:
                os.environ["AWS_IOT_DATA_ENDPOINT"] = orig_aws_endpoint

    def test_publish_endpoint_url_formats_https(self):
        """Verify that endpoint URLs without https:// scheme are automatically prefixed."""
        publisher = Boto3IotDataPublisher(
            endpoint_url="my-ats.iot.us-east-1.amazonaws.com"
        )
        resolved = publisher._resolve_endpoint_url()
        self.assertEqual(resolved, "https://my-ats.iot.us-east-1.amazonaws.com")

    def test_publish_endpoint_resolved_from_environment(self):
        """Verify that IOT_DATA_ENDPOINT environment variable is read correctly."""
        os.environ["IOT_DATA_ENDPOINT"] = "env-ats.iot.us-east-1.amazonaws.com"
        try:
            publisher = Boto3IotDataPublisher()
            resolved = publisher._resolve_endpoint_url()
            self.assertEqual(resolved, "https://env-ats.iot.us-east-1.amazonaws.com")
        finally:
            os.environ.pop("IOT_DATA_ENDPOINT", None)

    def test_publish_invalid_topic_wildcards(self):
        """Verify that topics with wildcard characters ('+' or '#') are rejected."""
        publisher = Boto3IotDataPublisher(client=StubIotDataClient())
        with self.assertRaises(PermanentMQTTPublishError):
            publisher.publish("gitops/+", self.valid_payload)
        with self.assertRaises(PermanentMQTTPublishError):
            publisher.publish("gitops/#", self.valid_payload)

    def test_publish_invalid_payload_non_dict(self):
        """Verify that non-dict payloads raise PermanentMQTTPublishError."""
        publisher = Boto3IotDataPublisher(client=StubIotDataClient())
        with self.assertRaises(PermanentMQTTPublishError):
            publisher.publish("gitops/commits", "raw-string-payload")

    def test_publish_non_json_serializable_payload(self):
        """Verify that payloads with non-JSON types raise PermanentMQTTPublishError."""
        publisher = Boto3IotDataPublisher(client=StubIotDataClient())
        with self.assertRaises(PermanentMQTTPublishError):
            publisher.publish("gitops/commits", {"set": {1, 2, 3}})

    def test_publish_transient_throttling(self):
        """Verify that ThrottlingException from IoT Data Plane is classified as transient."""
        stub = StubIotDataClient(
            side_effect=FakeClientError("ThrottlingException", "Rate exceeded", status_code=429)
        )
        publisher = Boto3IotDataPublisher(client=stub)
        with self.assertRaises(TransientMQTTPublishError) as ctx:
            publisher.publish("gitops/commits", self.valid_payload)
        self.assertIn("ThrottlingException", str(ctx.exception))

    def test_publish_transient_server_500(self):
        """Verify that 5xx errors from IoT Data Plane are classified as transient."""
        stub = StubIotDataClient(
            side_effect=FakeClientError("InternalFailureException", "IoT internal error", status_code=500)
        )
        publisher = Boto3IotDataPublisher(client=stub)
        with self.assertRaises(TransientMQTTPublishError):
            publisher.publish("gitops/commits", self.valid_payload)

    def test_publish_permanent_unauthorized(self):
        """Verify that UnauthorizedException is classified as permanent (non-retryable)."""
        stub = StubIotDataClient(
            side_effect=FakeClientError("UnauthorizedException", "Forbidden topic", status_code=403)
        )
        publisher = Boto3IotDataPublisher(client=stub)
        with self.assertRaises(PermanentMQTTPublishError):
            publisher.publish("gitops/commits", self.valid_payload)

    def test_publish_non_200_http_response(self):
        """Verify that non-200 HTTP responses raise TransientMQTTPublishError."""
        stub = StubIotDataClient(
            return_value={"ResponseMetadata": {"HTTPStatusCode": 503}}
        )
        publisher = Boto3IotDataPublisher(client=stub)
        with self.assertRaises(TransientMQTTPublishError):
            publisher.publish("gitops/commits", self.valid_payload)


# ==============================================================================
# Phase 4 & 5 Tests: Production Wiring & End-to-End Integration
# ==============================================================================

class TestProductionHandlerIntegration(unittest.TestCase):
    """Offline unit tests for production_lambda_handler with production adapters."""

    def setUp(self):
        self.event = load_fixture("event_valid_commit.json")

    def test_production_handler_e2e_success(self):
        """Verify successful end-to-end processing with injected Boto3CodeCommitProvider and Boto3IotDataPublisher."""
        stub_cc = StubCodeCommitClient(
            return_value={
                "commit": {
                    "commitId": "317f2652b047545934fbcd810",
                    "message": "feat: connect live boto3 adapters",
                }
            }
        )
        stub_iot = StubIotDataClient()

        provider = Boto3CodeCommitProvider(client=stub_cc)
        publisher = Boto3IotDataPublisher(client=stub_iot)

        response = production_lambda_handler(
            self.event,
            message_provider=provider,
            publisher=publisher,
        )

        self.assertEqual(response["statusCode"], 200)
        self.assertTrue(response["published"])
        self.assertEqual(response["topic"], "gitops/commits")
        self.assertEqual(response["payload"]["message"], "feat: connect live boto3 adapters")

        # Verify IoT client received the publish call
        self.assertEqual(len(stub_iot.calls), 1)
        self.assertEqual(stub_iot.calls[0]["topic"], "gitops/commits")

    def test_production_handler_propagates_transient_codecommit_error(self):
        """Verify that transient CodeCommit errors propagate as unhandled exceptions."""
        stub_cc = StubCodeCommitClient(
            side_effect=FakeClientError("ThrottlingException", "Rate exceeded", status_code=429)
        )
        stub_iot = StubIotDataClient()

        provider = Boto3CodeCommitProvider(client=stub_cc)
        publisher = Boto3IotDataPublisher(client=stub_iot)

        with self.assertRaises(TransientCommitRetrievalError):
            production_lambda_handler(
                self.event,
                message_provider=provider,
                publisher=publisher,
            )

    def test_production_handler_propagates_transient_iot_error(self):
        """Verify that transient IoT errors propagate as unhandled exceptions."""
        stub_cc = StubCodeCommitClient(
            return_value={"commit": {"message": "feat: test IoT transient error"}}
        )
        stub_iot = StubIotDataClient(
            side_effect=FakeClientError("InternalFailureException", "Service error", status_code=500)
        )

        provider = Boto3CodeCommitProvider(client=stub_cc)
        publisher = Boto3IotDataPublisher(client=stub_iot)

        with self.assertRaises(TransientMQTTPublishError):
            production_lambda_handler(
                self.event,
                message_provider=provider,
                publisher=publisher,
            )

    def test_production_handler_swallows_permanent_codecommit_error(self):
        """Verify that permanent CodeCommit errors exit cleanly with code 400 without raising."""
        stub_cc = StubCodeCommitClient(
            side_effect=FakeClientError("CommitIdDoesNotExistException", "Commit not found", status_code=400)
        )
        stub_iot = StubIotDataClient()

        provider = Boto3CodeCommitProvider(client=stub_cc)
        publisher = Boto3IotDataPublisher(client=stub_iot)

        response = production_lambda_handler(
            self.event,
            message_provider=provider,
            publisher=publisher,
        )

        self.assertEqual(response["statusCode"], 400)
        self.assertFalse(response["retryable"])
        self.assertEqual(len(stub_iot.calls), 0)

    def test_production_handler_constructs_production_adapters_by_default(self):
        """
        Verify that production_lambda_handler genuinely constructs Boto3CodeCommitProvider
        and Boto3IotDataPublisher when invoked without adapter arguments.
        """
        # When invoked with no provider, Boto3CodeCommitProvider is constructed and attempts
        # to acquire a boto3 client. Since boto3 is not installed in the offline test environment,
        # it raises TransientCommitRetrievalError explicitly stating boto3 is required.
        with self.assertRaises(TransientCommitRetrievalError) as ctx:
            production_lambda_handler(self.event)

        self.assertIn("boto3", str(ctx.exception).lower())


if __name__ == "__main__":
    unittest.main()


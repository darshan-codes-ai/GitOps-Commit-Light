"""
GitOps Commit Light — GitHub Webhook Handler Automated Tests (Stage 1 Test Scaffolding)

Architecture Role:
    GitHub push webhook -> Amazon API Gateway (HTTP API v2) -> AWS Lambda -> AWS IoT Core MQTT

Test Specifications & Contracts:
    1. Valid GitHub push event with valid HMAC-SHA256 signature -> 200 OK + MQTT publish.
    2. Invalid signature -> 403 Forbidden without publishing.
    3. Missing signature -> 401 Unauthorized without publishing.
    4. Missing webhook secret -> 500 Internal Server Error (fail closed; never accept).
    5. Ping event -> 200 OK without publishing.
    6. Branch deletion -> 200 OK (ignored) without publishing.
    7. Non-monitored branch -> 200 OK (ignored) without publishing.
    8. Unsupported event type (e.g. issues, pull_request) -> 200 OK without publishing.
    9. Malformed JSON -> 400 Bad Request without publishing.
    10. Base64-encoded API Gateway request body -> decoded and verified correctly.
    11. Missing or malformed required commit fields -> rejected/ignored without publishing.
    12. Temporary publisher failure -> 502 Bad Gateway to allow GitHub webhook redelivery.
    13. Repeated delivery ID -> explicitly tests and documents stateless processing behavior.
    14. Case-insensitive HTTP header handling -> handles lower, upper, and mixed-case headers.
    15. Invalid signatures never invoke the publisher -> zero calls to publisher.publish().

Note on Stage 1 Scope:
    This file establishes the strict behavior contracts for the future handler.
    In accordance with Stage 1 constraints, production files (lambda_function.py, publisher.py)
    are not modified. If github_webhook_handler is not yet implemented, these tests are
    discovered and reported as skipped until Stage 2 implementation.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from pathlib import Path
import sys
from typing import Any, Dict, Optional, Union
import unittest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LAMBDA_DIR = PROJECT_ROOT / "backend" / "lambda"
for path in [PROJECT_ROOT, LAMBDA_DIR]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from publisher import (
    DEFAULT_MQTT_TOPIC,
    MockMQTTPublisher,
    MQTTPublishError,
    TransientMQTTPublishError,
)

# Attempt import of handler
try:
    from lambda_function import _clear_webhook_secret_cache, github_webhook_handler
    HANDLER_AVAILABLE = True
except ImportError:
    try:
        from github_webhook import _clear_webhook_secret_cache, github_webhook_handler
        HANDLER_AVAILABLE = True
    except ImportError:
        HANDLER_AVAILABLE = False
        github_webhook_handler = None
        _clear_webhook_secret_cache = lambda: None


SYNTHETIC_WEBHOOK_SECRET = "synthetic_test_secret_never_use_in_production_12345"
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def load_fixture(filename: str) -> dict:
    """Load and parse JSON fixture from tests/fixtures."""
    fixture_path = FIXTURES_DIR / filename
    with open(fixture_path, "r", encoding="utf-8") as f:
        return json.load(f)


def compute_hmac_sha256(secret: str, raw_body_bytes: bytes) -> str:
    """Compute standard GitHub 'sha256=<hex>' signature over raw payload bytes."""
    digest = hmac.new(
        key=secret.encode("utf-8"),
        msg=raw_body_bytes,
        digestmod=hashlib.sha256,
    ).hexdigest()
    return f"sha256={digest}"


def build_apigateway_v2_event(
    body: Union[str, bytes, dict],
    event_type: str = "push",
    delivery_id: str = "72d3162e-cc78-11e3-81ab-4c9367dc0958",
    secret: Optional[str] = SYNTHETIC_WEBHOOK_SECRET,
    signature_override: Optional[str] = None,
    include_signature: bool = True,
    is_base64: bool = False,
    headers_case: str = "lower",
) -> Dict[str, Any]:
    """
    Construct a synthetic Amazon API Gateway HTTP API (payload format v2.0) proxy event.

    Args:
        body: Request body (dict, json string, or raw bytes).
        event_type: Value for GitHub event header (e.g. 'push', 'ping', 'issues').
        delivery_id: GitHub delivery GUID header.
        secret: Secret used to compute HMAC-SHA256 signature if not overridden.
        signature_override: Explicit signature string (e.g. for testing invalid signatures).
        include_signature: Whether to include the X-Hub-Signature-256 header.
        is_base64: Whether to base64-encode body and set isBase64Encoded=True.
        headers_case: 'lower' (standard v2.0), 'upper', or 'mixed'.
    """
    if isinstance(body, dict):
        raw_body_bytes = json.dumps(body, separators=(",", ":")).encode("utf-8")
        body_str = raw_body_bytes.decode("utf-8")
    elif isinstance(body, bytes):
        raw_body_bytes = body
        body_str = body.decode("utf-8", errors="replace")
    else:
        body_str = str(body)
        raw_body_bytes = body_str.encode("utf-8")

    if is_base64:
        payload_body = base64.b64encode(raw_body_bytes).decode("ascii")
    else:
        payload_body = body_str

    # Compute or assign signature
    sig_header_val = None
    if include_signature:
        if signature_override is not None:
            sig_header_val = signature_override
        elif secret is not None:
            sig_header_val = compute_hmac_sha256(secret, raw_body_bytes)

    # Build headers dictionary according to requested casing
    if headers_case == "mixed":
        headers: Dict[str, str] = {
            "Content-Type": "application/json",
            "User-Agent": "GitHub-Hookshot/1e17cb0",
            "X-GitHub-Delivery": delivery_id,
            "X-GitHub-Event": event_type,
        }
        if sig_header_val is not None:
            headers["X-Hub-Signature-256"] = sig_header_val
    elif headers_case == "upper":
        headers = {
            "CONTENT-TYPE": "application/json",
            "USER-AGENT": "GitHub-Hookshot/1e17cb0",
            "X-GITHUB-DELIVERY": delivery_id,
            "X-GITHUB-EVENT": event_type,
        }
        if sig_header_val is not None:
            headers["X-HUB-SIGNATURE-256"] = sig_header_val
    else:  # lower (default API Gateway v2.0)
        headers = {
            "content-type": "application/json",
            "user-agent": "github-hookshot/1e17cb0",
            "x-github-delivery": delivery_id,
            "x-github-event": event_type,
        }
        if sig_header_val is not None:
            headers["x-hub-signature-256"] = sig_header_val

    return {
        "version": "2.0",
        "routeKey": "POST /webhook/github",
        "rawPath": "/webhook/github",
        "rawQueryString": "",
        "headers": headers,
        "requestContext": {
            "http": {
                "method": "POST",
                "path": "/webhook/github",
                "protocol": "HTTP/1.1",
                "sourceIp": "192.0.2.1",
                "userAgent": "GitHub-Hookshot/1e17cb0",
            }
        },
        "body": payload_body,
        "isBase64Encoded": is_base64,
    }


# ==============================================================================
# GitHub Webhook Test Suite
# ==============================================================================

@unittest.skipUnless(
    HANDLER_AVAILABLE,
    "github_webhook_handler is not implemented yet (pending Stage 2 implementation)",
)
class TestGitHubWebhookHandler(unittest.TestCase):
    """
    Automated offline tests for GitHub webhook event processing and MQTT publishing.
    """

    def setUp(self) -> None:
        """Configure clean test environment with synthetic secret and mock publisher."""
        _clear_webhook_secret_cache()
        self.publisher = MockMQTTPublisher()
        self.secret = SYNTHETIC_WEBHOOK_SECRET
        self.original_env_secret = os.environ.get("GITHUB_WEBHOOK_SECRET")
        self.original_env_secret_arn = os.environ.get("GITHUB_WEBHOOK_SECRET_ARN")
        os.environ["GITHUB_WEBHOOK_SECRET"] = self.secret
        os.environ.pop("GITHUB_WEBHOOK_SECRET_ARN", None)

    def tearDown(self) -> None:
        """Restore environment variables and clear secret cache."""
        _clear_webhook_secret_cache()
        if self.original_env_secret is not None:
            os.environ["GITHUB_WEBHOOK_SECRET"] = self.original_env_secret
        else:
            os.environ.pop("GITHUB_WEBHOOK_SECRET", None)

        if self.original_env_secret_arn is not None:
            os.environ["GITHUB_WEBHOOK_SECRET_ARN"] = self.original_env_secret_arn
        else:
            os.environ.pop("GITHUB_WEBHOOK_SECRET_ARN", None)

    # --------------------------------------------------------------------------
    # 1. Valid GitHub push event with valid HMAC-SHA256 signature
    # --------------------------------------------------------------------------
    def test_valid_signature_push_event_publishes_mqtt(self) -> None:
        """Verify that a valid push event with matching HMAC publishes Schema v1 payload to MQTT."""
        fixture = load_fixture("github_push_valid.json")
        delivery_id = "72d3162e-cc78-11e3-81ab-4c9367dc0958"
        event = build_apigateway_v2_event(
            body=fixture,
            event_type="push",
            delivery_id=delivery_id,
            secret=self.secret,
        )

        response = github_webhook_handler(event, publisher=self.publisher, secret=self.secret)

        self.assertEqual(response.get("statusCode"), 200)
        self.assertEqual(len(self.publisher.published_messages), 1)

        msg = self.publisher.published_messages[0]
        self.assertEqual(msg.topic, DEFAULT_MQTT_TOPIC)
        payload = msg.payload

        # Schema v1 Invariant Checks
        self.assertEqual(payload["schemaVersion"], 1)
        self.assertEqual(payload["eventId"], delivery_id)
        self.assertEqual(payload["repository"], "GitOps-Commit-Light")
        self.assertEqual(payload["branch"], "main")
        self.assertEqual(payload["commitId"], "0123456789abcdef0123456789abcdef01234567")
        self.assertEqual(payload["message"], "feat: add GitHub webhook support for commit light")
        self.assertEqual(payload["timestamp"], "2026-10-23T11:00:00Z")

    # --------------------------------------------------------------------------
    # 2. Invalid signature: reject without publishing
    # --------------------------------------------------------------------------
    def test_invalid_signature_rejects_without_publishing(self) -> None:
        """Verify that an invalid HMAC signature returns 403 Forbidden and aborts publication."""
        fixture = load_fixture("github_push_valid.json")
        bad_signature = "sha256=0000000000000000000000000000000000000000000000000000000000000000"
        event = build_apigateway_v2_event(
            body=fixture,
            event_type="push",
            signature_override=bad_signature,
            secret=self.secret,
        )

        response = github_webhook_handler(event, publisher=self.publisher, secret=self.secret)

        self.assertEqual(response.get("statusCode"), 403)
        self.assertEqual(len(self.publisher.published_messages), 0)

    # --------------------------------------------------------------------------
    # 3. Missing signature: reject without publishing
    # --------------------------------------------------------------------------
    def test_missing_signature_rejects_without_publishing(self) -> None:
        """Verify that a request missing X-Hub-Signature-256 returns 401 Unauthorized."""
        fixture = load_fixture("github_push_valid.json")
        event = build_apigateway_v2_event(
            body=fixture,
            event_type="push",
            include_signature=False,
            secret=self.secret,
        )

        response = github_webhook_handler(event, publisher=self.publisher, secret=self.secret)

        self.assertEqual(response.get("statusCode"), 401)
        self.assertEqual(len(self.publisher.published_messages), 0)

    # --------------------------------------------------------------------------
    # 4. Missing webhook secret: fail closed; never accept the request
    # --------------------------------------------------------------------------
    def test_missing_webhook_secret_fails_closed(self) -> None:
        """Verify that missing secret in environment causes 500 error and never accepts requests."""
        os.environ.pop("GITHUB_WEBHOOK_SECRET", None)
        fixture = load_fixture("github_push_valid.json")
        event = build_apigateway_v2_event(
            body=fixture,
            event_type="push",
            secret="some_secret",
        )

        # Call with secret=None to enforce reading from unset environment
        response = github_webhook_handler(event, publisher=self.publisher, secret=None)

        self.assertEqual(response.get("statusCode"), 500)
        self.assertEqual(len(self.publisher.published_messages), 0)

    # --------------------------------------------------------------------------
    # 5. Ping event: return success without publishing
    # --------------------------------------------------------------------------
    def test_ping_event_returns_success_without_publishing(self) -> None:
        """Verify that GitHub 'ping' events return 200 OK without dispatching MQTT messages."""
        fixture = load_fixture("github_ping_event.json")
        event = build_apigateway_v2_event(
            body=fixture,
            event_type="ping",
            secret=self.secret,
        )

        response = github_webhook_handler(event, publisher=self.publisher, secret=self.secret)

        self.assertEqual(response.get("statusCode"), 200)
        self.assertEqual(len(self.publisher.published_messages), 0)

    # --------------------------------------------------------------------------
    # 6. Branch deletion: ignore without publishing
    # --------------------------------------------------------------------------
    def test_branch_deletion_ignored_without_publishing(self) -> None:
        """Verify that branch deletion pushes (deleted=true) are ignored without publishing."""
        fixture = load_fixture("github_push_branch_deleted.json")
        event = build_apigateway_v2_event(
            body=fixture,
            event_type="push",
            secret=self.secret,
        )

        response = github_webhook_handler(event, publisher=self.publisher, secret=self.secret)

        self.assertEqual(response.get("statusCode"), 200)
        self.assertEqual(len(self.publisher.published_messages), 0)

    # --------------------------------------------------------------------------
    # 7. Non-monitored branch: ignore without publishing
    # --------------------------------------------------------------------------
    def test_non_monitored_branch_ignored_without_publishing(self) -> None:
        """Verify that pushes to branches other than 'main' return 200 OK without publishing."""
        fixture = load_fixture("github_push_non_monitored_branch.json")
        event = build_apigateway_v2_event(
            body=fixture,
            event_type="push",
            secret=self.secret,
        )

        response = github_webhook_handler(
            event,
            publisher=self.publisher,
            secret=self.secret,
            monitored_branch="main",
        )

        self.assertEqual(response.get("statusCode"), 200)
        self.assertEqual(len(self.publisher.published_messages), 0)

    # --------------------------------------------------------------------------
    # 8. Unsupported event type: safely ignore without publishing
    # --------------------------------------------------------------------------
    def test_unsupported_event_type_safely_ignored_without_publishing(self) -> None:
        """Verify that non-push events (e.g. issues, star) return 200 OK without publishing."""
        fixture = load_fixture("github_unsupported_event.json")
        event = build_apigateway_v2_event(
            body=fixture,
            event_type="issues",
            secret=self.secret,
        )

        response = github_webhook_handler(event, publisher=self.publisher, secret=self.secret)

        self.assertEqual(response.get("statusCode"), 200)
        self.assertEqual(len(self.publisher.published_messages), 0)

    # --------------------------------------------------------------------------
    # 9. Malformed JSON: reject without publishing
    # --------------------------------------------------------------------------
    def test_malformed_json_body_rejected_without_publishing(self) -> None:
        """Verify that non-JSON or truncated body returns 400 Bad Request."""
        malformed_body = "{ unquoted_key: invalid_json, "
        event = build_apigateway_v2_event(
            body=malformed_body,
            event_type="push",
            secret=self.secret,
        )

        response = github_webhook_handler(event, publisher=self.publisher, secret=self.secret)

        self.assertEqual(response.get("statusCode"), 400)
        self.assertEqual(len(self.publisher.published_messages), 0)

    # --------------------------------------------------------------------------
    # 10. Base64-encoded API Gateway request body
    # --------------------------------------------------------------------------
    def test_base64_encoded_request_body_supported(self) -> None:
        """Verify that API Gateway events with isBase64Encoded=True are decoded and verified."""
        fixture = load_fixture("github_push_valid.json")
        event = build_apigateway_v2_event(
            body=fixture,
            event_type="push",
            is_base64=True,
            secret=self.secret,
        )

        response = github_webhook_handler(event, publisher=self.publisher, secret=self.secret)

        self.assertEqual(response.get("statusCode"), 200)
        self.assertEqual(len(self.publisher.published_messages), 1)
        self.assertEqual(
            self.publisher.published_messages[0].payload["commitId"],
            "0123456789abcdef0123456789abcdef01234567",
        )

    # --------------------------------------------------------------------------
    # 11. Missing or malformed required commit fields
    # --------------------------------------------------------------------------
    def test_missing_or_malformed_required_commit_fields(self) -> None:
        """Verify that push events missing required commit metadata return 400 without publishing."""
        fixture = load_fixture("github_push_missing_fields.json")
        event = build_apigateway_v2_event(
            body=fixture,
            event_type="push",
            secret=self.secret,
        )

        response = github_webhook_handler(event, publisher=self.publisher, secret=self.secret)

        self.assertIn(response.get("statusCode"), (400, 200))
        self.assertEqual(len(self.publisher.published_messages), 0)

    # --------------------------------------------------------------------------
    # 12. Temporary publisher failure: return an appropriate server error
    # --------------------------------------------------------------------------
    def test_temporary_publisher_failure_returns_server_error(self) -> None:
        """Verify that downstream publisher failures return 502 to trigger GitHub redelivery."""
        failing_publisher = MockMQTTPublisher(should_fail=True)
        fixture = load_fixture("github_push_valid.json")
        event = build_apigateway_v2_event(
            body=fixture,
            event_type="push",
            secret=self.secret,
        )

        response = github_webhook_handler(event, publisher=failing_publisher, secret=self.secret)

        # 502 Bad Gateway / 500 signals downstream failure to API Gateway & GitHub
        self.assertIn(response.get("statusCode"), (500, 502))

    # --------------------------------------------------------------------------
    # 13. Repeated delivery ID: explicitly document and test chosen behavior
    # --------------------------------------------------------------------------
    def test_repeated_delivery_id_stateless_behavior(self) -> None:
        """
        Document and verify stateless delivery handling.

        Deduplication Design Note:
            In this stateless serverless AWS Lambda handler, invocations do not maintain
            a persistent cache across distinct containers without an external datastore
            (e.g., Amazon DynamoDB).
            Therefore, repeated deliveries (such as GitHub manual redeliveries) are processed
            cleanly, embedding the delivery GUID into 'eventId' for downstream consumer
            idempotency (the ESP32 microcontroller or MQTT subscriber).
            This test verifies that the handler deterministically processes redeliveries
            without crashing or corrupting state.
        """
        fixture = load_fixture("github_push_valid.json")
        delivery_id = "repeated-delivery-uuid-999"
        event = build_apigateway_v2_event(
            body=fixture,
            event_type="push",
            delivery_id=delivery_id,
            secret=self.secret,
        )

        # First delivery
        response1 = github_webhook_handler(event, publisher=self.publisher, secret=self.secret)
        self.assertEqual(response1.get("statusCode"), 200)

        # Second delivery (GitHub redelivery attempt)
        response2 = github_webhook_handler(event, publisher=self.publisher, secret=self.secret)
        self.assertEqual(response2.get("statusCode"), 200)

        # Both invocations record the delivery ID deterministically
        self.assertEqual(len(self.publisher.published_messages), 2)
        self.assertEqual(self.publisher.published_messages[0].payload["eventId"], delivery_id)
        self.assertEqual(self.publisher.published_messages[1].payload["eventId"], delivery_id)

    # --------------------------------------------------------------------------
    # 14. Case-insensitive HTTP header handling
    # --------------------------------------------------------------------------
    def test_case_insensitive_http_header_handling(self) -> None:
        """Verify that headers with mixed or uppercase casing are handled identically."""
        fixture = load_fixture("github_push_valid.json")

        for casing in ["mixed", "upper", "lower"]:
            with self.subTest(casing=casing):
                self.publisher.clear()
                event = build_apigateway_v2_event(
                    body=fixture,
                    event_type="push",
                    headers_case=casing,
                    secret=self.secret,
                )

                response = github_webhook_handler(event, publisher=self.publisher, secret=self.secret)

                self.assertEqual(response.get("statusCode"), 200)
                self.assertEqual(len(self.publisher.published_messages), 1)

    # --------------------------------------------------------------------------
    # 15. Ensure invalid signatures never invoke the publisher
    # --------------------------------------------------------------------------
    def test_invalid_signatures_never_invoke_publisher(self) -> None:
        """Verify that requests with invalid signatures never call publisher.publish()."""
        fixture = load_fixture("github_push_valid.json")

        class SpyPublisher(MockMQTTPublisher):
            def __init__(self) -> None:
                super().__init__()
                self.publish_call_count = 0

            def publish(self, topic: str, payload: Dict[str, Any]) -> bool:
                self.publish_call_count += 1
                return super().publish(topic, payload)

        spy = SpyPublisher()
        event = build_apigateway_v2_event(
            body=fixture,
            event_type="push",
            signature_override="sha256=forged_signature_hex_value_0123456789abcdef",
            secret=self.secret,
        )

        response = github_webhook_handler(event, publisher=spy, secret=self.secret)

        self.assertEqual(response.get("statusCode"), 403)
        self.assertEqual(spy.publish_call_count, 0)
        self.assertEqual(len(spy.published_messages), 0)

    # --------------------------------------------------------------------------
    # 16. Missing GitHub delivery ID: reject with 400 without publishing
    # --------------------------------------------------------------------------
    def test_missing_delivery_id_returns_400_without_publishing(self) -> None:
        """Verify that requests missing X-GitHub-Delivery return 400 and never publish."""
        fixture = load_fixture("github_push_valid.json")
        # Build event without X-GitHub-Delivery header
        event = build_apigateway_v2_event(
            body=fixture,
            event_type="push",
            delivery_id="",
            secret=self.secret,
        )
        # Explicitly remove delivery header if key remains
        if "x-github-delivery" in event.get("headers", {}):
            del event["headers"]["x-github-delivery"]

        response = github_webhook_handler(event, publisher=self.publisher, secret=self.secret)

        self.assertEqual(response.get("statusCode"), 400)
        body = json.loads(response.get("body", "{}"))
        self.assertIn("X-GitHub-Delivery", body.get("message", ""))
        self.assertEqual(len(self.publisher.published_messages), 0)

    # --------------------------------------------------------------------------
    # 17. Secret retrieval from AWS Secrets Manager: success
    # --------------------------------------------------------------------------
    def test_secret_retrieval_from_secretsmanager_success(self) -> None:
        """Verify secret retrieval from AWS Secrets Manager using GITHUB_WEBHOOK_SECRET_ARN."""
        os.environ.pop("GITHUB_WEBHOOK_SECRET", None)
        os.environ["GITHUB_WEBHOOK_SECRET_ARN"] = "arn:aws:secretsmanager:us-east-1:111122223333:secret:my-secret-123456"

        class MockSecretsManager:
            def get_secret_value(self, SecretId: str) -> Dict[str, Any]:
                return {"SecretString": SYNTHETIC_WEBHOOK_SECRET}

        fixture = load_fixture("github_push_valid.json")
        delivery_id = "sm-delivery-uuid-001"
        event = build_apigateway_v2_event(
            body=fixture,
            event_type="push",
            delivery_id=delivery_id,
            secret=self.secret,
        )

        response = github_webhook_handler(
            event,
            publisher=self.publisher,
            secret=None,
            secretsmanager_client=MockSecretsManager(),
        )

        self.assertEqual(response.get("statusCode"), 200)
        self.assertEqual(len(self.publisher.published_messages), 1)
        self.assertEqual(self.publisher.published_messages[0].payload["eventId"], delivery_id)

    # --------------------------------------------------------------------------
    # 18. Secret retrieval from AWS Secrets Manager: failure fails closed
    # --------------------------------------------------------------------------
    def test_secret_retrieval_from_secretsmanager_failure_fails_closed(self) -> None:
        """Verify that failure retrieving secret from Secrets Manager fails closed with HTTP 500."""
        os.environ.pop("GITHUB_WEBHOOK_SECRET", None)
        os.environ["GITHUB_WEBHOOK_SECRET_ARN"] = "arn:aws:secretsmanager:us-east-1:111122223333:secret:my-secret-123456"

        class FailingSecretsManager:
            def get_secret_value(self, SecretId: str) -> Dict[str, Any]:
                raise RuntimeError("AccessDeniedException: Simulated Secrets Manager failure")

        fixture = load_fixture("github_push_valid.json")
        event = build_apigateway_v2_event(
            body=fixture,
            event_type="push",
            secret=self.secret,
        )

        response = github_webhook_handler(
            event,
            publisher=self.publisher,
            secret=None,
            secretsmanager_client=FailingSecretsManager(),
        )

        self.assertEqual(response.get("statusCode"), 500)
        self.assertEqual(len(self.publisher.published_messages), 0)

    # --------------------------------------------------------------------------
    # 19. Secret retrieval from AWS Secrets Manager: in-memory caching
    # --------------------------------------------------------------------------
    def test_secret_retrieval_from_secretsmanager_caches_in_memory(self) -> None:
        """Verify that Secrets Manager secret is cached in-memory across warm Lambda invocations."""
        os.environ.pop("GITHUB_WEBHOOK_SECRET", None)
        os.environ["GITHUB_WEBHOOK_SECRET_ARN"] = "arn:aws:secretsmanager:us-east-1:111122223333:secret:cached-secret-999"

        class SpySecretsManager:
            def __init__(self) -> None:
                self.call_count = 0

            def get_secret_value(self, SecretId: str) -> Dict[str, Any]:
                self.call_count += 1
                return {"SecretString": SYNTHETIC_WEBHOOK_SECRET}

        sm_spy = SpySecretsManager()
        fixture = load_fixture("github_push_valid.json")
        event = build_apigateway_v2_event(body=fixture, event_type="push", secret=self.secret)

        # First invocation (cold start: calls Secrets Manager)
        resp1 = github_webhook_handler(event, publisher=self.publisher, secret=None, secretsmanager_client=sm_spy)
        self.assertEqual(resp1.get("statusCode"), 200)
        self.assertEqual(sm_spy.call_count, 1)

        # Second invocation (warm invocation: uses in-memory cache)
        resp2 = github_webhook_handler(event, publisher=self.publisher, secret=None, secretsmanager_client=sm_spy)
        self.assertEqual(resp2.get("statusCode"), 200)
        self.assertEqual(sm_spy.call_count, 1, "Warm invocation must not re-query Secrets Manager")


if __name__ == "__main__":
    unittest.main()


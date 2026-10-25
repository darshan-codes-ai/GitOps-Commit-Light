"""
Unit tests for GitOps Commit Light Local Development & Simulation Server
"""

import hashlib
import hmac
import json
import unittest

from backend.local_server import (
    LOCAL_DEV_SECRET,
    LOCAL_MQTT_TOPIC,
    ResetRequest,
    SimulationInput,
    get_events,
    get_health,
    get_mqtt_messages,
    get_stats,
    github_webhook_endpoint,
    reset_events,
    simulate_push,
)


class TestLocalServer(unittest.TestCase):
    """Test suite for local development and simulation API server endpoints."""

    def setUp(self):
        # Reset to known seed state before each test
        reset_events(ResetRequest(action="restore"))

    def test_health_endpoint(self):
        """Verify GET /api/health returns healthy simulation status."""
        data = get_health()
        self.assertEqual(data.get("status"), "healthy")
        self.assertEqual(data.get("mode"), "local-simulation")
        self.assertFalse(data.get("awsConnected"))
        self.assertEqual(data.get("mqttTopic"), LOCAL_MQTT_TOPIC)

    def test_stats_endpoint(self):
        """Verify GET /api/stats computes metrics dynamically."""
        data = get_stats()
        self.assertIn("totalEvents", data)
        self.assertIn("publishedCount", data)
        self.assertIn("ignoredCount", data)
        self.assertIn("failedCount", data)
        self.assertIn("uniqueRepositories", data)
        self.assertGreaterEqual(data["totalEvents"], 1)

    def test_get_events_endpoint(self):
        """Verify GET /api/events returns event list."""
        events = get_events()
        self.assertIsInstance(events, list)
        self.assertGreaterEqual(len(events), 1)
        first = events[0]
        self.assertIn("id", first)
        self.assertIn("status", first)
        self.assertIn("repository", first)

    def test_get_mqtt_messages_endpoint(self):
        """Verify GET /api/mqtt/messages returns recorded mock MQTT payloads."""
        messages = get_mqtt_messages()
        self.assertIsInstance(messages, list)
        self.assertGreaterEqual(len(messages), 1)
        self.assertEqual(messages[0]["topic"], LOCAL_MQTT_TOPIC)
        self.assertEqual(messages[0]["payload"]["schemaVersion"], 1)

    def test_simulate_push_main_branch_publishes(self):
        """Verify POST /api/simulate with push to main triggers successful Schema v1 MQTT publish."""
        input_data = SimulationInput(
            owner="darshan-codes-ai",
            repoName="GitOps-Commit-Light",
            branch="main",
            commitSha="4b825dc642cb6eb9a060e54bf8d69288fbee4904",
            commitMessage="feat(local): test local simulator integration",
            authorName="Darshan Kumar",
            authorEmail="darshan@example.com",
            changedFiles=["backend/local_server.py"],
            isDeleted=False,
            isMalformed=False,
            monitoredBranch="main",
        )
        data = simulate_push(input_data)
        self.assertTrue(data.get("success"))
        event = data.get("event", {})
        self.assertEqual(event.get("status"), "success")
        self.assertTrue(event.get("mqttPublished"))
        self.assertIsNotNone(event.get("mqttPayload"))
        self.assertEqual(event["mqttPayload"].get("schemaVersion"), 1)
        self.assertEqual(event["mqttPayload"].get("branch"), "main")
        self.assertEqual(event["mqttPayload"].get("commitId"), "4b825dc642cb6eb9a060e54bf8d69288fbee4904")

    def test_simulate_push_unmonitored_branch_ignored(self):
        """Verify POST /api/simulate with push to non-monitored branch is ignored (0 publish)."""
        input_data = SimulationInput(
            owner="darshan-codes-ai",
            repoName="GitOps-Commit-Light",
            branch="feat/experimental",
            commitSha="1111222233334444555566667777888899990000",
            commitMessage="feat: test non-monitored branch",
            authorName="Darshan Kumar",
            authorEmail="darshan@example.com",
            changedFiles=["test.txt"],
            isDeleted=False,
            isMalformed=False,
            monitoredBranch="main",
        )
        data = simulate_push(input_data)
        self.assertTrue(data.get("success"))
        event = data.get("event", {})
        self.assertEqual(event.get("status"), "ignored")
        self.assertFalse(event.get("mqttPublished"))
        self.assertIsNone(event.get("mqttPayload"))

    def test_simulate_push_deletion_ignored(self):
        """Verify POST /api/simulate with branch deletion is ignored."""
        input_data = SimulationInput(
            owner="darshan-codes-ai",
            repoName="GitOps-Commit-Light",
            branch="main",
            isDeleted=True,
        )
        data = simulate_push(input_data)
        event = data.get("event", {})
        self.assertEqual(event.get("status"), "ignored")
        self.assertFalse(event.get("mqttPublished"))

    def test_simulate_push_malformed_rejected(self):
        """Verify POST /api/simulate with malformed schema returns failed status (400)."""
        input_data = SimulationInput(
            owner="darshan-codes-ai",
            repoName="GitOps-Commit-Light",
            branch="main",
            isMalformed=True,
        )
        data = simulate_push(input_data)
        event = data.get("event", {})
        self.assertEqual(event.get("status"), "failed")
        self.assertFalse(event.get("mqttPublished"))
        self.assertEqual(data.get("lambdaStatusCode"), 400)

    def test_webhook_endpoint_with_valid_hmac(self):
        """Verify POST /webhook/github accepts valid HMAC signature and processes push event."""
        body = {
            "ref": "refs/heads/main",
            "repository": {"name": "GitOps-Commit-Light", "full_name": "darshan-codes-ai/GitOps-Commit-Light"},
            "head_commit": {
                "id": "abcdef1234567890abcdef1234567890abcdef12",
                "message": "test: webhook endpoint",
                "timestamp": "2026-10-25T14:00:00Z",
                "author": {"name": "Tester", "email": "tester@example.com"},
            },
        }
        body_bytes = json.dumps(body).encode("utf-8")
        sig = "sha256=" + hmac.new(LOCAL_DEV_SECRET.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()

        response = github_webhook_endpoint(
            raw_body_bytes=body_bytes,
            x_hub_signature_256=sig,
            x_github_delivery="123e4567-e89b-12d3-a456-426614174000",
            x_github_event="push",
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.body.decode("utf-8"))
        self.assertEqual(data.get("status"), "success")
        self.assertTrue(data.get("published"))

    def test_webhook_endpoint_with_invalid_hmac(self):
        """Verify POST /webhook/github rejects invalid HMAC signature with 403."""
        body_bytes = b'{"ref": "refs/heads/main"}'
        response = github_webhook_endpoint(
            raw_body_bytes=body_bytes,
            x_hub_signature_256="sha256=0000000000000000000000000000000000000000000000000000000000000000",
            x_github_delivery="123e4567-e89b-12d3-a456-426614174000",
            x_github_event="push",
        )
        self.assertEqual(response.status_code, 403)

    def test_reset_endpoint(self):
        """Verify POST /api/reset can clear and restore events."""
        # Clear
        resp_clear = reset_events(ResetRequest(action="clear"))
        self.assertTrue(resp_clear["success"])
        self.assertEqual(resp_clear["count"], 0)

        # Check events is empty
        self.assertEqual(len(get_events()), 0)

        # Restore
        resp_restore = reset_events(ResetRequest(action="restore"))
        self.assertTrue(resp_restore["success"])
        self.assertGreater(resp_restore["count"], 0)


if __name__ == "__main__":
    unittest.main()


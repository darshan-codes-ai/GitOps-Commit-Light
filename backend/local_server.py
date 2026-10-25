"""
GitOps Commit Light — Local Development & Simulation Server

This FastAPI application provides a local development server connecting the frontend
dashboard to the Python backend Lambda logic without requiring AWS credentials or cloud deployments.

It executes the actual GitHub webhook handler (backend/lambda/lambda_function.py)
using the offline MockMQTTPublisher (backend/lambda/publisher.py).
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
import sys
from typing import Any, Dict, List, Optional
import uuid

from fastapi import Body, FastAPI, Header, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Ensure backend/lambda directory is in python path
current_dir = os.path.dirname(os.path.abspath(__file__))
lambda_dir = os.path.join(current_dir, "lambda")
if lambda_dir not in sys.path:
    sys.path.insert(0, lambda_dir)

from lambda_function import github_webhook_handler
from publisher import DEFAULT_MQTT_TOPIC, MockMQTTPublisher

LOCAL_DEV_SECRET = os.environ.get("GITHUB_WEBHOOK_SECRET", "gitops-local-dev-secret-2026")
LOCAL_MONITORED_BRANCH = os.environ.get("MONITORED_BRANCH", "main")
LOCAL_MQTT_TOPIC = os.environ.get("MQTT_TOPIC", DEFAULT_MQTT_TOPIC)

# Shared Mock Publisher for local simulation
mock_publisher = MockMQTTPublisher()

# Seed events for local dashboard demonstration
INITIAL_SEED_EVENTS: List[Dict[str, Any]] = [
    {
        "id": "e1a49802-9bc5-4720-91c3-48e02d849b01",
        "eventId": "e1a49802-9bc5-4720-91c3-48e02d849b01",
        "deliveryId": "e1a49802-9bc5-4720-91c3-48e02d849b01",
        "source": "local-simulation",
        "repository": {
            "name": "GitOps-Commit-Light",
            "fullName": "darshan-codes-ai/GitOps-Commit-Light",
            "owner": "darshan-codes-ai",
        },
        "branch": "main",
        "commit": {
            "sha": "7f4c9a1d8b2e3f5a0c6e9d8b1a4c7f0e2d5b8a1c",
            "message": "feat: add Kubernetes ingress and TLS termination manifests",
            "author": {"name": "Darshan Kumar", "email": "darshan@example.com"},
            "changedFiles": ["k8s/ingress.yaml", "k8s/service.yaml", "docs/deployment-guide.md"],
        },
        "commitSha": "7f4c9a1d8b2e3f5a0c6e9d8b1a4c7f0e2d5b8a1c",
        "commitMessage": "feat: add Kubernetes ingress and TLS termination manifests",
        "author": "Darshan Kumar",
        "authorEmail": "darshan@example.com",
        "changedFiles": ["k8s/ingress.yaml", "k8s/service.yaml", "docs/deployment-guide.md"],
        "timestamp": "2026-10-25T11:42:15Z",
        "status": "success",
        "statusReason": "Valid push event on monitored branch 'main' successfully published to simulated topic.",
        "mqttPublished": True,
        "delivery": {
            "mode": "local-mock",
            "awsDelivered": False,
            "simulatedTopic": "gitops/commits",
            "qos": 0,
        },
        "mqttPayload": {
            "schemaVersion": 1,
            "eventId": "e1a49802-9bc5-4720-91c3-48e02d849b01",
            "repository": "GitOps-Commit-Light",
            "branch": "main",
            "commitId": "7f4c9a1d8b2e3f5a0c6e9d8b1a4c7f0e2d5b8a1c",
            "message": "feat: add Kubernetes ingress and TLS termination manifests",
            "timestamp": "2026-10-25T11:42:15Z",
        },
        "timeline": [
            {"step": "1. Webhook Ingress", "service": "API Gateway v2 HTTP API", "status": "completed", "description": "POST /webhook/github received with delivery UUID"},
            {"step": "2. Signature Verification", "service": "AWS Lambda (Python 3.12)", "status": "completed", "description": "HMAC-SHA256 signature verified in constant time"},
            {"step": "3. Branch Filtering", "service": "AWS Lambda (Python 3.12)", "status": "completed", "description": "Target branch matches monitored branch 'main'"},
            {"step": "4. Schema v1 Construction", "service": "Commit Parser", "status": "completed", "description": "Extracted commit metadata into Schema v1 JSON"},
            {"step": "5. MQTT Publish", "service": "Mock IoT Core Publisher", "status": "completed", "description": "Published message to topic 'gitops/commits' at QoS 0"},
        ],
    },
    {
        "id": "c3b87910-1da4-4f32-82d1-72e91b482a02",
        "eventId": "c3b87910-1da4-4f32-82d1-72e91b482a02",
        "deliveryId": "c3b87910-1da4-4f32-82d1-72e91b482a02",
        "source": "local-simulation",
        "repository": {
            "name": "GitOps-Commit-Light",
            "fullName": "darshan-codes-ai/GitOps-Commit-Light",
            "owner": "darshan-codes-ai",
        },
        "branch": "main",
        "commit": {
            "sha": "3e9b1c7a8e2f3d4c5b6a7e8f90123456789abcde",
            "message": "fix(core): correct warm-container secret caching invalidation logic",
            "author": {"name": "Darshan Kumar", "email": "darshan@example.com"},
            "changedFiles": ["backend/lambda/lambda_function.py", "tests/test_github_webhook.py"],
        },
        "commitSha": "3e9b1c7a8e2f3d4c5b6a7e8f90123456789abcde",
        "commitMessage": "fix(core): correct warm-container secret caching invalidation logic",
        "author": "Darshan Kumar",
        "authorEmail": "darshan@example.com",
        "changedFiles": ["backend/lambda/lambda_function.py", "tests/test_github_webhook.py"],
        "timestamp": "2026-10-25T12:05:40Z",
        "status": "success",
        "statusReason": "Valid bugfix push on monitored branch 'main' processed successfully.",
        "mqttPublished": True,
        "delivery": {
            "mode": "local-mock",
            "awsDelivered": False,
            "simulatedTopic": "gitops/commits",
            "qos": 0,
        },
        "mqttPayload": {
            "schemaVersion": 1,
            "eventId": "c3b87910-1da4-4f32-82d1-72e91b482a02",
            "repository": "GitOps-Commit-Light",
            "branch": "main",
            "commitId": "3e9b1c7a8e2f3d4c5b6a7e8f90123456789abcde",
            "message": "fix(core): correct warm-container secret caching invalidation logic",
            "timestamp": "2026-10-25T12:05:40Z",
        },
        "timeline": [
            {"step": "1. Webhook Ingress", "service": "API Gateway v2 HTTP API", "status": "completed", "description": "POST /webhook/github received"},
            {"step": "2. Signature Verification", "service": "AWS Lambda (Python 3.12)", "status": "completed", "description": "HMAC-SHA256 verified"},
            {"step": "3. Branch Filtering", "service": "AWS Lambda (Python 3.12)", "status": "completed", "description": "Matched monitored branch 'main'"},
            {"step": "4. Schema v1 Construction", "service": "Commit Parser", "status": "completed", "description": "Constructed Schema v1 payload"},
            {"step": "5. MQTT Publish", "service": "Mock IoT Core Publisher", "status": "completed", "description": "Published to 'gitops/commits' (QoS 0)"},
        ],
    },
    {
        "id": "f5d02341-7fe9-482a-9cb2-19e48c371d03",
        "eventId": "f5d02341-7fe9-482a-9cb2-19e48c371d03",
        "deliveryId": "f5d02341-7fe9-482a-9cb2-19e48c371d03",
        "source": "local-simulation",
        "repository": {
            "name": "GitOps-Commit-Light",
            "fullName": "darshan-codes-ai/GitOps-Commit-Light",
            "owner": "darshan-codes-ai",
        },
        "branch": "feat/iot-pipeline",
        "commit": {
            "sha": "a1b2c3d4e5f60718293a4b5c6d7e8f9012345678",
            "message": "feat(iot): experiment with alternative QoS 1 protocol handlers",
            "author": {"name": "Darshan Kumar", "email": "darshan@example.com"},
            "changedFiles": ["firmware/esp32/main.ino"],
        },
        "commitSha": "a1b2c3d4e5f60718293a4b5c6d7e8f9012345678",
        "commitMessage": "feat(iot): experiment with alternative QoS 1 protocol handlers",
        "author": "Darshan Kumar",
        "authorEmail": "darshan@example.com",
        "changedFiles": ["firmware/esp32/main.ino"],
        "timestamp": "2026-10-25T13:15:22Z",
        "status": "ignored",
        "statusReason": "Branch 'feat/iot-pipeline' does not match monitored branch 'main'. Acknowledged without publishing (0 messages sent).",
        "mqttPublished": False,
        "delivery": {
            "mode": "local-mock",
            "awsDelivered": False,
            "simulatedTopic": None,
            "qos": None,
        },
        "mqttPayload": None,
        "timeline": [
            {"step": "1. Webhook Ingress", "service": "API Gateway v2 HTTP API", "status": "completed", "description": "POST /webhook/github received"},
            {"step": "2. Signature Verification", "service": "AWS Lambda (Python 3.12)", "status": "completed", "description": "HMAC-SHA256 verified"},
            {"step": "3. Branch Filtering", "service": "AWS Lambda (Python 3.12)", "status": "ignored", "description": "Branch 'feat/iot-pipeline' ignored (monitored: 'main')"},
            {"step": "4. Schema v1 Construction", "service": "Commit Parser", "status": "skipped", "description": "Skipped for unmonitored branch"},
            {"step": "5. MQTT Publish", "service": "Mock IoT Core Publisher", "status": "skipped", "description": "0 messages published"},
        ],
    },
]

# In-memory storage for local session events
stored_events: List[Dict[str, Any]] = list(INITIAL_SEED_EVENTS)

# Prime mock publisher with initial seed payloads
for ev in stored_events:
    if ev.get("mqttPublished") and ev.get("mqttPayload"):
        mock_publisher.publish(LOCAL_MQTT_TOPIC, ev["mqttPayload"])

app = FastAPI(
    title="GitOps Commit Light Local Server",
    description="Local simulation server and API Gateway proxy simulator for GitOps Commit Light.",
    version="1.0.0",
)

# Enable CORS for local Vite development server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SimulationInput(BaseModel):
    owner: str = Field(default="darshan-codes-ai", description="Repository owner")
    repoName: str = Field(default="GitOps-Commit-Light", description="Repository name")
    branch: str = Field(default="main", description="Git branch name")
    commitSha: Optional[str] = Field(default=None, description="40-hex commit SHA")
    commitMessage: str = Field(
        default="feat: update infrastructure configuration",
        description="Commit message",
    )
    authorName: str = Field(default="Darshan Kumar", description="Commit author name")
    authorEmail: str = Field(default="darshan@example.com", description="Commit author email")
    changedFiles: List[str] = Field(default_factory=lambda: ["README.md"])
    isDeleted: bool = Field(default=False, description="Simulate branch deletion event")
    isMalformed: bool = Field(default=False, description="Simulate malformed payload schema")
    monitoredBranch: str = Field(default=LOCAL_MONITORED_BRANCH)


class ResetRequest(BaseModel):
    action: str = Field(default="restore", description="'restore' to reset seeds or 'clear' to empty")


def _generate_sha() -> str:
    return hashlib.sha1(uuid.uuid4().bytes).hexdigest() + hashlib.sha1(b"gitops").hexdigest()[:8]


@app.get("/api/health")
def get_health() -> Dict[str, Any]:
    """Healthcheck endpoint confirming local simulation engine status."""
    return {
        "status": "healthy",
        "service": "GitOps Commit Light Local Server",
        "mode": "local-simulation",
        "awsConnected": False,
        "environment": "offline-development",
        "monitoredBranch": LOCAL_MONITORED_BRANCH,
        "mqttTopic": LOCAL_MQTT_TOPIC,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/stats")
def get_stats() -> Dict[str, Any]:
    """Retrieve dynamic KPIs calculated from currently stored events."""
    total = len(stored_events)
    published = sum(1 for e in stored_events if e.get("status") == "success" and e.get("mqttPublished"))
    ignored = sum(1 for e in stored_events if e.get("status") == "ignored")
    failed = sum(1 for e in stored_events if e.get("status") == "failed")
    
    repo_names = set()
    for e in stored_events:
        repo = e.get("repository")
        if isinstance(repo, dict):
            repo_names.add(repo.get("fullName") or repo.get("name") or "Unknown")
        elif isinstance(repo, str) and repo.strip():
            repo_names.add(repo.strip())

    return {
        "totalEvents": total,
        "publishedCount": published,
        "ignoredCount": ignored,
        "failedCount": failed,
        "uniqueRepositories": len(repo_names),
        "topic": LOCAL_MQTT_TOPIC,
        "qos": 0,
        "mode": "local-simulation",
    }


@app.get("/api/events")
def get_events() -> List[Dict[str, Any]]:
    """Retrieve all simulated events ordered newest to oldest."""
    return stored_events


@app.get("/api/mqtt/messages")
def get_mqtt_messages() -> List[Dict[str, Any]]:
    """Retrieve messages published to the mock MQTT broker."""
    return [
        {
            "topic": m.topic,
            "payload": m.payload,
        }
        for m in mock_publisher.published_messages
    ]


@app.post("/api/simulate")
def simulate_push(input_data: SimulationInput) -> Dict[str, Any]:
    """
    Simulate a GitHub push webhook by constructing a realistic GitHub webhook payload,
    computing the HMAC-SHA256 signature, and executing the actual backend Lambda handler
    (github_webhook_handler) with MockMQTTPublisher.
    """
    commit_sha = (input_data.commitSha or _generate_sha()).strip()
    if input_data.isDeleted:
        after_sha = "0000000000000000000000000000000000000000"
    else:
        after_sha = commit_sha

    delivery_id = str(uuid.uuid4())
    event_timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    full_repo = f"{input_data.owner.strip()}/{input_data.repoName.strip()}"

    # Construct the GitHub push payload
    if input_data.isMalformed:
        # Intentionally invalid head_commit schema to trigger 400 rejection
        raw_body_dict: Dict[str, Any] = {
            "ref": f"refs/heads/{input_data.branch.strip()}",
            "repository": {"name": input_data.repoName.strip()},
            "head_commit": "invalid-head-commit-scalar-triggers-400",
        }
    elif input_data.isDeleted:
        raw_body_dict = {
            "ref": f"refs/heads/{input_data.branch.strip()}",
            "before": _generate_sha(),
            "after": after_sha,
            "deleted": True,
            "repository": {
                "name": input_data.repoName.strip(),
                "full_name": full_repo,
                "owner": {"name": input_data.owner.strip()},
            },
            "head_commit": None,
        }
    else:
        raw_body_dict = {
            "ref": f"refs/heads/{input_data.branch.strip()}",
            "before": _generate_sha(),
            "after": after_sha,
            "deleted": False,
            "repository": {
                "name": input_data.repoName.strip(),
                "full_name": full_repo,
                "owner": {"name": input_data.owner.strip()},
            },
            "head_commit": {
                "id": commit_sha,
                "message": input_data.commitMessage.strip(),
                "timestamp": event_timestamp,
                "author": {
                    "name": input_data.authorName.strip(),
                    "email": input_data.authorEmail.strip(),
                },
                "modified": input_data.changedFiles,
            },
        }

    raw_body_json = json.dumps(raw_body_dict)
    body_bytes = raw_body_json.encode("utf-8")

    # Compute valid HMAC-SHA256 signature
    signature = "sha256=" + hmac.new(LOCAL_DEV_SECRET.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()

    # Build API Gateway v2 event structure
    api_gateway_event = {
        "headers": {
            "x-hub-signature-256": signature,
            "x-github-delivery": delivery_id,
            "x-github-event": "push",
            "content-type": "application/json",
        },
        "body": raw_body_json,
        "isBase64Encoded": False,
    }

    # Execute backend Lambda handler directly
    initial_pub_count = len(mock_publisher.published_messages)
    lambda_response = github_webhook_handler(
        event=api_gateway_event,
        publisher=mock_publisher,
        secret=LOCAL_DEV_SECRET,
        mqtt_topic=LOCAL_MQTT_TOPIC,
        monitored_branch=input_data.monitoredBranch,
    )
    new_pub_count = len(mock_publisher.published_messages)
    published_to_mqtt = new_pub_count > initial_pub_count

    # Decode Lambda response body
    status_code = lambda_response.get("statusCode", 500)
    try:
        resp_data = json.loads(lambda_response.get("body", "{}"))
    except Exception:
        resp_data = {"raw": lambda_response.get("body")}

    # Determine event classification
    if status_code == 200 and published_to_mqtt:
        event_status = "success"
        reason = f"Push to monitored branch '{input_data.branch}' accepted and published to MQTT topic '{LOCAL_MQTT_TOPIC}'."
        mqtt_payload = resp_data.get("payload") or (mock_publisher.last_message().payload if mock_publisher.last_message() else None)
    elif status_code == 200:
        event_status = "ignored"
        reason = resp_data.get("reason", f"Event acknowledged but ignored by branch filter ({input_data.branch}). 0 MQTT messages published.")
        mqtt_payload = None
    else:
        event_status = "failed"
        reason = resp_data.get("message", f"Request rejected by Lambda with HTTP {status_code}.")
        mqtt_payload = None

    # Construct execution timeline
    timeline = [
        {
            "step": "1. Webhook Ingress (API Gateway)",
            "service": "Amazon API Gateway v2",
            "status": "completed",
            "description": f"POST /webhook/github received with X-GitHub-Delivery: {delivery_id}",
        },
        {
            "step": "2. HMAC-SHA256 Signature Verification",
            "service": "AWS Lambda (Python 3.12)",
            "status": "completed" if status_code != 401 and status_code != 403 else "failed",
            "description": "Signature verified using constant-time comparison against local secret" if status_code != 401 else "Missing or invalid signature header",
        },
        {
            "step": "3. Branch & Deletion Filtering",
            "service": "AWS Lambda (Python 3.12)",
            "status": "completed" if event_status == "success" else ("ignored" if event_status == "ignored" else "failed"),
            "description": (
                f"Branch '{input_data.branch}' matches monitored branch '{input_data.monitoredBranch}'"
                if event_status == "success"
                else (
                    f"Ignored: Branch '{input_data.branch}' does not match monitored branch '{input_data.monitoredBranch}'"
                    if not input_data.isDeleted
                    else "Ignored: Branch deletion event detected"
                )
            ),
        },
        {
            "step": "4. Schema v1 Construction",
            "service": "Commit Parser",
            "status": "completed" if event_status == "success" else "skipped",
            "description": "Constructed Schema v1 payload" if event_status == "success" else "Skipped for filtered event",
        },
        {
            "step": "5. MQTT Message Publication",
            "service": "AWS IoT Core Broker (Mock)",
            "status": "completed" if published_to_mqtt else "skipped",
            "description": f"Published Schema v1 payload to '{LOCAL_MQTT_TOPIC}' (QoS 0)" if published_to_mqtt else "Publication skipped (0 messages dispatched)",
        },
    ]

    event_record: Dict[str, Any] = {
        "id": delivery_id,
        "eventId": delivery_id,
        "deliveryId": delivery_id,
        "source": "local-simulation",
        "repository": {
            "name": input_data.repoName.strip(),
            "fullName": full_repo,
            "owner": input_data.owner.strip(),
        },
        "repoName": input_data.repoName.strip(),
        "branch": input_data.branch.strip(),
        "commit": {
            "sha": commit_sha,
            "message": input_data.commitMessage.strip(),
            "author": {
                "name": input_data.authorName.strip(),
                "email": input_data.authorEmail.strip(),
            },
            "changedFiles": input_data.changedFiles,
        },
        "commitSha": commit_sha,
        "commitMessage": input_data.commitMessage.strip(),
        "author": input_data.authorName.strip(),
        "authorEmail": input_data.authorEmail.strip(),
        "changedFiles": input_data.changedFiles,
        "timestamp": event_timestamp,
        "status": event_status,
        "statusReason": reason,
        "mqttPublished": published_to_mqtt,
        "delivery": {
            "mode": "local-mock",
            "awsDelivered": False,
            "simulatedTopic": LOCAL_MQTT_TOPIC if published_to_mqtt else None,
            "qos": 0 if published_to_mqtt else None,
        },
        "mqttPayload": mqtt_payload,
        "rawPayload": raw_body_dict,
        "timeline": timeline,
    }

    # Prepend to stored events
    stored_events.insert(0, event_record)

    return {
        "success": True,
        "event": event_record,
        "lambdaStatusCode": status_code,
        "lambdaResponse": resp_data,
    }


@app.post("/webhook/github")
def github_webhook_endpoint(
    raw_body_bytes: bytes = Body(default=b""),
    x_hub_signature_256: Optional[str] = Header(None, alias="x-hub-signature-256"),
    x_github_delivery: Optional[str] = Header(None, alias="x-github-delivery"),
    x_github_event: Optional[str] = Header("push", alias="x-github-event"),
) -> Response:
    """
    Standard GitHub Webhook ingestion endpoint.
    Accepts live or simulated webhook POST requests, passes them directly to
    github_webhook_handler, and returns the Lambda HTTP response.
    """
    try:
        body_text = raw_body_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Invalid UTF-8 body")

    headers: Dict[str, str] = {
        "x-github-event": x_github_event or "push",
        "content-type": "application/json",
    }
    if x_hub_signature_256:
        headers["x-hub-signature-256"] = x_hub_signature_256
    if x_github_delivery:
        headers["x-github-delivery"] = x_github_delivery

    api_gateway_event = {
        "headers": headers,
        "body": body_text,
        "isBase64Encoded": False,
    }

    lambda_resp = github_webhook_handler(
        event=api_gateway_event,
        publisher=mock_publisher,
        secret=LOCAL_DEV_SECRET,
        mqtt_topic=LOCAL_MQTT_TOPIC,
        monitored_branch=LOCAL_MONITORED_BRANCH,
    )

    status_code = lambda_resp.get("statusCode", 500)
    resp_body = lambda_resp.get("body", "{}")

    # If push event was processed, store in event history
    try:
        parsed_body = json.loads(resp_body)
    except Exception:
        parsed_body = {}

    if status_code in (200, 400):
        try:
            req_json = json.loads(body_text) if body_text else {}
            head_commit = req_json.get("head_commit") or {}
            repo_info = req_json.get("repository") or {}
            branch_ref = req_json.get("ref", "")
            branch_name = branch_ref.replace("refs/heads/", "") if branch_ref else "unknown"

            ev_id = x_github_delivery or str(uuid.uuid4())
            is_pub = parsed_body.get("published", False)

            stored_events.insert(0, {
                "id": ev_id,
                "eventId": ev_id,
                "deliveryId": ev_id,
                "source": "webhook-endpoint",
                "repository": repo_info.get("full_name") or repo_info.get("name") or "unknown/repo",
                "branch": branch_name,
                "commitSha": head_commit.get("id", _generate_sha() if is_pub else "N/A"),
                "commitMessage": head_commit.get("message", "(No commit message)"),
                "author": head_commit.get("author", {}).get("name", "Unknown"),
                "authorEmail": head_commit.get("author", {}).get("email", ""),
                "changedFiles": head_commit.get("modified", []),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "success" if is_pub else ("ignored" if status_code == 200 else "failed"),
                "statusReason": parsed_body.get("reason") or parsed_body.get("message", "Processed via webhook endpoint"),
                "mqttPublished": is_pub,
                "delivery": {
                    "mode": "local-mock",
                    "awsDelivered": False,
                    "simulatedTopic": LOCAL_MQTT_TOPIC if is_pub else None,
                    "qos": 0 if is_pub else None,
                },
                "mqttPayload": parsed_body.get("payload"),
                "rawPayload": req_json,
            })
        except Exception:
            pass

    return Response(
        content=resp_body,
        status_code=status_code,
        media_type="application/json",
    )


@app.post("/api/reset")
def reset_events(req: ResetRequest) -> Dict[str, Any]:
    """Reset event history to default seed events or clear history."""
    global stored_events
    if req.action == "clear":
        stored_events.clear()
        mock_publisher.clear()
        return {"success": True, "message": "Event history cleared.", "count": 0}

    stored_events = list(INITIAL_SEED_EVENTS)
    mock_publisher.clear()
    for ev in stored_events:
        if ev.get("mqttPublished") and ev.get("mqttPayload"):
            mock_publisher.publish(LOCAL_MQTT_TOPIC, ev["mqttPayload"])

    return {"success": True, "message": "Seed events restored.", "count": len(stored_events)}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("backend.local_server:app", host="127.0.0.1", port=port, reload=True)

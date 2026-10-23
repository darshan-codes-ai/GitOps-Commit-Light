# ⚙️ Backend Event Processing — Lambda & Offline Testing

This document explains the backend event processing module implemented in [`backend/lambda/lambda_function.py`](file:///c:/Users/Darsh/OneDrive/Desktop/GitOps%20Commit%20Light/backend/lambda/lambda_function.py), the MQTT publishing abstraction in [`backend/lambda/publisher.py`](file:///c:/Users/Darsh/OneDrive/Desktop/GitOps%20Commit%20Light/backend/lambda/publisher.py), how to run the automated offline tests on Windows PowerShell, what is currently mocked, and what remains for live AWS integration.

---

## 🚀 Running the Tests on Windows PowerShell

All tests run locally using Python's standard-library `unittest` module. No external packages, internet connection, or AWS credentials are required.

From the project root directory (`C:\Users\Darsh\OneDrive\Desktop\GitOps Commit Light`):

### Option 1: Verbose Test Discovery (Recommended — Runs All 42 Tests)
```powershell
python -m unittest discover tests -v
```

### Option 2: Run Individual Test Suites
* **Event Processing Suite (25 tests):**
  ```powershell
  python tests/test_event_processing.py
  ```
* **MQTT Publisher Suite (17 tests):**
  ```powershell
  python tests/test_mqtt_publisher.py
  ```

### Option 3: Run with Python 3 Explicitly
```powershell
py -3 -m unittest discover tests -v
```

---

## 🔍 What the Handler Currently Does

The handler in [`backend/lambda/lambda_function.py`](file:///c:/Users/Darsh/OneDrive/Desktop/GitOps%20Commit%20Light/backend/lambda/lambda_function.py) provides pure, deterministic event parsing, payload creation, and optional MQTT publication:

1. **Event Structure Validation:**
   - Validates that the event is a JSON object (`dict`).
   - Ensures `source == "aws.codecommit"`.
   - Ensures `detail-type == "CodeCommit Repository State Change"`.
   - Confirms that the event action is supported (`referenceUpdated` or `referenceCreated`). Explicitly rejects branch deletions (`referenceDeleted`).
   - Confirms that `referenceType == "branch"`.
   - Ensures `repositoryName`, `referenceName` (branch), and `commitId` are non-empty strings.

2. **Metadata Extraction & Fallback Behavior:**
   - **Event ID (`eventId`):** Extracted from `event["id"]`. If missing or empty, generates a deterministic fallback: `fallback-<uuid4>`.
   - **Timestamp (`timestamp`):** Extracted from `event["time"]`. If missing or empty, generates the current UTC ISO-8601 timestamp (`YYYY-MM-DDTHH:MM:SSZ`).
   - **Repository, Branch, Commit ID:** Extracted directly without fallback to ensure real commit data is never fabricated.

3. **Decoupled Commit Message Retrieval:**
   - Interfaces with an abstract `CommitMessageProvider` or callable provider.
   - For offline test fixtures, optionally reads `detail.commitMessage` if present.
   - Validates that the retrieved message is a valid, non-empty string.

4. **Payload Construction:**
   Constructs the target JSON notification payload matching schema version 1:
   ```json
   {
     "schemaVersion": 1,
     "eventId": "synthetic-event-id-001",
     "repository": "gitops-commit-light",
     "branch": "main",
     "commitId": "0123456789abcdef0123456789abcdef01234567",
     "message": "docs: add architecture specs",
     "timestamp": "2026-10-23T11:00:00Z"
   }
   ```

5. **Decoupled MQTT Publishing via Dependency Injection:**
   - If an `MQTTPublisher` instance is provided, the handler publishes the constructed payload to topic `gitops/commits`.
   - If publishing succeeds, returns `statusCode: 200` with `"published": True` and `"topic": "gitops/commits"`.
   - If event validation or payload construction fails, **publishing is aborted immediately** and zero messages are dispatched.
   - If publishing fails (e.g., broker disconnect), catches `MQTTPublishError` and returns `statusCode: 500` with clear diagnostic information.

6. **Structured Handler Output:**
   - **Success without Publisher (`200 OK`):** `{"statusCode": 200, "status": "success", "payload": {...}}`
   - **Success with Publisher (`200 OK`):** `{"statusCode": 200, "status": "success", "payload": {...}, "published": True, "topic": "gitops/commits"}`
   - **Client Error (`400 Bad Request`):** Catches `EventValidationError`, `UnsupportedEventError`, or `CommitMessageError`, returning structured error details without crashing.
   - **Publisher / Server Error (`500 Internal Server Error`):** Returns structured diagnostic information for `MQTTPublishError` or unexpected exceptions.

---

## 📡 MQTT Publishing Abstraction

The publisher design in [`backend/lambda/publisher.py`](file:///c:/Users/Darsh/OneDrive/Desktop/GitOps%20Commit%20Light/backend/lambda/publisher.py) isolates MQTT logic from the Lambda handler:

```text
┌────────────────┐     publishes to      ┌─────────────────────────┐
│ lambda_handler ├──────────────────────►│ MQTTPublisher Interface │
└────────────────┘     "gitops/commits"  └────────────┬────────────┘
                                                      │
                       ┌──────────────────────────────┴──────────────────────────────┐
                       ▼                                                             ▼
         ┌───────────────────────────┐                                 ┌───────────────────────────┐
         │     MockMQTTPublisher     │ (Used in offline tests)         │   Boto3 / IoT Publisher   │ (Future production)
         │ • Validates topic format  │                                 │ • Connects to AWS IoT Core│
         │ • Validates JSON payload  │                                 │ • Publishes over TLS      │
         │ • Records messages in RAM │                                 │ • Scoped by IAM policy    │
         └───────────────────────────┘                                 └───────────────────────────┘
```

### Components
* **`MQTTPublisher` (Abstract Base Class):** Defines `publish(topic: str, payload: Dict[str, Any]) -> bool`.
* **`MockMQTTPublisher`:** In-memory test publisher that validates topics (rejects wildcards `+` and `#`), validates JSON serializability, records sent messages in `published_messages`, and can simulate network failures with `should_fail=True`.
* **`DEFAULT_MQTT_TOPIC`:** Constant set to `"gitops/commits"`.

---

## 🛡️ Planned AWS Infrastructure Permissions & Policies

In accordance with least-privilege security principles, the future live cloud integration will require precise IAM permissions and resource policies. These specifications will form the basis of the infrastructure JSON policies in the next milestone.

### 1. AWS Lambda Execution Role Policy (IAM)
The Lambda function needs permissions to write diagnostic logs, query commit details from CodeCommit, and publish MQTT messages to AWS IoT Core:

| Action | Target Resource | Justification |
| :--- | :--- | :--- |
| `logs:CreateLogGroup`<br>`logs:CreateLogStream`<br>`logs:PutLogEvents` | `arn:aws:logs:<region>:<account-id>:log-group:/aws/lambda/<function-name>:*` | Standard CloudWatch logging for serverless monitoring and troubleshooting. |
| `codecommit:GetCommit` | `arn:aws:codecommit:<region>:<account-id>:<repository-name>` | Allows Lambda to fetch the commit message for the received `commitId`. Restricted strictly to the monitored repository. |
| `iot:Publish` | `arn:aws:iot:<region>:<account-id>:topic/gitops/commits` | Allows publishing JSON notifications to AWS IoT Core. Restricted strictly to the `gitops/commits` topic (no wildcard `*` allowed). |

### 2. EventBridge Rule Target Permission (Lambda Resource-Based Policy)
To allow Amazon EventBridge to invoke the Lambda function when matching repository events occur:

| Field | Configuration | Notes |
| :--- | :--- | :--- |
| **Principal** | `events.amazonaws.com` | AWS EventBridge service principal. |
| **Action** | `lambda:InvokeFunction` | Permission to trigger Lambda execution. |
| **Source ARN** | `arn:aws:events:<region>:<account-id>:rule/<rule-name>` | Limits invocation authorization strictly to the specific EventBridge rule monitoring the repository. |

### 3. ESP32 Device IoT Policy (AWS IoT Core)
Attached to the X.509 device certificate on the physical ESP32 to receive commit alerts:

| Action | Target Resource | Notes |
| :--- | :--- | :--- |
| `iot:Connect` | `arn:aws:iot:<region>:<account-id>:client/${iot:Connection.Thing.ThingName}` | Restricts device connection strictly to its assigned Thing client ID. |
| `iot:Subscribe` | `arn:aws:iot:<region>:<account-id>:topicfilter/gitops/commits` | Authorizes the ESP32 to subscribe to notifications on `gitops/commits`. |
| `iot:Receive` | `arn:aws:iot:<region>:<account-id>:topic/gitops/commits` | Authorizes the ESP32 to receive incoming messages on `gitops/commits`. |

---

## 🧩 What Is Mocked in This Milestone

* **EventBridge Event Payloads:** Synthetic JSON fixtures in [`tests/fixtures/`](file:///c:/Users/Darsh/OneDrive/Desktop/GitOps%20Commit%20Light/tests/fixtures/) simulate CodeCommit events with dummy identifiers.
* **Commit Message Retrieval:** In-memory [`StaticCommitMessageProvider`](file:///c:/Users/Darsh/OneDrive/Desktop/GitOps%20Commit%20Light/backend/lambda/lambda_function.py#L93) simulates API retrieval.
* **MQTT Message Broker:** [`MockMQTTPublisher`](file:///c:/Users/Darsh/OneDrive/Desktop/GitOps%20Commit%20Light/backend/lambda/publisher.py#L65) records message delivery in memory without connecting to AWS IoT Core.
* **Lambda Runtime & Context:** The handler runs as a pure Python function locally.

---

## ☁️ What Still Requires Live AWS Integration

1. **AWS CodeCommit API Call:** Retrieving live commit messages using `boto3.client('codecommit').get_commit(...)`.
2. **Amazon EventBridge Rule:** Deploying the event pattern rule to route real git push events.
3. **AWS IoT Core Data Endpoint:** Connecting `boto3.client('iot-data')` to publish over TLS.
4. **AWS IAM Infrastructure:** Provisioning the execution role and IoT device policies detailed above.

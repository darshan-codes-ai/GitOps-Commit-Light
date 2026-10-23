# ⚙️ Backend Event Processing — Lambda & Offline Testing

This document explains the backend event processing module implemented in [`backend/lambda/lambda_function.py`](file:///c:/Users/Darsh/OneDrive/Desktop/GitOps%20Commit%20Light/backend/lambda/lambda_function.py), the MQTT publishing abstraction in [`backend/lambda/publisher.py`](file:///c:/Users/Darsh/OneDrive/Desktop/GitOps%20Commit%20Light/backend/lambda/publisher.py), how to run the automated offline tests on Windows PowerShell, the publishing success contract, asynchronous Lambda retry semantics, and what remains for live AWS integration.

---

## 🚀 Running the Tests on Windows PowerShell

All tests run locally using Python's standard-library `unittest` module. No external packages, internet connection, or AWS credentials are required.

From the project root directory (`C:\Users\Darsh\OneDrive\Desktop\GitOps Commit Light`):

### Option 1: Verbose Test Discovery (Recommended — Runs All 60 Tests)
```powershell
python -m unittest discover tests -v
```

### Option 2: Run Individual Test Suites
* **Event Processing Suite (25 tests):**
  ```powershell
  python tests/test_event_processing.py
  ```
* **MQTT Publisher Suite (22 tests):**
  ```powershell
  python tests/test_mqtt_publisher.py
  ```
* **Asynchronous Lambda & Failure Handling Suite (13 tests):**
  ```powershell
  python tests/test_asynchronous_lambda.py
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
   - Strictly enforces the **Publishing Success Contract**: publication is reported as successful **only if** `publisher.publish(...)` returns explicit boolean `True`.
   - If publishing returns `False` or raises an exception, the handler reports an error and **never claims the message was published**.
   - If event validation or payload construction fails, **publishing is aborted immediately** and zero messages are dispatched.

6. **Structured Handler Output:**
   - **Success without Publisher (`200 OK`):** `{"statusCode": 200, "status": "success", "payload": {...}}`
   - **Success with Publisher (`200 OK`):** `{"statusCode": 200, "status": "success", "payload": {...}, "published": True, "topic": "gitops/commits"}`
   - **Client Error (`400 Bad Request`):** Catches `EventValidationError`, `UnsupportedEventError`, or `CommitMessageError`, returning structured error details without crashing.
   - **Publisher / Server Error (`500 Internal Server Error`):** Returns structured diagnostic information for `MQTTPublishError` or unexpected exceptions.

---

## 📡 MQTT Publishing Success Contract

The publisher contract in [`backend/lambda/publisher.py`](file:///c:/Users/Darsh/OneDrive/Desktop/GitOps%20Commit%20Light/backend/lambda/publisher.py) ensures reliable cloud-to-device messaging without false positives:

```text
┌────────────────┐     publishes to      ┌─────────────────────────┐
│ lambda_handler ├──────────────────────►│ MQTTPublisher.publish() │
└───────┬────────┘     "gitops/commits"  └────────────┬────────────┘
        │                                             │
        │                                 ┌───────────┴───────────┐
        │                                 ▼                       ▼
        │                            Returns True            Returns False
        │                                 │                  or raises Error
        │                                 │                       │
        ▼                                 ▼                       ▼
   Confirmed                       [Success Result]        [Failure Result]
   Delivery?                      "published": True       Raise MQTTPublishError
                                  statusCode: 200         statusCode: 500
                                                          "published": NOT True
```

### Success Guarantee Rules
1. **Explicit Confirmation Required:** Publication is confirmed if and only if `publisher.publish()` returns strict boolean `True`. Truthy integers (e.g. `1`) or non-boolean returns are rejected.
2. **False Means Failure:** If a publisher rejects delivery by returning `False` without raising an exception, `lambda_handler` intercepts this, raises an [`MQTTPublishError`](file:///c:/Users/Darsh/OneDrive/Desktop/GitOps%20Commit%20Light/backend/lambda/publisher.py#L25), and returns `statusCode: 500`. It **never** reports `"published": True`.
3. **No Publishing on Upstream Failure:** If an event has invalid syntax or the commit message is missing, the handler halts at step 1 or 3. The publisher is never called.
4. **Offline Mock Safety:** [`MockMQTTPublisher`](file:///c:/Users/Darsh/OneDrive/Desktop/GitOps%20Commit%20Light/backend/lambda/publisher.py#L65) records messages purely in RAM (`published_messages`) for test inspection and explicitly does not claim real network delivery.

---

## ⚡ Lambda Execution Semantics: Synchronous vs Asynchronous Invocations

A vital architectural distinction exists between **local/synchronous invocation** and **production asynchronous EventBridge invocation**.

### The "statusCode 500" Myth in Asynchronous Lambda
In web APIs behind Amazon API Gateway, returning `{"statusCode": 500}` informs API Gateway to send an HTTP 500 response to the client.

However, **Amazon EventBridge invokes AWS Lambda asynchronously** (`InvocationType: Event`).
* From the AWS Lambda service perspective, returning a dictionary like `{"statusCode": 500, "status": "error"}` is a **successful execution (exit code 0)**.
* AWS Lambda and EventBridge do **not** inspect internal dictionary keys like `statusCode: 500`.
* Therefore, simply returning `statusCode: 500` **will NOT cause EventBridge or AWS Lambda to retry the event!**
* To trigger automatic AWS retries in an asynchronous invocation, the Lambda function must **raise an unhandled exception** out of the function entry point.

### Failure Classification: Permanent vs Transient

| Category | Examples | Nature | Desired Asynchronous Behavior |
| :--- | :--- | :--- | :--- |
| **Permanent Validation Errors (Poison Pills)** | • Missing `commitId` or `repositoryName`<br>• Non-CodeCommit source<br>• `referenceDeleted` events<br>• Malformed JSON | The event itself is invalid or unmonitored. Retrying 100 times will never fix it. | **Do NOT retry.** Acknowledge and drop cleanly with diagnostic logging (or record a CloudWatch metric). Retrying wastes compute time and delays the queue. |
| **Transient Infrastructure Failures** | • CodeCommit API throttling / rate limit<br>• AWS IoT Core endpoint timeout<br>• Temporary TLS handshake blip | The event is valid, but an AWS service is momentarily unavailable. | **Must retry.** Must bubble up as an unhandled exception so EventBridge's retry policy (up to 24 hours with exponential backoff) retries the event until it succeeds. |

---

## 🔄 Production Asynchronous Handler & Recovery Architecture

The production entry point [`production_lambda_handler`](file:///c:/Users/Darsh/OneDrive/Desktop/GitOps%20Commit%20Light/backend/lambda/lambda_function.py#L487) is implemented to enforce asynchronous reliability:

```python
def production_lambda_handler(
    event: Dict[str, Any],
    context: Any = None,
    message_provider: Optional[MessageProviderType] = None,
    publisher: Optional[MQTTPublisher] = None,
    mqtt_topic: str = DEFAULT_MQTT_TOPIC,
) -> Dict[str, Any]:
    """
    Production entry point for asynchronous EventBridge Lambda invocations.
    
    - Permanent validation errors: acknowledged cleanly with statusCode 400 (no exception raised).
      Prevents futile retries on unfixable poison-pill events.
    - Transient infrastructure errors: raised as unhandled exceptions.
      Signals invocation failure to AWS Lambda runtime so EventBridge retries.
    """
    return lambda_handler(
        event=event,
        context=context,
        message_provider=message_provider,
        publisher=publisher,
        mqtt_topic=mqtt_topic,
        raise_on_retryable=True,
    )
```

### Distinction Between Implemented Code and Future AWS Configuration

| Component | Status | Details / Implementation |
| :--- | :--- | :--- |
| **Error Classification** | **Implemented** | [`backend/lambda/lambda_function.py`](file:///c:/Users/Darsh/OneDrive/Desktop/GitOps%20Commit%20Light/backend/lambda/lambda_function.py) — Distinguishes `PermanentError` (never retried) from `RetryableError` (always retried). |
| **Invocation Failure Propagation** | **Implemented** | [`production_lambda_handler`](file:///c:/Users/Darsh/OneDrive/Desktop/GitOps%20Commit%20Light/backend/lambda/lambda_function.py#L487) — Raises unhandled exceptions for transient errors; returns 400 cleanly for permanent errors. |
| **Publishing Confirmation** | **Implemented** | Strict boolean check confirms delivery only on explicit `True` from publisher. |
| **EventBridge Retry Policy** | *Future AWS Configuration* | Attached to the EventBridge Rule target: Maximum Event Age (e.g. 24 hours), Maximum Retry Attempts (e.g. 185 attempts) with exponential backoff and jitter. |
| **Dead-Letter Queue (DLQ)** | *Future AWS Configuration* | Amazon SQS standard queue attached to the EventBridge Rule target. Receives events that fail all retries. |
| **DLQ Monitoring & Redrive** | *Future AWS Configuration* | CloudWatch Alarm on `ApproximateNumberOfMessagesVisible > 0` in DLQ, with SQS redrive to re-process once outages resolve. |

---

## 🛡️ Planned AWS Infrastructure Permissions & Policies

In accordance with least-privilege security principles, the future live cloud integration will require precise IAM permissions and resource policies:

### 1. AWS Lambda Execution Role Policy (IAM)
| Action | Target Resource | Justification |
| :--- | :--- | :--- |
| `logs:CreateLogGroup`<br>`logs:CreateLogStream`<br>`logs:PutLogEvents` | `arn:aws:logs:<region>:<account-id>:log-group:/aws/lambda/<function-name>:*` | Standard CloudWatch logging for serverless monitoring. |
| `codecommit:GetCommit` | `arn:aws:codecommit:<region>:<account-id>:<repository-name>` | Fetches commit message for `commitId`. Restricted strictly to the monitored repository. |
| `iot:Publish` | `arn:aws:iot:<region>:<account-id>:topic/gitops/commits` | Publishes JSON notifications to AWS IoT Core. Restricted strictly to `gitops/commits` (no wildcards). |

### 2. EventBridge Rule Target Permission (Lambda Resource-Based Policy)
| Field | Configuration | Notes |
| :--- | :--- | :--- |
| **Principal** | `events.amazonaws.com` | AWS EventBridge service principal. |
| **Action** | `lambda:InvokeFunction` | Permission to trigger Lambda execution. |
| **Source ARN** | `arn:aws:events:<region>:<account-id>:rule/<rule-name>` | Restricts execution strictly to the specific EventBridge rule. |

### 3. ESP32 Device IoT Policy (AWS IoT Core)
| Action | Target Resource | Notes |
| :--- | :--- | :--- |
| `iot:Connect` | `arn:aws:iot:<region>:<account-id>:client/${iot:Connection.Thing.ThingName}` | Restricts device connection strictly to its assigned Thing client ID. |
| `iot:Subscribe` | `arn:aws:iot:<region>:<account-id>:topicfilter/gitops/commits` | Authorizes subscription to `gitops/commits`. |
| `iot:Receive` | `arn:aws:iot:<region>:<account-id>:topic/gitops/commits` | Authorizes receiving messages on `gitops/commits`. |

---

## 🧩 What Is Mocked in This Milestone

* **EventBridge Event Payloads:** Synthetic JSON fixtures in [`tests/fixtures/`](file:///c:/Users/Darsh/OneDrive/Desktop/GitOps%20Commit%20Light/tests/fixtures/) simulate CodeCommit events.
* **Commit Message Retrieval:** In-memory [`StaticCommitMessageProvider`](file:///c:/Users/Darsh/OneDrive/Desktop/GitOps%20Commit%20Light/backend/lambda/lambda_function.py#L93) simulates API retrieval.
* **MQTT Message Broker:** [`MockMQTTPublisher`](file:///c:/Users/Darsh/OneDrive/Desktop/GitOps%20Commit%20Light/backend/lambda/publisher.py#L65) records message delivery in memory without connecting to AWS IoT Core.
* **Lambda Runtime & Context:** The handler runs as a pure Python function locally.

---

## ☁️ What Still Requires Live AWS Integration

1. **AWS CodeCommit API Call:** Retrieving live commit messages using `boto3.client('codecommit').get_commit(...)`.
2. **Amazon EventBridge Rule:** Deploying the event pattern rule to route real git push events.
3. **AWS IoT Core Data Endpoint:** Connecting `boto3.client('iot-data')` to publish over TLS.
4. **AWS IAM Infrastructure:** Provisioning the execution role and IoT device policies detailed above.

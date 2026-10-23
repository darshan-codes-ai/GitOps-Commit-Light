# ⚙️ Backend Event Processing — Lambda & Offline Testing

This document explains the backend event processing module implemented in [`backend/lambda/lambda_function.py`](file:///c:/Users/Darsh/OneDrive/Desktop/GitOps%20Commit%20Light/backend/lambda/lambda_function.py), how to run the automated offline tests on Windows PowerShell, what is currently mocked, and what remains for live AWS integration.

---

## 🚀 Running the Tests on Windows PowerShell

All tests run locally using Python's standard-library `unittest` module. No external packages, internet connection, or AWS credentials are required.

From the project root directory (`C:\Users\Darsh\OneDrive\Desktop\GitOps Commit Light`):

### Option 1: Verbose Test Discovery (Recommended)
```powershell
python -m unittest discover tests -v
```

### Option 2: Run the Test Module Directly
```powershell
python tests/test_event_processing.py
```

### Option 3: Run with Python 3 Explicitly (if multiple Python versions are installed)
```powershell
py -3 -m unittest discover tests -v
```

---

## 🔍 What the Handler Currently Does

The handler in [`backend/lambda/lambda_function.py`](file:///c:/Users/Darsh/OneDrive/Desktop/GitOps%20Commit%20Light/backend/lambda/lambda_function.py) provides pure, deterministic event parsing and payload creation:

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

5. **Structured Handler Output:**
   - **Success (`200 OK`):** Returns `{"statusCode": 200, "status": "success", "payload": {...}}`.
   - **Client Error (`400 Bad Request`):** Catches `EventValidationError`, `UnsupportedEventError`, or `CommitMessageError`, returning structured error details without crashing.
   - **Server Error (`500 Internal Server Error`):** Returns structured diagnostic information for unexpected exceptions.

---

## 🧩 What Is Mocked in This Milestone

* **EventBridge Event Payloads:** Synthetic JSON fixtures in [`tests/fixtures/`](file:///c:/Users/Darsh/OneDrive/Desktop/GitOps%20Commit%20Light/tests/fixtures/) simulate CodeCommit events using dummy account IDs (`111122223333`) and placeholder commit hashes.
* **Commit Message Retrieval:** An in-memory [`StaticCommitMessageProvider`](file:///c:/Users/Darsh/OneDrive/Desktop/GitOps%20Commit%20Light/backend/lambda/lambda_function.py#L93) and callable functions simulate retrieving the commit message without calling AWS APIs.
* **Lambda Runtime & Context:** The handler accepts an optional `context` parameter, allowing offline test runners to invoke it as a plain Python function.

---

## ☁️ What Still Requires Live AWS Integration

The following components are intentionally deferred to future milestones and require cloud resources:

1. **AWS CodeCommit API Integration:**
   - Calling the CodeCommit service to look up actual commit messages.
2. **Amazon EventBridge Rule:**
   - Cloud configuration to capture repository events and invoke Lambda.
3. **AWS IoT Core MQTT Publishing:**
   - Using the AWS SDK (`boto3.client('iot-data')`) to publish the constructed payload to topic `gitops/commits`.
4. **AWS IAM Role & Permissions:**
   - An execution role granting `codecommit:GetCommit` and `iot:Publish`.

---

## 📖 How the Commit Message Will Eventually Be Retrieved

### The Challenge
AWS CodeCommit EventBridge events contain metadata such as `repositoryName`, `referenceName`, and `commitId`, but **do not include the commit message text**.

### The Solution: Boto3 Provider Implementation
Because our handler relies on the abstract [`CommitMessageProvider`](file:///c:/Users/Darsh/OneDrive/Desktop/GitOps%20Commit%20Light/backend/lambda/lambda_function.py#L65) interface, live AWS integration will be implemented by creating a Boto3 provider:

```python
import boto3
from backend.lambda.lambda_function import CommitMessageProvider, CommitMessageError

class Boto3CodeCommitProvider(CommitMessageProvider):
    """Production provider that retrieves commit messages from AWS CodeCommit."""

    def __init__(self, codecommit_client=None):
        self.client = codecommit_client or boto3.client("codecommit")

    def get_commit_message(self, repository: str, commit_id: str) -> str:
        try:
            response = self.client.get_commit(
                repositoryName=repository,
                commitId=commit_id
            )
            return response["commit"]["message"]
        except Exception as err:
            raise CommitMessageError(f"Failed to fetch commit from AWS CodeCommit: {err}") from err
```

This design allows the same parsing and payload construction code to run identically in production without modifying existing business logic.


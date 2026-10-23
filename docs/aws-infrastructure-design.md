# ☁️ AWS Infrastructure Configuration Design — GitOps Commit Light

> **Status:** Offline Design & Scaffolding Phase  
> **Target Cloud:** AWS (CodeCommit, EventBridge, Lambda, IoT Core, SQS DLQ)  
> **Local Repository:** `GitOps Commit Light`  
> **Safety Notice:** All configuration templates use standardized placeholder tokens (`<REGION>`, `<ACCOUNT_ID>`, `<REPOSITORY_NAME>`, `<FUNCTION_NAME>`, `<RULE_NAME>`, `<DLQ_NAME>`). No real AWS account numbers, access keys, or live infrastructure are used in this milestone.

---

## 1. Architectural Scope & File Mapping

To bridge the offline Python backend to live AWS services in the next implementation phase, the infrastructure configuration is partitioned into decoupled, least-privilege configuration templates located in the `aws/` directory:

| Template File | AWS Component / Mechanism | Purpose / Description |
| :--- | :--- | :--- |
| [`aws/eventbridge-rule.json`](file:///c:/Users/Darsh/OneDrive/Desktop/GitOps%20Commit%20Light/aws/eventbridge-rule.json) | EventBridge Rule (`put-rule`) | Filters CodeCommit repository state changes strictly for branch updates on `main`. |
| [`aws/eventbridge-target.json`](file:///c:/Users/Darsh/OneDrive/Desktop/GitOps%20Commit%20Light/aws/eventbridge-target.json) | EventBridge Target (`put-targets`) | Configures the Lambda target, retry parameters, and Dead-Letter Queue (DLQ) ARN. |
| [`aws/lambda-policy.json`](file:///c:/Users/Darsh/OneDrive/Desktop/GitOps%20Commit%20Light/aws/lambda-policy.json) | IAM Execution Role Policy | Grants Lambda permissions to log to CloudWatch, query CodeCommit, and publish to IoT Core. |
| [`aws/lambda-resource-policy.json`](file:///c:/Users/Darsh/OneDrive/Desktop/GitOps%20Commit%20Light/aws/lambda-resource-policy.json) | Lambda Resource Policy (`add-permission`) | Authorizes the Amazon EventBridge service principal to invoke the Lambda function. |
| [`aws/iot-policy.json`](file:///c:/Users/Darsh/OneDrive/Desktop/GitOps%20Commit%20Light/aws/iot-policy.json) | AWS IoT Core Certificate Policy | Grants the physical ESP32 device permission to connect, subscribe, and receive messages (strictly no publishing). |

---

## 2. Policy Decoupling & Permissions Matrix

A common security anti-pattern is combining invocation, execution, and device permissions into a single monolithic policy. In GitOps Commit Light, these responsibilities are strictly separated across three isolated planes:

### A. Lambda Execution-Role Policy (`aws/lambda-policy.json`)
Attached to the IAM role assumed by the Lambda function during execution:
- **CloudWatch Logs:**
  - `logs:CreateLogStream`
  - `logs:PutLogEvents`
  - Resource: `arn:aws:logs:<REGION>:<ACCOUNT_ID>:log-group:/aws/lambda/<FUNCTION_NAME>:*`
  - *No administrative `logs:*` wildcard.*
- **AWS CodeCommit:**
  - `codecommit:GetCommit`
  - Resource: `arn:aws:codecommit:<REGION>:<ACCOUNT_ID>:<REPOSITORY_NAME>`
  - *Read-only inspection of the commit SHA; no write or repository modification rights.*
- **AWS IoT Core:**
  - `iot:Publish`
  - Resource: `arn:aws:iot:<REGION>:<ACCOUNT_ID>:topic/gitops/commits`
  - *Scoped strictly to the designated topic; no wildcards (`topic/*` or `iot:*`).*

### B. EventBridge Invocation Permission (`aws/lambda-resource-policy.json`)
Resource-based policy attached directly to the Lambda function resource:
- **Principal:** `events.amazonaws.com`
- **Action:** `lambda:InvokeFunction`
- **Condition:** `ArnLike` matching `AWS:SourceArn: arn:aws:events:<REGION>:<ACCOUNT_ID>:rule/<RULE_NAME>`
- *Guarantees that only the designated EventBridge rule can trigger the function.*

### C. ESP32 IoT Certificate Policy (`aws/iot-policy.json`)
Attached to the X.509 client certificate installed on the ESP32 hardware:
- **`iot:Connect`:**
  - Resource: `arn:aws:iot:<REGION>:<ACCOUNT_ID>:client/${iot:Connection.Thing.ThingName}`
  - *Client identity enforced via IoT Core Thing Name.*
- **`iot:Subscribe`:**
  - Resource: `arn:aws:iot:<REGION>:<ACCOUNT_ID>:topicfilter/gitops/commits`
  - *Uses the AWS IoT `topicfilter/` ARN namespace.*
- **`iot:Receive`:**
  - Resource: `arn:aws:iot:<REGION>:<ACCOUNT_ID>:topic/gitops/commits`
  - *Uses the AWS IoT `topic/` ARN namespace.*
- **Security Invariant — No Publish Rights:**
  - The ESP32 is exclusively a consumer/subscriber. It **must not** possess `iot:Publish` permissions, preventing edge device compromise from injecting falsified commit notifications.

---

## 3. Asynchronous Failure Handling, Retries & Dead-Letter Queues (DLQ)

When Amazon EventBridge triggers an AWS Lambda function, the invocation is **asynchronous** (`InvocationType: Event`).

### Lambda Return Semantics vs. Exception Raising
- **Returning a dictionary with `statusCode: 500`:**  
  Lambda treats any function return (regardless of dictionary contents or status codes) as a **successful invocation execution**. EventBridge will NOT trigger retries if Lambda exits cleanly.
- **Raising an unhandled exception:**  
  When an exception propagates out of the Lambda entry point, the Lambda service records an execution failure (`FunctionError`). Only this signals to EventBridge that the invocation failed and requires retry logic.

### Error Classification in Handler Code
As implemented in [`backend/lambda/lambda_function.py`](file:///c:/Users/Darsh/OneDrive/Desktop/GitOps%20Commit%20Light/backend/lambda/lambda_function.py):
1. **Permanent / Non-Retryable Defects:**
   - Schema validation errors (`EventValidationError`), unsupported sources, unsupported git actions (e.g. branch deletion), or missing commit messages.
   - Handled cleanly, returning a structured `statusCode: 400` dictionary. These are intentionally swallowed so EventBridge does not waste retries on unrecoverable events.
2. **Transient / Infrastructure Failures:**
   - Commit retrieval errors (`TransientCommitRetrievalError`, network timeouts, rate limiting) and IoT Core publication errors (`TransientMQTTPublishError`).
   - Propagated as unhandled exceptions via `raise_on_retryable=True` (the production default), triggering EventBridge's retry mechanism.

### EventBridge Retry Policy & Dead-Letter Queue (DLQ)
Configured via [`aws/eventbridge-target.json`](file:///c:/Users/Darsh/OneDrive/Desktop/GitOps%20Commit%20Light/aws/eventbridge-target.json):
- **Retry Mechanism:** EventBridge automatically retries failed asynchronous invocations with exponential backoff and jitter. Target settings allow capping:
  - `MaximumEventAgeInSeconds`: e.g., 86,400 seconds (24 hours).
  - `MaximumRetryAttempts`: e.g., 185 attempts.
- **Dead-Letter Queue (DLQ):** When retry attempts are exhausted or an event expires, EventBridge routes the failed event payload along with diagnostic metadata to an Amazon SQS DLQ:
  - Resource: `arn:aws:sqs:<REGION>:<ACCOUNT_ID>:<DLQ_NAME>`
  - Prevents silent event dropping and allows operators to inspect poison-pill messages or infrastructure outages.

### Responsibility Separation
| Responsibility | Implemented in Python Code | Configured in AWS Cloud |
| :--- | :--- | :--- |
| Input validation & event format checks | Yes (`lambda_function.py`) | No |
| Commit message retrieval & payload construction | Yes (`lambda_function.py`) | No |
| Distinguishing transient vs permanent errors | Yes (`lambda_function.py`) | No |
| Escalating transient errors via Python exceptions | Yes (`raise_on_retryable=True`) | No |
| Event filtering (repository, branch) | Partial (code defensively re-checks) | Yes (`aws/eventbridge-rule.json`) |
| Exponential backoff & retry invocation loop | No (delegated to platform) | Yes (EventBridge / Lambda async queue) |
| DLQ storage for exhausted failures | No (delegated to platform) | Yes (`aws/eventbridge-target.json` + SQS) |
| IAM authentication & TLS certificate checks | No (delegated to AWS SDK/broker) | Yes (`aws/lambda-policy.json`, `aws/iot-policy.json`) |

---

## 4. Offline Verification Suite

The repository includes a dedicated offline verification suite in [`tests/test_aws_policies.py`](file:///c:/Users/Darsh/OneDrive/Desktop/GitOps%20Commit%20Light/tests/test_aws_policies.py) to guarantee:
1. **JSON Syntax:** All JSON templates parse without syntax errors.
2. **Security & Placeholders:** No hardcoded AWS 12-digit account IDs or credentials exist in templates.
3. **Least-Privilege Enforcement:**
   - Lambda `iot:Publish` is scoped strictly to `topic/gitops/commits` with no wildcards.
   - CodeCommit permissions are strictly read-only (`codecommit:GetCommit`).
   - CloudWatch Logs are restricted to function stream creation and event ingestion.
   - ESP32 policy contains **no** `iot:Publish` permission, strictly separating client connect, topicfilter subscribe, and topic receive.
4. **Invocation Authorization:** Lambda resource policy strictly authorizes `events.amazonaws.com` scoped to the rule ARN.


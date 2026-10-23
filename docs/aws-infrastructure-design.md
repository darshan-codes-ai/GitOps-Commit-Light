# ☁️ AWS Infrastructure Configuration Design — GitOps Commit Light

> **Status:** Offline Design & Scaffolding Phase  
> **Target Cloud:** AWS (CodeCommit, EventBridge, Lambda, IoT Core, SQS DLQs)  
> **Local Repository:** `GitOps Commit Light`  
> **Safety Notice:** All configuration templates use standardized placeholder tokens (`<REGION>`, `<ACCOUNT_ID>`, `<REPOSITORY_NAME>`, `<FUNCTION_NAME>`, `<RULE_NAME>`, `<EVENTBRIDGE_DLQ_NAME>`, `<LAMBDA_DLQ_NAME>`, `<EXECUTION_ROLE_NAME>`). No real AWS account numbers, access keys, or live infrastructure are accessed in this milestone.

---

## 1. Architectural Scope & File Mapping

To bridge the offline Python backend to live AWS services in the next implementation phase, the infrastructure configuration is partitioned into decoupled, least-privilege configuration templates located in the `aws/` directory:

| Template File | AWS Component / Mechanism | Purpose / Description |
| :--- | :--- | :--- |
| [`aws/eventbridge-rule.json`](file:///c:/Users/Darsh/OneDrive/Desktop/GitOps%20Commit%20Light/aws/eventbridge-rule.json) | EventBridge Rule (`put-rule`) | Filters CodeCommit repository state changes strictly for branch updates on `main`. |
| [`aws/eventbridge-target.json`](file:///c:/Users/Darsh/OneDrive/Desktop/GitOps%20Commit%20Light/aws/eventbridge-target.json) | EventBridge Target (`put-targets`) | Configures Path A Target Delivery: Lambda target, delivery retry limits (185 attempts, 24h), and Target DLQ. |
| [`aws/lambda-function-config.json`](file:///c:/Users/Darsh/OneDrive/Desktop/GitOps%20Commit%20Light/aws/lambda-function-config.json) | Lambda Function Config (`create-function`) | Establishes runtime settings and enforces `lambda_function.production_lambda_handler` as the verified entry point. |
| [`aws/lambda-event-invoke-config.json`](file:///c:/Users/Darsh/OneDrive/Desktop/GitOps%20Commit%20Light/aws/lambda-event-invoke-config.json) | Lambda Event Invoke Config (`put-function-event-invoke-config`) | Configures Path B Asynchronous Execution: function retry limits (2 retries, 6h), and Lambda On-Failure DLQ destination. |
| [`aws/lambda-policy.json`](file:///c:/Users/Darsh/OneDrive/Desktop/GitOps%20Commit%20Light/aws/lambda-policy.json) | IAM Execution Role Policy | Grants Lambda permissions to log to CloudWatch, query CodeCommit, publish to IoT Core, and write to Lambda DLQ. |
| [`aws/lambda-resource-policy.json`](file:///c:/Users/Darsh/OneDrive/Desktop/GitOps%20Commit%20Light/aws/lambda-resource-policy.json) | Lambda Resource Policy (`add-permission`) | Authorizes the Amazon EventBridge service principal to invoke the Lambda function. |
| [`aws/iot-policy.json`](file:///c:/Users/Darsh/OneDrive/Desktop/GitOps%20Commit%20Light/aws/iot-policy.json) | AWS IoT Core Certificate Policy | Grants the physical ESP32 device permission to connect, subscribe, and receive messages (strictly no publishing). |

---

## 2. Policy Decoupling & Permissions Matrix

Responsibilities are strictly separated across isolated planes to enforce the principle of least privilege:

### A. Lambda Execution-Role Policy (`aws/lambda-policy.json`)
Attached to the IAM role assumed by the Lambda function during execution:
- **CloudWatch Logs:**
  - `logs:CreateLogStream`, `logs:PutLogEvents`
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
- **Lambda Asynchronous Failure Destination (Path B DLQ):**
  - `sqs:SendMessage`
  - Resource: `arn:aws:sqs:<REGION>:<ACCOUNT_ID>:<LAMBDA_DLQ_NAME>`
  - *Enables the Lambda service to forward invocation records to the On-Failure SQS queue when function retries are exhausted.*

### B. EventBridge Invocation Permission (`aws/lambda-resource-policy.json`)
Resource-based policy attached directly to the Lambda function resource:
- **Principal:** `events.amazonaws.com`
- **Action:** `lambda:InvokeFunction`
- **Condition:** `ArnLike` matching `AWS:SourceArn: arn:aws:events:<REGION>:<ACCOUNT_ID>:rule/<RULE_NAME>`
- *Guarantees that only the designated EventBridge rule can trigger the function.*

### C. ESP32 IoT Certificate Policy (`aws/iot-policy.json`)
Attached to the X.509 client certificate installed on the ESP32 hardware:
- **`iot:Connect`:** Resource: `arn:aws:iot:<REGION>:<ACCOUNT_ID>:client/${iot:Connection.Thing.ThingName}`
- **`iot:Subscribe`:** Resource: `arn:aws:iot:<REGION>:<ACCOUNT_ID>:topicfilter/gitops/commits` (*AWS IoT `topicfilter/` namespace*)
- **`iot:Receive`:** Resource: `arn:aws:iot:<REGION>:<ACCOUNT_ID>:topic/gitops/commits` (*AWS IoT `topic/` namespace*)
- **Security Invariant — No Publish Rights:** The ESP32 is exclusively a consumer/subscriber. It **must not** possess `iot:Publish` permissions, preventing edge device compromise from injecting falsified commit notifications.

---

## 3. Two Distinct Failure Paths: EventBridge Delivery vs. Lambda Execution

A critical architectural distinction exists between **EventBridge target delivery retries** and **Lambda asynchronous function execution retries**. They operate under separate AWS services, separate retry counters, separate service limits, and separate Dead-Letter Queues.

```
[ CodeCommit Event ]
         │
         ▼
[ Amazon EventBridge ]
         │
         ├─── (Path A: Target Delivery Failure) ───► EventBridge Target RetryPolicy (0-185 retries, max 24h)
         │    (Lambda throttled, service down, IAM denied)               │
         │                                                               ▼ (retries exhausted)
         │                                                   [ EventBridge Target DLQ ]
         ▼
[ Lambda Async Queue (HTTP 202 Accepted) ]
  * EventBridge marks delivery SUCCESSFUL; EventBridge is finished with the event *
         │
         ▼
[ production_lambda_handler Execution ]
         │
         ├─── statusCode: 400 (Permanent Error) ───► Clean Exit (No retries; poison pill dropped)
         │
         ├─── statusCode: 200 (Success) ───────────► Clean Exit (MQTT published)
         │
         └─── Unhandled Exception (Transient) ────► (Path B: Lambda Execution Failure)
              (CodeCommit throttle, MQTT failure)                        │
                                                                         ▼
                                                     Lambda Event Invoke Config (0-2 retries, max 6h)
                                                                         │
                                                                         ▼ (retries exhausted)
                                                             [ Lambda On-Failure DLQ ]
```

### Detailed Failure Path Breakdown

#### Path A: EventBridge Target Delivery Failures
- **What it is:** EventBridge attempts to call `lambda:InvokeFunction` with `InvocationType: Event`. If the AWS Lambda service API is unavailable, throttled before queueing, access is denied by the resource policy, or the target ARN is invalid, EventBridge cannot deliver the event.
- **Handling Mechanism:** Handled entirely by EventBridge using [`aws/eventbridge-target.json`](file:///c:/Users/Darsh/OneDrive/Desktop/GitOps%20Commit%20Light/aws/eventbridge-target.json).
- **Service Limits & Defaults:**
  - `MaximumRetryAttempts`: Valid range **0 to 185** (default: 185).
  - `MaximumEventAgeInSeconds`: Valid range **60 to 86,400 seconds** (24 hours; default: 86,400).
- **Target DLQ:** If delivery fails after retries, EventBridge sends the raw event to `arn:aws:sqs:<REGION>:<ACCOUNT_ID>:<EVENTBRIDGE_DLQ_NAME>`.
- **Handoff Boundary:** Once the Lambda service accepts the invoke request into its internal queue and returns **HTTP status 202 ("Accepted")**, EventBridge considers delivery successful. **EventBridge does NOT observe function execution results, does NOT retry function errors, and never writes execution errors to the EventBridge DLQ.**

#### Path B: Lambda Asynchronous Invocation Queue & Function Execution Failures
- **What it is:** The event is inside Lambda's internal asynchronous queue. Lambda invokes the handler. If the function raises an unhandled exception (e.g. [`TransientCommitRetrievalError`](file:///c:/Users/Darsh/OneDrive/Desktop/GitOps%20Commit%20Light/backend/lambda/lambda_function.py#L42-L46) or [`TransientMQTTPublishError`](file:///c:/Users/Darsh/OneDrive/Desktop/GitOps%20Commit%20Light/backend/lambda/lambda_function.py#L48-L52)), the Lambda runtime records an execution failure (`FunctionError`).
- **Handling Mechanism:** Handled entirely by AWS Lambda Asynchronous Event Invoke Config using [`aws/lambda-event-invoke-config.json`](file:///c:/Users/Darsh/OneDrive/Desktop/GitOps%20Commit%20Light/aws/lambda-event-invoke-config.json).
- **Service Limits & Defaults:**
  - `MaximumRetryAttempts`: Valid range **0 to 2** (default: 2). *Notice: Lambda retries at most 2 times, NOT 185 times!*
  - `MaximumEventAgeInSeconds`: Valid range **60 to 21,600 seconds** (1 minute to 6 hours; default: 21,600). *Notice: Maximum age is 6 hours, NOT 24 hours!*
- **Lambda On-Failure Destination / DLQ:** When Lambda exhausts its 2 retries (or 6 hours expire), Lambda sends a detailed invocation record (request payload, error type, and stack trace) to `arn:aws:sqs:<REGION>:<ACCOUNT_ID>:<LAMBDA_DLQ_NAME>`.
- **Required IAM Permission:** For Lambda to deliver the invocation record to SQS, the Lambda execution role **must** have `sqs:SendMessage` on the queue ARN (configured in [`aws/lambda-policy.json`](file:///c:/Users/Darsh/OneDrive/Desktop/GitOps%20Commit%20Light/aws/lambda-policy.json)).

### Side-by-Side Architectural Comparison

| Dimension | Path A: EventBridge Target Delivery | Path B: Lambda Asynchronous Execution |
| :--- | :--- | :--- |
| **Trigger Condition** | Inability to deliver event to Lambda service API | Lambda handler raises an unhandled exception |
| **Managing Service** | Amazon EventBridge | AWS Lambda Asynchronous Queue |
| **Configuration File** | [`aws/eventbridge-target.json`](file:///c:/Users/Darsh/OneDrive/Desktop/GitOps%20Commit%20Light/aws/eventbridge-target.json) | [`aws/lambda-event-invoke-config.json`](file:///c:/Users/Darsh/OneDrive/Desktop/GitOps%20Commit%20Light/aws/lambda-event-invoke-config.json) |
| **AWS API / CLI** | `aws events put-targets` | `aws lambda put-function-event-invoke-config` |
| **Retry Range** | 0 to 185 retries | 0 to 2 retries |
| **Event Age Range** | 60 to 86,400 seconds (up to 24 hours) | 60 to 21,600 seconds (up to 6 hours) |
| **Dead-Letter Queue** | EventBridge Target DLQ (`<EVENTBRIDGE_DLQ_NAME>`) | Lambda On-Failure Destination DLQ (`<LAMBDA_DLQ_NAME>`) |
| **DLQ Message Content** | Original unmodified event payload | Invocation record JSON with stack trace & request payload |
| **Required Permissions** | EventBridge SQS policy / KMS key permissions | Lambda execution role `sqs:SendMessage` |

### Entry Point Configuration Requirement

The deployment template [`aws/lambda-function-config.json`](file:///c:/Users/Darsh/OneDrive/Desktop/GitOps%20Commit%20Light/aws/lambda-function-config.json) explicitly sets:
```json
"Handler": "lambda_function.production_lambda_handler"
```
**Why this is mandatory:**
- If the handler were mistakenly configured as `lambda_function.lambda_handler`, `raise_on_retryable` defaults to `False`.
- Under `raise_on_retryable=False`, transient errors return a dictionary `{"statusCode": 500, "status": "error"}`.
- To the AWS Lambda service, any dictionary return is evaluated as a **clean exit code 0 (success)**.
- Lambda would dequeue and discard the event without ever retrying or forwarding to the Lambda DLQ, leading to **silent message loss**.
- Using `production_lambda_handler` guarantees `raise_on_retryable=True` is always enforced in cloud deployment.

---

## 4. Responsibility Separation: Code vs. Cloud Configuration

| Responsibility | Handled in Python Code | Configured in AWS Cloud |
| :--- | :--- | :--- |
| Schema validation & poison-pill detection | Yes (`lambda_function.py`) | No |
| Acknowledging permanent defects with code 400 | Yes (`lambda_function.py`) | No |
| Raising transient exceptions to trigger Path B | Yes (`production_lambda_handler`) | No |
| Target delivery retry loop (Path A) | No | Yes (`aws/eventbridge-target.json`) |
| Target delivery failure DLQ (Path A) | No | Yes (`aws/eventbridge-target.json` + SQS) |
| Function execution retry loop (Path B) | No | Yes (`aws/lambda-event-invoke-config.json`) |
| Function failure On-Failure DLQ (Path B) | No | Yes (`aws/lambda-event-invoke-config.json` + SQS) |
| DLQ delivery permission | No | Yes (`aws/lambda-policy.json`) |
| Entry point mapping | No | Yes (`aws/lambda-function-config.json`) |

---

## 5. Offline Verification Suite

The repository includes a dedicated offline verification suite in [`tests/test_aws_policies.py`](file:///c:/Users/Darsh/OneDrive/Desktop/GitOps%20Commit%20Light/tests/test_aws_policies.py) to guarantee:
1. **JSON Syntax:** All JSON configuration templates in `aws/` parse without syntax errors.
2. **Security & Placeholders:** No hardcoded AWS 12-digit account IDs, real secrets, or credentials exist.
3. **Least-Privilege Enforcement:**
   - Lambda `iot:Publish` is scoped strictly to `topic/gitops/commits` with no wildcards.
   - CodeCommit permissions are strictly read-only (`codecommit:GetCommit`).
   - Lambda role includes `sqs:SendMessage` scoped strictly to `arn:aws:sqs:<REGION>:<ACCOUNT_ID>:<LAMBDA_DLQ_NAME>`.
   - ESP32 policy contains **no** `iot:Publish` permission, strictly separating client connect, topicfilter subscribe, and topic receive.
4. **Service Limit Compliance & Retry Counter Independence:**
   - EventBridge target retries comply with `0 <= retries <= 185` and `60 <= age <= 86400`.
   - Lambda async retries comply with `0 <= retries <= 2` and `60 <= age <= 21600`.
   - Verifies EventBridge and Lambda do not share one retry counter or configuration.
   - Verifies `lambda-function-config.json` sets `Handler` to `lambda_function.production_lambda_handler`.

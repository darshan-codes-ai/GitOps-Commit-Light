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
| [`aws/trust-policy.json`](file:///c:/Users/Darsh/OneDrive/Desktop/GitOps%20Commit%20Light/aws/trust-policy.json) | IAM Role Trust Policy (`create-role`) | Authorizes the AWS Lambda service principal (`lambda.amazonaws.com`) to assume the execution role. |
| [`aws/eventbridge-rule.json`](file:///c:/Users/Darsh/OneDrive/Desktop/GitOps%20Commit%20Light/aws/eventbridge-rule.json) | EventBridge Rule (`put-rule`) | Filters CodeCommit repository state changes strictly for branch updates on `main`. |
| [`aws/eventbridge-target.json`](file:///c:/Users/Darsh/OneDrive/Desktop/GitOps%20Commit%20Light/aws/eventbridge-target.json) | EventBridge Target (`put-targets`) | Configures Path A Target Delivery: Lambda target, delivery retry limits (185 attempts, 24h), and Target DLQ. |
| [`aws/eventbridge-dlq-policy.json`](file:///c:/Users/Darsh/OneDrive/Desktop/GitOps%20Commit%20Light/aws/eventbridge-dlq-policy.json) | SQS Queue Resource Policy (`set-queue-attributes`) | Authorizes the EventBridge service principal (`events.amazonaws.com`) to write failed target delivery events to the EventBridge DLQ. |
| [`aws/lambda-function-config.json`](file:///c:/Users/Darsh/OneDrive/Desktop/GitOps%20Commit%20Light/aws/lambda-function-config.json) | Lambda Function Config (`create-function`) | Establishes runtime settings, environment variables (`IOT_DATA_ENDPOINT`, `MQTT_TOPIC`), and enforces `lambda_function.production_lambda_handler` for CodeCommit. |
| [`aws/lambda-event-invoke-config.json`](file:///c:/Users/Darsh/OneDrive/Desktop/GitOps%20Commit%20Light/aws/lambda-event-invoke-config.json) | Lambda Event Invoke Config (`put-function-event-invoke-config`) | Configures Path B Asynchronous Execution: function retry limits (2 retries, 6h), and Lambda On-Failure DLQ destination. |
| [`aws/lambda-policy.json`](file:///c:/Users/Darsh/OneDrive/Desktop/GitOps%20Commit%20Light/aws/lambda-policy.json) | IAM Execution Role Policy (CodeCommit) | Grants Lambda permissions to log to CloudWatch, query CodeCommit, publish to IoT Core, and write to Lambda DLQ. |
| [`aws/lambda-resource-policy.json`](file:///c:/Users/Darsh/OneDrive/Desktop/GitOps%20Commit%20Light/aws/lambda-resource-policy.json) | Lambda Resource Policy (`add-permission`) | Authorizes the Amazon EventBridge service principal to invoke the CodeCommit Lambda function. |
| [`aws/iot-policy.json`](file:///c:/Users/Darsh/OneDrive/Desktop/GitOps%20Commit%20Light/aws/iot-policy.json) | AWS IoT Core Certificate Policy | Grants the physical ESP32 device permission to connect, subscribe, and receive messages (strictly no publishing). |
| [`aws/apigateway-http-api.json`](file:///c:/Users/Darsh/OneDrive/Desktop/GitOps%20Commit%20Light/aws/apigateway-http-api.json) | API Gateway HTTP API Specification | Declarative resource specification for HTTP API v2 route (`POST /webhook/github`), Lambda proxy integration v2.0, and stage throttling. |
| [`aws/apigateway-lambda-permission.json`](file:///c:/Users/Darsh/OneDrive/Desktop/GitOps%20Commit%20Light/aws/apigateway-lambda-permission.json) | Lambda Resource Policy (`add-permission`) | Authorizes Amazon API Gateway (`apigateway.amazonaws.com`) scoped strictly to `POST /webhook/github` and `<ACCOUNT_ID>`. |
| [`aws/lambda-github-policy.json`](file:///c:/Users/Darsh/OneDrive/Desktop/GitOps%20Commit%20Light/aws/lambda-github-policy.json) | IAM Execution Role Policy (GitHub) | Dedicated least-privilege policy granting only CloudWatch logging, IoT Core publish, and Secrets Manager read access (no CodeCommit or SQS). |
| [`aws/lambda-github-function-config.json`](file:///c:/Users/Darsh/OneDrive/Desktop/GitOps%20Commit%20Light/aws/lambda-github-function-config.json) | Lambda Function Config (GitHub) | Runtime settings and environment variables (`GITHUB_WEBHOOK_SECRET_ARN`, `MONITORED_BRANCH`, `IOT_DATA_ENDPOINT`), enforcing `lambda_function.github_webhook_handler`. |
| [`aws/github-webhook-template.yaml`](file:///c:/Users/Darsh/OneDrive/Desktop/GitOps%20Commit%20Light/aws/github-webhook-template.yaml) | CloudFormation Template (Authoritative Deployable Stack) | Fully parameterized, single-step deployable CloudFormation template orchestrating API Gateway v2, Lambda, IAM, and LogGroup. |

---

## 2. Policy Decoupling & Permissions Matrix

Responsibilities are strictly separated across isolated planes to enforce the principle of least privilege:

### A. Lambda Execution-Role Trust Policy (`aws/trust-policy.json`)
Attached to the IAM role itself (AssumeRolePolicyDocument):
- **Principal:** `lambda.amazonaws.com`
- **Action:** `sts:AssumeRole`
- *Authorizes the AWS Lambda compute service to assume this role when executing the function.*

### B. Lambda Execution-Role Permissions Policy (`aws/lambda-policy.json`)
Inline or customer-managed policy attached to the IAM role assumed by Lambda:
- **CloudWatch Logs:**
  - `logs:CreateLogGroup` on `arn:aws:logs:<REGION>:<ACCOUNT_ID>:log-group:/aws/lambda/<FUNCTION_NAME>` (auto-provisions log group on first execution).
  - `logs:CreateLogStream`, `logs:PutLogEvents` on `arn:aws:logs:<REGION>:<ACCOUNT_ID>:log-group:/aws/lambda/<FUNCTION_NAME>:*`.
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

### C. EventBridge Target DLQ SQS Queue Policy (`aws/eventbridge-dlq-policy.json`)
Attached to the Amazon SQS queue designated as `<EVENTBRIDGE_DLQ_NAME>`:
- **Principal:** `events.amazonaws.com`
- **Action:** `sqs:SendMessage`
- **Resource:** `arn:aws:sqs:<REGION>:<ACCOUNT_ID>:<EVENTBRIDGE_DLQ_NAME>`
- **Conditions:** `aws:SourceArn` matches `arn:aws:events:<REGION>:<ACCOUNT_ID>:rule/<RULE_NAME>` and `aws:SourceAccount` matches `<ACCOUNT_ID>`.
- *Authorizes EventBridge to write target delivery failure events (Path A) to its dedicated DLQ.*

### D. EventBridge Invocation Permission (`aws/lambda-resource-policy.json`)
Resource-based policy attached directly to the Lambda function resource:
- **Principal:** `events.amazonaws.com`
- **Action:** `lambda:InvokeFunction`
- **Condition:** `ArnLike` matching `AWS:SourceArn: arn:aws:events:<REGION>:<ACCOUNT_ID>:rule/<RULE_NAME>`
- *Guarantees that only the designated EventBridge rule can trigger the function.*

### E. ESP32 IoT Certificate Policy (`aws/iot-policy.json`)
Attached to the X.509 client certificate installed on the ESP32 hardware:
- **`iot:Connect`:** Resource: `arn:aws:iot:<REGION>:<ACCOUNT_ID>:client/${iot:Connection.Thing.ThingName}`
- **`iot:Subscribe`:** Resource: `arn:aws:iot:<REGION>:<ACCOUNT_ID>:topicfilter/gitops/commits` (*AWS IoT `topicfilter/` namespace*)
- **`iot:Receive`:** Resource: `arn:aws:iot:<REGION>:<ACCOUNT_ID>:topic/gitops/commits` (*AWS IoT `topic/` namespace*)
- **Security Invariant — No Publish Rights:** The ESP32 is exclusively a consumer/subscriber. It **must not** possess `iot:Publish` permissions, preventing edge device compromise from injecting falsified commit notifications.

### 🛡️ Summary of Authorization Boundaries

| Authorization Mechanism | Target Resource | Authorized Principal | Actions Permitted | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **Trust Policy** (`trust-policy.json`) | IAM Role | `lambda.amazonaws.com` | `sts:AssumeRole` | Allows Lambda to assume the execution role |
| **Execution Policy** (`lambda-policy.json`) | CloudWatch, CodeCommit, IoT, SQS | Lambda Function | `logs:*`, `codecommit:GetCommit`, `iot:Publish`, `sqs:SendMessage` | Lambda runtime execution permissions |
| **EventBridge DLQ Policy** (`eventbridge-dlq-policy.json`) | SQS (`<EVENTBRIDGE_DLQ_NAME>`) | `events.amazonaws.com` | `sqs:SendMessage` | EventBridge writes Path A delivery failures |
| **Lambda OnFailure DLQ** (`lambda-policy.json`) | SQS (`<LAMBDA_DLQ_NAME>`) | Lambda Execution Role | `sqs:SendMessage` | Lambda writes Path B function execution failures |

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

---

## 6. GitHub Webhook Architecture: API Gateway HTTP API & Dedicated Lambda

To transition to GitHub as the event source while leaving the CodeCommit pipeline intact, the system introduces a dedicated synchronous ingestion path:

```
[ Developer: git push to GitHub ]
                │
                ▼
      ┌──────────────────┐
      │  GitHub.com Repo │  Generates push event payload (commit message included!)
      └─────────┬────────┘  Signs body with HMAC-SHA256 (X-Hub-Signature-256)
                │
                ▼ HTTPS POST /webhook/github
┌─────────────────────────────────┐
│ Amazon API Gateway (HTTP API v2)│  Defined in aws/apigateway-http-api.json
│        (Route & Stage)          │  Throttled: 50 req/sec, burst 100
└───────────────┬─────────────────┘
                │ Synchronous Lambda Proxy Integration (PayloadFormatVersion: "2.0")
                ▼
┌─────────────────────────────────┐
│     Dedicated GitHub Lambda     │  Configured in aws/lambda-github-function-config.json
│(github_webhook_handler entry)   │  IAM Role in aws/lambda-github-policy.json
│                                 │
│  1. Check GITHUB_WEBHOOK_SECRET │  Fail closed (500) if unconfigured
│  2. Verify HMAC-SHA256 (403)    │  Constant-time check over raw bytes (handles base64)
│  3. Filter Event & Branch (200) │  Acknowledge ping, branch-delete, non-main without publishing
│  4. Build Schema v1 Message     │  Maps head_commit directly (zero external API calls!)
│  5. Publish to AWS IoT Core     │  Reuses existing Boto3IotDataPublisher
└───────────────┬─────────────────┘
                │
                ├────────────────────────────────────────┐
                ▼ MQTT over TLS (gitops/commits)         ▼ Synchronous HTTP Response
      ┌──────────────────┐                     ┌───────────────────┐
      │   AWS IoT Core   │                     │  API Gateway HTTP │
      │  gitops/commits  │                     │   200 OK / 502    │
      └─────────┬────────┘                     └─────────┬─────────┘
                │ MQTT                                   │ Delivery Status
                ▼                                        ▼
      ┌──────────────────┐                     ┌───────────────────┐
      │   ESP32 Device   │                     │  GitHub Webhooks  │
      │ (No code change) │                     │ (Green checkmark) │
      └──────────────────┘                     └───────────────────┘
```

### 1. Dedicated GitHub Lambda vs. CodeCommit Lambda Separation
* **CodeCommit Pipeline (`aws/lambda-function-config.json`):**
  - Handler: `lambda_function.production_lambda_handler`
  - Trigger: Asynchronous EventBridge state-change rule.
  - IAM Policy: Includes `codecommit:GetCommit` and `sqs:SendMessage` for Path B DLQ.
* **GitHub Pipeline (`aws/lambda-github-function-config.json`):**
  - Handler: `lambda_function.github_webhook_handler`
  - Trigger: Synchronous API Gateway HTTP API v2 (`POST /webhook/github`).
  - IAM Policy: Strictly scoped to CloudWatch Logs and `iot:Publish`. **No CodeCommit or SQS permissions.**

### 2. API Gateway HTTP API Specification (`aws/apigateway-http-api.json`)
The file [`aws/apigateway-http-api.json`](file:///c:/Users/Darsh/OneDrive/Desktop/GitOps%20Commit%20Light/aws/apigateway-http-api.json) provides a declarative specification of the required API Gateway v2 resources:
* **Protocol:** HTTP API (API Gateway v2) for lower cost ($1.00/million calls) and reduced latency.
* **Route:** `POST /webhook/github` with `AuthorizationType: NONE` (authentication is handled via HMAC-SHA256 signature in Lambda).
* **Integration:** `IntegrationType: AWS_PROXY`, `PayloadFormatVersion: "2.0"`, targeting the GitHub Lambda function ARN.
* **Stage:** `$default` with `AutoDeploy: true`.
* **Throttling:** Default route throttling configured with `ThrottlingBurstLimit: 100` and `ThrottlingRateLimit: 50` req/sec to protect downstream services against denial-of-service spikes.

#### Multi-Step AWS CLI Provisioning Sequence
Because API Gateway HTTP APIs require creating interconnected resources, deployment via AWS CLI follows this sequence:
```powershell
# 1. Create HTTP API
$apiId = (aws apigatewayv2 create-api --name "<API_NAME>" --protocol-type HTTP --query "ApiId" --output text)

# 2. Create Lambda Proxy Integration (Payload v2.0)
$integrationId = (aws apigatewayv2 create-integration --api-id $apiId --integration-type AWS_PROXY `
    --integration-uri "arn:aws:lambda:<REGION>:<ACCOUNT_ID>:function:<GITHUB_FUNCTION_NAME>" `
    --payload-format-version "2.0" --query "IntegrationId" --output text)

# 3. Create Route targeting the integration
aws apigatewayv2 create-route --api-id $apiId --route-key "POST /webhook/github" `
    --target "integrations/$integrationId"

# 4. Create and deploy $default stage with throttling
aws apigatewayv2 create-stage --api-id $apiId --stage-name "$default" --auto-deploy `
    --default-route-settings "ThrottlingBurstLimit=100,ThrottlingRateLimit=50,DetailedMetricsEnabled=true"

# 5. Grant API Gateway permission to invoke Lambda
aws lambda add-permission --function-name "<GITHUB_FUNCTION_NAME>" `
    --statement-id "AllowApiGatewayToInvokeGitHubWebhookLambda" `
    --action "lambda:InvokeFunction" --principal "apigateway.amazonaws.com" `
    --source-arn "arn:aws:execute-api:<REGION>:<ACCOUNT_ID>:$apiId/$default/POST/webhook/github"
```

#### Declarative CloudFormation Equivalent
For automated single-step deployment, the equivalent CloudFormation snippet is:
```yaml
Resources:
  GitHubHttpApi:
    Type: AWS::ApiGatewayV2::Api
    Properties:
      Name: GitOpsCommitLight-GitHubApi
      ProtocolType: HTTP

  GitHubApiIntegration:
    Type: AWS::ApiGatewayV2::Integration
    Properties:
      ApiId: !Ref GitHubHttpApi
      IntegrationType: AWS_PROXY
      IntegrationUri: !GetAtt GitHubWebhookFunction.Arn
      PayloadFormatVersion: "2.0"

  GitHubApiRoute:
    Type: AWS::ApiGatewayV2::Route
    Properties:
      ApiId: !Ref GitHubHttpApi
      RouteKey: "POST /webhook/github"
      Target: !Join ['/', ['integrations', !Ref GitHubApiIntegration]]

  GitHubApiStage:
    Type: AWS::ApiGatewayV2::Stage
    Properties:
      ApiId: !Ref GitHubHttpApi
      StageName: "$default"
      AutoDeploy: true
      DefaultRouteSettings:
        ThrottlingBurstLimit: 100
        ThrottlingRateLimit: 50

  GitHubApiLambdaPermission:
    Type: AWS::Lambda::Permission
    Properties:
      FunctionName: !Ref GitHubWebhookFunction
      Action: lambda:InvokeFunction
      Principal: apigateway.amazonaws.com
      SourceArn: !Sub "arn:aws:execute-api:${AWS::Region}:${AWS::AccountId}:${GitHubHttpApi}/$default/POST/webhook/github"
```

### 3. Narrowly Scoped Lambda Invocation Permission (`aws/apigateway-lambda-permission.json`)
The resource-based policy statement restricts execution strictly:
* **Principal:** `apigateway.amazonaws.com`.
* **Action:** `lambda:InvokeFunction`.
* **Resource:** `arn:aws:lambda:<REGION>:<ACCOUNT_ID>:function:<GITHUB_FUNCTION_NAME>`.
* **Scoped Source ARN:** `arn:aws:execute-api:<REGION>:<ACCOUNT_ID>:<API_ID>/$default/POST/webhook/github`. This guarantees that **only** the designated API, the `$default` stage, the `POST` method, and the `/webhook/github` path can invoke the function.
* **Source Account Condition:** `aws:SourceAccount: "<ACCOUNT_ID>"` prevents cross-account confused deputy vulnerabilities.

### 4. Dedicated Least-Privilege IAM Policy (`aws/lambda-github-policy.json`)
* **CloudWatch Logs:**
  - `logs:CreateLogGroup` on `arn:aws:logs:<REGION>:<ACCOUNT_ID>:log-group:/aws/lambda/<GITHUB_FUNCTION_NAME>`.
  - `logs:CreateLogStream`, `logs:PutLogEvents` on `arn:aws:logs:<REGION>:<ACCOUNT_ID>:log-group:/aws/lambda/<GITHUB_FUNCTION_NAME>:*`.
  - *Note: Pre-creating the log group `/aws/lambda/<GITHUB_FUNCTION_NAME>` prior to deployment is best practice to avoid cold-start IAM races.*
* **AWS IoT Core:**
  - `iot:Publish` restricted strictly to `arn:aws:iot:<REGION>:<ACCOUNT_ID>:topic/gitops/commits`.
* **AWS Secrets Manager:**
  - `secretsmanager:GetSecretValue` on `arn:aws:secretsmanager:<REGION>:<ACCOUNT_ID>:secret:<SECRET_NAME>-*` (or specific secret ARN).
* **Zero Extraneous Permissions:**
  - **No `codecommit:*`:** GitHub push events embed commit metadata; no SDK queries to CodeCommit are made.
  - **No `sqs:*`:** API Gateway integration is synchronous; dead-letter queues are not attached to synchronous proxy invocations.
  - **No administrative wildcards (`logs:*`, `iot:*`, `secretsmanager:*`, `Resource: "*"`).**

### 5. Secure Webhook Secret Provisioning (`GITHUB_WEBHOOK_SECRET` & Secrets Manager)
* **Security Rules:**
  - Never commit real secret strings into `aws/lambda-github-function-config.json`, CloudFormation templates, or Git repositories.
  - Configuration files maintain token placeholders (`"<GITHUB_WEBHOOK_SECRET_PLACEHOLDER>"`, `<SECRET_NAME>`).
* **Recommended Provisioning Architecture:**
  1. **AWS Secrets Manager (Preferred & Default in CloudFormation Stack):**
     - The shared webhook secret is created in AWS Secrets Manager:
       ```powershell
       aws secretsmanager create-secret --name "gitops-commit-light/github-webhook-secret" `
         --secret-string "$GeneratedSecretToken"
       ```
     - The Lambda execution role is granted `secretsmanager:GetSecretValue` strictly on this secret's ARN.
     - At runtime, [`github_webhook_handler`](file:///c:/Users/Darsh/OneDrive/Desktop/GitOps%20Commit%20Light/backend/lambda/lambda_function.py#L890) retrieves the secret via boto3 `secretsmanager.get_secret_value(SecretId=...)`.
     - **In-Memory Caching:** To minimize Secrets Manager latency and API costs, the secret is cached in-memory across warm Lambda invocations. Calls to Secrets Manager occur only during container cold starts.
     - **Cost Consideration:** AWS Secrets Manager costs **$0.40 per secret per month** and **$0.05 per 10,000 API calls**. Because warm containers cache the secret, API call volume is negligible (< $0.01/month for typical commit rates).
  2. **Direct Environment Variable Injection (Low-Cost Alternative):**
     - If avoiding Secrets Manager's $0.40/month cost, the secret can be injected as a masked environment variable (`GITHUB_WEBHOOK_SECRET`) during CI/CD deployment or AWS CLI `update-function-configuration`. The code supports both methods seamlessly.

### 6. Missing Delivery ID Enforcement
* **Enforced Behavior:**
  - [`github_webhook_handler`](file:///c:/Users/Darsh/OneDrive/Desktop/GitOps%20Commit%20Light/backend/lambda/lambda_function.py#L1170) strictly requires `X-GitHub-Delivery`.
  - If missing or empty, it returns **HTTP 400 Bad Request** (`{"status": "error", "message": "Missing required X-GitHub-Delivery header."}`) and **publishes zero MQTT messages**.
  - Fallback UUID generation has been removed to enforce strict GitHub webhook contract compliance.

### 7. Authoritative vs. Illustrative Template Hierarchy
* **Deployable CloudFormation Stack ([`aws/github-webhook-template.yaml`](file:///c:/Users/Darsh/OneDrive/Desktop/GitOps%20Commit%20Light/aws/github-webhook-template.yaml)):**
  - **Authoritative Deployable Template.** Contains the complete, parameterized, single-step AWS CloudFormation template ready for deployment with `aws cloudformation deploy`.
* **Modular Specifications (`aws/apigateway-*.json`, `aws/lambda-github-*.json`):**
  - **Authoritative Declarative Definitions** for granular, multi-step AWS CLI scripting or microservice orchestration. They provide exact schema mappings and IAM policy definitions decoupled from CloudFormation syntax.

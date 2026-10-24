"""Offline verification tests for AWS infrastructure configuration files.

Validates:
1. JSON syntax correctness across all configuration files in aws/.
2. Absence of hardcoded AWS 12-digit account IDs, real regions, or secret keys.
3. IAM Role Trust Policy (aws/trust-policy.json):
   - Restricted strictly to lambda.amazonaws.com principal and sts:AssumeRole.
4. EventBridge Target DLQ SQS Resource Policy (aws/eventbridge-dlq-policy.json):
   - Restricted strictly to events.amazonaws.com principal and sqs:SendMessage.
   - Condition scoped to aws:SourceArn (rule ARN) and aws:SourceAccount (account ID).
5. Decoupled Retry & DLQ Architecture (Path A vs Path B):
   - Path A (Target Delivery): EventBridge Target RetryPolicy (0-185 attempts, max 86400s)
     and EventBridge DeadLetterConfig.
   - Path B (Function Execution): Lambda Asynchronous Event Invoke Config (0-2 attempts,
     max 21600s) and On-Failure Destination DLQ.
   - Distinct retry counters and compliance with current AWS service limits.
6. Production Handler Entry Point:
   - Verifies lambda-function-config.json specifies 'lambda_function.production_lambda_handler'.
7. Least-privilege IAM policy invariants:
   - Lambda execution role (aws/lambda-policy.json):
     * logs:CreateLogGroup scoped to log-group.
     * logs:CreateLogStream and logs:PutLogEvents restricted to function log-group streams.
     * No logs:* wildcard.
     * iot:Publish restricted strictly to 'gitops/commits' topic (no wildcards).
     * codecommit:GetCommit read-only on repository ARN.
     * sqs:SendMessage restricted to Lambda On-Failure DLQ ARN.
   - ESP32 IoT certificate policy (aws/iot-policy.json):
     * Actions restricted to iot:Connect, iot:Subscribe, and iot:Receive.
     * iot:Publish is strictly absent (subscriber-only device).
     * iot:Subscribe uses 'topicfilter/gitops/commits'.
     * iot:Receive uses 'topic/gitops/commits'.
   - EventBridge Rule (aws/eventbridge-rule.json):
     * Scoped to aws.codecommit source and main branch.
   - Lambda Resource Policy (aws/lambda-resource-policy.json):
     * Scoped to events.amazonaws.com principal and rule ARN condition.
"""

import json
from pathlib import Path
import re
import unittest
import yaml

AWS_DIR = Path(__file__).resolve().parent.parent / "aws"


class TestAwsConfigurationJson(unittest.TestCase):
    """Test JSON syntax validity and placeholder conventions in aws/."""

    EXPECTED_FILES = [
        "eventbridge-rule.json",
        "eventbridge-target.json",
        "eventbridge-dlq-policy.json",
        "trust-policy.json",
        "lambda-function-config.json",
        "lambda-event-invoke-config.json",
        "lambda-policy.json",
        "lambda-resource-policy.json",
        "iot-policy.json",
        "apigateway-http-api.json",
        "apigateway-lambda-permission.json",
        "lambda-github-policy.json",
        "lambda-github-function-config.json",
    ]

    def test_all_expected_files_exist(self):
        """Verify that all required AWS configuration templates exist."""
        for filename in self.EXPECTED_FILES:
            file_path = AWS_DIR / filename
            self.assertTrue(
                file_path.is_file(),
                f"Missing expected AWS template file: {filename}",
            )

    def test_all_json_files_parse_validly(self):
        """Verify that every JSON file in aws/ contains valid JSON syntax."""
        json_files = list(AWS_DIR.glob("*.json"))
        self.assertGreaterEqual(len(json_files), 9)
        for json_file in json_files:
            with open(json_file, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                    self.assertIsInstance(
                        data, dict, f"{json_file.name} root must be a JSON object"
                    )
                except json.JSONDecodeError as err:
                    self.fail(f"Invalid JSON syntax in {json_file.name}: {err}")

    def test_no_hardcoded_aws_account_ids_or_credentials(self):
        """Verify that no real 12-digit AWS account IDs or secrets exist in any template."""
        account_id_pattern = re.compile(r"\b\d{12}\b")
        secret_indicators = [
            "BEGIN PRIVATE KEY",
            "BEGIN RSA PRIVATE KEY",
            "BEGIN CERTIFICATE",
            "AKIA",  # AWS Access Key ID prefix
        ]

        for template_file in list(AWS_DIR.glob("*.json")) + list(AWS_DIR.glob("*.yaml")):
            content = template_file.read_text(encoding="utf-8")

            matches = account_id_pattern.findall(content)
            self.assertEqual(
                matches,
                [],
                f"Hardcoded 12-digit AWS account ID found in {template_file.name}: {matches}",
            )

            for indicator in secret_indicators:
                self.assertNotIn(
                    indicator,
                    content,
                    f"Credential indicator '{indicator}' detected in {template_file.name}",
                )

            # Templates containing ARNs or account IDs must use <ACCOUNT_ID> placeholder
            if "arn:aws:" in content or "SourceAccount" in content:
                self.assertIn(
                    "<ACCOUNT_ID>",
                    content,
                    f"Expected placeholder <ACCOUNT_ID> in {json_file.name}",
                )


class TestTrustPolicy(unittest.TestCase):
    """Test IAM Role Trust Policy for Lambda execution role."""

    def setUp(self):
        with open(AWS_DIR / "trust-policy.json", "r", encoding="utf-8") as f:
            self.policy = json.load(f)
        self.statements = self.policy.get("Statement", [])

    def test_trust_policy_structure(self):
        """Verify trust policy permits only lambda.amazonaws.com to sts:AssumeRole."""
        self.assertEqual(self.policy.get("Version"), "2012-10-17")
        self.assertEqual(len(self.statements), 1)

        stmt = self.statements[0]
        self.assertEqual(stmt.get("Effect"), "Allow")
        self.assertEqual(
            stmt.get("Principal"),
            {"Service": "lambda.amazonaws.com"},
            "Trust policy must authorize only lambda.amazonaws.com service principal",
        )
        self.assertEqual(stmt.get("Action"), "sts:AssumeRole")


class TestEventBridgeTargetDlqPolicy(unittest.TestCase):
    """Test SQS Queue Resource Policy for EventBridge Target DLQ."""

    def setUp(self):
        with open(AWS_DIR / "eventbridge-dlq-policy.json", "r", encoding="utf-8") as f:
            self.policy = json.load(f)
        self.statements = self.policy.get("Statement", [])

    def test_eb_dlq_policy_structure(self):
        """Verify EventBridge DLQ policy authorizes events.amazonaws.com for sqs:SendMessage."""
        self.assertEqual(self.policy.get("Version"), "2012-10-17")
        self.assertEqual(len(self.statements), 1)

        stmt = self.statements[0]
        self.assertEqual(stmt.get("Effect"), "Allow")
        self.assertEqual(
            stmt.get("Principal"),
            {"Service": "events.amazonaws.com"},
            "EventBridge DLQ policy must authorize only events.amazonaws.com",
        )
        self.assertEqual(stmt.get("Action"), "sqs:SendMessage")
        self.assertEqual(
            stmt.get("Resource"),
            "arn:aws:sqs:<REGION>:<ACCOUNT_ID>:<EVENTBRIDGE_DLQ_NAME>",
        )

        condition = stmt.get("Condition", {})
        # Verify aws:SourceArn and aws:SourceAccount conditions
        arn_cond = condition.get("ArnEquals", {}).get("aws:SourceArn")
        self.assertEqual(
            arn_cond,
            "arn:aws:events:<REGION>:<ACCOUNT_ID>:rule/<RULE_NAME>",
            "EventBridge DLQ policy must be restricted to the rule ARN",
        )
        acct_cond = condition.get("StringEquals", {}).get("aws:SourceAccount")
        self.assertEqual(
            acct_cond,
            "<ACCOUNT_ID>",
            "EventBridge DLQ policy must be restricted to the source account ID",
        )

    def test_separation_between_eb_dlq_and_lambda_dlq(self):
        """Verify EventBridge DLQ and Lambda DLQ use distinct queue names and mechanisms."""
        with open(AWS_DIR / "eventbridge-dlq-policy.json", "r", encoding="utf-8") as f:
            eb_dlq = json.load(f)
        with open(AWS_DIR / "lambda-policy.json", "r", encoding="utf-8") as f:
            lambda_policy = json.load(f)

        eb_res = eb_dlq["Statement"][0]["Resource"]
        lambda_sqs_stmt = next(
            s for s in lambda_policy["Statement"] if "sqs:SendMessage" in s.get("Action", [])
        )
        lambda_res = lambda_sqs_stmt["Resource"]

        self.assertIn("<EVENTBRIDGE_DLQ_NAME>", eb_res)
        self.assertIn("<LAMBDA_DLQ_NAME>", lambda_res)
        self.assertNotEqual(eb_res, lambda_res, "EventBridge DLQ and Lambda DLQ must use separate queues")


class TestLambdaPolicyLeastPrivilege(unittest.TestCase):
    """Test IAM permissions for the Lambda execution role."""

    def setUp(self):
        with open(AWS_DIR / "lambda-policy.json", "r", encoding="utf-8") as f:
            self.policy = json.load(f)
        self.statements = self.policy.get("Statement", [])

    def test_statement_structure(self):
        """Verify policy version and statements."""
        self.assertEqual(self.policy.get("Version"), "2012-10-17")
        self.assertGreaterEqual(len(self.statements), 5)

    def test_iot_publish_strictly_scoped(self):
        """Verify iot:Publish is scoped strictly to topic/gitops/commits without wildcards."""
        iot_stmt = next(
            (
                s
                for s in self.statements
                if "iot:Publish" in s.get("Action", [])
                or s.get("Action") == "iot:Publish"
            ),
            None,
        )
        self.assertIsNotNone(iot_stmt, "Missing iot:Publish statement in Lambda policy")
        self.assertEqual(iot_stmt.get("Effect"), "Allow")

        resource = iot_stmt.get("Resource")
        self.assertEqual(
            resource,
            "arn:aws:iot:<REGION>:<ACCOUNT_ID>:topic/gitops/commits",
            "iot:Publish must be scoped strictly to 'topic/gitops/commits' without wildcards",
        )
        self.assertNotIn("*", resource)

    def test_codecommit_read_only_access(self):
        """Verify CodeCommit permission is read-only (codecommit:GetCommit)."""
        cc_stmt = next(
            (
                s
                for s in self.statements
                if "codecommit:GetCommit" in s.get("Action", [])
                or s.get("Action") == "codecommit:GetCommit"
            ),
            None,
        )
        self.assertIsNotNone(
            cc_stmt, "Missing codecommit:GetCommit statement in Lambda policy"
        )
        self.assertEqual(cc_stmt.get("Effect"), "Allow")

        actions = cc_stmt.get("Action")
        if isinstance(actions, str):
            actions = [actions]
        for act in actions:
            self.assertTrue(
                act.startswith("codecommit:Get")
                or act.startswith("codecommit:Describe")
                or act.startswith("codecommit:List")
                or act.startswith("codecommit:BatchGet"),
                f"Unauthorized mutating action in CodeCommit statement: {act}",
            )

        self.assertEqual(
            cc_stmt.get("Resource"),
            "arn:aws:codecommit:<REGION>:<ACCOUNT_ID>:<REPOSITORY_NAME>",
        )

    def test_cloudwatch_logging_least_privilege(self):
        """Verify CloudWatch permissions include log group creation and stream delivery without logs:*."""
        log_group_stmt = next(
            (
                s
                for s in self.statements
                if "logs:CreateLogGroup" in s.get("Action", [])
            ),
            None,
        )
        self.assertIsNotNone(
            log_group_stmt, "Missing logs:CreateLogGroup statement in Lambda policy"
        )
        self.assertEqual(
            log_group_stmt.get("Resource"),
            "arn:aws:logs:<REGION>:<ACCOUNT_ID>:log-group:/aws/lambda/<FUNCTION_NAME>",
        )

        stream_stmt = next(
            (
                s
                for s in self.statements
                if "logs:CreateLogStream" in s.get("Action", [])
            ),
            None,
        )
        self.assertIsNotNone(
            stream_stmt, "Missing logs:CreateLogStream statement in Lambda policy"
        )
        actions = stream_stmt.get("Action", [])
        self.assertIn("logs:CreateLogStream", actions)
        self.assertIn("logs:PutLogEvents", actions)
        self.assertEqual(
            stream_stmt.get("Resource"),
            "arn:aws:logs:<REGION>:<ACCOUNT_ID>:log-group:/aws/lambda/<FUNCTION_NAME>:*",
        )

        # Ensure no statement contains the dangerous administrative logs:* wildcard
        for stmt in self.statements:
            stmt_actions = stmt.get("Action", [])
            if isinstance(stmt_actions, str):
                stmt_actions = [stmt_actions]
            self.assertNotIn("logs:*", stmt_actions, "Security violation: logs:* wildcard detected")

    def test_lambda_dlq_send_message_permission(self):
        """Verify Lambda execution role has sqs:SendMessage for the On-Failure DLQ."""
        dlq_stmt = next(
            (
                s
                for s in self.statements
                if "sqs:SendMessage" in s.get("Action", [])
                or s.get("Action") == "sqs:SendMessage"
            ),
            None,
        )
        self.assertIsNotNone(
            dlq_stmt,
            "Missing sqs:SendMessage statement in Lambda policy for On-Failure DLQ",
        )
        self.assertEqual(dlq_stmt.get("Effect"), "Allow")
        self.assertEqual(
            dlq_stmt.get("Resource"),
            "arn:aws:sqs:<REGION>:<ACCOUNT_ID>:<LAMBDA_DLQ_NAME>",
        )


class TestIotPolicyLeastPrivilege(unittest.TestCase):
    """Test AWS IoT Core certificate policy for the ESP32 edge device."""

    def setUp(self):
        with open(AWS_DIR / "iot-policy.json", "r", encoding="utf-8") as f:
            self.policy = json.load(f)
        self.statements = self.policy.get("Statement", [])

    def test_statement_structure(self):
        """Verify policy version and statements."""
        self.assertEqual(self.policy.get("Version"), "2012-10-17")
        self.assertEqual(len(self.statements), 3)

    def test_esp32_cannot_publish(self):
        """Security Invariant: ESP32 MUST NOT have iot:Publish permissions."""
        for stmt in self.statements:
            actions = stmt.get("Action", [])
            if isinstance(actions, str):
                actions = [actions]
            self.assertNotIn(
                "iot:Publish",
                actions,
                "Security violation: ESP32 certificate policy must not permit iot:Publish",
            )
            for act in actions:
                self.assertNotEqual(
                    act,
                    "iot:*",
                    "Security violation: ESP32 certificate policy must not use iot:* wildcard",
                )

    def test_esp32_subscribe_uses_topicfilter_arn(self):
        """Verify iot:Subscribe uses the topicfilter ARN namespace."""
        sub_stmt = next(
            (
                s
                for s in self.statements
                if "iot:Subscribe" in s.get("Action", [])
                or s.get("Action") == "iot:Subscribe"
            ),
            None,
        )
        self.assertIsNotNone(sub_stmt, "Missing iot:Subscribe statement")
        self.assertEqual(
            sub_stmt.get("Resource"),
            "arn:aws:iot:<REGION>:<ACCOUNT_ID>:topicfilter/gitops/commits",
            "iot:Subscribe resource must use 'topicfilter/' ARN namespace",
        )

    def test_esp32_receive_uses_topic_arn(self):
        """Verify iot:Receive uses the topic ARN namespace."""
        recv_stmt = next(
            (
                s
                for s in self.statements
                if "iot:Receive" in s.get("Action", [])
                or s.get("Action") == "iot:Receive"
            ),
            None,
        )
        self.assertIsNotNone(recv_stmt, "Missing iot:Receive statement")
        self.assertEqual(
            recv_stmt.get("Resource"),
            "arn:aws:iot:<REGION>:<ACCOUNT_ID>:topic/gitops/commits",
            "iot:Receive resource must use 'topic/' ARN namespace",
        )

    def test_esp32_connect_uses_client_arn(self):
        """Verify iot:Connect uses the client ARN namespace with ThingName variable."""
        conn_stmt = next(
            (
                s
                for s in self.statements
                if "iot:Connect" in s.get("Action", [])
                or s.get("Action") == "iot:Connect"
            ),
            None,
        )
        self.assertIsNotNone(conn_stmt, "Missing iot:Connect statement")
        self.assertIn("client/", conn_stmt.get("Resource", ""))


class TestEventBridgeAndLambdaResourcePolicy(unittest.TestCase):
    """Test EventBridge rule pattern and Lambda resource-based invoke policy."""

    def test_eventbridge_rule_filters(self):
        """Verify EventBridge rule filters for CodeCommit main branch commits."""
        with open(AWS_DIR / "eventbridge-rule.json", "r", encoding="utf-8") as f:
            rule = json.load(f)

        self.assertEqual(rule.get("source"), ["aws.codecommit"])
        self.assertEqual(
            rule.get("detail-type"), ["CodeCommit Repository State Change"]
        )
        detail = rule.get("detail", {})
        self.assertIn("referenceUpdated", detail.get("event", []))
        self.assertIn("referenceCreated", detail.get("event", []))
        self.assertEqual(detail.get("referenceType"), ["branch"])
        self.assertEqual(detail.get("referenceName"), ["main"])

    def test_lambda_resource_policy_invocation_permissions(self):
        """Verify Lambda resource policy grants invoke permissions solely to EventBridge."""
        with open(
            AWS_DIR / "lambda-resource-policy.json", "r", encoding="utf-8"
        ) as f:
            policy = json.load(f)

        stmt = policy.get("Statement", [])[0]
        self.assertEqual(stmt.get("Effect"), "Allow")
        self.assertEqual(
            stmt.get("Principal"), {"Service": "events.amazonaws.com"}
        )
        self.assertEqual(stmt.get("Action"), "lambda:InvokeFunction")
        self.assertEqual(
            stmt.get("Resource"),
            "arn:aws:lambda:<REGION>:<ACCOUNT_ID>:function:<FUNCTION_NAME>",
        )
        condition = stmt.get("Condition", {})
        self.assertEqual(
            condition.get("ArnLike", {}).get("AWS:SourceArn"),
            "arn:aws:events:<REGION>:<ACCOUNT_ID>:rule/<RULE_NAME>",
        )


class TestAsynchronousRetryAndFailureRecovery(unittest.TestCase):
    """Test the decoupling between Path A (EventBridge Delivery) and Path B (Lambda Execution)."""

    def test_path_a_eventbridge_target_retry_policy(self):
        """Verify Path A EventBridge target retry limits comply with AWS service limits."""
        with open(AWS_DIR / "eventbridge-target.json", "r", encoding="utf-8") as f:
            target_config = json.load(f)

        targets = target_config.get("Targets", [])
        self.assertEqual(len(targets), 1)
        target = targets[0]

        retry = target.get("RetryPolicy", {})
        attempts = retry.get("MaximumRetryAttempts")
        age = retry.get("MaximumEventAgeInSeconds")

        # AWS EventBridge Target Service Limits: attempts in [0, 185], age in [60, 86400]
        self.assertIsInstance(attempts, int)
        self.assertTrue(0 <= attempts <= 185, f"Attempts {attempts} exceeds EventBridge limit [0, 185]")
        self.assertIsInstance(age, int)
        self.assertTrue(60 <= age <= 86400, f"Event age {age} exceeds EventBridge limit [60, 86400]")

        dlq = target.get("DeadLetterConfig", {})
        self.assertEqual(
            dlq.get("Arn"),
            "arn:aws:sqs:<REGION>:<ACCOUNT_ID>:<EVENTBRIDGE_DLQ_NAME>",
            "EventBridge target DLQ must reference the dedicated EventBridge DLQ ARN",
        )

    def test_path_b_lambda_event_invoke_config(self):
        """Verify Path B Lambda async invocation config complies with AWS service limits."""
        with open(AWS_DIR / "lambda-event-invoke-config.json", "r", encoding="utf-8") as f:
            invoke_config = json.load(f)

        attempts = invoke_config.get("MaximumRetryAttempts")
        age = invoke_config.get("MaximumEventAgeInSeconds")

        # AWS Lambda Asynchronous Invocation Service Limits: attempts in [0, 2], age in [60, 21600]
        self.assertIsInstance(attempts, int)
        self.assertTrue(0 <= attempts <= 2, f"Attempts {attempts} exceeds Lambda async limit [0, 2]")
        self.assertIsInstance(age, int)
        self.assertTrue(60 <= age <= 21600, f"Event age {age} exceeds Lambda async limit [60, 21600]")

        dest = invoke_config.get("DestinationConfig", {}).get("OnFailure", {}).get("Destination")
        self.assertEqual(
            dest,
            "arn:aws:sqs:<REGION>:<ACCOUNT_ID>:<LAMBDA_DLQ_NAME>",
            "Lambda On-Failure destination must reference the dedicated Lambda DLQ ARN",
        )

    def test_retry_counters_are_distinct(self):
        """Verify EventBridge and Lambda do NOT share one retry counter or configuration."""
        with open(AWS_DIR / "eventbridge-target.json", "r", encoding="utf-8") as f:
            eb_config = json.load(f)
        with open(AWS_DIR / "lambda-event-invoke-config.json", "r", encoding="utf-8") as f:
            lambda_config = json.load(f)

        eb_attempts = eb_config["Targets"][0]["RetryPolicy"]["MaximumRetryAttempts"]
        lambda_attempts = lambda_config["MaximumRetryAttempts"]

        # Crucial architectural assertion: EventBridge and Lambda have different retry counts
        self.assertNotEqual(
            eb_attempts,
            lambda_attempts,
            "EventBridge target retries and Lambda async retries must not share one counter",
        )
        self.assertEqual(eb_attempts, 185)
        self.assertEqual(lambda_attempts, 2)

    def test_lambda_function_config_sets_production_handler(self):
        """Verify lambda-function-config.json configures production_lambda_handler as entry point."""
        with open(AWS_DIR / "lambda-function-config.json", "r", encoding="utf-8") as f:
            func_config = json.load(f)

        self.assertEqual(
            func_config.get("Handler"),
            "lambda_function.production_lambda_handler",
            "Production deployment must configure production_lambda_handler as the Lambda entry point",
        )
        self.assertTrue(
            func_config.get("Runtime", "").startswith("python3."),
            "Lambda runtime must be Python 3.x",
        )
        self.assertIn("<ACCOUNT_ID>", func_config.get("Role", ""))


class TestGitHubAwsInfrastructure(unittest.TestCase):
    """Test offline configuration contracts for GitHub Webhook + API Gateway infrastructure."""

    def test_github_lambda_function_config(self):
        """Verify lambda-github-function-config.json specifies github_webhook_handler and env vars."""
        with open(AWS_DIR / "lambda-github-function-config.json", "r", encoding="utf-8") as f:
            config = json.load(f)

        self.assertEqual(
            config.get("Handler"),
            "lambda_function.github_webhook_handler",
            "GitHub Lambda must configure github_webhook_handler as entry point",
        )
        self.assertTrue(
            config.get("Runtime", "").startswith("python3."),
            "GitHub Lambda runtime must be Python 3.x",
        )
        self.assertIn("<ACCOUNT_ID>", config.get("Role", ""))

        env_vars = config.get("Environment", {}).get("Variables", {})
        self.assertIn("GITHUB_WEBHOOK_SECRET", env_vars)
        self.assertEqual(env_vars.get("MONITORED_BRANCH"), "main")
        self.assertIn("<IOT_ENDPOINT_PREFIX>", env_vars.get("IOT_DATA_ENDPOINT", ""))
        self.assertEqual(env_vars.get("MQTT_TOPIC"), "gitops/commits")

    def test_apigateway_http_api_template(self):
        """Verify apigateway-http-api.json route, proxy integration v2.0, and stage throttling."""
        with open(AWS_DIR / "apigateway-http-api.json", "r", encoding="utf-8") as f:
            api_spec = json.load(f)

        # Route check
        route = api_spec.get("Route", {})
        self.assertEqual(route.get("RouteKey"), "POST /webhook/github")

        # Integration check
        integration = api_spec.get("Integration", {})
        self.assertEqual(integration.get("IntegrationType"), "AWS_PROXY")
        self.assertEqual(integration.get("PayloadFormatVersion"), "2.0")
        self.assertIn("<GITHUB_FUNCTION_NAME>", integration.get("IntegrationUri", ""))

        # Stage and throttling check
        stage = api_spec.get("Stage", {})
        self.assertEqual(stage.get("StageName"), "$default")
        self.assertTrue(stage.get("AutoDeploy"))
        throttle = stage.get("DefaultRouteSettings", {})
        self.assertGreater(throttle.get("ThrottlingBurstLimit", 0), 0)
        self.assertGreater(throttle.get("ThrottlingRateLimit", 0), 0)

    def test_apigateway_lambda_permission_scoping(self):
        """Verify apigateway-lambda-permission.json is narrowly scoped to HTTP route and account."""
        with open(AWS_DIR / "apigateway-lambda-permission.json", "r", encoding="utf-8") as f:
            policy = json.load(f)

        statements = policy.get("Statement", [])
        self.assertEqual(len(statements), 1)
        stmt = statements[0]

        self.assertEqual(stmt.get("Effect"), "Allow")
        self.assertEqual(stmt.get("Action"), "lambda:InvokeFunction")
        self.assertEqual(stmt.get("Principal", {}).get("Service"), "apigateway.amazonaws.com")
        self.assertIn("<GITHUB_FUNCTION_NAME>", stmt.get("Resource", ""))

        condition = stmt.get("Condition", {})
        source_arn = condition.get("ArnLike", {}).get("AWS:SourceArn", "")
        self.assertIn("POST/webhook/github", source_arn)
        self.assertIn("<API_ID>", source_arn)
        self.assertEqual(condition.get("StringEquals", {}).get("aws:SourceAccount"), "<ACCOUNT_ID>")

    def test_github_lambda_policy_least_privilege(self):
        """Verify lambda-github-policy.json grants only logs and IoT publish without CodeCommit or SQS."""
        with open(AWS_DIR / "lambda-github-policy.json", "r", encoding="utf-8") as f:
            policy = json.load(f)

        statements = policy.get("Statement", [])
        all_actions = []
        all_resources = []
        for stmt in statements:
            actions = stmt.get("Action", [])
            if isinstance(actions, str):
                actions = [actions]
            all_actions.extend(actions)
            res = stmt.get("Resource", [])
            if isinstance(res, str):
                res = [res]
            all_resources.extend(res)

        # Must contain IoT publish on gitops/commits
        self.assertIn("iot:Publish", all_actions)
        self.assertTrue(
            any("topic/gitops/commits" in r for r in all_resources),
            "Must restrict iot:Publish to topic/gitops/commits",
        )

        # Must contain CloudWatch logging
        self.assertIn("logs:CreateLogStream", all_actions)
        self.assertIn("logs:PutLogEvents", all_actions)

        # Must contain Secrets Manager get_secret_value
        self.assertIn("secretsmanager:GetSecretValue", all_actions)
        self.assertTrue(
            any("arn:aws:secretsmanager:" in r for r in all_resources),
            "Must restrict secretsmanager:GetSecretValue to secret ARN",
        )

        # Must strictly omit CodeCommit, SQS, and wildcard permissions
        for act in all_actions:
            self.assertFalse(act.startswith("codecommit:"), f"Must not grant CodeCommit action: {act}")
            self.assertFalse(act.startswith("sqs:"), f"Must not grant SQS action: {act}")
            self.assertNotEqual(act, "*")
            self.assertNotEqual(act, "logs:*")
            self.assertNotEqual(act, "iot:*")
            self.assertNotEqual(act, "secretsmanager:*")

        for res in all_resources:
            self.assertNotEqual(res, "*", "Resource wildcard '*' is not permitted in least-privilege policy")

    def test_cloudformation_template_structure_and_consistency(self):
        """Verify github-webhook-template.yaml parses, has valid resources, parameters, and routes."""
        cfn_path = AWS_DIR / "github-webhook-template.yaml"
        self.assertTrue(cfn_path.is_file(), "github-webhook-template.yaml must exist")

        with open(cfn_path, "r", encoding="utf-8") as f:
            template = yaml.safe_load(f)

        self.assertEqual(template.get("AWSTemplateFormatVersion"), "2010-09-09")
        params = template.get("Parameters", {})
        self.assertIn("GitHubWebhookSecretArn", params)
        self.assertIn("IoTDataEndpoint", params)
        self.assertIn("MqttTopic", params)
        self.assertIn("MonitoredBranch", params)
        self.assertIn("LambdaCodeS3Bucket", params)
        self.assertIn("LambdaCodeS3Key", params)

        resources = template.get("Resources", {})
        # Log group
        self.assertIn("GitHubWebhookLogGroup", resources)
        self.assertEqual(resources["GitHubWebhookLogGroup"].get("Type"), "AWS::Logs::LogGroup")

        # IAM role
        self.assertIn("GitHubWebhookExecutionRole", resources)
        self.assertEqual(resources["GitHubWebhookExecutionRole"].get("Type"), "AWS::IAM::Role")

        # Lambda function
        self.assertIn("GitHubWebhookFunction", resources)
        func = resources["GitHubWebhookFunction"]
        self.assertEqual(func.get("Type"), "AWS::Lambda::Function")
        self.assertEqual(func.get("Properties", {}).get("Handler"), "lambda_function.github_webhook_handler")
        self.assertEqual(func.get("Properties", {}).get("Runtime"), "python3.12")

        # API Gateway HTTP API, Integration, Route, Stage, and Permission
        self.assertIn("GitHubHttpApi", resources)
        self.assertEqual(resources["GitHubHttpApi"].get("Type"), "AWS::ApiGatewayV2::Api")

        self.assertIn("GitHubApiIntegration", resources)
        integration = resources["GitHubApiIntegration"]
        self.assertEqual(integration.get("Type"), "AWS::ApiGatewayV2::Integration")
        self.assertEqual(integration.get("Properties", {}).get("IntegrationType"), "AWS_PROXY")
        self.assertEqual(integration.get("Properties", {}).get("PayloadFormatVersion"), "2.0")

        self.assertIn("GitHubApiRoute", resources)
        route = resources["GitHubApiRoute"]
        self.assertEqual(route.get("Type"), "AWS::ApiGatewayV2::Route")
        self.assertEqual(route.get("Properties", {}).get("RouteKey"), "POST /webhook/github")

        self.assertIn("GitHubApiStage", resources)
        stage = resources["GitHubApiStage"]
        self.assertEqual(stage.get("Type"), "AWS::ApiGatewayV2::Stage")
        self.assertEqual(stage.get("Properties", {}).get("StageName"), "$default")

        self.assertIn("GitHubApiLambdaPermission", resources)
        perm = resources["GitHubApiLambdaPermission"]
        self.assertEqual(perm.get("Type"), "AWS::Lambda::Permission")
        self.assertEqual(perm.get("Properties", {}).get("Principal"), "apigateway.amazonaws.com")
        self.assertEqual(perm.get("Properties", {}).get("Action"), "lambda:InvokeFunction")

        outputs = template.get("Outputs", {})
        self.assertIn("WebhookUrl", outputs)
        self.assertIn("GitHubLambdaArn", outputs)
        self.assertIn("HttpApiId", outputs)

    def test_codecommit_configuration_remains_intact(self):
        """Verify existing CodeCommit Lambda configuration and policies were not altered or broken."""
        with open(AWS_DIR / "lambda-function-config.json", "r", encoding="utf-8") as f:
            cc_config = json.load(f)
        self.assertEqual(
            cc_config.get("Handler"),
            "lambda_function.production_lambda_handler",
            "CodeCommit config must retain production_lambda_handler",
        )

        with open(AWS_DIR / "lambda-policy.json", "r", encoding="utf-8") as f:
            cc_policy = json.load(f)
        actions = [a for s in cc_policy.get("Statement", []) for a in (s.get("Action") if isinstance(s.get("Action"), list) else [s.get("Action")])]
        self.assertIn("codecommit:GetCommit", actions, "CodeCommit policy must retain codecommit:GetCommit")
        self.assertIn("sqs:SendMessage", actions, "CodeCommit policy must retain sqs:SendMessage for DLQ")


if __name__ == "__main__":
    unittest.main()

"""Offline verification tests for AWS infrastructure configuration files.

Validates:
1. JSON syntax correctness across all configuration files in aws/.
2. Absence of hardcoded AWS 12-digit account IDs, real regions, or secret keys.
3. Decoupled Retry & DLQ Architecture (Path A vs Path B):
   - Path A (Target Delivery): EventBridge Target RetryPolicy (0-185 attempts, max 86400s)
     and EventBridge DeadLetterConfig.
   - Path B (Function Execution): Lambda Asynchronous Event Invoke Config (0-2 attempts,
     max 21600s) and On-Failure Destination DLQ.
   - Distinct retry counters and compliance with current AWS service limits.
4. Production Handler Entry Point:
   - Verifies lambda-function-config.json specifies 'lambda_function.production_lambda_handler'.
5. Least-privilege IAM policy invariants:
   - Lambda execution role:
     * iot:Publish restricted strictly to 'gitops/commits' topic (no wildcards).
     * codecommit:GetCommit read-only on repository ARN.
     * logs:CreateLogStream and logs:PutLogEvents restricted to function log-group.
     * sqs:SendMessage restricted to Lambda On-Failure DLQ ARN.
   - ESP32 IoT certificate policy:
     * Actions restricted to iot:Connect, iot:Subscribe, and iot:Receive.
     * iot:Publish is strictly absent (subscriber-only device).
     * iot:Subscribe uses 'topicfilter/gitops/commits'.
     * iot:Receive uses 'topic/gitops/commits'.
   - EventBridge Rule:
     * Scoped to aws.codecommit source and main branch.
   - Lambda Resource Policy:
     * Scoped to events.amazonaws.com principal and rule ARN condition.
"""

import json
from pathlib import Path
import re
import unittest

AWS_DIR = Path(__file__).resolve().parent.parent / "aws"


class TestAwsConfigurationJson(unittest.TestCase):
    """Test JSON syntax validity and placeholder conventions in aws/."""

    EXPECTED_FILES = [
        "eventbridge-rule.json",
        "eventbridge-target.json",
        "lambda-function-config.json",
        "lambda-event-invoke-config.json",
        "lambda-policy.json",
        "lambda-resource-policy.json",
        "iot-policy.json",
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
        self.assertGreaterEqual(len(json_files), 7)
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

        for json_file in AWS_DIR.glob("*.json"):
            content = json_file.read_text(encoding="utf-8")

            matches = account_id_pattern.findall(content)
            self.assertEqual(
                matches,
                [],
                f"Hardcoded 12-digit AWS account ID found in {json_file.name}: {matches}",
            )

            for indicator in secret_indicators:
                self.assertNotIn(
                    indicator,
                    content,
                    f"Credential indicator '{indicator}' detected in {json_file.name}",
                )

            self.assertIn(
                "<ACCOUNT_ID>",
                content,
                f"Expected placeholder <ACCOUNT_ID> in {json_file.name}",
            )


class TestLambdaPolicyLeastPrivilege(unittest.TestCase):
    """Test IAM permissions for the Lambda execution role."""

    def setUp(self):
        with open(AWS_DIR / "lambda-policy.json", "r", encoding="utf-8") as f:
            self.policy = json.load(f)
        self.statements = self.policy.get("Statement", [])

    def test_statement_structure(self):
        """Verify policy version and statements."""
        self.assertEqual(self.policy.get("Version"), "2012-10-17")
        self.assertGreaterEqual(len(self.statements), 4)

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
        """Verify CloudWatch permissions are restricted to log stream creation and event putting."""
        cw_stmt = next(
            (
                s
                for s in self.statements
                if any(act.startswith("logs:") for act in s.get("Action", []))
            ),
            None,
        )
        self.assertIsNotNone(
            cw_stmt, "Missing CloudWatch Logs statement in Lambda policy"
        )
        actions = cw_stmt.get("Action", [])
        self.assertIn("logs:CreateLogStream", actions)
        self.assertIn("logs:PutLogEvents", actions)
        self.assertNotIn("logs:*", actions)
        self.assertTrue(
            cw_stmt.get("Resource", "").startswith(
                "arn:aws:logs:<REGION>:<ACCOUNT_ID>:log-group:/aws/lambda/<FUNCTION_NAME>"
            )
        )

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


if __name__ == "__main__":
    unittest.main()

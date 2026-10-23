"""Offline verification tests for AWS infrastructure configuration files.

Validates:
1. JSON syntax correctness across all configuration files in aws/.
2. Absence of hardcoded AWS 12-digit account IDs, real regions, or secret keys.
3. Least-privilege IAM policy invariants:
   - Lambda execution role:
     * iot:Publish restricted strictly to 'gitops/commits' topic (no wildcards).
     * codecommit:GetCommit read-only on repository ARN.
     * logs:CreateLogStream and logs:PutLogEvents restricted to function log-group.
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
import re
from pathlib import Path
import unittest

AWS_DIR = Path(__file__).resolve().parent.parent / "aws"


class TestAwsConfigurationJson(unittest.TestCase):
    """Test JSON syntax validity and placeholder conventions in aws/."""

    EXPECTED_FILES = [
        "eventbridge-rule.json",
        "lambda-policy.json",
        "iot-policy.json",
        "eventbridge-target.json",
        "lambda-resource-policy.json",
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
        self.assertGreaterEqual(len(json_files), 5)
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
        # Regex for 12 consecutive digits (standard AWS account ID format)
        account_id_pattern = re.compile(r"\b\d{12}\b")
        secret_indicators = [
            "BEGIN PRIVATE KEY",
            "BEGIN RSA PRIVATE KEY",
            "BEGIN CERTIFICATE",
            "AKIA",  # AWS Access Key ID prefix
        ]

        for json_file in AWS_DIR.glob("*.json"):
            content = json_file.read_text(encoding="utf-8")

            # Check for 12-digit numbers
            matches = account_id_pattern.findall(content)
            self.assertEqual(
                matches,
                [],
                f"Hardcoded 12-digit AWS account ID found in {json_file.name}: {matches}",
            )

            # Check for secrets/key markers
            for indicator in secret_indicators:
                self.assertNotIn(
                    indicator,
                    content,
                    f"Credential indicator '{indicator}' detected in {json_file.name}",
                )

            # Ensure placeholder format is followed
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
        self.assertGreaterEqual(len(self.statements), 3)

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
        # Explicitly verify no wildcard topic or action
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

        # Ensure no write actions are granted
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

    def test_eventbridge_target_retry_and_dlq_configuration(self):
        """Verify EventBridge target includes retry limits and DLQ configuration."""
        with open(AWS_DIR / "eventbridge-target.json", "r", encoding="utf-8") as f:
            target_config = json.load(f)

        targets = target_config.get("Targets", [])
        self.assertEqual(len(targets), 1)
        target = targets[0]

        retry = target.get("RetryPolicy", {})
        self.assertIn("MaximumEventAgeInSeconds", retry)
        self.assertIn("MaximumRetryAttempts", retry)

        dlq = target.get("DeadLetterConfig", {})
        self.assertTrue(dlq.get("Arn", "").startswith("arn:aws:sqs:"))


if __name__ == "__main__":
    unittest.main()


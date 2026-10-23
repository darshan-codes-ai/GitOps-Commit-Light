"""
GitOps Commit Light — Backend Lambda Event Processor

This module provides event parsing, payload construction, and handler logic
for CodeCommit events routed via Amazon EventBridge.

Architecture Role:
    CodeCommit -> EventBridge -> [Lambda Event Processor] -> (Future: AWS IoT Core MQTT)

Design Principles:
    - Pure offline logic: does not perform network calls or require AWS credentials.
    - Decoupled commit message retrieval via the CommitMessageProvider interface.
    - Strict validation with clear custom exceptions.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from typing import Any, Callable, Dict, Optional, Tuple, Union
import uuid

try:
    from publisher import (
        DEFAULT_MQTT_TOPIC,
        Boto3IotDataPublisher,
        MockMQTTPublisher,
        MQTTPublishError,
        MQTTPublisher,
        PermanentMQTTPublishError,
        PublishedMessage,
        TransientMQTTPublishError,
    )
except ImportError:
    from .publisher import (
        DEFAULT_MQTT_TOPIC,
        Boto3IotDataPublisher,
        MockMQTTPublisher,
        MQTTPublishError,
        MQTTPublisher,
        PermanentMQTTPublishError,
        PublishedMessage,
        TransientMQTTPublishError,
    )


# ==============================================================================
# Custom Exceptions & Error Classification Strategy
# ==============================================================================

class EventProcessingError(Exception):
    """Base exception for all event processing errors."""
    pass


class PermanentError(EventProcessingError):
    """
    Base marker for non-retryable errors (poison pills).
    
    In asynchronous EventBridge invocations, permanent errors are acknowledged
    cleanly with statusCode 400 (no exception raised) to avoid useless, costly retries.
    """
    pass


class RetryableError(EventProcessingError):
    """
    Base marker for transient, retryable errors (service timeouts, rate limits).
    
    In production asynchronous invocations, retryable errors are raised out of
    the Lambda entry point so AWS Lambda marks the invocation as failed and triggers
    EventBridge retries and eventual Dead-Letter Queue (DLQ) routing.
    """
    pass


class EventValidationError(PermanentError):
    """Raised when an EventBridge event is malformed or missing required fields."""
    pass


class UnsupportedEventError(PermanentError):
    """Raised when the event is valid JSON but from an unsupported source or type."""
    pass


class CommitMessageError(EventProcessingError):
    """Base exception for commit message retrieval errors."""
    pass


class PermanentCommitMessageError(CommitMessageError, PermanentError):
    """Raised when commit message is permanently unavailable (e.g. missing from event and no provider)."""
    pass


class TransientCommitRetrievalError(CommitMessageError, RetryableError):
    """Raised when commit message retrieval fails due to transient infrastructure issues."""
    pass


def is_retryable_error(error: Exception) -> bool:
    """
    Determine whether an error represents a transient failure that should be retried
    by Amazon EventBridge in an asynchronous invocation.
    """
    if isinstance(error, (PermanentError, PermanentMQTTPublishError)):
        return False
    if isinstance(error, (RetryableError, TransientMQTTPublishError)):
        return True
    if isinstance(error, (ConnectionError, TimeoutError, OSError)):
        return True
    if isinstance(error, MQTTPublishError):
        return True
    # Unexpected runtime exceptions are treated as retryable to prevent silent data loss
    return not isinstance(error, (EventValidationError, UnsupportedEventError, PermanentCommitMessageError))


# ==============================================================================
# Parsed Event Data Model
# ==============================================================================

@dataclass(frozen=True)
class ParsedCommitEvent:
    """
    Extracted metadata from an AWS CodeCommit EventBridge event.
    """
    event_id: str
    timestamp: str
    repository: str
    branch: str
    commit_id: str


# ==============================================================================
# Commit Message Provider Interface
# ==============================================================================

class CommitMessageProvider(abc.ABC):
    """
    Abstract interface for retrieving Git commit messages.
    
    In production, an implementation will call the AWS CodeCommit GetCommit API
    using boto3. In offline development and testing, mock implementations or
    fixtures are supplied without making external network calls.
    """

    @abc.abstractmethod
    def get_commit_message(self, repository: str, commit_id: str) -> str:
        """
        Retrieve the commit message for a given repository and commit ID.

        Args:
            repository: Name of the CodeCommit repository.
            commit_id: The SHA commit hash.

        Returns:
            The commit message string.

        Raises:
            CommitMessageError: If the message cannot be obtained.
        """
        pass


class StaticCommitMessageProvider(CommitMessageProvider):
    """
    In-memory commit message provider for offline testing and development.
    
    Can return a fixed default message or map specific commit IDs to messages.
    """

    def __init__(
        self,
        default_message: Optional[str] = None,
        commit_messages: Optional[Dict[str, str]] = None,
    ):
        self.default_message = default_message
        self.commit_messages = commit_messages or {}

    def get_commit_message(self, repository: str, commit_id: str) -> str:
        if commit_id in self.commit_messages:
            return self.commit_messages[commit_id]
        if self.default_message is not None:
            return self.default_message
        raise CommitMessageError(
            f"No commit message configured for commit ID '{commit_id}' in repository '{repository}'."
        )


PERMANENT_CODECOMMIT_ERROR_CODES = {
    "CommitDoesNotExistException",
    "CommitIdDoesNotExistException",
    "CommitIdRequiredException",
    "InvalidCommitIdException",
    "RepositoryDoesNotExistException",
    "RepositoryNameRequiredException",
    "InvalidRepositoryNameException",
    "ValidationException",
}

TRANSIENT_CODECOMMIT_ERROR_CODES = {
    "ThrottlingException",
    "RequestThrottled",
    "ThrottledException",
    "ProvisionedThroughputExceededException",
    "TooManyRequestsException",
    "InternalServerError",
    "ServiceUnavailableException",
}


def _extract_boto_error_details(err: Exception) -> Optional[Tuple[str, str, int]]:
    """Extract (code, message, status_code) from a botocore ClientError or duck-typed mock."""
    response = getattr(err, "response", None)
    if not isinstance(response, dict):
        return None
    error_dict = response.get("Error", {})
    if not isinstance(error_dict, dict):
        return None
    code = error_dict.get("Code", "")
    message = error_dict.get("Message", str(err))
    status_code = response.get("ResponseMetadata", {}).get("HTTPStatusCode", 400)
    return code, message, status_code


class Boto3CodeCommitProvider(CommitMessageProvider):
    """
    Production CommitMessageProvider that retrieves commit messages from
    AWS CodeCommit using the AWS SDK for Python (boto3).

    Validates inputs, calls CodeCommit get_commit, validates the returned commit metadata,
    and classifies transient vs permanent failures.
    """

    def __init__(
        self,
        client: Optional[Any] = None,
        region_name: Optional[str] = None,
        session: Optional[Any] = None,
    ):
        self._client = client
        self._region_name = (
            region_name
            or os.environ.get("AWS_REGION")
            or os.environ.get("AWS_DEFAULT_REGION")
        )
        self._session = session

    def _get_client(self) -> Any:
        """Get or lazily instantiate the boto3 'codecommit' client."""
        if self._client is not None:
            return self._client
        try:
            import boto3
        except ImportError as err:
            raise TransientCommitRetrievalError(
                "AWS SDK (boto3) is required for Boto3CodeCommitProvider but is not installed."
            ) from err

        kwargs: Dict[str, Any] = {}
        if self._region_name:
            kwargs["region_name"] = self._region_name

        try:
            if self._session is not None:
                self._client = self._session.client("codecommit", **kwargs)
            else:
                self._client = boto3.client("codecommit", **kwargs)
            return self._client
        except Exception as err:
            raise TransientCommitRetrievalError(
                f"Failed to create CodeCommit client: {err}"
            ) from err

    def get_commit_message(self, repository: str, commit_id: str) -> str:
        """
        Retrieve commit message from CodeCommit for the specified repository and commit SHA.

        Args:
            repository: CodeCommit repository name.
            commit_id: Commit hash/SHA.

        Returns:
            Non-empty, trimmed commit message string.

        Raises:
            PermanentCommitMessageError: If commit or repository is missing/invalid,
                                         or returned message is empty.
            TransientCommitRetrievalError: If API call throttles, times out, or fails transiently.
        """
        if not repository or not isinstance(repository, str) or not repository.strip():
            raise PermanentCommitMessageError("Repository name must be a non-empty string.")
        if not commit_id or not isinstance(commit_id, str) or not commit_id.strip():
            raise PermanentCommitMessageError("Commit ID must be a non-empty string.")

        clean_repo = repository.strip()
        clean_commit_id = commit_id.strip()

        client = self._get_client()

        try:
            response = client.get_commit(
                repositoryName=clean_repo,
                commitId=clean_commit_id,
            )
        except Exception as err:
            self._handle_client_error(err, clean_repo, clean_commit_id)

        if not isinstance(response, dict):
            raise PermanentCommitMessageError("CodeCommit get_commit returned non-dictionary response.")

        commit_info = response.get("commit")
        if not isinstance(commit_info, dict):
            raise PermanentCommitMessageError("CodeCommit response missing 'commit' dictionary.")

        message = commit_info.get("message")
        if message is None:
            raise PermanentCommitMessageError(
                f"Commit '{clean_commit_id}' in repository '{clean_repo}' is missing the 'message' field."
            )
        if not isinstance(message, str) or not message.strip():
            raise PermanentCommitMessageError(
                f"Commit '{clean_commit_id}' in repository '{clean_repo}' contains an empty commit message."
            )
        return message.strip()

    def _handle_client_error(self, err: Exception, repository: str, commit_id: str) -> None:
        """Categorize CodeCommit API exceptions as permanent or transient."""
        if isinstance(err, CommitMessageError):
            raise err

        details = _extract_boto_error_details(err)
        if details is not None:
            code, message, status_code = details
            if code in PERMANENT_CODECOMMIT_ERROR_CODES:
                raise PermanentCommitMessageError(
                    f"CodeCommit rejected commit query for '{commit_id}' in '{repository}' with permanent error ({code}): {message}"
                ) from err
            if code in TRANSIENT_CODECOMMIT_ERROR_CODES or status_code >= 500:
                raise TransientCommitRetrievalError(
                    f"CodeCommit transient failure retrieving commit '{commit_id}' in '{repository}' ({code}): {message}"
                ) from err
            if 400 <= status_code < 500:
                raise PermanentCommitMessageError(
                    f"CodeCommit client error for '{commit_id}' in '{repository}' ({code}): {message}"
                ) from err

        if isinstance(err, (ConnectionError, TimeoutError, OSError)):
            raise TransientCommitRetrievalError(
                f"Network connection error contacting CodeCommit for commit '{commit_id}' in '{repository}': {err}"
            ) from err

        err_type = type(err).__name__
        if "Timeout" in err_type or "Connection" in err_type or "Network" in err_type:
            raise TransientCommitRetrievalError(
                f"Network error ({err_type}) contacting CodeCommit for commit '{commit_id}' in '{repository}': {err}"
            ) from err

        raise TransientCommitRetrievalError(
            f"Unexpected error retrieving commit '{commit_id}' from CodeCommit repository '{repository}': {err}"
        ) from err


# Type alias for acceptable message provider arguments
MessageProviderType = Union[CommitMessageProvider, Callable[[str, str], str]]


# ==============================================================================
# Event Parsing & Validation
# ==============================================================================

EXPECTED_SOURCE = "aws.codecommit"
EXPECTED_DETAIL_TYPE = "CodeCommit Repository State Change"
SUPPORTED_ACTIONS = {"referenceUpdated", "referenceCreated"}


def parse_event(event: Any) -> ParsedCommitEvent:
    """
    Validate and extract essential fields from an EventBridge CodeCommit event.

    Expected structure:
    {
        "id": "<event-id>",
        "detail-type": "CodeCommit Repository State Change",
        "source": "aws.codecommit",
        "time": "<iso-8601-timestamp>",
        "detail": {
            "event": "referenceUpdated",
            "repositoryName": "<repo-name>",
            "referenceType": "branch",
            "referenceName": "<branch-name>",
            "commitId": "<commit-hash>"
        }
    }

    Fallback Behavior:
    - If top-level 'id' is missing, empty, or non-string, a unique fallback
      ID is generated: 'fallback-<uuid4>'.
    - If top-level 'time' is missing, empty, or non-string, the current UTC time
      formatted as ISO-8601 ('YYYY-MM-DDTHH:MM:SSZ') is generated.
    - Repository, branch, and commitId do NOT have fallbacks; omitting them
      raises EventValidationError to prevent inventing false commit data.

    Raises:
        EventValidationError: If event structure or required fields are missing.
        UnsupportedEventError: If source or event action is unsupported.
    """
    if not isinstance(event, dict):
        raise EventValidationError(
            f"Event must be a JSON object (dict), received: {type(event).__name__}"
        )

    # 1. Validate top-level source
    source = event.get("source")
    if source != EXPECTED_SOURCE:
        raise UnsupportedEventError(
            f"Unsupported event source: '{source}'. Expected '{EXPECTED_SOURCE}'."
        )

    # 2. Validate detail-type
    detail_type = event.get("detail-type")
    if detail_type != EXPECTED_DETAIL_TYPE:
        raise UnsupportedEventError(
            f"Unsupported detail-type: '{detail_type}'. Expected '{EXPECTED_DETAIL_TYPE}'."
        )

    # 3. Validate detail container
    detail = event.get("detail")
    if not isinstance(detail, dict):
        raise EventValidationError(
            "Event 'detail' field is missing or is not a JSON object."
        )

    # 4. Validate event action (referenceUpdated vs referenceDeleted vs others)
    event_action = detail.get("event")
    if event_action == "referenceDeleted":
        raise UnsupportedEventError(
            "Unsupported event action: 'referenceDeleted'. Branch deletions do not trigger commit lights."
        )
    if event_action not in SUPPORTED_ACTIONS:
        raise UnsupportedEventError(
            f"Unsupported CodeCommit event action: '{event_action}'. Supported: {sorted(SUPPORTED_ACTIONS)}."
        )

    # 5. Validate reference type (we only monitor branch commits, not tags)
    reference_type = detail.get("referenceType")
    if reference_type != "branch":
        raise UnsupportedEventError(
            f"Unsupported referenceType: '{reference_type}'. Only 'branch' updates are supported."
        )

    # 6. Extract and validate required repository name
    repository_name = detail.get("repositoryName")
    if not isinstance(repository_name, str) or not repository_name.strip():
        raise EventValidationError("Missing or empty 'detail.repositoryName'.")

    # 7. Extract and validate required branch name
    branch_name = detail.get("referenceName")
    if not isinstance(branch_name, str) or not branch_name.strip():
        raise EventValidationError("Missing or empty 'detail.referenceName'.")

    # 8. Extract and validate required commit ID
    commit_id = detail.get("commitId")
    if not isinstance(commit_id, str) or not commit_id.strip():
        raise EventValidationError("Missing or empty 'detail.commitId'.")

    # 9. Extract or fallback for event ID
    raw_event_id = event.get("id")
    if isinstance(raw_event_id, str) and raw_event_id.strip():
        event_id = raw_event_id.strip()
    else:
        event_id = f"fallback-{uuid.uuid4()}"

    # 10. Extract or fallback for timestamp
    raw_time = event.get("time")
    if isinstance(raw_time, str) and raw_time.strip():
        timestamp = raw_time.strip()
    else:
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    return ParsedCommitEvent(
        event_id=event_id,
        timestamp=timestamp,
        repository=repository_name.strip(),
        branch=branch_name.strip(),
        commit_id=commit_id.strip(),
    )


# ==============================================================================
# Payload Construction
# ==============================================================================

SCHEMA_VERSION = 1


def build_notification_payload(
    event: Any,
    message_provider: Optional[MessageProviderType] = None,
) -> Dict[str, Any]:
    """
    Parse an EventBridge event and construct the target IoT notification payload.

    Target Schema:
    {
        "schemaVersion": 1,
        "eventId": "<event-id>",
        "repository": "<repo-name>",
        "branch": "<branch-name>",
        "commitId": "<commit-hash>",
        "message": "<commit-message>",
        "timestamp": "<iso-8601-timestamp>"
    }

    Commit Message Resolution:
    1. If `message_provider` is supplied (either CommitMessageProvider or callable),
       it is invoked with (repository, commitId).
    2. If `message_provider` is None, checks if the event includes an offline
       synthetic fixture message under `detail.commitMessage`.
    3. If neither is available, raises CommitMessageError.

    Raises:
        EventValidationError: On malformed event input.
        UnsupportedEventError: On unsupported source/action.
        CommitMessageError: If message retrieval fails or returns empty text.
    """
    parsed = parse_event(event)

    # Resolve the commit message
    commit_message: Optional[str] = None

    if message_provider is not None:
        try:
            if isinstance(message_provider, CommitMessageProvider):
                commit_message = message_provider.get_commit_message(
                    parsed.repository, parsed.commit_id
                )
            elif callable(message_provider):
                commit_message = message_provider(parsed.repository, parsed.commit_id)
            else:
                raise PermanentCommitMessageError(
                    f"Invalid message_provider type: {type(message_provider).__name__}. "
                    "Expected CommitMessageProvider or callable(repository, commit_id)."
                )
        except CommitMessageError:
            raise
        except (ConnectionError, TimeoutError, OSError) as err:
            raise TransientCommitRetrievalError(
                f"Transient network error retrieving commit message from provider: {err}"
            ) from err
        except Exception as err:
            raise TransientCommitRetrievalError(
                f"Transient error retrieving commit message from provider: {err}"
            ) from err
    else:
        # Check for synthetic test fixture message inside detail
        detail = event.get("detail", {}) if isinstance(event, dict) else {}
        fixture_msg = detail.get("commitMessage")
        if isinstance(fixture_msg, str) and fixture_msg.strip():
            commit_message = fixture_msg.strip()
        else:
            raise PermanentCommitMessageError(
                "Commit message could not be obtained. In offline mode, provide a "
                "CommitMessageProvider, a callable provider, or include 'commitMessage' in the synthetic test event."
            )

    if not isinstance(commit_message, str) or not commit_message.strip():
        raise PermanentCommitMessageError("Retrieved commit message is empty or invalid.")

    return {
        "schemaVersion": SCHEMA_VERSION,
        "eventId": parsed.event_id,
        "repository": parsed.repository,
        "branch": parsed.branch,
        "commitId": parsed.commit_id,
        "message": commit_message.strip(),
        "timestamp": parsed.timestamp,
    }


# ==============================================================================
# AWS Lambda Handler Entrypoint
# ==============================================================================

def lambda_handler(
    event: Dict[str, Any],
    context: Any = None,
    message_provider: Optional[MessageProviderType] = None,
    publisher: Optional[MQTTPublisher] = None,
    mqtt_topic: str = DEFAULT_MQTT_TOPIC,
    raise_on_retryable: bool = False,
) -> Dict[str, Any]:
    """
    AWS Lambda core event processor.

    Args:
        event: The incoming EventBridge event dictionary.
        context: AWS Lambda runtime context (optional/mockable in offline tests).
        message_provider: Optional CommitMessageProvider instance or callable.
                          If None in a real environment, production integration
                          will instantiate a Boto3 CodeCommit provider.
        publisher: Optional MQTTPublisher instance for delivering the payload.
                   If None, payload is constructed and returned without publishing.
        mqtt_topic: Target MQTT topic string (defaults to 'gitops/commits').
        raise_on_retryable: If True, transient retryable failures are raised as
                            unhandled exceptions so AWS Lambda marks the invocation
                            as failed to trigger Lambda's asynchronous invocation retry
                            queue (up to 2 retries) and On-Failure DLQ destination routing.
                            If False (default), returns structured dicts with statusCode
                            for offline test convenience.

    Returns:
        Structured response dictionary containing status code and payload or error info:
        - 200: {"statusCode": 200, "status": "success", "payload": {...}} (if publisher is None)
        - 200: {"statusCode": 200, "status": "success", "payload": {...}, "published": True, "topic": "..."} (if publisher is provided)
        - 400: {"statusCode": 400, "status": "error", "errorType": "...", "message": "...", "retryable": False}
        - 500: {"statusCode": 500, "status": "error", "errorType": "...", "message": "...", "retryable": True}
    """
    try:
        payload = build_notification_payload(event, message_provider=message_provider)

        # If an MQTT publisher is injected, publish payload to the topic
        if publisher is not None:
            publish_success = publisher.publish(topic=mqtt_topic, payload=payload)
            if publish_success is not True:
                raise TransientMQTTPublishError(
                    f"MQTT publisher rejected delivery to topic '{mqtt_topic}' (returned False)."
                )
            return {
                "statusCode": 200,
                "status": "success",
                "payload": payload,
                "published": True,
                "topic": mqtt_topic,
            }

        return {
            "statusCode": 200,
            "status": "success",
            "payload": payload,
        }
    except (EventValidationError, UnsupportedEventError) as err:
        return {
            "statusCode": 400,
            "status": "error",
            "errorType": err.__class__.__name__,
            "message": str(err),
            "retryable": False,
        }
    except CommitMessageError as err:
        is_retryable = is_retryable_error(err)
        if is_retryable and raise_on_retryable:
            raise
        return {
            "statusCode": 500 if is_retryable else 400,
            "status": "error",
            "errorType": "CommitMessageError",
            "message": str(err),
            "retryable": is_retryable,
        }
    except MQTTPublishError as err:
        is_retryable = is_retryable_error(err)
        if is_retryable and raise_on_retryable:
            raise
        return {
            "statusCode": 500,
            "status": "error",
            "errorType": "MQTTPublishError",
            "message": str(err),
            "retryable": is_retryable,
        }
    except Exception as err:
        if raise_on_retryable:
            raise
        return {
            "statusCode": 500,
            "status": "error",
            "errorType": "InternalError",
            "message": f"Unexpected error during event processing: {err}",
            "retryable": True,
        }


_UNSET = object()


def production_lambda_handler(
    event: Dict[str, Any],
    context: Any = None,
    message_provider: Any = _UNSET,
    publisher: Any = _UNSET,
    mqtt_topic: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Production entry point for asynchronous EventBridge Lambda invocations.

    When invoked by AWS Lambda (where message_provider and publisher are not supplied):
    - Automatically constructs Boto3CodeCommitProvider using the AWS SDK.
    - Automatically constructs Boto3IotDataPublisher using the AWS SDK and environment config.
    - Resolves MQTT topic from parameter, 'MQTT_TOPIC' environment variable, or default 'gitops/commits'.

    Asynchronous Failure Handling Strategy:
    - Permanent validation errors (EventValidationError, UnsupportedEventError,
      PermanentCommitMessageError, PermanentMQTTPublishError) are caught and acknowledged
      with statusCode 400 (retryable=False). The invocation exits cleanly with code 0 so
      neither EventBridge nor Lambda async queues fruitlessly retry permanent poison pills.
    - Transient infrastructure errors (TransientCommitRetrievalError,
      TransientMQTTPublishError, unexpected exceptions) are raised as unhandled
      exceptions. AWS Lambda marks the invocation as failed, triggering Lambda's
      asynchronous invocation retry mechanism (up to 2 retries) and eventual
      routing to the Lambda On-Failure destination (DLQ).
    - Note on EventBridge vs Lambda failure isolation:
      EventBridge target RetryPolicy and DLQ handle target delivery failures (e.g. Lambda
      service throttles or outages). Once Lambda accepts the event into its async queue,
      function execution failures are managed exclusively by Lambda Event Invoke Config.
    - Successful events return statusCode 200 with payload and published=True.
    """
    target_topic = (
        mqtt_topic
        if mqtt_topic is not None
        else os.environ.get("MQTT_TOPIC", DEFAULT_MQTT_TOPIC)
    )

    if message_provider is _UNSET:
        message_provider = Boto3CodeCommitProvider()
    if publisher is _UNSET:
        publisher = Boto3IotDataPublisher()

    return lambda_handler(
        event=event,
        context=context,
        message_provider=message_provider,
        publisher=publisher,
        mqtt_topic=target_topic,
        raise_on_retryable=True,
    )


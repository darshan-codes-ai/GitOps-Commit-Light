"""
GitOps Commit Light — MQTT Publishing Abstraction

This module defines the MQTT publishing interface, an offline mock
implementation for local testing, and a production AWS IoT Data Plane publisher.

Architecture Role:
    CodeCommit -> EventBridge -> Lambda -> [MQTTPublisher] -> ESP32
                                                │
                                    Offline: MockMQTTPublisher
                                    Production: Boto3IotDataPublisher

Topic:
    gitops/commits
"""

from __future__ import annotations

import abc
from dataclasses import dataclass
import json
import os
from typing import Any, Dict, List, Optional, Tuple

# Default MQTT topic for GitOps Commit Light notifications
DEFAULT_MQTT_TOPIC = "gitops/commits"

# Permanent error codes from AWS IoT Data Plane ClientError (non-retryable)
PERMANENT_IOT_ERROR_CODES = {
    "InvalidRequestException",
    "UnauthorizedException",
    "MethodNotAllowedException",
    "ResourceNotFoundException",
}

# Transient error codes from AWS IoT Data Plane ClientError (retryable)
TRANSIENT_IOT_ERROR_CODES = {
    "ThrottlingException",
    "RequestThrottled",
    "TooManyRequestsException",
    "InternalFailureException",
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


class MQTTPublishError(Exception):
    """Base exception for all MQTT publishing errors."""
    pass


class PermanentMQTTPublishError(MQTTPublishError):
    """Raised when an MQTT topic or payload is fundamentally invalid (non-retryable)."""
    pass


class TransientMQTTPublishError(MQTTPublishError):
    """Raised when publication fails due to transient broker or network issues (retryable)."""
    pass


@dataclass(frozen=True)
class PublishedMessage:
    """
    Represents an in-memory recorded message for verification in offline tests.
    
    Attributes:
        topic: The MQTT topic where the message was published.
        payload: The JSON-compatible payload dictionary.
    """
    topic: str
    payload: Dict[str, Any]


class MQTTPublisher(abc.ABC):
    """
    Abstract base class interface for MQTT publishers.
    
    Decouples event handling from the underlying MQTT transport mechanism.
    """

    @abc.abstractmethod
    def publish(self, topic: str, payload: Dict[str, Any]) -> bool:
        """
        Publish a JSON-serializable payload to an MQTT topic.

        Args:
            topic: The target MQTT topic string (e.g. 'gitops/commits').
            payload: A dictionary representing the notification payload.

        Returns:
            True if publication was accepted.

        Raises:
            MQTTPublishError: If the topic or payload is invalid, or if publication fails.
        """
        pass


class MockMQTTPublisher(MQTTPublisher):
    """
    Offline mock MQTT publisher for local development and automated testing.

    Features:
        - Validates topic format (rejects empty topics and MQTT wildcards '+' or '#').
        - Validates JSON serializability of the payload.
        - Records accepted messages in memory for test assertions.
        - Can be configured to simulate publication failures (should_fail=True).

    Note:
        This mock records messages in memory for offline testing.
        It does NOT deliver messages to a real MQTT broker or network.
    """

    def __init__(
        self,
        should_fail: bool = False,
        fail_message: str = "Simulated MQTT publication failure.",
        return_value: bool = True,
    ):
        self.should_fail = should_fail
        self.fail_message = fail_message
        self.return_value = return_value
        self._published_messages: List[PublishedMessage] = []

    @property
    def published_messages(self) -> List[PublishedMessage]:
        """Return a read-only copy of messages published to this mock."""
        return list(self._published_messages)

    def publish(self, topic: str, payload: Dict[str, Any]) -> bool:
        """
        Record a published message in memory after validation.

        Args:
            topic: The target MQTT topic.
            payload: The notification payload dictionary.

        Returns:
            True if validation succeeds and should_fail is False.

        Raises:
            MQTTPublishError: If topic or payload is invalid, or if simulated failure is triggered.
        """
        # 1. Validate topic
        if not isinstance(topic, str) or not topic.strip():
            raise PermanentMQTTPublishError("MQTT topic must be a non-empty string.")

        clean_topic = topic.strip()

        # Concrete publication topics must not contain MQTT subscription wildcards
        if "+" in clean_topic or "#" in clean_topic:
            raise PermanentMQTTPublishError(
                f"Cannot publish to wildcard topic '{clean_topic}'. Wildcards ('+' and '#') are for subscriptions only."
            )

        # 2. Validate payload structure and serializability
        if not isinstance(payload, dict):
            raise PermanentMQTTPublishError(
                f"Payload must be a dictionary, received: {type(payload).__name__}."
            )

        try:
            # Confirm that payload can be serialized to JSON
            json.dumps(payload)
        except (TypeError, OverflowError) as err:
            raise PermanentMQTTPublishError(
                f"Payload is not JSON-serializable: {err}"
            ) from err

        # 3. Simulate failure if configured
        if self.should_fail:
            raise TransientMQTTPublishError(self.fail_message)

        # 4. If return_value is False, simulate publisher rejection without raising an exception
        if not self.return_value:
            return False

        # 5. Record published message in memory
        self._published_messages.append(
            PublishedMessage(topic=clean_topic, payload=payload)
        )
        return True

    def clear(self) -> None:
        """Clear recorded messages from memory."""
        self._published_messages.clear()

    def last_message(self) -> Optional[PublishedMessage]:
        """Return the most recently published message, or None if none exist."""
        return self._published_messages[-1] if self._published_messages else None


class Boto3IotDataPublisher(MQTTPublisher):
    """
    Production MQTT publisher using the AWS SDK for Python (boto3) IoT Data Plane client.

    Uses HTTPS POST to the AWS IoT Core REST publish API endpoint
    (boto3 client 'iot-data'). In serverless Lambda, this is the standard,
    best-practice method for publishing to AWS IoT topics without requiring
    a stateful MQTT/TLS connection or device X.509 certificates.
    """

    def __init__(
        self,
        client: Optional[Any] = None,
        endpoint_url: Optional[str] = None,
        region_name: Optional[str] = None,
        session: Optional[Any] = None,
        qos: int = 0,
    ):
        self._client = client
        self._endpoint_url = endpoint_url
        self._region_name = (
            region_name
            or os.environ.get("AWS_REGION")
            or os.environ.get("AWS_DEFAULT_REGION")
        )
        self._session = session
        self.qos = qos

    def _resolve_endpoint_url(self) -> str:
        """Resolve and format the AWS IoT Data Plane endpoint URL from config or environment."""
        url = (
            self._endpoint_url
            or os.environ.get("IOT_DATA_ENDPOINT")
            or os.environ.get("AWS_IOT_DATA_ENDPOINT")
        )
        if not url or not isinstance(url, str) or not url.strip():
            raise PermanentMQTTPublishError(
                "AWS IoT Data Plane endpoint URL is not configured. "
                "Set the 'IOT_DATA_ENDPOINT' environment variable or pass endpoint_url to Boto3IotDataPublisher."
            )
        clean_url = url.strip()
        if not (clean_url.startswith("https://") or clean_url.startswith("http://")):
            clean_url = f"https://{clean_url}"
        return clean_url

    def _get_client(self) -> Any:
        """Get or lazily instantiate the boto3 'iot-data' client."""
        if self._client is not None:
            return self._client

        endpoint = self._resolve_endpoint_url()

        try:
            import boto3
        except ImportError as err:
            raise TransientMQTTPublishError(
                "AWS SDK (boto3) is required for Boto3IotDataPublisher but is not installed."
            ) from err

        kwargs: Dict[str, Any] = {
            "endpoint_url": endpoint,
        }
        if self._region_name:
            kwargs["region_name"] = self._region_name

        try:
            if self._session is not None:
                self._client = self._session.client("iot-data", **kwargs)
            else:
                self._client = boto3.client("iot-data", **kwargs)
            return self._client
        except Exception as err:
            raise TransientMQTTPublishError(
                f"Failed to create AWS IoT Data client: {err}"
            ) from err

    def publish(self, topic: str, payload: Dict[str, Any]) -> bool:
        """
        Publish a JSON-serializable payload to AWS IoT Core via boto3 iot-data.

        Args:
            topic: Target MQTT topic string.
            payload: Dictionary notification payload.

        Returns:
            True if publication succeeded (HTTP 200).

        Raises:
            PermanentMQTTPublishError: On invalid topic, non-serializable payload, or permanent client error.
            TransientMQTTPublishError: On throttling, service 5xx, or network timeout.
        """
        # 1. Topic validation
        if not isinstance(topic, str) or not topic.strip():
            raise PermanentMQTTPublishError("MQTT topic must be a non-empty string.")

        clean_topic = topic.strip()
        if "+" in clean_topic or "#" in clean_topic:
            raise PermanentMQTTPublishError(
                f"Cannot publish to wildcard topic '{clean_topic}'. Wildcards ('+' and '#') are for subscriptions only."
            )

        # 2. Payload validation and serialization
        if not isinstance(payload, dict):
            raise PermanentMQTTPublishError(
                f"Payload must be a dictionary, received: {type(payload).__name__}."
            )

        try:
            payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        except (TypeError, OverflowError) as err:
            raise PermanentMQTTPublishError(
                f"Payload is not JSON-serializable: {err}"
            ) from err

        # 3. Obtain client and call publish
        client = self._get_client()

        try:
            response = client.publish(
                topic=clean_topic,
                qos=self.qos,
                payload=payload_bytes,
            )
        except Exception as err:
            self._handle_publish_error(err, clean_topic)

        # 4. Validate response
        if isinstance(response, dict):
            status_code = response.get("ResponseMetadata", {}).get("HTTPStatusCode", 200)
            if status_code != 200:
                raise TransientMQTTPublishError(
                    f"AWS IoT Core publish returned non-200 HTTP status code: {status_code}"
                )
        return True

    def _handle_publish_error(self, err: Exception, topic: str) -> None:
        """Categorize and raise appropriate MQTTPublishError."""
        if isinstance(err, MQTTPublishError):
            raise err

        details = _extract_boto_error_details(err)
        if details is not None:
            code, message, status_code = details
            if code in PERMANENT_IOT_ERROR_CODES:
                raise PermanentMQTTPublishError(
                    f"AWS IoT Core rejected publication to topic '{topic}' with permanent error ({code}): {message}"
                ) from err
            if code in TRANSIENT_IOT_ERROR_CODES or status_code >= 500:
                raise TransientMQTTPublishError(
                    f"AWS IoT Core publication to topic '{topic}' failed with transient error ({code}): {message}"
                ) from err
            if 400 <= status_code < 500:
                raise PermanentMQTTPublishError(
                    f"AWS IoT Core publication to topic '{topic}' failed with client error ({code}): {message}"
                ) from err

        if isinstance(err, (ConnectionError, TimeoutError, OSError)):
            raise TransientMQTTPublishError(
                f"Network connection error publishing to AWS IoT Core topic '{topic}': {err}"
            ) from err

        err_type = type(err).__name__
        if "Timeout" in err_type or "Connection" in err_type or "Network" in err_type:
            raise TransientMQTTPublishError(
                f"Network error ({err_type}) publishing to AWS IoT Core topic '{topic}': {err}"
            ) from err

        raise TransientMQTTPublishError(
            f"Unexpected error publishing to AWS IoT Core topic '{topic}': {err}"
        ) from err

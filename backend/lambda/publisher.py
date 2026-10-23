"""
GitOps Commit Light — MQTT Publishing Abstraction

This module defines the MQTT publishing interface and an offline mock
implementation for local testing without connecting to AWS IoT Core.

Architecture Role:
    CodeCommit -> EventBridge -> Lambda -> [MQTTPublisher] -> ESP32
                                                │
                                    Offline: MockMQTTPublisher
                                    Future : Boto3/IoT-Data Publisher

Topic:
    gitops/commits
"""

from __future__ import annotations

import abc
from dataclasses import dataclass
import json
from typing import Any, Dict, List, Optional

# Default MQTT topic for GitOps Commit Light notifications
DEFAULT_MQTT_TOPIC = "gitops/commits"


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


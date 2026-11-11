#pragma once

#include <Arduino.h>
#include <ArduinoJson.h>

/**
 * ============================================================================
 * CommitEvent — Parsed GitOps Commit Light Notification
 * ============================================================================
 *
 * Strict Schema v1 Contract Representation:
 * {
 *   "schemaVersion": 1,
 *   "eventId": "<GitHub delivery GUID>",
 *   "repository": "<repository name>",
 *   "branch": "<branch name>",
 *   "commitId": "<commit SHA>",
 *   "message": "<commit message>",
 *   "timestamp": "<ISO-8601 timestamp>"
 * }
 */
struct CommitEvent {
    int schemaVersion;
    String eventId;
    String repository;
    String branch;
    String commitId;
    String message;
    String timestamp;
    bool isValid;
};

// Optional callback signature for hardware extensions (LEDs, OLED, Buzzer)
typedef void (*CommitNotificationCallback)(const CommitEvent& event);

/**
 * ============================================================================
 * CommitHandler — JSON Deserialization and Notification Processing
 * ============================================================================
 *
 * Responsibilities:
 * - Validate raw MQTT byte buffer and length.
 * - Deserializes JSON safely using ArduinoJson with fixed allocations.
 * - Validates schemaVersion == 1 and verifies required fields.
 * - Handles malformed JSON, truncated packets, and unexpected schema versions.
 * - Prints structured, professional notifications to the Serial Monitor.
 * - Provides extension hooks for optional physical indicators.
 */
class CommitHandler {
public:
    CommitHandler();

    /**
     * Parse and process a raw MQTT payload received on 'gitops/commits'.
     *
     * @param payload Pointer to incoming MQTT byte buffer
     * @param length Number of bytes in the payload
     * @return true if the payload was successfully parsed and validated as Schema v1
     */
    bool handlePayload(const byte* payload, unsigned int length);

    /**
     * Retrieve the most recently received valid commit event.
     */
    const CommitEvent& getLastEvent() const;

    /**
     * Total number of valid commit notifications processed since boot.
     */
    unsigned long getProcessedCount() const;

    /**
     * Register an optional callback for physical hardware indicators (LED, OLED).
     */
    void setCallback(CommitNotificationCallback callback);

private:
    CommitEvent _lastEvent;
    unsigned long _processedCount;
    CommitNotificationCallback _callback;

    void _printNotificationBanner(const CommitEvent& event);
};

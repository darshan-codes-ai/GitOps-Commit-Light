#pragma once

#include <Arduino.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include "commit_handler.h"

/**
 * ============================================================================
 * MqttManager — AWS IoT Core Secure MQTT Client
 * ============================================================================
 *
 * Responsibilities:
 * - Configure WiFiClientSecure with X.509 mTLS certificates:
 *     - Amazon Root CA 1
 *     - ESP32 Device Certificate
 *     - ESP32 Device Private Key
 * - Initialize PubSubClient with 2048-byte packet buffer.
 * - Establish secure TLS connection on port 8883.
 * - Subscribe exclusively to 'gitops/commits' (QoS 0).
 * - Monitor connection health and handle non-blocking reconnection.
 * - Route incoming MQTT payloads to CommitHandler.
 * - Report TLS and MQTT diagnostic states to Serial Monitor.
 */
class MqttManager {
public:
    MqttManager(
        const char* endpoint,
        uint16_t port,
        const char* clientId,
        const char* topic,
        const char* rootCA,
        const char* deviceCert,
        const char* privateKey,
        CommitHandler& commitHandler
    );

    /**
     * Configure TLS credentials and initialize MQTT client settings.
     */
    void begin();

    /**
     * Maintain MQTT connection and process incoming network packets.
     * Must be called frequently from loop().
     *
     * @param wifiConnected Current Wi-Fi connection status from WiFiManager
     */
    void update(bool wifiConnected);

    /**
     * Query active MQTT broker connection status.
     * @return true if connected and authenticated with AWS IoT Core.
     */
    bool isConnected();

    /**
     * Internal callback invoked by PubSubClient when an MQTT message arrives.
     */
    void handleMessage(char* topic, byte* payload, unsigned int length);

private:
    const char* _endpoint;
    uint16_t _port;
    const char* _clientId;
    const char* _topic;
    const char* _rootCA;
    const char* _deviceCert;
    const char* _privateKey;

    CommitHandler& _commitHandler;
    WiFiClientSecure _wifiClientSecure;
    PubSubClient _mqttClient;

    unsigned long _lastReconnectAttempt;
    bool _wasConnected;

    void _connect();
    void _printMqttState(int state);
};

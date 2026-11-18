#include "mqtt_manager.h"

// Non-blocking reconnect delay (5 seconds)
static const unsigned long RECONNECT_INTERVAL_MS = 5000;

// Static instance pointer for C-style PubSubClient callback dispatch
static MqttManager* s_mqttManagerInstance = nullptr;

static void globalMqttCallback(char* topic, byte* payload, unsigned int length) {
    if (s_mqttManagerInstance) {
        s_mqttManagerInstance->handleMessage(topic, payload, length);
    }
}

MqttManager::MqttManager(
    const char* endpoint,
    uint16_t port,
    const char* clientId,
    const char* topic,
    const char* rootCA,
    const char* deviceCert,
    const char* privateKey,
    CommitHandler& commitHandler
) : _endpoint(endpoint),
    _port(port),
    _clientId(clientId),
    _topic(topic),
    _rootCA(rootCA),
    _deviceCert(deviceCert),
    _privateKey(privateKey),
    _commitHandler(commitHandler),
    _mqttClient(_wifiClientSecure),
    _lastReconnectAttempt(0),
    _wasConnected(false) {}

void MqttManager::begin() {
    s_mqttManagerInstance = this;

    Serial.println();
    Serial.println(F("========================================"));
    Serial.println(F("        AWS IOT MQTT INITIALIZATION"));
    Serial.println(F("========================================"));
    Serial.printf("[MQTT] Broker Endpoint : %s\n", _endpoint);
    Serial.printf("[MQTT] Port            : %u\n", _port);
    Serial.printf("[MQTT] Client ID       : %s\n", _clientId);
    Serial.printf("[MQTT] Monitored Topic : %s\n", _topic);

    // 1. Configure TLS X.509 mutual authentication credentials
    _wifiClientSecure.setCACert(_rootCA);
    _wifiClientSecure.setCertificate(_deviceCert);
    _wifiClientSecure.setPrivateKey(_privateKey);

    // 2. Configure PubSubClient network parameters
    _mqttClient.setServer(_endpoint, _port);
    _mqttClient.setCallback(globalMqttCallback);
    if (!_mqttClient.setBufferSize(2048)) {
        Serial.println(F("[MQTT ERROR] Failed to allocate 2048-byte MQTT packet buffer! Out of memory."));
    } else {
        Serial.println(F("[MQTT] Packet buffer allocated: 2048 bytes."));
    }
    _mqttClient.setKeepAlive(60);     // 60-second ping interval
}

void MqttManager::update(bool wifiConnected) {
    // If Wi-Fi is down, we cannot talk to AWS IoT Core
    if (!wifiConnected) {
        if (_wasConnected) {
            _wasConnected = false;
            Serial.println(F("[MQTT] Disconnected due to Wi-Fi outage."));
        }
        return;
    }

    if (_mqttClient.connected()) {
        if (!_wasConnected) {
            _wasConnected = true;
            Serial.println(F("[MQTT] Status: CONNECTED & SUBSCRIBED"));
            Serial.printf("[MQTT] Actively listening for notifications on '%s'...\n", _topic);
            Serial.println(F("========================================"));
        }
        _mqttClient.loop();
        return;
    }

    // MQTT is disconnected but Wi-Fi is available
    if (_wasConnected) {
        _wasConnected = false;
        Serial.println();
        Serial.println(F("[MQTT WARNING] Connection to AWS IoT Core broker lost!"));
        _printMqttState(_mqttClient.state());
    }

    unsigned long now = millis();
    if (now - _lastReconnectAttempt > RECONNECT_INTERVAL_MS) {
        _lastReconnectAttempt = now;
        Serial.println(F("[MQTT] Attempting connection to AWS IoT Core..."));
        _connect();
    }
}

void MqttManager::_connect() {
    // 1. Verify buffer size before connecting to prevent silent packet truncation
    if (_mqttClient.getBufferSize() < 2048) {
        Serial.printf("[MQTT ERROR] Buffer is undersized (%u bytes, required: 2048). Attempting re-allocation...\n", _mqttClient.getBufferSize());
        if (!_mqttClient.setBufferSize(2048)) {
            Serial.println(F("[MQTT ABORT] Cannot connect: Insufficient heap for 2048-byte buffer."));
            return;
        }
        Serial.println(F("[MQTT] Packet buffer re-allocated: 2048 bytes."));
    }

    // 2. Check for unconfigured placeholders
    if (!_endpoint || strstr(_endpoint, "YOUR_ENDPOINT") != nullptr) {
        Serial.println(F("[MQTT ERROR] Placeholder AWS IoT endpoint detected! Update include/config.h."));
        return;
    }

    if (!_deviceCert || strstr(_deviceCert, "REPLACE WITH") != nullptr ||
        !_privateKey || strstr(_privateKey, "REPLACE WITH") != nullptr) {
        Serial.println(F("[MQTT ERROR] Placeholder X.509 certificate or private key detected!"));
        Serial.println(F("[MQTT ERROR] Follow firmware/esp32/README.md to configure include/certificates.h."));
        return;
    }

    Serial.printf("[MQTT] Connecting as client '%s'...\n", _clientId);

    // In AWS IoT Core mTLS, authentication is in the TLS layer; username and password are NULL
    if (_mqttClient.connect(_clientId)) {
        Serial.println(F("[MQTT] TLS Handshake & Authentication SUCCESSFUL."));

        // Subscribe to gitops/commits (QoS 0)
        if (_mqttClient.subscribe(_topic, 0)) {
            Serial.printf("[MQTT] Subscribed to topic: %s (QoS 0)\n", _topic);
        } else {
            Serial.printf("[MQTT ERROR] Failed to subscribe to topic: %s\n", _topic);
        }
    } else {
        Serial.print(F("[MQTT ERROR] Connect failed! "));
        _printMqttState(_mqttClient.state());
    }
}

void MqttManager::handleMessage(char* topic, byte* payload, unsigned int length) {
    Serial.println();
    Serial.printf("[MQTT RX] Message arrived on [%s] (%u bytes)\n", topic, length);

    // Verify topic matches expected topic
    if (strcmp(topic, _topic) != 0) {
        Serial.printf("[MQTT RX WARNING] Unexpected topic '%s' (expected '%s'). Discarding.\n", topic, _topic);
        return;
    }

    // Forward to commit handler
    _commitHandler.handlePayload(payload, length);
}

bool MqttManager::isConnected() {
    return _mqttClient.connected();
}

void MqttManager::_printMqttState(int state) {
    Serial.printf("State (%d): ", state);
    switch (state) {
        case -4: Serial.println(F("MQTT_CONNECTION_TIMEOUT — Server did not respond within keepalive time")); break;
        case -3: Serial.println(F("MQTT_CONNECTION_LOST — Network connection was broken")); break;
        case -2: Serial.println(F("MQTT_CONNECT_FAILED — Network connection failed (check Wi-Fi / DNS)")); break;
        case -1: Serial.println(F("MQTT_DISCONNECTED — Client is disconnected cleanly")); break;
        case 0:  Serial.println(F("MQTT_CONNECTED — Successfully connected")); break;
        case 1:  Serial.println(F("MQTT_CONNECT_BAD_PROTOCOL — Broker doesn't support the requested version of MQTT")); break;
        case 2:  Serial.println(F("MQTT_CONNECT_BAD_CLIENT_ID — Broker rejected client identifier (check IoT policy)")); break;
        case 3:  Serial.println(F("MQTT_CONNECT_UNAVAILABLE — Broker was unable to accept the connection")); break;
        case 4:  Serial.println(F("MQTT_CONNECT_BAD_CREDENTIALS — Bad username/password")); break;
        case 5:  Serial.println(F("MQTT_CONNECT_UNAUTHORIZED — Client not authorized to connect (check IoT Policy attachment)")); break;
        default: Serial.println(F("Unknown error state")); break;
    }
}

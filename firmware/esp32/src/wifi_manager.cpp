#include "wifi_manager.h"

// Reconnect interval when disconnected (5 seconds)
static const unsigned long RECONNECT_INTERVAL_MS = 5000;
static const unsigned long CONNECT_TIMEOUT_MS = 20000;

WiFiManager::WiFiManager(const char* ssid, const char* password)
    : _ssid(ssid),
      _password(password),
      _wasConnected(false),
      _lastReconnectAttempt(0),
      _connectionStartTime(0),
      _isConnecting(false) {}

void WiFiManager::begin() {
    Serial.println();
    Serial.println(F("========================================"));
    Serial.println(F("        WIFI INITIALIZATION"));
    Serial.println(F("========================================"));
    Serial.printf("[WIFI] Target SSID: %s\n", _ssid);
    Serial.printf("[WIFI] MAC Address: %s\n", WiFi.macAddress().c_str());

    WiFi.mode(WIFI_STA);
    WiFi.setAutoReconnect(false); // We handle reconnection explicitly to avoid blocking
    _connect();
}

void WiFiManager::_connect() {
    if (!_ssid || strlen(_ssid) == 0 || strcmp(_ssid, "YOUR_WIFI_SSID") == 0) {
        Serial.println(F("[WIFI ERROR] Invalid or placeholder SSID configured in config.h!"));
        Serial.println(F("[WIFI ERROR] Please update include/config.h with real Wi-Fi credentials."));
        _isConnecting = false;
        return;
    }

    Serial.print(F("[WIFI] Connecting to network..."));
    WiFi.begin(_ssid, _password);
    _isConnecting = true;
    _connectionStartTime = millis();
    _lastReconnectAttempt = millis();
}

void WiFiManager::update() {
    wl_status_t currentStatus = WiFi.status();

    if (currentStatus == WL_CONNECTED) {
        if (!_wasConnected) {
            _wasConnected = true;
            _isConnecting = false;
            Serial.println();
            Serial.println(F("[WIFI] Status: CONNECTED"));
            Serial.printf("[WIFI] Assigned IP : %s\n", WiFi.localIP().toString().c_str());
            Serial.printf("[WIFI] Subnet Mask : %s\n", WiFi.subnetMask().toString().c_str());
            Serial.printf("[WIFI] Gateway IP  : %s\n", WiFi.gatewayIP().toString().c_str());
            Serial.printf("[WIFI] Signal (RSSI): %d dBm\n", WiFi.RSSI());
            Serial.println(F("========================================"));
        }
        return;
    }

    // Wi-Fi is currently not connected
    if (_wasConnected) {
        _wasConnected = false;
        _isConnecting = false;
        Serial.println();
        Serial.println(F("[WIFI WARNING] Wi-Fi connection lost!"));
        Serial.println(F("[WIFI] Will attempt automatic reconnection in background..."));
    }

    unsigned long now = millis();

    // Check if an active connection attempt timed out
    if (_isConnecting && (now - _connectionStartTime > CONNECT_TIMEOUT_MS)) {
        Serial.println();
        Serial.println(F("[WIFI TIMEOUT] Connection attempt timed out. Disconnecting before retry."));
        WiFi.disconnect();
        _isConnecting = false;
    }

    // Trigger retry if interval has elapsed and not currently connecting
    if (!_isConnecting && (now - _lastReconnectAttempt > RECONNECT_INTERVAL_MS)) {
        _lastReconnectAttempt = now;
        Serial.println(F("[WIFI] Retrying connection to network..."));
        _connect();
    }
}

bool WiFiManager::isConnected() const {
    return WiFi.status() == WL_CONNECTED;
}

String WiFiManager::getLocalIP() const {
    if (WiFi.status() == WL_CONNECTED) {
        return WiFi.localIP().toString();
    }
    return String("0.0.0.0");
}

int WiFiManager::getRSSI() const {
    if (WiFi.status() == WL_CONNECTED) {
        return WiFi.RSSI();
    }
    return 0;
}

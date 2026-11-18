#pragma once

#include <Arduino.h>
#include <WiFi.h>

/**
 * ============================================================================
 * WiFiManager — Non-blocking Wi-Fi Lifecycle Management
 * ============================================================================
 *
 * Responsibilities:
 * - Initialize ESP32 Wi-Fi in Station mode (WIFI_STA).
 * - Connect to configured SSID using credentials.
 * - Monitor connection health periodically without blocking the main execution loop.
 * - Execute automatic, rate-limited reconnection when Wi-Fi is lost.
 * - Provide connection telemetry (IP address, MAC address, RSSI signal strength).
 */
class WiFiManager {
public:
    WiFiManager(const char* ssid, const char* password);

    /**
     * Initialize Wi-Fi hardware and begin initial connection.
     */
    void begin();

    /**
     * Poll Wi-Fi state. Must be called regularly from loop().
     * Handles non-blocking reconnection attempts if Wi-Fi drops.
     */
    void update();

    /**
     * Query connection status.
     * @return true if Wi-Fi is currently connected with a valid IP address.
     */
    bool isConnected() const;

    /**
     * Get the current local IP address as a string.
     */
    String getLocalIP() const;

    /**
     * Get the current Wi-Fi Received Signal Strength Indicator (RSSI) in dBm.
     */
    int getRSSI() const;

private:
    const char* _ssid;
    const char* _password;

    bool _wasConnected;
    unsigned long _lastReconnectAttempt;
    unsigned long _connectionStartTime;
    bool _isConnecting;

    void _connect();
};

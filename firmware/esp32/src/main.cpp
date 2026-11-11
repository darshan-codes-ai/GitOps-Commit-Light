/**
 * ============================================================================
 * GitOps Commit Light — ESP32 Firmware Entry Point
 * ============================================================================
 *
 * Hardware:  ESP32 DevKit V1 (ESP32-WROOM-32)
 * Framework: Arduino (PlatformIO)
 * Transport: Secure MQTT over TLS (Port 8883)
 * Broker:    AWS IoT Core (Data-ATS Endpoint)
 * Topic:     gitops/commits (QoS 0)
 * Payload:   Schema v1 Notification Contract
 *
 * Responsibilities:
 * - Initialize Serial Monitor (115200 baud).
 * - Initialize Wi-Fi connection manager.
 * - Initialize AWS IoT Core secure MQTT manager (X.509 mutual TLS).
 * - Register Schema v1 commit notification callback.
 * - Run continuous non-blocking poll loops in loop().
 * ============================================================================
 */

#include <Arduino.h>

// Fallback to example configuration if private config headers have not been created
#if __has_include("config.h")
    #include "config.h"
#elif __has_include("../include/config.h")
    #include "../include/config.h"
#elif __has_include("../include/config.h.example")
    #include "../include/config.h.example"
#else
    #include "config.h.example"
#endif

#if __has_include("certificates.h")
    #include "certificates.h"
#elif __has_include("../include/certificates.h")
    #include "../include/certificates.h"
#elif __has_include("../include/certificates.h.example")
    #include "../include/certificates.h.example"
#else
    #include "certificates.h.example"
#endif

#include "wifi_manager.h"
#include "commit_handler.h"
#include "mqtt_manager.h"

// Instantiate core subsystems
static WiFiManager wifiManager(WIFI_SSID, WIFI_PASSWORD);
static CommitHandler commitHandler;
static MqttManager mqttManager(
    AWS_IOT_ENDPOINT,
    AWS_IOT_PORT,
    AWS_IOT_CLIENT_ID,
    AWS_IOT_TOPIC,
    AWS_CERT_CA,
    AWS_CERT_CRT,
    AWS_CERT_PRIVATE,
    commitHandler
);

/**
 * Optional hardware callback for physical indicators (LED flash, OLED screen, Buzzer).
 * Invoked automatically by CommitHandler whenever a valid Schema v1 commit arrives.
 */
static void onCommitReceived(const CommitEvent& event) {
#if defined(PIN_COMMIT_LED) && (PIN_COMMIT_LED >= 0)
    // Optional hardware indicator pulse
    digitalWrite(PIN_COMMIT_LED, HIGH);
    delay(100);
    digitalWrite(PIN_COMMIT_LED, LOW);
#endif
    // Additional peripheral handlers (e.g., SSD1306 OLED) can be added here
}

void setup() {
    // 1. Initialize Serial communication
    Serial.begin(SERIAL_BAUD_RATE);
    while (!Serial && millis() < 2000) {
        // Brief pause for native USB CDC if applicable
    }

    Serial.println();
    Serial.println(F("========================================"));
    Serial.println(F("    GITOPS COMMIT LIGHT — ESP32 NODE    "));
    Serial.println(F("========================================"));
    Serial.println(F("Firmware Version : 1.0.0"));
    Serial.println(F("Target Board     : ESP32 DevKit V1"));
    Serial.println(F("Framework        : Arduino / PlatformIO"));
    Serial.println(F("MQTT Contract    : Schema v1"));
    Serial.println(F("Target Topic     : gitops/commits"));
    Serial.println(F("========================================"));
    Serial.println();

#if defined(PIN_COMMIT_LED) && (PIN_COMMIT_LED >= 0)
    pinMode(PIN_COMMIT_LED, OUTPUT);
    digitalWrite(PIN_COMMIT_LED, LOW);
#endif

    // 2. Attach physical hardware hook to commit handler
    commitHandler.setCallback(onCommitReceived);

    // 3. Initialize Wi-Fi subsystem
    wifiManager.begin();

    // 4. Initialize AWS IoT Core secure MQTT subsystem
    mqttManager.begin();
}

void loop() {
    // 1. Service Wi-Fi state machine and automatic reconnects
    wifiManager.update();

    // 2. Service MQTT client, keep-alive pings, and message reception
    mqttManager.update(wifiManager.isConnected());

    // 3. Yield to FreeRTOS scheduler to prevent watchdog timeouts
    delay(10);
}

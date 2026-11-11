# 💡 GitOps Commit Light — ESP32 Firmware

Production-grade ESP32 firmware for **GitOps Commit Light**, built with C++ on the Arduino framework via **PlatformIO**.

The ESP32 acts as a secure, edge subscriber to AWS IoT Core over mutual TLS (mTLS), listening for GitHub commit notifications published by the serverless Lambda backend on MQTT topic `gitops/commits`.

---

## 🧭 Hardware & Architecture Overview

* **Microcontroller:** ESP32 DevKit V1 (ESP32-WROOM-32, dual-core 240MHz, 520KB SRAM).
* **Framework:** Arduino framework via PlatformIO.
* **Connectivity:** 2.4 GHz Wi-Fi (802.11 b/g/n) with automatic, non-blocking reconnection.
* **Security:** TLS 1.2 with mutual authentication (X.509 client certificate + RSA private key).
* **Protocol:** MQTT 3.1.1 (QoS 0) via `PubSubClient` with 2048-byte packet buffer.
* **Payload Serialization:** `ArduinoJson` Schema v1 deserializer and validator.

```text
GitHub Push Event
       │
       ▼ (HTTPS Webhook)
AWS API Gateway HTTP API v2
       │
       ▼ (Lambda Proxy)
AWS Lambda (github_webhook_handler)
       │
       ▼ (MQTT over TLS)
AWS IoT Core Broker (Topic: gitops/commits)
       │
       ▼ (Mutual TLS port 8883)
ESP32 Subscriber (firmware/esp32/)
  ├── WiFiManager (Non-blocking reconnection)
  ├── MqttManager (WiFiClientSecure + Amazon Root CA 1 + Device X.509 Cert)
  ├── CommitHandler (ArduinoJson Schema v1 Parser)
  └── Serial Monitor (Formatted commit banner at 115200 baud)
```

---

## 📂 Firmware Directory Structure

```text
firmware/esp32/
├── platformio.ini              # PlatformIO build configuration & dependencies
├── .gitignore                  # Excludes private config and TLS keys
├── README.md                   # This guide
├── include/
│   ├── config.h.example        # Wi-Fi SSID, password, AWS endpoint placeholders
│   └── certificates.h.example  # Root CA 1, device certificate, private key placeholders
├── src/
│   ├── main.cpp                # Setup, loop, FreeRTOS yield, subsystem lifecycle
│   ├── wifi_manager.h          # Wi-Fi connection interface
│   ├── wifi_manager.cpp        # Non-blocking Wi-Fi state machine & diagnostics
│   ├── mqtt_manager.h          # AWS IoT Core MQTT manager interface
│   ├── mqtt_manager.cpp        # TLS mTLS setup, buffer sizing, subscription, callback
│   ├── commit_handler.h        # Schema v1 parser & CommitEvent struct definition
│   └── commit_handler.cpp      # ArduinoJson validation, missing field guards & Serial banner
└── test/
    └── README.md               # Test matrix and simulation guidelines
```

---

## 🛠️ Prerequisites & Setup

### 1. Development Environment
* [Visual Studio Code](https://code.visualstudio.com/)
* [PlatformIO IDE Extension](https://marketplace.visualstudio.com/items?itemName=platformio.platformio-ide) for VS Code.

### 2. AWS IoT Core Setup (One-Time Setup)

#### Step A: Create an AWS IoT Thing
1. Open the [AWS IoT Core Console](https://console.aws.amazon.com/iot/).
2. In the navigation pane, choose **Manage** -> **All devices** -> **Things**.
3. Click **Create things** -> **Create single thing**.
4. Thing name: `esp32-gitops-commit-light`
5. Click **Next**.

#### Step B: Generate Device Certificates
1. Under **Device certificate**, choose **Auto-generate a new certificate (recommended)**.
2. Click **Next**.

#### Step C: Attach Least-Privilege IoT Policy
1. Select the policy created from `aws/iot-policy.json`. If you have not created it yet, create a policy named `GitOpsESP32SubscriberPolicy` with the following document:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": ["iot:Connect"],
         "Resource": "arn:aws:iot:us-east-1:ACCOUNT_ID:client/esp32-gitops-commit-light"
       },
       {
         "Effect": "Allow",
         "Action": ["iot:Subscribe"],
         "Resource": "arn:aws:iot:us-east-1:ACCOUNT_ID:topicfilter/gitops/commits"
       },
       {
         "Effect": "Allow",
         "Action": ["iot:Receive"],
         "Resource": "arn:aws:iot:us-east-1:ACCOUNT_ID:topic/gitops/commits"
       }
     ]
   }
   ```
   *(Replace `ACCOUNT_ID` with your 12-digit AWS account ID. Notice: Strictly NO `iot:Publish` permission).*
2. Click **Create thing**.

#### Step D: Download Certificates
Download and store securely:
* **Device certificate:** `xxxx-certificate.pem.crt`
* **Private key:** `xxxx-private.pem.key`
* **Amazon Root CA 1:** `AmazonRootCA1.pem` (Already included in `certificates.h.example`).

---

## 🔐 Firmware Configuration

### 1. Create Private `config.h`
Copy `config.h.example` to `config.h`:
```bash
cp firmware/esp32/include/config.h.example firmware/esp32/include/config.h
```

Edit `firmware/esp32/include/config.h` with your Wi-Fi credentials and AWS IoT endpoint:
```c
#define WIFI_SSID "Your_WiFi_Network"
#define WIFI_PASSWORD "Your_WiFi_Password"
#define AWS_IOT_ENDPOINT "a1jg5cptbrzoqy-ats.iot.us-east-1.amazonaws.com"
#define AWS_IOT_CLIENT_ID "esp32-gitops-commit-light"
#define AWS_IOT_TOPIC "gitops/commits"
```

### 2. Create Private `certificates.h`
Copy `certificates.h.example` to `certificates.h`:
```bash
cp firmware/esp32/include/certificates.h.example firmware/esp32/include/certificates.h
```

Paste the contents of your downloaded files into the raw string literals:
* `AWS_CERT_CRT`: Paste text from `xxxx-certificate.pem.crt`.
* `AWS_CERT_PRIVATE`: Paste text from `xxxx-private.pem.key`.

> ⚠️ **SECURITY GUARANTEE:** Both `config.h` and `certificates.h` are explicitly excluded by `.gitignore`. Real credentials will never be tracked or committed to Git.

---

## ⚡ Compilation & Flashing

### Compile Firmware (Without Physical Hardware)
You can compile the firmware on any computer without connecting a board:

```bash
# Navigate to the firmware directory
cd firmware/esp32

# Compile with PlatformIO CLI
pio run
```

Or in **VS Code**:
1. Open the project root or `firmware/esp32/` in VS Code.
2. Click the PlatformIO alien icon in the sidebar.
3. Under **esp32dev**, click **Build**.

### Flash to Physical ESP32 (When Hardware is Connected)
1. Connect your ESP32 DevKit V1 to your computer via micro-USB.
2. Ensure the Silicon Labs CP210x or CH340 USB-to-UART driver is installed.
3. Run:
   ```bash
   pio run --target upload
   ```
4. Open the Serial Monitor:
   ```bash
   pio device monitor -b 115200
   ```

---

## 📺 Expected Serial Output

When powered on and connected to Wi-Fi and AWS IoT Core:

```text
========================================
    GITOPS COMMIT LIGHT — ESP32 NODE
========================================
Firmware Version : 1.0.0
Target Board     : ESP32 DevKit V1
Framework        : Arduino / PlatformIO
MQTT Contract    : Schema v1
Target Topic     : gitops/commits
========================================

========================================
        WIFI INITIALIZATION
========================================
[WIFI] Target SSID: Your_WiFi_Network
[WIFI] MAC Address: 24:6F:28:XX:XX:XX
[WIFI] Connecting to network...
[WIFI] Status: CONNECTED
[WIFI] Assigned IP : 192.168.1.105
[WIFI] Subnet Mask : 255.255.255.0
[WIFI] Gateway IP  : 192.168.1.1
[WIFI] Signal (RSSI): -54 dBm
========================================

========================================
        AWS IOT MQTT INITIALIZATION
========================================
[MQTT] Broker Endpoint : a1jg5cptbrzoqy-ats.iot.us-east-1.amazonaws.com
[MQTT] Port            : 8883
[MQTT] Client ID       : esp32-gitops-commit-light
[MQTT] Monitored Topic : gitops/commits
[MQTT] Attempting connection to AWS IoT Core...
[MQTT] Connecting as client 'esp32-gitops-commit-light'...
[MQTT] TLS Handshake & Authentication SUCCESSFUL.
[MQTT] Subscribed to topic: gitops/commits (QoS 0)
[MQTT] Status: CONNECTED & SUBSCRIBED
[MQTT] Actively listening for notifications on 'gitops/commits'...
========================================
```

When a commit is pushed to GitHub:

```text
[MQTT RX] Message arrived on [gitops/commits] (384 bytes)

========================================
          GITOPS COMMIT LIGHT
========================================

[NEW COMMIT RECEIVED]

Repository : GitOps-Commit-Light
Branch     : main
Commit ID  : 8bf7bfb1a2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7
Message    : feat: implement ESP32 PlatformIO firmware
Timestamp  : 2026-11-11T12:00:00Z
Event ID   : 7d6c5b4a-3e2f-1a0b-9c8d-7e6f5a4b3c2d

========================================
```

---

## 🔍 Troubleshooting

| Issue / Symptom | Probable Cause | Corrective Action |
| :--- | :--- | :--- |
| `[WIFI ERROR] Invalid or placeholder SSID` | `config.h` was not created or still has `"YOUR_WIFI_SSID"`. | Copy `config.h.example` to `config.h` and supply real Wi-Fi credentials. |
| `[MQTT ERROR] Placeholder X.509 certificate detected` | `certificates.h` has not been populated. | Paste your device certificate and private key into `include/certificates.h`. |
| `MQTT State (-2): MQTT_CONNECT_FAILED` | TLS DNS lookup failure or invalid endpoint hostname. | Verify `AWS_IOT_ENDPOINT` format in `include/config.h`. (Must NOT include `https://`). |
| `MQTT State (5): MQTT_CONNECT_UNAUTHORIZED` | AWS IoT Policy is missing or has incorrect client ID. | Verify that the certificate is **Active** and that `GitOpsESP32SubscriberPolicy` allows `iot:Connect` for `client/esp32-gitops-commit-light`. |
| `[JSON ERROR] Deserialization failed` | Corrupted MQTT packet or payload exceeds buffer. | Verify that `-D MQTT_MAX_PACKET_SIZE=2048` is present in `platformio.ini`. |

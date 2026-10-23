# 🏛️ System Architecture — GitOps Commit Light

Welcome to the **GitOps Commit Light** architecture document! This document outlines how code pushed to an AWS CodeCommit repository triggers an event that travels through AWS cloud services and arrives at an ESP32 microcontroller to flash an LED and update an OLED display.

> **Project Phase Notice:** We are currently in the **SOFTWARE ONLY** development phase. All hardware integration, physical wiring, and bench testing will take place in a later phase.

---

## 🧭 End-to-End Event Flow

The system operates via an asynchronous, event-driven pipeline:

```text
[ Developer: git push ]
          │
          ▼
┌──────────────────┐
│  AWS CodeCommit  │  Repository receives new commit on monitored branch
└─────────┬────────┘
          │ Event: Repository State Change
          ▼
┌──────────────────┐
│Amazon EventBridge│  Rule filters for matching branch events and routes to Lambda
└─────────┬────────┘
          │ Invocation
          ▼
┌──────────────────┐
│    AWS Lambda    │  Python function extracts commit details & builds JSON payload
└─────────┬────────┘
          │ Publish (MQTT over TLS)
          ▼
┌──────────────────┐
│   AWS IoT Core   │  MQTT Broker routes message to topic: gitops/commits
└─────────┬────────┘
          │ MQTT Subscription (Wi-Fi + TLS)
          ▼
┌──────────────────┐
│      ESP32       │  Microcontroller receives JSON payload
└─────────┬────────┘
          ├─────────────────────────┐
          ▼                         ▼
   ┌─────────────┐           ┌─────────────┐
   │  Green LED  │           │ OLED Screen │
   │ Flashes Once│           │ Shows Msg   │
   └─────────────┘           └─────────────┘
```

### Detailed Step-by-Step Flow

1. **Commit & Push (AWS CodeCommit):**
   * A developer pushes code changes to a designated branch (e.g., `main`) in the AWS CodeCommit repository.
   * AWS CodeCommit emits a cloud event indicating a repository state change (`referenceUpdated`).

2. **Event Routing (Amazon EventBridge):**
   * Amazon EventBridge acts as the central event bus.
   * An EventBridge Rule monitors CodeCommit events, filters for repository and branch matches, and triggers the backend AWS Lambda function.

3. **Event Processing & Payload Construction (AWS Lambda):**
   * A serverless Python AWS Lambda function is invoked with the EventBridge event data.
   * Lambda parses the event, retrieves commit details (such as commit ID and commit message), and constructs a standardized JSON notification payload.
   * Lambda connects to AWS IoT Core and publishes the JSON payload to the MQTT topic.

4. **Message Broker (AWS IoT Core):**
   * AWS IoT Core serves as the scalable, secure MQTT message broker.
   * It receives the published message on the topic `gitops/commits` and distributes it to authorized subscribers.

5. **Hardware Notification (ESP32 Microcontroller):**
   * The ESP32 is connected to local Wi-Fi and maintains a secure MQTT over TLS connection to AWS IoT Core.
   * When the notification payload arrives on `gitops/commits`:
     - The ESP32 parses the JSON payload.
     - The green LED flashes once to signal a new commit event.
     - The OLED screen updates with the latest commit message and branch information.

---

## 📡 MQTT Communication

* **Proposed Topic:** `gitops/commits`
* **Transport:** MQTT over TLS (Port 8883) with X.509 certificate authentication.
* **Roles:**
  * **Publisher:** AWS Lambda
  * **Broker:** AWS IoT Core
  * **Subscriber:** ESP32 Microcontroller

---

## 📦 Provisional JSON Notification Format

Lambda constructs and publishes the following provisional JSON structure to the `gitops/commits` topic:

```json
{
  "schemaVersion": 1,
  "eventId": "example-event-id",
  "repository": "gitops-commit-light",
  "branch": "main",
  "commitId": "example-commit-id",
  "message": "Example commit message",
  "timestamp": "2026-01-01T12:00:00Z"
}
```

> [!NOTE]
> **Example Data Notice:** All values above (such as `"example-event-id"`, `"example-commit-id"`, and `"2026-01-01T12:00:00Z"`) are illustrative placeholder examples and do **not** represent real event data or active identifiers.

### Payload Field Descriptions

| Field | Type | Description |
| :--- | :--- | :--- |
| `schemaVersion` | Integer | Schema version number (for backward compatibility). |
| `eventId` | String | Unique identifier for the event from EventBridge. |
| `repository` | String | Name of the source CodeCommit repository. |
| `branch` | String | Branch name where the commit was pushed. |
| `commitId` | String | Git commit hash / identifier. |
| `message` | String | Commit message text to be displayed on the OLED screen. |
| `timestamp` | String | ISO 8601 formatted timestamp when the commit occurred. |

---

## 🔌 Provisional Hardware Pin Assignments

For future hardware implementation, the following pin assignments are planned:

| Component | Pin / Signal | ESP32 GPIO | Description |
| :--- | :--- | :--- | :--- |
| **Green LED** | Anode (+) | **GPIO 18** | Connected via current-limiting series resistor (220–330 Ω) |
| **Green LED** | Cathode (−) | **GND** | Connected to common ground |
| **OLED Display (SSD1306)** | SDA (Data) | **GPIO 21** | I²C Serial Data line |
| **OLED Display (SSD1306)** | SCL (Clock) | **GPIO 22** | I²C Serial Clock line |
| **OLED Display (SSD1306)** | VCC | **3.3V** | Power rail (verify 3.3V vs 5V based on module) |
| **OLED Display (SSD1306)** | GND | **GND** | Common ground |

> [!WARNING]
> **Provisional Pin Notice:** These GPIO pin assignments are provisional proposals for software modeling and planning. **They are not yet verified against the actual physical hardware.** Physical verification will take place when the physical ESP32 development board and OLED module are connected in the hardware testing phase.

---

## 🔒 Security Best Practices

1. **No Hardcoded Credentials:** Wi-Fi credentials, private keys, and AWS credentials must never be committed to source control.
2. **Device Certificates:** The ESP32 authenticates to AWS IoT Core using X.509 client certificates with least-privilege IoT policies.
3. **Execution Roles:** The AWS Lambda function uses an IAM role with minimal permissions strictly limited to publishing to `gitops/commits` and reading the monitored CodeCommit repository.


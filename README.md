# 🟢 GitOps Commit Light

### Turn Every Git Commit into a Physical Signal!

An IoT-powered DevOps monitoring system that connects **AWS CodeCommit, AWS Lambda, AWS IoT Core, and an ESP32** to provide real-time physical notifications whenever a new commit is made to a monitored Git repository.

A green LED flashes once for every successfully processed new commit notification, while an OLED display shows the latest commit message.

---

## 📌 Project Overview

Developers frequently monitor source-code changes through Git dashboards, terminal windows, and cloud consoles. GitOps Commit Light introduces a simple, physical way to observe repository activity without constantly checking a screen.

Whenever a new commit is pushed to the monitored AWS CodeCommit repository, an event-driven workflow processes the commit information and sends a notification to an ESP32 over MQTT.

The ESP32 receives the notification, flashes a green LED, and updates the OLED display with the commit message.

**The goal:** Make cloud-based development activity visible through a small, affordable IoT device.

> **Project status:** Planning and architecture definition. Implementation, integration, and testing will be completed in subsequent development phases.

---

## 🎯 Project Objectives

* 🔔 Detect new commits in an AWS CodeCommit repository.
* ⚡ Automatically process repository events using AWS Lambda.
* ☁️ Route repository events through Amazon EventBridge.
* 📡 Deliver commit notifications using AWS IoT Core and MQTT.
* 🟢 Flash a green LED once for each successfully processed notification.
* 🖥️ Display the latest commit message on an OLED screen.
* 🔐 Implement secure device authentication and least-privilege permissions.
* 🔄 Handle duplicate notifications and network reconnections.
* 🧪 Test individual components and the complete end-to-end workflow.

---

## 🏗️ System Architecture

```text
                  DEVELOPER
                      |
                      | Git Push
                      v
             +-------------------+
             |   AWS CodeCommit  |
             |                   |
             |  Git Repository   |
             +---------+---------+
                       |
                       | Repository Event
                       v
             +-------------------+
             | Amazon EventBridge|
             |                   |
             |    Event Rule     |
             +---------+---------+
                       |
                       | Invoke
                       v
             +-------------------+
             |    AWS Lambda     |
             |                   |
             | Validate Event    |
             | Retrieve Commit   |
             | Build JSON Message|
             +---------+---------+
                       |
                       | Publish MQTT Message
                       v
             +-------------------+
             |    AWS IoT Core   |
             |                   |
             | MQTT Topic        |
             | gitops/commits    |
             +---------+---------+
                       |
                       | MQTT over TLS
                       | Wi-Fi
                       v
             +-------------------+
             |       ESP32       |
             |                   |
             | MQTT Subscriber   |
             | JSON Processing   |
             +---------+---------+
                       |
                 +-----+-----+
                 |           |
                 v           v
          +------------+ +------------+
          | Green LED  | | OLED       |
          |            | | Display    |
          | Flash Once | | Commit Text|
          +------------+ +------------+
```

### Architecture Components

| Component          | Responsibility                                          |
| ------------------ | ------------------------------------------------------- |
| AWS CodeCommit     | Stores source code and commit history                   |
| Amazon EventBridge | Detects and routes matching repository events           |
| AWS Lambda         | Processes commit events and publishes notifications     |
| AWS IoT Core       | Provides managed MQTT messaging and device connectivity |
| ESP32              | Receives notifications and controls the hardware        |
| Green LED          | Provides a visual signal for a new commit               |
| OLED display       | Displays the latest commit message and status           |

**Note:** This project uses an event-driven notification architecture. It does not currently implement automatic application deployment or a complete GitOps deployment pipeline.

---

## 🔄 How It Works

1. **Commit:** A developer modifies the source code and pushes a commit to the monitored CodeCommit branch.
2. **Event detection:** AWS generates a repository state-change event.
3. **Event routing:** Amazon EventBridge matches the event against the configured rule.
4. **Event processing:** AWS Lambda validates the event and retrieves the relevant commit information.
5. **Message creation:** Lambda constructs a JSON notification containing the repository, branch, commit ID, commit message, and timestamp.
6. **Cloud publishing:** Lambda publishes the notification to an AWS IoT Core MQTT topic.
7. **Device reception:** The ESP32 receives the message through its secure MQTT subscription.
8. **LED notification:** The green LED flashes once for the new, accepted commit notification.
9. **OLED update:** The OLED displays the latest commit message.

The workflow is designed to run automatically without requiring manual interaction with the device after setup.

---

## 🧰 Hardware Requirements

| Component               | Purpose                                                      |
| ----------------------- | ------------------------------------------------------------ |
| ESP32 development board | Main microcontroller with Wi-Fi                              |
| Green LED               | Visual commit indicator                                      |
| 220–330 Ω resistor      | Limits LED current; final value depends on component ratings |
| 0.96-inch OLED display  | Displays commit messages                                     |
| SSD1306 OLED controller | Drives the OLED display                                      |
| Breadboard              | Prototyping and circuit assembly                             |
| Jumper wires            | Electrical connections                                       |
| USB cable               | Powers and programs the ESP32                                |
| Wi-Fi connection        | Connects the ESP32 to AWS IoT Core                           |

### Recommended OLED Specifications

* Display size: 0.96 inch
* Resolution: 128 × 64 pixels
* Controller: SSD1306
* Interface: I²C

The actual board and display specifications should be verified before wiring.

---

## 🔌 Hardware Connection Plan

The following pin assignments are proposed for a compatible ESP32 DevKit board.

| Component | Pin         | ESP32 Connection                  |
| --------- | ----------- | --------------------------------- |
| Green LED | Anode (+)   | GPIO 18 through a series resistor |
| Green LED | Cathode (−) | GND                               |
| OLED      | SDA         | GPIO 21                           |
| OLED      | SCL         | GPIO 22                           |
| OLED      | GND         | GND                               |
| OLED      | VCC         | Compatible power supply           |

**Important:** Confirm the exact ESP32 board pinout and OLED module voltage requirements before making connections.

### LED Operation

```text
New Commit Notification
          |
          v
      LED ON
          |
          | Short delay
          v
      LED OFF
```

The LED should produce one short flash for each newly accepted notification, rather than remaining continuously illuminated.

---

## ☁️ AWS Services

### 1. AWS CodeCommit

Stores the Git repository and provides repository events associated with source-code changes.

### 2. Amazon EventBridge

Matches supported CodeCommit repository events and routes qualifying events to the Lambda function.

### 3. AWS Lambda

Runs the backend processing logic, retrieves commit details when necessary, prepares the notification payload, and publishes the message to AWS IoT Core.

**Recommended runtime:** Python.

### 4. AWS IoT Core

Provides managed IoT connectivity and MQTT messaging between the cloud backend and the ESP32.

### 5. AWS Identity and Access Management (IAM)

Controls which AWS operations the Lambda function and other authorized identities can perform.

### 6. AWS IoT Device Authentication

Uses device certificates and an appropriate IoT policy to authenticate the ESP32 and restrict its access to the required MQTT resources.

### 7. Amazon CloudWatch

Collects Lambda logs to support debugging, monitoring, and failure investigation.

> **Availability note:** AWS CodeCommit access is restricted for new customers. Confirm that your AWS account can create or access repositories before proceeding with this integration.

---

## 📡 MQTT Communication

The project uses MQTT, a lightweight publish-subscribe messaging protocol commonly used in IoT applications.

### Proposed MQTT Topic

```text
gitops/commits
```

### Communication Roles

| Component    | Role            |
| ------------ | --------------- |
| AWS Lambda   | MQTT publisher  |
| AWS IoT Core | MQTT broker     |
| ESP32        | MQTT subscriber |

Lambda publishes commit notifications to the configured topic, and the ESP32 subscribes to that topic to receive the messages.

The ESP32 will use MQTT over TLS with appropriate certificates and permissions.

---

## 📦 Example Notification Payload

The following JSON represents the proposed notification format.

```json
{
  "schemaVersion": 1,
  "eventId": "example-event-123",
  "repository": "gitops-commit-light",
  "branch": "main",
  "commitId": "abc123def456",
  "message": "feat: add OLED support",
  "timestamp": "2026-10-12T17:30:00Z"
}
```

All values are illustrative.

| Field           | Description                                |
| --------------- | ------------------------------------------ |
| `schemaVersion` | Identifies the notification format version |
| `eventId`       | Identifies the notification event          |
| `repository`    | Name of the source repository              |
| `branch`        | Branch associated with the commit          |
| `commitId`      | Identifier of the relevant commit          |
| `message`       | Commit message displayed on the OLED       |
| `timestamp`     | Event timestamp                            |

The cloud function and ESP32 firmware will use the same message format to ensure consistent communication.

---

## 🖥️ Example OLED Output

The display is intended to show the latest commit information.

```text
+------------------------+
| GITOPS COMMIT LIGHT    |
|------------------------|
| Branch: main           |
|------------------------|
| feat: add OLED support |
|------------------------|
| Status: RECEIVED       |
+------------------------+
```

Long commit messages will be wrapped or truncated to fit the display.

The final layout may change depending on the available display resolution and firmware implementation.

---

## 💻 Software Requirements

| Tool or Technology     | Purpose                                      |
| ---------------------- | -------------------------------------------- |
| Arduino IDE            | ESP32 firmware development                   |
| C++                    | ESP32 programming                            |
| Python                 | AWS Lambda backend                           |
| AWS Management Console | AWS resource configuration                   |
| AWS CLI                | Optional command-line management and testing |
| Git                    | Source-code version control                  |
| AWS CodeCommit         | Repository hosting                           |
| MQTT                   | Cloud-to-device messaging                    |
| JSON                   | Notification data format                     |

### Proposed ESP32 Libraries

The following libraries are candidates for implementation:

* `WiFi` — Wi-Fi connectivity.
* `WiFiClientSecure` — TLS-enabled network connections where appropriate.
* `PubSubClient` — MQTT client functionality.
* `ArduinoJson` — JSON parsing.
* `Adafruit GFX Library` — Graphics and text rendering.
* `Adafruit SSD1306` — SSD1306 OLED support.

Library compatibility and the final dependency list will be verified during implementation.

---

## 📁 Proposed Project Structure

```text
gitops-commit-light/
│
├── firmware/
│   └── esp32/
│       ├── esp32.ino
│       ├── config.example.h
│       └── README.md
│
├── backend/
│   └── lambda/
│       ├── lambda_function.py
│       └── requirements.txt
│
├── aws/
│   ├── eventbridge-rule.json
│   ├── lambda-policy.json
│   └── iot-policy.json
│
├── docs/
│   ├── architecture.md
│   ├── hardware-connections.md
│   ├── setup-guide.md
│   └── testing.md
│
├── tests/
│   ├── test_event_processing.py
│   └── test_payload_validation.py
│
├── .gitignore
└── README.md
```

This is a proposed structure. Files will be added as their corresponding modules are implemented.

Private credentials, device private keys, and account-specific secrets must not be committed to the repository.

---

## 🔐 Security Considerations

Security is a core part of the project architecture.

* Use TLS for ESP32 communication with AWS IoT Core.
* Authenticate the device using an appropriate X.509 certificate.
* Apply least-privilege IAM permissions to the Lambda execution role.
* Restrict IoT policies to the required connection and MQTT topic resources.
* Avoid hardcoding AWS access keys in source code.
* Never commit device private keys or other secrets to Git.
* Use environment variables or managed configuration for appropriate backend settings.
* Validate incoming events and MQTT messages.
* Log useful diagnostic information without exposing credentials.
* Revoke exposed credentials and certificates promptly.

The ESP32 should receive commit notifications rather than having direct access to the source repository.

---

## 🧪 Testing Strategy

Testing will be performed incrementally.

### Phase 1: Hardware Testing

* Verify ESP32 startup.
* Test LED on/off behavior.
* Test OLED initialization.
* Display sample text.
* Verify message wrapping and truncation.

### Phase 2: MQTT Testing

* Connect the ESP32 to Wi-Fi.
* Establish a secure AWS IoT Core connection.
* Subscribe to the configured MQTT topic.
* Publish a test notification.
* Verify that the ESP32 receives the message.

### Phase 3: Backend Testing

* Test Lambda event validation.
* Verify commit metadata retrieval.
* Validate JSON payload generation.
* Test MQTT publishing.
* Inspect CloudWatch logs.

### Phase 4: Integration Testing

* Push a new commit to the monitored branch.
* Verify EventBridge event routing.
* Confirm Lambda execution.
* Confirm MQTT message delivery.
* Observe the LED flash.
* Verify the OLED displays the correct commit message.

### Phase 5: Reliability Testing

* Test duplicate notification handling.
* Test Wi-Fi reconnection.
* Test MQTT reconnection.
* Test long commit messages.
* Investigate failure behavior when the device is offline.

Actual test results will be documented after the corresponding tests have been executed.

---

## ⚠️ Limitations

The initial design has several limitations that will be considered during development.

* The OLED has limited display space.
* Live MQTT notifications may be missed while the device is disconnected.
* Duplicate filtering on the ESP32 may lose its history after a restart if only RAM is used.
* Event delivery and retries depend on the AWS service configuration.
* The system depends on network connectivity and AWS service availability.
* AWS usage may incur charges.
* The CodeCommit integration depends on account access and service availability.

A future version could add persistent event recovery, a web dashboard, multiple devices, and enhanced monitoring.

---

## 🚀 Future Enhancements

Potential improvements include:

* 🔵 Different LED patterns for different event types.
* 🌿 Separate notification behavior for `main` and `develop` branches.
* 📊 A web dashboard showing commit history.
* 🔔 Notifications for pull requests and deployment events.
* 📶 A dedicated connection-status indicator.
* 💾 Persistent storage of recently processed commit IDs.
* 🔄 Recovery of notifications missed while the device is offline.
* 👥 Support for multiple repositories.
* 📈 CloudWatch metrics and alarms.
* 🐳 Integration with a larger CI/CD workflow.
* 🚀 Optional deployment-status notifications.

These are planned enhancements, not currently implemented features.

---

## 📚 Learning Outcomes

This project provides practical experience with:

* Git and source-code management.
* Event-driven cloud architecture.
* Serverless computing with AWS Lambda.
* AWS IAM and access control.
* Amazon EventBridge event routing.
* AWS IoT Core.
* MQTT publish-subscribe communication.
* TLS and certificate-based device authentication.
* ESP32 embedded programming.
* GPIO and electronic component interfacing.
* I²C communication.
* OLED display programming.
* JSON-based system integration.
* End-to-end testing and troubleshooting.

---

## 🎬 Project Demonstration

The planned demonstration will show the following sequence:

1. Open the monitored CodeCommit repository.
2. Make a source-code change.
3. Commit and push the change to the monitored branch.
4. Observe the EventBridge and Lambda processing workflow.
5. Confirm the MQTT notification reaches the ESP32.
6. Observe the green LED flash once.
7. Verify that the OLED displays the commit message.

Screenshots, hardware photographs, and a demonstration video will be added after implementation.

---

## 🛠️ Implementation Roadmap

* [x] Project concept and objectives defined.
* [x] High-level system architecture planned.
* [x] Hardware requirements identified.
* [x] MQTT topic and message format proposed.
* [x] Security and testing strategies outlined.
* [ ] Confirm CodeCommit availability.
* [ ] Assemble and test the hardware.
* [ ] Develop the ESP32 firmware.
* [ ] Configure AWS IoT Core.
* [ ] Implement the Lambda function.
* [ ] Configure the EventBridge rule.
* [ ] Integrate the complete system.
* [ ] Execute and document tests.
* [ ] Capture demonstration screenshots and video.

The checklist reflects the current planning stage and will be updated as implementation progresses.

---

## 👨‍💻 Author

**Darshan**

GitHub: [@darshan-codes-ai](https://github.com/darshan-codes-ai)

---

## 📄 License

A license has not yet been selected. Choose an appropriate open-source license before publishing the repository for reuse by others.

---

## ⭐ Support

If you find this project interesting, consider starring the repository and following its development.

**GitOps Commit Light — Because every commit deserves a signal! 🟢**
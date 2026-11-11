# ESP32 Firmware Testing Strategy

This directory describes the verification and testing methodology for the **GitOps Commit Light** ESP32 firmware module.

---

## 1. Test Matrix

| # | Test Scenario | Input / Condition | Expected Behavior |
| :- | :--- | :--- | :--- |
| **TC-01** | **Valid Schema v1 Payload** | Standard 7-field JSON on `gitops/commits` | Deserialization succeeds, commit attributes extracted, formatted Serial banner printed. |
| **TC-02** | **Missing Repository** | Payload missing `"repository"` key | Schema validation fails, logged with `[SCHEMA ERROR] Missing or empty 'repository'`, no banner printed. |
| **TC-03** | **Missing Branch** | Payload missing `"branch"` key | Schema validation fails with `[SCHEMA ERROR] Missing or empty 'branch'`, rejected. |
| **TC-04** | **Missing Commit ID** | Payload missing `"commitId"` key | Schema validation fails with `[SCHEMA ERROR] Missing or empty 'commitId'`, rejected. |
| **TC-05** | **Missing Commit Message** | Payload missing `"message"` key | Schema validation fails with `[SCHEMA ERROR] Missing or empty 'message'`, rejected. |
| **TC-05b** | **Missing Event ID** | Payload missing `"eventId"` key | Schema validation fails with `[SCHEMA ERROR] Missing or empty 'eventId'`, rejected. |
| **TC-05c** | **Missing Timestamp** | Payload missing `"timestamp"` key | Schema validation fails with `[SCHEMA ERROR] Missing or empty 'timestamp'`, rejected. |
| **TC-06** | **Malformed JSON** | Truncated or syntax-broken JSON (e.g., `{"schemaVersion": 1, ...`) | `deserializeJson` returns error (e.g. `IncompleteInput` or `InvalidInput`), error logged, no crash. |
| **TC-07** | **Unsupported Schema Version** | `"schemaVersion": 2` | Schema check fails with `[SCHEMA ERROR] Unsupported schema version: 2 (expected 1)`, rejected. |
| **TC-08** | **Long Commit Message** | Message containing 800+ characters | Safely deserialized within 2048-byte buffer without memory corruption or truncation. |
| **TC-09** | **Wi-Fi Connection Loss** | Wi-Fi router reboot or AP disconnect | `WiFiManager` detects disconnect, MQTT transitions to disconnected, periodic non-blocking reconnect attempts every 5s. |
| **TC-10** | **Wi-Fi Recovery** | Wi-Fi network restored | `WiFiManager` reconnects, retrieves IP, `MqttManager` automatically reconnects and re-subscribes to `gitops/commits`. |
| **TC-11** | **MQTT Broker Disconnect** | TCP RST or keep-alive timeout | `MqttManager` prints MQTT state transition, retries connection every 5s until reconnected. |
| **TC-12** | **Unexpected Topic Delivery** | Message received on `gitops/other` | Discarded with `[MQTT RX WARNING] Unexpected topic. Discarding.` |

---

## 2. Host-Side Validation (Offline Python Mirror)

Because the Schema v1 contract is identical between the Python Lambda backend and the C++ firmware, the 150 offline unit tests in the project root verify all payload variations:

```bash
# Run from repository root
python -m unittest discover tests -v
```

Specifically:
- `tests/test_github_webhook.py`: Verifies Schema v1 payload construction.
- `tests/test_production_adapters.py`: Verifies IoT Core message delivery formatting.
- `tests/test_event_processing.py`: Verifies event attribute extraction.

---

## 3. Live Cloud & Hardware-in-the-Loop Testing

When physical ESP32 hardware is connected:

1. **Verify Wi-Fi & MQTT Handshake:**
   Open the Serial Monitor at 115200 baud to observe the startup sequence:
   ```text
   [WIFI] Status: CONNECTED
   [WIFI] Assigned IP : 192.168.1.xxx
   [MQTT] TLS Handshake & Authentication SUCCESSFUL.
   [MQTT] Subscribed to topic: gitops/commits (QoS 0)
   ```

2. **Simulate Commit via AWS IoT Core MQTT Test Client:**
   In the AWS Management Console:
   - Navigate to **AWS IoT Core -> Test -> MQTT test client**.
   - Select **Publish to a topic**.
   - Topic name: `gitops/commits`
   - Message payload:
     ```json
     {
       "schemaVersion": 1,
       "eventId": "test-manual-delivery-001",
       "repository": "GitOps-Commit-Light",
       "branch": "main",
       "commitId": "1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b",
       "message": "test: verified physical ESP32 live MQTT subscriber",
       "timestamp": "2026-11-11T12:00:00Z"
     }
     ```
   - Click **Publish**.
   - Observe the formatted banner in your ESP32 Serial Monitor.

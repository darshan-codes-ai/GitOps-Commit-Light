#include "commit_handler.h"

CommitHandler::CommitHandler()
    : _processedCount(0),
      _callback(nullptr) {
    _lastEvent.isValid = false;
}

bool CommitHandler::handlePayload(const byte* payload, unsigned int length) {
    if (!payload || length == 0) {
        Serial.println(F("[COMMIT HANDLER ERROR] Received empty payload."));
        return false;
    }

    // Safety guard against oversized payloads
    if (length > 2000) {
        Serial.printf("[COMMIT HANDLER ERROR] Payload length (%u bytes) exceeds safe processing buffer (2000 bytes).\n", length);
        return false;
    }

    // Compatible with both ArduinoJson v6 and v7
#if ARDUINOJSON_VERSION_MAJOR >= 7
    JsonDocument doc;
#else
    StaticJsonDocument<2048> doc;
#endif

    DeserializationError error = deserializeJson(doc, payload, length);

    if (error) {
        Serial.print(F("[JSON ERROR] Deserialization failed: "));
        Serial.println(error.c_str());
        return false;
    }

    // 1. Validate schemaVersion
    if (!doc.containsKey("schemaVersion")) {
        Serial.println(F("[SCHEMA ERROR] Missing 'schemaVersion' in notification payload."));
        return false;
    }

    int version = doc["schemaVersion"].as<int>();
    if (version != 1) {
        Serial.printf("[SCHEMA ERROR] Unsupported schema version: %d (expected 1).\n", version);
        return false;
    }

    // 2. Validate all required string fields
    const char* rawEventId = doc["eventId"];
    const char* rawRepo    = doc["repository"];
    const char* rawBranch  = doc["branch"];
    const char* rawCommit  = doc["commitId"];
    const char* rawMsg     = doc["message"];
    const char* rawTime    = doc["timestamp"];

    if (!rawEventId || strlen(rawEventId) == 0) {
        Serial.println(F("[SCHEMA ERROR] Missing or empty 'eventId' field."));
        return false;
    }

    if (!rawRepo || strlen(rawRepo) == 0) {
        Serial.println(F("[SCHEMA ERROR] Missing or empty 'repository' field."));
        return false;
    }

    if (!rawBranch || strlen(rawBranch) == 0) {
        Serial.println(F("[SCHEMA ERROR] Missing or empty 'branch' field."));
        return false;
    }

    if (!rawCommit || strlen(rawCommit) == 0) {
        Serial.println(F("[SCHEMA ERROR] Missing or empty 'commitId' field."));
        return false;
    }

    if (!rawMsg || strlen(rawMsg) == 0) {
        Serial.println(F("[SCHEMA ERROR] Missing or empty 'message' field."));
        return false;
    }

    if (!rawTime || strlen(rawTime) == 0) {
        Serial.println(F("[SCHEMA ERROR] Missing or empty 'timestamp' field."));
        return false;
    }

    // 3. Construct validated CommitEvent
    CommitEvent event;
    event.schemaVersion = version;
    event.eventId       = String(rawEventId);
    event.repository    = String(rawRepo);
    event.branch        = String(rawBranch);
    event.commitId      = String(rawCommit);
    event.message       = String(rawMsg);
    event.timestamp     = String(rawTime);
    event.isValid       = true;

    _lastEvent = event;
    _processedCount++;

    // 4. Output structured notification banner to Serial Monitor
    _printNotificationBanner(event);

    // 5. Trigger optional hardware extension callback (if registered)
    if (_callback) {
        _callback(event);
    }

    return true;
}

void CommitHandler::_printNotificationBanner(const CommitEvent& event) {
    Serial.println();
    Serial.println(F("========================================"));
    Serial.println(F("          GITOPS COMMIT LIGHT"));
    Serial.println(F("========================================"));
    Serial.println();
    Serial.println(F("[NEW COMMIT RECEIVED]"));
    Serial.println();
    Serial.printf("Repository : %s\n", event.repository.c_str());
    Serial.printf("Branch     : %s\n", event.branch.c_str());
    Serial.printf("Commit ID  : %s\n", event.commitId.c_str());
    Serial.printf("Message    : %s\n", event.message.c_str());
    Serial.printf("Timestamp  : %s\n", event.timestamp.c_str());
    Serial.printf("Event ID   : %s\n", event.eventId.c_str());
    Serial.println();
    Serial.println(F("========================================"));
    Serial.println();
}

const CommitEvent& CommitHandler::getLastEvent() const {
    return _lastEvent;
}

unsigned long CommitHandler::getProcessedCount() const {
    return _processedCount;
}

void CommitHandler::setCallback(CommitNotificationCallback callback) {
    _callback = callback;
}

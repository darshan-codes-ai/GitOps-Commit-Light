/**
 * Realistic local simulation engine for GitOps Commit Light.
 * Accurately models the exact validation and Schema v1 payload construction
 * performed by backend/lambda/lambda_function.py.
 */

import { SCHEMA_VERSION, DEFAULT_MQTT_TOPIC, DEFAULT_MQTT_QOS, DEFAULT_MONITORED_BRANCH, EVENT_STATUS } from '../types';

/**
 * Generate a random UUID v4 string for simulated delivery IDs.
 */
function generateUUID() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

/**
 * Generate random 40-character hex commit SHA.
 */
export function generateCommitSha() {
  const chars = '0123456789abcdef';
  let sha = '';
  for (let i = 0; i < 40; i++) {
    sha += chars[Math.floor(Math.random() * chars.length)];
  }
  return sha;
}

export const simulatorService = {
  /**
   * Simulate GitHub Push Event processing through the full pipeline.
   *
   * @param {Object} input - Form fields from the simulator UI
   * @returns {Object} Complete simulated event record with timeline and payloads
   */
  simulatePushEvent: (input) => {
    const {
      owner = 'darshan-codes-ai',
      repoName = 'GitOps-Commit-Light',
      branch = 'main',
      commitSha = generateCommitSha(),
      commitMessage = 'feat: update infrastructure configuration',
      authorName = 'Darshan Kumar',
      authorEmail = 'darshan@example.com',
      changedFiles = ['README.md'],
      isDeleted = false,
      isMalformed = false,
      monitoredBranch = DEFAULT_MONITORED_BRANCH,
    } = input;

    const eventId = generateUUID();
    const timestamp = new Date().toISOString();
    const cleanRepo = (repoName || '').trim();
    const cleanBranch = (branch || '').trim();
    const cleanSha = (commitSha || '').trim();
    const cleanMessage = (commitMessage || '').trim();
    const fullName = `${owner.trim()}/${cleanRepo}`;

    const timeline = [];

    // Stage 1: Webhook Ingestion
    timeline.push({
      step: '1. Webhook Ingestion',
      service: 'API Gateway v2 HTTP API',
      status: 'completed',
      description: `POST /webhook/github received with X-GitHub-Delivery: ${eventId}`
    });

    // Stage 2: HMAC-SHA256 Signature Verification
    if (isMalformed) {
      timeline.push({
        step: '2. Signature Verification',
        service: 'AWS Lambda (Python 3.12)',
        status: 'failed',
        description: 'HMAC-SHA256 mismatch: Malformed payload or invalid header structure'
      });
      timeline.push({
        step: '3. Pipeline Processing',
        service: 'Commit Parser',
        status: 'skipped',
        description: 'Halted: Request rejected with HTTP 400 Bad Request'
      });
      timeline.push({
        step: '4. MQTT Dispatch',
        service: 'AWS IoT Core Data Plane',
        status: 'skipped',
        description: 'Zero MQTT publish calls executed'
      });

      return {
        eventId,
        source: 'local-simulator',
        eventType: 'push',
        repository: { owner: owner.trim(), name: cleanRepo, fullName },
        branch: cleanBranch,
        commit: {
          sha: cleanSha,
          message: cleanMessage,
          author: { name: authorName.trim(), email: authorEmail.trim() },
          changedFiles
        },
        timestamp,
        status: EVENT_STATUS.FAILED,
        statusReason: 'Validation Error: Payload is malformed or missing required schema properties (HTTP 400).',
        delivery: {
          mode: 'local',
          awsDelivered: false,
          simulatedTopic: null,
          qos: null
        },
        mqttPayload: null,
        githubPayload: { error: 'Malformed JSON payload structure' },
        timeline
      };
    }

    timeline.push({
      step: '2. Signature Verification',
      service: 'AWS Lambda (Python 3.12)',
      status: 'completed',
      description: 'HMAC-SHA256 constant-time digest verified against Secrets Manager token'
    });

    // Stage 3: Branch & Deletion Filtering
    if (isDeleted || cleanSha === '0000000000000000000000000000000000000000') {
      timeline.push({
        step: '3. Event Filtering',
        service: 'AWS Lambda (Python 3.12)',
        status: 'ignored',
        description: `Branch deletion event detected (deleted=true, after=0000...0000)`
      });
      timeline.push({
        step: '4. Schema v1 Extraction',
        service: 'Commit Parser',
        status: 'skipped',
        description: 'Skipped for deleted ref (no commit to display)'
      });
      timeline.push({
        step: '5. MQTT Dispatch',
        service: 'AWS IoT Core',
        status: 'skipped',
        description: 'Filtered: Zero MQTT publication'
      });

      return {
        eventId,
        source: 'local-simulator',
        eventType: 'push',
        repository: { owner: owner.trim(), name: cleanRepo, fullName },
        branch: cleanBranch,
        commit: {
          sha: '0000000000000000000000000000000000000000',
          message: '(Branch deletion)',
          author: { name: authorName.trim(), email: authorEmail.trim() },
          changedFiles: []
        },
        timestamp,
        status: EVENT_STATUS.IGNORED,
        statusReason: 'Ignored: Branch deletion event safely acknowledged without publishing to MQTT.',
        delivery: {
          mode: 'local',
          awsDelivered: false,
          simulatedTopic: null,
          qos: null
        },
        mqttPayload: null,
        githubPayload: {
          ref: `refs/heads/${cleanBranch}`,
          deleted: true,
          before: generateCommitSha(),
          after: '0000000000000000000000000000000000000000',
          repository: { name: cleanRepo, full_name: fullName, owner: { name: owner.trim() } },
          head_commit: null
        },
        timeline
      };
    }

    if (cleanBranch !== monitoredBranch) {
      timeline.push({
        step: '3. Branch Filtering',
        service: 'AWS Lambda (Python 3.12)',
        status: 'ignored',
        description: `Branch '${cleanBranch}' does not match monitored branch '${monitoredBranch}'`
      });
      timeline.push({
        step: '4. Schema v1 Extraction',
        service: 'Commit Parser',
        status: 'skipped',
        description: 'Skipped for non-monitored branch'
      });
      timeline.push({
        step: '5. MQTT Dispatch',
        service: 'AWS IoT Core',
        status: 'skipped',
        description: 'Filtered: Zero MQTT publication'
      });

      return {
        eventId,
        source: 'local-simulator',
        eventType: 'push',
        repository: { owner: owner.trim(), name: cleanRepo, fullName },
        branch: cleanBranch,
        commit: {
          sha: cleanSha,
          message: cleanMessage,
          author: { name: authorName.trim(), email: authorEmail.trim() },
          changedFiles
        },
        timestamp,
        status: EVENT_STATUS.IGNORED,
        statusReason: `Ignored: Push was on branch '${cleanBranch}'. Only monitored branch '${monitoredBranch}' triggers notifications.`,
        delivery: {
          mode: 'local',
          awsDelivered: false,
          simulatedTopic: null,
          qos: null
        },
        mqttPayload: null,
        githubPayload: {
          ref: `refs/heads/${cleanBranch}`,
          deleted: false,
          before: generateCommitSha(),
          after: cleanSha,
          repository: { name: cleanRepo, full_name: fullName, owner: { name: owner.trim() } },
          head_commit: {
            id: cleanSha,
            message: cleanMessage,
            timestamp,
            author: { name: authorName.trim(), email: authorEmail.trim() },
            modified: changedFiles
          }
        },
        timeline
      };
    }

    // Stage 4: Metadata Extraction & Schema v1 Construction
    timeline.push({
      step: '3. Branch Filtering',
      service: 'AWS Lambda (Python 3.12)',
      status: 'completed',
      description: `Push confirmed on monitored branch '${monitoredBranch}'`
    });

    timeline.push({
      step: '4. Schema v1 Extraction',
      service: 'Commit Parser',
      status: 'completed',
      description: `Constructed Schema v1 payload: commitId=${cleanSha.substring(0, 7)}, message="${cleanMessage.substring(0, 30)}..."`
    });

    // Stage 5: Simulated MQTT Publication
    timeline.push({
      step: '5. MQTT Dispatch (Simulated)',
      service: 'AWS IoT Core Data Plane',
      status: 'completed',
      description: `Dispatched JSON payload to topic '${DEFAULT_MQTT_TOPIC}' with QoS ${DEFAULT_MQTT_QOS} [SIMULATED LOCAL ONLY]`
    });

    const mqttPayload = {
      schemaVersion: SCHEMA_VERSION,
      eventId,
      repository: cleanRepo,
      branch: cleanBranch,
      commitId: cleanSha,
      message: cleanMessage,
      timestamp
    };

    const githubPayload = {
      ref: `refs/heads/${cleanBranch}`,
      before: generateCommitSha(),
      after: cleanSha,
      repository: {
        name: cleanRepo,
        full_name: fullName,
        owner: { name: owner.trim() }
      },
      head_commit: {
        id: cleanSha,
        message: cleanMessage,
        timestamp,
        author: { name: authorName.trim(), email: authorEmail.trim() },
        modified: changedFiles
      }
    };

    return {
      eventId,
      source: 'local-simulator',
      eventType: 'push',
      repository: { owner: owner.trim(), name: cleanRepo, fullName },
      branch: cleanBranch,
      commit: {
        sha: cleanSha,
        message: cleanMessage,
        author: { name: authorName.trim(), email: authorEmail.trim() },
        changedFiles
      },
      timestamp,
      status: EVENT_STATUS.SUCCESS,
      statusReason: `Push to '${cleanBranch}' processed successfully. Schema v1 published to simulated topic '${DEFAULT_MQTT_TOPIC}'.`,
      delivery: {
        mode: 'local',
        awsDelivered: false,
        simulatedTopic: DEFAULT_MQTT_TOPIC,
        qos: DEFAULT_MQTT_QOS
      },
      mqttPayload,
      githubPayload,
      timeline
    };
  }
};


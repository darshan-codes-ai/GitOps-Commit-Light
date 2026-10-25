/**
 * Constants and Schema specifications for GitOps Commit Light
 */

export const SCHEMA_VERSION = 1;
export const DEFAULT_MQTT_TOPIC = 'gitops/commits';
export const MQTT_TOPIC = DEFAULT_MQTT_TOPIC;
export const DEFAULT_MQTT_QOS = 0;
export const MQTT_QOS = DEFAULT_MQTT_QOS;
export const DEFAULT_MONITORED_BRANCH = 'main';
export const MONITORED_BRANCH = DEFAULT_MONITORED_BRANCH;

export const SIMULATION_BANNER = 'LOCAL SIMULATION MODE — AWS NOT CONNECTED';
export const SIMULATION_BANNER_TEXT = SIMULATION_BANNER;

export const EVENT_STATUS = {
  SUCCESS: 'success',
  IGNORED: 'ignored',
  FAILED: 'failed',
};

export const PIPELINE_STAGES = [
  { id: 'webhook', name: 'GitHub Webhook (POST)', service: 'GitHub' },
  { id: 'apigateway', name: 'API Gateway v2 HTTP API', service: 'Amazon API Gateway' },
  { id: 'lambda', name: 'Lambda Event Processor', service: 'AWS Lambda (Python 3.12)' },
  { id: 'extract', name: 'Schema v1 Extraction', service: 'Commit Parser' },
  { id: 'mqtt', name: 'AWS IoT Core Data Plane', service: 'AWS IoT Core (gitops/commits)' },
  { id: 'esp32', name: 'ESP32 Commit Light Indicator', service: 'Physical Hardware / Wokwi' },
];


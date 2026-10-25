/**
 * Fictional seed data for local demonstration of GitOps Commit Light.
 * All entries are strictly simulated with fictitious metadata.
 */

export const INITIAL_SEED_EVENTS = [
  {
    eventId: "e1a49802-9bc5-4720-91c3-48e02d849b01",
    source: "local-simulator",
    eventType: "push",
    repository: {
      owner: "darshan-codes-ai",
      name: "GitOps-Commit-Light",
      fullName: "darshan-codes-ai/GitOps-Commit-Light"
    },
    branch: "main",
    commit: {
      sha: "7f4c9a1d8b2e3f5a0c6e9d8b1a4c7f0e2d5b8a1c",
      message: "feat: add Kubernetes ingress and TLS termination manifests",
      author: {
        name: "Darshan Kumar",
        email: "darshan@example.com"
      },
      changedFiles: [
        "k8s/ingress.yaml",
        "k8s/service.yaml",
        "docs/deployment-guide.md"
      ]
    },
    timestamp: "2026-10-25T11:42:15Z",
    status: "success",
    statusReason: "Push event to monitored branch 'main' successfully processed and published to simulated MQTT topic.",
    delivery: {
      mode: "local",
      awsDelivered: false,
      simulatedTopic: "gitops/commits",
      qos: 0
    },
    mqttPayload: {
      schemaVersion: 1,
      eventId: "e1a49802-9bc5-4720-91c3-48e02d849b01",
      repository: "GitOps-Commit-Light",
      branch: "main",
      commitId: "7f4c9a1d8b2e3f5a0c6e9d8b1a4c7f0e2d5b8a1c",
      message: "feat: add Kubernetes ingress and TLS termination manifests",
      timestamp: "2026-10-25T11:42:15Z"
    },
    githubPayload: {
      ref: "refs/heads/main",
      before: "3a1b2c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b",
      after: "7f4c9a1d8b2e3f5a0c6e9d8b1a4c7f0e2d5b8a1c",
      repository: {
        name: "GitOps-Commit-Light",
        full_name: "darshan-codes-ai/GitOps-Commit-Light",
        owner: { name: "darshan-codes-ai" }
      },
      head_commit: {
        id: "7f4c9a1d8b2e3f5a0c6e9d8b1a4c7f0e2d5b8a1c",
        message: "feat: add Kubernetes ingress and TLS termination manifests",
        timestamp: "2026-10-25T11:42:15Z",
        author: { name: "Darshan Kumar", email: "darshan@example.com" }
      }
    },
    timeline: [
      { step: "Webhook Ingestion", status: "completed", description: "GitHub push webhook received by API Gateway proxy route POST /webhook/github" },
      { step: "Signature Verification", status: "completed", description: "HMAC-SHA256 signature verified against Secrets Manager secret" },
      { step: "Branch Filtering", status: "completed", description: "Ref 'refs/heads/main' matches monitored branch 'main'" },
      { step: "Payload Extraction", status: "completed", description: "Extracted commit metadata conforming to Schema v1 specification" },
      { step: "MQTT Dispatch (Simulated)", status: "completed", description: "Dispatched payload to topic 'gitops/commits' (QoS 0) [SIMULATED LOCAL ONLY]" }
    ]
  },
  {
    eventId: "b890f12c-4731-4829-81a2-938bdf018241",
    source: "local-simulator",
    eventType: "push",
    repository: {
      owner: "darshan-codes-ai",
      name: "GitOps-Commit-Light",
      fullName: "darshan-codes-ai/GitOps-Commit-Light"
    },
    branch: "main",
    commit: {
      sha: "4b2e8d1a9f0c3e7b5a8d2c6f1a0e9b4d8c7a2f5e",
      message: "fix: resolve memory leak in warm Lambda secret cache container",
      author: {
        name: "DevOps Engineer",
        email: "devops@example.com"
      },
      changedFiles: [
        "backend/lambda/lambda_function.py",
        "tests/test_github_webhook.py"
      ]
    },
    timestamp: "2026-10-25T09:18:30Z",
    status: "success",
    statusReason: "Commit to 'main' processed successfully. Schema v1 published to simulated MQTT broker.",
    delivery: {
      mode: "local",
      awsDelivered: false,
      simulatedTopic: "gitops/commits",
      qos: 0
    },
    mqttPayload: {
      schemaVersion: 1,
      eventId: "b890f12c-4731-4829-81a2-938bdf018241",
      repository: "GitOps-Commit-Light",
      branch: "main",
      commitId: "4b2e8d1a9f0c3e7b5a8d2c6f1a0e9b4d8c7a2f5e",
      message: "fix: resolve memory leak in warm Lambda secret cache container",
      timestamp: "2026-10-25T09:18:30Z"
    },
    githubPayload: {
      ref: "refs/heads/main",
      before: "7f4c9a1d8b2e3f5a0c6e9d8b1a4c7f0e2d5b8a1c",
      after: "4b2e8d1a9f0c3e7b5a8d2c6f1a0e9b4d8c7a2f5e",
      repository: {
        name: "GitOps-Commit-Light",
        full_name: "darshan-codes-ai/GitOps-Commit-Light",
        owner: { name: "darshan-codes-ai" }
      },
      head_commit: {
        id: "4b2e8d1a9f0c3e7b5a8d2c6f1a0e9b4d8c7a2f5e",
        message: "fix: resolve memory leak in warm Lambda secret cache container",
        timestamp: "2026-10-25T09:18:30Z",
        author: { name: "DevOps Engineer", email: "devops@example.com" }
      }
    },
    timeline: [
      { step: "Webhook Ingestion", status: "completed", description: "Received push event for main branch" },
      { step: "Signature Verification", status: "completed", description: "HMAC digest validated" },
      { step: "Branch Filtering", status: "completed", description: "Branch main matches target branch" },
      { step: "Payload Extraction", status: "completed", description: "Schema v1 payload prepared" },
      { step: "MQTT Dispatch (Simulated)", status: "completed", description: "Simulated MQTT broadcast to gitops/commits" }
    ]
  },
  {
    eventId: "92d04a6e-71c4-4b51-829d-03487c5e8912",
    source: "local-simulator",
    eventType: "push",
    repository: {
      owner: "darshan-codes-ai",
      name: "Infrastructure-Live",
      fullName: "darshan-codes-ai/Infrastructure-Live"
    },
    branch: "feature/canary-traffic-split",
    commit: {
      sha: "9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b",
      message: "wip: add weighted routing to alb ingress controller",
      author: {
        name: "Alex Cloud",
        email: "alex@example.com"
      },
      changedFiles: [
        "terraform/ingress.tf"
      ]
    },
    timestamp: "2026-10-25T08:05:10Z",
    status: "ignored",
    statusReason: "Ignored: Branch 'feature/canary-traffic-split' is not the monitored branch 'main'. Zero MQTT publication.",
    delivery: {
      mode: "local",
      awsDelivered: false,
      simulatedTopic: null,
      qos: null
    },
    mqttPayload: null,
    githubPayload: {
      ref: "refs/heads/feature/canary-traffic-split",
      before: "0000000000000000000000000000000000000000",
      after: "9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b",
      repository: {
        name: "Infrastructure-Live",
        full_name: "darshan-codes-ai/Infrastructure-Live",
        owner: { name: "darshan-codes-ai" }
      },
      head_commit: {
        id: "9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b",
        message: "wip: add weighted routing to alb ingress controller",
        timestamp: "2026-10-25T08:05:10Z",
        author: { name: "Alex Cloud", email: "alex@example.com" }
      }
    },
    timeline: [
      { step: "Webhook Ingestion", status: "completed", description: "Webhook accepted with valid delivery ID" },
      { step: "Signature Verification", status: "completed", description: "HMAC signature verified" },
      { step: "Branch Filtering", status: "ignored", description: "Branch 'feature/canary-traffic-split' does not match monitored branch 'main'" },
      { step: "Payload Extraction", status: "skipped", description: "Skipped due to non-monitored branch" },
      { step: "MQTT Dispatch (Simulated)", status: "skipped", description: "Skipped - zero MQTT messages published" }
    ]
  },
  {
    eventId: "43a29b01-5e82-416b-a2c7-74892c5d61e3",
    source: "local-simulator",
    eventType: "push",
    repository: {
      owner: "darshan-codes-ai",
      name: "GitOps-Commit-Light",
      fullName: "darshan-codes-ai/GitOps-Commit-Light"
    },
    branch: "main",
    commit: {
      sha: "c3d5e7f9a1b3c5e7f9a1b3c5e7f9a1b3c5e7f9a1",
      message: "docs: document Phase 1 local simulation and architecture boundaries",
      author: {
        name: "Darshan Kumar",
        email: "darshan@example.com"
      },
      changedFiles: [
        "README.md",
        "docs/architecture.md"
      ]
    },
    timestamp: "2026-10-24T18:30:00Z",
    status: "success",
    statusReason: "Documentation commit to 'main' processed successfully and published to gitops/commits.",
    delivery: {
      mode: "local",
      awsDelivered: false,
      simulatedTopic: "gitops/commits",
      qos: 0
    },
    mqttPayload: {
      schemaVersion: 1,
      eventId: "43a29b01-5e82-416b-a2c7-74892c5d61e3",
      repository: "GitOps-Commit-Light",
      branch: "main",
      commitId: "c3d5e7f9a1b3c5e7f9a1b3c5e7f9a1b3c5e7f9a1",
      message: "docs: document Phase 1 local simulation and architecture boundaries",
      timestamp: "2026-10-24T18:30:00Z"
    },
    githubPayload: {
      ref: "refs/heads/main",
      before: "4b2e8d1a9f0c3e7b5a8d2c6f1a0e9b4d8c7a2f5e",
      after: "c3d5e7f9a1b3c5e7f9a1b3c5e7f9a1b3c5e7f9a1",
      repository: {
        name: "GitOps-Commit-Light",
        full_name: "darshan-codes-ai/GitOps-Commit-Light",
        owner: { name: "darshan-codes-ai" }
      },
      head_commit: {
        id: "c3d5e7f9a1b3c5e7f9a1b3c5e7f9a1b3c5e7f9a1",
        message: "docs: document Phase 1 local simulation and architecture boundaries",
        timestamp: "2026-10-24T18:30:00Z",
        author: { name: "Darshan Kumar", email: "darshan@example.com" }
      }
    },
    timeline: [
      { step: "Webhook Ingestion", status: "completed", description: "Valid delivery ID and payload accepted" },
      { step: "Signature Verification", status: "completed", description: "HMAC signature verified" },
      { step: "Branch Filtering", status: "completed", description: "Matches monitored branch 'main'" },
      { step: "Payload Extraction", status: "completed", description: "Extracted commit title and author" },
      { step: "MQTT Dispatch (Simulated)", status: "completed", description: "Published Schema v1 to gitops/commits" }
    ]
  },
  {
    eventId: "5f891a23-bc42-491a-9820-21a48c7e90b2",
    source: "local-simulator",
    eventType: "push",
    repository: {
      owner: "darshan-codes-ai",
      name: "Microservices-Mesh",
      fullName: "darshan-codes-ai/Microservices-Mesh"
    },
    branch: "main",
    commit: {
      sha: "0000000000000000000000000000000000000000",
      message: "(Branch deletion - no commit)",
      author: {
        name: "Security Bot",
        email: "bot@example.com"
      },
      changedFiles: []
    },
    timestamp: "2026-10-24T14:15:22Z",
    status: "ignored",
    statusReason: "Ignored: Push event indicates branch deletion (after=0000...0000). Safely filtered without MQTT publishing.",
    delivery: {
      mode: "local",
      awsDelivered: false,
      simulatedTopic: null,
      qos: null
    },
    mqttPayload: null,
    githubPayload: {
      ref: "refs/heads/temp-hotfix",
      deleted: true,
      before: "1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b",
      after: "0000000000000000000000000000000000000000",
      repository: {
        name: "Microservices-Mesh",
        full_name: "darshan-codes-ai/Microservices-Mesh",
        owner: { name: "darshan-codes-ai" }
      },
      head_commit: null
    },
    timeline: [
      { step: "Webhook Ingestion", status: "completed", description: "Received push event" },
      { step: "Signature Verification", status: "completed", description: "HMAC signature verified" },
      { step: "Branch Filtering", status: "ignored", description: "Branch deletion detected (deleted=true, after=all zeros)" },
      { step: "Payload Extraction", status: "skipped", description: "Skipped" },
      { step: "MQTT Dispatch (Simulated)", status: "skipped", description: "Zero MQTT publish calls" }
    ]
  }
];


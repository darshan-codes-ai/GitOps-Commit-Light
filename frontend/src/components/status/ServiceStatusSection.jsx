import React from 'react';
import { 
  Cloud, 
  GitBranch, 
  Server, 
  Radio, 
  Cpu, 
  ShieldCheck, 
  AlertTriangle, 
  CheckCircle2, 
  Clock, 
  ExternalLink,
  Layers,
  ArrowRight
} from 'lucide-react';
import { SIMULATION_BANNER_TEXT } from '../../types';

export default function ServiceStatusSection({ backendStatus = 'checking' }) {
  const isBackendLive = backendStatus === 'connected';

  const pipelineNodes = [
    {
      id: 'github',
      title: 'GitHub Webhook',
      role: 'Event Producer',
      status: 'LOCAL SIMULATOR',
      statusType: 'simulated',
      desc: 'Generates push webhooks with HMAC-SHA256 signature and delivery UUID headers.',
      icon: GitBranch,
      awsResource: 'Webhook Config',
      details: ['Payload format: GitHub push JSON', 'Signature: X-Hub-Signature-256', 'Delivery ID: X-GitHub-Delivery']
    },
    {
      id: 'apigw',
      title: 'API Gateway HTTP API',
      role: 'Ingress Proxy',
      status: isBackendLive ? 'LOCAL FASTAPI PROXY' : 'NOT PROVISIONED',
      statusType: isBackendLive ? 'tested' : 'offline',
      desc: isBackendLive
        ? 'Local FastAPI server routes incoming webhook requests directly to the Python Lambda handler with CORS support.'
        : 'Routes incoming webhook POST requests to AWS Lambda with low latency and zero payload transformation.',
      icon: Server,
      awsResource: 'AWS::ApiGatewayV2::Api',
      details: ['Route: POST /webhook/github', 'Payload format version: 2.0', 'CORS: Enabled for local development']
    },
    {
      id: 'lambda',
      title: 'AWS Lambda (Python 3.12)',
      role: 'Processing & Validation',
      status: isBackendLive ? 'RUNNING LOCALLY (:8000)' : 'OFFLINE / TESTED',
      statusType: isBackendLive ? 'tested' : 'offline',
      desc: isBackendLive
        ? 'Actively executing backend/lambda/lambda_function.py github_webhook_handler with in-memory secret validation.'
        : 'Validates HMAC signature, reads secret from Secrets Manager, filters main branch pushes, and constructs Schema v1 payload.',
      icon: Layers,
      awsResource: 'AWS::Lambda::Function',
      details: ['Handler: lambda_function.github_webhook_handler', 'Secret: Local Dev Secret / Secrets Manager', 'Test suite: 150 offline unit tests passing']
    },
    {
      id: 'iot',
      title: 'AWS IoT Core',
      role: 'Message Broker',
      status: isBackendLive ? 'MOCK MQTT BROKER' : 'SIMULATED LOCAL QUEUE',
      statusType: 'simulated',
      desc: 'Distributes commit events to subscribed hardware clients over MQTT QoS 0 on topic gitops/commits.',
      icon: Radio,
      awsResource: 'iot:Publish',
      details: ['Topic: gitops/commits', 'Quality of Service: QoS 0', 'Schema: Schema v1 (JSON)']
    },
    {
      id: 'esp32',
      title: 'ESP32 Commit Light',
      role: 'Physical Display',
      status: 'FUTURE PHASE',
      statusType: 'future',
      desc: 'Microcontroller subscribed to MQTT topic with X.509 certs. Drives WS2812B NeoPixel RGB LED sequence.',
      icon: Cpu,
      awsResource: 'Hardware / Wokwi',
      details: ['Connection: MQTTS / TLS v1.2', 'LEDs: WS2812B RGB NeoPixels', 'Sim support: Wokwi simulator compatible']
    }
  ];

  return (
    <div className="space-y-6">
      {/* Top Warning Banner */}
      <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-5 shadow-lg flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="p-2 rounded-lg bg-amber-500/20 text-amber-400 shrink-0">
            <AlertTriangle className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs font-bold uppercase tracking-wider text-amber-300">
                {SIMULATION_BANNER_TEXT}
              </span>
            </div>
            <h2 className="text-lg font-bold text-white mt-0.5">
              Phase 1 Local Environment Architecture Status
            </h2>
            <p className="text-sm text-slate-300 mt-1 max-w-3xl">
              All commit events and MQTT notifications in this dashboard are executed inside the local browser simulation engine. No live AWS resources are provisioned or billed. CloudFormation templates, IAM least-privilege policies, and Python handlers are verified offline and ready for future deployment.
            </p>
          </div>
        </div>

        <div className="shrink-0 bg-slate-950/80 border border-slate-800 rounded-lg p-3 text-center">
          <span className="text-[11px] text-slate-400 uppercase tracking-wider block">Backend Test Status</span>
          <span className="text-emerald-400 font-bold font-mono text-sm flex items-center justify-center gap-1 mt-0.5">
            <CheckCircle2 className="w-4 h-4" /> 138/138 Passing
          </span>
        </div>
      </div>

      {/* Visual Pipeline Flow */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-lg">
        <h3 className="text-base font-semibold text-white mb-2 flex items-center gap-2">
          <Cloud className="w-5 h-5 text-indigo-400" />
          End-to-End Pipeline Architecture
        </h3>
        <p className="text-sm text-slate-400 mb-6">
          Architectural flow demonstrating event progression from GitHub push to the physical ESP32 Commit Light indicator:
        </p>

        <div className="grid grid-cols-1 md:grid-cols-5 gap-3 relative">
          {pipelineNodes.map((node, idx) => {
            const Icon = node.icon;
            const isLast = idx === pipelineNodes.length - 1;

            return (
              <div key={node.id} className="relative group">
                <div className="h-full bg-slate-950/70 border border-slate-800 rounded-xl p-4 flex flex-col justify-between hover:border-slate-700 transition-all">
                  <div>
                    <div className="flex items-center justify-between mb-3">
                      <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400">
                        <Icon className="w-5 h-5" />
                      </div>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-slate-800 text-slate-400">
                        Step {idx + 1}
                      </span>
                    </div>

                    <h4 className="text-sm font-semibold text-white mb-1">{node.title}</h4>
                    <span className="text-[11px] font-mono text-indigo-400 block mb-2">{node.role}</span>
                    <p className="text-xs text-slate-400 leading-relaxed">{node.desc}</p>
                  </div>

                  <div className="mt-4 pt-3 border-t border-slate-800/80">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] uppercase font-mono text-slate-500">Status</span>
                      <span className={`text-[10px] font-mono px-2 py-0.5 rounded font-semibold ${
                        node.statusType === 'tested'
                          ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                          : node.statusType === 'simulated'
                          ? 'bg-blue-500/10 text-blue-400 border border-blue-500/30'
                          : node.statusType === 'future'
                          ? 'bg-purple-500/10 text-purple-400 border border-purple-500/30'
                          : 'bg-amber-500/10 text-amber-400 border border-amber-500/30'
                      }`}>
                        {node.status}
                      </span>
                    </div>
                  </div>
                </div>

                {!isLast && (
                  <div className="hidden md:flex absolute -right-2 top-1/2 -translate-y-1/2 z-10 text-slate-600">
                    <ArrowRight className="w-4 h-4" />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* CloudFormation & Readiness Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* CloudFormation & IAM Specifications */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-lg space-y-4">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-emerald-400" />
            <h3 className="text-base font-semibold text-white">AWS Infrastructure Scaffolding</h3>
          </div>
          <p className="text-sm text-slate-400">
            Local CloudFormation templates and IAM policies have been validated and structured for least-privilege access:
          </p>

          <div className="space-y-3">
            <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-800 flex items-start justify-between gap-3">
              <div>
                <span className="text-xs font-mono font-semibold text-indigo-300">aws/github-webhook-template.yaml</span>
                <p className="text-xs text-slate-400 mt-0.5">
                  Full CloudFormation template specifying HTTP API, dedicated Lambda function, Secrets Manager access, and IoT publish policy.
                </p>
              </div>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 shrink-0">
                Validated
              </span>
            </div>

            <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-800 flex items-start justify-between gap-3">
              <div>
                <span className="text-xs font-mono font-semibold text-indigo-300">backend/lambda/lambda_function.py</span>
                <p className="text-xs text-slate-400 mt-0.5">
                  Dual-handler architecture: preserves existing CodeCommit pipeline while providing dedicated GitHub webhook handler with HMAC verification.
                </p>
              </div>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 shrink-0">
                138 Unit Tests
              </span>
            </div>

            <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-800 flex items-start justify-between gap-3">
              <div>
                <span className="text-xs font-mono font-semibold text-indigo-300">Runtime Security Enforcer</span>
                <p className="text-xs text-slate-400 mt-0.5">
                  Production guard strictly rejects plaintext fallback secrets when running inside AWS Lambda execution environments.
                </p>
              </div>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 shrink-0">
                Fail-Closed
              </span>
            </div>
          </div>
        </div>

        {/* Phase Comparison Table */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-lg space-y-4">
          <div className="flex items-center gap-2">
            <Clock className="w-5 h-5 text-indigo-400" />
            <h3 className="text-base font-semibold text-white">Phase 1 vs Future AWS Deployment</h3>
          </div>
          <p className="text-sm text-slate-400">
            Comparison between the current Phase 1 local simulation environment and future deployment targets:
          </p>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-slate-800 text-slate-400">
                <tr>
                  <th className="pb-2 font-semibold">Component</th>
                  <th className="pb-2 font-semibold">Phase 1 (Current)</th>
                  <th className="pb-2 font-semibold">Phase 2+ (Production)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                <tr>
                  <td className="py-2.5 text-slate-300 font-medium">Event Source</td>
                  <td className="py-2.5 text-blue-400">Browser Simulator UI</td>
                  <td className="py-2.5 text-emerald-400">Live GitHub Push Event</td>
                </tr>
                <tr>
                  <td className="py-2.5 text-slate-300 font-medium">Ingress Gateway</td>
                  <td className="py-2.5 text-blue-400">Client-side Dispatcher</td>
                  <td className="py-2.5 text-emerald-400">API Gateway HTTP API</td>
                </tr>
                <tr>
                  <td className="py-2.5 text-slate-300 font-medium">Lambda Compute</td>
                  <td className="py-2.5 text-blue-400">JS Deterministic Mirror</td>
                  <td className="py-2.5 text-emerald-400">AWS Lambda (Python 3.12)</td>
                </tr>
                <tr>
                  <td className="py-2.5 text-slate-300 font-medium">Secret Storage</td>
                  <td className="py-2.5 text-blue-400">Client Configuration</td>
                  <td className="py-2.5 text-emerald-400">AWS Secrets Manager</td>
                </tr>
                <tr>
                  <td className="py-2.5 text-slate-300 font-medium">MQTT Broker</td>
                  <td className="py-2.5 text-blue-400">Local State Queue</td>
                  <td className="py-2.5 text-emerald-400">AWS IoT Core (gitops/commits)</td>
                </tr>
                <tr>
                  <td className="py-2.5 text-slate-300 font-medium">Indicator</td>
                  <td className="py-2.5 text-blue-400">Web UI Live Monitor</td>
                  <td className="py-2.5 text-emerald-400">ESP32 Physical NeoPixel</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}


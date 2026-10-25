import React, { useState } from 'react';
import { 
  Info, 
  Trash2, 
  RotateCcw, 
  Database, 
  ShieldCheck, 
  Github, 
  FileCode, 
  Cpu, 
  CheckCircle2, 
  AlertCircle 
} from 'lucide-react';
import { clearStoredEvents, restoreSeedEvents, getStoredEvents } from '../../services/storageService';
import { SIMULATION_BANNER_TEXT, MQTT_TOPIC } from '../../types';

export default function AboutSection({ onResetEvents, eventCount, backendStatus = 'checking' }) {
  const [showClearConfirm, setShowClearConfirm] = useState(false);
  const [actionMessage, setActionMessage] = useState(null);

  const handleClearHistory = () => {
    if (onResetEvents) onResetEvents('clear');
    setShowClearConfirm(false);
    setActionMessage({ type: 'success', text: 'All event history cleared successfully.' });
    setTimeout(() => setActionMessage(null), 3000);
  };

  const handleRestoreSeeds = () => {
    if (onResetEvents) onResetEvents('restore');
    setActionMessage({ type: 'success', text: 'Default seed events restored successfully.' });
    setTimeout(() => setActionMessage(null), 3000);
  };

  return (
    <div className="space-y-6">
      {/* Notifications */}
      {actionMessage && (
        <div className={`p-4 rounded-xl border flex items-center gap-3 transition-all ${
          actionMessage.type === 'success' 
            ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300' 
            : 'bg-red-500/10 border-red-500/30 text-red-300'
        }`}>
          <CheckCircle2 className="w-5 h-5 shrink-0" />
          <span className="text-sm font-medium">{actionMessage.text}</span>
        </div>
      )}

      {/* Hero Overview */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-lg">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs font-mono font-bold uppercase tracking-wider text-indigo-400">
                Phase 1 Simulation Environment
              </span>
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-amber-500/10 border border-amber-500/30 text-amber-300">
                {SIMULATION_BANNER_TEXT}
              </span>
            </div>
            <h2 className="text-2xl font-bold text-white tracking-tight">About GitOps Commit Light</h2>
            <p className="text-sm text-slate-400 mt-1 max-w-3xl">
              GitOps Commit Light is an event-driven IoT notification system designed to illuminate a physical WS2812B NeoPixel RGB LED strip whenever valid push events occur on production branches.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <a
              href="https://github.com/darshan-codes-ai/GitOps-Commit-Light"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition-colors"
            >
              <Github className="w-4 h-4" />
              GitHub Repository
            </a>
          </div>
        </div>
      </div>

      {/* Architecture Highlights & Local Storage Management */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Local Storage Management */}
        <div className="lg:col-span-1 bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg space-y-4">
          <div className="flex items-center gap-2">
            <Database className="w-5 h-5 text-indigo-400" />
            <h3 className="text-base font-semibold text-white">Local Event Storage</h3>
          </div>
          <p className="text-xs text-slate-400 leading-relaxed">
            All simulation activities, push events, and generated MQTT payloads are maintained locally in your browser's <code className="text-slate-300">localStorage</code>.
          </p>

          <div className="bg-slate-950/70 p-4 rounded-lg border border-slate-800 space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-400">Stored Events Count</span>
              <span className="font-mono font-bold text-indigo-400 text-sm">{eventCount}</span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-400">Storage Key</span>
              <span className="font-mono text-slate-300 text-[11px]">gitops_commit_events_v1</span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-400">Active Topic</span>
              <span className="font-mono text-slate-300 text-[11px]">{MQTT_TOPIC}</span>
            </div>
            <div className="flex items-center justify-between text-xs pt-1 border-t border-slate-800/60">
              <span className="text-slate-400">Python Backend</span>
              <span className={`font-mono text-[11px] font-semibold ${
                backendStatus === 'connected' ? 'text-emerald-400' : 'text-amber-400'
              }`}>
                {backendStatus === 'connected' ? 'Online (FastAPI :8000)' : 'Offline (Client Fallback)'}
              </span>
            </div>
          </div>

          <div className="pt-2 space-y-3">
            {!showClearConfirm ? (
              <button
                onClick={() => setShowClearConfirm(true)}
                className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-red-500/10 hover:bg-red-500/20 text-red-300 border border-red-500/30 text-xs font-medium transition-colors"
              >
                <Trash2 className="w-4 h-4" />
                Clear Event History
              </button>
            ) : (
              <div className="p-3 bg-red-950/40 border border-red-500/50 rounded-lg space-y-2">
                <p className="text-xs text-red-200 font-medium">Are you sure? This will delete all simulated events.</p>
                <div className="flex items-center gap-2">
                  <button
                    onClick={handleClearHistory}
                    className="flex-1 py-1.5 px-3 bg-red-600 hover:bg-red-500 text-white rounded text-xs font-semibold"
                  >
                    Yes, Clear
                  </button>
                  <button
                    onClick={() => setShowClearConfirm(false)}
                    className="flex-1 py-1.5 px-3 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded text-xs"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}

            <button
              onClick={handleRestoreSeeds}
              className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-slate-800 hover:bg-slate-750 text-slate-200 border border-slate-700 text-xs font-medium transition-colors"
            >
              <RotateCcw className="w-4 h-4 text-slate-400" />
              Restore Default Seed Scenarios
            </button>
          </div>
        </div>

        {/* Right Column: Architectural Highlights */}
        <div className="lg:col-span-2 space-y-6">
          {/* Security & Invariants */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg space-y-3">
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-emerald-400" />
              <h3 className="text-base font-semibold text-white">Security & Architectural Invariants</h3>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs text-slate-400">
              <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-800/80">
                <span className="font-semibold text-slate-200 block mb-1">HMAC-SHA256 Signature Verification</span>
                Incoming webhooks must carry <code className="text-indigo-300">X-Hub-Signature-256</code> matching the shared secret computed via SHA-256 HMAC digest in constant-time.
              </div>
              <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-800/80">
                <span className="font-semibold text-slate-200 block mb-1">Strict Delivery ID Enforcement</span>
                Every push event must include an <code className="text-indigo-300">X-GitHub-Delivery</code> header. Missing or empty delivery IDs fail closed with HTTP 400.
              </div>
              <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-800/80">
                <span className="font-semibold text-slate-200 block mb-1">Branch Filtering & Deletion Guards</span>
                Only pushes to <code className="text-indigo-300">refs/heads/main</code> trigger MQTT publication. Branch deletions and other branches return HTTP 200 (ignored).
              </div>
              <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-800/80">
                <span className="font-semibold text-slate-200 block mb-1">Production Plaintext Secret Guard</span>
                When running in AWS Lambda, the backend strictly rejects plaintext secret fallback and demands AWS Secrets Manager ARN configuration.
              </div>
            </div>
          </div>

          {/* Schema Contract */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg space-y-3">
            <div className="flex items-center gap-2">
              <FileCode className="w-5 h-5 text-indigo-400" />
              <h3 className="text-base font-semibold text-white">MQTT Schema v1 Payload Contract</h3>
            </div>
            <p className="text-xs text-slate-400">
              Payloads published to <code className="text-indigo-300">gitops/commits</code> follow a strict Schema v1 contract:
            </p>
            <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 font-mono text-xs text-slate-300 overflow-x-auto">
{`{
  "schemaVersion": 1,
  "eventId": "f1d0a890-a33d-4c3e-8f3e-80c7d23a1012",
  "repository": "darshan-codes-ai/GitOps-Commit-Light",
  "branch": "main",
  "commitId": "9b1c7a8e2f3d4c5b6a7e8f90123456789abcdef0",
  "message": "feat(core): implement secure webhook verification",
  "timestamp": "2026-10-25T14:32:10.000Z"
}`}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}


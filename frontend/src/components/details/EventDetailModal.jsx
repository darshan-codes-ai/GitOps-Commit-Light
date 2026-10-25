import React, { useState } from 'react';
import Modal from '../common/Modal';
import StatusBadge from '../common/StatusBadge';
import JsonViewer from '../common/JsonViewer';
import { 
  GitBranch, 
  Clock, 
  User, 
  FileCode, 
  Terminal, 
  Layers, 
  Radio, 
  CheckCircle2, 
  XCircle, 
  AlertCircle 
} from 'lucide-react';
import { MQTT_TOPIC, MQTT_QOS } from '../../types';

export default function EventDetailModal({ event, isOpen, onClose }) {
  if (!event) return null;

  const [activeTab, setActiveTab] = useState('overview'); // 'overview' | 'mqtt' | 'raw' | 'timeline'
  const shaStr = event.commitSha || event.commit?.sha || '0000000000000000000000000000000000000000';
  const msgStr = event.commitMessage || event.commit?.message || '(No commit message)';
  const repoStr = typeof event.repository === 'string' ? event.repository : (event.repository?.fullName || event.repository?.name || 'GitOps-Commit-Light');
  const authorStr = event.author || event.commit?.author?.name || 'Developer';
  const changedFilesList = event.changedFiles || event.commit?.changedFiles || [];

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Event Details: ${shaStr.substring(0, 7)}`}
    >
      <div className="space-y-5">
        {/* Top Header Card */}
        <div className="bg-slate-950/70 border border-slate-800 rounded-lg p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <StatusBadge status={event.status} />
              <span className="text-xs font-mono text-slate-400">
                Delivery ID: {event.deliveryId || event.eventId || event.id}
              </span>
            </div>
            <h3 className="text-base font-semibold text-white">
              {msgStr}
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Repository: <span className="font-mono text-slate-300">{repoStr}</span> • Branch: <span className="font-mono text-indigo-400">{event.branch}</span>
            </p>
          </div>

          <div className="text-right sm:border-l sm:border-slate-800 sm:pl-4 shrink-0">
            <span className="text-[11px] text-slate-500 uppercase tracking-wider block">Timestamp</span>
            <span className="text-xs font-mono text-slate-300">
              {new Date(event.timestamp).toLocaleString()}
            </span>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-slate-800 text-xs">
          <button
            onClick={() => setActiveTab('overview')}
            className={`pb-2.5 px-3 font-semibold border-b-2 transition-colors ${
              activeTab === 'overview'
                ? 'border-indigo-500 text-indigo-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            Overview & Metadata
          </button>
          <button
            onClick={() => setActiveTab('mqtt')}
            className={`pb-2.5 px-3 font-semibold border-b-2 transition-colors ${
              activeTab === 'mqtt'
                ? 'border-indigo-500 text-indigo-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            MQTT Payload {event.mqttPublished ? '(Schema v1)' : '(Filtered)'}
          </button>
          <button
            onClick={() => setActiveTab('raw')}
            className={`pb-2.5 px-3 font-semibold border-b-2 transition-colors ${
              activeTab === 'raw'
                ? 'border-indigo-500 text-indigo-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            GitHub Webhook Payload
          </button>
          <button
            onClick={() => setActiveTab('timeline')}
            className={`pb-2.5 px-3 font-semibold border-b-2 transition-colors ${
              activeTab === 'timeline'
                ? 'border-indigo-500 text-indigo-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            Execution Pipeline
          </button>
        </div>

        {/* Tab 1: Overview */}
        {activeTab === 'overview' && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-800">
                <span className="text-[11px] text-slate-500 uppercase tracking-wider block">Author</span>
                <span className="text-xs font-medium text-slate-200 truncate block mt-0.5">
                  {authorStr}
                </span>
              </div>
              <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-800">
                <span className="text-[11px] text-slate-500 uppercase tracking-wider block">Full Commit SHA</span>
                <span className="text-xs font-mono text-indigo-400 truncate block mt-0.5" title={shaStr}>
                  {shaStr}
                </span>
              </div>
              <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-800">
                <span className="text-[11px] text-slate-500 uppercase tracking-wider block">Changed Files</span>
                <span className="text-xs font-medium text-slate-200 block mt-0.5">
                  {Array.isArray(changedFilesList) ? changedFilesList.length : 0} files
                </span>
              </div>
              <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-800">
                <span className="text-[11px] text-slate-500 uppercase tracking-wider block">MQTT Status</span>
                <span className={`text-xs font-semibold block mt-0.5 ${
                  event.mqttPublished ? 'text-emerald-400' : 'text-slate-400'
                }`}>
                  {event.mqttPublished ? `Published (QoS ${MQTT_QOS})` : 'Not Published'}
                </span>
              </div>
            </div>

            {/* Changed Files List */}
            {changedFilesList && changedFilesList.length > 0 && (
              <div className="p-4 bg-slate-950/60 rounded-lg border border-slate-800">
                <span className="text-xs font-semibold text-slate-300 block mb-2">
                  Modified File Paths:
                </span>
                <ul className="space-y-1 font-mono text-xs text-slate-400 max-h-32 overflow-y-auto custom-scrollbar">
                  {changedFilesList.map((file, idx) => (
                    <li key={idx} className="flex items-center gap-2">
                      <span className="text-indigo-400">•</span>
                      <span>{file}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Result Explanation */}
            <div className="p-4 bg-slate-950/80 rounded-lg border border-slate-800 text-xs space-y-1">
              <span className="font-semibold text-slate-300 block">Processing Result:</span>
              <p className="text-slate-400">
                {event.reason || (event.mqttPublished ? 'Valid push event on main branch. Formatted as Schema v1 and published.' : 'Filtered by Lambda rules.')}
              </p>
            </div>
          </div>
        )}

        {/* Tab 2: MQTT Payload */}
        {activeTab === 'mqtt' && (
          <div className="space-y-3">
            {event.mqttPublished && event.mqttPayload ? (
              <>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-400">
                    Topic: <code className="text-indigo-300 font-mono font-semibold">{MQTT_TOPIC}</code> • Delivery: <code className="text-emerald-400 font-mono font-semibold">QoS {MQTT_QOS}</code>
                  </span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                    Schema v1 Compliant
                  </span>
                </div>
                <JsonViewer data={event.mqttPayload} />
              </>
            ) : (
              <div className="p-8 text-center bg-slate-950/50 rounded-lg border border-slate-800">
                <AlertCircle className="w-8 h-8 text-slate-500 mx-auto mb-2" />
                <p className="text-sm font-semibold text-slate-300">No MQTT Message Published</p>
                <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
                  {event.reason || 'This event did not satisfy publication criteria (e.g., non-monitored branch, branch deletion, or failed validation).'}
                </p>
              </div>
            )}
          </div>
        )}

        {/* Tab 3: Raw Webhook Payload */}
        {activeTab === 'raw' && (
          <div className="space-y-3">
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span>Simulated GitHub Push Webhook HTTP Body</span>
              <span className="text-[10px] font-mono bg-slate-800 px-2 py-0.5 rounded">application/json</span>
            </div>
            <JsonViewer data={event.rawPayload || event} />
          </div>
        )}

        {/* Tab 4: Processing Timeline */}
        {activeTab === 'timeline' && (
          <div className="space-y-3">
            <div className="relative border-l-2 border-slate-800 ml-4 pl-4 space-y-4 py-2">
              <div className="relative">
                <span className="absolute -left-[23px] top-1 w-3 h-3 rounded-full bg-emerald-500 ring-4 ring-slate-900" />
                <h5 className="text-xs font-semibold text-slate-200">1. Webhook Ingress (API Gateway)</h5>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  POST /webhook received with headers: <code className="text-slate-300">X-GitHub-Delivery: {event.deliveryId || 'present'}</code>
                </p>
              </div>

              <div className="relative">
                <span className="absolute -left-[23px] top-1 w-3 h-3 rounded-full bg-emerald-500 ring-4 ring-slate-900" />
                <h5 className="text-xs font-semibold text-slate-200">2. Signature Verification (Lambda)</h5>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  HMAC-SHA256 signature verified against secret from AWS Secrets Manager.
                </p>
              </div>

              <div className="relative">
                <span className={`absolute -left-[23px] top-1 w-3 h-3 rounded-full ${
                  event.status === 'ignored' || event.status === 'rejected' ? 'bg-amber-500' : 'bg-emerald-500'
                } ring-4 ring-slate-900`} />
                <h5 className="text-xs font-semibold text-slate-200">3. Branch & Action Filtering</h5>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Branch target: <code className="text-indigo-300">{event.branch}</code>. Monitored branch: <code className="text-indigo-300">main</code>.
                  {event.status === 'ignored' ? ' Filter matched ignore criteria.' : ' Passed branch filter.'}
                </p>
              </div>

              <div className="relative">
                <span className={`absolute -left-[23px] top-1 w-3 h-3 rounded-full ${
                  event.mqttPublished ? 'bg-emerald-500' : 'bg-slate-600'
                } ring-4 ring-slate-900`} />
                <h5 className="text-xs font-semibold text-slate-200">4. IoT Core Dispatch (Simulated)</h5>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  {event.mqttPublished 
                    ? `Dispatched Schema v1 payload to topic ${MQTT_TOPIC} at QoS ${MQTT_QOS}.`
                    : 'Dispatch skipped (0 messages published).'}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Modal Footer */}
        <div className="flex justify-end pt-3 border-t border-slate-800">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </Modal>
  );
}


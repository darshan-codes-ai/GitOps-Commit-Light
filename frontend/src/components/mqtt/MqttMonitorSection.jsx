import React, { useState } from 'react';
import { Wifi, Radio, Copy, Check, Terminal, Info, ShieldAlert, Cpu } from 'lucide-react';
import JsonViewer from '../common/JsonViewer';
import StatusBadge from '../common/StatusBadge';
import { MQTT_TOPIC, MQTT_QOS } from '../../types';

export default function MqttMonitorSection({ events, onSelectEvent }) {
  const publishedEvents = events.filter((e) => (e.mqttPublished || e.status === 'success') && e.mqttPayload);
  const [selectedEventId, setSelectedEventId] = useState(
    publishedEvents.length > 0 ? (publishedEvents[0].id || publishedEvents[0].eventId) : null
  );

  const activeEvent = publishedEvents.find((e) => (e.id || e.eventId) === selectedEventId) || publishedEvents[0];

  return (
    <div className="space-y-6">
      {/* Top Banner & Header */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-lg relative overflow-hidden">
        <div className="absolute top-0 right-0 p-8 opacity-10 pointer-events-none">
          <Radio className="w-48 h-48 text-indigo-400" />
        </div>

        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="flex h-2.5 w-2.5 rounded-full bg-emerald-400 animate-ping" />
              <span className="text-xs font-semibold uppercase tracking-wider text-emerald-400">
                MQTT Monitor Active
              </span>
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-amber-500/10 border border-amber-500/30 text-amber-300 ml-2">
                SIMULATED — NOT SENT TO AWS
              </span>
            </div>
            <h2 className="text-2xl font-bold text-white tracking-tight">AWS IoT Core Message Monitor</h2>
            <p className="text-sm text-slate-400 mt-1 max-w-2xl">
              Inspect messages formatted according to MQTT Schema v1 dispatched to the local IoT queue. In production, these payloads are published to AWS IoT Core for consumption by the ESP32 Commit Light indicator.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <div className="bg-slate-950/80 border border-slate-800 rounded-lg px-4 py-2 text-right">
              <span className="text-xs text-slate-400 block">Topic Target</span>
              <span className="text-sm font-mono font-bold text-indigo-400">{MQTT_TOPIC}</span>
            </div>
            <div className="bg-slate-950/80 border border-slate-800 rounded-lg px-4 py-2 text-right">
              <span className="text-xs text-slate-400 block">Delivery QoS</span>
              <span className="text-sm font-mono font-bold text-emerald-400">QoS {MQTT_QOS}</span>
            </div>
          </div>
        </div>
      </div>

      {publishedEvents.length === 0 ? (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center">
          <Wifi className="w-12 h-12 text-slate-600 mx-auto mb-3" />
          <h3 className="text-lg font-semibold text-white">No MQTT Messages Published Yet</h3>
          <p className="text-sm text-slate-400 max-w-md mx-auto mt-1">
            Simulate a commit push event to the monitored branch (<code className="text-indigo-300">main</code>) to generate an MQTT Schema v1 payload.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Published Messages List */}
          <div className="lg:col-span-1 bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-lg flex flex-col h-[650px]">
            <div className="flex items-center justify-between pb-3 mb-3 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <Terminal className="w-4 h-4 text-indigo-400" />
                <h3 className="text-sm font-semibold text-white">Message Stream</h3>
              </div>
              <span className="text-xs font-mono text-slate-400 bg-slate-800 px-2 py-0.5 rounded">
                {publishedEvents.length} {publishedEvents.length === 1 ? 'message' : 'messages'}
              </span>
            </div>

            <div className="flex-1 overflow-y-auto space-y-2 pr-1 custom-scrollbar">
              {publishedEvents.map((ev) => {
                const evId = ev.id || ev.eventId;
                const isSelected = (activeEvent?.id || activeEvent?.eventId) === evId;
                const repoStr = typeof ev.repository === 'string' ? ev.repository : (ev.repository?.fullName || ev.repository?.name || 'GitOps-Commit-Light');
                const shaStr = (ev.commitSha || ev.commit?.sha || '0000000').substring(0, 7);
                const msgStr = ev.commitMessage || ev.commit?.message || '(No commit message)';

                return (
                  <button
                    key={evId}
                    onClick={() => setSelectedEventId(evId)}
                    className={`w-full text-left p-3 rounded-lg border transition-all ${
                      isSelected
                        ? 'bg-indigo-950/40 border-indigo-500/60 shadow-md ring-1 ring-indigo-500/20'
                        : 'bg-slate-950/50 border-slate-800/80 hover:bg-slate-800/40 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2 mb-1">
                      <span className="font-mono text-xs font-semibold text-indigo-300 truncate">
                        {shaStr}
                      </span>
                      <span className="text-[10px] text-slate-400 font-mono">
                        {new Date(ev.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                      </span>
                    </div>
                    <p className="text-xs text-slate-300 line-clamp-1 font-medium mb-2">
                      {msgStr}
                    </p>
                    <div className="flex items-center justify-between text-[11px] text-slate-400">
                      <span>{repoStr}</span>
                      <span className="font-mono text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded text-[10px]">
                        QoS 0
                      </span>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Active Payload Viewer */}
          <div className="lg:col-span-2 space-y-6">
            {activeEvent && (
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg space-y-5">
                {/* Message Header */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-800">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <StatusBadge status={activeEvent.status} />
                      <span className="text-xs text-slate-400 font-mono">
                        Event ID: {activeEvent.deliveryId || activeEvent.eventId || activeEvent.id}
                      </span>
                    </div>
                    <h3 className="text-base font-semibold text-white">
                      {activeEvent.commitMessage || activeEvent.commit?.message || '(No commit message)'}
                    </h3>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => onSelectEvent && onSelectEvent(activeEvent)}
                      className="text-xs text-indigo-400 hover:text-indigo-300 bg-indigo-500/10 hover:bg-indigo-500/20 px-3 py-1.5 rounded-lg border border-indigo-500/30 transition-colors"
                    >
                      View Full Event
                    </button>
                  </div>
                </div>

                {/* Metadata Row */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-slate-950/60 p-3 rounded-lg border border-slate-800/80">
                  <div>
                    <span className="text-[11px] text-slate-500 uppercase tracking-wider block">Repository</span>
                    <span className="text-xs font-mono font-medium text-slate-300 truncate block">
                      {typeof activeEvent.repository === 'string' ? activeEvent.repository : (activeEvent.repository?.name || activeEvent.repository?.fullName || 'GitOps-Commit-Light')}
                    </span>
                  </div>
                  <div>
                    <span className="text-[11px] text-slate-500 uppercase tracking-wider block">Branch</span>
                    <span className="text-xs font-mono font-medium text-indigo-300">
                      {activeEvent.branch}
                    </span>
                  </div>
                  <div>
                    <span className="text-[11px] text-slate-500 uppercase tracking-wider block">Author</span>
                    <span className="text-xs font-medium text-slate-300 truncate block">
                      {activeEvent.author || activeEvent.commit?.author?.name || 'Developer'}
                    </span>
                  </div>
                  <div>
                    <span className="text-[11px] text-slate-500 uppercase tracking-wider block">Committed At</span>
                    <span className="text-xs font-mono text-slate-400">
                      {new Date(activeEvent.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                </div>

                {/* JSON Payload Display */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                        Schema v1 JSON Payload
                      </span>
                      <span className="text-[10px] bg-indigo-500/20 text-indigo-300 px-2 py-0.5 rounded-full font-mono">
                        Topic: {MQTT_TOPIC}
                      </span>
                    </div>
                  </div>

                  <JsonViewer data={activeEvent.mqttPayload} />
                </div>

                {/* Hardware Consumption Hint */}
                <div className="bg-slate-950/70 border border-slate-800 rounded-lg p-4 flex items-start gap-3">
                  <Cpu className="w-5 h-5 text-indigo-400 shrink-0 mt-0.5" />
                  <div className="text-xs text-slate-400 space-y-1">
                    <p className="font-semibold text-slate-200">
                      Future Consumer: ESP32 Hardware / Wokwi Simulator
                    </p>
                    <p>
                      The ESP32 microcontroller subscribes to <code className="text-indigo-300">gitops/commits</code> over TLS with X.509 client certificates. When this JSON arrives, the device parses the commit metadata and triggers the WS2812B NeoPixel RGB LED commit sequence.
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Schema Contract Documentation */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg">
              <h4 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
                <Info className="w-4 h-4 text-indigo-400" />
                Schema v1 Specification Reference
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                <div className="p-3 bg-slate-950/60 rounded border border-slate-800">
                  <span className="font-mono text-indigo-400 font-semibold">schemaVersion</span>
                  <span className="text-slate-500 ml-1.5">(number)</span>
                  <p className="text-slate-400 mt-1">Always <code className="text-slate-300">1</code>. Enables future schema version negotiation.</p>
                </div>
                <div className="p-3 bg-slate-950/60 rounded border border-slate-800">
                  <span className="font-mono text-indigo-400 font-semibold">eventId</span>
                  <span className="text-slate-500 ml-1.5">(string)</span>
                  <p className="text-slate-400 mt-1">GitHub webhook delivery ID (<code className="text-slate-300">X-GitHub-Delivery</code> header).</p>
                </div>
                <div className="p-3 bg-slate-950/60 rounded border border-slate-800">
                  <span className="font-mono text-indigo-400 font-semibold">repository</span>
                  <span className="text-slate-500 ml-1.5">(string)</span>
                  <p className="text-slate-400 mt-1">Full repository name (<code className="text-slate-300">owner/repo</code>).</p>
                </div>
                <div className="p-3 bg-slate-950/60 rounded border border-slate-800">
                  <span className="font-mono text-indigo-400 font-semibold">branch</span>
                  <span className="text-slate-500 ml-1.5">(string)</span>
                  <p className="text-slate-400 mt-1">Branch name stripped of <code className="text-slate-300">refs/heads/</code> prefix.</p>
                </div>
                <div className="p-3 bg-slate-950/60 rounded border border-slate-800">
                  <span className="font-mono text-indigo-400 font-semibold">commitId</span>
                  <span className="text-slate-500 ml-1.5">(string)</span>
                  <p className="text-slate-400 mt-1">Full 40-character commit SHA from the push head.</p>
                </div>
                <div className="p-3 bg-slate-950/60 rounded border border-slate-800">
                  <span className="font-mono text-indigo-400 font-semibold">message</span>
                  <span className="text-slate-500 ml-1.5">(string)</span>
                  <p className="text-slate-400 mt-1">Commit message summary line.</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}


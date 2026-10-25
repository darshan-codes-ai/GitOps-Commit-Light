import React from 'react';
import {
  Layers,
  CheckCircle2,
  XCircle,
  FolderGit2,
  PlayCircle,
  ArrowRight,
  Radio,
  Clock,
  GitCommit,
  GitBranch,
  ShieldCheck
} from 'lucide-react';
import { KpiCard } from '../common/KpiCard';
import { StatusBadge } from '../common/StatusBadge';
import { EVENT_STATUS } from '../../types';

export const OverviewSection = ({ events = [], onNavigate, onSelectEvent }) => {
  // Compute KPIs dynamically from actual local state
  const totalEvents = events.length;
  const successfulEvents = events.filter((e) => e.status === EVENT_STATUS.SUCCESS).length;
  const failedEvents = events.filter((e) => e.status === EVENT_STATUS.FAILED).length;
  const ignoredEvents = events.filter((e) => e.status === EVENT_STATUS.IGNORED).length;

  const uniqueRepos = Array.from(
    new Set(events.map((e) => e.repository?.name || e.repository?.fullName || 'unknown'))
  ).length;

  const recentEvents = events.slice(0, 5);

  // Group events by repo for distribution
  const repoCounts = events.reduce((acc, curr) => {
    const name = curr.repository?.name || 'Unknown';
    acc[name] = (acc[name] || 0) + 1;
    return acc;
  }, {});

  const sortedRepos = Object.entries(repoCounts).sort((a, b) => b[1] - a[1]);

  return (
    <div className="space-y-6">
      {/* Hero Welcome & Quick Action Card */}
      <div className="relative overflow-hidden rounded-2xl border border-slate-800 bg-gradient-to-r from-slate-900 via-slate-900/90 to-slate-950 p-6 shadow-xl">
        <div className="relative z-10 flex flex-col justify-between gap-4 md:flex-row md:items-center">
          <div className="max-w-2xl">
            <div className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-3 py-1 text-xs font-semibold text-emerald-400 border border-emerald-500/20">
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>Phase 1 Demonstration Engine</span>
            </div>
            <h2 className="mt-2.5 text-2xl font-black text-slate-100 sm:text-3xl tracking-tight">
              GitOps Commit Event Simulator
            </h2>
            <p className="mt-1.5 text-sm text-slate-400 leading-relaxed">
              Interactive local demonstration of the commit notification pipeline: GitHub Push &rarr; API Gateway &rarr; Lambda Event Processor &rarr; AWS IoT Core MQTT.
            </p>
          </div>

          <div className="flex flex-wrap gap-3">
            <button
              onClick={() => onNavigate('simulator')}
              className="inline-flex items-center gap-2 rounded-xl bg-emerald-500 px-4 py-2.5 text-sm font-bold text-slate-950 shadow-lg shadow-emerald-500/20 transition-all hover:bg-emerald-400 focus:outline-none focus:ring-2 focus:ring-emerald-400"
            >
              <PlayCircle className="w-4 h-4" />
              <span>Simulate a Commit</span>
            </button>
            <button
              onClick={() => onNavigate('activity')}
              className="inline-flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-800 px-4 py-2.5 text-sm font-semibold text-slate-200 transition-all hover:bg-slate-700 hover:text-white focus:outline-none focus:ring-2 focus:ring-slate-400"
            >
              <span>Inspect History</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Ambient background glow */}
        <div className="absolute -top-24 -right-24 h-64 w-64 rounded-full bg-emerald-500/5 blur-3xl pointer-events-none" />
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard
          title="Total Events"
          value={totalEvents}
          subtext="Simulated webhook pushes received"
          icon={Layers}
          color="indigo"
        />
        <KpiCard
          title="Published (QoS 0)"
          value={successfulEvents}
          badge={`${totalEvents ? Math.round((successfulEvents / totalEvents) * 100) : 0}% success`}
          subtext="Dispatched to gitops/commits topic"
          icon={CheckCircle2}
          color="emerald"
        />
        <KpiCard
          title="Ignored / Filtered"
          value={ignoredEvents}
          subtext="Non-monitored branches or deletions"
          icon={Radio}
          color="amber"
        />
        <KpiCard
          title="Distinct Repos"
          value={uniqueRepos}
          subtext="Active repositories simulated"
          icon={FolderGit2}
          color="sky"
        />
      </div>

      {/* Main Grid: Recent Activity & Repository Distribution */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Left Column: Recent Events (2 cols) */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 lg:col-span-2">
          <div className="flex items-center justify-between border-b border-slate-800/80 pb-4">
            <div>
              <h3 className="text-base font-bold text-slate-100">Recent Commit Events</h3>
              <p className="text-xs text-slate-400">Latest push events processed through the local pipeline</p>
            </div>
            <button
              onClick={() => onNavigate('activity')}
              className="text-xs font-semibold text-emerald-400 hover:text-emerald-300 transition-colors flex items-center gap-1"
            >
              <span>View all ({totalEvents})</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="mt-4 divide-y divide-slate-800/60">
            {recentEvents.length === 0 ? (
              <div className="py-8 text-center text-slate-500 text-sm">
                No simulated events yet. Click &quot;Simulate a Commit&quot; to create your first event!
              </div>
            ) : (
              recentEvents.map((evt) => (
                <div
                  key={evt.eventId}
                  onClick={() => onSelectEvent(evt)}
                  className="group flex flex-col gap-2 py-3.5 transition-colors hover:bg-slate-800/40 rounded-lg px-2 cursor-pointer sm:flex-row sm:items-center sm:justify-between"
                >
                  <div className="space-y-1 min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-semibold text-slate-300 truncate">
                        {evt.repository?.name || 'GitOps-Commit-Light'}
                      </span>
                      <span className="inline-flex items-center gap-1 text-[11px] font-mono text-slate-400 bg-slate-800 px-2 py-0.5 rounded">
                        <GitBranch className="w-3 h-3 text-emerald-400" />
                        {evt.branch}
                      </span>
                      <span className="font-mono text-[11px] text-slate-500">
                        {evt.commit?.sha ? evt.commit.sha.substring(0, 7) : '0000000'}
                      </span>
                    </div>
                    <p className="text-xs text-slate-300 font-medium truncate group-hover:text-emerald-400 transition-colors">
                      {evt.commit?.message || '(No commit message)'}
                    </p>
                    <div className="flex items-center gap-3 text-[11px] text-slate-500">
                      <span>{evt.commit?.author?.name || 'Developer'}</span>
                      <span>•</span>
                      <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {new Date(evt.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                      </span>
                    </div>
                  </div>

                  <div className="flex-shrink-0 flex items-center gap-2">
                    <StatusBadge status={evt.status} />
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right Column: Repository Activity & Simulation Status (1 col) */}
        <div className="space-y-6">
          {/* Repository Activity Breakdown */}
          <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
            <h3 className="text-base font-bold text-slate-100">Repository Distribution</h3>
            <p className="text-xs text-slate-400">Events grouped by repository</p>

            <div className="mt-4 space-y-3">
              {sortedRepos.length === 0 ? (
                <p className="text-xs text-slate-500">No repositories recorded.</p>
              ) : (
                sortedRepos.map(([name, count]) => {
                  const pct = totalEvents ? Math.round((count / totalEvents) * 100) : 0;
                  return (
                    <div key={name} className="space-y-1">
                      <div className="flex justify-between text-xs font-medium">
                        <span className="text-slate-300 truncate max-w-[160px]">{name}</span>
                        <span className="text-slate-400 font-mono">{count} ({pct}%)</span>
                      </div>
                      <div className="h-1.5 w-full rounded-full bg-slate-800 overflow-hidden">
                        <div
                          className="h-full rounded-full bg-emerald-500 transition-all duration-500"
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {/* MQTT Quick Target Card */}
          <div className="rounded-xl border border-emerald-500/20 bg-emerald-950/20 p-5">
            <div className="flex items-center gap-2 text-emerald-400 font-semibold text-sm">
              <Radio className="w-4 h-4" />
              <span>Simulated MQTT Target</span>
            </div>
            <div className="mt-3 space-y-2 text-xs text-slate-300">
              <div className="flex justify-between">
                <span className="text-slate-400">Broker:</span>
                <span className="font-mono text-emerald-400">AWS IoT Core ATS (Simulated)</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Topic:</span>
                <code className="font-mono text-emerald-300 bg-slate-900 px-1.5 py-0.5 rounded">gitops/commits</code>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">QoS:</span>
                <span className="font-mono text-slate-300">0 (At most once)</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Payload Contract:</span>
                <span className="font-mono text-emerald-300">Schema v1</span>
              </div>
            </div>

            <button
              onClick={() => onNavigate('mqtt')}
              className="mt-4 w-full rounded-lg bg-emerald-500/10 border border-emerald-500/30 py-2 text-center text-xs font-semibold text-emerald-400 hover:bg-emerald-500/20 transition-colors"
            >
              Open MQTT Message Monitor &rarr;
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default OverviewSection;


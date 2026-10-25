import React from 'react';
import { GitCommit, ShieldAlert, Cpu, Menu, RefreshCw, Server, Wifi } from 'lucide-react';
import { SIMULATION_BANNER } from '../../types';

export const Header = ({
  onToggleSidebar,
  mobileMenuOpen,
  setMobileMenuOpen,
  backendStatus = 'checking',
  onRefresh,
  isSyncing = false
}) => {
  const handleToggle = onToggleSidebar || (() => setMobileMenuOpen && setMobileMenuOpen(!mobileMenuOpen));

  return (
    <header className="sticky top-0 z-40 border-b border-slate-800 bg-slate-950/90 backdrop-blur">
      {/* Simulation Banner required by specification */}
      <div className="bg-amber-500/10 border-b border-amber-500/20 px-4 py-1.5 text-center text-xs font-semibold tracking-wide text-amber-400 flex items-center justify-center gap-2">
        <ShieldAlert className="w-3.5 h-3.5 flex-shrink-0" />
        <span>{SIMULATION_BANNER}</span>
        <span className="hidden sm:inline text-amber-500/60">•</span>
        <span className="hidden sm:inline text-slate-400 font-normal">Deterministic in-memory simulation</span>
      </div>

      <div className="flex h-16 items-center justify-between px-4 sm:px-6">
        <div className="flex items-center gap-3">
          <button
            onClick={handleToggle}
            type="button"
            className="rounded-lg p-2 text-slate-400 hover:bg-slate-900 hover:text-slate-100 lg:hidden focus:outline-none focus:ring-2 focus:ring-emerald-500"
            aria-label="Toggle navigation"
          >
            <Menu className="w-5 h-5" />
          </button>

          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-tr from-emerald-600 to-teal-400 text-slate-950 font-bold shadow-lg shadow-emerald-500/20">
              <GitCommit className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-base font-bold text-slate-100 tracking-tight sm:text-lg">
                  GitOps Commit Light
                </h1>
                <span className="rounded bg-emerald-500/10 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-400 border border-emerald-500/20">
                  LOCAL DEV
                </span>
              </div>
              <p className="hidden sm:block text-xs text-slate-400">
                GitHub Webhook &rarr; AWS Lambda &rarr; IoT Core MQTT Simulator
              </p>
            </div>
          </div>
        </div>

        {/* Right Status Indicators */}
        <div className="flex items-center gap-2 sm:gap-3">
          {/* Refresh Button */}
          {onRefresh && (
            <button
              onClick={onRefresh}
              disabled={isSyncing}
              title="Refresh connection and events from backend"
              className="p-1.5 rounded-lg border border-slate-800 bg-slate-900/60 text-slate-400 hover:text-white hover:bg-slate-800 transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isSyncing ? 'animate-spin text-indigo-400' : ''}`} />
            </button>
          )}

          {/* Backend Connection Indicator */}
          <div className="flex items-center gap-2 rounded-lg border border-slate-800 bg-slate-900/80 px-2.5 py-1.5 text-xs font-medium">
            <span className="relative flex h-2 w-2">
              {backendStatus === 'connected' ? (
                <>
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                </>
              ) : (
                <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-500"></span>
              )}
            </span>
            <span className="hidden md:inline text-slate-400">Backend:</span>
            <span className={backendStatus === 'connected' ? 'text-emerald-400 font-mono text-[11px]' : 'text-amber-400 font-mono text-[11px]'}>
              {backendStatus === 'connected' ? 'Connected (:8000)' : 'Client Sim'}
            </span>
          </div>

          {/* Target MQTT Topic */}
          <div className="hidden lg:flex items-center gap-2 rounded-lg border border-slate-800 bg-slate-900/60 px-3 py-1.5 text-xs text-slate-300">
            <Wifi className="w-3.5 h-3.5 text-indigo-400" />
            <span className="text-slate-400">Topic:</span>
            <code className="font-mono text-indigo-300">gitops/commits</code>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;

import React from 'react';
import { GitCommit, ShieldAlert, Cpu, Menu } from 'lucide-react';
import { SIMULATION_BANNER } from '../../types';

export const Header = ({ onToggleSidebar, mobileMenuOpen, setMobileMenuOpen }) => {
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
                  PHASE 1
                </span>
              </div>
              <p className="hidden sm:block text-xs text-slate-400">
                GitHub Webhook &rarr; AWS Lambda &rarr; IoT Core MQTT Simulator
              </p>
            </div>
          </div>
        </div>

        {/* Right Status Indicator */}
        <div className="flex items-center gap-3">
          <div className="hidden md:flex items-center gap-2 rounded-lg border border-slate-800 bg-slate-900/60 px-3 py-1.5 text-xs text-slate-300">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <span className="text-slate-400">Target Topic:</span>
            <code className="font-mono text-emerald-400">gitops/commits</code>
          </div>

          <div className="flex items-center gap-1.5 rounded-lg border border-slate-800 bg-slate-900/80 px-2.5 py-1.5 text-xs font-medium text-slate-300">
            <Cpu className="w-3.5 h-3.5 text-amber-400" />
            <span className="hidden sm:inline">Engine:</span>
            <span className="text-amber-400">Local Mock</span>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;

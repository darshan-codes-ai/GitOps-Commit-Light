import React from 'react';
import {
  LayoutDashboard,
  GitPullRequest,
  PlayCircle,
  Radio,
  Server,
  Info,
  GitBranch
} from 'lucide-react';

export const Sidebar = ({ 
  activeTab, 
  onSelectTab, 
  setActiveTab, 
  eventCount = 0, 
  isOpen, 
  mobileOpen, 
  onClose 
}) => {
  const handleSelect = onSelectTab || setActiveTab;
  const isMenuOpen = isOpen || mobileOpen;

  const navItems = [
    {
      id: 'overview',
      label: 'Overview Dashboard',
      icon: LayoutDashboard,
      badge: null,
    },
    {
      id: 'simulator',
      label: 'Push Simulator',
      icon: PlayCircle,
      badge: 'Interactive',
    },
    {
      id: 'activity',
      label: 'Commit Activity',
      icon: GitPullRequest,
      badge: eventCount > 0 ? eventCount : null,
    },
    {
      id: 'mqtt',
      label: 'MQTT Message Monitor',
      icon: Radio,
      badge: 'Schema v1',
    },
    {
      id: 'status',
      label: 'AWS Integration Status',
      icon: Server,
      badge: 'Local',
    },
    {
      id: 'about',
      label: 'Project & Roadmap',
      icon: Info,
      badge: null,
    },
  ];

  return (
    <>
      {/* Mobile backdrop */}
      {isMenuOpen && (
        <div 
          className="fixed inset-0 z-40 bg-slate-950/80 backdrop-blur-sm lg:hidden"
          onClick={onClose}
        />
      )}

      <aside
        className={`fixed top-16 bottom-0 left-0 z-40 w-64 border-r border-slate-800 bg-slate-950 p-4 transition-transform lg:static lg:translate-x-0 ${
          isMenuOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex h-full flex-col justify-between">
          <div className="space-y-6">
            <div>
              <span className="px-3 text-[11px] font-bold uppercase tracking-wider text-slate-500">
                Navigation
              </span>
              <nav className="mt-2 space-y-1">
                {navItems.map((item) => {
                  const Icon = item.icon;
                  const isActive = activeTab === item.id;
                  return (
                    <button
                      key={item.id}
                      onClick={() => {
                        if (handleSelect) handleSelect(item.id);
                        if (onClose) onClose();
                      }}
                      className={`flex w-full items-center justify-between rounded-xl px-3 py-2.5 text-sm font-medium transition-all ${
                        isActive
                          ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 shadow-sm'
                          : 'text-slate-400 hover:bg-slate-900 hover:text-slate-200'
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <Icon className={`w-4 h-4 ${isActive ? 'text-emerald-400' : 'text-slate-400'}`} />
                        <span>{item.label}</span>
                      </div>
                      {item.badge !== null && (
                        <span
                          className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                            isActive
                              ? 'bg-emerald-500/20 text-emerald-300'
                              : 'bg-slate-800 text-slate-400'
                          }`}
                        >
                          {item.badge}
                        </span>
                      )}
                    </button>
                  );
                })}
              </nav>
            </div>

            {/* Quick Context Card */}
            <div className="rounded-xl border border-slate-800/80 bg-slate-900/40 p-3.5 text-xs">
              <div className="flex items-center gap-2 font-semibold text-slate-300">
                <GitBranch className="w-3.5 h-3.5 text-emerald-400" />
                <span>Monitored Branch</span>
              </div>
              <p className="mt-1 text-slate-400 leading-relaxed">
                Pushes to <code className="text-emerald-400 font-mono">main</code> trigger MQTT commit alerts. Other branches are safely ignored.
              </p>
            </div>
          </div>

          {/* Footer note */}
          <div className="border-t border-slate-800/80 pt-4 text-[11px] text-slate-500 flex items-center justify-between">
            <span>GitOps Commit Light</span>
            <span className="font-mono text-slate-600">v1.0-sim</span>
          </div>
        </div>
      </aside>
    </>
  );
};

export default Sidebar;


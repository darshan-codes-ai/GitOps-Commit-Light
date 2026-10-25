import React from 'react';

export const KpiCard = ({ title, value, subtext, icon: Icon, badge, color = 'emerald' }) => {
  const colorStyles = {
    emerald: {
      border: 'hover:border-emerald-500/40',
      iconBg: 'bg-emerald-500/10 text-emerald-400',
      glow: 'group-hover:text-emerald-400',
    },
    amber: {
      border: 'hover:border-amber-500/40',
      iconBg: 'bg-amber-500/10 text-amber-400',
      glow: 'group-hover:text-amber-400',
    },
    rose: {
      border: 'hover:border-rose-500/40',
      iconBg: 'bg-rose-500/10 text-rose-400',
      glow: 'group-hover:text-rose-400',
    },
    indigo: {
      border: 'hover:border-indigo-500/40',
      iconBg: 'bg-indigo-500/10 text-indigo-400',
      glow: 'group-hover:text-indigo-400',
    },
    sky: {
      border: 'hover:border-sky-500/40',
      iconBg: 'bg-sky-500/10 text-sky-400',
      glow: 'group-hover:text-sky-400',
    }
  };

  const style = colorStyles[color] || colorStyles.emerald;

  return (
    <div className={`group relative rounded-xl border border-slate-800 bg-slate-900/70 p-5 shadow-lg backdrop-blur transition-all duration-200 ${style.border}`}>
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
          {title}
        </span>
        {Icon && (
          <div className={`rounded-lg p-2.5 ${style.iconBg}`}>
            <Icon className="w-5 h-5" />
          </div>
        )}
      </div>

      <div className="mt-3 flex items-baseline gap-2">
        <span className={`text-3xl font-extrabold tracking-tight text-slate-100 transition-colors ${style.glow}`}>
          {value}
        </span>
        {badge && (
          <span className="text-xs font-medium text-slate-400">
            {badge}
          </span>
        )}
      </div>

      {subtext && (
        <p className="mt-2 text-xs text-slate-400">
          {subtext}
        </p>
      )}
    </div>
  );
};

export default KpiCard;


import React from 'react';
import { CheckCircle2, AlertCircle, AlertTriangle, Radio } from 'lucide-react';
import { EVENT_STATUS } from '../../types';

export const StatusBadge = ({ status, size = 'sm' }) => {
  const normalized = (status || '').toLowerCase();

  const isSmall = size === 'sm';
  const sizeClasses = isSmall 
    ? 'px-2.5 py-0.5 text-xs' 
    : 'px-3 py-1 text-sm font-medium';

  if (normalized === EVENT_STATUS.SUCCESS) {
    return (
      <span className={`inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 ${sizeClasses}`}>
        <CheckCircle2 className={isSmall ? "w-3 h-3" : "w-4 h-4"} />
        <span>Published (QoS 0)</span>
      </span>
    );
  }

  if (normalized === EVENT_STATUS.IGNORED) {
    return (
      <span className={`inline-flex items-center gap-1.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20 ${sizeClasses}`}>
        <AlertTriangle className={isSmall ? "w-3 h-3" : "w-4 h-4"} />
        <span>Ignored (Filtered)</span>
      </span>
    );
  }

  if (normalized === EVENT_STATUS.FAILED) {
    return (
      <span className={`inline-flex items-center gap-1.5 rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/20 ${sizeClasses}`}>
        <AlertCircle className={isSmall ? "w-3 h-3" : "w-4 h-4"} />
        <span>Rejected (400)</span>
      </span>
    );
  }

  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700 ${sizeClasses}`}>
      <Radio className={isSmall ? "w-3 h-3" : "w-4 h-4"} />
      <span>{status || 'Simulated'}</span>
    </span>
  );
};

export default StatusBadge;


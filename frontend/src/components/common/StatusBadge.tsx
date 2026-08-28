import React from 'react';

interface StatusBadgeProps {
  status: string;
  className?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  className = '',
}) => {
  const getStyles = () => {
    const s = status.toUpperCase();

    // Critical / Emergency / High
    if (s.includes('CRITICAL') || s.includes('P1') || s.includes('FLOOD') || s.includes('FIRE')) {
      return 'bg-red-950/70 text-red-400 border-red-800/60 shadow-[0_0_8px_rgba(239,68,68,0.2)]';
    }

    // High / Urgent / Warning
    if (s.includes('HIGH') || s.includes('P2') || s.includes('WARNING') || s.includes('PROPOSED')) {
      return 'bg-amber-950/70 text-amber-400 border-amber-800/60 shadow-[0_0_8px_rgba(245,158,11,0.2)]';
    }

    // Success / Clear / Approved / Available
    if (s.includes('OK') || s.includes('CLEAR') || s.includes('APPROVED') || s.includes('AVAILABLE') || s.includes('RESOLVED')) {
      return 'bg-emerald-950/70 text-emerald-400 border-emerald-800/60 shadow-[0_0_8px_rgba(16,185,129,0.2)]';
    }

    // Active / Dispatched / In Progress
    if (s.includes('PROGRESS') || s.includes('DISPATCHED') || s.includes('DEPLOYED') || s.includes('EN_ROUTE')) {
      return 'bg-blue-950/70 text-blue-400 border-blue-800/60 shadow-[0_0_8px_rgba(59,130,246,0.2)]';
    }

    // Standard / Low
    return 'bg-slate-800/80 text-slate-300 border-slate-700';
  };

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-mono font-medium border uppercase tracking-wider ${getStyles()} ${className}`}
    >
      <span className="w-1.5 h-1.5 rounded-full mr-1.5 bg-current animate-pulse opacity-80" />
      {status.replace(/_/g, ' ')}
    </span>
  );
};

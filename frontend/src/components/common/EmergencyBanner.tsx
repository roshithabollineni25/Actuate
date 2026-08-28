import React, { useEffect, useState } from 'react';
import { Radio, AlertTriangle, ShieldCheck } from 'lucide-react';
import { healthService } from '../../services/healthService';

export const EmergencyBanner: React.FC = () => {
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null);

  useEffect(() => {
    let isMounted = true;
    const checkApi = async () => {
      try {
        const res = await healthService.getHealth();
        if (isMounted) {
          setBackendOnline(res.status === 'ok');
        }
      } catch {
        if (isMounted) {
          setBackendOnline(false);
        }
      }
    };

    checkApi();
    const interval = setInterval(checkApi, 15000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  return (
    <aside aria-label="System status" className="bg-tactical-900 border-b border-slate-800/80 px-4 py-1 text-xs font-mono">
      <div className="max-w-[1400px] mx-auto flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 text-blue-400">
            <Radio className="w-3.5 h-3.5 animate-pulse text-emerald-400" />
            <span className="font-bold tracking-wider text-white">ACTUATE NETWORK</span>
          </div>
          <span className="text-slate-600 hidden sm:inline">|</span>
          <span className="text-slate-400 hidden sm:inline text-[11px]">
            Agentic Emergency Response & Coordination System
          </span>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5">
            <span className="text-slate-500">SYSTEM STATUS:</span>
            {backendOnline === true && (
              <span className="flex items-center gap-1 text-emerald-400 font-semibold">
                <ShieldCheck className="w-3.5 h-3.5" /> OPERATIONAL
              </span>
            )}
            {backendOnline === false && (
              <span className="flex items-center gap-1 text-amber-400 font-semibold" title="Connecting to backend...">
                <AlertTriangle className="w-3.5 h-3.5" /> CONNECTING
              </span>
            )}
            {backendOnline === null && (
              <span className="text-slate-500 animate-pulse">SYNCING...</span>
            )}
          </div>
        </div>
      </div>
    </aside>
  );
};

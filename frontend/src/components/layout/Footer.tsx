import React from 'react';
import { Shield, Terminal } from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer className="border-t border-slate-800 bg-tactical-900/80 py-4 text-slate-400 text-xs font-mono">
      <div className="max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <Shield className="w-4 h-4 text-blue-500" />
          <span className="text-white font-bold tracking-wider">ACTUATE</span>
          <span className="text-slate-600">—</span>
          <span>Agentic Emergency Response & Coordination System</span>
        </div>

        <div className="flex items-center gap-6 text-slate-500">
          <span className="flex items-center gap-1 text-cyan-400 font-semibold">
            From Intelligence to Action
          </span>
          <span className="flex items-center gap-1">
            <Terminal className="w-3.5 h-3.5 text-slate-400" /> FastAPI + React + TS
          </span>
        </div>
      </div>
    </footer>
  );
};

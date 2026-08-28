import React from 'react';
import { Link } from 'react-router-dom';
import { ShieldAlert, ArrowLeft } from 'lucide-react';

export const NotFoundPage: React.FC = () => {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-tactical-900 text-slate-100 p-4">
      <div className="text-center max-w-md">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-red-600/20 border border-red-500/40 text-red-400 mb-6">
          <ShieldAlert className="w-8 h-8" />
        </div>
        <h1 className="text-4xl font-bold font-mono tracking-tight text-white mb-2">404</h1>
        <h2 className="text-lg font-mono text-slate-300 mb-4">TACTICAL SECTOR NOT FOUND</h2>
        <p className="text-sm text-slate-400 font-sans mb-8">
          The requested coordinate or operations HUD is either restricted or does not exist in the active mesh.
        </p>
        <Link
          to="/"
          className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white font-mono text-xs uppercase tracking-wider py-3 px-6 rounded-lg font-semibold transition-all shadow-[0_0_15px_rgba(59,130,246,0.3)]"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Return to Command Base</span>
        </Link>
      </div>
    </div>
  );
};

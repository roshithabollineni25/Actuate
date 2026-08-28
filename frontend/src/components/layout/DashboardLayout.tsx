import React from 'react';
import { Navbar } from './Navbar';
import { Footer } from './Footer';
import { EmergencyBanner } from '../common/EmergencyBanner';

interface DashboardLayoutProps {
  children: React.ReactNode;
  roleBadgeTitle?: string;
  roleBadgeColor?: 'blue' | 'amber' | 'emerald';
}

export const DashboardLayout: React.FC<DashboardLayoutProps> = ({
  children,
  roleBadgeTitle,
  roleBadgeColor = 'blue',
}) => {
  return (
    <div className="min-h-screen flex flex-col bg-tactical-900 text-slate-100 selection:bg-blue-600 selection:text-white">
      <EmergencyBanner />
      <Navbar />

      <main className="flex-1 max-w-[1400px] w-full mx-auto px-4 sm:px-6 lg:px-8 py-4">
        {roleBadgeTitle && (
          <div className="mb-4 flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-3">
              <span
                className={`w-2.5 h-2.5 rounded-full animate-pulse ${
                  roleBadgeColor === 'emerald'
                    ? 'bg-emerald-500'
                    : roleBadgeColor === 'amber'
                    ? 'bg-amber-500'
                    : 'bg-blue-500'
                }`}
              />
              <h1 className="text-lg font-bold font-mono tracking-wide text-white uppercase">
                {roleBadgeTitle}
              </h1>
            </div>
            <span className="text-xs font-mono text-cyan-400 font-semibold hidden sm:inline">
              ACTUATE
            </span>
          </div>
        )}
        {children}
      </main>

      <Footer />
    </div>
  );
};

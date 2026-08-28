import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Shield, Radio, Activity, Users, Lock, Mail, ArrowRight, AlertCircle } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { UserRole } from '../types/auth';
import { EmergencyBanner } from '../components/common/EmergencyBanner';
import { Navbar } from '../components/layout/Navbar';
import { Footer } from '../components/layout/Footer';

export const LoginPage: React.FC = () => {
  const [selectedRole, setSelectedRole] = useState<UserRole>('CITIZEN');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { login, loginAsRole } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const from = (location.state as any)?.from?.pathname || (
    selectedRole === 'CITIZEN' ? '/citizen' : selectedRole === 'ADMIN' ? '/admin' : '/rescue'
  );

  const handleQuickDemoLogin = async (role: UserRole) => {
    setErrorMsg(null);
    try {
      await loginAsRole(role);
      navigate(role === 'CITIZEN' ? '/citizen' : role === 'ADMIN' ? '/admin' : '/rescue');
    } catch (err: any) {
      setErrorMsg(err.message || 'Quick login failed.');
    }
  };

  const handleFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) {
      setErrorMsg('Please enter an email address.');
      return;
    }
    setErrorMsg(null);
    setIsSubmitting(true);
    try {
      await login(email, password || 'demo123', selectedRole);
      navigate(from);
    } catch (err: any) {
      setErrorMsg(err.message || 'Authentication failed. Please check credentials.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-tactical-900 text-slate-100 selection:bg-blue-600 selection:text-white">
      <EmergencyBanner />
      <Navbar />

      <main className="flex-1 flex items-center justify-center px-4 sm:px-6 lg:px-8 py-12">
        <div className="max-w-md w-full space-y-8">
          {/* Header */}
          <div className="text-center">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-blue-600/20 border border-blue-500/40 text-blue-400 mb-4 shadow-[0_0_20px_rgba(59,130,246,0.2)]">
              <Shield className="w-8 h-8" />
            </div>
            <h2 className="text-2xl font-bold font-mono tracking-wider text-white uppercase">
              ACTUATE Access Portal
            </h2>
            <p className="mt-1 text-xs font-mono text-slate-400">
              Agentic Emergency Response & Coordination System
            </p>
          </div>

          {/* Quick 1-Click Role Switcher */}
          <div className="p-4 rounded-xl border border-slate-800 bg-tactical-800/80">
            <div className="text-[11px] font-mono uppercase text-slate-400 mb-3 flex items-center justify-between">
              <span>Quick Demo Role Access</span>
              <span className="text-cyan-400 text-[10px]">1-CLICK DEMO</span>
            </div>

            <div className="grid grid-cols-3 gap-2">
              <button
                type="button"
                onClick={() => handleQuickDemoLogin('CITIZEN')}
                className="flex flex-col items-center gap-1.5 p-3 rounded-lg border border-blue-900/60 bg-blue-950/40 hover:bg-blue-900/50 text-blue-300 text-xs font-mono transition-all"
              >
                <Radio className="w-4 h-4 text-blue-400" />
                <span>Citizen</span>
              </button>

              <button
                type="button"
                onClick={() => handleQuickDemoLogin('ADMIN')}
                className="flex flex-col items-center gap-1.5 p-3 rounded-lg border border-amber-900/60 bg-amber-950/40 hover:bg-amber-900/50 text-amber-300 text-xs font-mono transition-all"
              >
                <Activity className="w-4 h-4 text-amber-400" />
                <span>Coordinator</span>
              </button>

              <button
                type="button"
                onClick={() => handleQuickDemoLogin('RESCUE_TEAM')}
                className="flex flex-col items-center gap-1.5 p-3 rounded-lg border border-emerald-900/60 bg-emerald-950/40 hover:bg-emerald-900/50 text-emerald-300 text-xs font-mono transition-all"
              >
                <Users className="w-4 h-4 text-emerald-400" />
                <span>Rescue Unit</span>
              </button>
            </div>
          </div>

          {/* Standard Login Form */}
          <form onSubmit={handleFormSubmit} className="mt-8 space-y-6 p-6 rounded-xl border border-slate-800 bg-tactical-800/50">
            {errorMsg && (
              <div className="p-3 rounded bg-red-950/80 border border-red-800/80 text-red-300 text-xs font-mono flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
                <span>{errorMsg}</span>
              </div>
            )}

            {/* Role Selection Tabs */}
            <div>
              <label className="block text-xs font-mono text-slate-400 uppercase mb-2">
                Target Role
              </label>
              <div className="grid grid-cols-3 gap-2 bg-tactical-900 p-1 rounded-lg border border-slate-800">
                {(['CITIZEN', 'ADMIN', 'RESCUE_TEAM'] as UserRole[]).map((r) => (
                  <button
                    key={r}
                    type="button"
                    onClick={() => setSelectedRole(r)}
                    className={`py-1.5 text-[11px] font-mono rounded uppercase transition-all ${
                      selectedRole === r
                        ? 'bg-blue-600 text-white font-semibold shadow'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    {r === 'RESCUE_TEAM' ? 'Rescue' : r}
                  </button>
                ))}
              </div>
            </div>

            {/* Email Input */}
            <div>
              <label className="block text-xs font-mono text-slate-400 uppercase mb-1.5">
                Email Address
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
                  <Mail className="w-4 h-4" />
                </div>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder={`${selectedRole.toLowerCase()}@actuate.ai`}
                  className="w-full pl-9 pr-3 py-2 bg-tactical-900 border border-slate-700 rounded-lg text-sm text-white placeholder-slate-500 font-mono focus:outline-none focus:border-blue-500 transition-colors"
                />
              </div>
            </div>

            {/* Password Input */}
            <div>
              <label className="block text-xs font-mono text-slate-400 uppercase mb-1.5">
                Password
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
                  <Lock className="w-4 h-4" />
                </div>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="w-full pl-9 pr-3 py-2 bg-tactical-900 border border-slate-700 rounded-lg text-sm text-white placeholder-slate-500 font-mono focus:outline-none focus:border-blue-500 transition-colors"
                />
              </div>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-500 disabled:bg-blue-900 text-white font-mono text-xs uppercase tracking-wider py-3 px-4 rounded-lg font-semibold transition-all shadow-[0_0_15px_rgba(59,130,246,0.3)]"
            >
              {isSubmitting ? (
                <span>Authenticating Session...</span>
              ) : (
                <>
                  <span>Sign In as {selectedRole}</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>
        </div>
      </main>

      <Footer />
    </div>
  );
};

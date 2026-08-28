import React from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { Shield, Radio, Users, Activity, LogOut, LogIn, ChevronRight } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { UserRole } from '../../types/auth';

export const Navbar: React.FC = () => {
  const { isAuthenticated, role, user, logout, loginAsRole } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const handleRoleSwitch = async (newRole: UserRole) => {
    await loginAsRole(newRole);
    if (newRole === 'CITIZEN') navigate('/citizen');
    if (newRole === 'ADMIN') navigate('/admin');
    if (newRole === 'RESCUE_TEAM') navigate('/rescue');
  };

  return (
    <header className="sticky top-0 z-50 bg-tactical-900/95 backdrop-blur border-b border-slate-800">
      <div className="max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Brand */}
          <Link to="/" className="flex items-center gap-3 group">
            <div className="w-10 h-10 rounded-lg bg-blue-600/20 border border-blue-500/40 flex items-center justify-center text-blue-400 group-hover:border-blue-400 transition-colors">
              <Shield className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-extrabold text-xl tracking-wider text-white group-hover:text-blue-400 transition-colors font-mono">
                  ACTUATE
                </span>
                <span className="text-[10px] font-mono text-cyan-400 px-2 py-0.5 rounded bg-cyan-950/80 border border-cyan-800/80 hidden sm:inline-block">
                  From Intelligence to Action
                </span>
              </div>
              <p className="text-[11px] text-slate-400 font-mono hidden md:block">
                Agentic Emergency Response & Coordination System
              </p>
            </div>
          </Link>

          {/* Navigation Links & Role Selector */}
          <nav className="flex items-center gap-3">
            {isAuthenticated ? (
              <>
                {/* Role Switcher Pills */}
                <div className="hidden md:flex items-center bg-tactical-800 p-1 rounded-lg border border-slate-750 text-xs font-mono">
                  <button
                    onClick={() => handleRoleSwitch('CITIZEN')}
                    className={`px-3 py-1.5 rounded transition-all flex items-center gap-1.5 ${
                      role === 'CITIZEN'
                        ? 'bg-blue-600 text-white shadow-sm font-semibold'
                        : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    <Radio className="w-3.5 h-3.5" /> Citizen Portal
                  </button>
                  <button
                    onClick={() => handleRoleSwitch('ADMIN')}
                    className={`px-3 py-1.5 rounded transition-all flex items-center gap-1.5 ${
                      role === 'ADMIN'
                        ? 'bg-amber-600 text-white shadow-sm font-semibold'
                        : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    <Activity className="w-3.5 h-3.5" /> Coordinator Dashboard
                  </button>
                  <button
                    onClick={() => handleRoleSwitch('RESCUE_TEAM')}
                    className={`px-3 py-1.5 rounded transition-all flex items-center gap-1.5 ${
                      role === 'RESCUE_TEAM'
                        ? 'bg-emerald-600 text-white shadow-sm font-semibold'
                        : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    <Users className="w-3.5 h-3.5" /> Rescue Field Unit
                  </button>
                </div>

                {/* Active Dashboard Link */}
                <Link
                  to={
                    role === 'CITIZEN'
                      ? '/citizen'
                      : role === 'ADMIN'
                      ? '/admin'
                      : '/rescue'
                  }
                  className={`text-xs font-mono uppercase tracking-wider px-3 py-1.5 rounded border transition-colors flex items-center gap-1.5 ${
                    location.pathname.includes('/citizen') ||
                    location.pathname.includes('/admin') ||
                    location.pathname.includes('/rescue')
                      ? 'border-blue-500/50 bg-blue-950/40 text-blue-300'
                      : 'border-slate-700 bg-slate-800/60 text-slate-300 hover:text-white'
                  }`}
                >
                  <span>Dashboard</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </Link>

                {/* User info & Logout */}
                <div className="flex items-center gap-2 pl-2 border-l border-slate-800">
                  <span className="text-xs font-mono text-slate-400 hidden lg:inline max-w-[120px] truncate">
                    {user?.email}
                  </span>
                  <button
                    onClick={logout}
                    title="Sign Out"
                    className="p-2 rounded hover:bg-slate-800 text-slate-400 hover:text-red-400 transition-colors"
                  >
                    <LogOut className="w-4 h-4" />
                  </button>
                </div>
              </>
            ) : (
              <div className="flex items-center gap-3">
                <Link
                  to="/login"
                  className="flex items-center gap-2 text-xs font-mono uppercase tracking-wider bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded font-semibold transition-colors shadow-[0_0_12px_rgba(59,130,246,0.3)]"
                >
                  <LogIn className="w-3.5 h-3.5" /> Access Portal
                </Link>
              </div>
            )}
          </nav>
        </div>
      </div>
    </header>
  );
};

import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Shield,
  Radio,
  Activity,
  Users,
  Cpu,
  Compass,
  Repeat,
  CheckCircle2,
  Lock,
  ArrowRight,
  Sparkles,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { UserRole } from '../types/auth';
import { EmergencyBanner } from '../components/common/EmergencyBanner';
import { Navbar } from '../components/layout/Navbar';
import { Footer } from '../components/layout/Footer';

export const LandingPage: React.FC = () => {
  const { loginAsRole } = useAuth();
  const navigate = useNavigate();

  const handleQuickRoleAccess = async (role: UserRole, targetRoute: string) => {
    await loginAsRole(role);
    navigate(targetRoute);
  };

  const agents = [
    {
      name: 'Situation Understanding Agent',
      icon: Sparkles,
      color: 'text-purple-400 border-purple-800/60 bg-purple-950/20',
      description:
        'Powered by Google Gemini (gemini-3.6-flash). Extracts casualties, trapped status, and geolocations from multimodal speech & unstructured messages.',
    },
    {
      name: 'Risk & Priority Agent',
      icon: Activity,
      color: 'text-red-400 border-red-800/60 bg-red-950/20',
      description:
        'Computes objective severity indices (1-10), dynamic triage levels, and hazard danger circles.',
    },
    {
      name: 'Resource Matching Agent',
      icon: Cpu,
      color: 'text-amber-400 border-amber-800/60 bg-amber-950/20',
      description:
        'Matches required emergency equipment against PostgreSQL inventory and calculates rescue team availability.',
    },
    {
      name: 'Route Intelligence Agent',
      icon: Compass,
      color: 'text-blue-400 border-blue-800/60 bg-blue-950/20',
      description:
        'OSRM routing graph engine generating deterministic corridors that strictly bypass active road hazards.',
    },
    {
      name: 'Mission Coordination Agent',
      icon: Shield,
      color: 'text-emerald-400 border-emerald-800/60 bg-emerald-950/20',
      description:
        'Synthesizes multi-agent outputs into actionable Mission Orders and enforces Human-in-the-Loop (HITL) approval gates.',
    },
    {
      name: 'Continuous Replanning Agent',
      icon: Repeat,
      color: 'text-cyan-400 border-cyan-800/60 bg-cyan-950/20',
      description:
        'Live telemetry sentinel monitoring active en-route teams to compute dynamic bypass detours when hazards emerge.',
    },
  ];

  return (
    <div className="min-h-screen flex flex-col bg-tactical-900 text-slate-100 selection:bg-blue-600 selection:text-white">
      <EmergencyBanner />
      <Navbar />

      {/* Hero Section */}
      <section className="relative overflow-hidden border-b border-slate-800 py-16 lg:py-24 bg-gradient-to-b from-tactical-900 via-tactical-800 to-tactical-900">
        <div className="absolute inset-0 opacity-10 pointer-events-none bg-[radial-gradient(#3b82f6_1px,transparent_1px)] [background-size:24px_24px]"></div>

        <div className="max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-8 relative">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-cyan-500/40 bg-cyan-950/60 text-cyan-300 text-xs font-mono mb-6">
            <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping"></span>
            <span>AGENTIC EMERGENCY RESPONSE & COORDINATION SYSTEM</span>
          </div>

          <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight text-white max-w-4xl leading-tight font-mono">
            ACTUATE
          </h1>

          <p className="mt-3 text-xl sm:text-2xl text-cyan-300 font-mono font-bold max-w-3xl">
            From Intelligence to Action
          </p>

          <p className="mt-4 text-slate-300 text-base sm:text-lg max-w-2xl leading-relaxed">
            An autonomous multi-agent emergency coordination platform integrating situational AI understanding,
            deterministic route intelligence, PostGIS spatial queries, and human-in-the-loop (HITL) authorization gates.
          </p>

          {/* Call to Actions */}
          <div className="mt-8 flex flex-wrap gap-4">
            <Link
              to="/login"
              className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white font-mono text-sm px-6 py-3 rounded-lg font-semibold transition-all shadow-[0_0_20px_rgba(59,130,246,0.4)]"
            >
              <span>Launch Operations Portal</span>
              <ArrowRight className="w-4 h-4" />
            </Link>
            <a
              href="#agentic-architecture"
              className="inline-flex items-center gap-2 bg-slate-800 hover:bg-slate-700 text-slate-200 font-mono text-sm px-6 py-3 rounded-lg border border-slate-700 transition-colors"
            >
              <span>Explore Agent Specs</span>
            </a>
          </div>

          {/* Quick Metrics Bar */}
          <div className="mt-12 grid grid-cols-2 sm:grid-cols-4 gap-4 border-t border-slate-800 pt-8 font-mono">
            <div>
              <div className="text-2xl font-bold text-blue-400">6 Specialized</div>
              <div className="text-xs text-slate-400 uppercase">AI Agents</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-emerald-400">100% HITL</div>
              <div className="text-xs text-slate-400 uppercase">Coordinator Guard</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-amber-400">PostGIS + OSM</div>
              <div className="text-xs text-slate-400 uppercase">Safe Corridors</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-purple-400">Gemini 3.7</div>
              <div className="text-xs text-slate-400 uppercase">Multimodal Core</div>
            </div>
          </div>
        </div>
      </section>

      {/* Role Selection HUD Section */}
      <section className="py-16 bg-tactical-900 border-b border-slate-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="mb-10">
            <h2 className="text-xs font-mono uppercase tracking-widest text-blue-400 mb-1">
              ROLE-BASED DISASTER INTERFACES
            </h2>
            <p className="text-2xl sm:text-3xl font-bold text-white">
              Instant Access to Tactical HUDs
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Citizen Role Card */}
            <div className="p-6 rounded-xl border border-blue-900/40 bg-tactical-800/60 hover:border-blue-500/50 transition-all flex flex-col justify-between group">
              <div>
                <div className="w-12 h-12 rounded-lg bg-blue-600/10 border border-blue-500/30 flex items-center justify-center text-blue-400 mb-4">
                  <Radio className="w-6 h-6" />
                </div>
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-lg font-bold text-white">Citizen Portal</h3>
                  <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-blue-950 text-blue-400 border border-blue-800">
                    CITIZEN
                  </span>
                </div>
                <p className="text-sm text-slate-400 leading-relaxed">
                  Voice and text SOS reporting, real-time broadcast alerts, nearby safe evacuation zones, and rescue status tracking.
                </p>
              </div>

              <div className="mt-6 pt-4 border-t border-slate-700/60">
                <button
                  onClick={() => handleQuickRoleAccess('CITIZEN', '/citizen')}
                  className="w-full inline-flex items-center justify-center gap-2 bg-blue-600/20 hover:bg-blue-600 text-blue-300 hover:text-white font-mono text-xs py-2.5 px-4 rounded border border-blue-500/30 transition-all"
                >
                  <span>Open Citizen HUD</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            {/* Admin / Coordinator Role Card */}
            <div className="p-6 rounded-xl border border-amber-900/40 bg-tactical-800/60 hover:border-amber-500/50 transition-all flex flex-col justify-between group">
              <div>
                <div className="w-12 h-12 rounded-lg bg-amber-600/10 border border-amber-500/30 flex items-center justify-center text-amber-400 mb-4">
                  <Activity className="w-6 h-6" />
                </div>
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-lg font-bold text-white">Emergency Coordinator</h3>
                  <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-amber-950 text-amber-400 border border-amber-800">
                    ADMIN / EOC
                  </span>
                </div>
                <p className="text-sm text-slate-400 leading-relaxed">
                  Command center dashboard with the AI Agent Proposal Approval Queue, live resource allocation, and manual overrides.
                </p>
              </div>

              <div className="mt-6 pt-4 border-t border-slate-700/60">
                <button
                  onClick={() => handleQuickRoleAccess('ADMIN', '/admin')}
                  className="w-full inline-flex items-center justify-center gap-2 bg-amber-600/20 hover:bg-amber-600 text-amber-300 hover:text-white font-mono text-xs py-2.5 px-4 rounded border border-amber-500/30 transition-all"
                >
                  <span>Open Command EOC</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            {/* Rescue Team Role Card */}
            <div className="p-6 rounded-xl border border-emerald-900/40 bg-tactical-800/60 hover:border-emerald-500/50 transition-all flex flex-col justify-between group">
              <div>
                <div className="w-12 h-12 rounded-lg bg-emerald-600/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 mb-4">
                  <Users className="w-6 h-6" />
                </div>
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-lg font-bold text-white">Rescue Field Team</h3>
                  <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800">
                    RESCUE_TEAM
                  </span>
                </div>
                <p className="text-sm text-slate-400 leading-relaxed">
                  Tactical field HUD displaying assigned missions, live casualty briefs, turn-by-turn safe routes, and real-time status dispatch.
                </p>
              </div>

              <div className="mt-6 pt-4 border-t border-slate-700/60">
                <button
                  onClick={() => handleQuickRoleAccess('RESCUE_TEAM', '/rescue')}
                  className="w-full inline-flex items-center justify-center gap-2 bg-emerald-600/20 hover:bg-emerald-600 text-emerald-300 hover:text-white font-mono text-xs py-2.5 px-4 rounded border border-emerald-500/30 transition-all"
                >
                  <span>Open Field HUD</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 6 Specialized Agents Section */}
      <section id="agentic-architecture" className="py-16 bg-tactical-800/40 border-b border-slate-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="mb-10">
            <h2 className="text-xs font-mono uppercase tracking-widest text-blue-400 mb-1">
              AGENTIC INTELLIGENCE MESH
            </h2>
            <p className="text-2xl sm:text-3xl font-bold text-white">
              6 Specialized Agents Operating in Harmony
            </p>
            <p className="text-sm text-slate-400 mt-2 max-w-2xl font-mono">
              Deterministic precision where safety is critical; generative intelligence where understanding is complex.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {agents.map((agent, index) => {
              const Icon = agent.icon;
              return (
                <div
                  key={index}
                  className="p-6 rounded-xl border border-slate-800 bg-tactical-800/80 hover:border-slate-700 transition-colors flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-center justify-between mb-4">
                      <div className={`p-2.5 rounded-lg border ${agent.color}`}>
                        <Icon className="w-5 h-5" />
                      </div>
                      <span className="text-[10px] font-mono uppercase bg-cyan-950 text-cyan-400 px-2 py-0.5 rounded border border-cyan-800">
                        ACTIVE AGENT
                      </span>
                    </div>
                    <h3 className="text-base font-bold text-white mb-2">{agent.name}</h3>
                    <p className="text-xs text-slate-400 leading-relaxed font-sans">{agent.description}</p>
                  </div>

                  <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-[11px] font-mono text-slate-500">
                    <span>Architecture Module</span>
                    <span className="text-emerald-400 flex items-center gap-1 font-semibold">
                      <CheckCircle2 className="w-3 h-3" /> Operational
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* Safety & Engineering Principles */}
      <section className="py-16 bg-tactical-900">
        <div className="max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-8">
          <div className="p-8 rounded-2xl border border-blue-900/30 bg-gradient-to-r from-tactical-800 via-tactical-850 to-tactical-800">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-center">
              <div className="lg:col-span-2">
                <div className="flex items-center gap-2 text-blue-400 font-mono text-xs mb-2">
                  <Lock className="w-4 h-4" />
                  <span>SAFETY-FIRST SYSTEM DESIGN</span>
                </div>
                <h3 className="text-2xl font-bold text-white mb-3">
                  Human-in-the-Loop Life-Critical Verification
                </h3>
                <p className="text-sm text-slate-300 leading-relaxed">
                  ACTUATE never dispatches emergency rescue teams without explicit Emergency Coordinator authorization.
                  The multi-agent system accelerates analysis and compiles verified proposals—keeping human experts in full control.
                </p>
              </div>

              <div className="flex flex-col sm:flex-row lg:flex-col gap-3 justify-end">
                <Link
                  to="/login"
                  className="inline-flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-500 text-white font-mono text-xs py-3 px-6 rounded-lg font-semibold transition-all shadow-[0_0_15px_rgba(59,130,246,0.3)]"
                >
                  <span>Sign In with Roles</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </div>
            </div>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
};

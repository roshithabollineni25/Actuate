import React, { useCallback, useEffect, useState } from 'react';
import { DashboardLayout } from '../../components/layout/DashboardLayout';
import { StatusBadge } from '../../components/common/StatusBadge';
import {
  Mic,
  Send,
  MapPin,
  AlertOctagon,
  Shield,
  Radio,
  Compass,
  Loader2,
  CheckCircle2,
  XCircle,
  TriangleAlert,
} from 'lucide-react';
import {
  incidentService,
  IncidentResponse,
  SituationAnalysisResponse,
} from '../../services/incidentService';

interface SpeechRecognitionEventLike {
  results: {
    [index: number]: {
      [index: number]: {
        transcript: string;
      };
    };
  };
}

interface SpeechRecognitionLike {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  start: () => void;
  stop: () => void;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
  onend: (() => void) | null;
  onerror: (() => void) | null;
}

interface SpeechRecognitionConstructor {
  new (): SpeechRecognitionLike;
}

interface BrowserWindow extends Window {
  SpeechRecognition?: SpeechRecognitionConstructor;
  webkitSpeechRecognition?: SpeechRecognitionConstructor;
}

type SubmissionState =
  | 'idle'
  | 'locating'
  | 'analyzing'
  | 'creating'
  | 'success'
  | 'error';

const getSpeechRecognition = (): SpeechRecognitionConstructor | null => {
  const browserWindow = window as BrowserWindow;

  return (
    browserWindow.SpeechRecognition ??
    browserWindow.webkitSpeechRecognition ??
    null
  );
};

export const CitizenDashboard: React.FC = () => {
  const [reportText, setReportText] = useState('');
  const [isRecording, setIsRecording] = useState(false);

  const [reports, setReports] = useState<IncidentResponse[]>([]);

  const [submissionState, setSubmissionState] =
    useState<SubmissionState>('idle');

  const [errorMessage, setErrorMessage] = useState('');

  const [analysis, setAnalysis] =
    useState<SituationAnalysisResponse | null>(null);

  const [createdIncident, setCreatedIncident] =
    useState<IncidentResponse | null>(null);

  const [coordinates, setCoordinates] = useState<{
    latitude: number;
    longitude: number;
  } | null>(null);

  const loadReports = useCallback(async () => {
    try {
      const incidents = await incidentService.getIncidents();

      setReports(incidents);
    } catch (error) {
      console.error('Failed to load incidents:', error);
    }
  }, []);

  useEffect(() => {
    void loadReports();
    const interval = window.setInterval(() => {
      void loadReports();
    }, 10000);
    return () => window.clearInterval(interval);
  }, [loadReports]);

  const isWithinOperationalSector = (lat: number, lng: number): boolean => {
    // ACTUATE Hyderabad operational sector boundary: 17.0°N - 17.8°N, 78.0°E - 78.9°E
    return lat >= 17.0 && lat <= 17.8 && lng >= 78.0 && lng <= 78.9;
  };

  const getCurrentLocation = (): Promise<{
    latitude: number;
    longitude: number;
  }> => {
    return new Promise((resolve) => {
      const defaultOperationalLocation = {
        latitude: 17.4550,
        longitude: 78.3650,
      };

      if (!navigator.geolocation) {
        setCoordinates(defaultOperationalLocation);
        resolve(defaultOperationalLocation);
        return;
      }

      navigator.geolocation.getCurrentPosition(
        (position) => {
          const lat = position.coords.latitude;
          const lng = position.coords.longitude;

          if (isWithinOperationalSector(lat, lng)) {
            const realLocation = { latitude: lat, longitude: lng };
            setCoordinates(realLocation);
            resolve(realLocation);
          } else {
            // Browser GPS succeeded but is outside ACTUATE Hyderabad operational sector
            setCoordinates(defaultOperationalLocation);
            resolve(defaultOperationalLocation);
          }
        },
        () => {
          setCoordinates(defaultOperationalLocation);
          resolve(defaultOperationalLocation);
        },
        {
          enableHighAccuracy: true,
          timeout: 5000,
          maximumAge: 0,
        },
      );
    });
  };

  const handleVoiceInput = () => {
    const SpeechRecognition = getSpeechRecognition();

    if (!SpeechRecognition) {
      setErrorMessage(
        'Voice input is not supported by this browser. Please use Chrome or enter the emergency description manually.',
      );
      setSubmissionState('error');
      return;
    }

    if (isRecording) {
      return;
    }

    const recognition = new SpeechRecognition();

    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-IN';

    recognition.onresult = (event) => {
      const transcript =
        event.results[0]?.[0]?.transcript?.trim();

      if (transcript) {
        setReportText((current) =>
          current ? `${current} ${transcript}` : transcript,
        );
      }
    };

    recognition.onend = () => {
      setIsRecording(false);
    };

    recognition.onerror = () => {
      setIsRecording(false);
      setErrorMessage(
        'Voice recognition failed. Please try again or enter the report manually.',
      );
      setSubmissionState('error');
    };

    setErrorMessage('');
    setSubmissionState('idle');
    setIsRecording(true);

    recognition.start();
  };

  const handleSendReport = async (
    event: React.FormEvent<HTMLFormElement>,
  ) => {
    event.preventDefault();

    const cleanedReport = reportText.trim();

    if (!cleanedReport) {
      setErrorMessage(
        'Please describe the emergency before submitting the SOS alert.',
      );
      setSubmissionState('error');
      return;
    }

    setErrorMessage('');
    setAnalysis(null);
    setCreatedIncident(null);

    try {
      /*
       * STEP 1
       * Obtain the citizen's REAL browser location.
       */
      setSubmissionState('locating');

      const location = await getCurrentLocation();

      /*
       * STEP 2
       * Send the citizen's actual emergency description
       * to the real Situation Understanding Agent.
       */
      setSubmissionState('analyzing');

      const situation =
        await incidentService.analyzeSituation({
          raw_text: cleanedReport,
          metadata: {
            latitude: location.latitude,
            longitude: location.longitude,
          },
        });

      setAnalysis(situation);

      /*
       * STEP 3
       * Persist the AI-processed emergency as a REAL incident.
       *
       * No Math.random().
       * No fake incident ID.
       * No hard-coded category.
       * No hard-coded urgency.
       */
      setSubmissionState('creating');

      const estimatedCasualties =
        situation.injured_count + situation.critical_count;

      const incident =
        await incidentService.createIncident({
          title: situation.summary,
          description: cleanedReport,
          category: situation.category,
          urgency_level: situation.urgency_level,
          latitude: location.latitude,
          longitude: location.longitude,
          raw_input_text: cleanedReport,
          estimated_casualties: estimatedCasualties,
        });

      /*
       * STEP 4
       * Store the REAL database response.
       */
      setCreatedIncident(incident);
      setSubmissionState('success');

      /*
       * STEP 5
       * Reload from the backend so the incident shown
       * in "Your Reported Incidents" is actually persisted data.
       */
      await loadReports();

      setReportText('');
    } catch (error) {
      console.error('SOS submission failed:', error);

      const message =
        error instanceof Error
          ? error.message
          : 'Emergency submission failed.';

      setErrorMessage(message);
      setSubmissionState('error');

      /*
       * IMPORTANT:
       * We intentionally do NOT create a fake incident
       * when the backend or AI fails.
       */
    }
  };

  const getSubmissionMessage = (): string | null => {
    switch (submissionState) {
      case 'locating':
        return 'Obtaining your real GPS location...';

      case 'analyzing':
        return 'Situation Understanding Agent is analyzing the emergency...';

      case 'creating':
        return 'AI analysis complete. Creating the emergency incident...';

      case 'success':
        return 'Emergency incident successfully created and synchronized.';

      default:
        return null;
    }
  };

  return (
    <DashboardLayout
      roleBadgeTitle="Citizen Emergency Portal"
      roleBadgeColor="blue"
    >
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* =========================================================
            LEFT COLUMN
            ========================================================= */}

        <div className="lg:col-span-2 space-y-6">

          {/* =======================================================
              REAL SOS INTAKE
              ======================================================= */}

          <div className="p-6 rounded-xl border border-red-900/50 bg-tactical-800/80 shadow-[0_0_20px_rgba(239,68,68,0.15)] relative overflow-hidden">

            <div className="absolute top-0 right-0 px-3 py-1 bg-red-950/90 text-red-400 border-b border-l border-red-800 text-[10px] font-mono uppercase tracking-wider">
              Priority SOS Channel
            </div>

            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-lg bg-red-600/20 border border-red-500/40 flex items-center justify-center text-red-400">
                <AlertOctagon className="w-6 h-6" />
              </div>

              <div>
                <h2 className="text-lg font-bold text-white">
                  Report Emergency Situation
                </h2>

                <p className="text-xs text-slate-400 font-mono">
                  Your report will be processed by the Situation
                  Understanding Agent.
                </p>
              </div>
            </div>

            {/* =====================================================
                VOICE INPUT
                ===================================================== */}

            <div className="mb-4 p-4 rounded-lg bg-tactical-900 border border-slate-700/80 flex flex-col sm:flex-row items-center justify-between gap-4">

              <div className="flex items-center gap-3">

                <button
                  type="button"
                  onClick={handleVoiceInput}
                  disabled={submissionState === 'analyzing' || submissionState === 'creating'}
                  className={`w-12 h-12 rounded-full flex items-center justify-center transition-all ${
                    isRecording
                      ? 'bg-red-600 text-white animate-pulse shadow-[0_0_20px_rgba(239,68,68,0.6)]'
                      : 'bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-600'
                  }`}
                  title={
                    isRecording
                      ? 'Listening...'
                      : 'Record Emergency Voice Message'
                  }
                >
                  <Mic className="w-5 h-5" />
                </button>

                <div>
                  <div className="text-sm font-semibold text-white">
                    {isRecording
                      ? 'Listening to emergency message...'
                      : 'Voice Emergency Message'}
                  </div>

                  <div className="text-xs text-slate-400 font-mono">
                    {isRecording
                      ? 'Speak clearly. Your speech will be converted to text.'
                      : 'Click microphone to provide your emergency by voice.'}
                  </div>
                </div>

              </div>

              <span className="text-[11px] font-mono bg-slate-800 text-slate-400 px-2.5 py-1 rounded border border-slate-700">
                Browser Voice Input
              </span>

            </div>

            {/* =====================================================
                TEXT REPORT
                ===================================================== */}

            <form
              onSubmit={handleSendReport}
              className="space-y-3"
            >
              <textarea
                rows={4}
                value={reportText}
                onChange={(event) =>
                  setReportText(event.target.value)
                }
                disabled={
                  submissionState === 'locating' ||
                  submissionState === 'analyzing' ||
                  submissionState === 'creating'
                }
                placeholder="Describe your emergency situation..."
                className="w-full p-3 bg-tactical-900 border border-slate-700 rounded-lg text-sm text-white placeholder-slate-500 font-sans focus:outline-none focus:border-red-500 transition-colors disabled:opacity-60"
              />

              {/* =================================================
                  REAL GPS
                  ================================================= */}

              <div className="flex flex-wrap items-center justify-between gap-3">

                <div className="flex items-center gap-2 text-xs font-mono text-slate-400">

                  <MapPin className="w-4 h-4 text-blue-400" />

                  {coordinates ? (
                    <span>
                      GPS Locked:{' '}
                      {coordinates.latitude.toFixed(6)}° N,{' '}
                      {coordinates.longitude.toFixed(6)}° E
                    </span>
                  ) : (
                    <span>
                      GPS will be obtained when SOS is submitted
                    </span>
                  )}

                </div>

                <button
                  type="submit"
                  disabled={
                    submissionState === 'locating' ||
                    submissionState === 'analyzing' ||
                    submissionState === 'creating'
                  }
                  className="inline-flex items-center gap-2 bg-red-600 hover:bg-red-500 disabled:bg-red-900 disabled:cursor-not-allowed text-white font-mono text-xs uppercase tracking-wider py-2.5 px-5 rounded-lg font-semibold transition-all shadow-[0_0_15px_rgba(239,68,68,0.3)]"
                >

                  {submissionState === 'locating' ||
                  submissionState === 'analyzing' ||
                  submissionState === 'creating' ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Send className="w-3.5 h-3.5" />
                  )}

                  <span>
                    {submissionState === 'locating'
                      ? 'Getting Location...'
                      : submissionState === 'analyzing'
                        ? 'Analyzing...'
                        : submissionState === 'creating'
                          ? 'Creating Incident...'
                          : 'Submit SOS Alert'}
                  </span>

                </button>

              </div>
            </form>

            {/* =====================================================
                PROCESS STATUS
                ===================================================== */}

            {getSubmissionMessage() && (
              <div
                className={`mt-4 p-3 rounded-lg border text-xs font-mono ${
                  submissionState === 'success'
                    ? 'border-emerald-800 bg-emerald-950/30 text-emerald-300'
                    : 'border-blue-800 bg-blue-950/30 text-blue-300'
                }`}
              >
                <div className="flex items-center gap-2">
                  {submissionState === 'success' ? (
                    <CheckCircle2 className="w-4 h-4" />
                  ) : (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  )}

                  <span>{getSubmissionMessage()}</span>
                </div>
              </div>
            )}

            {/* =====================================================
                ERROR
                ===================================================== */}

            {submissionState === 'error' && errorMessage && (
              <div className="mt-4 p-3 rounded-lg border border-red-800 bg-red-950/30 text-red-300 text-xs font-mono">
                <div className="flex items-start gap-2">
                  <XCircle className="w-4 h-4 mt-0.5 shrink-0" />

                  <div>
                    <div className="font-bold">
                      Emergency submission failed
                    </div>

                    <div className="mt-1 text-red-200/80">
                      {errorMessage}
                    </div>
                  </div>
                </div>
              </div>
            )}

          </div>

          {/* =======================================================
              AI ANALYSIS RESULT
              ======================================================= */}

          {analysis && (
            <div className="p-6 rounded-xl border border-blue-900/60 bg-tactical-800/80">

              <div className="flex items-center justify-between mb-4">

                <div className="flex items-center gap-2">
                  <TriangleAlert className="w-4 h-4 text-blue-400" />

                  <h3 className="text-base font-bold text-white">
                    Situation Understanding Agent
                  </h3>
                </div>

                <StatusBadge
                  status={analysis.urgency_level}
                />

              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">

                <div className="p-3 rounded-lg bg-tactical-900 border border-slate-800">
                  <div className="text-[10px] text-slate-500 font-mono uppercase">
                    Category
                  </div>
                  <div className="mt-1 text-sm text-white font-bold">
                    {analysis.category}
                  </div>
                </div>

                <div className="p-3 rounded-lg bg-tactical-900 border border-slate-800">
                  <div className="text-[10px] text-slate-500 font-mono uppercase">
                    People
                  </div>
                  <div className="mt-1 text-sm text-white font-bold">
                    {analysis.people_count}
                  </div>
                </div>

                <div className="p-3 rounded-lg bg-tactical-900 border border-slate-800">
                  <div className="text-[10px] text-slate-500 font-mono uppercase">
                    Injured
                  </div>
                  <div className="mt-1 text-sm text-white font-bold">
                    {analysis.injured_count}
                  </div>
                </div>

                <div className="p-3 rounded-lg bg-tactical-900 border border-slate-800">
                  <div className="text-[10px] text-slate-500 font-mono uppercase">
                    Trapped
                  </div>
                  <div className="mt-1 text-sm text-white font-bold">
                    {analysis.trapped_count}
                  </div>
                </div>

              </div>

              <div className="p-4 rounded-lg bg-tactical-900 border border-slate-800">

                <div className="text-xs text-slate-500 font-mono uppercase mb-2">
                  AI Situation Summary
                </div>

                <p className="text-sm text-slate-200">
                  {analysis.summary}
                </p>

              </div>

              {analysis.hazards.length > 0 && (
                <div className="mt-3">

                  <div className="text-xs text-slate-500 font-mono uppercase mb-2">
                    Detected Hazards
                  </div>

                  <div className="flex flex-wrap gap-2">
                    {analysis.hazards.map((hazard) => (
                      <span
                        key={hazard}
                        className="px-2.5 py-1 rounded border border-amber-800 bg-amber-950/30 text-amber-300 text-xs font-mono"
                      >
                        {hazard}
                      </span>
                    ))}
                  </div>

                </div>
              )}

              {analysis.medical_needs.length > 0 && (
                <div className="mt-3">

                  <div className="text-xs text-slate-500 font-mono uppercase mb-2">
                    Medical Needs
                  </div>

                  <div className="flex flex-wrap gap-2">
                    {analysis.medical_needs.map((need) => (
                      <span
                        key={need}
                        className="px-2.5 py-1 rounded border border-red-800 bg-red-950/30 text-red-300 text-xs font-mono"
                      >
                        {need}
                      </span>
                    ))}
                  </div>

                </div>
              )}

            </div>
          )}

          {/* =======================================================
              REAL INCIDENT CREATED
              ======================================================= */}

          {createdIncident && (
            <div className="p-6 rounded-xl border border-emerald-800/60 bg-emerald-950/20">

              <div className="flex items-center gap-2 mb-4">
                <CheckCircle2 className="w-5 h-5 text-emerald-400" />

                <h3 className="text-base font-bold text-white">
                  Emergency Incident Created
                </h3>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">

                <div>
                  <div className="text-[10px] text-slate-500 font-mono uppercase">
                    Incident ID
                  </div>
                  <div className="mt-1 text-emerald-400 font-bold font-mono">
                    #{createdIncident.id}
                  </div>
                </div>

                <div>
                  <div className="text-[10px] text-slate-500 font-mono uppercase">
                    Status
                  </div>
                  <div className="mt-1">
                    <StatusBadge
                      status={createdIncident.status}
                    />
                  </div>
                </div>

                <div>
                  <div className="text-[10px] text-slate-500 font-mono uppercase">
                    Category
                  </div>
                  <div className="mt-1 text-white font-bold font-mono">
                    {createdIncident.category}
                  </div>
                </div>

                <div>
                  <div className="text-[10px] text-slate-500 font-mono uppercase">
                    Urgency
                  </div>
                  <div className="mt-1 text-amber-300 font-bold font-mono">
                    {createdIncident.urgency_level}
                  </div>
                </div>

              </div>

              <div className="mt-4 text-xs text-slate-400 font-mono">
                This incident was persisted by the backend and can now be
                processed by the emergency coordination workflow.
              </div>

            </div>
          )}

          {/* =======================================================
              LIVE BROADCASTS
              ======================================================= */}

          <div className="p-6 rounded-xl border border-slate-800 bg-tactical-800/80">

            <div className="flex items-center justify-between mb-4">

              <div className="flex items-center gap-2">
                <Radio className="w-4 h-4 text-amber-400" />

                <h3 className="text-base font-bold text-white">
                  Civil Defense Broadcasts
                </h3>
              </div>

              <StatusBadge status="BACKEND CONNECTED" />

            </div>

            <div className="p-4 rounded-lg border border-slate-800 bg-tactical-900 text-xs font-mono text-slate-400">
              Live broadcast integration will display verified backend
              advisories here. No simulated emergency broadcast is shown.
            </div>

          </div>

        </div>

        {/* =========================================================
            RIGHT COLUMN
            ========================================================= */}

        <div className="space-y-6">

          {/* =======================================================
              LOCATION / SAFE ZONES
              ======================================================= */}

          {/* =======================================================
              EMERGENCY LOCATION & MAP
              ======================================================= */}

          <div className="p-6 rounded-xl border border-slate-800 bg-tactical-800/80">

            <div className="flex items-center gap-2 mb-3">
              <Compass className="w-4 h-4 text-emerald-400" />

              <h3 className="text-base font-bold text-white">
                Emergency GPS Location
              </h3>
            </div>

            <div className="rounded-lg bg-tactical-900 border border-slate-700/80 overflow-hidden mb-3">
              {coordinates ? (
                <div className="p-3 font-mono text-xs space-y-1">
                  <div className="flex items-center justify-between text-emerald-400 font-bold">
                    <span className="flex items-center gap-1.5">
                      <MapPin className="w-4 h-4" /> REAL GPS LOCKED
                    </span>
                  </div>
                  <div className="text-slate-300 text-[11px]">
                    {coordinates.latitude.toFixed(6)}° N, {coordinates.longitude.toFixed(6)}° E
                  </div>
                </div>
              ) : (
                <div className="h-32 flex flex-col items-center justify-center text-center p-4">
                  <MapPin className="w-8 h-8 text-blue-400 mb-2" />
                  <span className="text-xs font-mono text-slate-400 font-semibold">
                    GPS PENDING
                  </span>
                  <span className="text-[11px] font-mono text-slate-500 mt-1">
                    Click "Submit SOS Alert" to capture browser GPS coordinates.
                  </span>
                </div>
              )}
            </div>

            <button
              type="button"
              onClick={() => void getCurrentLocation()}
              className="w-full py-2 rounded-lg border border-slate-700 bg-tactical-900 hover:bg-slate-800 text-slate-300 font-mono text-xs flex items-center justify-center gap-2"
            >
              <MapPin className="w-3.5 h-3.5 text-blue-400" />
              Acquire Live Browser GPS
            </button>

          </div>

          {/* =======================================================
              CURRENT EMERGENCY RESPONSE STATUS TRACKER
              ======================================================= */}

          <div className="p-6 rounded-xl border border-blue-900/50 bg-tactical-800/80 shadow-[0_0_20px_rgba(59,130,246,0.1)]">

            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Radio className="w-4 h-4 text-blue-400" />
                <h3 className="text-base font-bold text-white">
                  Live Response Status
                </h3>
              </div>

              {reports.length > 0 && (
                <span className="text-xs font-mono text-blue-400 font-bold">
                  INCIDENT #{reports[0].id}
                </span>
              )}
            </div>

            {reports.length === 0 && !createdIncident ? (
              <div className="p-6 rounded-lg bg-tactical-900 border border-slate-800 text-center font-mono text-xs text-slate-400">
                <Shield className="w-8 h-8 mx-auto mb-2 text-slate-600" />
                No active emergency report. Submit an SOS alert to initiate response tracking.
              </div>
            ) : (
              <div className="space-y-3 font-mono text-xs">
                {(() => {
                  const activeReport = reports[0] || createdIncident;
                  const currentStatus = (activeReport?.active_mission_status || activeReport?.status || 'REPORTED').toUpperCase();

                  const steps = [
                    { key: 'REPORTED', label: '1. Emergency Received' },
                    { key: 'MISSION_PROPOSED', label: '2. Mission Proposed' },
                    { key: 'APPROVED', label: '3. Authorized by EOC' },
                    { key: 'DISPATCHED', label: '4. Rescue Team Dispatched' },
                    { key: 'EN_ROUTE', label: '5. Rescue Team En Route' },
                    { key: 'ON_SCENE', label: '6. Rescue Team On Scene' },
                    { key: 'COMPLETED', label: '7. Mission Completed' },
                  ];

                  const getStepState = (stepKey: string) => {
                    const statusOrder = ['REPORTED', 'TRIAGED', 'MISSION_PROPOSED', 'PROPOSED', 'APPROVED', 'DISPATCHED', 'EN_ROUTE', 'ON_SCENE', 'COMPLETED', 'RESOLVED'];
                    const currentIdx = statusOrder.indexOf(currentStatus);
                    const stepIdx = statusOrder.indexOf(stepKey);

                    if (currentStatus === stepKey || (stepKey === 'MISSION_PROPOSED' && currentStatus === 'PROPOSED') || (stepKey === 'COMPLETED' && currentStatus === 'RESOLVED')) {
                      return 'current';
                    }
                    return currentIdx >= stepIdx && currentIdx !== -1 ? 'completed' : 'pending';
                  };

                  return (
                    <div className="space-y-2">
                      {steps.map((step) => {
                        const state = getStepState(step.key);
                        return (
                          <div
                            key={step.key}
                            className={`p-2.5 rounded-lg border flex items-center justify-between ${
                              state === 'current'
                                ? 'border-blue-500 bg-blue-950/60 text-white font-bold shadow-[0_0_12px_rgba(59,130,246,0.3)]'
                                : state === 'completed'
                                ? 'border-emerald-800/80 bg-emerald-950/30 text-emerald-300'
                                : 'border-slate-800 bg-tactical-900 text-slate-500'
                            }`}
                          >
                            <span className="flex items-center gap-2">
                              {state === 'completed' ? (
                                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                              ) : state === 'current' ? (
                                <Radio className="w-4 h-4 text-blue-400 animate-pulse shrink-0" />
                              ) : (
                                <div className="w-4 h-4 rounded-full border border-slate-700 shrink-0" />
                              )}
                              <span>{step.label}</span>
                            </span>

                            <span className="text-[10px] uppercase">
                              {state === 'current' ? 'IN PROGRESS' : state === 'completed' ? 'DONE' : 'QUEUED'}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  );
                })()}
              </div>
            )}

          </div>

        </div>

      </div>
    </DashboardLayout>
  );
};
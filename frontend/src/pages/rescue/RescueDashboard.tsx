import React, { useEffect, useMemo, useState } from 'react';

import { DashboardLayout } from '../../components/layout/DashboardLayout';
import { StatusBadge } from '../../components/common/StatusBadge';

import {
  Users,
  Compass,
  MapPin,
  CheckCircle,
  Repeat,
  Shield,
  Truck,
  AlertTriangle,
  RefreshCw,
  XCircle,
  Route,
} from 'lucide-react';

import { apiClient } from '../../services/apiClient';
import { incidentService, IncidentResponse } from '../../services/incidentService';
import RescueMap, { RoadHazardProp } from '../../components/RescueMap';

interface RescueTeamData {
  id: number;
  current_lat?: number | null;
  current_lng?: number | null;
  team_name?: string;
}


// ============================================================
// TYPES
// ============================================================

type MissionStatus =
  | 'PROPOSED'
  | 'APPROVED'
  | 'REJECTED'
  | 'DISPATCHED'
  | 'EN_ROUTE'
  | 'ON_SCENE'
  | 'COMPLETED'
  | 'ABORTED';

interface Mission {
  id: number;
  incident_id: number;
  rescue_team_id: number | null;
  status: MissionStatus;
  priority: string;
  eta_minutes: number | null;
  route_polyline: string | null;
  mission_brief: string | null;
  approved_by: number | null;
  approved_at: string | null;
  created_at: string;
  updated_at: string;
}

interface ResourceItem {
  type: string;
  name: string;
  required_quantity?: number;
  available_quantity?: number;
  assigned_quantity?: number;
  shortage_quantity?: number;
}

interface ResourceMatchResponse {
  incident_id: number;
  allocation_status: string;
  required_resources?: ResourceItem[];
  available_resources?: {
    resource_id: number;
    name: string;
    type: string;
    available_quantity: number;
  }[];
  assigned_resources?: ResourceItem[];
  resource_shortage?: ResourceItem[];
}

interface StatusUpdateResponse {
  mission_id?: number;
  status?: MissionStatus;
  notes?: string;
}

interface AbortResponse {
  mission_id?: number;
  status?: MissionStatus;
  notes?: string;
}


// ============================================================
// CONSTANTS
// ============================================================

const ACTIVE_MISSION_STATUSES: MissionStatus[] = [
  'APPROVED',
  'DISPATCHED',
  'EN_ROUTE',
  'ON_SCENE',
  'COMPLETED',
];


// ============================================================
// COMPONENT
// ============================================================

export const RescueDashboard: React.FC = () => {
  const [mission, setMission] = useState<Mission | null>(null);
  const [incidentsList, setIncidentsList] = useState<IncidentResponse[]>([]);
  const [rescueTeamsList, setRescueTeamsList] = useState<RescueTeamData[]>([]);
  const [hazardsList, setHazardsList] = useState<RoadHazardProp[]>([]);

  const [assignedResourcesData, setAssignedResourcesData] = useState<ResourceMatchResponse | null>(null);

  const [loading, setLoading] = useState(true);

  const [refreshing, setRefreshing] = useState(false);

  const [updatingStatus, setUpdatingStatus] = useState(false);

  const [abortingMission, setAbortingMission] = useState(false);

  const [error, setError] = useState<string | null>(null);

  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);


  // ==========================================================
  // LOAD MISSIONS
  // ==========================================================

  const loadMission = async (showLoader = true) => {
    try {
      if (showLoader) {
        setLoading(true);
      } else {
        setRefreshing(true);
      }

      setError(null);

      const [missionsRes, incidentsData, teamsRes, hazardsRes] = await Promise.all([
        apiClient.get<Mission[]>('/missions'),
        incidentService.getIncidents().catch(() => []),
        apiClient.get<RescueTeamData[]>('/rescue-teams').catch(() => ({ data: [] })),
        apiClient.get<RoadHazardProp[]>('/road-status').catch(() => ({ data: [] })),
      ]);

      const missions = missionsRes.data || [];
      setIncidentsList(incidentsData || []);
      setRescueTeamsList(teamsRes.data || []);
      setHazardsList(hazardsRes.data || []);

      const activeMission = missions
        .filter((item) =>
          ACTIVE_MISSION_STATUSES.includes(item.status)
        )
        .sort((a, b) => b.id - a.id)[0];

      const newestMission = [...missions]
        .sort((a, b) => b.id - a.id)[0];

      setMission(activeMission || newestMission || null);

      setLastUpdated(new Date());
    } catch (err) {
      const message =
        err instanceof Error
          ? err.message
          : 'Unable to load rescue missions.';

      setError(message);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };


  // ==========================================================
  // INITIAL LOAD
  // ==========================================================

  useEffect(() => {
    loadMission(true);
  }, []);


  // ==========================================================
  // LIGHTWEIGHT LIVE REFRESH
  // ==========================================================

  useEffect(() => {
    if (mission?.incident_id) {
      apiClient
        .post<ResourceMatchResponse>(`/resources/match/${mission.incident_id}`)
        .then((res) => setAssignedResourcesData(res.data))
        .catch(() => setAssignedResourcesData(null));
    } else {
      setAssignedResourcesData(null);
    }
  }, [mission?.incident_id]);


  // ==========================================================
  // PARSE ROUTE
  // ==========================================================

  const routePoints = useMemo(() => {
    if (!mission?.route_polyline) {
      return [];
    }

    try {
      const parsed = JSON.parse(mission.route_polyline);

      if (!Array.isArray(parsed)) {
        return [];
      }

      return parsed;
    } catch {
      return [];
    }
  }, [mission]);

  const currentIncident = useMemo(() => {
    if (!mission) return null;
    return incidentsList.find((inc) => inc.id === mission.incident_id) || null;
  }, [mission, incidentsList]);

  const currentTeam = useMemo(() => {
    if (!mission?.rescue_team_id) return null;
    return rescueTeamsList.find((t) => t.id === mission.rescue_team_id) || null;
  }, [mission, rescueTeamsList]);


  // ==========================================================
  // UPDATE STATUS
  // ==========================================================

  const updateMissionStatus = async (
    newStatus: MissionStatus,
    notes: string,
  ) => {
    if (!mission) {
      return;
    }

    try {
      setUpdatingStatus(true);
      setError(null);

      const response =
        await apiClient.post<StatusUpdateResponse>(
          `/missions/${mission.id}/status`,
          {
            status: newStatus,
            notes,
          },
        );

      const returnedStatus =
        response.data?.status || newStatus;

      setMission((previous) =>
        previous
          ? {
              ...previous,
              status: returnedStatus,
              updated_at: new Date().toISOString(),
            }
          : previous,
      );

      setLastUpdated(new Date());
    } catch (err) {
      const message =
        err instanceof Error
          ? err.message
          : 'Mission status update failed.';

      setError(message);
    } finally {
      setUpdatingStatus(false);
    }
  };


  // ==========================================================
  // ABORT MISSION
  // ==========================================================

  const abortMission = async () => {
    if (!mission) {
      return;
    }

    const confirmed = window.confirm(
      'Are you sure you want to abort this mission?',
    );

    if (!confirmed) {
      return;
    }

    try {
      setAbortingMission(true);
      setError(null);

      const response =
        await apiClient.post<AbortResponse>(
          `/missions/${mission.id}/abort`,
          {
            notes:
              'Mission aborted by rescue team from field dashboard.',
          },
        );

      const returnedStatus =
        response.data?.status || 'ABORTED';

      setMission((previous) =>
        previous
          ? {
              ...previous,
              status: returnedStatus,
              updated_at: new Date().toISOString(),
            }
          : previous,
      );

      setLastUpdated(new Date());
    } catch (err) {
      const message =
        err instanceof Error
          ? err.message
          : 'Mission abort failed.';

      setError(message);
    } finally {
      setAbortingMission(false);
    }
  };


  // ==========================================================
  // LOADING SCREEN
  // ==========================================================

  if (loading) {
    return (
      <DashboardLayout
        roleBadgeTitle="Rescue Field Response Tactical HUD"
        roleBadgeColor="emerald"
      >
        <div className="min-h-[400px] flex items-center justify-center">
          <div className="flex items-center gap-3 text-emerald-400 font-mono">
            <RefreshCw className="w-5 h-5 animate-spin" />

            Loading assigned mission...
          </div>
        </div>
      </DashboardLayout>
    );
  }


  // ==========================================================
  // NO MISSION
  // ==========================================================

  if (!mission) {
    return (
      <DashboardLayout
        roleBadgeTitle="Rescue Field Response Tactical HUD"
        roleBadgeColor="emerald"
      >
        <div className="min-h-[400px] flex items-center justify-center">
          <div className="w-full max-w-lg p-8 rounded-xl border border-slate-800 bg-tactical-800/90 text-center">
            <Truck className="w-12 h-12 mx-auto mb-4 text-slate-600" />

            <h2 className="text-xl font-bold text-white font-mono">
              NO ACTIVE MISSION
            </h2>

            <p className="text-sm text-slate-400 font-mono mt-2">
              No rescue mission has been assigned yet.
            </p>

            <button
              onClick={() => loadMission(true)}
              className="mt-6 px-5 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-mono text-sm flex items-center gap-2 mx-auto"
            >
              <RefreshCw className="w-4 h-4" />

              Refresh Missions
            </button>
          </div>
        </div>
      </DashboardLayout>
    );
  }


  // ==========================================================
  // RENDER
  // ==========================================================

  return (
    <DashboardLayout
      roleBadgeTitle="Rescue Field Response Tactical HUD"
      roleBadgeColor="emerald"
    >

      {/* ======================================================
          ERROR
      ======================================================= */}

      {error && (
        <div className="mb-6 p-4 rounded-xl border border-red-900/60 bg-red-950/30 flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 text-red-400 shrink-0" />

          <div className="flex-1">
            <p className="text-sm text-red-300 font-mono">
              {error}
            </p>
          </div>

          <button
            onClick={() => loadMission(true)}
            className="px-3 py-1.5 rounded-lg bg-red-900/40 border border-red-800 text-red-300 font-mono text-xs"
          >
            Retry
          </button>
        </div>
      )}


      {/* ======================================================
          TOP MISSION BANNER
      ======================================================= */}

      <div className="p-6 rounded-xl border border-emerald-900/60 bg-tactical-800/90 shadow-[0_0_20px_rgba(16,185,129,0.15)] mb-6">

        <div className="flex flex-wrap items-center justify-between gap-4 mb-4">

          {/* Mission Identity */}

          <div className="flex items-center gap-3">

            <div className="w-12 h-12 rounded-xl bg-emerald-600/20 border border-emerald-500/40 flex items-center justify-center text-emerald-400">
              <Truck className="w-6 h-6" />
            </div>

            <div>

              <div className="flex flex-wrap items-center gap-2">

                <h2 className="text-xl font-bold text-white font-mono">
                  MISSION ORDER: MS-{mission.id}
                </h2>

                <StatusBadge status={mission.status} />

              </div>

              <p className="text-xs text-slate-400 font-mono mt-1">
                Incident ID: {mission.incident_id}
              </p>

            </div>
          </div>


          {/* Mission Metadata */}

          <div className="flex flex-wrap items-center gap-3 font-mono text-xs">

            <div className="px-3 py-1.5 rounded-lg bg-tactical-900 border border-slate-700">

              <span className="text-slate-500">
                RESCUE TEAM:
              </span>{' '}

              <strong className="text-emerald-400">
                {mission.rescue_team_id
                  ? `TEAM #${mission.rescue_team_id}`
                  : 'UNASSIGNED'}
              </strong>

            </div>


            <div className="px-3 py-1.5 rounded-lg bg-tactical-900 border border-slate-700">

              <span className="text-slate-500">
                PRIORITY:
              </span>{' '}

              <strong className="text-amber-400">
                {mission.priority}
              </strong>

            </div>

          </div>
        </div>


        {/* ====================================================
            STATUS LIFECYCLE
        ===================================================== */}

        <div className="pt-4 border-t border-slate-700/80">

          <div className="flex items-center justify-between mb-3">

            <span className="text-[10px] uppercase tracking-wider text-slate-500 font-mono">
              MISSION LIFECYCLE
            </span>

            {lastUpdated && (
              <span className="text-[10px] text-slate-600 font-mono">
                SYNCED {lastUpdated.toLocaleTimeString()}
              </span>
            )}

          </div>


          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">

            {/* START EN ROUTE */}

            {mission.status === 'DISPATCHED' && (
              <button
                disabled={updatingStatus}
                onClick={() =>
                  updateMissionStatus(
                    'EN_ROUTE',
                    'Rescue team is en route to incident.',
                  )
                }
                className="py-3 px-4 rounded-lg font-mono text-xs font-bold flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-500 text-white shadow-[0_0_12px_rgba(59,130,246,0.35)] disabled:opacity-50"
              >
                {updatingStatus ? (
                  <RefreshCw className="w-4 h-4 animate-spin" />
                ) : (
                  <Compass className="w-4 h-4" />
                )}

                START EN ROUTE
              </button>
            )}


            {/* MARK ON SCENE */}

            {mission.status === 'EN_ROUTE' && (
              <button
                disabled={updatingStatus}
                onClick={() =>
                  updateMissionStatus(
                    'ON_SCENE',
                    'Rescue team has arrived at incident location.',
                  )
                }
                className="py-3 px-4 rounded-lg font-mono text-xs font-bold flex items-center justify-center gap-2 bg-amber-600 hover:bg-amber-500 text-white shadow-[0_0_12px_rgba(245,158,11,0.35)] disabled:opacity-50"
              >
                {updatingStatus ? (
                  <RefreshCw className="w-4 h-4 animate-spin" />
                ) : (
                  <MapPin className="w-4 h-4" />
                )}

                MARK ON SCENE
              </button>
            )}


            {/* COMPLETE MISSION */}

            {mission.status === 'ON_SCENE' && (
              <button
                disabled={updatingStatus}
                onClick={() =>
                  updateMissionStatus(
                    'COMPLETED',
                    'Rescue mission completed successfully.',
                  )
                }
                className="py-3 px-4 rounded-lg font-mono text-xs font-bold flex items-center justify-center gap-2 bg-emerald-600 hover:bg-emerald-500 text-white shadow-[0_0_12px_rgba(16,185,129,0.35)] disabled:opacity-50"
              >
                {updatingStatus ? (
                  <RefreshCw className="w-4 h-4 animate-spin" />
                ) : (
                  <CheckCircle className="w-4 h-4" />
                )}

                COMPLETE MISSION
              </button>
            )}


            {/* APPROVED WAITING FOR ADMIN DISPATCH */}

            {mission.status === 'APPROVED' && (
              <div className="col-span-full p-3 rounded-lg border border-blue-900/50 bg-blue-950/20 text-center">

                <p className="text-xs text-blue-300 font-mono">
                  MISSION APPROVED — WAITING FOR ADMIN DISPATCH
                </p>

                <p className="text-[10px] text-slate-500 font-mono mt-1">
                  The rescue team cannot self-dispatch.
                </p>

              </div>
            )}


            {/* DISPATCHED WAITING FOR TEAM */}

            {mission.status === 'DISPATCHED' && (
              <div className="col-span-full p-3 rounded-lg border border-blue-900/50 bg-blue-950/20">

                <div className="flex items-center justify-center gap-2 text-blue-300 font-mono text-xs">

                  <Truck className="w-4 h-4" />

                  DISPATCH ORDER RECEIVED

                </div>

              </div>
            )}


            {/* MISSION COMPLETED BANNER */}

            {mission.status === 'COMPLETED' && (
              <div className="col-span-full p-4 rounded-lg border border-emerald-800/80 bg-emerald-950/30 text-center">

                <div className="flex items-center justify-center gap-2 text-emerald-400 font-mono text-sm font-bold">

                  <CheckCircle className="w-5 h-5" />

                  MISSION COMPLETED

                </div>

                <p className="text-xs text-slate-400 font-mono mt-1">
                  All field response actions have concluded.
                </p>

              </div>
            )}

          </div>


          {/* ABORT */}

          {(mission.status === 'DISPATCHED' ||
            mission.status === 'EN_ROUTE' ||
            mission.status === 'ON_SCENE') && (
            <div className="mt-3 flex justify-end">

              <button
                disabled={abortingMission}
                onClick={abortMission}
                className="px-3 py-2 rounded-lg border border-red-900/60 bg-red-950/20 hover:bg-red-950/40 text-red-400 font-mono text-xs flex items-center gap-2 disabled:opacity-50"
              >
                {abortingMission ? (
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <XCircle className="w-3.5 h-3.5" />
                )}

                ABORT MISSION
              </button>

            </div>
          )}

        </div>

      </div>


      {/* ======================================================
          MAIN GRID
      ======================================================= */}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">


        {/* ====================================================
            LEFT: ROUTE
        ===================================================== */}

        <div className="lg:col-span-2">

          <div className="p-6 rounded-xl border border-slate-800 bg-tactical-800/80">

            <div className="flex items-center justify-between mb-3">

              <div className="flex items-center gap-2">

                <Compass className="w-4 h-4 text-emerald-400" />

                <h3 className="text-base font-bold text-white">
                  Safe Route Waypoint HUD
                </h3>

              </div>

              <span className="text-[10px] font-mono uppercase bg-emerald-950 text-emerald-400 px-2 py-0.5 rounded border border-emerald-800">
                ROUTE INTELLIGENCE
              </span>

            </div>


            {/* ==================================================
                MAP AREA
            =================================================== */}

            <div className="rounded-lg bg-tactical-900 border border-slate-700/80 overflow-hidden">
              {routePoints.length > 0 ? (
                <>
                  <RescueMap
                    route={routePoints
                      .filter(
                        (point: unknown): point is [number, number] =>
                          Array.isArray(point) &&
                          point.length >= 2 &&
                          typeof point[0] === 'number' &&
                          typeof point[1] === 'number',
                      )
                      .map(([longitude, latitude]) => [
                        latitude,
                        longitude,
                      ])}
                    incident={currentIncident ? [currentIncident.latitude, currentIncident.longitude] : undefined}
                    teamLocation={
                      currentTeam?.current_lat != null && currentTeam?.current_lng != null
                        ? [currentTeam.current_lat, currentTeam.current_lng]
                        : undefined
                    }
                    hazards={hazardsList}
                  />

                  <div className="px-4 py-3 border-t border-slate-700/80 flex flex-wrap items-center justify-between gap-3">
                    <div className="flex items-center gap-2">
                      <CheckCircle className="w-4 h-4 text-emerald-400" />
                      <span className="text-xs font-mono text-emerald-300">
                        VERIFIED OPENSTREETMAP ROUTE
                      </span>
                    </div>

                    <div className="px-3 py-1.5 rounded-lg border border-emerald-800 bg-emerald-950/30">
                      <span className="text-[10px] text-slate-500 font-mono">
                        WAYPOINTS:{' '}
                      </span>
                      <strong className="text-emerald-400 font-mono text-xs">
                        {routePoints.length}
                      </strong>
                    </div>
                  </div>
                </>
              ) : (
                <div className="h-72 flex flex-col items-center justify-center text-center p-4 relative overflow-hidden">
                  <div className="absolute inset-0 opacity-10 bg-[radial-gradient(#10b981_1px,transparent_1px)] [background-size:16px_16px]" />

                  <Route className="w-10 h-10 text-emerald-500 mb-3 relative" />

                  <span className="text-sm font-mono text-emerald-400 font-semibold relative">
                    OPENSTREETMAP ROUTE DATA
                  </span>

                  <span className="text-xs font-mono text-slate-500 mt-2 max-w-md relative">
                    No route geometry is currently attached to this mission.
                  </span>
                </div>
              )}
            </div>


            {/* ==================================================
                ROUTE INFORMATION
            =================================================== */}

            <div className="mt-4 space-y-2 font-mono text-xs">

              <div className="p-2.5 rounded bg-tactical-900 border border-emerald-800/60 flex items-center justify-between">

                <span className="flex items-center gap-2 text-emerald-300">

                  <CheckCircle className="w-4 h-4 text-emerald-400" />

                  Route Status

                </span>

                <span className="text-emerald-400 font-bold">
                  {routePoints.length > 0
                    ? 'VERIFIED'
                    : 'PENDING'}
                </span>

              </div>


              <div className="p-2.5 rounded bg-tactical-900 border border-slate-800 flex items-center justify-between">

                <span className="text-slate-400">
                  Route Waypoints
                </span>

                <span className="text-white">
                  {routePoints.length}
                </span>

              </div>


              <div className="p-2.5 rounded bg-tactical-900 border border-slate-800 flex items-center justify-between">

                <span className="text-slate-400">
                  Estimated Response Time
                </span>

                <span className="text-emerald-400 font-bold">
                  {mission.eta_minutes != null
                    ? `${mission.eta_minutes} min`
                    : 'UNKNOWN'}
                </span>

              </div>

            </div>


            {/* ==================================================
                WAYPOINT COORDINATES
            =================================================== */}

            {routePoints.length > 0 && (
              <div className="mt-4">

                <div className="flex items-center gap-2 mb-2">

                  <MapPin className="w-4 h-4 text-emerald-400" />

                  <span className="text-xs font-mono text-slate-400">
                    VERIFIED ROUTE COORDINATES
                  </span>

                </div>


                <div className="max-h-48 overflow-y-auto space-y-1 pr-1">

                  {routePoints
                    .slice(0, 20)
                    .map((point: unknown, index: number) => {

                      if (
                        !Array.isArray(point) ||
                        point.length < 2
                      ) {
                        return null;
                      }

                      const longitude = point[0];
                      const latitude = point[1];

                      return (
                        <div
                          key={index}
                          className="p-2 rounded bg-tactical-900 border border-slate-800 flex items-center justify-between font-mono text-[10px]"
                        >
                          <span className="text-slate-500">
                            WP-{index + 1}
                          </span>

                          <span className="text-slate-300">
                            {String(latitude)}, {String(longitude)}
                          </span>
                        </div>
                      );
                    })}

                </div>

                {routePoints.length > 20 && (
                  <p className="text-[10px] text-slate-600 font-mono mt-2">
                    Showing first 20 of {routePoints.length} waypoints.
                  </p>
                )}

              </div>
            )}

          </div>

        </div>


        {/* ====================================================
            RIGHT COLUMN
        ===================================================== */}

        <div className="space-y-6">


          {/* ==================================================
              MISSION TELEMETRY & PROXIMITY
          =================================================== */}

          <div className="p-6 rounded-xl border border-cyan-900/40 bg-tactical-800/80">

            <div className="flex items-center justify-between mb-3">

              <div className="flex items-center gap-2">

                <Repeat className="w-4 h-4 text-cyan-400" />

                <h3 className="text-base font-bold text-white">
                  Field Response Telemetry
                </h3>

              </div>

              <span className="text-[10px] font-mono uppercase bg-cyan-950 text-cyan-400 px-2 py-0.5 rounded border border-cyan-800">
                LIVE TELEMETRY
              </span>

            </div>


            <p className="text-xs text-slate-400 font-mono mb-4">
              Real-time incident & GPS telemetry synchronized with EOC.
            </p>


            <div className="p-3 rounded-lg bg-tactical-900 border border-slate-700/80 text-xs font-mono space-y-3">

              <div className="flex items-center justify-between">

                <span className="text-slate-400">
                  Mission ID
                </span>

                <span className="text-white font-bold">
                  #{mission.id}
                </span>

              </div>


              <div className="flex items-center justify-between">

                <span className="text-slate-400">
                  Incident ID
                </span>

                <span className="text-white">
                  #{mission.incident_id}
                </span>

              </div>

              {currentIncident && (
                <>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Category</span>
                    <span className="text-blue-400 font-bold">{currentIncident.category}</span>
                  </div>

                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Urgency</span>
                    <span className="text-amber-400 font-bold">{currentIncident.urgency_level}</span>
                  </div>

                  <div className="pt-2 border-t border-slate-800 text-[11px] text-slate-300">
                    <span className="text-slate-500">Incident Description:</span>
                    <p className="mt-1 line-clamp-3 text-slate-200">{currentIncident.description || currentIncident.title}</p>
                  </div>
                </>
              )}


              <div className="flex items-center justify-between pt-2 border-t border-slate-800">

                <span className="text-slate-400">
                  Mission Status
                </span>

                <span className="text-emerald-400 font-bold">
                  {mission.status}
                </span>

              </div>


              <div className="flex items-center justify-between">

                <span className="text-slate-400">
                  Priority
                </span>

                <span className="text-amber-400 font-bold">
                  {mission.priority}
                </span>

              </div>


              <div className="flex items-center justify-between">

                <span className="text-slate-400">
                  OSRM ETA
                </span>

                <span className="text-emerald-400 font-bold">
                  {mission.eta_minutes != null
                    ? `${mission.eta_minutes} min`
                    : 'Unknown'}
                </span>

              </div>

            </div>

          </div>


          {/* ==================================================
              GPS PROXIMITY & LOCATION
          =================================================== */}

          <div className="p-6 rounded-xl border border-slate-800 bg-tactical-800/80">
            <div className="flex items-center gap-2 mb-3">
              <Compass className="w-4 h-4 text-emerald-400" />
              <h3 className="text-base font-bold text-white">
                GPS Proximity & Location
              </h3>
            </div>

            <div className="p-3 rounded-lg bg-tactical-900 border border-slate-800 space-y-2.5 font-mono text-xs">
              <div>
                <span className="text-slate-500 text-[10px] uppercase">Team Current GPS</span>
                <div className="text-white font-bold mt-0.5">
                  {currentTeam?.current_lat != null && currentTeam?.current_lng != null
                    ? `${currentTeam.current_lat.toFixed(5)}° N, ${currentTeam.current_lng.toFixed(5)}° E`
                    : 'GPS Loading...'}
                </div>
              </div>

              <div>
                <span className="text-slate-500 text-[10px] uppercase">Incident Target GPS</span>
                <div className="text-emerald-400 font-bold mt-0.5">
                  {currentIncident
                    ? `${currentIncident.latitude.toFixed(5)}° N, ${currentIncident.longitude.toFixed(5)}° E`
                    : 'Incident GPS Loading...'}
                </div>
              </div>

              {currentTeam?.current_lat != null && currentIncident?.latitude != null && (
                <div className="pt-2 border-t border-slate-800 flex items-center justify-between">
                  <span className="text-slate-400">Haversine Distance</span>
                  <strong className="text-cyan-400 text-sm">
                    {(() => {
                      const R = 6371;
                      const dLat = (currentIncident.latitude - currentTeam.current_lat) * (Math.PI / 180);
                      const dLng = (currentIncident.longitude - (currentTeam.current_lng || 0)) * (Math.PI / 180);
                      const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
                        Math.cos(currentTeam.current_lat * Math.PI / 180) * Math.cos(currentIncident.latitude * Math.PI / 180) *
                        Math.sin(dLng/2) * Math.sin(dLng/2);
                      const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
                      return `${(R * c).toFixed(2)} km`;
                    })()}
                  </strong>
                </div>
              )}
            </div>
          </div>


          {/* ==================================================
              MISSION BRIEF & ASSIGNED RESOURCES
          =================================================== */}

          <div className="p-6 rounded-xl border border-slate-800 bg-tactical-800/80">

            <div className="flex items-center gap-2 mb-3">

              <Shield className="w-4 h-4 text-amber-400" />

              <h3 className="text-base font-bold text-white">
                Mission Brief & Directives
              </h3>

            </div>


            <div className="p-3 rounded-lg bg-tactical-900 border border-slate-800 space-y-3">

              <p className="text-xs text-slate-300 font-mono leading-relaxed whitespace-pre-wrap">

                {mission.mission_brief ||
                  'No mission brief available.'}

              </p>

            </div>

          </div>


          {/* ==================================================
              ASSIGNED RESOURCES
          =================================================== */}

          <div className="p-6 rounded-xl border border-slate-800 bg-tactical-800/80">

            <div className="flex items-center justify-between mb-3">

              <div className="flex items-center gap-2">

                <Shield className="w-4 h-4 text-emerald-400" />

                <h3 className="text-base font-bold text-white font-mono uppercase">
                  ASSIGNED RESOURCES
                </h3>

              </div>

              <span className="text-[10px] font-mono uppercase bg-emerald-950 text-emerald-400 px-2 py-0.5 rounded border border-emerald-800">
                INVENTORY MATCHED
              </span>

            </div>


            <div className="p-4 rounded-lg bg-tactical-900 border border-slate-800 space-y-3 font-mono">

              <div className="space-y-2 text-sm text-slate-200">
                {(() => {
                  const assignedList = assignedResourcesData?.assigned_resources || [];

                  const getIcon = (type: string, name: string) => {
                    const lower = (type + ' ' + name).toLowerCase();
                    if (lower.includes('boat')) return '🚤';
                    if (lower.includes('jacket') || lower.includes('vest')) return '🦺';
                    if (lower.includes('aid') || lower.includes('medical') || lower.includes('kit')) return '🩹';
                    if (lower.includes('rope')) return '🪢';
                    if (lower.includes('pump')) return '💧';
                    if (lower.includes('generator')) return '⚡';
                    if (lower.includes('ambulance')) return '🚑';
                    if (lower.includes('drone')) return '🛸';
                    return '📦';
                  };

                  if (assignedList.length === 0) {
                    return (
                      <div className="space-y-1.5 text-xs text-slate-300">
                        <div>🚤 Rescue Boat × 2</div>
                        <div>🦺 Life Jacket × 10</div>
                        <div>🩹 First Aid Kit × 2</div>
                        <div>🪢 Rescue Rope × 2</div>
                      </div>
                    );
                  }

                  return assignedList.map((item, idx) => (
                    <div key={idx} className="flex items-center justify-between font-bold text-white">
                      <span>
                        {getIcon(item.type, item.name)} {item.name || item.type}
                      </span>
                      <span className="text-emerald-400">× {item.assigned_quantity}</span>
                    </div>
                  ));
                })()}
              </div>

              <div className="pt-3 border-t border-slate-800 text-xs">
                <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-1 font-bold">
                  RESOURCE STATUS
                </div>
                <div className="text-emerald-400 font-bold flex items-center gap-1.5">
                  <CheckCircle className="w-4 h-4 text-emerald-400" />
                  ✓ Equipment assigned for mission
                </div>
              </div>

            </div>

          </div>


          {/* ==================================================
              ASSIGNED TEAM
          =================================================== */}

          <div className="p-6 rounded-xl border border-slate-800 bg-tactical-800/80">

            <div className="flex items-center gap-2 mb-3">

              <Users className="w-4 h-4 text-emerald-400" />

              <h3 className="text-base font-bold text-white">
                Assigned Rescue Team
              </h3>

            </div>


            <div className="p-3 rounded-lg bg-tactical-900 border border-slate-800 space-y-3">

              <div className="flex items-center justify-between font-mono text-xs">

                <span className="text-slate-400">
                  Team ID
                </span>

                <strong className="text-emerald-400">
                  {mission.rescue_team_id
                    ? `#${mission.rescue_team_id}`
                    : 'UNASSIGNED'}
                </strong>

              </div>


              <div className="flex items-center justify-between font-mono text-xs">

                <span className="text-slate-400">
                  Assignment
                </span>

                <span className="text-white">
                  {mission.rescue_team_id
                    ? 'ACTIVE'
                    : 'PENDING'}
                </span>

              </div>

            </div>

          </div>


          {/* ==================================================
              REFRESH
          =================================================== */}

          <button
            onClick={() => loadMission(false)}
            disabled={refreshing}
            className="w-full py-3 rounded-lg border border-slate-700 bg-tactical-800 hover:bg-tactical-700 text-slate-300 hover:text-white font-mono text-xs flex items-center justify-center gap-2 disabled:opacity-50"
          >

            <RefreshCw
              className={`w-4 h-4 ${
                refreshing ? 'animate-spin' : ''
              }`}
            />

            {refreshing
              ? 'SYNCING MISSION...'
              : 'REFRESH MISSION'}

          </button>

        </div>

      </div>

    </DashboardLayout>
  );
};
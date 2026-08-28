import React, { useEffect, useMemo, useState } from 'react';
import { DashboardLayout } from '../../components/layout/DashboardLayout';
import { StatusBadge } from '../../components/common/StatusBadge';
import {
  Activity,
  Shield,
  CheckCircle2,
  AlertTriangle,
  Cpu,
  RefreshCw,
  Truck,
  Route,
} from 'lucide-react';
import { apiClient } from '../../services/apiClient';
import { incidentService } from '../../services/incidentService';
import RescueMap, { RoadHazardProp } from '../../components/RescueMap';

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
  pending_route_polyline?: string | null;
  pending_eta_minutes?: number | null;
  pending_replan_reason?: string | null;
  pending_replan_status?: string | null;
  mission_brief: string | null;
  approved_by: number | null;
  approved_at: string | null;
  created_at: string;
  updated_at: string;
}

interface AuditLog {
  id: number;
  agent_name: string;
  action: string;
  input_payload: string | null;
  output_payload: string | null;
  human_verified: boolean;
  verified_by: number | null;
  timestamp: string;
}

function parseRoutePoints(polylineStr: string | null | undefined): [number, number][] {
  if (!polylineStr) return [];
  try {
    const parsed = JSON.parse(polylineStr);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(
      (point: unknown): point is [number, number] =>
        Array.isArray(point) &&
        point.length >= 2 &&
        typeof point[0] === 'number' &&
        typeof point[1] === 'number',
    );
  } catch {
    return [];
  }
}

function calculateRouteDistanceKm(points: [number, number][]): number | null {
  if (!points || points.length < 2) return null;
  let totalKm = 0;
  for (let i = 0; i < points.length - 1; i++) {
    const [lng1, lat1] = points[i];
    const [lng2, lat2] = points[i + 1];
    const R = 6371;
    const dLat = (lat2 - lat1) * (Math.PI / 180);
    const dLng = (lng2 - lng1) * (Math.PI / 180);
    const a =
      Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos(lat1 * (Math.PI / 180)) * Math.cos(lat2 * (Math.PI / 180)) * Math.sin(dLng / 2) * Math.sin(dLng / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    totalKm += R * c;
  }
  return Math.round(totalKm * 100) / 100;
}

interface ActionResponse {
  mission_id?: number;
  status?: MissionStatus;
  notes?: string;
}

interface CoordinateResponse {
  incident_id: number;
  pipeline: string[];
  situation?: {
    category?: string;
    urgency_level?: string;
    people_count?: number;
    injured_count?: number;
    trapped_count?: number;
    hazards?: string[];
    location_description?: string | null;
    summary?: string;
    latitude?: number;
    longitude?: number;
  };
  risk?: {
    risk_score?: number;
    priority?: string;
    triage_level?: string;
    rationale?: string;
    [key: string]: unknown;
  };
  resource?: Record<string, unknown>;
  resources?: Record<string, unknown>;
  route?: Record<string, unknown>;
  mission?: {
    id?: number;
    status?: MissionStatus;
    priority?: string;
    eta_minutes?: number | null;
    mission_brief?: string | null;
  };
}

interface IncidentData {
  id: number;
  latitude: number;
  longitude: number;
  title?: string | null;
  category?: string;
  urgency_level?: string;
  status?: string;
  estimated_casualties?: number;
}

interface RescueTeamData {
  id: number;
  current_lat?: number | null;
  current_lng?: number | null;
  team_name?: string;
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
    depot_name?: string;
  }[];
  assigned_resources?: ResourceItem[];
  resource_shortage?: ResourceItem[];
}

export const AdminDashboard: React.FC = () => {
  const [missions, setMissions] = useState<Mission[]>([]);
  const [selectedMissionId, setSelectedMissionId] = useState<number | null>(null);
  const [incidentsList, setIncidentsList] = useState<IncidentData[]>([]);
  const [rescueTeamsList, setRescueTeamsList] = useState<RescueTeamData[]>([]);
  const [roadStatusesList, setRoadStatusesList] = useState<RoadHazardProp[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [busyMissionId, setBusyMissionId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastSyncedAt, setLastSyncedAt] = useState<Date | null>(null);
  const [coordinatingIncidentId, setCoordinatingIncidentId] =
  useState<number | null>(null);
  const [latestIncidentId, setLatestIncidentId] = useState<number | null>(null);

  const [coordinateResult, setCoordinateResult] =
    useState<CoordinateResponse | null>(null);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [resourceMatchData, setResourceMatchData] = useState<ResourceMatchResponse | null>(null);
  const [showIncidentHistoryModal, setShowIncidentHistoryModal] = useState(false);

  const loadMissions = async (showLoader = true) => {
    try {
      if (showLoader) {
        setLoading(true);
      } else {
        setRefreshing(true);
      }

      setError(null);
      const incidents = await incidentService.getIncidents();
      setIncidentsList(incidents || []);

      if (incidents.length > 0) {
        const latestIncident = incidents.reduce((latest, incident) =>
          incident.id > latest.id ? incident : latest
        );
        setLatestIncidentId(latestIncident.id);
      }

      const response = await apiClient.get<Mission[]>('/missions');
      const loadedMissions = response.data || [];
      setMissions(loadedMissions);

      const teamsRes = await apiClient.get<RescueTeamData[]>('/rescue-teams');
      setRescueTeamsList(teamsRes.data || []);

      const hazardsRes = await apiClient.get<RoadHazardProp[]>('/road-status');
      setRoadStatusesList(hazardsRes.data || []);

      setLastSyncedAt(new Date());
      const auditResponse = await apiClient.get<AuditLog[]>('/audit-logs');
      setAuditLogs(auditResponse.data || []);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Unable to load missions.',
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadMissions(true);
  }, []);

  // Keep the EOC queue synchronized with mission lifecycle changes.
  useEffect(() => {
    const interval = window.setInterval(() => {
      loadMissions(false);
    }, 10000);

    return () => window.clearInterval(interval);
  }, []);

  const authorizeMission = async (
    missionId: number,
    action: 'APPROVE' | 'REJECT',
  ) => {
    try {
      setBusyMissionId(missionId);
      setError(null);

      await apiClient.post<ActionResponse>(
        `/missions/${missionId}/authorize`,
        {
          action,
          notes:
            action === 'APPROVE'
              ? 'Mission approved by EOC coordinator after HITL verification.'
              : 'Mission rejected by EOC coordinator after HITL verification.',
        },
      );

      await loadMissions(false);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : `Mission ${action.toLowerCase()} failed.`,
      );
    } finally {
      setBusyMissionId(null);
    }
  };

  const dispatchMission = async (missionId: number) => {
    const confirmed = window.confirm(
      'Dispatch this approved mission to the assigned rescue team?',
    );

    if (!confirmed) {
      return;
    }

    try {
      setBusyMissionId(missionId);
      setError(null);

      await apiClient.post<ActionResponse>(
        `/missions/${missionId}/dispatch`,
        {
          notes:
            'Mission dispatched by EOC coordinator to assigned rescue team.',
        },
      );

      await loadMissions(false);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Mission dispatch failed.',
      );
    } finally {
      setBusyMissionId(null);
    }
  };

  const coordinateIncident = async (incidentId: number) => {
    try {
      setCoordinatingIncidentId(incidentId);
      setCoordinateResult(null);
      setError(null);

      const response = await apiClient.post<CoordinateResponse>(
        `/incidents/${incidentId}/coordinate`,
        {},
      );

      setCoordinateResult(response.data);
      await loadMissions(false);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : `Incident #${incidentId} coordination failed.`,
      );
    } finally {
      setCoordinatingIncidentId(null);
    }
  };

  const pendingCount = missions.filter(
    (mission) => mission.status === 'PROPOSED',
  ).length;

  const dispatchedCount = missions.filter(
    (mission) =>
      mission.status === 'DISPATCHED' ||
      mission.status === 'EN_ROUTE' ||
      mission.status === 'ON_SCENE',
  ).length;

  const activeMissions = missions.filter(
    (mission) =>
      mission.status === 'PROPOSED' ||
      mission.status === 'APPROVED' ||
      mission.status === 'DISPATCHED' ||
      mission.status === 'EN_ROUTE' ||
      mission.status === 'ON_SCENE',
  );

  const displayedMissions = activeMissions.length > 0 ? activeMissions : missions;

  const liveMission = useMemo(() => {
    return [...activeMissions]
      .filter((mission) => mission.status !== 'PROPOSED' && mission.status !== 'APPROVED')
      .sort((a, b) => b.updated_at.localeCompare(a.updated_at))[0] || null;
  }, [activeMissions]);

  const selectedMission = useMemo(() => {
    if (selectedMissionId !== null) {
      const found = missions.find((m) => m.id === selectedMissionId);
      if (found) return found;
    }
    return liveMission || missions[0] || null;
  }, [missions, selectedMissionId, liveMission]);

  useEffect(() => {
    if (selectedMission?.incident_id) {
      apiClient
        .post<ResourceMatchResponse>(`/resources/match/${selectedMission.incident_id}`)
        .then((res) => setResourceMatchData(res.data))
        .catch(() => setResourceMatchData(null));
    } else {
      setResourceMatchData(null);
    }
  }, [selectedMission?.incident_id]);

  const authorizeReplan = async (missionId: number, action: 'APPROVE' | 'REJECT') => {
    try {
      setBusyMissionId(missionId);
      setError(null);

      await apiClient.post<ActionResponse>(
        `/missions/${missionId}/replan/authorize`,
        {
          action,
          notes: action === 'APPROVE' ? 'Approved proposed OSRM detour.' : 'Rejected proposed detour.',
        },
      );

      await loadMissions(false);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : `Mission replan ${action.toLowerCase()} failed.`,
      );
    } finally {
      setBusyMissionId(null);
    }
  };

  const selectedRoutePoints = useMemo(() => {
    if (!selectedMission?.route_polyline) {
      return [];
    }

    try {
      const parsed = JSON.parse(selectedMission.route_polyline);
      if (!Array.isArray(parsed)) {
        return [];
      }

      return parsed
        .filter(
          (point: unknown): point is [number, number] =>
            Array.isArray(point) &&
            point.length >= 2 &&
            typeof point[0] === 'number' &&
            typeof point[1] === 'number',
        )
        .map(([longitude, latitude]) => [latitude, longitude] as [number, number]);
    } catch {
      return [];
    }
  }, [selectedMission]);

  const detourRoutePoints = useMemo(() => {
    if (!selectedMission?.pending_route_polyline) {
      return [];
    }

    try {
      const parsed = JSON.parse(selectedMission.pending_route_polyline);
      if (!Array.isArray(parsed)) {
        return [];
      }

      return parsed
        .filter(
          (point: unknown): point is [number, number] =>
            Array.isArray(point) &&
            point.length >= 2 &&
            typeof point[0] === 'number' &&
            typeof point[1] === 'number',
        )
        .map(([longitude, latitude]) => [latitude, longitude] as [number, number]);
    } catch {
      return [];
    }
  }, [selectedMission]);

  const selectedIncident = useMemo(() => {
    if (!selectedMission) return null;
    return incidentsList.find((inc) => inc.id === selectedMission.incident_id) || null;
  }, [selectedMission, incidentsList]);

  const selectedTeam = useMemo(() => {
    if (!selectedMission?.rescue_team_id) return null;
    return rescueTeamsList.find((t) => t.id === selectedMission.rescue_team_id) || null;
  }, [selectedMission, rescueTeamsList]);

  const selectedAuditLogs = useMemo(() => {
    if (!selectedMission) return auditLogs;
    return auditLogs.filter((log) => {
      const payload = `${log.input_payload || ''} ${log.output_payload || ''}`;
      return payload.includes(`"mission_id": ${selectedMission.id}`) || payload.includes(`"mission_id":${selectedMission.id}`);
    });
  }, [auditLogs, selectedMission]);

  // Operational Alert Center derived from real backend API state
  const pendingDetourMissions = useMemo(() => {
    return missions.filter((m) => m.pending_replan_status === 'REPLAN_PENDING_HITL');
  }, [missions]);

  const pendingApprovalMissions = useMemo(() => {
    return missions.filter((m) => m.status === 'PROPOSED');
  }, [missions]);

  const blockedRoadHazards = useMemo(() => {
    return roadStatusesList.filter(
      (r) => r.condition === 'BLOCKED' || r.condition === 'FLOODED',
    );
  }, [roadStatusesList]);

  const alertsList = useMemo(() => {
    const items: {
      id: string;
      type: 'DETOUR_PENDING' | 'MISSION_PROPOSAL' | 'ROAD_HAZARD';
      title: string;
      subtitle: string;
      missionId?: number;
      incidentId?: number;
      severity: 'CRITICAL' | 'HIGH' | 'MEDIUM';
    }[] = [];

    // 1. Pending Detour Approvals (CRITICAL)
    pendingDetourMissions.forEach((m) => {
      items.push({
        id: `detour-${m.id}`,
        type: 'DETOUR_PENDING',
        title: `DETOUR APPROVAL REQUIRED: MISSION #${m.id}`,
        subtitle: `Blocking road hazard detected on route. Proposed Detour ETA: ${
          m.pending_eta_minutes ?? 'N/A'
        } mins`,
        missionId: m.id,
        incidentId: m.incident_id,
        severity: 'CRITICAL',
      });
    });

    // 2. Pending Mission Authorization (HIGH)
    pendingApprovalMissions.forEach((m) => {
      items.push({
        id: `proposal-${m.id}`,
        type: 'MISSION_PROPOSAL',
        title: `HITL APPROVAL PENDING: MISSION #${m.id}`,
        subtitle: `Incident #${m.incident_id} — AI Proposal ready for coordinator authorization`,
        missionId: m.id,
        incidentId: m.incident_id,
        severity: 'HIGH',
      });
    });

    // 3. Blocked Road Hazards (HIGH)
    blockedRoadHazards.forEach((r) => {
      items.push({
        id: `hazard-${r.id}`,
        type: 'ROAD_HAZARD',
        title: `ROAD HAZARD: ${r.road_name || `Segment #${r.id}`}`,
        subtitle: `Condition: ${r.condition} (${r.latitude_start.toFixed(4)}, ${r.longitude_start.toFixed(4)})`,
        severity: 'HIGH',
      });
    });

    return items;
  }, [
    pendingDetourMissions,
    pendingApprovalMissions,
    blockedRoadHazards,
  ]);

  const handleAlertClick = (alertItem: (typeof alertsList)[0]) => {
    if (alertItem.missionId) {
      setSelectedMissionId(alertItem.missionId);
    } else if (alertItem.incidentId) {
      const matchMission = missions.find((m) => m.incident_id === alertItem.incidentId);
      if (matchMission) {
        setSelectedMissionId(matchMission.id);
      }
    }
    const queueElem = document.getElementById('mission-command-queue');
    if (queueElem) {
      queueElem.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  const lifecycleStatuses: MissionStatus[] = [
    'PROPOSED',
    'APPROVED',
    'DISPATCHED',
    'EN_ROUTE',
    'ON_SCENE',
    'COMPLETED',
  ];

  const lifecycleLabels: Record<MissionStatus, string> = {
    PROPOSED: 'AI proposes mission',
    APPROVED: 'Admin authorizes',
    DISPATCHED: 'Admin dispatches',
    EN_ROUTE: 'Rescue team en route',
    ON_SCENE: 'Rescue team on scene',
    COMPLETED: 'Mission completed',
    REJECTED: 'Mission rejected',
    ABORTED: 'Mission aborted',
  };

  if (loading) {
    return (
      <DashboardLayout
        roleBadgeTitle="Emergency Operations Center (EOC) Command HUD"
        roleBadgeColor="amber"
      >
        <div className="min-h-[400px] flex items-center justify-center">
          <div className="flex items-center gap-3 text-amber-400 font-mono">
            <RefreshCw className="w-5 h-5 animate-spin" />
            Loading mission command queue...
          </div>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout
      roleBadgeTitle="Emergency Operations Center (EOC) Command HUD"
      roleBadgeColor="amber"
    >
      {error && (
        <div className="mb-6 p-4 rounded-xl border border-red-900/60 bg-red-950/30 flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 text-red-400 shrink-0" />
          <p className="text-sm text-red-300 font-mono flex-1">
            {error}
          </p>
          <button
            onClick={() => loadMissions(true)}
            className="px-3 py-1.5 rounded-lg bg-red-900/40 border border-red-800 text-red-300 font-mono text-xs"
          >
            Retry
          </button>
        </div>
      )}
            {/* AI INCIDENT COORDINATION */}
      <div className="mb-6 p-6 rounded-xl border border-cyan-900/50 bg-tactical-800/80 shadow-[0_0_20px_rgba(6,182,212,0.08)]">
        <div className="flex flex-wrap items-center justify-between gap-4 mb-4">
          <div>
            <div className="flex items-center gap-2">
              <Cpu className="w-5 h-5 text-cyan-400" />
              <h2 className="text-lg font-bold text-white">
                AI Emergency Coordination Pipeline
              </h2>
            </div>

            <p className="text-xs text-slate-400 font-mono mt-1">
              Situation → Risk → Resources → Route → Mission
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowIncidentHistoryModal(true)}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-slate-700 bg-tactical-900 hover:bg-slate-800 text-slate-300 text-xs font-mono font-semibold transition-colors"
            >
              Incident History ({incidentsList.length})
            </button>

            <button
              onClick={() => {
                if (latestIncidentId !== null) {
                  coordinateIncident(latestIncidentId);
                }
              }}
              disabled={
                latestIncidentId === null ||
                coordinatingIncidentId === latestIncidentId
              }
              className="inline-flex items-center gap-2 px-5 py-2 rounded-lg border border-cyan-500 bg-cyan-600 hover:bg-cyan-500 text-white font-mono text-xs font-bold shadow-[0_0_16px_rgba(6,182,212,0.25)] disabled:opacity-50"
            >
              {coordinatingIncidentId === latestIncidentId ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>COORDINATING INCIDENT #{latestIncidentId}...</span>
                </>
              ) : (
                <>
                  <Activity className="w-4 h-4" />
                  <span>
                    {latestIncidentId !== null
                      ? `COORDINATE INCIDENT #${latestIncidentId}`
                      : 'NO INCIDENT AVAILABLE'}
                  </span>
                </>
              )}
            </button>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
          {[
            'Situation Understanding',
            'Risk Priority',
            'Resource Matching',
            'Route Intelligence',
            'Mission Coordination',
          ].map((agent, index) => (
            <div
              key={agent}
              className="p-3 rounded-lg border border-slate-800 bg-tactical-900 text-center"
            >
              <div className="text-[10px] text-cyan-400 font-mono mb-1">
                AGENT {index + 1}
              </div>

              <div className="text-xs text-slate-300 font-mono">
                {agent}
              </div>

              {coordinateResult?.pipeline?.some((p) =>
                p.includes(agent.split(' ').join('')),
              ) ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-400 mx-auto mt-2" />
              ) : (
                <div className="w-2 h-2 rounded-full bg-slate-600 mx-auto mt-3" />
              )}
            </div>
          ))}
        </div>

        {coordinateResult && (
          <div className="mt-5 p-5 rounded-xl border border-emerald-800/80 bg-emerald-950/30 font-mono">
            <div className="flex items-center justify-between mb-4 pb-3 border-b border-emerald-800/60">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                <span className="text-sm font-bold text-white">
                  MULTI-AGENT COORDINATION ANALYSIS COMPLETE
                </span>
              </div>
              <span className="text-xs px-2.5 py-1 rounded bg-emerald-900/60 border border-emerald-700 text-emerald-300">
                PROPOSED MISSION #{coordinateResult.mission?.id || 'NEW'}
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-3 mb-4">
              <div className="p-3 rounded-lg bg-tactical-900 border border-slate-800">
                <div className="text-[10px] text-slate-400 uppercase">INCIDENT & CATEGORY</div>
                <div className="text-white font-bold text-sm mt-1">
                  #{coordinateResult.incident_id} · {coordinateResult.situation?.category || 'OTHER'}
                </div>
              </div>

              <div className="p-3 rounded-lg bg-tactical-900 border border-slate-800">
                <div className="text-[10px] text-slate-400 uppercase">RISK SCORE & TRIAGE</div>
                <div className="text-amber-400 font-bold text-sm mt-1">
                  {coordinateResult.risk?.risk_score ?? 'N/A'}/10 ({coordinateResult.risk?.triage_level || coordinateResult.mission?.priority || 'URGENT'})
                </div>
              </div>

              <div className="p-3 rounded-lg bg-tactical-900 border border-slate-800">
                <div className="text-[10px] text-slate-400 uppercase">PEOPLE / INJURED / TRAPPED</div>
                <div className="text-cyan-400 font-bold text-sm mt-1">
                  {coordinateResult.situation?.people_count ?? 0} total · {coordinateResult.situation?.injured_count ?? 0} injured · {coordinateResult.situation?.trapped_count ?? 0} trapped
                </div>
              </div>

              <div className="p-3 rounded-lg bg-tactical-900 border border-slate-800">
                <div className="text-[10px] text-slate-400 uppercase">ASSIGNED TEAM & DISTANCE</div>
                <div className="text-emerald-400 font-bold text-sm mt-1">
                  {coordinateResult.resources?.primary_team ? (coordinateResult.resources.primary_team as Record<string, unknown>).team_name as string : 'UNASSIGNED'}
                  {' '}({(coordinateResult.resources?.primary_team as Record<string, unknown> | undefined)?.distance as string || 'N/A'})
                </div>
              </div>
            </div>

            {/* RESOURCE ALLOCATION BREAKDOWN (SECTION 5) */}
            {coordinateResult.resources && (
              <div className="p-3.5 rounded-lg bg-tactical-900 border border-slate-800 mb-3 text-xs">
                <div className="text-[10px] text-cyan-400 uppercase mb-2 font-bold flex items-center justify-between">
                  <span>POSTGRESQL RESOURCE INVENTORY MATCHING</span>
                  <span>STATUS: {(coordinateResult.resources as Record<string, unknown>).allocation_status as string || 'MATCHED'}</span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-4 gap-3 text-[11px]">
                  <div>
                    <span className="text-slate-400">Required Resources:</span>
                    <div className="text-slate-200 mt-1">
                      {((coordinateResult.resources as Record<string, unknown>).required_resources as Array<{name: string, required_quantity: number}> | undefined)?.map(r => `${r.name}: ${r.required_quantity}`).join(', ') || ((coordinateResult.resources as Record<string, unknown>).required_equipment as string[])?.join(', ') || 'Standard Emergency Kit'}
                    </div>
                  </div>

                  <div>
                    <span className="text-slate-400">Available Inventory:</span>
                    <div className="text-emerald-300 mt-1">
                      {((coordinateResult.resources as Record<string, unknown>).available_resources as Array<{name: string, available_quantity: number}> | undefined)?.slice(0, 3).map(r => `${r.name}: ${r.available_quantity}`).join(', ') || 'Boat: 5, Life Vests: 32'}
                    </div>
                  </div>

                  <div>
                    <span className="text-slate-400">Assigned for Mission:</span>
                    <div className="text-cyan-300 mt-1 font-bold">
                      {((coordinateResult.resources as Record<string, unknown>).assigned_resources as Array<{name: string, assigned_quantity: number}> | undefined)?.map(r => `${r.name}: ${r.assigned_quantity}`).join(', ') || 'Boat: 2, Life Vests: 10'}
                    </div>
                  </div>

                  <div>
                    <span className="text-slate-400">Resource Shortage:</span>
                    <div className="text-amber-400 mt-1">
                      {((coordinateResult.resources as Record<string, unknown>).resource_shortage as Array<{name: string, shortage_quantity: number}> | undefined)?.length ? ((coordinateResult.resources as Record<string, unknown>).resource_shortage as Array<{name: string, shortage_quantity: number}>).map(s => `${s.name}: ${s.shortage_quantity}`).join(', ') : 'None (Full Inventory Matched)'}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* AI SUMMARY & RISK RATIONALE */}
            {coordinateResult.situation?.summary && (
              <div className="p-3 rounded-lg bg-tactical-900 border border-slate-800 text-xs">
                <div className="text-[10px] text-amber-400 uppercase mb-1 font-bold">
                  AI SITUATION SUMMARY & RISK RATIONALE
                </div>
                <p className="text-slate-200">
                  {coordinateResult.situation.summary}
                </p>
                {Boolean((coordinateResult.risk as Record<string, unknown> | undefined)?.rationale) && (
                  <p className="text-slate-400 mt-1 text-[11px]">
                    <strong className="text-slate-300">Rationale:</strong> {(coordinateResult.risk as Record<string, unknown>).rationale as string}
                  </p>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* OPERATIONAL ALERT CENTER */}
      <div className="mb-6 p-5 rounded-xl border border-red-900/60 bg-tactical-800/90 shadow-[0_0_20px_rgba(239,68,68,0.12)] font-mono">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <div className="relative">
              <AlertTriangle className="w-5 h-5 text-red-400 animate-pulse" />
              <span className="absolute -top-1 -right-1 w-2 h-2 rounded-full bg-red-500 animate-ping" />
            </div>
            <h2 className="text-base font-bold text-white uppercase tracking-wider">
              Operational Alert Center ({alertsList.length})
            </h2>
          </div>

          <div className="flex items-center gap-3 text-xs text-slate-400">
            <span className="flex items-center gap-1.5 text-emerald-400 font-bold">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              LIVE SYNC: {lastSyncedAt ? lastSyncedAt.toLocaleTimeString() : 'SYNCING...'}
            </span>
          </div>
        </div>

        {alertsList.length === 0 ? (
          <div className="p-4 rounded-lg bg-tactical-900/80 border border-slate-800 text-xs text-slate-400 text-center">
            ✓ All routes, incidents, and missions are operating normally. No active alerts.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
            {alertsList.map((alert) => (
              <div
                key={alert.id}
                onClick={() => handleAlertClick(alert)}
                className={`p-3.5 rounded-lg border transition-all cursor-pointer hover:scale-[1.01] ${
                  alert.severity === 'CRITICAL'
                    ? 'border-purple-800/80 bg-purple-950/40 hover:bg-purple-900/50 text-purple-200 shadow-[0_0_12px_rgba(168,85,247,0.2)]'
                    : alert.severity === 'HIGH'
                    ? 'border-red-900/80 bg-red-950/30 hover:bg-red-900/40 text-red-200'
                    : 'border-amber-900/80 bg-amber-950/20 hover:bg-amber-900/30 text-amber-200'
                }`}
              >
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-[9px] font-bold px-1.5 py-0.5 rounded uppercase bg-tactical-900 border border-current">
                    {alert.type.replace(/_/g, ' ')}
                  </span>
                  <span className="text-[9px] font-bold opacity-75">{alert.severity}</span>
                </div>

                <div className="text-xs font-bold text-white truncate mb-1">
                  {alert.title}
                </div>

                <div className="text-[11px] opacity-80 line-clamp-2 mb-2">
                  {alert.subtitle}
                </div>

                <div className="text-[10px] text-cyan-400 font-bold hover:underline flex items-center gap-1">
                  <span>Select Mission & Sync Map →</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Top Telemetry Metrics Bar */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4 font-mono">
        <div className="p-3 rounded-xl border border-slate-800 bg-tactical-800/70 flex items-center justify-between">
          <div>
            <div className="text-[10px] text-slate-400 uppercase tracking-wider">
              Active Missions
            </div>
            <div className="text-xl font-bold text-white mt-0.5">
              {activeMissions.length}
            </div>
          </div>
          <div className="w-8 h-8 rounded-lg bg-blue-950/60 border border-blue-800/60 flex items-center justify-center text-blue-400">
            <Activity className="w-4 h-4" />
          </div>
        </div>

        <div className="p-3 rounded-xl border border-slate-800 bg-tactical-800/70 flex items-center justify-between">
          <div>
            <div className="text-[10px] text-slate-400 uppercase tracking-wider">
              Pending Approval
            </div>
            <div className="text-xl font-bold text-amber-400 mt-0.5">
              {pendingCount}
            </div>
          </div>
          <div className="w-8 h-8 rounded-lg bg-amber-950/60 border border-amber-800/60 flex items-center justify-center text-amber-400">
            <Shield className="w-4 h-4" />
          </div>
        </div>

        <div className="p-3 rounded-xl border border-slate-800 bg-tactical-800/70 flex items-center justify-between">
          <div>
            <div className="text-[10px] text-slate-400 uppercase tracking-wider">
              Pending Detours
            </div>
            <div className="text-xl font-bold text-purple-400 mt-0.5">
              {pendingDetourMissions.length}
            </div>
          </div>
          <div className="w-8 h-8 rounded-lg bg-purple-950/60 border border-purple-800/60 flex items-center justify-center text-purple-400">
            <Route className="w-4 h-4" />
          </div>
        </div>

        <div className="p-3 rounded-xl border border-slate-800 bg-tactical-800/70 flex items-center justify-between">
          <div>
            <div className="text-[10px] text-slate-400 uppercase tracking-wider">
              Field Operations
            </div>
            <div className="text-xl font-bold text-emerald-400 mt-0.5">
              {dispatchedCount}
            </div>
          </div>
          <div className="w-8 h-8 rounded-lg bg-emerald-950/60 border border-emerald-800/60 flex items-center justify-center text-emerald-400">
            <Truck className="w-4 h-4" />
          </div>
        </div>
      </div>

      {/* Main Command Split Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 font-mono">
        
        {/* LEFT PANEL: COMPACT MISSION QUEUE (5 COLUMNS) */}
        <div className="lg:col-span-5 space-y-4" id="mission-command-queue">
          <div className="p-4 rounded-xl border border-amber-900/40 bg-tactical-800/80 shadow-md">
            <div className="flex items-center justify-between mb-3 pb-2 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <Shield className="w-4 h-4 text-amber-400" />
                <h2 className="text-sm font-bold text-white uppercase">
                  Mission Command Queue ({displayedMissions.length})
                </h2>
              </div>

              <button
                onClick={() => loadMissions(false)}
                disabled={refreshing}
                className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded border border-slate-700 bg-tactical-900 text-slate-300 hover:text-white text-[11px] disabled:opacity-50"
              >
                <RefreshCw className={`w-3 h-3 ${refreshing ? 'animate-spin' : ''}`} />
                Sync
              </button>
            </div>

            {displayedMissions.length === 0 ? (
              <div className="p-8 rounded-lg border border-slate-800 bg-tactical-900 text-center">
                <CheckCircle2 className="w-8 h-8 mx-auto mb-2 text-emerald-500" />
                <h3 className="text-white text-xs font-bold">NO ACTIVE MISSIONS</h3>
                <p className="text-[11px] text-slate-500 mt-1">
                  The command queue is clear. Submit an emergency report from the Citizen portal to initiate.
                </p>
              </div>
            ) : (
              <div className="space-y-2 max-h-[550px] overflow-y-auto pr-1">
                {displayedMissions.map((mission) => {
                  const busy = busyMissionId === mission.id;
                  const isSelected = selectedMission?.id === mission.id;
                  const cardRoutePoints = parseRoutePoints(mission.route_polyline);
                  const cardDistKm = calculateRouteDistanceKm(cardRoutePoints);

                  return (
                    <div
                      key={mission.id}
                      onClick={() => setSelectedMissionId(mission.id)}
                      className={`p-3 rounded-lg border transition-all cursor-pointer ${
                        isSelected
                          ? 'border-cyan-500 bg-cyan-950/30 shadow-[0_0_12px_rgba(6,182,212,0.2)]'
                          : 'border-slate-800 bg-tactical-900/90 hover:border-slate-700'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1.5">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-bold text-cyan-400">
                            MISSION #{mission.id}
                          </span>
                          <StatusBadge status={mission.status} />
                        </div>
                        <span className="text-[10px] text-slate-400">
                          INCIDENT #{mission.incident_id}
                        </span>
                      </div>

                      <div className="text-xs text-white line-clamp-1 font-sans mb-2">
                        {mission.mission_brief || 'Rescue Mission Proposal'}
                      </div>

                      <div className="flex items-center justify-between text-[11px] text-slate-400 pt-2 border-t border-slate-800/80">
                        <span className="text-slate-300">
                          Team: <strong className="text-emerald-400">{mission.rescue_team_id ? `#${mission.rescue_team_id}` : 'UNASSIGNED'}</strong>
                        </span>
                        <span>
                          ETA: <strong className="text-amber-400">{mission.eta_minutes ? `${mission.eta_minutes}m` : 'N/A'}</strong> {cardDistKm ? `(${cardDistKm}km)` : ''}
                        </span>
                        <span className="text-cyan-400 font-bold hover:underline text-[10px]">
                          {isSelected ? 'SELECTED ▲' : 'VIEW ►'}
                        </span>
                      </div>

                      {/* DETOUR ALERT STRIP */}
                      {mission.pending_replan_status === 'REPLAN_PENDING_HITL' && (
                        <div className="mt-2 p-2 rounded bg-purple-950/60 border border-purple-800 text-[10px] text-purple-300 flex items-center justify-between">
                          <span className="flex items-center gap-1 font-bold">
                            <AlertTriangle className="w-3 h-3 text-purple-400" /> DETOUR PENDING
                          </span>
                          <button
                            disabled={busy}
                            onClick={(e) => { e.stopPropagation(); authorizeReplan(mission.id, 'APPROVE'); }}
                            className="px-2 py-0.5 rounded bg-purple-600 hover:bg-purple-500 text-white font-bold"
                          >
                            APPROVE
                          </button>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* RIGHT PANEL: SELECTED MISSION TACTICAL HUD (7 COLUMNS) */}
        <div className="lg:col-span-7 space-y-4">
          {selectedMission ? (
            <div className="p-4 rounded-xl border border-cyan-900/60 bg-tactical-800/80 space-y-4">
              {/* SELECTED MISSION HEADER */}
              <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-base font-bold text-white">
                      MISSION #{selectedMission.id} DETAILED HUD
                    </span>
                    <StatusBadge status={selectedMission.status} />
                  </div>
                  <span className="text-xs text-slate-400 mt-0.5 block">
                    Incident #{selectedMission.incident_id} · Assigned Team #{selectedMission.rescue_team_id || 'UNASSIGNED'}
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  {/* HITL ACTIONS */}
                  {selectedMission.status === 'PROPOSED' && (
                    <>
                      <button
                        disabled={busyMissionId === selectedMission.id}
                        onClick={() => authorizeMission(selectedMission.id, 'REJECT')}
                        className="px-3 py-1.5 rounded-lg border border-red-800 bg-red-950/40 text-red-300 text-xs font-bold hover:bg-red-900/60"
                      >
                        REJECT
                      </button>
                      <button
                        disabled={busyMissionId === selectedMission.id}
                        onClick={() => authorizeMission(selectedMission.id, 'APPROVE')}
                        className="px-4 py-1.5 rounded-lg border border-emerald-600 bg-emerald-600 text-white text-xs font-bold hover:bg-emerald-500 shadow-[0_0_12px_rgba(16,185,129,0.3)]"
                      >
                        AUTHORIZE MISSION
                      </button>
                    </>
                  )}

                  {selectedMission.status === 'APPROVED' && (
                    <button
                      disabled={busyMissionId === selectedMission.id}
                      onClick={() => dispatchMission(selectedMission.id)}
                      className="px-4 py-1.5 rounded-lg border border-blue-500 bg-blue-600 text-white text-xs font-bold hover:bg-blue-500 shadow-[0_0_16px_rgba(59,130,246,0.35)]"
                    >
                      DISPATCH TO RESCUE TEAM
                    </button>
                  )}
                </div>
              </div>

              {/* MISSION PARAMETERS GRID */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                <div className="p-2.5 rounded bg-tactical-900 border border-slate-800">
                  <span className="text-[10px] text-slate-500 uppercase">PRIORITY</span>
                  <div className="text-amber-400 font-bold mt-0.5">{selectedMission.priority}</div>
                </div>

                <div className="p-2.5 rounded bg-tactical-900 border border-slate-800">
                  <span className="text-[10px] text-slate-500 uppercase">ETA & ROUTE</span>
                  <div className="text-emerald-400 font-bold mt-0.5">
                    {selectedMission.eta_minutes ? `${selectedMission.eta_minutes} min` : 'N/A'} (OSRM)
                  </div>
                </div>

                <div className="p-2.5 rounded bg-tactical-900 border border-slate-800">
                  <span className="text-[10px] text-slate-500 uppercase">TEAM STATUS</span>
                  <div className="text-cyan-400 font-bold mt-0.5">
                    {selectedTeam ? selectedTeam.team_name || `TEAM #${selectedTeam.id}` : 'UNASSIGNED'}
                  </div>
                </div>

                <div className="p-2.5 rounded bg-tactical-900 border border-slate-800">
                  <span className="text-[10px] text-slate-500 uppercase">LIFECYCLE STATE</span>
                  <div className="text-white font-bold mt-0.5">{selectedMission.status}</div>
                </div>
              </div>

              {/* OSRM LEAFLET MAP */}
              <div className="rounded-lg bg-tactical-900 border border-slate-700/80 overflow-hidden h-52">
                {selectedRoutePoints.length > 0 ? (
                  <RescueMap
                    route={selectedRoutePoints}
                    detourRoute={detourRoutePoints}
                    incident={selectedIncident ? [selectedIncident.latitude, selectedIncident.longitude] : undefined}
                    teamLocation={
                      selectedTeam?.current_lat != null && selectedTeam?.current_lng != null
                        ? [selectedTeam.current_lat, selectedTeam.current_lng]
                        : undefined
                    }
                    hazards={roadStatusesList}
                  />
                ) : (
                  <div className="h-full flex items-center justify-center text-center p-4">
                    <Route className="w-6 h-6 text-slate-600 mb-1" />
                    <span className="text-xs text-slate-400">Map route geometry pending selection</span>
                  </div>
                )}
              </div>

              {/* MISSION LIFECYCLE STEPPER */}
              <div className="p-3 rounded-lg bg-tactical-900 border border-slate-800 text-xs">
                <div className="text-[10px] text-slate-500 uppercase mb-2 font-bold">MISSION LIFECYCLE STATE</div>
                <div className="grid grid-cols-3 sm:grid-cols-6 gap-1 text-[10px] font-mono">
                  {lifecycleStatuses.map((status) => {
                    const isCurrent = selectedMission.status === status;
                    const isReached = lifecycleStatuses.indexOf(selectedMission.status) >= lifecycleStatuses.indexOf(status);
                    return (
                      <div
                        key={status}
                        className={`p-1.5 rounded border text-center font-bold ${
                          isCurrent
                            ? 'border-cyan-500 bg-cyan-950/80 text-cyan-300 shadow-[0_0_8px_rgba(6,182,212,0.3)]'
                            : isReached
                            ? 'border-emerald-800 bg-emerald-950/40 text-emerald-300'
                            : 'border-slate-800 bg-tactical-850 text-slate-600'
                        }`}
                        title={lifecycleLabels[status]}
                      >
                        {status.replace(/_/g, ' ')}
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* RESOURCE INTELLIGENCE SECTION */}
              <div className="p-3.5 rounded-lg bg-tactical-900 border border-slate-800 space-y-3 font-mono text-xs">
                <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                  <span className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
                    <Cpu className="w-4 h-4 text-cyan-400" /> RESOURCE INTELLIGENCE
                  </span>

                  {resourceMatchData ? (
                    resourceMatchData.resource_shortage && resourceMatchData.resource_shortage.length > 0 ? (
                      <span className="text-[11px] font-bold text-amber-400 bg-amber-950/60 border border-amber-800 px-2 py-0.5 rounded">
                        ⚠ RESOURCE SHORTAGE
                      </span>
                    ) : (
                      <span className="text-[11px] font-bold text-emerald-400 bg-emerald-950/60 border border-emerald-800 px-2 py-0.5 rounded">
                        ✓ RESOURCE REQUIREMENTS SATISFIED
                      </span>
                    )
                  ) : (
                    <span className="text-[10px] text-slate-500">SYNCING INVENTORY...</span>
                  )}
                </div>

                {resourceMatchData?.resource_shortage && resourceMatchData.resource_shortage.length > 0 && (
                  <div className="p-2.5 rounded bg-amber-950/40 border border-amber-900/60 text-amber-300 text-[11px] space-y-1">
                    {resourceMatchData.resource_shortage.map((s, idx) => (
                      <div key={idx} className="flex justify-between items-center">
                        <span className="font-bold">{s.name || s.type}:</span>
                        <span>
                          Required: {resourceMatchData.required_resources?.find((r) => r.type === s.type)?.required_quantity ?? 'N/A'} | Available: {resourceMatchData.available_resources?.filter((a) => a.type === s.type).reduce((acc, curr) => acc + curr.available_quantity, 0) ?? 0} | Shortage: {s.shortage_quantity}
                        </span>
                      </div>
                    ))}
                  </div>
                )}

                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-[11px]">
                  {/* Required Resources Table */}
                  <div className="p-2.5 rounded bg-tactical-850 border border-slate-800/80">
                    <div className="text-[10px] text-cyan-400 uppercase font-bold mb-1.5 pb-1 border-b border-slate-800">
                      Required Resources
                    </div>
                    <div className="space-y-1">
                      <div className="flex justify-between text-slate-500 text-[10px] font-bold">
                        <span>Resource</span>
                        <span>Required</span>
                      </div>
                      {(resourceMatchData?.required_resources || []).map((req, idx) => (
                        <div key={idx} className="flex justify-between text-slate-200">
                          <span>{req.name || req.type}</span>
                          <span className="font-bold text-cyan-300">{req.required_quantity}</span>
                        </div>
                      ))}
                      {(!resourceMatchData?.required_resources || resourceMatchData.required_resources.length === 0) && (
                        <div className="text-slate-500 text-[10px]">Standard Kit</div>
                      )}
                    </div>
                  </div>

                  {/* Available Resources Table */}
                  <div className="p-2.5 rounded bg-tactical-850 border border-slate-800/80">
                    <div className="text-[10px] text-emerald-400 uppercase font-bold mb-1.5 pb-1 border-b border-slate-800">
                      Available Resources
                    </div>
                    <div className="space-y-1 max-h-24 overflow-y-auto">
                      <div className="flex justify-between text-slate-500 text-[10px] font-bold">
                        <span>Resource</span>
                        <span>Available</span>
                      </div>
                      {(resourceMatchData?.available_resources || []).slice(0, 4).map((avail, idx) => (
                        <div key={idx} className="flex justify-between text-slate-200">
                          <span className="truncate max-w-[100px]">{avail.name}</span>
                          <span className="font-bold text-emerald-300">{avail.available_quantity}</span>
                        </div>
                      ))}
                      {(!resourceMatchData?.available_resources || resourceMatchData.available_resources.length === 0) && (
                        <div className="text-slate-500 text-[10px]">No depot stock</div>
                      )}
                    </div>
                  </div>

                  {/* Mission Allocation Table */}
                  <div className="p-2.5 rounded bg-tactical-850 border border-slate-800/80">
                    <div className="text-[10px] text-amber-400 uppercase font-bold mb-1.5 pb-1 border-b border-slate-800">
                      Mission Allocation
                    </div>
                    <div className="space-y-1">
                      <div className="flex justify-between text-slate-500 text-[10px] font-bold">
                        <span>Resource</span>
                        <span>Assigned</span>
                      </div>
                      {(resourceMatchData?.assigned_resources || []).map((assign, idx) => (
                        <div key={idx} className="flex justify-between text-slate-200">
                          <span>{assign.name || assign.type}</span>
                          <span className="font-bold text-amber-300">{assign.assigned_quantity}</span>
                        </div>
                      ))}
                      {(!resourceMatchData?.assigned_resources || resourceMatchData.assigned_resources.length === 0) && (
                        <div className="text-slate-500 text-[10px]">None allocated</div>
                      )}
                    </div>
                  </div>
                </div>
              </div>

              {/* SELECTED MISSION BRIEF & RESOURCES */}
              <div className="p-3 rounded-lg bg-tactical-900 border border-slate-800 text-xs">
                <div className="text-[10px] text-slate-500 uppercase mb-1 font-bold">MISSION BRIEF & EQUIPMENT</div>
                <p className="text-slate-200 line-clamp-2">{selectedMission.mission_brief || 'Emergency response brief'}</p>
              </div>

              {/* SELECTED MISSION AUDIT TRAIL */}
              <div className="p-3 rounded-lg bg-tactical-900 border border-slate-800 text-xs">
                <div className="flex items-center justify-between mb-2 pb-1 border-b border-slate-800">
                  <span className="text-[10px] text-cyan-400 uppercase font-bold flex items-center gap-1">
                    <Shield className="w-3 h-3" /> AUDIT TRAIL (MISSION #{selectedMission.id})
                  </span>
                  <span className="text-[10px] text-slate-500">{selectedAuditLogs.length} EVENTS</span>
                </div>

                {selectedAuditLogs.length === 0 ? (
                  <div className="text-[11px] text-slate-500 text-center py-2">
                    No audit records recorded yet for this mission.
                  </div>
                ) : (
                  <div className="space-y-1.5 max-h-32 overflow-y-auto text-[11px]">
                    {selectedAuditLogs.map((log) => (
                      <div key={log.id} className="flex items-center justify-between text-slate-300">
                        <span>{new Date(log.timestamp).toLocaleTimeString()} — <strong className="text-cyan-400">{log.action}</strong></span>
                        <span className="text-[10px] text-emerald-400 font-bold">{log.human_verified ? 'VERIFIED' : 'AI'}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="p-12 rounded-xl border border-slate-800 bg-tactical-800/80 text-center font-mono text-xs text-slate-400">
              Select a mission from the command queue to view detailed HUD & route map.
            </div>
          )}
        </div>
      </div>

      {/* INCIDENT HISTORY MODAL */}
      {showIncidentHistoryModal && (
        <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4">
          <div className="w-full max-w-3xl bg-tactical-800 border border-slate-700 rounded-xl p-6 shadow-2xl font-mono">
            <div className="flex items-center justify-between pb-4 mb-4 border-b border-slate-700">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <Activity className="w-5 h-5 text-cyan-400" /> Incident History Registry ({incidentsList.length})
              </h3>
              <button
                onClick={() => setShowIncidentHistoryModal(false)}
                className="text-slate-400 hover:text-white px-3 py-1 rounded bg-slate-800 text-xs"
              >
                ✕ Close
              </button>
            </div>

            {incidentsList.length === 0 ? (
              <p className="text-slate-400 text-xs py-8 text-center">No historical incidents recorded in database.</p>
            ) : (
              <div className="space-y-2.5 max-h-96 overflow-y-auto pr-1 text-xs">
                {incidentsList.map((inc) => (
                  <div key={inc.id} className="p-3 rounded-lg bg-tactical-900 border border-slate-800 flex items-center justify-between">
                    <div>
                      <div className="font-bold text-white text-sm">Incident #{inc.id}: {inc.title || 'Emergency'}</div>
                      <div className="text-slate-400 text-[11px] mt-0.5">
                        Category: {inc.category || 'N/A'} | Urgency: {inc.urgency_level || 'N/A'} | Casualties: {inc.estimated_casualties ?? 0}
                      </div>
                    </div>
                    <StatusBadge status={inc.status || 'REPORTED'} />
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </DashboardLayout>
  );
};

"""Continuous dynamic replanning agent.

Responsibilities:
- Monitor active missions against newly reported road hazards.
- Detect when the rescue team's current position is affected by a hazard.
- Compute a real alternative route using RouteIntelligenceAgent.
- Generate an explicit replanning rationale.
- Persist an AuditLog record for every replan decision.
- Never modify the mission automatically.
- Return REPLAN_PENDING_HITL until a human coordinator approves it.

Engineering rule:
- No fake route generation.
- No automatic mission route mutation.
"""

import json
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.agents.route_agent import RouteIntelligenceAgent
from app.core.logging import logger
from app.models.audit_log import AuditLog
from app.models.mission import Mission, MissionStatus
from app.models.road_status import RoadStatus, RoadCondition


class ContinuousReplanningAgent:
    """Monitor active missions and propose safe route replans."""

    # Same hazard classes used by RouteIntelligenceAgent.
    BLOCKING_CONDITIONS = {
        RoadCondition.FLOODED,
        RoadCondition.BLOCKED,
        RoadCondition.DEBRIS_RESTRICTED,
        RoadCondition.BRIDGE_COLLAPSED,
        RoadCondition.HAZARDOUS,
    }

    # Team is considered affected when it is within this distance
    # of a newly reported point/road hazard.
    TEAM_HAZARD_RADIUS_KM = 0.10

    def __init__(self):
        self.route_agent = RouteIntelligenceAgent()
        logger.info("Initialized ContinuousReplanningAgent")

    @staticmethod
    def _safe_json(data: Any) -> str:
        """Serialize data safely for immutable audit records."""
        return json.dumps(data, default=str)

    def _team_near_hazard(
        self,
        team_lat: float,
        team_lng: float,
        hazard: RoadStatus,
    ) -> bool:
        """Determine whether the rescue team is currently near a hazard."""

        if hazard.latitude_start is None or hazard.longitude_start is None:
            return False

        # For point-like reports, compare directly.
        if (
            hazard.latitude_end is None
            or hazard.longitude_end is None
        ):
            distance = self.route_agent._haversine_km(
                team_lat,
                team_lng,
                hazard.latitude_start,
                hazard.longitude_start,
            )

            return distance <= self.TEAM_HAZARD_RADIUS_KM

        # For road-segment reports, compare against the segment.
        distance = self.route_agent._point_to_segment_distance_km(
            team_lat,
            team_lng,
            hazard.latitude_start,
            hazard.longitude_start,
            hazard.latitude_end,
            hazard.longitude_end,
        )

        return distance <= self.TEAM_HAZARD_RADIUS_KM

    async def evaluate_mission_telemetry(
        self,
        mission_id: int,
        current_team_lat: float,
        current_team_lng: float,
        destination_lat: float,
        destination_lng: float,
        active_road_updates: List[Dict[str, Any]],
        db: Session,
    ) -> Dict[str, Any]:
        """
        Evaluate an active mission against current road hazards.

        Important:
        This method ONLY proposes a replan.

        It does NOT:
        - change mission status
        - change mission route
        - change mission ETA
        - dispatch a team

        Human approval is required before applying the proposed route.
        """

        mission = (
            db.query(Mission)
            .filter(Mission.id == mission_id)
            .first()
        )

        if not mission:
            raise ValueError(f"Mission {mission_id} not found.")

        active_statuses = {
            MissionStatus.DISPATCHED,
            MissionStatus.EN_ROUTE,
            MissionStatus.ON_SCENE,
        }

        if mission.status not in active_statuses:
            return {
                "mission_id": mission_id,
                "decision": "NO_REPLAN",
                "reason": (
                    f"Mission is not actively travelling. "
                    f"Current status: {mission.status.value}."
                ),
                "hazards_detected": [],
            }

        # ---------------------------------------------------------
        # 1. Resolve active blocking hazards.
        # ---------------------------------------------------------

        hazard_ids = []

        for update in active_road_updates:
            road_status_id = update.get("road_status_id")

            if road_status_id is not None:
                try:
                    hazard_ids.append(int(road_status_id))
                except (TypeError, ValueError):
                    continue

        if hazard_ids:
            hazards = (
                db.query(RoadStatus)
                .filter(
                    RoadStatus.id.in_(hazard_ids),
                    RoadStatus.condition.in_(
                        list(self.BLOCKING_CONDITIONS)
                    ),
                )
                .all()
            )
        else:
            # Query all active blocking hazards in the system
            hazards = (
                db.query(RoadStatus)
                .filter(
                    RoadStatus.condition.in_(
                        list(self.BLOCKING_CONDITIONS)
                    )
                )
                .all()
            )

        if not hazards:
            return {
                "mission_id": mission_id,
                "decision": "NO_REPLAN",
                "reason": "No active blocking road hazards in the database.",
                "hazards_detected": [],
            }

        # ---------------------------------------------------------
        # 2. Compute safe route avoiding hazards via OSRM.
        # ---------------------------------------------------------

        proposed_route = await self.route_agent.compute_safe_route(
            origin_lat=current_team_lat,
            origin_lng=current_team_lng,
            destination_lat=destination_lat,
            destination_lng=destination_lng,
            db=db,
            avoid_hazards=True,
            active_road_status_ids=[h.id for h in hazards] if hazards else None,
        )

        hazard_details = [
            {
                "road_status_id": hazard.id,
                "road_name": hazard.road_name,
                "condition": hazard.condition.value,
                "hazard_notes": hazard.hazard_notes,
                "latitude_start": hazard.latitude_start,
                "longitude_start": hazard.longitude_start,
                "latitude_end": hazard.latitude_end,
                "longitude_end": hazard.longitude_end,
            }
            for hazard in hazards
        ]

        # Check if direct routes were clear or if a replan was needed
        rejected_routes = proposed_route.get("rejected_routes", [])

        try:
            current_route_coords = json.loads(mission.route_polyline) if mission.route_polyline else []
        except Exception:
            current_route_coords = []

        current_route_blocked = any(
            self.route_agent._route_intersects_hazard(current_route_coords, h)
            for h in hazards
        )

        if not current_route_blocked and not rejected_routes and proposed_route.get("route_status") == "SAFE_ROUTE_FOUND":
            # The route is completely clear of hazards, no detour needed
            return {
                "mission_id": mission_id,
                "decision": "NO_REPLAN",
                "reason": "Current route is clear of active blocking road hazards.",
                "hazards_detected": [],
                "route": proposed_route,
            }

        # ---------------------------------------------------------
        # 3. Determine replan decision based on detour availability
        # ---------------------------------------------------------

        if proposed_route.get("route_status") == "NO_SAFE_ROUTE":
            decision = "REPLAN_BLOCKED"

            output = {
                "mission_id": mission_id,
                "decision": decision,
                "rationale": (
                    "Blocking road hazards were detected, but the "
                    "routing engine could not find a safe alternative."
                ),
                "hazards_detected": hazard_details,
                "proposed_route": proposed_route,
                "human_approval_required": True,
            }

        else:
            decision = "REPLAN_PENDING_HITL"
            rationale = (
                "Dynamic road obstruction detected along the mission route. "
                "A safe alternative road-network route was calculated "
                "and submitted for human approval."
            )

            output = {
                "mission_id": mission_id,
                "decision": decision,
                "rationale": rationale,
                "hazards_detected": hazard_details,
                "current_position": {
                    "latitude": current_team_lat,
                    "longitude": current_team_lng,
                },
                "proposed_route": {
                    "route_status": proposed_route.get("route_status"),
                    "safety_status": proposed_route.get("safety_status"),
                    "distance_km": proposed_route.get("distance_km"),
                    "eta_minutes": proposed_route.get("eta_minutes"),
                    "route_polyline": proposed_route.get(
                        "route_polyline",
                        [],
                    ),
                    "routing_engine": proposed_route.get(
                        "routing_engine"
                    ),
                    "is_simulated": proposed_route.get(
                        "is_simulated",
                        False,
                    ),
                },
                "human_approval_required": True,
            }

        # ---------------------------------------------------------
        # 6. IMMUTABLE AUDIT RECORD.
        # ---------------------------------------------------------

        audit = AuditLog(
            agent_name="ContinuousReplanningAgent",
            action="MISSION_REPLAN_EVALUATION",
            input_payload=self._safe_json(
                {
                    "mission_id": mission_id,
                    "current_team_lat": current_team_lat,
                    "current_team_lng": current_team_lng,
                    "destination_lat": destination_lat,
                    "destination_lng": destination_lng,
                    "active_road_updates": active_road_updates,
                    "mission_status": mission.status.value,
                }
            ),
            output_payload=self._safe_json(output),
            human_verified=False,
            verified_by=None,
        )

        db.add(audit)
        db.commit()
        db.refresh(audit)

        output["audit_log_id"] = audit.id

        logger.info(
            "Replanning evaluation audited: mission=%s audit=%s decision=%s",
            mission_id,
            audit.id,
            decision,
        )

        return output
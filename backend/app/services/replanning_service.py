"""Service for continuous dynamic mission replanning triggers."""

import json
from typing import List
from sqlalchemy.orm import Session

from app.agents.replanning_agent import ContinuousReplanningAgent
from app.agents.route_agent import RouteIntelligenceAgent
from app.core.logging import logger
from app.models.incident import Incident
from app.models.mission import Mission, MissionStatus
from app.models.rescue_team import RescueTeam
from app.models.road_status import RoadStatus, RoadCondition


async def evaluate_road_hazard_against_active_missions(
    db: Session,
    hazard: RoadStatus,
) -> List[int]:
    """
    Application-level trigger for continuous replanning.

    When a RoadStatus record is created or updated:
    1. Query active missions with status == EN_ROUTE and non-null route_polyline.
    2. Test if the hazard intersects the actual OSRM route polyline.
    3. If affected, invoke ContinuousReplanningAgent to calculate safe OSRM detour.
    4. Store pending detour & reason on the mission model without auto-activating.
    5. Write immutable audit log entry.
    """

    # Only evaluate active EN_ROUTE missions
    active_missions = (
        db.query(Mission)
        .filter(
            Mission.status == MissionStatus.EN_ROUTE,
            Mission.route_polyline.isnot(None),
        )
        .all()
    )

    if not active_missions:
        logger.info(f"Hazard #{hazard.id} update: No active EN_ROUTE missions in transit.")
        return []

    # Check if hazard is a blocking condition
    blocking_conditions = {
        RoadCondition.FLOODED,
        RoadCondition.BLOCKED,
        RoadCondition.DEBRIS_RESTRICTED,
        RoadCondition.BRIDGE_COLLAPSED,
        RoadCondition.HAZARDOUS,
    }

    if hazard.condition not in blocking_conditions:
        logger.info(f"Hazard #{hazard.id} condition ({hazard.condition.value}) is not a blocking hazard.")
        return []

    replanning_agent = ContinuousReplanningAgent()
    affected_mission_ids = []

    for mission in active_missions:
        try:
            route_coords = json.loads(mission.route_polyline)
            if not isinstance(route_coords, list) or len(route_coords) < 2:
                continue
        except (json.JSONDecodeError, TypeError):
            continue

        # Check route intersection using actual OSRM route geometry
        intersects = RouteIntelligenceAgent._route_intersects_hazard(route_coords, hazard)

        if not intersects:
            logger.info(f"Hazard #{hazard.id} does NOT intersect active route of Mission #{mission.id}.")
            continue

        logger.info(f"Hazard #{hazard.id} INTERSECTS route of active Mission #{mission.id}! Evaluating dynamic replan...")
        affected_mission_ids.append(mission.id)

        # Resolve team position & incident destination
        team = db.query(RescueTeam).filter(RescueTeam.id == mission.rescue_team_id).first() if mission.rescue_team_id else None
        incident = db.query(Incident).filter(Incident.id == mission.incident_id).first()

        current_lat = team.current_lat if (team and team.current_lat is not None) else route_coords[0][1]
        current_lng = team.current_lng if (team and team.current_lng is not None) else route_coords[0][0]

        dest_lat = incident.latitude if incident else route_coords[-1][1]
        dest_lng = incident.longitude if incident else route_coords[-1][0]

        res = await replanning_agent.evaluate_mission_telemetry(
            mission_id=mission.id,
            current_team_lat=current_lat,
            current_team_lng=current_lng,
            destination_lat=dest_lat,
            destination_lng=dest_lng,
            active_road_updates=[{"road_status_id": hazard.id}],
            db=db,
        )

        decision = res.get("decision")

        if decision == "REPLAN_PENDING_HITL":
            proposed_route = res.get("proposed_route", {})
            polyline = proposed_route.get("route_polyline", [])
            eta = proposed_route.get("eta_minutes")

            mission.pending_route_polyline = json.dumps(polyline) if polyline else None
            mission.pending_eta_minutes = eta
            mission.pending_replan_reason = res.get("rationale") or "Current route intersects active blocking road hazard."
            mission.pending_replan_status = "REPLAN_PENDING_HITL"
            logger.info(f"Mission #{mission.id}: SAFE DETOUR CALCULATED ({eta} mins). Set status REPLAN_PENDING_HITL.")

        elif decision in ("REPLAN_BLOCKED", "NO_SAFE_ROUTE"):
            mission.pending_route_polyline = None
            mission.pending_eta_minutes = None
            mission.pending_replan_reason = "No safe road-network route available around active hazards."
            mission.pending_replan_status = "NO_SAFE_ROUTE"
            logger.warning(f"Mission #{mission.id}: NO SAFE ROUTE DETOUR FOUND. Set status NO_SAFE_ROUTE.")

        db.commit()
        db.refresh(mission)

    return affected_mission_ids

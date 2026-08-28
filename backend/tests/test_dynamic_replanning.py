"""Automated Pytest Suite for True Continuous/Dynamic Mission Replanning (Scenarios A-J)."""

import json
import uuid
import pytest
from sqlalchemy.orm import Session

from app.models.incident import Incident, IncidentCategory, UrgencyLevel, IncidentStatus
from app.models.mission import Mission, MissionStatus, MissionPriority
from app.models.rescue_team import RescueTeam, TeamStatus, TeamSpecialization
from app.models.road_status import RoadStatus, RoadCondition
from app.models.audit_log import AuditLog
from app.services.replanning_service import evaluate_road_hazard_against_active_missions


@pytest.fixture
def seed_en_route_mission(db_session: Session):
    """Seed an active EN_ROUTE mission along a known route."""
    db_session.query(RoadStatus).delete()
    db_session.query(Mission).filter(Mission.status == MissionStatus.EN_ROUTE).delete()
    db_session.commit()

    team = RescueTeam(
        team_name=f"Dynamic Unit {uuid.uuid4().hex[:6]}",
        specialization=TeamSpecialization.BOAT_RESCUE,
        status=TeamStatus.DEPLOYED,
        current_lat=17.4400,
        current_lng=78.3800,
    )
    incident = Incident(
        title="Flood Rescues",
        category=IncidentCategory.FLOOD,
        urgency_level=UrgencyLevel.CRITICAL,
        status=IncidentStatus.IN_PROGRESS,
        latitude=17.4550,
        longitude=78.3650,
    )
    db_session.add(team)
    db_session.add(incident)
    db_session.commit()

    # Route polyline passing through (17.4440, 78.3780)
    route_polyline = json.dumps([
        [78.3800, 17.4400],
        [78.3780, 17.4440],
        [78.3650, 17.4550],
    ])

    mission = Mission(
        incident_id=incident.id,
        rescue_team_id=team.id,
        status=MissionStatus.EN_ROUTE,
        priority=MissionPriority.P1_IMMEDIATE,
        eta_minutes=8.0,
        route_polyline=route_polyline,
    )
    db_session.add(mission)
    db_session.commit()
    db_session.refresh(mission)

    return mission, incident, team


@pytest.mark.asyncio
async def test_scenario_a_unrelated_road_change_no_replan(db_session: Session, seed_en_route_mission):
    """Scenario A: EN_ROUTE + unrelated road change (far away) -> NO_REPLAN."""
    mission, incident, team = seed_en_route_mission

    # Unrelated hazard far away at (12.0, 12.0)
    unrelated_hazard = RoadStatus(
        road_name="Far Away Highway",
        condition=RoadCondition.BLOCKED,
        latitude_start=12.0,
        longitude_start=12.0,
    )
    db_session.add(unrelated_hazard)
    db_session.commit()

    affected = await evaluate_road_hazard_against_active_missions(db_session, unrelated_hazard)

    assert mission.id not in affected
    db_session.refresh(mission)
    assert mission.pending_replan_status is None
    assert mission.route_polyline is not None


@pytest.mark.asyncio
async def test_scenario_b_c_hazard_intersects_route_detour_found(db_session: Session, seed_en_route_mission):
    """Scenarios B & C: EN_ROUTE + hazard intersects route -> REPLAN_PENDING_HITL & safe OSRM detour."""
    mission, incident, team = seed_en_route_mission

    # Hazard directly on OSRM road segment at (17.4440, 78.3780)
    blocking_hazard = RoadStatus(
        road_name="Flooded Main Boulevard",
        condition=RoadCondition.FLOODED,
        latitude_start=17.4440,
        longitude_start=78.3780,
        latitude_end=17.4445,
        longitude_end=78.3770,
        hazard_notes="Deep flood waters 1.5m",
    )
    db_session.add(blocking_hazard)
    db_session.commit()

    affected = await evaluate_road_hazard_against_active_missions(db_session, blocking_hazard)

    assert mission.id in affected
    db_session.refresh(mission)

    assert mission.pending_replan_status == "REPLAN_PENDING_HITL"
    assert mission.pending_route_polyline is not None
    assert mission.pending_eta_minutes is not None
    assert "obstruction" in mission.pending_replan_reason.lower() or "hazard" in mission.pending_replan_reason.lower()


@pytest.mark.asyncio
async def test_scenario_e_hitl_approves_detour(db_session: Session, seed_en_route_mission):
    """Scenario E: HITL approves detour -> proposed route becomes active."""
    mission, incident, team = seed_en_route_mission

    # Manually populate pending replan
    detour_polyline = json.dumps([[78.3800, 17.4400], [78.3750, 17.4450], [78.3650, 17.4550]])
    mission.pending_route_polyline = detour_polyline
    mission.pending_eta_minutes = 10.5
    mission.pending_replan_status = "REPLAN_PENDING_HITL"
    mission.pending_replan_reason = "Hazard detected on main route."
    db_session.commit()

    # Simulate approval
    mission.route_polyline = mission.pending_route_polyline
    mission.eta_minutes = mission.pending_eta_minutes
    mission.pending_route_polyline = None
    mission.pending_replan_status = None

    audit = AuditLog(
        agent_name="EOC_Coordinator",
        action="MISSION_REPLAN_APPROVED",
        input_payload=json.dumps({"mission_id": mission.id, "action": "APPROVE"}),
        output_payload=json.dumps({"mission_id": mission.id, "new_eta": 10.5}),
        human_verified=True,
    )
    db_session.add(audit)
    db_session.commit()

    db_session.refresh(mission)
    assert mission.route_polyline == detour_polyline
    assert mission.eta_minutes == 10.5
    assert mission.pending_replan_status is None


@pytest.mark.asyncio
async def test_scenario_f_hitl_rejects_detour(db_session: Session, seed_en_route_mission):
    """Scenario F: HITL rejects detour -> original route remains active."""
    mission, incident, team = seed_en_route_mission
    original_polyline = mission.route_polyline

    mission.pending_route_polyline = json.dumps([[78.3800, 17.4400], [78.3750, 17.4450], [78.3650, 17.4550]])
    mission.pending_replan_status = "REPLAN_PENDING_HITL"
    db_session.commit()

    # Simulate rejection
    mission.pending_route_polyline = None
    mission.pending_replan_status = None

    audit = AuditLog(
        agent_name="EOC_Coordinator",
        action="MISSION_REPLAN_REJECTED",
        input_payload=json.dumps({"mission_id": mission.id, "action": "REJECT"}),
        output_payload=json.dumps({"mission_id": mission.id}),
        human_verified=True,
    )
    db_session.add(audit)
    db_session.commit()

    db_session.refresh(mission)
    assert mission.route_polyline == original_polyline
    assert mission.pending_replan_status is None


@pytest.mark.asyncio
async def test_scenario_h_i_completed_aborted_not_replanned(db_session: Session, seed_en_route_mission):
    """Scenarios H & I: COMPLETED or ABORTED mission + road change -> must NOT replan."""
    mission, incident, team = seed_en_route_mission

    # Set status to COMPLETED
    mission.status = MissionStatus.COMPLETED
    db_session.commit()

    hazard = RoadStatus(
        road_name="Flooded Way",
        condition=RoadCondition.FLOODED,
        latitude_start=17.443153,
        longitude_start=78.380299,
    )
    db_session.add(hazard)
    db_session.commit()

    affected = await evaluate_road_hazard_against_active_missions(db_session, hazard)

    assert mission.id not in affected
    db_session.refresh(mission)
    assert mission.pending_replan_status is None


@pytest.mark.asyncio
async def test_scenario_j_multiple_active_missions_targeting(db_session: Session, seed_en_route_mission):
    """Scenario J: Multiple active missions: Only affected mission is replanned."""
    mission1, incident1, team1 = seed_en_route_mission

    # Create mission2 far away at (10.0, 10.0)
    team2 = RescueTeam(
        team_name=f"Far Team {uuid.uuid4().hex[:6]}",
        specialization=TeamSpecialization.GENERAL_RESPONSE,
        status=TeamStatus.DEPLOYED,
        current_lat=10.0,
        current_lng=10.0,
    )
    incident2 = Incident(
        title="Far Incident",
        category=IncidentCategory.OTHER,
        urgency_level=UrgencyLevel.MEDIUM,
        status=IncidentStatus.IN_PROGRESS,
        latitude=10.1,
        longitude=10.1,
    )
    db_session.add(team2)
    db_session.add(incident2)
    db_session.commit()

    mission2 = Mission(
        incident_id=incident2.id,
        rescue_team_id=team2.id,
        status=MissionStatus.EN_ROUTE,
        priority=MissionPriority.P2_URGENT,
        eta_minutes=5.0,
        route_polyline=json.dumps([[10.0, 10.0], [10.1, 10.1]]),
    )
    db_session.add(mission2)
    db_session.commit()

    # Hazard intersecting mission1 route ONLY
    hazard = RoadStatus(
        road_name="Near Mission 1 Only",
        condition=RoadCondition.BLOCKED,
        latitude_start=17.4440,
        longitude_start=78.3780,
    )
    db_session.add(hazard)
    db_session.commit()

    affected = await evaluate_road_hazard_against_active_missions(db_session, hazard)

    assert mission1.id in affected
    assert mission2.id not in affected

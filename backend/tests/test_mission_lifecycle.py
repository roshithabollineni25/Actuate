"""Complete test suite for mission dispatch lifecycle, approval gates, team status sync, and audit logging."""

import json
import pytest
from app.models.mission import Mission, MissionStatus, MissionPriority
from app.models.rescue_team import RescueTeam, TeamStatus
from app.models.incident import Incident, IncidentCategory, UrgencyLevel, IncidentStatus
from app.models.audit_log import AuditLog
from app.agents.mission_agent import MissionCoordinationAgent


import uuid
from app.models.rescue_team import RescueTeam, TeamStatus, TeamSpecialization

@pytest.fixture
def seed_incident_and_team(db_session):
    """Seed a test incident and rescue team."""
    incident = Incident(
        title="Test Flood Incident",
        description="Flood stranded residents",
        category=IncidentCategory.FLOOD,
        urgency_level=UrgencyLevel.CRITICAL,
        status=IncidentStatus.REPORTED,
        latitude=17.4450,
        longitude=78.3850,
        estimated_casualties=3,
    )
    team = RescueTeam(
        team_name=f"Alpha Rescue Unit {uuid.uuid4().hex[:6]}",
        specialization=TeamSpecialization.BOAT_RESCUE,
        status=TeamStatus.AVAILABLE,
        current_lat=17.4400,
        current_lng=78.3800,
    )
    db_session.add(incident)
    db_session.add(team)
    db_session.commit()
    db_session.refresh(incident)
    db_session.refresh(team)
    return incident, team


@pytest.mark.asyncio
async def test_happy_path_mission_lifecycle(db_session, seed_incident_and_team):
    """Scenario A: PROPOSED -> APPROVED -> DISPATCHED -> EN_ROUTE -> ON_SCENE -> COMPLETED."""
    incident, team = seed_incident_and_team
    agent = MissionCoordinationAgent()

    # 1. PROPOSED
    proposal = await agent.synthesize_mission_proposal(
        db=db_session,
        incident_id=incident.id,
        situation_data={"category": "FLOOD", "urgency_level": "CRITICAL"},
        risk_data={"triage_level": "CRITICAL", "matched_hazards": ["Flooded Road"]},
        resource_data={"rescue_team_id": team.id},
        route_data={"route_polyline": "[[78.38, 17.44], [78.385, 17.445]]", "eta_minutes": 5.2},
    )
    mission_id = proposal["mission_id"]
    assert proposal["status"] == "PROPOSED"

    # Verify DB state
    mission_db = db_session.query(Mission).filter(Mission.id == mission_id).first()
    assert mission_db.status == MissionStatus.PROPOSED
    assert team.status == TeamStatus.AVAILABLE

    # 2. APPROVED (Human Approval Gate)
    auth_res = await agent.authorize_mission(
        db=db_session,
        mission_id=mission_id,
        coordinator_user_id=1,
        action="APPROVE",
        notes="Approved for emergency dispatch",
    )
    assert auth_res["status"] == "APPROVED"
    assert auth_res["approved_by"] == 1

    db_session.refresh(mission_db)
    assert mission_db.status == MissionStatus.APPROVED

    # 3. DISPATCHED (Coordinator Dispatch & Rescue Team Status Sync)
    disp_res = await agent.dispatch_mission(
        db=db_session,
        mission_id=mission_id,
        coordinator_user_id=1,
        notes="Dispatched Alpha Rescue Unit",
    )
    assert disp_res["status"] == "DISPATCHED"

    db_session.refresh(mission_db)
    db_session.refresh(team)
    assert mission_db.status == MissionStatus.DISPATCHED
    assert team.status == TeamStatus.DEPLOYED  # Team status updated to DEPLOYED

    # 4. EN_ROUTE (Rescue Team Accepts & Departs)
    en_route_res = await agent.transition_mission(
        db=db_session,
        mission_id=mission_id,
        actor_user_id=10,
        actor_role="RESCUE_TEAM",
        target_status="EN_ROUTE",
        notes="Departed base station",
    )
    assert en_route_res["status"] == "EN_ROUTE"
    db_session.refresh(mission_db)
    assert mission_db.status == MissionStatus.EN_ROUTE
    assert mission_db.route_polyline == "[[78.38, 17.44], [78.385, 17.445]]"  # OSRM route preserved

    # 5. ON_SCENE (Team Arrives)
    on_scene_res = await agent.transition_mission(
        db=db_session,
        mission_id=mission_id,
        actor_user_id=10,
        actor_role="RESCUE_TEAM",
        target_status="ON_SCENE",
        notes="Arrived at flooded structure",
    )
    assert on_scene_res["status"] == "ON_SCENE"
    db_session.refresh(mission_db)
    assert mission_db.status == MissionStatus.ON_SCENE

    # 6. COMPLETED (Rescue Complete & Team Reset to AVAILABLE)
    completed_res = await agent.transition_mission(
        db=db_session,
        mission_id=mission_id,
        actor_user_id=10,
        actor_role="RESCUE_TEAM",
        target_status="COMPLETED",
        notes="All 3 victims safely evacuated",
    )
    assert completed_res["status"] == "COMPLETED"

    db_session.refresh(mission_db)
    db_session.refresh(team)
    assert mission_db.status == MissionStatus.COMPLETED
    assert team.status == TeamStatus.AVAILABLE  # Reset to AVAILABLE


@pytest.mark.asyncio
async def test_abort_from_approved(db_session, seed_incident_and_team):
    """Scenario B: APPROVED -> ABORTED."""
    incident, team = seed_incident_and_team
    agent = MissionCoordinationAgent()

    proposal = await agent.synthesize_mission_proposal(
        db=db_session,
        incident_id=incident.id,
        situation_data={"category": "FLOOD"},
        risk_data={"triage_level": "HIGH"},
        resource_data={"rescue_team_id": team.id},
        route_data={"eta_minutes": 10},
    )
    mission_id = proposal["mission_id"]

    await agent.authorize_mission(
        db=db_session, mission_id=mission_id, coordinator_user_id=1, action="APPROVE"
    )

    abort_res = await agent.abort_mission(
        db=db_session, mission_id=mission_id, actor_user_id=1, actor_role="ADMIN", notes="False alarm"
    )
    assert abort_res["status"] == "ABORTED"

    mission_db = db_session.query(Mission).filter(Mission.id == mission_id).first()
    assert mission_db.status == MissionStatus.ABORTED


@pytest.mark.asyncio
async def test_abort_from_dispatched(db_session, seed_incident_and_team):
    """Scenario C: DISPATCHED -> ABORTED."""
    incident, team = seed_incident_and_team
    agent = MissionCoordinationAgent()

    proposal = await agent.synthesize_mission_proposal(
        db=db_session,
        incident_id=incident.id,
        situation_data={"category": "FLOOD"},
        risk_data={"triage_level": "HIGH"},
        resource_data={"rescue_team_id": team.id},
        route_data={"eta_minutes": 10},
    )
    mission_id = proposal["mission_id"]

    await agent.authorize_mission(
        db=db_session, mission_id=mission_id, coordinator_user_id=1, action="APPROVE"
    )
    await agent.dispatch_mission(
        db=db_session, mission_id=mission_id, coordinator_user_id=1
    )

    db_session.refresh(team)
    assert team.status == TeamStatus.DEPLOYED

    abort_res = await agent.abort_mission(
        db=db_session, mission_id=mission_id, actor_user_id=1, actor_role="ADMIN", notes="Hazmat threat detected"
    )
    assert abort_res["status"] == "ABORTED"

    db_session.refresh(team)
    assert team.status == TeamStatus.AVAILABLE  # Reset to AVAILABLE on abort


@pytest.mark.asyncio
async def test_invalid_transition_proposed_to_completed(db_session, seed_incident_and_team):
    """Scenario D: PROPOSED -> COMPLETED must fail."""
    incident, team = seed_incident_and_team
    agent = MissionCoordinationAgent()

    proposal = await agent.synthesize_mission_proposal(
        db=db_session,
        incident_id=incident.id,
        situation_data={"category": "FLOOD"},
        risk_data={"triage_level": "HIGH"},
        resource_data={"rescue_team_id": team.id},
        route_data={"eta_minutes": 10},
    )
    mission_id = proposal["mission_id"]

    with pytest.raises(ValueError, match="cannot transition from PROPOSED to COMPLETED"):
        await agent.transition_mission(
            db=db_session,
            mission_id=mission_id,
            actor_user_id=10,
            actor_role="RESCUE_TEAM",
            target_status="COMPLETED",
        )


@pytest.mark.asyncio
async def test_dispatch_without_approval_must_fail(db_session, seed_incident_and_team):
    """Scenario E: Dispatching PROPOSED mission without approval must fail."""
    incident, team = seed_incident_and_team
    agent = MissionCoordinationAgent()

    proposal = await agent.synthesize_mission_proposal(
        db=db_session,
        incident_id=incident.id,
        situation_data={"category": "FLOOD"},
        risk_data={"triage_level": "HIGH"},
        resource_data={"rescue_team_id": team.id},
        route_data={"eta_minutes": 10},
    )
    mission_id = proposal["mission_id"]

    with pytest.raises(ValueError, match="cannot be dispatched from status PROPOSED"):
        await agent.dispatch_mission(
            db=db_session, mission_id=mission_id, coordinator_user_id=1
        )


@pytest.mark.asyncio
async def test_audit_logs_for_every_transition(db_session, seed_incident_and_team):
    """Scenario F: Every successful transition creates an audit log entry."""
    incident, team = seed_incident_and_team
    agent = MissionCoordinationAgent()

    initial_audit_count = db_session.query(AuditLog).count()

    proposal = await agent.synthesize_mission_proposal(
        db=db_session,
        incident_id=incident.id,
        situation_data={"category": "FLOOD"},
        risk_data={"triage_level": "HIGH"},
        resource_data={"rescue_team_id": team.id},
        route_data={"eta_minutes": 10},
    )
    mission_id = proposal["mission_id"]

    await agent.authorize_mission(db=db_session, mission_id=mission_id, coordinator_user_id=1, action="APPROVE")
    await agent.dispatch_mission(db=db_session, mission_id=mission_id, coordinator_user_id=1)
    await agent.transition_mission(db=db_session, mission_id=mission_id, actor_user_id=10, actor_role="RESCUE_TEAM", target_status="EN_ROUTE")
    await agent.transition_mission(db=db_session, mission_id=mission_id, actor_user_id=10, actor_role="RESCUE_TEAM", target_status="ON_SCENE")
    await agent.transition_mission(db=db_session, mission_id=mission_id, actor_user_id=10, actor_role="RESCUE_TEAM", target_status="COMPLETED")

    final_audit_count = db_session.query(AuditLog).count()
    # Exactly 6 audit log entries created for this mission lifecycle
    assert final_audit_count - initial_audit_count == 6


@pytest.mark.asyncio
async def test_database_state_matches_api(db_session, seed_incident_and_team):
    """Scenario G: Database state after lifecycle matches API response."""
    incident, team = seed_incident_and_team
    agent = MissionCoordinationAgent()

    proposal = await agent.synthesize_mission_proposal(
        db=db_session,
        incident_id=incident.id,
        situation_data={"category": "FLOOD"},
        risk_data={"triage_level": "HIGH"},
        resource_data={"rescue_team_id": team.id},
        route_data={"eta_minutes": 10},
    )
    mission_id = proposal["mission_id"]

    await agent.authorize_mission(db=db_session, mission_id=mission_id, coordinator_user_id=1, action="APPROVE")
    await agent.dispatch_mission(db=db_session, mission_id=mission_id, coordinator_user_id=1)
    res = await agent.transition_mission(
        db=db_session, mission_id=mission_id, actor_user_id=10, actor_role="RESCUE_TEAM", target_status="EN_ROUTE"
    )

    mission_db = db_session.query(Mission).filter(Mission.id == mission_id).first()
    assert mission_db.status.value == res["status"]
    assert res["status"] == "EN_ROUTE"

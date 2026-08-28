"""Tests for Route Intelligence Agent and Continuous Replanning Agent."""

import json
import pytest
from app.agents.route_agent import RouteIntelligenceAgent
from app.agents.replanning_agent import ContinuousReplanningAgent
from app.models.road_status import RoadStatus, RoadCondition
from app.models.incident import Incident, IncidentCategory, IncidentStatus, UrgencyLevel
from app.models.rescue_team import RescueTeam, TeamSpecialization, TeamStatus
from app.models.mission import Mission, MissionStatus, MissionPriority


def test_point_to_segment_distance_accuracy():
    """Verify that point-to-segment distance calculation returns accurate distance in KM."""
    agent = RouteIntelligenceAgent()
    
    # Segment from (17.4400, 78.3800) to (17.4400, 78.3900) - approx 1.06 km long
    # Point at (17.4400, 78.3850) is right on the segment -> distance should be ~0.0 km
    dist_on_segment = agent._point_to_segment_distance_km(
        point_lat=17.4400,
        point_lng=78.3850,
        start_lat=17.4400,
        start_lng=78.3800,
        end_lat=17.4400,
        end_lng=78.3900,
    )
    assert dist_on_segment < 0.01

    # Point at 1 km north (approx 0.009 degrees lat diff)
    # 1 degree lat ~ 111.32 km -> 0.009 deg ~ 1.0 km
    dist_1km_off = agent._point_to_segment_distance_km(
        point_lat=17.4490,
        point_lng=78.3850,
        start_lat=17.4400,
        start_lng=78.3800,
        end_lat=17.4400,
        end_lng=78.3900,
    )
    assert 0.9 < dist_1km_off < 1.1


def test_route_intersects_hazard_detection():
    """Verify that hazard intersection detects routes passing through hazard segments."""
    agent = RouteIntelligenceAgent()

    hazard = RoadStatus(
        id=1,
        osm_way_id="test-way",
        road_name="Main St",
        condition=RoadCondition.BLOCKED,
        latitude_start=17.4400,
        longitude_start=78.3800,
        latitude_end=17.4400,
        longitude_end=78.3900,
    )

    # Route passing directly through the hazard segment
    intersecting_route = [
        [78.3750, 17.4400],
        [78.3850, 17.4400],
        [78.3950, 17.4400],
    ]
    assert agent._route_intersects_hazard(intersecting_route, hazard) is True

    # Route 2 km away from hazard segment
    clear_route = [
        [78.3750, 17.4600],
        [78.3850, 17.4600],
        [78.3950, 17.4600],
    ]
    assert agent._route_intersects_hazard(clear_route, hazard) is False


@pytest.mark.asyncio
async def test_compute_safe_route_real_osrm(db_session):
    """Test real OSRM route computation between valid coordinates."""
    agent = RouteIntelligenceAgent()
    
    # Real driving coordinates in Hyderabad
    origin_lat, origin_lng = 17.4400, 78.3800
    dest_lat, dest_lng = 17.4550, 78.3650

    result = await agent.compute_safe_route(
        origin_lat=origin_lat,
        origin_lng=origin_lng,
        destination_lat=dest_lat,
        destination_lng=dest_lng,
        db=db_session,
        avoid_hazards=False,
    )

    assert result["route_status"] == "SAFE_ROUTE_FOUND"
    assert result["routing_engine"] == "OSRM"
    assert result["is_simulated"] is False
    assert len(result["route_polyline"]) > 1
    assert result["distance_km"] > 0.0
    assert result["eta_minutes"] > 0.0


@pytest.mark.asyncio
async def test_replanning_agent_clear_route(db_session):
    """Test replanning evaluation when route is clear of hazards."""
    # Seed incident, team, mission
    import uuid
    team = RescueTeam(
        team_name=f"Test Team Clear {uuid.uuid4().hex[:6]}",
        specialization=TeamSpecialization.GENERAL_RESPONSE,
        status=TeamStatus.DEPLOYED,
        current_lat=10.0,
        current_lng=10.0,
    )
    incident = Incident(
        title="Test Incident Clear",
        category=IncidentCategory.OTHER,
        urgency_level=UrgencyLevel.MEDIUM,
        status=IncidentStatus.IN_PROGRESS,
        latitude=10.1,
        longitude=10.1,
    )
    db_session.query(RoadStatus).delete()
    db_session.commit()

    db_session.add(team)
    db_session.add(incident)
    db_session.commit()

    mission = Mission(
        incident_id=incident.id,
        rescue_team_id=team.id,
        status=MissionStatus.EN_ROUTE,
        priority=MissionPriority.P2_URGENT,
        eta_minutes=10.0,
        route_polyline=json.dumps([[10.0, 10.0], [10.1, 10.1]]),
    )
    db_session.add(mission)
    db_session.commit()

    replanning_agent = ContinuousReplanningAgent()
    res = await replanning_agent.evaluate_mission_telemetry(
        mission_id=mission.id,
        current_team_lat=10.0,
        current_team_lng=10.0,
        destination_lat=10.1,
        destination_lng=10.1,
        active_road_updates=[],
        db=db_session,
    )

    assert res["decision"] == "NO_REPLAN"
    assert res["mission_id"] == mission.id

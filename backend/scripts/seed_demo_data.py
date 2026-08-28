"""Deterministic seed script for ResQMesh AI platform demo data.

Seeds real OSRM road-network route geometry and consistent geographic records:
- Rescue Team Alpha
- Incident (Flooding at Kondapur)
- Road Status (hazard segment on the actual OSRM route)
- Active Mission with real OSRM route polyline
"""

import asyncio
import json
import os
import sys

# Ensure backend root is on Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import httpx
from app.db.session import SessionLocal, engine
from app.db.base import Base
from app.models.incident import Incident, IncidentCategory, IncidentStatus, UrgencyLevel
from app.models.rescue_team import RescueTeam, TeamSpecialization, TeamStatus
from app.models.road_status import RoadStatus, RoadCondition
from app.models.mission import Mission, MissionStatus, MissionPriority
from app.models.resource import Resource, ResourceType, ResourceStatus


OSRM_BASE_URL = "https://router.project-osrm.org"


async def fetch_osrm_route(
    origin_lat: float, origin_lng: float, dest_lat: float, dest_lng: float
):
    """Query OSRM for real driving route geometry."""
    url = f"{OSRM_BASE_URL}/route/v1/driving/{origin_lng},{origin_lat};{dest_lng},{dest_lat}"
    params = {
        "overview": "full",
        "geometries": "geojson",
        "steps": "true",
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(url, params=params)
    response.raise_for_status()
    payload = response.json()
    if payload.get("code") != "Ok" or not payload.get("routes"):
        raise RuntimeError(f"OSRM query failed: {payload}")
    return payload["routes"][0]


async def seed_data():
    """Execute deterministic database seed process."""
    print("Initializing database tables...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        print("Clearing existing demo data...")
        db.query(Mission).delete()
        db.query(RoadStatus).delete()
        db.query(Incident).delete()
        db.query(RescueTeam).delete()
        db.query(Resource).delete()
        db.commit()

        # Real coordinates in Hyderabad, India
        team_lat, team_lng = 17.4400, 78.3800      # Hitec City area
        incident_lat, incident_lng = 17.4550, 78.3650  # Kondapur area

        print(f"Fetching real OSRM route from ({team_lat}, {team_lng}) to ({incident_lat}, {incident_lng})...")
        osrm_route = await fetch_osrm_route(team_lat, team_lng, incident_lat, incident_lng)

        route_coords = osrm_route["geometry"]["coordinates"]
        dist_km = round(osrm_route["distance"] / 1000, 2)
        duration_mins = round(osrm_route["duration"] / 60, 1)

        print(f"Fetched OSRM route: {len(route_coords)} waypoints, {dist_km} km, {duration_mins} mins.")

        # Pick a middle segment of the real OSRM route for the road hazard
        mid_idx = len(route_coords) // 2
        p1 = route_coords[mid_idx]
        p2 = route_coords[mid_idx + 1] if mid_idx + 1 < len(route_coords) else route_coords[mid_idx]

        # 1. Rescue Team
        team = RescueTeam(
            team_name="Rescue Team Alpha",
            specialization=TeamSpecialization.BOAT_RESCUE,
            status=TeamStatus.DEPLOYED,
            capacity=6,
            current_lat=team_lat,
            current_lng=team_lng,
            contact_radio_channel="CH-14",
        )
        db.add(team)
        db.flush()

        # 2. Incident
        incident = Incident(
            title="Severe Flooding & Trapped Residents",
            description="Flash flood in Kondapur residential block. 5 persons trapped on roof.",
            category=IncidentCategory.FLOOD,
            urgency_level=UrgencyLevel.CRITICAL,
            status=IncidentStatus.IN_PROGRESS,
            latitude=incident_lat,
            longitude=incident_lng,
            address="Kondapur Main Road, Hyderabad",
            estimated_casualties=5,
        )
        db.add(incident)
        db.flush()

        # 3. Road Hazard along real segment
        road_status = RoadStatus(
            osm_way_id="25491034",
            road_name="Hitec City - Kondapur Connecting Corridor",
            condition=RoadCondition.FLOODED,
            hazard_notes="Water level 1.2m blocking primary rescue corridor.",
            latitude_start=p1[1],
            longitude_start=p1[0],
            latitude_end=p2[1],
            longitude_end=p2[0],
        )
        db.add(road_status)
        db.flush()

        # 4. Resources
        resource = Resource(
            name="Inflatable Rescue Boat-1",
            type=ResourceType.LIFE_BOAT,
            total_quantity=2,
            available_quantity=1,
            location_lat=team_lat,
            location_lng=team_lng,
            depot_name="Hitec City Emergency Depot",
            status=ResourceStatus.AVAILABLE,
        )
        db.add(resource)

        # 5. Mission with REAL route geometry
        mission = Mission(
            incident_id=incident.id,
            rescue_team_id=team.id,
            status=MissionStatus.EN_ROUTE,
            priority=MissionPriority.P1_IMMEDIATE,
            eta_minutes=duration_mins,
            route_polyline=json.dumps(route_coords),
            mission_brief=f"Deploy Rescue Team Alpha to Kondapur flood site ({dist_km} km, ~{duration_mins} mins).",
        )
        db.add(mission)
        db.commit()

        print("Database seed completed successfully!")
        print(f"Created Incident #{incident.id}, Rescue Team #{team.id}, RoadStatus #{road_status.id}, Mission #{mission.id}.")

    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise e
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(seed_data())

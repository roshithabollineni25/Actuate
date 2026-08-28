"""Integration verification script for ResQMesh AI endpoints."""

import asyncio
import json
import os
import sys

# Ensure backend root is on Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app
from app.core.security import create_access_token
from app.db.session import SessionLocal
from app.models.road_status import RoadStatus, RoadCondition
from app.models.mission import Mission


def run_integration_tests():
    client = TestClient(app)

    print("=== 1. VERIFY HEALTH ENDPOINT ===")
    r = client.get("/api/v1/health")
    print(f"GET /api/v1/health -> {r.status_code}: {r.json()}")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

    print("\n=== 2. VERIFY DATABASE HEALTH ENDPOINT ===")
    r = client.get("/api/v1/health/db")
    print(f"GET /api/v1/health/db -> {r.status_code}: {r.json()}")
    assert r.status_code == 200

    admin_token = create_access_token(subject="1", role="ADMIN")
    headers = {"Authorization": f"Bearer {admin_token}"}

    print("\n=== 3. VERIFY ROAD-STATUS GET ===")
    r = client.get("/api/v1/road-status", headers=headers)
    print(f"GET /api/v1/road-status -> {r.status_code}, count={len(r.json())}")
    assert r.status_code == 200
    road_statuses = r.json()
    assert len(road_statuses) > 0
    hazard_id = road_statuses[0]["id"]

    print(f"\n=== 4. VERIFY ROAD-STATUS PATCH (ID #{hazard_id}) ===")
    patch_payload = {
        "condition": "FLOODED",
        "hazard_notes": "Updated: Flash flood water level 1.5m",
    }
    r = client.patch(f"/api/v1/road-status/{hazard_id}", json=patch_payload, headers=headers)
    print(f"PATCH /api/v1/road-status/{hazard_id} -> {r.status_code}: {r.json()['hazard_notes']}")
    assert r.status_code == 200
    assert r.json()["condition"] == "FLOODED"

    db = SessionLocal()
    mission = db.query(Mission).first()
    mission_id = mission.id if mission else 1
    db.close()

    print(f"\n=== 5. VERIFY MISSION REPLANNING EVALUATE (CLEAR ROAD SCENARIO) ===")
    # Temporarily set hazard condition to CLEAR to test clear road scenario
    r_patch = client.patch(f"/api/v1/road-status/{hazard_id}", json={"condition": "CLEAR"}, headers=headers)
    
    replan_payload_clear = {
        "current_team_lat": 17.4400,
        "current_team_lng": 78.3800,
        "destination_lat": 17.4550,
        "destination_lng": 78.3650,
        "active_road_updates": [],
    }
    r = client.post(f"/api/v1/missions/{mission_id}/replan/evaluate", json=replan_payload_clear, headers=headers)
    print(f"Clear road replan decision -> {r.status_code}: decision='{r.json().get('decision')}'")
    assert r.status_code == 200
    assert r.json()["decision"] == "NO_REPLAN"

    print(f"\n=== 6. VERIFY MISSION REPLANNING EVALUATE (BLOCKED ROAD & REAL DETOUR SCENARIO) ===")
    # Restore hazard to FLOODED on the primary route segment
    r_patch = client.patch(f"/api/v1/road-status/{hazard_id}", json={"condition": "FLOODED"}, headers=headers)

    replan_payload_blocked = {
        "current_team_lat": 17.4400,
        "current_team_lng": 78.3800,
        "destination_lat": 17.4550,
        "destination_lng": 78.3650,
        "active_road_updates": [{"road_status_id": hazard_id}],
    }
    r = client.post(f"/api/v1/missions/{mission_id}/replan/evaluate", json=replan_payload_blocked, headers=headers)
    data = r.json()
    print(f"Blocked road replan decision -> {r.status_code}: decision='{data.get('decision')}'")
    print(f"Rationale: {data.get('rationale')}")
    if data.get("proposed_route"):
        print(f"Proposed Route Status: {data['proposed_route'].get('route_status')}, engine={data['proposed_route'].get('routing_engine')}")
        print(f"Distance: {data['proposed_route'].get('distance_km')} km, ETA: {data['proposed_route'].get('eta_minutes')} mins")
    
    assert r.status_code == 200
    assert data["decision"] in ("REPLAN_PENDING_HITL", "REPLAN_BLOCKED")

    print("\nALL API VERIFICATION CHECKS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    run_integration_tests()

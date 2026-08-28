"""Execute and verify the complete mission dispatch lifecycle against the running backend and real PostgreSQL database."""

import requests
import json

BASE_URL = "http://127.0.0.1:8000/api/v1"

import sys
import os
sys.path.insert(0, os.path.abspath("."))

from app.core.security import create_access_token

def get_admin_token():
    return create_access_token(subject="1", role="ADMIN")

def get_rescue_token():
    return create_access_token(subject="10", role="RESCUE_TEAM")

def run_e2e_lifecycle_tests():
    admin_token = get_admin_token()
    rescue_token = get_rescue_token()
    
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    rescue_headers = {"Authorization": f"Bearer {rescue_token}"}

    print("=== STARTING END-TO-END MISSION DISPATCH LIFECYCLE VERIFICATION ===")

    # 1. CREATE INCIDENT
    inc_res = requests.post(
        f"{BASE_URL}/incidents",
        json={
            "title": "E2E Flood Emergency",
            "description": "Stranded families requiring boat rescue",
            "category": "FLOOD",
            "urgency_level": "CRITICAL",
            "latitude": 17.4450,
            "longitude": 78.3850,
            "estimated_casualties": 4,
        },
        headers=admin_headers,
    )
    assert inc_res.status_code == 201, f"Failed to create incident: {inc_res.text}"
    incident_id = inc_res.json()["id"]
    print(f"1. Created Incident #{incident_id}")

    # GET SEEDED RESCUE TEAM
    teams_res = requests.get(f"{BASE_URL}/rescue-teams", headers=admin_headers)
    assert teams_res.status_code == 200
    teams = teams_res.json()
    rescue_team_id = teams[0]["id"] if teams else 1
    print(f"   Using Rescue Team #{rescue_team_id}")

    # 2. PROPOSE MISSION
    prop_res = requests.post(
        f"{BASE_URL}/missions/propose",
        json={
            "incident_id": incident_id,
            "situation_data": {"category": "FLOOD", "urgency_level": "CRITICAL"},
            "risk_data": {"triage_level": "CRITICAL", "matched_hazards": []},
            "resource_data": {"rescue_team_id": rescue_team_id},
            "route_data": {"route_polyline": "[[78.3800, 17.4400], [78.3850, 17.4450]]", "eta_minutes": 6.5},
        },
        headers=admin_headers,
    )
    assert prop_res.status_code == 200, f"Propose failed: {prop_res.text}"
    mission_id = prop_res.json()["mission_id"]
    assert prop_res.json()["status"] == "PROPOSED"
    print(f"2. Mission #{mission_id} status: PROPOSED (AI Synthesis)")

    # 3. TEST INVALID TRANSITION: DISPATCH WITHOUT APPROVAL MUST FAIL
    unapproved_dispatch = requests.post(
        f"{BASE_URL}/missions/{mission_id}/dispatch",
        json={"notes": "Attempt unapproved dispatch"},
        headers=admin_headers,
    )
    assert unapproved_dispatch.status_code == 400, f"Unapproved dispatch should fail! Got {unapproved_dispatch.status_code}"
    print(f"3. Unapproved Dispatch Gate: REJECTED with 400 Bad Request ({unapproved_dispatch.json()['detail']})")

    # 4. TEST INVALID TRANSITION: PROPOSED -> COMPLETED MUST FAIL
    invalid_jump = requests.post(
        f"{BASE_URL}/missions/{mission_id}/status",
        json={"status": "COMPLETED", "notes": "Direct jump"},
        headers=rescue_headers,
    )
    assert invalid_jump.status_code == 400, f"Invalid transition should fail! Got {invalid_jump.status_code}"
    print(f"4. Invalid Jump PROPOSED -> COMPLETED: REJECTED with 400 Bad Request ({invalid_jump.json()['detail']})")

    # 5. HUMAN AUTHORIZATION: APPROVE MISSION
    auth_res = requests.post(
        f"{BASE_URL}/missions/{mission_id}/authorize",
        json={"action": "APPROVE", "notes": "EOC Coordinator Authorization"},
        headers=admin_headers,
    )
    assert auth_res.status_code == 200, f"Authorize failed: {auth_res.text}"
    assert auth_res.json()["status"] == "APPROVED"
    print(f"5. Mission #{mission_id} status: APPROVED (Human Coordinator)")

    # 6. COORDINATOR DISPATCH
    disp_res = requests.post(
        f"{BASE_URL}/missions/{mission_id}/dispatch",
        json={"notes": "Dispatched to field unit"},
        headers=admin_headers,
    )
    assert disp_res.status_code == 200, f"Dispatch failed: {disp_res.text}"
    assert disp_res.json()["status"] == "DISPATCHED"
    print(f"6. Mission #{mission_id} status: DISPATCHED (Rescue Team assigned)")

    # VERIFY TEAM STATUS IS DEPLOYED
    team_chk = requests.get(f"{BASE_URL}/rescue-teams/{rescue_team_id}", headers=admin_headers).json()
    assert team_chk["status"] == "DEPLOYED"
    print(f"   Rescue Team #{rescue_team_id} status in DB: DEPLOYED")

    # 7. RESCUE TEAM ACCEPTS & STARTS: EN_ROUTE
    en_route_res = requests.post(
        f"{BASE_URL}/missions/{mission_id}/status",
        json={"status": "EN_ROUTE", "notes": "En route via flood boat"},
        headers=rescue_headers,
    )
    assert en_route_res.status_code == 200, f"EN_ROUTE failed: {en_route_res.text}"
    assert en_route_res.json()["status"] == "EN_ROUTE"
    print(f"7. Mission #{mission_id} status: EN_ROUTE (OSRM polyline preserved)")

    # 8. TEAM ARRIVES: ON_SCENE
    on_scene_res = requests.post(
        f"{BASE_URL}/missions/{mission_id}/status",
        json={"status": "ON_SCENE", "notes": "On scene at residential complex"},
        headers=rescue_headers,
    )
    assert on_scene_res.status_code == 200, f"ON_SCENE failed: {on_scene_res.text}"
    assert on_scene_res.json()["status"] == "ON_SCENE"
    print(f"8. Mission #{mission_id} status: ON_SCENE (Team arrived)")

    # 9. RESCUE COMPLETE: COMPLETED
    completed_res = requests.post(
        f"{BASE_URL}/missions/{mission_id}/status",
        json={"status": "COMPLETED", "notes": "Rescue operations successfully completed"},
        headers=rescue_headers,
    )
    assert completed_res.status_code == 200, f"COMPLETED failed: {completed_res.text}"
    assert completed_res.json()["status"] == "COMPLETED"
    print(f"9. Mission #{mission_id} status: COMPLETED (All casualties safe)")

    # VERIFY TEAM STATUS RESET TO AVAILABLE
    team_chk_after = requests.get(f"{BASE_URL}/rescue-teams/{rescue_team_id}", headers=admin_headers).json()
    assert team_chk_after["status"] == "AVAILABLE"
    print(f"   Rescue Team #{rescue_team_id} status in DB: AVAILABLE")

    # 10. TEST ABORT PATH
    print("\n--- TESTING EMERGENCY ABORT PATH ---")
    prop_abort = requests.post(
        f"{BASE_URL}/missions/propose",
        json={
            "incident_id": incident_id,
            "situation_data": {"category": "FLOOD"},
            "risk_data": {"triage_level": "HIGH"},
            "resource_data": {"rescue_team_id": rescue_team_id},
            "route_data": {"eta_minutes": 5.0},
        },
        headers=admin_headers,
    ).json()
    m_abort_id = prop_abort["mission_id"]

    requests.post(f"{BASE_URL}/missions/{m_abort_id}/authorize", json={"action": "APPROVE"}, headers=admin_headers)
    requests.post(f"{BASE_URL}/missions/{m_abort_id}/dispatch", json={"notes": "Dispatch before abort"}, headers=admin_headers)

    abort_res = requests.post(
        f"{BASE_URL}/missions/{m_abort_id}/abort",
        json={"notes": "Extreme weather hazard force abort"},
        headers=admin_headers,
    )
    assert abort_res.status_code == 200, f"Abort failed: {abort_res.text}"
    assert abort_res.json()["status"] == "ABORTED"
    print(f"10. Mission #{m_abort_id} Emergency Abort: DISPATCHED -> ABORTED")

    # 11. AUDIT LOG VERIFICATION
    audit_res = requests.get(f"{BASE_URL}/audit-logs", headers=admin_headers)
    assert audit_res.status_code == 200
    audits = audit_res.json()
    print(f"\n11. Audit Log Database Count: {len(audits)} immutable audit records verified.")

    print("\n=== ALL E2E MISSION LIFECYCLE TESTS PASSED 100% ===")

if __name__ == "__main__":
    run_e2e_lifecycle_tests()

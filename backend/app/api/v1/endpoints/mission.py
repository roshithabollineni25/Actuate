"""Rescue mission management and coordination endpoints."""

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agents.mission_agent import MissionCoordinationAgent
from app.agents.replanning_agent import ContinuousReplanningAgent
from app.core.security import require_roles
from app.db.session import get_db
from app.models.mission import Mission, MissionStatus
from app.schemas.mission import (
    MissionCreate,
    MissionRead,
    MissionUpdate,
    MissionAuthorizeRequest,
    MissionProposalRequest,
    MissionStatusUpdateRequest,
    MissionDispatchRequest,
    MissionAbortRequest,
    MissionReplanAuthorizeRequest,
)


class MissionReplanEvaluateRequest(BaseModel):
    """Evaluate an active mission against current telemetry and road hazards."""

    current_team_lat: float = Field(..., ge=-90, le=90)
    current_team_lng: float = Field(..., ge=-180, le=180)
    destination_lat: float = Field(..., ge=-90, le=90)
    destination_lng: float = Field(..., ge=-180, le=180)
    active_road_updates: List[Dict[str, Any]] = Field(default_factory=list)


router = APIRouter()
# ============================================================
# DYNAMIC REPLANNING EVALUATION
# ============================================================

@router.post(
    "/{mission_id}/replan/evaluate",
    summary="Evaluate Mission for Dynamic Replanning",
)
async def evaluate_mission_replan(
    mission_id: int,
    request: MissionReplanEvaluateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(
        require_roles("ADMIN", "RESCUE_TEAM")
    ),
) -> Dict[str, Any]:
    """
    Evaluate an active mission for dynamic route replanning.

    This endpoint only creates a replan proposal. It does not mutate
    the mission route, ETA, status, or dispatch state. Human approval
    is required before any proposed route is applied.
    """

    agent = ContinuousReplanningAgent()

    try:
        return await agent.evaluate_mission_telemetry(
            mission_id=mission_id,
            current_team_lat=request.current_team_lat,
            current_team_lng=request.current_team_lng,
            destination_lat=request.destination_lat,
            destination_lng=request.destination_lng,
            active_road_updates=request.active_road_updates,
            db=db,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    except Exception as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                f"Mission replanning evaluation failed: "
                f"{type(exc).__name__}: {exc}"
            ),
        )




# ============================================================
# CREATE MISSION
# ============================================================

@router.post(
    "",
    response_model=MissionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create Mission",
)
def create_mission(
    mission_in: MissionCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(
        require_roles("ADMIN", "RESCUE_TEAM")
    ),
) -> MissionRead:
    """Create a new rescue mission."""

    mission_data = mission_in.model_dump()

    # Prevent manually creating a mission in a later lifecycle state.
    mission_data["status"] = MissionStatus.PROPOSED

    mission = Mission(**mission_data)

    db.add(mission)
    db.commit()
    db.refresh(mission)

    return mission


# ============================================================
# GENERATE MISSION PROPOSAL
# ============================================================

@router.post(
    "/propose",
    summary="Generate Mission Proposal",
)
async def generate_mission_proposal(
    request: MissionProposalRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(
        require_roles("ADMIN", "RESCUE_TEAM")
    ),
):
    """Generate a PROPOSED mission from Phase 3 agent outputs."""

    agent = MissionCoordinationAgent()

    try:
        return await agent.synthesize_mission_proposal(
            db=db,
            incident_id=request.incident_id,
            situation_data=request.situation_data,
            risk_data=request.risk_data,
            resource_data=request.resource_data,
            route_data=request.route_data,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    except Exception as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                f"Mission proposal failed: "
                f"{type(exc).__name__}: {exc}"
            ),
        )


# ============================================================
# LIST MISSIONS
# ============================================================

@router.get(
    "",
    response_model=List[MissionRead],
    summary="List Missions",
)
def list_missions(
    db: Session = Depends(get_db),
    current_user: dict = Depends(
        require_roles("CITIZEN", "ADMIN", "RESCUE_TEAM")
    ),
) -> List[MissionRead]:
    """Return all rescue missions."""

    return (
        db.query(Mission)
        .order_by(Mission.id)
        .all()
    )


# ============================================================
# HUMAN AUTHORIZATION
# ============================================================

@router.post(
    "/{mission_id}/authorize",
    summary="Authorize Mission",
)
async def authorize_mission(
    mission_id: int,
    request: MissionAuthorizeRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(
        require_roles("ADMIN")
    ),
):
    """Approve or reject a proposed mission."""

    coordinator_user_id = current_user.get("sub")

    if coordinator_user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user ID not available.",
        )

    try:
        coordinator_user_id = int(coordinator_user_id)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authenticated user ID.",
        )

    agent = MissionCoordinationAgent()

    try:
        return await agent.authorize_mission(
            db=db,
            mission_id=mission_id,
            coordinator_user_id=coordinator_user_id,
            action=request.action,
            notes=request.notes,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    except Exception as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                f"Mission authorization failed: "
                f"{type(exc).__name__}: {exc}"
            ),
        )


# ============================================================
# DISPATCH APPROVED MISSION
# ============================================================

@router.post(
    "/{mission_id}/dispatch",
    summary="Dispatch Mission",
)
async def dispatch_mission(
    mission_id: int,
    request: MissionDispatchRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(
        require_roles("ADMIN")
    ),
):
    """Dispatch an approved mission."""

    coordinator_user_id = current_user.get("sub")

    if coordinator_user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user ID not available.",
        )

    try:
        coordinator_user_id = int(coordinator_user_id)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authenticated user ID.",
        )

    agent = MissionCoordinationAgent()

    try:
        return await agent.dispatch_mission(
            db=db,
            mission_id=mission_id,
            coordinator_user_id=coordinator_user_id,
            notes=request.notes,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    except Exception as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                f"Mission dispatch failed: "
                f"{type(exc).__name__}: {exc}"
            ),
        )


# ============================================================
# UPDATE MISSION STATUS
# ============================================================

@router.post(
    "/{mission_id}/status",
    summary="Update Mission Status",
)
async def update_mission_status(
    mission_id: int,
    request: MissionStatusUpdateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(
        require_roles("ADMIN", "RESCUE_TEAM")
    ),
):
    """
    Advance a mission through its validated lifecycle.

    Rescue-team transitions are authorized against the
    assigned team's leader_id.
    """

    actor_user_id = current_user.get("sub")

    if actor_user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user ID not available.",
        )

    try:
        actor_user_id = int(actor_user_id)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authenticated user ID.",
        )

    actor_role = current_user.get("role")

    agent = MissionCoordinationAgent()

    try:
        return await agent.transition_mission(
            db=db,
            mission_id=mission_id,
            target_status=request.status,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            notes=request.notes,
            human_verified=(actor_role == "ADMIN"),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    except Exception as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                f"Mission status update failed: "
                f"{type(exc).__name__}: {exc}"
            ),
        )


# ============================================================
# ABORT MISSION
# ============================================================

@router.post(
    "/{mission_id}/abort",
    summary="Abort Mission",
)
async def abort_mission(
    mission_id: int,
    request: MissionAbortRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(
        require_roles("ADMIN", "RESCUE_TEAM")
    ),
):
    """Abort an active mission."""

    actor_user_id = current_user.get("sub")

    if actor_user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user ID not available.",
        )

    try:
        actor_user_id = int(actor_user_id)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authenticated user ID.",
        )

    actor_role = current_user.get("role")

    agent = MissionCoordinationAgent()

    try:
        return await agent.abort_mission(
            db=db,
            mission_id=mission_id,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            notes=request.notes,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    except Exception as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                f"Mission abort failed: "
                f"{type(exc).__name__}: {exc}"
            ),
        )


# ============================================================
# GET SINGLE MISSION
# ============================================================

@router.get(
    "/{mission_id}",
    response_model=MissionRead,
    summary="Get Mission",
)
def get_mission(
    mission_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(
        require_roles("CITIZEN", "ADMIN", "RESCUE_TEAM")
    ),
) -> MissionRead:
    """Return one rescue mission."""

    mission = (
        db.query(Mission)
        .filter(Mission.id == mission_id)
        .first()
    )

    if not mission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mission not found.",
        )

    return mission


# ============================================================
# UPDATE MISSION
# ============================================================

@router.patch(
    "/{mission_id}",
    response_model=MissionRead,
    summary="Update Mission",
)
def update_mission(
    mission_id: int,
    mission_in: MissionUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(
        require_roles("ADMIN", "RESCUE_TEAM")
    ),
) -> MissionRead:
    """Update mission details without changing lifecycle status."""

    mission = (
        db.query(Mission)
        .filter(Mission.id == mission_id)
        .first()
    )

    if not mission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mission not found.",
        )

    update_data = mission_in.model_dump(
        exclude_unset=True
    )

    for field, value in update_data.items():
        setattr(mission, field, value)

    db.commit()
    db.refresh(mission)

    return mission


# ============================================================
# DELETE MISSION
# ============================================================

@router.delete(
    "/{mission_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Mission",
)
def delete_mission(
    mission_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(
        require_roles("ADMIN")
    ),
):
    """Delete a rescue mission."""

    mission = (
        db.query(Mission)
        .filter(Mission.id == mission_id)
        .first()
    )

    if not mission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mission not found.",
        )

    db.delete(mission)
    db.commit()

    return None


# ============================================================
# AUTHORIZE MISSION REPLAN (HITL DETOUR APPROVAL / REJECTION)
# ============================================================

@router.post(
    "/{mission_id}/replan/authorize",
    response_model=MissionRead,
    summary="Authorize Mission Replan",
)
def authorize_mission_replan(
    mission_id: int,
    request: MissionReplanAuthorizeRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(
        require_roles("ADMIN", "RESCUE_TEAM")
    ),
) -> MissionRead:
    """Approve or reject a proposed mission route detour."""
    import json
    from app.models.audit_log import AuditLog

    mission = (
        db.query(Mission)
        .filter(Mission.id == mission_id)
        .first()
    )

    if not mission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mission not found.",
        )

    if request.action == "APPROVE":
        if mission.pending_replan_status != "REPLAN_PENDING_HITL" or not mission.pending_route_polyline:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No pending route detour available for approval.",
            )

        previous_route = mission.route_polyline
        previous_eta = mission.eta_minutes

        mission.route_polyline = mission.pending_route_polyline
        mission.eta_minutes = mission.pending_eta_minutes

        mission.pending_route_polyline = None
        mission.pending_eta_minutes = None
        mission.pending_replan_reason = None
        mission.pending_replan_status = None

        audit = AuditLog(
            agent_name="EOC_Coordinator",
            action="MISSION_REPLAN_APPROVED",
            input_payload=json.dumps({"mission_id": mission_id, "action": "APPROVE", "notes": request.notes}),
            output_payload=json.dumps({
                "mission_id": mission_id,
                "previous_eta": previous_eta,
                "new_eta": mission.eta_minutes,
                "status": mission.status.value,
            }),
            human_verified=True,
            verified_by=int(current_user.get("sub")) if current_user.get("sub") and str(current_user.get("sub")).isdigit() else 1,
        )
        db.add(audit)

    elif request.action == "REJECT":
        if not mission.pending_replan_status:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No pending replan request available.",
            )

        mission.pending_route_polyline = None
        mission.pending_eta_minutes = None
        mission.pending_replan_reason = None
        mission.pending_replan_status = None

        audit = AuditLog(
            agent_name="EOC_Coordinator",
            action="MISSION_REPLAN_REJECTED",
            input_payload=json.dumps({"mission_id": mission_id, "action": "REJECT", "notes": request.notes}),
            output_payload=json.dumps({"mission_id": mission_id, "status": mission.status.value}),
            human_verified=True,
            verified_by=int(current_user.get("sub")) if current_user.get("sub") and str(current_user.get("sub")).isdigit() else 1,
        )
        db.add(audit)

    db.commit()
    db.refresh(mission)
    return mission
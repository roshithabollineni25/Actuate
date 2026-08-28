"""Incident intake, incident management, and AI coordination endpoints."""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agents.mission_agent import MissionCoordinationAgent
from app.agents.resource_agent import ResourceMatchingAgent
from app.agents.risk_agent import RiskPriorityAgent
from app.agents.route_agent import RouteIntelligenceAgent
from app.agents.situation_agent import SituationUnderstandingAgent
from app.core.security import require_roles
from app.db.session import get_db
from app.models.incident import Incident
from app.models.mission import Mission
from app.models.rescue_team import RescueTeam
from app.schemas.incident import (
    IncidentCreate,
    IncidentRead,
    IncidentUpdate,
)


router = APIRouter()


# ---------------------------------------------------------------------------
# PHASE 2B - AI Situation Analysis
# ---------------------------------------------------------------------------


class SituationAnalysisRequest(BaseModel):
    """Request payload for AI-powered emergency situation analysis."""

    raw_text: Optional[str] = Field(
        default=None,
        min_length=1,
        description="Unstructured emergency report provided by the citizen.",
    )

    audio_url: Optional[str] = Field(
        default=None,
        description=(
            "URL of an emergency audio recording. "
            "Audio processing is not yet enabled."
        ),
    )

    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional contextual metadata associated with the report.",
    )


class SituationAnalysisResponse(BaseModel):
    """Structured response returned by the Situation Understanding Agent."""

    category: str
    urgency_level: str
    people_count: int
    children_count: int
    elderly_count: int
    pregnant_count: int
    injured_count: int
    critical_count: int
    trapped_count: int
    medical_needs: list[str]
    hazards: list[str]
    location_description: Optional[str] = None
    summary: str


@router.post(
    "/analyze",
    response_model=SituationAnalysisResponse,
    summary="Analyze Emergency Report",
    description=(
        "Use the Situation Understanding Agent and Google Gemini "
        "to convert an unstructured emergency report into "
        "structured emergency information."
    ),
)
async def analyze_incident(
    request: SituationAnalysisRequest,
    current_user: dict = Depends(
        require_roles("CITIZEN", "ADMIN", "RESCUE_TEAM")
    ),
) -> SituationAnalysisResponse:
    """Analyze an emergency report using the Situation Understanding Agent."""

    if not request.raw_text and not request.audio_url:
        raise HTTPException(
            status_code=422,
            detail="Provide either raw_text or audio_url.",
        )

    try:
        agent = SituationUnderstandingAgent()

        result = await agent.analyze_report(
            raw_text=request.raw_text,
            audio_url=request.audio_url,
            metadata=request.metadata,
        )

        return SituationAnalysisResponse.model_validate(result)

    except NotImplementedError as exc:
        raise HTTPException(
            status_code=501,
            detail=str(exc),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                f"Situation analysis failed: "
                f"{type(exc).__name__}: {str(exc)}"
            ),
        )


# ---------------------------------------------------------------------------
# PHASE 3 - FULL MULTI-AGENT EMERGENCY COORDINATION
# ---------------------------------------------------------------------------


@router.post(
    "/{incident_id}/coordinate",
    summary="Run Full Emergency Coordination Pipeline",
    description=(
        "Runs Situation Understanding, Risk, Resource, Route, "
        "and Mission Coordination agents."
    ),
)
async def coordinate_incident(
    incident_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(
        require_roles("ADMIN", "RESCUE_TEAM")
    ),
) -> Dict[str, Any]:
    """
    Run the complete ResQMesh multi-agent coordination pipeline.

    Pipeline:

        Situation Understanding
                ↓
        Risk / Priority
                ↓
        Resource Matching
                ↓
        Safe Route
                ↓
        Mission Proposal

    The resulting mission remains PROPOSED and requires human approval.
    """

    # ------------------------------------------------------------------
    # 1. LOAD INCIDENT
    # ------------------------------------------------------------------

    incident = (
        db.query(Incident)
        .filter(Incident.id == incident_id)
        .first()
    )

    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident not found.",
        )

    # ------------------------------------------------------------------
    # 1A. DUPLICATE MISSION PROTECTION
    # ------------------------------------------------------------------
    #
    # IMPORTANT:
    # One incident should not generate multiple missions every time
    # the coordinator button is clicked.
    #
    # If a mission already exists for this incident, return the newest
    # existing mission instead of running the complete pipeline again.
    #

   
    try:

        # ==============================================================
        # 2. SITUATION UNDERSTANDING AGENT
        # ==============================================================

        situation_agent = SituationUnderstandingAgent()

        raw_text = (
            incident.raw_input_text
            or incident.description
            or incident.title
        )

        situation_data = await situation_agent.analyze_report(
            raw_text=raw_text,
            metadata={
                "incident_id": incident.id,
                "latitude": incident.latitude,
                "longitude": incident.longitude,
            },
        )

        # Trusted coordinates.
        #
        # These coordinates come from the incident database record,
        # NOT from the LLM.
        situation_data["latitude"] = incident.latitude
        situation_data["longitude"] = incident.longitude

        # ==============================================================
        # 3. UPDATE NORMALIZED INCIDENT DATA
        # ==============================================================

        try:

            situation_category = situation_data.get("category")

            if situation_category:
                incident.category = situation_category

            situation_urgency = situation_data.get("urgency_level")

            if situation_urgency:
                incident.urgency_level = situation_urgency

            people_count = situation_data.get("people_count")

            if isinstance(people_count, int) and people_count > 0:
                incident.estimated_casualties = people_count

            db.commit()
            db.refresh(incident)

        except Exception:

            # Do not allow normalized metadata persistence failure
            # to destroy the coordination pipeline.
            db.rollback()

            incident = (
                db.query(Incident)
                .filter(Incident.id == incident_id)
                .first()
            )

        # ==============================================================
        # 4. RISK / PRIORITY AGENT
        # ==============================================================

        risk_agent = RiskPriorityAgent()

        risk_data = await risk_agent.evaluate_risk(
            incident_data=situation_data,
            environmental_context={},
        )

        # ==============================================================
        # 5. RESOURCE MATCHING AGENT
        # ==============================================================

        resource_agent = ResourceMatchingAgent()

        resource_data = await resource_agent.match_resources(
            incident_id=incident_id,
            db=db,
        )

        # ==============================================================
        # 6. ROUTE INTELLIGENCE AGENT
        # ==============================================================

        route_agent = RouteIntelligenceAgent()

        primary_team = resource_data.get("primary_team")

        route_data: Dict[str, Any]

        if primary_team:

            rescue_team_id = primary_team.get("team_id")

            rescue_team = (
                db.query(RescueTeam)
                .filter(RescueTeam.id == rescue_team_id)
                .first()
            )

            if (
                rescue_team
                and rescue_team.current_lat is not None
                and rescue_team.current_lng is not None
                and incident.latitude is not None
                and incident.longitude is not None
            ):

                route_data = await route_agent.compute_safe_route(
                    origin_lat=float(rescue_team.current_lat),
                    origin_lng=float(rescue_team.current_lng),
                    destination_lat=float(incident.latitude),
                    destination_lng=float(incident.longitude),
                    db=db,
                    avoid_hazards=True,
                )

            else:

                route_data = {
                    "route_status": "ROUTE_UNAVAILABLE",
                    "message": (
                        "Primary rescue team does not have valid "
                        "GPS coordinates."
                    ),
                    "route_polyline": [],
                    "eta_minutes": None,
                }

        else:

            route_data = {
                "route_status": "NO_TEAM_AVAILABLE",
                "message": (
                    "No available rescue team was found, "
                    "so route calculation was skipped."
                ),
                "route_polyline": [],
                "eta_minutes": None,
            }

        # ==============================================================
        # 7. PREPARE RESOURCE DATA FOR MISSION AGENT
        # ==============================================================

        mission_resource_data = dict(resource_data)

        if primary_team:

            mission_resource_data["rescue_team_id"] = (
                primary_team.get("team_id")
            )

        else:

            mission_resource_data["rescue_team_id"] = None

        # ==============================================================
        # 8. MISSION COORDINATION AGENT
        # ==============================================================

        mission_agent = MissionCoordinationAgent()

        mission_data = await mission_agent.synthesize_mission_proposal(
            db=db,
            incident_id=incident_id,
            situation_data=situation_data,
            risk_data=risk_data,
            resource_data=mission_resource_data,
            route_data=route_data,
        )

        # ==============================================================
        # 9. RETURN COMPLETE AGENT TRACE
        # ==============================================================

        return {
            "success": True,
            "incident_id": incident_id,

            "pipeline": [
                "SituationUnderstandingAgent",
                "RiskPriorityAgent",
                "ResourceMatchingAgent",
                "RouteIntelligenceAgent",
                "MissionCoordinationAgent",
            ],

            "situation": situation_data,

            "risk": risk_data,

            "resources": resource_data,

            "route": route_data,

            "mission": mission_data,

            "human_approval_required": True,

            "message": (
                "Multi-agent emergency coordination completed. "
                "Mission is PROPOSED and requires human approval."
            ),
        }

    except ValueError as exc:

        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    except Exception as exc:

        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                f"Emergency coordination failed: "
                f"{type(exc).__name__}: {str(exc)}"
            ),
        )


# ============================================================================
# PHASE 2C - INCIDENT MANAGEMENT
# ============================================================================


@router.post(
    "",
    response_model=IncidentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create Incident",
    description="Create and persist a new emergency incident.",
)
def create_incident(
    incident_in: IncidentCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(
        require_roles("CITIZEN", "ADMIN", "RESCUE_TEAM")
    ),
) -> IncidentRead:
    """Create a new incident record."""

    reporter_id = current_user.get("sub")

    try:
        reporter_id = (
            int(reporter_id)
            if reporter_id is not None
            else None
        )
    except (TypeError, ValueError):
        reporter_id = None

    incident = Incident(
        reporter_id=reporter_id,
        title=incident_in.title,
        description=incident_in.description,
        category=incident_in.category,
        urgency_level=incident_in.urgency_level,
        latitude=incident_in.latitude,
        longitude=incident_in.longitude,
        address=incident_in.address,
        raw_input_text=incident_in.raw_input_text,
        audio_file_url=incident_in.audio_file_url,
        estimated_casualties=incident_in.estimated_casualties,
    )

    db.add(incident)
    db.commit()
    db.refresh(incident)

    return IncidentRead.model_validate(incident)


@router.get(
    "",
    response_model=list[IncidentRead],
    summary="List Incidents",
    description="Return all stored emergency incidents.",
)
def list_incidents(
    db: Session = Depends(get_db),
    current_user: dict = Depends(
        require_roles("CITIZEN", "ADMIN", "RESCUE_TEAM")
    ),
) -> list[IncidentRead]:
    """Return all incidents with active mission status."""

    incidents = (
        db.query(Incident)
        .order_by(Incident.created_at.desc())
        .all()
    )

    missions = (
        db.query(Mission)
        .order_by(Mission.id.desc())
        .all()
    )
    mission_map = {}
    for m in missions:
        if m.incident_id not in mission_map:
            mission_map[m.incident_id] = m.status.value

    results = []
    for incident in incidents:
        read_item = IncidentRead.model_validate(incident)
        read_item.active_mission_status = mission_map.get(incident.id)
        results.append(read_item)

    return results


@router.get(
    "/{incident_id}",
    response_model=IncidentRead,
    summary="Get Incident",
    description="Return a single incident by ID.",
)
def get_incident(
    incident_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(
        require_roles("CITIZEN", "ADMIN", "RESCUE_TEAM")
    ),
) -> IncidentRead:
    """Return one incident."""

    incident = (
        db.query(Incident)
        .filter(Incident.id == incident_id)
        .first()
    )

    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident not found",
        )

    mission = (
        db.query(Mission)
        .filter(Mission.incident_id == incident_id)
        .order_by(Mission.id.desc())
        .first()
    )

    read_item = IncidentRead.model_validate(incident)
    if mission:
        read_item.active_mission_status = mission.status.value

    return read_item


@router.patch(
    "/{incident_id}",
    response_model=IncidentRead,
    summary="Update Incident",
    description="Update an existing emergency incident.",
)
def update_incident(
    incident_id: int,
    incident_in: IncidentUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(
        require_roles("CITIZEN", "ADMIN", "RESCUE_TEAM")
    ),
) -> IncidentRead:
    """Update an existing incident."""

    incident = (
        db.query(Incident)
        .filter(Incident.id == incident_id)
        .first()
    )

    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident not found",
        )

    update_data = incident_in.model_dump(
        exclude_unset=True
    )

    for field, value in update_data.items():
        setattr(incident, field, value)

    db.commit()
    db.refresh(incident)

    return IncidentRead.model_validate(incident)


@router.delete(
    "/{incident_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Incident",
    description="Delete an existing emergency incident.",
)
def delete_incident(
    incident_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(
        require_roles("ADMIN")
    ),
) -> None:
    """Delete an incident. Restricted to administrators."""

    incident = (
        db.query(Incident)
        .filter(Incident.id == incident_id)
        .first()
    )

    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident not found",
        )

    db.delete(incident)
    db.commit()
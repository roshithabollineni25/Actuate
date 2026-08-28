"""Route intelligence endpoints."""

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agents.route_agent import RouteIntelligenceAgent
from app.core.security import require_roles
from app.db.session import get_db


router = APIRouter()


class RouteRequest(BaseModel):
    origin_lat: float = Field(..., ge=-90, le=90)
    origin_lng: float = Field(..., ge=-180, le=180)

    destination_lat: float = Field(..., ge=-90, le=90)
    destination_lng: float = Field(..., ge=-180, le=180)

    avoid_hazards: bool = True


@router.post(
    "/compute",
    summary="Compute Safe Emergency Route",
)
async def compute_route(
    request: RouteRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(
        require_roles("ADMIN", "RESCUE_TEAM")
    ),
) -> Dict[str, Any]:

    agent = RouteIntelligenceAgent()

    try:
        return await agent.compute_safe_route(
            origin_lat=request.origin_lat,
            origin_lng=request.origin_lng,
            destination_lat=request.destination_lat,
            destination_lng=request.destination_lng,
            db=db,
            avoid_hazards=request.avoid_hazards,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Route calculation failed: {str(exc)}",
        )
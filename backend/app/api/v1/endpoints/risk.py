"""Risk and priority assessment endpoints."""

from typing import Any, Dict

from fastapi import APIRouter, Depends

from app.agents.risk_agent import RiskPriorityAgent
from app.core.security import require_roles
from app.schemas.risk import (
    RiskAssessmentRequest,
    RiskAssessmentResponse,
)


router = APIRouter()


@router.post(
    "/assess",
    response_model=RiskAssessmentResponse,
    summary="Assess Emergency Risk",
    description=(
        "Run the deterministic Risk and Priority Agent against "
        "structured emergency situation data."
    ),
)
async def assess_risk(
    request: RiskAssessmentRequest,
    current_user: dict = Depends(
        require_roles("CITIZEN", "ADMIN", "RESCUE_TEAM")
    ),
) -> RiskAssessmentResponse:

    agent = RiskPriorityAgent()

    result = await agent.evaluate_risk(
        incident_data=request.situation_data,
        environmental_context=request.environmental_context,
    )

    return RiskAssessmentResponse.model_validate(result)
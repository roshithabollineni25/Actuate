"""Schemas for deterministic emergency risk assessment."""

from typing import Any, Dict, List

from pydantic import BaseModel, Field


class RiskAssessmentRequest(BaseModel):
    """Structured situation data supplied to the Risk/Priority Agent."""

    situation_data: Dict[str, Any] = Field(
        ...,
        description="Structured situation assessment produced by the Situation Agent.",
    )

    environmental_context: Dict[str, Any] | None = Field(
        default=None,
        description="Verified environmental and operational context.",
    )


class RiskAssessmentResponse(BaseModel):
    """Deterministic risk and triage assessment."""

    risk_score: float = Field(..., ge=1.0, le=10.0)

    triage_level: str

    category: str

    urgency_level: str

    casualty_summary: Dict[str, int]

    hazards: List[str]

    matched_hazards: List[str]

    environmental_context: Dict[str, Any]

    environmental_risk_score: float

    elapsed_minutes: float | None = None

    casualty_risk_velocity: Dict[str, Any]

    danger_radius_meters: int

    danger_perimeter: List[Dict[str, float]]

    score_breakdown: Dict[str, float]

    rationale: str
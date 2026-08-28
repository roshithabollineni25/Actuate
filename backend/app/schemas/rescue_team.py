"""Schemas for rescue team management."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.rescue_team import (
    TeamSpecialization,
    TeamStatus,
)


class RescueTeamBase(BaseModel):
    """Common rescue team fields."""

    team_name: str = Field(..., min_length=2, max_length=100)

    leader_id: Optional[int] = None

    specialization: TeamSpecialization = TeamSpecialization.GENERAL_RESPONSE

    status: TeamStatus = TeamStatus.AVAILABLE

    capacity: int = Field(default=4, ge=1)

    current_lat: Optional[float] = Field(
        default=None,
        ge=-90.0,
        le=90.0,
    )

    current_lng: Optional[float] = Field(
        default=None,
        ge=-180.0,
        le=180.0,
    )

    contact_radio_channel: Optional[str] = Field(
        default=None,
        max_length=50,
    )


class RescueTeamCreate(RescueTeamBase):
    """Create a rescue team."""

    pass


class RescueTeamUpdate(BaseModel):
    """Update an existing rescue team."""

    team_name: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=100,
    )

    leader_id: Optional[int] = None

    specialization: Optional[TeamSpecialization] = None

    status: Optional[TeamStatus] = None

    capacity: Optional[int] = Field(
        default=None,
        ge=1,
    )

    current_lat: Optional[float] = Field(
        default=None,
        ge=-90.0,
        le=90.0,
    )

    current_lng: Optional[float] = Field(
        default=None,
        ge=-180.0,
        le=180.0,
    )

    contact_radio_channel: Optional[str] = Field(
        default=None,
        max_length=50,
    )


class RescueTeamRead(RescueTeamBase):
    """Return rescue team information."""

    id: int
    created_at: datetime

    class Config:
        from_attributes = True
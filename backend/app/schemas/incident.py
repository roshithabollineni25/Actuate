"""Incident and emergency intake schemas."""

from typing import Optional
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.incident import (
    IncidentCategory,
    UrgencyLevel,
    IncidentStatus,
)


class IncidentBase(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None

    category: IncidentCategory = IncidentCategory.OTHER
    urgency_level: UrgencyLevel = UrgencyLevel.MEDIUM

    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)

    address: Optional[str] = None
    estimated_casualties: int = Field(default=0, ge=0)


class IncidentCreate(IncidentBase):
    raw_input_text: Optional[str] = None
    audio_file_url: Optional[str] = None


class IncidentUpdate(BaseModel):
    """Fields that can be updated after an incident is created."""

    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[IncidentCategory] = None
    urgency_level: Optional[UrgencyLevel] = None
    status: Optional[IncidentStatus] = None

    latitude: Optional[float] = Field(
        default=None,
        ge=-90.0,
        le=90.0,
    )

    longitude: Optional[float] = Field(
        default=None,
        ge=-180.0,
        le=180.0,
    )

    address: Optional[str] = None
    raw_input_text: Optional[str] = None
    audio_file_url: Optional[str] = None

    estimated_casualties: Optional[int] = Field(
        default=None,
        ge=0,
    )


class IncidentRead(IncidentBase):
    id: int
    reporter_id: Optional[int] = None
    status: IncidentStatus
    active_mission_status: Optional[str] = None

    raw_input_text: Optional[str] = None
    audio_file_url: Optional[str] = None

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
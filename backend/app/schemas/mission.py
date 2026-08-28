"""Schemas for rescue mission coordination and lifecycle."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.mission import MissionPriority, MissionStatus


class MissionBase(BaseModel):
    """Common mission fields."""

    incident_id: int = Field(..., gt=0)

    rescue_team_id: Optional[int] = Field(
        default=None,
        gt=0,
    )

    status: MissionStatus = MissionStatus.PROPOSED

    priority: MissionPriority = MissionPriority.P2_URGENT

    eta_minutes: Optional[float] = Field(
        default=None,
        ge=0,
    )

    route_polyline: Optional[str] = None
    pending_route_polyline: Optional[str] = None
    pending_eta_minutes: Optional[float] = None
    pending_replan_reason: Optional[str] = None
    pending_replan_status: Optional[str] = None

    mission_brief: Optional[str] = None


class MissionCreate(MissionBase):
    """Create a new rescue mission."""

    pass


class MissionUpdate(BaseModel):
    """Update editable mission information.

    Mission lifecycle status must be changed through the
    dedicated lifecycle endpoints, not this generic PATCH endpoint.
    """

    rescue_team_id: Optional[int] = Field(
        default=None,
        gt=0,
    )

    priority: Optional[MissionPriority] = None

    eta_minutes: Optional[float] = Field(
        default=None,
        ge=0,
    )

    route_polyline: Optional[str] = None

    mission_brief: Optional[str] = None


class MissionRead(MissionBase):
    """Return stored mission information."""

    id: int

    approved_by: Optional[int] = None

    approved_at: Optional[datetime] = None

    created_at: datetime

    updated_at: datetime

    class Config:
        from_attributes = True


class MissionProposalRequest(BaseModel):
    """Validated outputs from Phase 3 agents."""

    incident_id: int = Field(..., gt=0)

    situation_data: dict

    risk_data: dict

    resource_data: dict

    route_data: dict


class MissionAuthorizeRequest(BaseModel):
    """Human coordinator authorization request."""

    action: str = Field(
        ...,
        pattern="^(APPROVE|REJECT)$",
    )

    notes: Optional[str] = None


class MissionStatusUpdateRequest(BaseModel):
    """Request to transition a mission to its next lifecycle state."""

    status: MissionStatus

    notes: Optional[str] = None


class MissionDispatchRequest(BaseModel):
    """Request to dispatch an approved mission."""

    notes: Optional[str] = None


class MissionAbortRequest(BaseModel):
    """Request to abort an active mission."""

    notes: Optional[str] = None


class MissionReplanAuthorizeRequest(BaseModel):
    """Request to authorize or reject a pending mission route detour."""

    action: str = Field(
        ...,
        pattern="^(APPROVE|REJECT)$",
    )

    notes: Optional[str] = None
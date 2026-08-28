"""Rescue mission coordination and lifecycle model."""

import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, Enum, ForeignKey, Text
from app.db.base import Base


class MissionStatus(str, enum.Enum):
    PROPOSED = "PROPOSED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    DISPATCHED = "DISPATCHED"
    EN_ROUTE = "EN_ROUTE"
    ON_SCENE = "ON_SCENE"
    COMPLETED = "COMPLETED"
    ABORTED = "ABORTED"


class MissionPriority(str, enum.Enum):
    P1_IMMEDIATE = "P1_IMMEDIATE"
    P2_URGENT = "P2_URGENT"
    P3_STANDARD = "P3_STANDARD"
    P4_MONITOR = "P4_MONITOR"


class Mission(Base):
    __tablename__ = "missions"

    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(Integer, ForeignKey("incidents.id"), nullable=False)
    rescue_team_id = Column(Integer, ForeignKey("rescue_teams.id"), nullable=True)
    status = Column(Enum(MissionStatus), default=MissionStatus.PROPOSED, nullable=False)
    priority = Column(Enum(MissionPriority), default=MissionPriority.P2_URGENT, nullable=False)
    eta_minutes = Column(Float, nullable=True)
    route_polyline = Column(Text, nullable=True)
    pending_route_polyline = Column(Text, nullable=True)
    pending_eta_minutes = Column(Float, nullable=True)
    pending_replan_reason = Column(Text, nullable=True)
    pending_replan_status = Column(String, nullable=True)
    mission_brief = Column(Text, nullable=True)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

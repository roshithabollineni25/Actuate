"""Rescue team model definition."""

import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, Enum, ForeignKey
from app.db.base import Base


class TeamSpecialization(str, enum.Enum):
    BOAT_RESCUE = "BOAT_RESCUE"
    MEDICAL_EVAC = "MEDICAL_EVAC"
    HEAVY_EQUIPMENT = "HEAVY_EQUIPMENT"
    DRONE_RECON = "DRONE_RECON"
    URBAN_SEARCH = "URBAN_SEARCH"
    GENERAL_RESPONSE = "GENERAL_RESPONSE"


class TeamStatus(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    DEPLOYED = "DEPLOYED"
    STANDBY = "STANDBY"
    OFF_DUTY = "OFF_DUTY"


class RescueTeam(Base):
    __tablename__ = "rescue_teams"

    id = Column(Integer, primary_key=True, index=True)
    team_name = Column(String(100), unique=True, nullable=False)
    leader_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    specialization = Column(Enum(TeamSpecialization), default=TeamSpecialization.GENERAL_RESPONSE, nullable=False)
    status = Column(Enum(TeamStatus), default=TeamStatus.AVAILABLE, nullable=False)
    capacity = Column(Integer, default=4, nullable=False)
    current_lat = Column(Float, nullable=True)
    current_lng = Column(Float, nullable=True)
    contact_radio_channel = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

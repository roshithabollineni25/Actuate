"""Incident model for emergency reports."""

import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, Enum, ForeignKey, Text
from app.db.base import Base


class IncidentCategory(str, enum.Enum):
    FLOOD = "FLOOD"
    FIRE = "FIRE"
    BUILDING_COLLAPSE = "BUILDING_COLLAPSE"
    MEDICAL_EMERGENCY = "MEDICAL_EMERGENCY"
    TRAPPED_PERSONS = "TRAPPED_PERSONS"
    HAZARDOUS_LEAK = "HAZARDOUS_LEAK"
    OTHER = "OTHER"


class UrgencyLevel(str, enum.Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class IncidentStatus(str, enum.Enum):
    REPORTED = "REPORTED"
    TRIAGED = "TRIAGED"
    MISSION_PROPOSED = "MISSION_PROPOSED"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CANCELLED = "CANCELLED"


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True)
    reporter_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    title = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    category = Column(Enum(IncidentCategory), default=IncidentCategory.OTHER, nullable=False)
    urgency_level = Column(Enum(UrgencyLevel), default=UrgencyLevel.MEDIUM, nullable=False)
    status = Column(Enum(IncidentStatus), default=IncidentStatus.REPORTED, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    address = Column(String(500), nullable=True)
    raw_input_text = Column(Text, nullable=True)
    audio_file_url = Column(String(500), nullable=True)
    estimated_casualties = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

"""Road network status and obstruction tracking model."""

import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, Enum, Text
from app.db.base import Base


class RoadCondition(str, enum.Enum):
    CLEAR = "CLEAR"
    FLOODED = "FLOODED"
    BLOCKED = "BLOCKED"
    DEBRIS_RESTRICTED = "DEBRIS_RESTRICTED"
    BRIDGE_COLLAPSED = "BRIDGE_COLLAPSED"
    HAZARDOUS = "HAZARDOUS"


class RoadStatus(Base):
    __tablename__ = "road_statuses"

    id = Column(Integer, primary_key=True, index=True)
    osm_way_id = Column(String(50), nullable=True, index=True)
    road_name = Column(String(150), nullable=True)
    condition = Column(Enum(RoadCondition), default=RoadCondition.CLEAR, nullable=False)
    hazard_notes = Column(Text, nullable=True)
    latitude_start = Column(Float, nullable=False)
    longitude_start = Column(Float, nullable=False)
    latitude_end = Column(Float, nullable=True)
    longitude_end = Column(Float, nullable=True)
    reported_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

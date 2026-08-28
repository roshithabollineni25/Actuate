"""Physical and medical resource inventory model."""

import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, Enum
from app.db.base import Base


class ResourceType(str, enum.Enum):
    LIFE_BOAT = "LIFE_BOAT"
    AMBULANCE = "AMBULANCE"
    MEDICAL_KIT = "MEDICAL_KIT"
    DRONE = "DRONE"
    WATER_PUMP = "WATER_PUMP"
    GENERATOR = "GENERATOR"
    FOOD_RATIONS = "FOOD_RATIONS"
    CLEAN_WATER = "CLEAN_WATER"
    OTHER = "OTHER"


class ResourceStatus(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    ALLOCATED = "ALLOCATED"
    DEPLETED = "DEPLETED"
    MAINTENANCE = "MAINTENANCE"


class Resource(Base):
    __tablename__ = "resources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    type = Column(
        Enum(ResourceType),
        default=ResourceType.OTHER,
        nullable=False
    )
    total_quantity = Column(Integer, default=1, nullable=False)
    available_quantity = Column(Integer, default=1, nullable=False)
    location_lat = Column(Float, nullable=False)
    location_lng = Column(Float, nullable=False)
    depot_name = Column(String(100), nullable=True)
    status = Column(
        Enum(ResourceStatus),
        default=ResourceStatus.AVAILABLE,
        nullable=False
    )
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
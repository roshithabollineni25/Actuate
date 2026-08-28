"""Schemas for road network status and obstruction tracking."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.road_status import RoadCondition


class RoadStatusBase(BaseModel):
    """Common road status fields."""

    osm_way_id: Optional[str] = Field(
        default=None,
        max_length=50,
    )

    road_name: Optional[str] = Field(
        default=None,
        max_length=150,
    )

    condition: RoadCondition = RoadCondition.CLEAR

    hazard_notes: Optional[str] = None

    latitude_start: float = Field(
        ...,
        ge=-90.0,
        le=90.0,
    )

    longitude_start: float = Field(
        ...,
        ge=-180.0,
        le=180.0,
    )

    latitude_end: Optional[float] = Field(
        default=None,
        ge=-90.0,
        le=90.0,
    )

    longitude_end: Optional[float] = Field(
        default=None,
        ge=-180.0,
        le=180.0,
    )


class RoadStatusCreate(RoadStatusBase):
    """Create a road status report."""

    pass


class RoadStatusUpdate(BaseModel):
    """Update an existing road status."""

    osm_way_id: Optional[str] = Field(
        default=None,
        max_length=50,
    )

    road_name: Optional[str] = Field(
        default=None,
        max_length=150,
    )

    condition: Optional[RoadCondition] = None

    hazard_notes: Optional[str] = None

    latitude_start: Optional[float] = Field(
        default=None,
        ge=-90.0,
        le=90.0,
    )

    longitude_start: Optional[float] = Field(
        default=None,
        ge=-180.0,
        le=180.0,
    )

    latitude_end: Optional[float] = Field(
        default=None,
        ge=-90.0,
        le=90.0,
    )

    longitude_end: Optional[float] = Field(
        default=None,
        ge=-180.0,
        le=180.0,
    )


class RoadStatusRead(RoadStatusBase):
    """Return stored road status information."""

    id: int
    reported_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
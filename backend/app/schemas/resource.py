"""Schemas for physical and medical resource inventory."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.resource import ResourceType, ResourceStatus


class ResourceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)

    type: ResourceType = ResourceType.OTHER

    total_quantity: int = Field(
        default=1,
        ge=0
    )

    available_quantity: int = Field(
        default=1,
        ge=0
    )

    location_lat: float = Field(
        ...,
        ge=-90.0,
        le=90.0
    )

    location_lng: float = Field(
        ...,
        ge=-180.0,
        le=180.0
    )

    depot_name: str | None = Field(
        default=None,
        max_length=100
    )

    status: ResourceStatus = ResourceStatus.AVAILABLE


class ResourceCreate(ResourceBase):
    pass


class ResourceUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100
    )

    type: ResourceType | None = None

    total_quantity: int | None = Field(
        default=None,
        ge=0
    )

    available_quantity: int | None = Field(
        default=None,
        ge=0
    )

    location_lat: float | None = Field(
        default=None,
        ge=-90.0,
        le=90.0
    )

    location_lng: float | None = Field(
        default=None,
        ge=-180.0,
        le=180.0
    )

    depot_name: str | None = Field(
        default=None,
        max_length=100
    )

    status: ResourceStatus | None = None


class ResourceRead(ResourceBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
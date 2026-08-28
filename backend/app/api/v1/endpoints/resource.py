"""Resource inventory management endpoints."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from typing import Any, Dict, Optional

from app.agents.resource_agent import ResourceMatchingAgent

from app.core.security import require_roles
from app.db.session import get_db
from app.models.resource import Resource
from app.schemas.resource import (
    ResourceCreate,
    ResourceRead,
    ResourceUpdate,
)


router = APIRouter()


@router.post(
    "",
    response_model=ResourceRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create Resource",
)
def create_resource(
    resource_in: ResourceCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(
        require_roles("ADMIN")
    ),
) -> ResourceRead:
    """Create a new resource."""

    resource = Resource(**resource_in.model_dump())

    db.add(resource)
    db.commit()
    db.refresh(resource)

    return resource


@router.get(
    "",
    response_model=List[ResourceRead],
    summary="List Resources",
)
def list_resources(
    db: Session = Depends(get_db),
    current_user: dict = Depends(
        require_roles("CITIZEN", "ADMIN", "RESCUE_TEAM")
    ),
) -> List[ResourceRead]:
    """Return all resources."""

    return (
        db.query(Resource)
        .order_by(Resource.id)
        .all()
    )


@router.get(
    "/{resource_id}",
    response_model=ResourceRead,
    summary="Get Resource",
)
def get_resource(
    resource_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(
        require_roles("CITIZEN", "ADMIN", "RESCUE_TEAM")
    ),
) -> ResourceRead:
    """Return one resource by ID."""

    resource = (
        db.query(Resource)
        .filter(Resource.id == resource_id)
        .first()
    )

    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found.",
        )

    return resource


@router.patch(
    "/{resource_id}",
    response_model=ResourceRead,
    summary="Update Resource",
)
def update_resource(
    resource_id: int,
    resource_in: ResourceUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(
        require_roles("ADMIN")
    ),
) -> ResourceRead:
    """Update an existing resource."""

    resource = (
        db.query(Resource)
        .filter(Resource.id == resource_id)
        .first()
    )

    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found.",
        )

    update_data = resource_in.model_dump(
        exclude_unset=True
    )

    for field, value in update_data.items():
        setattr(resource, field, value)

    db.commit()
    db.refresh(resource)

    return resource


@router.delete(
    "/{resource_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Resource",
)
def delete_resource(
    resource_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(
        require_roles("ADMIN")
    ),
):
    """Delete a resource."""

    resource = (
        db.query(Resource)
        .filter(Resource.id == resource_id)
        .first()
    )

    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found.",
        )

    db.delete(resource)
    db.commit()

    return None

@router.post(
    "/match/{incident_id}",
    summary="Match Resources to Incident",
)
async def match_resources_to_incident(
    incident_id: int,
    required_specialization: Optional[str] = None,
    required_equipment: Optional[List[str]] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(
        require_roles("ADMIN", "RESCUE_TEAM")
    ),
) -> Dict[str, Any]:
    """
    Match available rescue teams and resources to an incident.
    """

    agent = ResourceMatchingAgent()

    try:
        return await agent.match_resources(
            incident_id=incident_id,
            db=db,
            required_specialization=required_specialization,
            required_equipment=required_equipment,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
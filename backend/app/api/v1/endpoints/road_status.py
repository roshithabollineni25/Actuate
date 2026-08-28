"""Road status and obstruction management endpoints."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import require_roles
from app.db.session import get_db
from app.models.road_status import RoadStatus
from app.schemas.road_status import (
    RoadStatusCreate,
    RoadStatusRead,
    RoadStatusUpdate,
)


router = APIRouter()


from app.services.replanning_service import evaluate_road_hazard_against_active_missions

@router.post(
    "",
    response_model=RoadStatusRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create Road Status",
)
async def create_road_status(
    road_in: RoadStatusCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(
        require_roles("ADMIN", "RESCUE_TEAM")
    ),
) -> RoadStatusRead:
    """Create a new road status report."""

    road_status = RoadStatus(**road_in.model_dump())

    db.add(road_status)
    db.commit()
    db.refresh(road_status)

    # Application-level trigger for continuous replanning
    await evaluate_road_hazard_against_active_missions(db, road_status)

    return road_status


@router.get(
    "",
    response_model=List[RoadStatusRead],
    summary="List Road Statuses",
)
def list_road_statuses(
    db: Session = Depends(get_db),
    current_user: dict = Depends(
        require_roles("CITIZEN", "ADMIN", "RESCUE_TEAM")
    ),
) -> List[RoadStatusRead]:
    """Return all road status reports."""

    return (
        db.query(RoadStatus)
        .order_by(RoadStatus.id)
        .all()
    )


@router.get(
    "/{road_status_id}",
    response_model=RoadStatusRead,
    summary="Get Road Status",
)
def get_road_status(
    road_status_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(
        require_roles("CITIZEN", "ADMIN", "RESCUE_TEAM")
    ),
) -> RoadStatusRead:
    """Return one road status report."""

    road_status = (
        db.query(RoadStatus)
        .filter(RoadStatus.id == road_status_id)
        .first()
    )

    if not road_status:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Road status not found.",
        )

    return road_status


@router.patch(
    "/{road_status_id}",
    response_model=RoadStatusRead,
    summary="Update Road Status",
)
async def update_road_status(
    road_status_id: int,
    road_in: RoadStatusUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(
        require_roles("ADMIN", "RESCUE_TEAM")
    ),
) -> RoadStatusRead:
    """Update an existing road status report."""

    road_status = (
        db.query(RoadStatus)
        .filter(RoadStatus.id == road_status_id)
        .first()
    )

    if not road_status:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Road status not found.",
        )

    update_data = road_in.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(road_status, field, value)

    db.commit()
    db.refresh(road_status)

    # Application-level trigger for continuous replanning
    await evaluate_road_hazard_against_active_missions(db, road_status)

    return road_status


@router.delete(
    "/{road_status_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Road Status",
)
def delete_road_status(
    road_status_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(
        require_roles("ADMIN")
    ),
):
    """Delete a road status report."""

    road_status = (
        db.query(RoadStatus)
        .filter(RoadStatus.id == road_status_id)
        .first()
    )

    if not road_status:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Road status not found.",
        )

    db.delete(road_status)
    db.commit()

    return None
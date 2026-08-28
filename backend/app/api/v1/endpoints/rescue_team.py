"""Rescue team management endpoints."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import require_roles
from app.db.session import get_db
from app.models.rescue_team import RescueTeam
from app.schemas.rescue_team import (
    RescueTeamCreate,
    RescueTeamRead,
    RescueTeamUpdate,
)


router = APIRouter()


@router.post(
    "",
    response_model=RescueTeamRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create Rescue Team",
)
def create_rescue_team(
    team_in: RescueTeamCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(
        require_roles("ADMIN")
    ),
) -> RescueTeamRead:
    """Create a new rescue team."""

    existing_team = (
        db.query(RescueTeam)
        .filter(RescueTeam.team_name == team_in.team_name)
        .first()
    )

    if existing_team:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A rescue team with this name already exists.",
        )

    team = RescueTeam(**team_in.model_dump())

    db.add(team)
    db.commit()
    db.refresh(team)

    return team


@router.get(
    "",
    response_model=List[RescueTeamRead],
    summary="List Rescue Teams",
)
def list_rescue_teams(
    db: Session = Depends(get_db),
    current_user: dict = Depends(
        require_roles("CITIZEN", "ADMIN", "RESCUE_TEAM")
    ),
) -> List[RescueTeamRead]:
    """Return all rescue teams."""

    return (
        db.query(RescueTeam)
        .order_by(RescueTeam.id)
        .all()
    )


@router.get(
    "/{team_id}",
    response_model=RescueTeamRead,
    summary="Get Rescue Team",
)
def get_rescue_team(
    team_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(
        require_roles("CITIZEN", "ADMIN", "RESCUE_TEAM")
    ),
) -> RescueTeamRead:
    """Return one rescue team by ID."""

    team = (
        db.query(RescueTeam)
        .filter(RescueTeam.id == team_id)
        .first()
    )

    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rescue team not found.",
        )

    return team


@router.patch(
    "/{team_id}",
    response_model=RescueTeamRead,
    summary="Update Rescue Team",
)
def update_rescue_team(
    team_id: int,
    team_in: RescueTeamUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(
        require_roles("ADMIN")
    ),
) -> RescueTeamRead:
    """Update an existing rescue team."""

    team = (
        db.query(RescueTeam)
        .filter(RescueTeam.id == team_id)
        .first()
    )

    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rescue team not found.",
        )

    update_data = team_in.model_dump(exclude_unset=True)

    if "team_name" in update_data:
        existing_team = (
            db.query(RescueTeam)
            .filter(
                RescueTeam.team_name == update_data["team_name"],
                RescueTeam.id != team_id,
            )
            .first()
        )

        if existing_team:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A rescue team with this name already exists.",
            )

    for field, value in update_data.items():
        setattr(team, field, value)

    db.commit()
    db.refresh(team)

    return team


@router.delete(
    "/{team_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Rescue Team",
)
def delete_rescue_team(
    team_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(
        require_roles("ADMIN")
    ),
):
    """Delete a rescue team."""

    team = (
        db.query(RescueTeam)
        .filter(RescueTeam.id == team_id)
        .first()
    )

    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rescue team not found.",
        )

    db.delete(team)
    db.commit()

    return None
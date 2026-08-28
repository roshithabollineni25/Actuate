"""API v1 master router aggregating all sub-routers."""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    health,
    auth,
    incident,
    rescue_team,
    resource,
    road_status,
    mission,
    risk,
    route,
    audit,
)


api_router = APIRouter()


# Core routes
api_router.include_router(
    health.router,
    tags=["Health"],
)

api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"],
)

api_router.include_router(
    incident.router,
    prefix="/incidents",
    tags=["Incidents"],
)

api_router.include_router(
    rescue_team.router,
    prefix="/rescue-teams",
    tags=["Rescue Teams"],
)

api_router.include_router(
    resource.router,
    prefix="/resources",
    tags=["Resources"],
)

api_router.include_router(
    road_status.router,
    prefix="/road-status",
    tags=["Road Status"],
)

api_router.include_router(
    mission.router,
    prefix="/missions",
    tags=["Missions"],
)

api_router.include_router(
    risk.router,
    prefix="/risk",
    tags=["Risk & Priority"],
)

api_router.include_router(
    route.router,
    prefix="/route",
    tags=["Route Intelligence"],
)

api_router.include_router(
    audit.router,
    tags=["Audit Logs"],
)
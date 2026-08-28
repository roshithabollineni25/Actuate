"""Health check and database connectivity endpoints."""

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.schemas.health import HealthResponse, DatabaseHealthResponse
from app.core.database import verify_database_connection

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="System Health Check",
    description="Check the operational status of the ResQMesh AI API.",
)
async def health_check() -> HealthResponse:
    """Return operational health status. No authentication required."""
    return HealthResponse(
        status="ok",
        service="ResQMesh AI API",
    )


@router.get(
    "/health/db",
    response_model=DatabaseHealthResponse,
    summary="Database Connectivity Check",
    description=(
        "Verify that FastAPI can reach the Supabase PostgreSQL database "
        "by executing a lightweight SELECT 1 query. "
        "Does not expose any credentials or connection strings."
    ),
)
async def database_health_check():
    """Execute SELECT 1 against PostgreSQL and return connectivity status."""
    is_healthy, message = verify_database_connection()

    response_body = DatabaseHealthResponse(
        status="ok" if is_healthy else "error",
        service="ResQMesh AI API",
        database="connected" if is_healthy else "unreachable",
        detail=message,
    )

    http_status = status.HTTP_200_OK if is_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(content=response_body.model_dump(), status_code=http_status)
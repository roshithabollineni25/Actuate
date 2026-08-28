"""ResQMesh AI FastAPI Application Main Entrypoint.

"AI-Powered Emergency Coordination. Human-Verified Response."
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.logging import logger
from app.db.base import Base
from app.db.session import engine
from app.core.database import verify_database_connection


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown event lifecycle."""
    logger.info("Initializing ResQMesh AI platform...")
    logger.info(f"Configured Gemini AI model: {settings.GEMINI_MODEL}")

    # Log database host only (never the password)
    db_target = settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else settings.DATABASE_URL
    logger.info(f"Database Target: {db_target}")

    # Verify database connectivity with SELECT 1 (no table creation in Phase 2A)
    db_ok, db_msg = verify_database_connection()
    if db_ok:
        logger.info(f"Database connectivity verified: {db_msg}")
    else:
        logger.warning(f"Database connectivity check failed at startup: {db_msg}")

    yield

    logger.info("Shutting down ResQMesh AI platform.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="ResQMesh AI — Agentic Emergency Response & Resource Coordination Platform.\n\n"
                "Tagline: 'AI-Powered Emergency Coordination. Human-Verified Response.'",
    version="0.1.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)

# Configure CORS using settings.BACKEND_CORS_ORIGINS dynamically
app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin).rstrip("/") for origin in settings.BACKEND_CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global uncaught exception handler to prevent leakages and ensure structured errors."""
    logger.error(f"Unhandled error processing {request.method} {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An internal server error occurred during request processing.",
            "error_type": exc.__class__.__name__,
        },
    )


# Mount versioned API router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/", tags=["Root"])
async def root():
    """Root platform welcome message."""
    return {
        "service": settings.PROJECT_NAME,
        "tagline": "AI-Powered Emergency Coordination. Human-Verified Response.",
        "version": "0.1.0",
        "docs": f"{settings.API_V1_STR}/docs",
        "health": f"{settings.API_V1_STR}/health",
    }

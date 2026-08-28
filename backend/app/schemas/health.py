"""Health check response schemas."""

from typing import Optional
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "ResQMesh AI API"


class DatabaseHealthResponse(BaseModel):
    status: str
    service: str = "ResQMesh AI API"
    database: str
    detail: Optional[str] = None

"""Pytest fixtures for ResQMesh AI backend testing."""

import pytest
from fastapi.testclient import TestClient
from app.main import app


from app.db.session import SessionLocal, engine
from app.db.base import Base


@pytest.fixture(scope="session")
def client():
    """Create a synchronous TestClient instance for endpoint tests."""
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="function")
def db_session():
    """Create a transactional database session for tests."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

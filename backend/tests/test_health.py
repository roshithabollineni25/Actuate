"""Tests for health check and root endpoints."""

from fastapi import status


def test_health_check(client):
    """Test GET /api/v1/health returns expected status and service payload."""
    response = client.get("/api/v1/health")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "ResQMesh AI API"


def test_root_endpoint(client):
    """Test root endpoint returns 200 and platform metadata."""
    response = client.get("/")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["service"] == "ResQMesh AI API"
    assert "tagline" in data
    assert "docs" in data


def test_database_health_check(client):
    """Test GET /api/v1/health/db executes SELECT 1 and returns connectivity status."""
    response = client.get("/api/v1/health/db")
    data = response.json()
    # Accept both 200 (connected) and 503 (unreachable) as valid structured responses
    assert response.status_code in (status.HTTP_200_OK, status.HTTP_503_SERVICE_UNAVAILABLE)
    assert "status" in data
    assert data["status"] in ("ok", "error")
    assert "database" in data
    assert data["database"] in ("connected", "unreachable")
    # Verify no secrets are exposed in the response
    response_text = response.text
    assert "PASSWORD" not in response_text
    assert "@" not in response_text or "pooler.supabase.com" not in response_text
